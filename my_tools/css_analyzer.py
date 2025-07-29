# my_tools/css_analyzer.py

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

    def _internal_list_css_rules(self, file_path: str) -> Dict[str, Any]:
        file_id = self._get_file_id(file_path)
        if not file_id:
            return {"file_path": file_path, "error": "File not found.", "status": "error_not_found"}

        rules_cursor = self._execute_query(
            "SELECT id, source_code, start_lineno, end_lineno FROM css_rules WHERE file_id = ?", (file_id,)
        )
        if not rules_cursor:
            return {"error": "DB query failed for CSS rules.", "status": "error_db_query"}

        rules = []
        for rule_row in rules_cursor.fetchall():
            rule_data = dict(rule_row)
            rule_id = rule_data.pop('id')

            selectors_cursor = self._execute_query(
                "SELECT selector_text FROM css_selectors WHERE rule_id = ?", (rule_id,)
            )
            if selectors_cursor:
                rule_data['selectors'] = [s_row['selector_text'] for s_row in selectors_cursor.fetchall()]
            else:
                rule_data['selectors'] = [] # Ensure key exists

            rules.append(rule_data)

        return {"file_path": file_path, "rules": rules, "status": "success"}

# --- Public Tool Function ---

def list_css_rules(file_path: str) -> str:
    """
    Lists all rules and their selectors from a given CSS file.

    @param file_path (string): The path to the CSS file to analyze. REQUIRED.
    """
    manager = _CodebaseManager()
    if not manager.conn:
        return json.dumps({"error": "Database connection not available.", "status": "error_no_db"})
    if not file_path:
        return json.dumps({"error": "Missing required 'file_path' parameter.", "status": "error_missing_param"})

    result_dict = manager._internal_list_css_rules(file_path)
    return json.dumps(result_dict, indent=2)

if __name__ == '__main__':
    print("--- Testing CSSAnalyzer Tool ---")
    db_path = os.environ.get("CODEBASE_DB_PATH", "project_context.db")
    if not os.path.exists(db_path):
        print(f"\nERROR: Database file '{db_path}' not found.")
    else:
        print(f"Using existing database: '{db_path}'")
        # --- IMPORTANT ---
        # You must replace 'test_file_path' with the actual path to a CSS file
        # that exists in your 'project_context.db' database for these tests to work.
        test_file = "static/css/styles.css" # <-- REPLACE IF NEEDED

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM files WHERE path=?", (test_file,))
        file_exists = cursor.fetchone()[0] > 0
        conn.close()

        if not file_exists:
            print(f"\nWARNING: The test file '{test_file}' was not found in your database.")
            print("Please edit the 'test_file' variable in the __main__ block of css_analyzer.py.")
        else:
            print(f"\n--- Test Call 1: list_css_rules(file_path='{test_file}') ---")
            print(list_css_rules(file_path=test_file))
