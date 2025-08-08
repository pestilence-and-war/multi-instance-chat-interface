# my_tools/jailed_file_manager.py (Corrected)

import subprocess
import json
import os
from my_tools.path_security import _get_project_root
from my_tools.code_editor import _sync_db_after_file_creation, _sync_db_after_file_delete, _sync_db_after_file_move
from my_tools.codebase_manager import _CodebaseManager

def _execute_command(command_str: str) -> str:
    """(Internal Engine) Calls the SafeExecutor.ps1 script."""
    project_root = _get_project_root()
    if not project_root:
        return json.dumps({'status': 'error', 'message': 'CODEBASE_DB_PATH environment variable not set or invalid.'}, indent=2)

    try:
        executor_script_path = os.path.join(os.path.dirname(__file__), "SafeExecutor.ps1")
        
        final_command = [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", executor_script_path,
            "-WorkspacePath", project_root,
            "-CommandToRun", command_str
        ]

        process = subprocess.run(
            final_command, capture_output=True, text=True, encoding='utf-8', timeout=30
        )
        return json.dumps({
            'status': 'success' if not process.stderr.strip() else 'error',
            'stdout': process.stdout.strip(),
            'stderr': process.stderr.strip()
        }, indent=2)

    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'An unexpected error occurred: {e}'}, indent=2)

# --- Public Tool Functions ---

def jailed_create_directory(path: str) -> str:
    """(Low-Cost) Safely creates a new directory within the sandboxed project workspace.
    This tool executes a PowerShell command (`New-Item`) within a secure, isolated
    environment to prevent access outside the defined project directory.

    @param path (string): The project-relative path for the new directory to be created. REQUIRED.

    Returns:
        string: A JSON string containing the status of the operation ('success' or 'error'), along with any output from stdout and stderr.
    """
    command = f"New-Item -ItemType Directory -Path '{path}'"
    result_str = _execute_command(command)
    result = json.loads(result_str)

    if result.get("status") == "success":
        manager = _CodebaseManager()
        cursor = manager._execute_write_query("INSERT OR IGNORE INTO directories (path) VALUES (?)", (path + '/',))
        if cursor:
             result['database_sync_status'] = {'status': 'success', 'message': f'Directory {path}/ registered in database.'}
        else:
             result['database_sync_status'] = {'status': 'error', 'message': 'Failed to register directory in database.'}
        return json.dumps(result, indent=2)
    return result_str

def jailed_delete_directory(path: str) -> str:
    """
    (High-Risk) Safely deletes a directory and all its contents, and updates the database.
    This tool executes a PowerShell command (`Remove-Item`) within a secure, isolated
    environment to prevent access outside the defined project directory.

    @param path (string): The project-relative path of the directory to delete. REQUIRED.

    Returns:
        string: A JSON string containing the status of the operation ('success' or 'error'), along with any output from stdout and stderr.
    """
    command = f"Remove-Item -Path '{path}' -Recurse -Force"
    result_str = _execute_command(command)
    result = json.loads(result_str)

    if result.get("status") == "success":
        manager = _CodebaseManager()
        dir_cursor = manager._execute_write_query("DELETE FROM directories WHERE path = ?", (path + '/',))
        files_cursor = manager._execute_write_query("DELETE FROM files WHERE path LIKE ?", (path + '/%',))
        
        if dir_cursor and files_cursor:
             result['database_sync_status'] = {'status': 'success', 'message': f'Directory {path}/ and its contents removed from database.'}
        else:
             result['database_sync_status'] = {'status': 'error', 'message': 'Failed to update database after directory deletion.'}
        return json.dumps(result, indent=2)
            
    return result_str

def jailed_create_file(path: str, content: str = "") -> str:
    """(Medium-Cost) Safely creates or overwrites a file with content and syncs the database.
    Executes a sandboxed PowerShell command (`Set-Content`) to write to a file.
    If the file operation is successful, it automatically updates the project database
    to reflect the new or updated file.

    @param path (string): The project-relative path of the file to create or overwrite. REQUIRED.
    @param content (string): The content to write into the file. Optional. Defaults to an empty string.

    Returns:
        string: A JSON string containing the command execution status, stdout/stderr, and a 'database_sync_status' object.
    """
    escaped_content = content.replace("'", "''")
    command = f"Set-Content -Path '{path}' -Value '{escaped_content}'"
    result_str = _execute_command(command)
    result = json.loads(result_str)

    if result.get("status") == "success":
        db_sync_result = json.loads(_sync_db_after_file_creation(path))
        result['database_sync_status'] = db_sync_result
        return json.dumps(result, indent=2)
            
    return result_str

def jailed_delete_file(path: str) -> str:
    """(Low-Cost) Safely deletes a file and removes its record from the database.
    Executes a sandboxed PowerShell command (`Remove-Item`) to delete the specified file.
    On successful file deletion, it removes the corresponding entry from the project database.

    @param path (string): The project-relative path of the file to delete. REQUIRED.

    Returns:
        string: A JSON string containing the command execution status, stdout/stderr, and a 'database_sync_status' object.
    """
    
    command = f"Remove-Item -Path '{path}' -Force"
    result_str = _execute_command(command)
    result = json.loads(result_str)

    if result.get("status") == "success":
        db_sync_result = json.loads(_sync_db_after_file_delete(path))
        result['database_sync_status'] = db_sync_result
        return json.dumps(result, indent=2)

    return result_str

def jailed_move_file(source_path: str, destination_path: str) -> str:
    """(Low-Cost) Safely moves or renames a file and updates the database.
    Executes a sandboxed PowerShell command (`Move-Item`) to move a file from a source path
    to a destination path. On success, it updates the file's record in the project database
    to reflect the new path.

    @param source_path (string): The current project-relative path of the file to move. REQUIRED.
    @param destination_path (string): The new project-relative path for the file. REQUIRED.

    Returns:
        string: A JSON string containing the command execution status, stdout/stderr, and a 'database_sync_status' object.
    """
    command = f"Move-Item -Path '{source_path}' -Destination '{destination_path}' -Force"
    result_str = _execute_command(command)
    result = json.loads(result_str)

    if result.get("status") == "success":
        db_sync_result = json.loads(_sync_db_after_file_move(source_path, destination_path))
        result['database_sync_status'] = db_sync_result
        return json.dumps(result, indent=2)

    return result_str