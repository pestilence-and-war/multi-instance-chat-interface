# my_tools/javascript_analyzer.py

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

    def _get_file_id(self, file_path: str) -> Optional[int]:
        if not file_path: return None
        cursor = self._execute_query("SELECT id FROM files WHERE path = ?", (file_path,))
        if cursor:
            row = cursor.fetchone()
            return row['id'] if row else None
        return None

    def _internal_list_javascript_constructs(self, file_path: str, construct_type: Optional[str]) -> Dict[str, Any]:
        file_id = self._get_file_id(file_path)
        if not file_id:
            return {"file_path": file_path, "error": "File not found.", "status": "error_not_found"}

        query = "SELECT name, construct_type, start_lineno, end_lineno FROM javascript_constructs WHERE file_id = ?"
        params = [file_id]
        if construct_type:
            query += " AND construct_type = ?"
            params.append(construct_type)

        query += " ORDER BY start_lineno"

        cursor = self._execute_query(query, tuple(params))
        if not cursor:
            return {"error": "DB query failed for JavaScript constructs.", "status": "error_db_query"}

        constructs = [dict(row) for row in cursor.fetchall()]

        return {
            "file_path": file_path,
            "filter": construct_type or "all",
            "constructs": constructs,
            "status": "success"
        }

# --- Public Tool Function ---

def list_javascript_constructs(file_path: str, construct_type: Optional[str] = None) -> str:
    """
    Lists all programming constructs or a specific type of construct from a JavaScript file.

    This tool can be used to find all functions, classes, imports, or exports
    within a given JavaScript file.

    @param file_path (string): The path to the JavaScript file to analyze. REQUIRED.
    @param construct_type (string): The specific type of construct to filter for.
        Valid types include: 'function', 'class', 'import', 'export'.
        If omitted, all recognized constructs are returned.
    """
    manager = _CodebaseManager()
    if not manager.conn:
        return json.dumps({"error": "Database connection not available.", "status": "error_no_db"})
    if not file_path:
        return json.dumps({"error": "Missing required 'file_path' parameter.", "status": "error_missing_param"})

    result_dict = manager._internal_list_javascript_constructs(file_path, construct_type)
    return json.dumps(result_dict, indent=2)

if __name__ == '__main__':
    print("--- Testing JavaScriptAnalyzer Tool ---")
    db_path = os.environ.get("CODEBASE_DB_PATH", "project_context.db")
    if not os.path.exists(db_path):
        print(f"\nERROR: Database file '{db_path}' not found.")
    else:
        print(f"Using existing database: '{db_path}'")
        # --- IMPORTANT ---
        # You must replace 'test_file' with the actual path to a JavaScript file
        # that exists in your 'project_context.db' database for these tests to work.
        test_file = "static/js/app.js" # <-- REPLACE IF NEEDED

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM files WHERE path=?", (test_file,))
        file_exists = cursor.fetchone()[0] > 0
        conn.close()

        if not file_exists:
            print(f"\nWARNING: The test file '{test_file}' was not found in your database.")
            print("Please edit the 'test_file' variable in the __main__ block of javascript_analyzer.py.")
        else:
            print(f"\n--- Test Call 1: list_javascript_constructs(file_path='{test_file}') ---")
            print(list_javascript_constructs(file_path=test_file))

            print(f"\n--- Test Call 2: list_javascript_constructs(file_path='{test_file}', construct_type='function') ---")
            print(list_javascript_constructs(file_path=test_file, construct_type='function'))

            print(f"\n--- Test Call 3: list_javascript_constructs(file_path='{test_file}', construct_type='import') ---")
            print(list_javascript_constructs(file_path=test_file, construct_type='import'))
