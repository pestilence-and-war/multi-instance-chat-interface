# my_tools/jailed_file_manager.py (Python-Native & Cross-Platform)

import json
import os
import shutil
from my_tools.path_security import _get_project_root, _is_path_safe
from my_tools.code_editor import _sync_db_after_file_creation, _sync_db_after_file_delete, _sync_db_after_file_move
from my_tools.codebase_manager import _CodebaseManager

# --- Helper: Safe Path Resolution ---

def _resolve_and_validate_path(relative_path: str) -> str | None:
    """
    Resolves a relative path against the project root and verifies safety.
    Returns the absolute path if safe, or None if unsafe/invalid.
    """
    project_root = _get_project_root()
    if not project_root:
        return None
    
    full_path = os.path.abspath(os.path.join(project_root, relative_path))
    
    if _is_path_safe(full_path):
        return full_path
    return None

# --- Public Tool Functions ---

def jailed_create_directory(path: str) -> str:
    """(Low-Cost) Safely creates a new directory within the sandboxed project workspace.
    Uses Python's native os module to ensure cross-platform compatibility.

    @param path (string): The project-relative path for the new directory. REQUIRED.
    """
    full_path = _resolve_and_validate_path(path)
    if not full_path:
        return json.dumps({'status': 'error', 'message': f'Security Error: Path "{path}" is outside the workspace.'}, indent=2)

    try:
        os.makedirs(full_path, exist_ok=True)
        
        # Sync DB
        manager = _CodebaseManager()
        # Ensure path ends with slash for consistency with DB convention
        db_path_str = path.replace('\\', '/').strip('/') + '/' 
        cursor = manager._execute_write_query("INSERT OR IGNORE INTO directories (path) VALUES (?)", (db_path_str,))
        
        db_msg = 'Directory registered in database.' if cursor else 'Failed to register directory in database.'
        
        return json.dumps({
            'status': 'success', 
            'message': f'Directory created: {path}',
            'database_sync_status': {'status': 'success' if cursor else 'error', 'message': db_msg}
        }, indent=2)

    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'Error creating directory: {e}'}, indent=2)

def jailed_delete_directory(path: str) -> str:
    """
    (High-Risk) Safely deletes a directory and all its contents.
    
    @param path (string): The project-relative path of the directory to delete. REQUIRED.
    """
    full_path = _resolve_and_validate_path(path)
    if not full_path:
        return json.dumps({'status': 'error', 'message': f'Security Error: Path "{path}" is outside the workspace.'}, indent=2)

    if not os.path.exists(full_path):
        return json.dumps({'status': 'error', 'message': f'Directory not found: {path}'}, indent=2)
    if not os.path.isdir(full_path):
        return json.dumps({'status': 'error', 'message': f'Path is not a directory: {path}'}, indent=2)

    try:
        shutil.rmtree(full_path)

        # Sync DB
        manager = _CodebaseManager()
        db_path_str = path.replace('\\', '/').strip('/') + '/'
        
        dir_cursor = manager._execute_write_query("DELETE FROM directories WHERE path = ?", (db_path_str,))
        files_cursor = manager._execute_write_query("DELETE FROM files WHERE path LIKE ?", (db_path_str + '%',))
        
        db_status = 'success' if (dir_cursor and files_cursor) else 'error'
        db_msg = 'Database updated.' if db_status == 'success' else 'Database update failed.'

        return json.dumps({
            'status': 'success', 
            'message': f'Directory deleted: {path}',
            'database_sync_status': {'status': db_status, 'message': db_msg}
        }, indent=2)

    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'Error deleting directory: {e}'}, indent=2)

def jailed_create_file(path: str, content: str = "") -> str:
    """(Medium-Cost) Safely creates or overwrites a file with content.
    
    @param path (string): The project-relative path of the file. REQUIRED.
    @param content (string): The content to write. Optional.
    """
    full_path = _resolve_and_validate_path(path)
    if not full_path:
        return json.dumps({'status': 'error', 'message': f'Security Error: Path "{path}" is outside the workspace.'}, indent=2)

    try:
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Sync DB
        db_sync_result = json.loads(_sync_db_after_file_creation(path))
        
        return json.dumps({
            'status': 'success',
            'message': f'File written: {path}',
            'database_sync_status': db_sync_result
        }, indent=2)

    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'Error writing file: {e}'}, indent=2)

