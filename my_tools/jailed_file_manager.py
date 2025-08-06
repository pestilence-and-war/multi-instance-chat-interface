# my_tools/jailed_file_manager.py

import subprocess
import json
import os
from my_tools.path_security import get_project_root
from my_tools.code_editor import refresh_file_representation, delete_file_representation

def _execute_command(command_str: str) -> str:
    """
    (Internal Engine) This function calls the SafeExecutor.ps1 script to run a command.
    It assumes the Python process is already running as JeaToolUser.
    This function is NOT a tool for the LLM.
    """
    try:
        # Construct the full, portable path to our security script
        executor_script_path = os.path.join(os.path.dirname(__file__), "SafeExecutor.ps1")
        
        # The command is much simpler now. We just pass the command string
        # as an argument to our trusted executor script.
        final_command = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass", # Ensures the script can run
            "-File", executor_script_path,
            "-CommandToRun", command_str
        ]

        process = subprocess.run(
            final_command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=30
        )

        return json.dumps({
            'status': 'success' if not process.stderr.strip() else 'error',
            'stdout': process.stdout.strip(),
            'stderr': process.stderr.strip()
        }, indent=2)

    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'An unexpected error occurred in the tool executor: {e}'}, indent=2)

# --- Public Tool Functions ---

def jailed_create_directory(path: str) -> str:
    """
    (High-Risk) Safely creates a new directory in the sandboxed project workspace.
    This operation does not require database synchronization.
    """
    command = f"New-Item -ItemType Directory -Path '{path}'"
    return _execute_command(command)

def jailed_create_file(path: str, content: str = "") -> str:
    """
    (High-Risk) Safely creates a new file, or overwrites an existing file, with provided content.
    This operation is immediately synchronized with the project database.
    """
    # PowerShell requires single quotes inside the -Value string to be escaped by doubling them
    escaped_content = content.replace("'", "''")
    command = f"Set-Content -Path '{path}' -Value '{escaped_content}'"
    
    result_str = _execute_command(command)
    result = json.loads(result_str)

    # If the file system operation was successful, sync the database
    if result.get("status") == "success":
        project_root = get_project_root()
        if project_root:
            # Construct the full OS path to the file for the DB sync function
            full_path = os.path.join(project_root, path.replace('/', '\\'))
            db_sync_result = json.loads(refresh_file_representation(full_path))
            result['database_sync_status'] = db_sync_result
            return json.dumps(result, indent=2)
            
    return result_str

def jailed_delete_file(path: str) -> str:
    """
    (High-Risk) Safely deletes a file from the sandboxed project workspace.
    This operation is immediately synchronized with the project database.
    """
    command = f"Remove-Item -Path '{path}' -Force"
    result_str = _execute_command(command)
    result = json.loads(result_str)

    # If the file system operation was successful, remove it from the database
    if result.get("status") == "success":
        project_root = get_project_root()
        if project_root:
            full_path = os.path.join(project_root, path.replace('/', '\\'))
            db_sync_result = json.loads(delete_file_representation(full_path))
            result['database_sync_status'] = db_sync_result
            return json.dumps(result, indent=2)

    return result_str

def jailed_move_file(source_path: str, destination_path: str) -> str:
    """
    (High-Risk) Safely moves or renames a file in the sandboxed project workspace.
    This operation is immediately synchronized with the project database.
    """
    command = f"Move-Item -Path '{source_path}' -Destination '{destination_path}' -Force"
    result_str = _execute_command(command)
    result = json.loads(result_str)

    # If the move was successful, update the database by deleting the old record and refreshing the new one
    if result.get("status") == "success":
        project_root = get_project_root()
        if project_root:
            full_source_path = os.path.join(project_root, source_path.replace('/', '\\'))
            full_dest_path = os.path.join(project_root, destination_path.replace('/', '\\'))
            
            delete_status = json.loads(delete_file_representation(full_source_path))
            refresh_status = json.loads(refresh_file_representation(full_dest_path))

            result['database_sync_status'] = {
                'delete_old_record': delete_status,
                'refresh_new_record': refresh_status
            }
            return json.dumps(result, indent=2)

    return result_str