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
    
    @param path (string): The project-relative path of the file (e.g., 'folder/file.txt'). REQUIRED.
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

def jailed_append_file(path: str, content: str = "") -> str:
    """(Medium-Cost) Safely appends content to a file. Creates the file if it doesn't exist.
    
    @param path (string): The project-relative path of the file (e.g., 'folder/file.txt'). REQUIRED.
    @param content (string): The content to append. REQUIRED.
    """
    full_path = _resolve_and_validate_path(path)
    if not full_path:
        return json.dumps({'status': 'error', 'message': f'Security Error: Path "{path}" is outside the workspace.'}, indent=2)

    try:
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'a', encoding='utf-8') as f:
            f.write(content)

        # Sync DB (treating as creation if it's new, or just sync existing)
        # For simplicity, we use creation sync which usually updates or adds.
        db_sync_result = json.loads(_sync_db_after_file_creation(path))
        
        return json.dumps({
            'status': 'success',
            'message': f'Content appended to: {path}',
            'database_sync_status': db_sync_result
        }, indent=2)

    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'Error appending to file: {e}'}, indent=2)

def jailed_delete_file(path: str) -> str:
    """(Low-Cost) Safely deletes a file.
    
    @param path (string): The project-relative path of the file (e.g., 'folder/file.txt'). REQUIRED.
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

def jailed_file_exists(path: str) -> str:
    """(Low-Cost) Checks if a file or directory exists within the sandboxed project workspace.
    
    @param path (string): The project-relative path to check. REQUIRED.
    """
    full_path = _resolve_and_validate_path(path)
    if not full_path:
        return json.dumps({'status': 'error', 'message': f'Security Error: Path "{path}" is outside the workspace.'}, indent=2)

    exists = os.path.exists(full_path)
    is_file = os.path.isfile(full_path)
    is_dir = os.path.isdir(full_path)

    return json.dumps({
        'status': 'success',
        'exists': exists,
        'is_file': is_file,
        'is_dir': is_dir,
        'path': path
    }, indent=2)

def jailed_read_file(path: str) -> str:
    """(Medium-Cost) Safely reads the content of a file within the sandboxed project workspace.
    Use this for reading files that might not be in the codebase database yet (e.g., newly created drafts or test scripts).

    @param path (string): The project-relative path of the file to read. REQUIRED.
    """
    full_path = _resolve_and_validate_path(path)
    if not full_path:
        return json.dumps({'status': 'error', 'message': f'Security Error: Path "{path}" is outside the workspace.'}, indent=2)

    if not os.path.exists(full_path):
        return json.dumps({'status': 'error', 'message': f'File not found: {path}'}, indent=2)
    
    if not os.path.isfile(full_path):
        return json.dumps({'status': 'error', 'message': f'Path is not a file: {path}'}, indent=2)

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return json.dumps({
            'status': 'success',
            'path': path,
            'content': content
        }, indent=2)
    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'Error reading file: {e}'}, indent=2)

def jailed_word_count(path: str) -> str:
    """(Low-Cost) Returns an objective word count for a file in the workspace.
    Use this to audit length requirements without relying on the LLM's internal (and often hallucinated) count.

    @param path (string): The project-relative path of the file (e.g., 'folder/file.txt'). REQUIRED.
    """
    full_path = _resolve_and_validate_path(path)
    if not full_path:
        return json.dumps({'status': 'error', 'message': f'Security Error: Path "{path}" is outside the workspace.'}, indent=2)

    if not os.path.exists(full_path):
        return json.dumps({'status': 'error', 'message': f'File not found: {path}'}, indent=2)

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            text = f.read()
            words = text.split()
            count = len(words)
        return json.dumps({
            'status': 'success',
            'word_count': count,
            'path': path
        }, indent=2)
    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'Error counting words: {e}'}, indent=2)

def jailed_tail_file(path: str, lines: int = 10) -> str:
    """(Low-Cost) Reads the last few lines of a file. Use this for verifying draft progress without reading the entire file.
    
    @param path (string): The project-relative path of the file (e.g., 'folder/file.txt'). REQUIRED.
    @param lines (integer): Number of lines to read from the end. Defaults to 10.
    """
    full_path = _resolve_and_validate_path(path)
    if not full_path:
        return json.dumps({'status': 'error', 'message': f'Security Error: Path "{path}" is outside the workspace.'}, indent=2)

    if not os.path.exists(full_path):
        return json.dumps({'status': 'error', 'message': f'File not found: {path}'}, indent=2)

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            tail = all_lines[-lines:] if lines > 0 else []
        return json.dumps({
            'status': 'success',
            'path': path,
            'lines_read': len(tail),
            'content': "".join(tail)
        }, indent=2)
    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'Error tailing file: {e}'}, indent=2)

def harvest_to_file(source_tool: str, query_or_url: str, target_path: str, milestone_name: str = "Unknown") -> str:
    """(High-Cost) Directly pipes raw tool output from a search or read tool into a research artifact file.
    This prevents the model from having to transcribe large amounts of text, saving context and preventing truncation.

    @param source_tool (string): The name of the tool to harvest from ('tavily_search' or 'grokipedia_read'). REQUIRED.
    @param query_or_url (string): The search query or the article URL/slug to fetch. REQUIRED.
    @param target_path (string): The project-relative path (e.g., 'research/milestone_1950.json') to save the artifact. REQUIRED.
    @param milestone_name (string): A friendly name for the milestone being researched. Optional.
    """
    from my_tools.tavily_search_tool import tavily_search
    from my_tools.grokipedia_tool import grokipedia_read

    full_path = _resolve_and_validate_path(target_path)
    if not full_path:
        return json.dumps({'status': 'error', 'message': 'Security Error: Path is outside workspace.'}, indent=2)

    raw_content = ""
    source_info = query_or_url

    try:
        if source_tool == 'tavily_search':
            result_json = tavily_search(query=query_or_url, search_depth="advanced", max_results=1)
            data = json.loads(result_json)
            if data.get('status') == 'success' and data.get('results'):
                first_res = data['results'][0]
                raw_content = first_res.get('content', '')
                source_info = first_res.get('url', query_or_url)
            else:
                return json.dumps({'status': 'error', 'message': f'Tavily search failed or returned no results: {result_json}'}, indent=2)
        
        elif source_tool == 'grokipedia_read':
            raw_content = grokipedia_read(url_or_slug=query_or_url)
            if raw_content.startswith('TITLE: '):
                # Success
                pass
            else:
                return json.dumps({'status': 'error', 'message': f'Grokipedia read failed: {raw_content}'}, indent=2)
        
        else:
            return json.dumps({'status': 'error', 'message': f'Unsupported source tool: {source_tool}'}, indent=2)

        if not raw_content:
            return json.dumps({'status': 'error', 'message': 'Harvested content is empty.'}, indent=2)

        # Structure the artifact
        artifact = {
            "milestone": milestone_name,
            "source_tool": source_tool,
            "source_url": source_info,
            "raw_blurb": raw_content
        }

        # Save to file
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(artifact, f, indent=2)

        # Sync DB
        db_sync_result = json.loads(_sync_db_after_file_creation(target_path))

        return json.dumps({
            'status': 'success',
            'message': f'Successfully harvested {source_tool} output to {target_path}',
            'word_count_estimate': len(raw_content.split()),
            'database_sync_status': db_sync_result
        }, indent=2)

    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'Harvesting error: {e}'}, indent=2)

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