def jailed_delete_file(path: str) -> str:
    """(Low-Cost) Safely deletes a file.
    
    @param path (string): The project-relative path of the file. REQUIRED.
    """
    full_path = _resolve_and_validate_path(path)
    if not full_path:
        return json.dumps({'status': 'error', 'message': f'Security Error: Path "{path}" is outside the workspace.'}, indent=2)

    if not os.path.exists(full_path):
        return json.dumps({'status': 'error', 'message': f'File not found: {path}'}, indent=2)
    if not os.path.isfile(full_path):
        return json.dumps({'status': 'error', 'message': f'Path is not a file: {path}'}, indent=2)

    try:
        os.remove(full_path)

        # Sync DB
        db_sync_result = json.loads(_sync_db_after_file_delete(path))
        
        return json.dumps({
            'status': 'success',
            'message': f'File deleted: {path}',
            'database_sync_status': db_sync_result
        }, indent=2)

    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'Error deleting file: {e}'}, indent=2)

def jailed_move_file(source_path: str, destination_path: str) -> str:
    """(Low-Cost) Safely moves or renames a file.
    
    @param source_path (string): Current project-relative path. REQUIRED.
    @param destination_path (string): New project-relative path. REQUIRED.
    """
    full_src = _resolve_and_validate_path(source_path)
    full_dest = _resolve_and_validate_path(destination_path)

    if not full_src:
        return json.dumps({'status': 'error', 'message': f'Security Error: Source path "{source_path}" is outside workspace.'}, indent=2)
    if not full_dest:
        return json.dumps({'status': 'error', 'message': f'Security Error: Destination path "{destination_path}" is outside workspace.'}, indent=2)

    if not os.path.exists(full_src):
        return json.dumps({'status': 'error', 'message': f'Source file not found: {source_path}'}, indent=2)

    try:
        # Ensure dest directory exists
        os.makedirs(os.path.dirname(full_dest), exist_ok=True)
        
        shutil.move(full_src, full_dest)

        # Sync DB
        db_sync_result = json.loads(_sync_db_after_file_move(source_path, destination_path))
        
        return json.dumps({
            'status': 'success',
            'message': f'Moved {source_path} to {destination_path}',
            'database_sync_status': db_sync_result
        }, indent=2)

    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'Error moving file: {e}'}, indent=2)

def setup_digital_office_structure() -> str:
    """
    (Low-Cost) Creates the standard "Digital Office" directory structure for AATFS.
    This tool is idempotent; it will not fail if the directories already exist.
    It creates the following structure:
    - personas/
    - tasks/ (with subdirectories 0_pending through 5_failed)
    - archive/deliverables/
    All created directories are automatically registered in the project database.

    Returns:
        string: A JSON string summarizing the results of each directory creation operation.
    """
    directories_to_create = [
        "personas",
        "tasks",
        "archive",
        "tasks/0_pending",
        "tasks/1_assigned",
        "tasks/2_in_progress",
        "tasks/3_review",
        "tasks/4_done",
        "tasks/5_failed",
        "archive/deliverables"
    ]

    results = []
    overall_status = "success"

    for directory in directories_to_create:
        result_str = jailed_create_directory(directory)
        try:
            result = json.loads(result_str)
            # Python's os.makedirs(exist_ok=True) won't throw an error for existing dirs,
            # so we check our own return message or just assume success.
            # Our new jailed_create_directory returns success even if it exists (idempotent logic implied by exist_ok=True).
            
            results.append({
                "directory": directory,
                "status": result.get("status"),
                "details": result
            })

        except json.JSONDecodeError:
            results.append({"directory": directory, "status": "error", "message": "Failed to decode JSON response."})
            overall_status = "partial_failure"

    final_report = {
        "tool": "setup_digital_office_structure",
        "overall_status": overall_status,
        "operations": results
    }

    return json.dumps(final_report, indent=2)
