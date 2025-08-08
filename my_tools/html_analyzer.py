# my_tools/html_analyzer.py

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

def _helper_list_html_elements(manager: _CodebaseManager, file_path: str, element_type: Optional[str]) -> Dict[str, Any]:
    """Helper to retrieve a list of structural elements from a given HTML file."""
    file_id = _helper_get_file_id(manager, file_path)
    if file_id is None:
        return {"file_path": file_path, "error": "File not found or DB connection failed.", "status": "error_not_found"}

    query = "SELECT element_type, data FROM html_elements WHERE file_id = ?"
    params = [file_id]
    if element_type:
        query += " AND element_type = ?"
        params.append(element_type)

    cursor = manager._execute_read_query(query, tuple(params))
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
        except (json.JSONDecodeError, TypeError):
            # Handle cases where data might not be valid JSON or is None
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
    if not file_path:
        return json.dumps({"error": "Missing required 'file_path' parameter.", "status": "error_missing_param"}, indent=2)

    valid_elements = {'form', 'link', 'script', 'htmx', None}
    if element_type not in valid_elements:
        return json.dumps({
            "error": f"Invalid 'element_type' parameter. Must be one of {sorted([e for e in valid_elements if e is not None])}.",
            "status": "error_invalid_param"
        }, indent=2)

    manager = _CodebaseManager()
    result_dict = _helper_list_html_elements(manager, file_path, element_type)
    return json.dumps(result_dict, indent=2)

if __name__ == '__main__':
    import os
    print("--- Testing HTMLAnalyzer Tool ---")

    workspace_dir = os.environ.get("CODEBASE_DB_PATH", ".")
    db_path = os.path.join(workspace_dir, "project_context.db")

    if not os.path.exists(db_path):
        print(f"\nERROR: Database file '{os.path.abspath(db_path)}' not found.")
    else:
        print(f"Using database found at: '{os.path.abspath(db_path)}'")

        # Dynamically find an HTML file from the DB to test against
        manager = _CodebaseManager()
        cursor = manager._execute_read_query("SELECT path FROM files WHERE type = 'html' LIMIT 1")

        test_file = None
        if cursor:
            row = cursor.fetchone()
            if row:
                test_file = row['path']

        if not test_file:
            print("\nWARNING: No HTML files found in the database. Skipping tests.")
        else:
            print(f"\n--- Found test file in DB: '{test_file}' ---")

            print(f"\n--- Test Call 1: list_html_elements(file_path='{test_file}') ---")
            print(list_html_elements(file_path=test_file))

            print(f"\n--- Test Call 2: list_html_elements(file_path='{test_file}', element_type='script') ---")
            print(list_html_elements(file_path=test_file, element_type='script'))

            print(f"\n--- Test Call 3: list_html_elements(file_path='{test_file}', element_type='htmx') ---")
            print(list_html_elements(file_path=test_file, element_type='htmx'))

            print(f"\n--- Test Call 4 (Error): list_html_elements(file_path='{test_file}', element_type='invalid_type') ---")
            print(list_html_elements(file_path=test_file, element_type='invalid_type'))
