# my_tools/jailed_file_manager.py

import json
from my_tools.jailed_shell_tool import execute_jailed_command # We use the low-level tool as a foundation
from my_tools.code_editor import refresh_file_representation, delete_file_representation # Import the DB sync functions

def jailed_create_file(path: str, content: str = "") -> str:
    """
    (High-Risk) Safely creates a new, empty file or a file with content in the sandboxed environment.
    This operation is immediately synchronized with the project database.

    Args:
        path (str): The path for the new file (e.g., "new_module/my_file.py").
        content (str, optional): The content to write into the new file. Defaults to "".

    Returns:
        A JSON string detailing the result of the file system and database operations.
    """
    # PowerShell's Set-Content creates a file if it doesn't exist.
    # We escape single quotes in the content for PowerShell.
    escaped_content = content.replace("'", "''")
    command = f"Set-Content -Path '{path}' -Value '{escaped_content}'"

    # Execute the command in the sandbox
    result_str = execute_jailed_command(command)
    result = json.loads(result_str)

    # If the file system operation was successful, sync the database
    if result.get("status") == "success":
        # The 'working_directory' is the project root, so we form the full path
        full_path = f"{result['working_directory']}\\{path}"
        db_sync_result_str = refresh_file_representation(full_path)
        db_sync_result = json.loads(db_sync_result_str)

        result['database_sync_status'] = db_sync_result
        return json.dumps(result, indent=2)

    return result_str

def jailed_delete_file(path: str) -> str:
    """
    (High-Risk) Safely deletes a file in the sandboxed environment.
    This operation is immediately synchronized with the project database.

    Args:
        path (str): The path of the file to delete.

    Returns:
        A JSON string detailing the result of the file system and database operations.
    """
    command = f"Remove-Item -Path '{path}' -Force"
    result_str = execute_jailed_command(command)
    result = json.loads(result_str)

    if result.get("status") == "success":
        full_path = f"{result['working_directory']}\\{path}"
        db_sync_result_str = delete_file_representation(full_path)
        db_sync_result = json.loads(db_sync_result_str)

        result['database_sync_status'] = db_sync_result
        return json.dumps(result, indent=2)

    return result_str

def jailed_move_file(source_path: str, destination_path: str) -> str:
    """
    (High-Risk) Safely moves or renames a file in the sandboxed environment.
    This operation is immediately synchronized with the project database.

    Args:
        source_path (str): The original path of the file.
        destination_path (str): The new path for the file.

    Returns:
        A JSON string detailing the result of the file system and database operations.
    """
    command = f"Move-Item -Path '{source_path}' -Destination '{destination_path}' -Force"
    result_str = execute_jailed_command(command)
    result = json.loads(result_str)

    if result.get("status") == "success":
        # Delete the old representation and refresh the new one
        project_root = result['working_directory']
        full_source_path = f"{project_root}\\{source_path}"
        full_dest_path = f"{project_root}\\{destination_path}"

        delete_status = json.loads(delete_file_representation(full_source_path))
        refresh_status = json.loads(refresh_file_representation(full_dest_path))

        result['database_sync_status'] = {
            'delete_old_record': delete_status,
            'refresh_new_record': refresh_status
        }
        return json.dumps(result, indent=2)

    return result_str

def jailed_create_directory(path: str) -> str:
    """
    (High-Risk) Safely creates a new directory in the sandboxed environment.
    This operation does not require database synchronization.

    Args:
        path (str): The path of the directory to create.

    Returns:
        The direct JSON output from the sandboxed shell command.
    """
    command = f"New-Item -ItemType Directory -Path '{path}'"
    return execute_jailed_command(command)
