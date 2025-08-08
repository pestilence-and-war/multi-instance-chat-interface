# my_tools/css_analyzer.py

import json
import os
import sqlite3
from typing import Dict, Any, Optional

from my_tools.codebase_manager import _CodebaseManager

# --- Helper Functions (Business Logic) ---

def _helper_get_file_id(manager: _CodebaseManager, file_path: str) -> Optional[int]:
    """Given a file path, queries the DB for its unique ID."""
    cursor = manager._execute_read_query("SELECT id FROM files WHERE path = ?", (file_path,))
    if cursor:
        row = cursor.fetchone()
        return row['id'] if row else None
    return None

def _helper_list_css_rules(manager: _CodebaseManager, file_path: str) -> Dict[str, Any]:
    """Helper to retrieve a list of all CSS rules and their selectors for a given file."""
    file_id = _helper_get_file_id(manager, file_path)
    if file_id is None:
        return {"file_path": file_path, "error": "File not found or DB connection failed.", "status": "error_not_found"}

    rules_cursor = manager._execute_read_query(
        "SELECT id, source_code, start_lineno, end_lineno FROM css_rules WHERE file_id = ? ORDER BY start_lineno", (file_id,)
    )
    if not rules_cursor:
        return {"error": "DB query failed for CSS rules.", "status": "error_db_query"}

    rules = []
    for rule_row in rules_cursor.fetchall():
        rule_data = dict(rule_row)
        rule_id = rule_data.pop('id')

        selectors_cursor = manager._execute_read_query(
            "SELECT selector_text FROM css_selectors WHERE rule_id = ?", (rule_id,)
        )
        if selectors_cursor:
            rule_data['selectors'] = [s_row['selector_text'] for s_row in selectors_cursor.fetchall()]
        else:
            rule_data['selectors'] = []  # Ensure key exists

        rules.append(rule_data)

    return {"file_path": file_path, "rules": rules, "status": "success"}

# --- Public Tool Function ---

def list_css_rules(file_path: str) -> str:
    """
    (Low-Cost) Lists all rules and their selectors from a given CSS file.

    @param file_path (string): The path to the CSS file to analyze. REQUIRED.
    """
    if not file_path:
        return json.dumps({"error": "Missing required 'file_path' parameter.", "status": "error_missing_param"}, indent=2)

    manager = _CodebaseManager()
    result_dict = _helper_list_css_rules(manager, file_path)
    return json.dumps(result_dict, indent=2)

if __name__ == '__main__':
    print("--- Testing CSSAnalyzer Tool ---")
    workspace_dir = os.environ.get("CODEBASE_DB_PATH", ".")
    db_path = os.path.join(workspace_dir, "project_context.db")

    if not os.path.exists(db_path):
        print(f"\nERROR: Database file '{os.path.abspath(db_path)}' not found.")
    else:
        print(f"Using database found at: '{os.path.abspath(db_path)}'")
        # --- IMPORTANT ---
        # This test requires a specific CSS file to be present in the database.
        # Replace 'test_file' with a known CSS file path from your project if needed.
        test_file = "static/css/styles.css"  # <-- REPLACE IF NEEDED

        try:
            # This direct check is the most reliable way to verify test data existence.
            conn = sqlite3.connect(f"file:{os.path.abspath(db_path)}?mode=ro", uri=True)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM files WHERE path=?", (test_file,))
            file_exists = cursor.fetchone()[0] > 0
            conn.close()
        except sqlite3.Error as e:
            print(f"\nERROR: Could not connect to DB to verify test file: {e}")
            file_exists = False

        if not file_exists:
            print(f"\nWARNING: The test file '{test_file}' was not found in your database.")
            print("Please edit the 'test_file' variable in the __main__ block of css_analyzer.py to point to a valid CSS file.")
        else:
            print(f"\n--- Test Call 1: list_css_rules(file_path='{test_file}') ---")
            print(list_css_rules(file_path=test_file))
