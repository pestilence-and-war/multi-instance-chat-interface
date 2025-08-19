# event_monitor.py

import os
import time
import json
import logging
import traceback
from dotenv import load_dotenv

# Import the singleton and helper function
from chat_manager import chat_manager
from my_tools.persona_manager import get_persona_details
load_dotenv()

# Configure logging to file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [EventMonitor] - %(message)s',
    handlers=[
        logging.FileHandler("monitor_logs.txt"),
        logging.StreamHandler()
    ]
)

class EventMonitor:
    def __init__(self, project_root=".", mode="auto", provider_name="Google", model_name="gemini-2.5-flash"):
        self.project_root = os.path.abspath(project_root)
        self.tasks_dir = os.path.join(self.project_root, "tasks")
        self.deliverables_dir = os.path.join(self.project_root, "archive", "deliverables")
        self.mode = mode
        self.provider_name = provider_name
        self.model_name = model_name

        # Use a state file to track processed files, making it resilient to restarts
        self.state_file = os.path.join(self.project_root, "monitor_state.json")
        self.processed_files = self._load_state()

    def _load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                return set(json.load(f))
        return set()

    def _save_state(self):
        with open(self.state_file, 'w') as f:
            json.dump(list(self.processed_files), f)

    def run(self):
        logging.info(f"AATFS Event Monitor started in '{self.mode}' mode.")
        while True:
            try:
                if self.mode == "stepped" and os.path.exists(os.path.join(self.tasks_dir, "review_pending.lock")):
                    logging.info("Paused. Awaiting user approval for a task in '3_review'.")
                    time.sleep(10)
                    continue

                self.scan_and_trigger()
            except Exception as e:
                logging.error(f"FATAL ERROR in main loop: {e}\n{traceback.format_exc()}")
            time.sleep(5)

    def scan_and_trigger(self):
        # The order of checks is critical for logical workflow
        self.handle_new_deliverables()
        self.handle_assigned_tasks()
        lock_file_path = os.path.join(self.tasks_dir, "pm_assigning.lock")
        if not os.path.exists(lock_file_path):
            self.handle_pending_tasks()
        else:
            logging.info("Skipping pending task check: Project Manager assignment is in progress (lock file exists).")
        self.handle_pending_tasks()
        self._save_state()

    def handle_new_deliverables(self):
        path = self.deliverables_dir
        for filename in os.listdir(path):
            filepath = os.path.join(path, filename)
            if filepath not in self.processed_files:
                logging.info(f"New Deliverable Detected: {filename}")
                prompt = (
                    f"A new deliverable has been created at 'archive/deliverables/{filename}'. "
                    "Your task is to identify which task in 'tasks/1_assigned/' or 'tasks/3_review/' this deliverable satisfies. "
                    f"Then, move that task's JSON file to the 'tasks/4_done/' directory. Finally, check the 'tasks/0_pending/' directory to see if you can assign the next task."
                )
                self.trigger_persona_and_run("Project Manager", prompt)
                self.processed_files.add(filepath)

    def handle_assigned_tasks(self):
        path = os.path.join(self.tasks_dir, "1_assigned")
        for filename in os.listdir(path):
            filepath = os.path.join(path, filename)
            if filepath not in self.processed_files:
                try:
                    with open(filepath, 'r') as f:
                        task_data = json.load(f)
                    
                    specialist_persona = task_data.get("persona")
                    if not specialist_persona:
                        logging.warning(f"Task file {filename} has no 'persona' field. Skipping.")
                        continue

                    logging.info(f"New Assigned Task Detected: {filename} for persona '{specialist_persona}'")
                    prompt = (
                        f"You have been assigned a new task. The task details are in the file 'tasks/1_assigned/{filename}'. "
                        "Read the contents of this file, execute the task described, and save your deliverable to the specified 'output_path'."
                    )
                    self.trigger_persona_and_run(specialist_persona, prompt)
                    self.processed_files.add(filepath)
                except Exception as e:
                    logging.error(f"Error processing assigned task {filename}: {e}")
                    # Consider moving the file to '5_failed' here
                    self.processed_files.add(filepath)

    def handle_pending_tasks(self):
        path = os.path.join(self.tasks_dir, "0_pending")
        if any(f for f in os.listdir(path) if f.endswith('.json')):
            logging.info("Pending tasks found. Acquiring lock and triggering Project Manager.")
             
            # --- CREATE THE LOCK FILE FIRST ---
            lock_file_path = os.path.join(self.tasks_dir, "pm_assigning.lock")
            with open(lock_file_path, 'w') as f:
                f.write(f"Locked at {time.time()}")
             
            prompt = (
                "There are tasks in the 'tasks/0_pending/' directory. "
                "Your job is to assign the next available task by moving its file to 'tasks/1_assigned/'. "
                "After you have successfully moved the file, you MUST perform one final, critical action: "
                "use the `jailed_delete_file` tool to delete the lock file located at 'tasks/pm_assigning.lock'. "
                "This signals that you are done and the system can continue."
            )
            self.trigger_persona_and_run("Project Manager", prompt)


    def trigger_persona_and_run(self, persona_name, prompt):
        instance = None
        try:
            logging.info(f"--- Triggering Persona: '{persona_name}' ---")
            
            # 1. Get Persona Details using our new helper
            details_str = get_persona_details(persona_name)
            details = json.loads(details_str)
            if details.get("status") == "error":
                raise ValueError(details.get("message"))

            # 2. Create a temporary ChatInstance via the ChatManager
            logging.info(f"Creating instance with provider: {self.provider_name}")
            instance = chat_manager.create_instance(provider_name=self.provider_name)
            if not instance:
                raise RuntimeError("Failed to create ChatInstance via ChatManager.")
            
            instance.name = f"AATFS_HEADLESS_{persona_name}_{instance.instance_id[:4]}"
            
            # 3. Configure the instance to be the persona
            instance.set_config(system_prompt=details.get("system_prompt"), model=self.model_name)
            for tool_name in details.get("tools", []):
                module_path = instance.tool_function_to_module_map.get(tool_name)
                if module_path:
                    instance.register_tool_from_config(name=tool_name, module_path=module_path, function_name=tool_name)
                else:
                    logging.warning(f"Tool '{tool_name}' for persona '{persona_name}' not found in tool map.")
            
            # 4. Execute the headless turn using our new method
            logging.info(f"Running prompt for '{persona_name}': '{prompt}'")
            result = instance.execute_headless_turn(prompt)
            logging.info(f"Persona '{persona_name}' finished. Status: {result['status']}. Output: {result['content']}")

        except Exception as e:
            logging.error(f"An error occurred while running persona '{persona_name}': {e}\n{traceback.format_exc()}")
        finally:
            # 5. VERY IMPORTANT: Clean up the temporary instance
            if instance:
                chat_manager.remove_instance(instance.instance_id)
                logging.info(f"Cleaned up temporary instance {instance.instance_id} for '{persona_name}'.")
            logging.info(f"--- Persona Trigger Finished: '{persona_name}' ---")


if __name__ == "__main__":
    monitor = EventMonitor(provider_name="Google", model_name="gemini-2.5-flash")
    monitor.run()