import os
import time
import json
import traceback
import queue
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from chat_instance import ChatInstance
from chat_manager import API_CLIENT_CLASSES, DEFAULT_PROVIDER

# --- Configuration ---
TASKS_ROOT = "tasks"
DELIVERABLES_ROOT = "archive/deliverables"
PERSONAS_ROOT = "personas"
TASK_DIRS = {
    "pending": os.path.join(TASKS_ROOT, "0_pending"),
    "assigned": os.path.join(TASKS_ROOT, "1_assigned"),
    "review": os.path.join(TASKS_ROOT, "3_review"),
    "done": os.path.join(TASKS_ROOT, "4_done"),
    "failed": os.path.join(TASKS_ROOT, "5_failed"),
}

# --- State Management ---
PROCESSING_FILES = set()

# --- Helper Functions ---
def move_task_to_failed(task_path, error_message="Unknown error"):
    if not os.path.exists(task_path):
        print(f"WARNING: Cannot move task to failed, file no longer exists: {task_path}")
        return
    failed_dir = TASK_DIRS["failed"]
    try:
        with open(task_path, 'r+', encoding='utf-8') as f:
            task_data = json.load(f)
            task_data['status'] = 'failed'
            task_data['error_message'] = str(error_message)
            task_data['failed_at'] = time.time()
            f.seek(0)
            json.dump(task_data, f, indent=2)
            f.truncate()
        destination_path = os.path.join(failed_dir, os.path.basename(task_path))
        print(f"Moving failed task from {task_path} to {destination_path}")
        os.replace(task_path, destination_path)
    except Exception as e:
        print(f"FATAL: Could not move failed task {task_path}: {e}")

def run_agent_for_task(prompt, persona_name, task_id):
    """Initializes and runs a ChatInstance for a given prompt and persona."""
    print(f"Instantiating agent with persona: '{persona_name}' for task '{task_id}'")
    persona_filename = f"{persona_name.lower().replace(' ', '_')}.json"
    persona_path = os.path.join(PERSONAS_ROOT, persona_filename)
    if not os.path.exists(persona_path):
        raise FileNotFoundError(f"Persona file not found at {persona_path}")

    with open(persona_path, 'r', encoding='utf-8') as f:
        persona_data = json.load(f)

    provider_name = "Ollama" # Use Ollama for local testing without API keys
    client_class = API_CLIENT_CLASSES.get(provider_name)
    if not client_class: raise ValueError(f"Provider '{provider_name}' not found.")
    # Ollama client doesn't require an API key, but ChatInstance expects a non-empty key to connect.
    api_key = os.getenv(f"OLLAMA_API_KEY", "ollama_is_local") # Pass a dummy key

    agent_instance = ChatInstance(api_client_class=client_class, api_key=api_key)
    if agent_instance.connection_error:
        raise ConnectionError(f"Failed to connect agent: {agent_instance.connection_error}")

    agent_instance.set_config(system_prompt=persona_data.get("system_prompt"))
    for tool_name in persona_data.get("tools", []):
        module_path = agent_instance.tool_function_to_module_map.get(tool_name)
        if module_path:
            agent_instance.register_tool_from_config(name=tool_name, module_path=module_path, function_name=tool_name)
        else:
            print(f"WARNING: Tool '{tool_name}' not found in map for persona '{persona_name}'.")

    sse_queue = queue.Queue()
    agent_instance.add_user_message(prompt)
    agent_instance.start_streaming_generation(sse_queue)

    if agent_instance.current_generation_thread:
        agent_instance.current_generation_thread.join()

    final_message = None
    while not sse_queue.empty():
        msg_json = sse_queue.get_nowait()
        if msg_json is None: continue
        msg = json.loads(msg_json)
        if msg.get("type") in ["finish", "error", "stopped"]:
            final_message = msg

    if final_message and final_message.get("type") == "error":
        raise RuntimeError(f"Agent returned an error: {final_message.get('content')}")

    return final_message

# --- Task Processors ---

def process_task_file(task_path):
    """Handles a new or modified task file."""
    try:
        with open(task_path, 'r', encoding='utf-8') as f:
            task_data = json.load(f)

        task_id = task_data.get("task_id")
        task_description = task_data.get("description")
        persona_name = task_data.get("persona")
        dependencies = task_data.get("dependencies", [])
        output_path = task_data.get("output_path")

        if not all([task_id, task_description, persona_name]):
            raise ValueError("Task file is missing required fields.")

        dependency_content = ""
        if dependencies:
            dependency_texts = []
            for dep_id in dependencies:
                dep_task_path = os.path.join(TASK_DIRS["done"], f"{dep_id}.json")
                if os.path.exists(dep_task_path):
                    # ... logic to read dep output ...
                    pass
            dependency_content = "\n\n".join(dependency_texts)

        prompt = f"Task: {task_description}\n\n{dependency_content}\n\nOutput should be saved to: {output_path}"

        run_agent_for_task(prompt, persona_name, task_id)

        if output_path and not os.path.exists(output_path):
            raise FileNotFoundError(f"Agent finished but did not create expected output: {output_path}")

        print(f"Task {task_id} completed successfully.")

    except Exception as e:
        print(f"ERROR processing task {task_path}: {e}")
        move_task_to_failed(task_path, str(e))

def process_deliverable_file(deliverable_path):
    """Triggers the Project Manager to review a new deliverable."""
    try:
        prompt = f"""A new deliverable has been created: `{deliverable_path}`.

Your task is to:
1. Identify which task in the `{TASK_DIRS['assigned']}` or `{TASK_DIRS['review']}` directory this deliverable corresponds to.
2. Review the deliverable's content.
3. If satisfactory, move the corresponding task file to `{TASK_DIRS['done']}`.
4. If not satisfactory, move the task to `{TASK_DIRS['failed']}` with a note about what needs to be fixed."""

        run_agent_for_task(prompt, "Project Manager", f"review-{os.path.basename(deliverable_path)}")
        print(f"Project Manager has been triggered to review {deliverable_path}.")

    except Exception as e:
        print(f"ERROR triggering review for {deliverable_path}: {e}")

# --- Watchdog Event Handler ---

class AATFSHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return

        filepath = event.src_path
        if filepath in PROCESSING_FILES:
            return

        print(f"--- Event: File Created - {filepath} ---")
        PROCESSING_FILES.add(filepath)

        try:
            if filepath.endswith(".json") and os.path.dirname(filepath) in [TASK_DIRS['pending'], TASK_DIRS['assigned']]:
                process_task_file(filepath)
            elif DELIVERABLES_ROOT in os.path.abspath(filepath):
                 # Simple check to see if the file is in the deliverables path
                 if os.path.commonpath([DELIVERABLES_ROOT, os.path.abspath(filepath)]) == os.path.abspath(DELIVERABLES_ROOT):
                    process_deliverable_file(filepath)
        finally:
            PROCESSING_FILES.remove(filepath)

# --- Main Execution ---

def main():
    print("Initializing AATFS Event Monitor...")
    for path in list(TASK_DIRS.values()) + [DELIVERABLES_ROOT]:
        os.makedirs(path, exist_ok=True)
        print(f"Watching directory: {path}")

    event_handler = AATFSHandler()
    observer = Observer()
    observer.schedule(event_handler, TASKS_ROOT, recursive=True)
    observer.schedule(event_handler, DELIVERABLES_ROOT, recursive=True)

    observer.start()
    print("Event Monitor started. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    print("Event Monitor has been shut down.")

if __name__ == "__main__":
    main()
