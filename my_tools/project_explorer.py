# my_tools/project_explorer.py

import json
import os
from typing import Optional

from my_tools.codebase_manager import _CodebaseManager

# --- Public Tool Functions ---

def get_directory_tree() -> str:
    """
    (Low-Cost) Lists all files and directories in the project in a tree-like format.
    This is useful for getting a quick, high-level overview of the entire project structure.
    """
    manager = _CodebaseManager()
    query = """
        SELECT path FROM files
        UNION
        SELECT path FROM directories
        ORDER BY path ASC;
    """
    cursor = manager._execute_read_query(query)

    if cursor:
        tree = [row['path'] for row in cursor.fetchall()]
        result_dict = {"directory_tree": tree, "status": "success"}
    else:
        result_dict = {"error": "Could not query directory tree from database.", "status": "error_db_query"}

    return json.dumps(result_dict, indent=2)

def list_files(directory_path: Optional[str] = None) -> str:
    """
    (Low-Cost) Lists all files, optionally filtering by a specific subdirectory.
    @param directory_path (string): The directory to filter by (e.g., "src/api/"). If omitted, all files in the project are listed.
    """
    manager = _CodebaseManager()

    # Base query for all files
    query = "SELECT path FROM files"
    query_params = []

    # Filtering logic if a directory_path is provided
    if directory_path:
        # Normalize path for consistent matching (e.g., remove leading ./, ensure trailing /)
        norm_dir_path = directory_path.replace("\\", "/").strip("./")
        if norm_dir_path and not norm_dir_path.endswith('/'):
            norm_dir_path += '/'

        # Add a WHERE clause to filter by the normalized path prefix
        if norm_dir_path:
            query += " WHERE path LIKE ?"
            query_params.append(f"{norm_dir_path}%")

    query += " ORDER BY path ASC"
    cursor = manager._execute_read_query(query, tuple(query_params))

    if cursor:
        files = [row['path'] for row in cursor.fetchall()]
        result_dict = {"directory_path": directory_path, "files": files, "status": "success"}
    else:
        result_dict = {"error": "Could not query file list from database.", "status": "error_db_query"}

    return json.dumps(result_dict, indent=2)

def get_project_summary() -> str:
    """
    (Low-Cost) Provides a high-level summary of the project, including file counts by type and total lines of code.
    """
    manager = _CodebaseManager()
    query = """
        SELECT
            COUNT(*) as total_files,
            SUM(CASE WHEN end_lineno IS NOT NULL THEN end_lineno ELSE 0 END) as total_lines,
            SUM(CASE WHEN type = 'python' THEN 1 ELSE 0 END) as python_files,
            SUM(CASE WHEN type = 'html' THEN 1 ELSE 0 END) as html_files,
            SUM(CASE WHEN type = 'css' THEN 1 ELSE 0 END) as css_files,
            SUM(CASE WHEN type = 'javascript' THEN 1 ELSE 0 END) as javascript_files,
            SUM(CASE WHEN type = 'json' THEN 1 ELSE 0 END) as json_files,
            SUM(CASE WHEN type = 'text' THEN 1 ELSE 0 END) as text_files,
            SUM(CASE WHEN type IS NULL THEN 1 ELSE 0 END) as other_files
        FROM files;
    """
    cursor = manager._execute_read_query(query)

    if not cursor:
        return json.dumps({"error": "Failed to query project summary.", "status": "error_db_query"}, indent=2)

    row = cursor.fetchone()
    # Ensure row is not None (e.g., for an empty table) before converting to dict
    if row:
        summary_data = dict(row)
        result_dict = {"summary": summary_data, "status": "success"}
    else:
        # This case handles an empty but valid database table.
        result_dict = {"summary": {}, "status": "success", "message": "Project database is empty."}

    return json.dumps(result_dict, indent=2)

def get_current_project_root() -> str:
    """
    (Low-Cost) Returns the absolute path of the current project's root directory.
    This path is determined by the CODEBASE_DB_PATH environment variable.
    """
    # This function does not use the database and is unchanged.
    from my_tools.path_security import _get_project_root
    import json
    try:
        root_path = _get_project_root()
        return json.dumps({"status": "success", "project_root": root_path})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to get project root: {e}"})

if __name__ == '__main__':
    print("--- Testing ProjectExplorer Tool ---")
    # The environment variable is the single source of truth for the DB path.
    # The codebase_manager will find it. We just check for its existence here for a user-friendly message.
    workspace_dir = os.environ.get("CODEBASE_DB_PATH", ".")
    db_path = os.path.join(workspace_dir, "project_context.db")

    if not os.path.exists(db_path):
        print(f"\nERROR: Database file '{os.path.abspath(db_path)}' not found.")
        print("Please ensure the CODEBASE_DB_PATH environment variable is set correctly or run the database creation script in the current directory.")
    else:
        print(f"Using database found at: '{os.path.abspath(db_path)}'")

        print("\n--- Test Call 1: get_project_summary() ---")
        print(get_project_summary())

        print("\n--- Test Call 2: get_directory_tree() ---")
        # Keep the output brief for testing
        tree_result = json.loads(get_directory_tree())
        if tree_result.get("status") == "success" and "directory_tree" in tree_result:
            if len(tree_result["directory_tree"]) > 15:
                tree_result["directory_tree"] = tree_result["directory_tree"][:15] + ["... (truncated for display)"]
        print(json.dumps(tree_result, indent=2))

        print("\n--- Test Call 3: list_files() ---")
        # List all files, but truncate for display
        list_all_result = json.loads(list_files())
        if list_all_result.get("status") == "success" and "files" in list_all_result:
            if len(list_all_result["files"]) > 15:
                list_all_result["files"] = list_all_result["files"][:15] + ["... (truncated for display)"]
        print(json.dumps(list_all_result, indent=2))

        print("\n--- Test Call 4: list_files(directory_path='my_tools') ---")
        print(list_files(directory_path="my_tools"))

        print("\n--- Test Call 5: list_files(directory_path='non_existent_dir/') ---")
        print(list_files(directory_path="non_existent_dir/"))
