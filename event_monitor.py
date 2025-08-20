# event_monitor.py

import os
import time
import json
import logging
import traceback
from dotenv import load_dotenv
from datetime import datetime, timedelta # Added for time-based checks

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
    def __init__(self, project_root=".", mode="auto", provider_name="Google", model_name="gemini-2.5-flash", polling_interval=5):
        env_root = os.getenv("CODEBASE_DB_PATH")
        definitive_root = env_root or project_root
        self.project_root = os.path.abspath(definitive_root)
        logging.info(f"Event Monitor initialized with project root: {self.project_root}")

        # Define task directories
        self.tasks_dir = os.path.join(self.project_root, "tasks")
        self.pending_dir = os.path.join(self.tasks_dir, "0_pending")
        self.assigned_dir = os.path.join(self.tasks_dir, "1_assigned")
        self.review_dir = os.path.join(self.tasks_dir, "3_review")
        self.done_dir = os.path.join(self.tasks_dir, "4_done")
        self.failed_dir = os.path.join(self.tasks_dir, "5_failed") # New: For failed tasks

        self.deliverables_dir = os.path.join(self.project_root, "archive", "deliverables")

        # Ensure all necessary directories exist
        for d in [self.tasks_dir, self.pending_dir, self.assigned_dir, self.review_dir, self.done_dir, self.failed_dir, self.deliverables_dir]:
            os.makedirs(d, exist_ok=True)

        self.mode = mode
        self.provider_name = provider_name
        self.model_name = model_name
        self.polling_interval = polling_interval
        self.state_file = os.path.join(self.project_root, "monitor_state.json")

        # self.processed_files will now track files that have been *successfully* processed or moved to a final state
        self.processed_files = self._load_state() 

        # New: Max retries and initial backoff for LLM calls
        self.max_llm_retries = 3
        self.initial_backoff_seconds = 60 # Start with a 1-minute backoff

        # Lock file paths
        self.pm_assigning_lock = os.path.join(self.tasks_dir, "pm_assigning.lock")
        self.review_pending_lock = os.path.join(self.tasks_dir, "review_pending.lock")


    def _load_state(self):
        """Loads the set of processed file paths."""
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                return set(json.load(f))
        return set()

    def _save_state(self):
        """Saves the set of processed file paths."""
        with open(self.state_file, 'w') as f:
            json.dump(list(self.processed_files), f)

    def _update_task_status(self, filepath, new_status, retries=None, last_attempt=None):
        """Helper to update task JSON with new status and retry info."""
        try:
            with open(filepath, 'r+') as f:
                task_data = json.load(f)
                task_data["status"] = new_status
                if retries is not None:
                    task_data["retries_attempted"] = retries
                if last_attempt is not None:
                    task_data["last_attempt_time"] = last_attempt.isoformat()
                f.seek(0)
                json.dump(task_data, f, indent=4)
                f.truncate()
            logging.info(f"Updated task '{os.path.basename(filepath)}' to status: '{new_status}'")
            return True
        except Exception as e:
            logging.error(f"Failed to update task status for {filepath}: {e}")
            return False

    def _move_file(self, source_path, dest_dir):
        """Helper to move a file and handle potential errors."""
        filename = os.path.basename(source_path)
        destination_path = os.path.join(dest_dir, filename)
        try:
            os.rename(source_path, destination_path)
            logging.info(f"Moved '{filename}' from '{os.path.basename(os.path.dirname(source_path))}' to '{os.path.basename(dest_dir)}'.")
            return destination_path
        except OSError as e:
            logging.error(f"Error moving file {source_path} to {destination_path}: {e}")
            return None

    def _is_lock_stale(self, lock_file_path, timeout_minutes=10):
        """Checks if a lock file is stale (older than timeout_minutes)."""
        if os.path.exists(lock_file_path):
            try:
                # Read the timestamp if available, otherwise use mtime
                with open(lock_file_path, 'r') as f:
                    content = f.read().strip()
                if content.startswith("Locked at "):
                    lock_time_str = content.replace("Locked at ", "")
                    lock_timestamp = float(lock_time_str)
                else: # Fallback to mtime if file content is not standard
                    lock_timestamp = os.path.getmtime(lock_file_path)

                if (time.time() - lock_timestamp) > (timeout_minutes * 60):
                    logging.warning(f"Stale lock file detected: {lock_file_path}. It will be removed.")
                    os.remove(lock_file_path)
                    return True
            except Exception as e:
                logging.error(f"Error checking or removing stale lock file {lock_file_path}: {e}")
                # If error, assume it's not stale or handle carefully, prevent infinite loop
                return False
        return False

    def run(self):
        logging.info(f"AATFS Event Monitor started in '{self.mode}' mode.")
        while True:
            try:
                # Check for stale locks at the start of each loop
                self._is_lock_stale(self.pm_assigning_lock)
                self._is_lock_stale(self.review_pending_lock) # New: Check review lock

                if self.mode == "stepped" and os.path.exists(self.review_pending_lock):
                    logging.info("Paused. Awaiting user approval for a task in '3_review'.")
                    time.sleep(self.polling_interval)
                    continue

                self.scan_and_trigger()
            except Exception as e:
                logging.error(f"FATAL ERROR in main loop: {e}\n{traceback.format_exc()}")
            time.sleep(self.polling_interval)

    def scan_and_trigger(self):
        # The order of checks is critical for logical workflow
        self.handle_new_deliverables()
        self.handle_assigned_tasks() # This handles retries and moves to failed

        if not os.path.exists(self.pm_assigning_lock):
            self.handle_pending_tasks() # Only assign if no PM assignment is in progress
        else:
            logging.info("Skipping pending task check: Project Manager assignment is in progress (lock file exists).")

        self._save_state() # Save state after a full scan cycle

    def handle_new_deliverables(self):
        path = self.deliverables_dir
        for filename in os.listdir(path):
            filepath = os.path.join(path, filename)
            # Only process if it hasn't been added to processed_files *after* its creation
            if filepath not in self.processed_files:
                logging.info(f"New Deliverable Detected: {filename}")
                prompt = (
                    f"A new deliverable has been created at 'archive/deliverables/{filename}'. "
                    "Your task is to identify which task in 'tasks/1_assigned/' or 'tasks/3_review/' this deliverable satisfies. "
                    f"Then, move that task's JSON file to the 'tasks/4_done/' directory if the system is in 'auto' mode, "
                    f"or to 'tasks/3_review/' if in 'stepped' mode. If moving to '3_review/', you MUST also create a lock file "
                    f"named 'review_pending.lock' in the 'tasks/' directory to signal human review is needed. "
                    f"Finally, check the 'tasks/0_pending/' directory to see if you can assign the next task."
                )

                # The PM needs to know the current mode to decide where to move the task
                mode_info = f"The current system mode is '{self.mode}'. "
                if self.mode == "stepped":
                    mode_info += "Remember to create 'tasks/review_pending.lock' if moving to '3_review'."

                self.trigger_persona_and_run(
                    persona_name="Project Manager", 
                    prompt=mode_info + prompt,
                    task_filepath=filepath, # Pass deliverable path for state tracking if needed
                    is_deliverable=True # Flag to indicate this is a deliverable event
                )
                self.processed_files.add(filepath) # Mark the deliverable itself as processed

    def handle_assigned_tasks(self):
        # Iterate over a copy of the list to allow modification during iteration
        for filename in list(os.listdir(self.assigned_dir)):
            filepath = os.path.join(self.assigned_dir, filename)

            # We don't use self.processed_files here directly for assigned tasks
            # because tasks need to be re-processed on retry.
            # Instead, we rely on the task's internal status and retry count.

            try:
                with open(filepath, 'r') as f:
                    task_data = json.load(f)

                # Check task status and retry count
                current_status = task_data.get("status", "assigned")
                retries_attempted = task_data.get("retries_attempted", 0)
                last_attempt_time_str = task_data.get("last_attempt_time")

                # Calculate backoff time
                if last_attempt_time_str:
                    last_attempt_dt = datetime.fromisoformat(last_attempt_time_str)
                    required_wait_seconds = self.initial_backoff_seconds * (2 ** retries_attempted)
                    if (datetime.now() - last_attempt_dt).total_seconds() < required_wait_seconds:
                        logging.info(f"Task {filename} is in backoff period. Skipping for now.")
                        continue # Skip if still in backoff

                if current_status == "done" or current_status == "failed":
                    # This task has somehow ended up back here or was already handled
                    logging.warning(f"Task {filename} has status '{current_status}'. Moving to '{self.done_dir}' or '{self.failed_dir}'.")
                    if current_status == "done":
                        self._move_file(filepath, self.done_dir)
                        self.processed_files.add(filepath) # Mark as successfully processed
                    else: # current_status == "failed"
                        self._move_file(filepath, self.failed_dir)
                    continue

                if retries_attempted >= self.max_llm_retries:
                    logging.error(f"Task {filename} exceeded max retries ({self.max_llm_retries}). Moving to '5_failed'.")
                    if self._update_task_status(filepath, "failed", retries_attempted):
                        self._move_file(filepath, self.failed_dir)
                    continue

                specialist_persona = task_data.get("persona")
                if not specialist_persona:
                    logging.warning(f"Task file {filename} has no 'persona' field. Moving to '5_failed'.")
                    if self._update_task_status(filepath, "failed", retries_attempted):
                        self._move_file(filepath, self.failed_dir)
                    continue

                logging.info(f"Processing Assigned Task: {filename} for persona '{specialist_persona}' (Attempt: {retries_attempted + 1}/{self.max_llm_retries})")
                prompt = (
                    f"You have been assigned a new task. The task details are in the file 'tasks/1_assigned/{filename}'. "
                    "Read the contents of this file, execute the task described, and save your deliverable to the specified 'output_path'. "
                    "Do NOT move the task file itself; the Project Manager will handle that upon deliverable creation."
                )

                # Update status to "in_progress" before triggering
                self._update_task_status(filepath, "in_progress", retries_attempted, datetime.now())

                # Trigger persona and handle its result
                # The deliverable path is typically in task_data["output_path"]
                result = self.trigger_persona_and_run(specialist_persona, prompt, task_filepath=filepath) 

                if result['status'] == "success":
                    logging.info(f"Persona '{specialist_persona}' successfully completed task {filename}.")
                    # The PM handles moving the task to 'done' or 'review' after deliverable is detected.
                    # We only mark the *deliverable* as processed in self.processed_files in handle_new_deliverables.
                    # This task file remains in 1_assigned until the deliverable is processed by PM.
                else:
                    retries_attempted += 1
                    logging.warning(f"Persona '{specialist_persona}' failed task {filename}. Retrying (attempt {retries_attempted}).")
                    if not self._update_task_status(filepath, "assigned", retries_attempted, datetime.now()): # Update status back to assigned for next retry
                        logging.error(f"Failed to update task status for {filename} after LLM failure.")
                    # Task remains in assigned_dir for retry or eventual move to failed_dir by this loop

            except json.JSONDecodeError:
                logging.error(f"Invalid JSON in task file {filename}. Moving to '5_failed'.")
                self._move_file(filepath, self.failed_dir)
            except Exception as e:
                logging.error(f"Error processing assigned task {filename}: {e}\n{traceback.format_exc()}")
                # Increment retry count and update timestamp even for monitor's internal errors
                retries_attempted = task_data.get("retries_attempted", 0) + 1
                if retries_attempted >= self.max_llm_retries:
                    logging.error(f"Task {filename} reached max retries due to monitor error. Moving to '5_failed'.")
                    if self._update_task_status(filepath, "failed", retries_attempted, datetime.now()):
                        self._move_file(filepath, self.failed_dir)
                else:
                    logging.warning(f"Task {filename} encountered monitor error. Retrying (attempt {retries_attempted}).")
                    if not self._update_task_status(filepath, "assigned", retries_attempted, datetime.now()):
                        logging.error(f"Failed to update task status for {filename} after monitor error.")


    def handle_pending_tasks(self):
        # Check if there are any pending tasks that are not already being processed
        pending_files = [f for f in os.listdir(self.pending_dir) if f.endswith('.json')]
        if not pending_files:
            return # No pending tasks

        logging.info("Pending tasks found. Attempting to acquire lock and triggering Project Manager.")

        # --- CREATE THE LOCK FILE FIRST ---
        with open(self.pm_assigning_lock, 'w') as f:
            f.write(f"Locked at {time.time()}")

        prompt = (
            "There are tasks in the 'tasks/0_pending/' directory. "
            "Your job is to assign the next available task by moving its file to 'tasks/1_assigned/'. "
            "You should also update the 'status' field in the task JSON to 'assigned' and set 'retries_attempted' to 0. "
            "After you have successfully moved the file, you MUST perform one final, critical action: "
            "use the `jailed_delete_file` tool to delete the lock file located at 'tasks/pm_assigning.lock'. "
            "This signals that you are done and the system can continue."
        )

        # Trigger PM. If PM fails to delete lock, the _is_lock_stale check will eventually clean it.
        result = self.trigger_persona_and_run("Project Manager", prompt)

        # If the PM failed, it might not have deleted the lock file.
        # The _is_lock_stale check will handle this eventually.
        if result['status'] != "success":
            logging.error(f"Project Manager failed to assign tasks. Lock file {self.pm_assigning_lock} might persist.")
        # else: The PM should have deleted the lock file.

    def trigger_persona_and_run(self, persona_name, prompt, task_filepath=None, is_deliverable=False):
        """
        Triggers an LLM persona to execute a task.
        Returns a dict with 'status' (success/failure) and 'content' (LLM's final output).
        """
        instance = None
        result = {"status": "failure", "content": ""}
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
            llm_response = instance.execute_headless_turn(prompt)

            result['status'] = llm_response.get('status', 'failure')
            result['content'] = llm_response.get('content', '')

            logging.info(f"Persona '{persona_name}' finished. Status: {result['status']}. Output: {result['content']}")

        except Exception as e:
            logging.error(f"An error occurred while running persona '{persona_name}': {e}\n{traceback.format_exc()}")
            result['status'] = "failure"
            result['content'] = f"Error: {e}"
        finally:
            # 5. VERY IMPORTANT: Clean up the temporary instance
            if instance:
                chat_manager.remove_instance(instance.instance_id)
                logging.info(f"Cleaned up temporary instance {instance.instance_id} for '{persona_name}'.")
            logging.info(f"--- Persona Trigger Finished: '{persona_name}' ---")
            return result


if __name__ == "__main__":
    # Example usage:
    # Run in 'auto' mode:
    # monitor = EventMonitor(mode="auto", provider_name="Google", model_name="gemini-2.5-flash", polling_interval=15)

    # Run in 'stepped' mode for human review:
    monitor = EventMonitor(mode="stepped", provider_name="Google", model_name="gemini-2.5-flash", polling_interval=15)

    monitor.run()
