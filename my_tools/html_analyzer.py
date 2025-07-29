# my_tools/html_analyzer.py

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

    def _internal_list_html_elements(self, file_path: str, element_type: Optional[str]) -> Dict[str, Any]:
        file_id = self._get_file_id(file_path)
        if not file_id:
            return {"file_path": file_path, "error": "File not found.", "status": "error_not_found"}

        query = "SELECT element_type, data FROM html_elements WHERE file_id = ?"
        params = [file_id]
        if element_type:
            query += " AND element_type = ?"
            params.append(element_type)

        cursor = self._execute_query(query, tuple(params))
        if not cursor:
            return {"error": "DB query failed for HTML elements.", "status": "error_db_query"}

        elements = []
        for row in cursor.fetchall():
            try:
                element_data = json.loads(row['data'])
                elements.append({
                    "type": row['element_type'],
                    "details": element_data
                })
            except json.JSONDecodeError:
                # Handle cases where data might not be valid JSON
                elements.append({
                    "type": row['element_type'],
                    "error": "Could not parse element data.",
                    "raw_data": row['data']
                })

        return {
            "file_path": file_path,
            "filter": element_type or "all",
            "elements": elements,
            "status": "success"
        }

# --- Public Tool Function ---

def list_html_elements(file_path: str, element_type: Optional[str] = None) -> str:
    """
    Lists all structural elements or a specific type of element from an HTML file.

    This tool can be used to find all forms, links, scripts, or htmx-specific attributes
    within a given HTML file.

    @param file_path (string): The path to the HTML file to analyze. REQUIRED.
    @param element_type (string): The specific type of element to filter for.
        Valid types include: 'form', 'link', 'script', 'htmx'.
        If omitted, all recognized structural elements are returned.
    """
    manager = _CodebaseManager()
    if not manager.conn:
        return json.dumps({"error": "Database connection not available.", "status": "error_no_db"})
    if not file_path:
        return json.dumps({"error": "Missing required 'file_path' parameter.", "status": "error_missing_param"})

    result_dict = manager._internal_list_html_elements(file_path, element_type)
    return json.dumps(result_dict, indent=2)

if __name__ == '__main__':
    print("--- Testing HTMLAnalyzer Tool ---")
    db_path = os.environ.get("CODEBASE_DB_PATH", "project_context.db")
    if not os.path.exists(db_path):
        print(f"\nERROR: Database file '{db_path}' not found.")
    else:
        print(f"Using existing database: '{db_path}'")
        # --- IMPORTANT ---
        # You must replace 'test_file_path' with the actual path to an HTML file
        # that exists in your 'project_context.db' database for these tests to work.
        test_file = "templates/index.html" # <-- REPLACE IF NEEDED

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM files WHERE path=?", (test_file,))
        file_exists = cursor.fetchone()[0] > 0
        conn.close()

        if not file_exists:
            print(f"\nWARNING: The test file '{test_file}' was not found in your database.")
            print("Please edit the 'test_file' variable in the __main__ block of html_analyzer.py.")
        else:
            print(f"\n--- Test Call 1: list_html_elements(file_path='{test_file}') ---")
            print(list_html_elements(file_path=test_file))

            print(f"\n--- Test Call 2: list_html_elements(file_path='{test_file}', element_type='script') ---")
            print(list_html_elements(file_path=test_file, element_type='script'))

            print(f"\n--- Test Call 3: list_html_elements(file_path='{test_file}', element_type='form') ---")
            print(list_html_elements(file_path=test_file, element_type='form'))
