# my_tools/project_explorer.py

import json
import os
import sqlite3
from typing import Dict, Any, Optional, List

# --- Internal Class for Data Management (Singleton) ---
class _CodebaseManager:
    _instance = None
    _db_file_path = "project_context.db"

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(_CodebaseManager, cls).__new__(cls)
            cls._instance.conn = None
            cls._instance._connect_to_db()
        return cls._instance

    def _connect_to_db(self):
        db_path = os.environ.get("CODEBASE_DB_PATH", self.__class__._db_file_path)
        if not os.path.exists(db_path):
            self.conn = None
            return
        try:
            db_uri = f"file:{os.path.abspath(db_path)}?mode=ro"
            self.conn = sqlite3.connect(db_uri, uri=True, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            print(f"Error connecting to DB in read-only mode: {e}. Falling back to read/write.")
            try:
                self.conn = sqlite3.connect(db_path, check_same_thread=False)
                self.conn.row_factory = sqlite3.Row
            except sqlite3.Error as e_fallback:
                print(f"Fatal error connecting to database '{db_path}': {e_fallback}")
                self.conn = None

    def _execute_query(self, query: str, params: tuple = ()):
        if not self.conn:
            return None
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor
        except sqlite3.Error as e:
            print(f"Database query error: {e}")
            return None

    def _internal_get_directory_tree(self) -> Dict[str, Any]:
        # The 'files' table contains all file paths, which is what we need.
        cursor = self._execute_query("SELECT path FROM files ORDER BY path ASC")
        if cursor:
            tree = [row['path'] for row in cursor.fetchall()]
            return {"directory_tree": tree, "status": "success"}
        return {"error": "Could not query directory tree from database.", "status": "error_db_query"}

    def _internal_list_files(self, directory_path: Optional[str]) -> Dict[str, Any]:
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
        cursor = self._execute_query(query, tuple(query_params))

        if cursor:
            files = [row['path'] for row in cursor.fetchall()]
            return {"directory_path": directory_path, "files": files, "status": "success"}
        return {"error": "Could not query file list from database.", "status": "error_db_query"}

    def _internal_get_project_summary(self) -> Dict[str, Any]:
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
        cursor = self._execute_query(query)
        if not cursor:
            return {"error": "Failed to query project summary.", "status": "error_db_query"}

        summary_data = dict(cursor.fetchone())
        return {"summary": summary_data, "status": "success"}

# --- Public Tool Functions ---

def get_directory_tree() -> str:
    """
    (Low-Cost) Lists all files and directories in the project in a tree-like format.

    This is useful for getting a quick, high-level overview of the entire project structure.
    """
    manager = _CodebaseManager()
    if not manager.conn:
        return json.dumps({"error": "Database connection not available.", "status": "error_no_db"})
    result_dict = manager._internal_get_directory_tree()
    return json.dumps(result_dict, indent=2)

def list_files(directory_path: Optional[str] = None) -> str:
    """
    (Low-Cost) Lists all files, optionally filtering by a specific subdirectory.

    @param directory_path (string): The directory to filter by (e.g., "src/api/"). If omitted, all files in the project are listed.
    """
    manager = _CodebaseManager()
    if not manager.conn:
        return json.dumps({"error": "Database connection not available.", "status": "error_no_db"})
    result_dict = manager._internal_list_files(directory_path)
    return json.dumps(result_dict, indent=2)

def get_project_summary() -> str:
    """
    (Low-Cost) Provides a high-level summary of the project, including file counts by type and total lines of code.
    """
    print(f"DEBUG: Attempting to use database path: {os.environ.get('CODEBASE_DB_PATH', 'project_context.db')}")
    manager = _CodebaseManager()
    if not manager.conn:
        return json.dumps({"error": "Database connection not available.", "status": "error_no_db"})
    result_dict = manager._internal_get_project_summary()
    return json.dumps(result_dict, indent=2)

def get_current_project_root() -> str:
    """
    (Low-Cost) Returns the absolute path of the current project's root directory.
    This path is determined by the CODEBASE_DB_PATH environment variable.
    """
    from my_tools.path_security import get_project_root
    import json
    try:
        root_path = get_project_root()
        return json.dumps({"status": "success", "project_root": root_path})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to get project root: {e}"})

if __name__ == '__main__':
    print("--- Testing ProjectExplorer Tool ---")
    db_path = os.environ.get("CODEBASE_DB_PATH", "project_context.db")
    if not os.path.exists(db_path):
        print(f"\nERROR: Database file '{db_path}' not found.")
        print("Please run the database creation script first.")
    else:
        print(f"Using existing database: '{db_path}'")

        print("\n--- Test Call 1: get_project_summary() ---")
        print(get_project_summary())

        print("\n--- Test Call 2: get_directory_tree() ---")
        # Keep the output brief for testing
        tree_result = json.loads(get_directory_tree())
        if tree_result.get("status") == "success":
            tree_result["directory_tree"] = tree_result["directory_tree"][:15] + ["... (truncated for display)"]
        print(json.dumps(tree_result, indent=2))

        print("\n--- Test Call 3: list_files() ---")
        # List all files, but truncate for display
        list_all_result = json.loads(list_files())
        if list_all_result.get("status") == "success":
            list_all_result["files"] = list_all_result["files"][:15] + ["... (truncated for display)"]
        print(json.dumps(list_all_result, indent=2))

        print("\n--- Test Call 4: list_files(directory_path='my_tools') ---")
        print(list_files(directory_path="my_tools"))

        print("\n--- Test Call 5: list_files(directory_path='non_existent_dir/') ---")
        print(list_files(directory_path="non_existent_dir/"))
