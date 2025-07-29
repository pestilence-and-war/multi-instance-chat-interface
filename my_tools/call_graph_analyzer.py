# my_tools/call_graph_analyzer.py

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

    def _get_function_id(self, file_path: str, function_name: str) -> Optional[int]:
        """Finds the ID of a function given its name and file path."""
        query = """
            SELECT pf.id FROM python_functions pf
            JOIN files f ON pf.file_id = f.id
            WHERE f.path = ? AND pf.name = ?
        """
        cursor = self._execute_query(query, (file_path, function_name))
        if cursor:
            # Note: This could find multiple functions with the same name in the same file (e.g. methods in different classes)
            # For this tool, we'll take the first one found. A more advanced tool might let the user specify.
            row = cursor.fetchone()
            return row['id'] if row else None
        return None

    def _internal_get_callers(self, file_path: str, function_name: str) -> Dict[str, Any]:
        # For callers, we search for the 'callee_name' in the python_function_calls table.
        # We don't need the function_id of the callee itself, as callee_name is directly stored.
        # The file_path parameter for the callee is not used in this query due to schema design.

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
        cursor = self._execute_query(query, (function_name,)) # Pass function_name directly
        if not cursor:
            return {"error": "DB query failed for callers.", "status": "error_db_query"}

        callers = [dict(row) for row in cursor.fetchall()]
        return {"file_path": file_path, "function_name": function_name, "callers": callers, "status": "success"}

    def _internal_get_callees(self, file_path: str, function_name: str) -> Dict[str, Any]:
        function_id = self._get_function_id(file_path, function_name)
        if not function_id:
            return {"file_path": file_path, "function_name": function_name, "error": "Function not found.", "status": "error_not_found"}

        # For callees, we search for functions where the 'caller_function_id' matches our function_id.
        # The python_function_calls table only stores 'callee_name', not a callee_function_id,
        # so we can only retrieve the name of the called function directly.
        query = """
            SELECT
                callee_name
            FROM python_function_calls
            WHERE caller_function_id = ?
        """
        cursor = self._execute_query(query, (function_id,))
        if not cursor:
            return {"error": "DB query failed for callees.", "status": "error_db_query"}

        callees = [dict(row) for row in cursor.fetchall()]
        return {"file_path": file_path, "function_name": function_name, "callees": callees, "status": "success"}

# --- Public Tool Functions ---

def get_function_callers(file_path: str, function_name: str) -> str:
    """
    (High-Cost) Finds all functions that call a specified function.

    This helps understand the impact of changing a function, as it shows all its entry points.

    @param file_path (string): The path to the Python file where the target function is defined. REQUIRED.
    @param function_name (string): The name of the target function (the "callee"). REQUIRED.
    """
    manager = _CodebaseManager()
    if not manager.conn: return json.dumps({"error": "Database connection not available.", "status": "error_no_db"})
    if not file_path or not function_name: return json.dumps({"error": "Missing 'file_path' or 'function_name' parameter.", "status": "error_missing_param"})
    result_dict = manager._internal_get_callers(file_path, function_name)
    return json.dumps(result_dict, indent=2)

def get_function_callees(file_path: str, function_name: str) -> str:
    """
    (High-Cost) Finds all functions that are called by a specified function.

    This helps understand what a function does by showing its dependencies and sub-tasks.

    @param file_path (string): The path to the Python file where the target function is defined. REQUIRED.
    @param function_name (string): The name of the target function (the "caller"). REQUIRED.
    """
    manager = _CodebaseManager()
    if not manager.conn: return json.dumps({"error": "Database connection not available.", "status": "error_no_db"})
    if not file_path or not function_name: return json.dumps({"error": "Missing 'file_path' or 'function_name' parameter.", "status": "error_missing_param"})
    result_dict = manager._internal_get_callees(file_path, function_name)
    return json.dumps(result_dict, indent=2)

if __name__ == '__main__':
    print("--- Testing CallGraphAnalyzer Tool ---")
    db_path = os.environ.get("CODEBASE_DB_PATH", "project_context.db")
    if not os.path.exists(db_path):
        print(f"\nERROR: Database file '{db_path}' not found.")
    else:
        print(f"Using existing database: '{db_path}'")
        # Use a function from the original codebase_query_tool that we know has calls
        test_file = "my_tools/codebase_query_tool.py"
        # This function is called by many public operations
        test_function_for_callers = "_execute_query"
        # This function calls _execute_query
        test_function_for_callees = "_get_file_id"

        print(f"\n--- Test Call 1: get_function_callers(file_path='{test_file}', function_name='{test_function_for_callers}') ---")
        print(get_function_callers(file_path=test_file, function_name=test_function_for_callers))

        print(f"\n--- Test Call 2: get_function_callees(file_path='{test_file}', function_name='{test_function_for_callees}') ---")
        print(get_function_callees(file_path=test_file, function_name=test_function_for_callees))

        print(f"\n--- Test Call 3 (Error): get_function_callers(file_path='{test_file}', function_name='non_existent_function') ---")
        print(get_function_callers(file_path=test_file, function_name="non_existent_function"))
