# my_tools/call_graph_analyzer.py

import json
import os
from typing import Dict, Any, Optional

from my_tools.codebase_manager import _CodebaseManager

# --- Internal Helper Class for Call Graph Logic ---
class _CallGraphHelper:
    """
    Encapsulates the specific database queries required for call graph analysis.
    """
    def _get_function_id(self, manager: _CodebaseManager, file_path: str, function_name: str) -> Optional[int]:
        """Finds the ID of a function given its name and file path."""
        query = """
            SELECT pf.id FROM python_functions pf
            JOIN files f ON pf.file_id = f.id
            WHERE f.path = ? AND pf.name = ?
        """
        cursor = manager._execute_read_query(query, (file_path, function_name))
        if cursor:
            # Note: This could find multiple functions with the same name in the same file (e.g. methods in different classes)
            # For this tool, we'll take the first one found.
            row = cursor.fetchone()
            return row['id'] if row else None
        return None

    def _get_callers(self, manager: _CodebaseManager, file_path: str, function_name: str) -> Dict[str, Any]:
        """
        Finds all functions that call a function with the given `function_name`.
        The search is global across the entire project's codebase.
        """
        query = """
            SELECT
                pf.name as caller_name,
                f.path as caller_file_path,
                pc.name as caller_class_name
            FROM python_function_calls pfc
            JOIN python_functions pf ON pfc.caller_function_id = pf.id
            JOIN files f ON pf.file_id = f.id
            LEFT JOIN python_classes pc ON pf.class_id = pc.id
            WHERE pfc.callee_name = ?
        """
        cursor = manager._execute_read_query(query, (function_name,))
        if not cursor:
            return {"error": "DB query failed for callers.", "status": "error_db_query"}

        callers = [dict(row) for row in cursor.fetchall()]
        return {"file_path": file_path, "function_name": function_name, "callers": callers, "status": "success"}

    def _get_callees(self, manager: _CodebaseManager, file_path: str, function_name: str) -> Dict[str, Any]:
        """
        Finds all functions called by a specific function instance (defined by file_path and function_name).
        """
        function_id = self._get_function_id(manager, file_path, function_name)
        if not function_id:
            return {"file_path": file_path, "function_name": function_name, "error": "Function not found.", "status": "error_not_found"}

        query = """
            SELECT
                callee_name
            FROM python_function_calls
            WHERE caller_function_id = ?
        """
        cursor = manager._execute_read_query(query, (function_id,))
        if not cursor:
            return {"error": "DB query failed for callees.", "status": "error_db_query"}

        callees = [dict(row) for row in cursor.fetchall()]
        return {"file_path": file_path, "function_name": function_name, "callees": callees, "status": "success"}

# --- Public Tool Functions ---

def get_function_callers(file_path: str, function_name: str) -> str:
    """
    (Low-Cost) Identifies PARENT functions (Upstream) that call this function.

    Use this to answer: "Who uses this?" or "Where is this triggered?"
    It returns a list of files/functions that depend on the target.
    
    @param file_path (string): The file containing the function.
    @param function_name (string): The name of the function.
    """
    if not file_path or not function_name:
        return json.dumps({"error": "Missing 'file_path' or 'function_name' parameter.", "status": "error_missing_param"}, indent=2)

    manager = _CodebaseManager()
    helper = _CallGraphHelper()
    result_dict = helper._get_callers(manager, file_path, function_name)
    return json.dumps(result_dict, indent=2)

def get_function_callees(file_path: str, function_name: str) -> str:
    """
    (Low-Cost) Identifies CHILD functions (Downstream) called BY this function.

    Use this to answer: "What does this do?" or "What is the execution chain?"
    It returns the list of helper functions, tools, or APIs that the target executes.
    PREFER THIS over reading source code to understand logic flow.

    @param file_path (string): The file containing the function.
    @param function_name (string): The name of the function.
    """
    if not file_path or not function_name:
        return json.dumps({"error": "Missing 'file_path' or 'function_name' parameter.", "status": "error_missing_param"}, indent=2)

    manager = _CodebaseManager()
    helper = _CallGraphHelper()
    result_dict = helper._get_callees(manager, file_path, function_name)
    return json.dumps(result_dict, indent=2)

if __name__ == '__main__':
    print("--- Testing CallGraphAnalyzer Tool ---")
    workspace_dir = os.environ.get("CODEBASE_DB_PATH", ".")
    db_path = os.path.join(workspace_dir, _CodebaseManager._db_filename)

    if not os.path.exists(db_path):
        print(f"\nERROR: Database file '{os.path.abspath(db_path)}' not found.")
        print("Please ensure the CODEBASE_DB_PATH environment variable is set correctly.")
    else:
        print(f"Using database found at: '{os.path.abspath(db_path)}'")

        # Test Case 1: Find callers of a shared, low-level function.
        # `_execute_read_query` is called by functions in `project_explorer.py` and this file.
        test_file_callers = "my_tools/codebase_manager.py"
        test_function_for_callers = "_execute_read_query"
        print(f"\n--- Test Call 1: get_function_callers(file_path='{test_file_callers}', function_name='{test_function_for_callers}') ---")
        print(get_function_callers(file_path=test_file_callers, function_name=test_function_for_callers))

        # Test Case 2: Find callees of a high-level function.
        # `get_directory_tree` in `project_explorer.py` calls `_execute_read_query`.
        test_file_callees = "my_tools/project_explorer.py"
        test_function_for_callees = "get_directory_tree"
        print(f"\n--- Test Call 2: get_function_callees(file_path='{test_file_callees}', function_name='{test_function_for_callees}') ---")
        print(get_function_callees(file_path=test_file_callees, function_name=test_function_for_callees))

        # Test Case 3: Error case for a non-existent function.
        print(f"\n--- Test Call 3 (Error): get_function_callees(file_path='{test_file_callees}', function_name='non_existent_function') ---")
        print(get_function_callees(file_path=test_file_callees, function_name="non_existent_function"))
