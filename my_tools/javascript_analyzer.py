# my_tools/javascript_analyzer.py

import json
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

def _helper_list_javascript_constructs(manager: _CodebaseManager, file_path: str, construct_type: Optional[str]) -> Dict[str, Any]:
    """Helper to retrieve a list of constructs for a given JavaScript file."""
    file_id = _helper_get_file_id(manager, file_path)
    if file_id is None:
        return {"file_path": file_path, "error": "File not found or DB connection failed.", "status": "error_not_found"}

    query = "SELECT name, construct_type, start_lineno, end_lineno FROM javascript_constructs WHERE file_id = ?"
    params = [file_id]
    if construct_type:
        query += " AND construct_type = ?"
        params.append(construct_type)

    query += " ORDER BY start_lineno"

    cursor = manager._execute_read_query(query, tuple(params))
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
    if not file_path:
        return json.dumps({"error": "Missing required 'file_path' parameter.", "status": "error_missing_param"}, indent=2)

    valid_constructs = {'function', 'class', 'import', 'export', None}
    if construct_type not in valid_constructs:
        return json.dumps({
            "error": f"Invalid 'construct_type' parameter. Must be one of {sorted([c for c in valid_constructs if c is not None])}.",
            "status": "error_invalid_param"
        }, indent=2)

    manager = _CodebaseManager()
    result_dict = _helper_list_javascript_constructs(manager, file_path, construct_type)
    return json.dumps(result_dict, indent=2)

if __name__ == '__main__':
    import os
    print("--- Testing JavaScriptAnalyzer Tool ---")

    workspace_dir = os.environ.get("CODEBASE_DB_PATH", ".")
    db_path = os.path.join(workspace_dir, "project_context.db")

    if not os.path.exists(db_path):
        print(f"\nERROR: Database file '{os.path.abspath(db_path)}' not found.")
    else:
        print(f"Using database found at: '{os.path.abspath(db_path)}'")

        # Dynamically find a JavaScript file from the DB to test against
        manager = _CodebaseManager()
        cursor = manager._execute_read_query("SELECT path FROM files WHERE type = 'javascript' LIMIT 1")

        test_file = None
        if cursor:
            row = cursor.fetchone()
            if row:
                test_file = row['path']

        if not test_file:
            print("\nWARNING: No JavaScript files found in the database. Skipping tests.")
        else:
            print(f"\n--- Found test file in DB: '{test_file}' ---")

            print(f"\n--- Test Call 1: list_javascript_constructs(file_path='{test_file}') ---")
            print(list_javascript_constructs(file_path=test_file))

            print(f"\n--- Test Call 2: list_javascript_constructs(file_path='{test_file}', construct_type='function') ---")
            print(list_javascript_constructs(file_path=test_file, construct_type='function'))

            print(f"\n--- Test Call 3: list_javascript_constructs(file_path='{test_file}', construct_type='import') ---")
            print(list_javascript_constructs(file_path=test_file, construct_type='import'))

            print(f"\n--- Test Call 4 (Error): list_javascript_constructs(file_path='non_existent_file.js') ---")
            print(list_javascript_constructs(file_path='non_existent_file.js'))
