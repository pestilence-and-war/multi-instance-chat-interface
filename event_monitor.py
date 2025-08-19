import os
import time
import json
from chat_instance import ChatInstance
from my_tools.persona_manager import PersonaManager
from my_tools.jailed_file_manager import JailedFileManager

class EventMonitor:
    def __init__(self, project_root=".", mode="auto"):
        self.project_root = os.path.abspath(project_root)
        self.tasks_dir = os.path.join(self.project_root, "tasks")
        self.deliverables_dir = os.path.join(self.project_root, "archive", "deliverables")
        self.mode = mode
        self.processed_files = set() # To avoid processing the same event multiple times
        self.persona_manager = PersonaManager()
        self.file_manager = JailedFileManager(self.project_root)

    def run(self):
        """The main, infinite loop of the monitor."""
        print("AATFS Event Monitor started. Watching for file system events...")
        while True:
            self.scan_and_trigger()
            time.sleep(5) # Polling interval of 5 seconds

    def scan_and_trigger(self):
        """
        Scans all monitored directories and triggers the appropriate handlers.
        The order of checks is important to ensure logical consistency.
        1. Check for deliverables (completed work).
        2. Check for assigned tasks (work in progress).
        3. Check for pending tasks (new work to be assigned).
        """
        # Implementation will call the handler methods below
        if self.mode == "stepped" and self.file_manager.file_exists(os.path.join(self.project_root, "review_pending.lock")):
            print("Monitor paused pending user review.")
            return

        self.handle_new_deliverables()
        self.handle_assigned_tasks()
        self.handle_pending_tasks()

    def handle_new_deliverables(self):
        """
        Event: A new file appears in /archive/deliverables/.
        Trigger: Activate the Project Manager to process the completed task.
        """
        # Logic to find new files in the deliverables dir, construct a prompt,
        # and call trigger_persona() for the "Project Manager".
        for root, _, files in os.walk(self.deliverables_dir):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                if file_path not in self.processed_files:
                    print(f"New deliverable detected: {file_path}")
                    prompt = f"A new deliverable '{file_name}' has been added to the archive. Please process this completed task."
                    self.trigger_persona("Project Manager", prompt)
                    self.processed_files.add(file_path)

    def handle_assigned_tasks(self):
        """
        Event: A new task file appears in a specialist queue (e.g., /tasks/1_assigned/).
        Trigger: Activate the specialist persona named in the task file.
        """
        # Logic to find new files in the assigned dir, parse the task JSON to get
        # the 'persona' field, and call trigger_persona() for that specialist.
        assigned_tasks_dir = os.path.join(self.tasks_dir, "1_assigned")
        for root, _, files in os.walk(assigned_tasks_dir):
            for file_name in files:
                if file_name.endswith(".json"):
                    file_path = os.path.join(root, file_name)
                    if file_path not in self.processed_files:
                        print(f"New assigned task detected: {file_path}")
                        try:
                            with open(file_path, 'r') as f:
                                task_data = json.load(f)
                            persona_name = task_data.get("persona")
                            task_description = task_data.get("description", "No description provided.")
                            if persona_name:
                                prompt = f"A new task '{file_name}' has been assigned to you: {task_description}. Please begin working on it."
                                self.trigger_persona(persona_name, prompt)
                                self.processed_files.add(file_path)
                            else:
                                print(f"Warning: Task file {file_name} in 1_assigned is missing 'persona' field.")
                        except json.JSONDecodeError:
                            print(f"Error: Could not decode JSON from {file_name}.")
                        except Exception as e:
                            print(f"An error occurred processing {file_name}: {e}")

    def handle_pending_tasks(self):
        """
        Event: A file exists in /tasks/0_pending/.
        Trigger: Activate the Project Manager to assign the next task.
        """
        # Logic to check if 0_pending is non-empty, construct a prompt,
        # and call trigger_persona() for the "Project Manager".
        pending_tasks_dir = os.path.join(self.tasks_dir, "0_pending")
        if os.path.exists(pending_tasks_dir) and os.listdir(pending_tasks_dir):
            for root, _, files in os.walk(pending_tasks_dir):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    if file_path not in self.processed_files:
                        print(f"Pending task detected: {file_name}")
                        prompt = f"There are new tasks in the '{os.path.basename(pending_tasks_dir)}' directory. Please review and assign the next task: {file_name}."
                        self.trigger_persona("Project Manager", prompt)
                        self.processed_files.add(file_path)

    def trigger_persona(self, persona_name, prompt):
        """
        The core activation logic. Instantiates and runs a persona headlessly.
        """
        print(f"Triggering persona: {persona_name} with prompt: {prompt}")
        try:
            # 1. Load the persona's JSON configuration using persona_manager.
            persona_data = self.persona_manager.get_persona(persona_name)
            if not persona_data:
                print(f"Error: Persona '{persona_name}' not found.")
                return

            # 2. Instantiate a ChatInstance with the persona's system_prompt and tools.
            # Assuming ChatInstance can take persona_data directly or needs specific fields
            # We'll need to check chat_instance.py for the exact constructor
            # For now, let's assume it needs system_prompt and tools_list
            system_prompt = persona_data.get("system_prompt", "")
            tools_list = persona_data.get("tools", []) # Assuming tools are listed here

            # This part will likely need adjustment after reviewing chat_instance.py
            # Placeholder for now:
            # chat_instance = ChatInstance(system_prompt=system_prompt, tools_list=tools_list)

            # 3. Add the initial prompt as the first user message.
            # 4. Programmatically run the chat loop.
            # This is the part that will require a new method in chat_instance.py
            # For now, let's just print a placeholder action.
            print(f"Simulating headless run for {persona_name} with prompt: {prompt}")
            # chat_instance.run_headless(initial_prompt=prompt) # This method needs to be added

            print(f"Persona {persona_name} finished processing event.")

        except Exception as e:
            print(f"Error triggering persona {persona_name}: {e}")

if __name__ == "__main__":
    monitor = EventMonitor()
    monitor.run()
