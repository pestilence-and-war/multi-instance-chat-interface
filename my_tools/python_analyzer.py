# my_tools/python_analyzer.py

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

    def _internal_list_python_classes(self, file_path: str) -> Dict[str, Any]:
        file_id = self._get_file_id(file_path)
        if not file_id: return {"file_path": file_path, "error": "File not found.", "status": "error_not_found"}

        cursor = self._execute_query("SELECT name, start_lineno, end_lineno FROM python_classes WHERE file_id = ?", (file_id,))
        if not cursor: return {"error": "DB query failed for classes.", "status": "error_db_query"}

        classes = [dict(row) for row in cursor.fetchall()]
        return {"file_path": file_path, "classes": classes, "status": "success"}

    def _internal_list_python_functions(self, file_path: str) -> Dict[str, Any]:
        file_id = self._get_file_id(file_path)
        if not file_id: return {"file_path": file_path, "error": "File not found.", "status": "error_not_found"}

        # Lists top-level functions only
        cursor = self._execute_query(
            "SELECT name, signature, start_lineno, end_lineno FROM python_functions WHERE file_id = ? AND class_id IS NULL", (file_id,)
        )
        if not cursor: return {"error": "DB query failed for functions.", "status": "error_db_query"}

        functions = [dict(row) for row in cursor.fetchall()]
        return {"file_path": file_path, "functions": functions, "status": "success"}

    def _internal_get_python_class_details(self, file_path: str, class_name: str) -> Dict[str, Any]:
        file_id = self._get_file_id(file_path)
        if not file_id: return {"file_path": file_path, "error": "File not found.", "status": "error_not_found"}

        class_cursor = self._execute_query(
            "SELECT id, name, docstring, start_lineno, end_lineno FROM python_classes WHERE file_id = ? AND name = ?", (file_id, class_name)
        )
        if not class_cursor: return {"error": "DB query failed for class details.", "status": "error_db_query"}
        class_data = class_cursor.fetchone()

        if not class_data:
            return {"file_path": file_path, "class_name": class_name, "error": "Class not found in file.", "status": "error_not_found"}

        class_details = dict(class_data)
        class_id = class_details.pop('id')

        methods_cursor = self._execute_query(
            "SELECT name, signature, docstring, start_lineno, end_lineno FROM python_functions WHERE class_id = ?", (class_id,)
        )
        if methods_cursor:
            class_details['methods'] = [dict(row) for row in methods_cursor.fetchall()]

        return {"file_path": file_path, "class_name": class_name, "details": class_details, "status": "success"}

    def _internal_get_python_function_details(self, file_path: str, function_name: str) -> Dict[str, Any]:
        file_id = self._get_file_id(file_path)
        if not file_id: return {"file_path": file_path, "error": "File not found.", "status": "error_not_found"}

        # This query still finds the target function(s)
        query = """
            SELECT f.id, f.name, f.signature, f.docstring, f.start_lineno, f.end_lineno, c.name as class_name
            FROM python_functions f
            LEFT JOIN python_classes c ON f.class_id = c.id
            WHERE f.file_id = ? AND f.name = ?
        """
        cursor = self._execute_query(query, (file_id, function_name))
        if not cursor: return {"error": "DB query failed for function details.", "status": "error_db_query"}

        func_data = cursor.fetchall()
        if not func_data:
            return {"file_path": file_path, "function_name": function_name, "error": "Function not found in file.", "status": "error_not_found"}

        # Prepare results, could be multiple if function names are overloaded in different classes
        results = []
        for row in func_data:
            func_details = dict(row)
            # We get the ID for our next query, but remove it from the final user-facing output.
            function_id = func_details.pop('id')

            # Query for any directly nested functions of this function.
            nested_functions_cursor = self._execute_query(
                "SELECT name, signature, start_lineno, end_lineno FROM python_functions WHERE parent_function_id = ?",
                (function_id,)
            )
            
            nested_functions_list = []
            if nested_functions_cursor:
                nested_functions_list = [dict(r) for r in nested_functions_cursor.fetchall()]

            # Add the list of nested functions to the result. It will be empty if there are none.
            func_details['nested_functions'] = nested_functions_list
            results.append(func_details)
            
        return {"file_path": file_path, "function_name": function_name, "details": results, "status": "success"}
    
# --- Public Tool Functions ---

def list_python_classes(file_path: str) -> str:
    """
    (Low-Cost) Lists all classes declared in a given Python file.
    @param file_path (string): The path to the Python file to analyze. REQUIRED.
    """
    manager = _CodebaseManager()
    if not manager.conn: return json.dumps({"error": "Database connection not available.", "status": "error_no_db"})
    if not file_path: return json.dumps({"error": "Missing 'file_path' parameter.", "status": "error_missing_param"})
    result_dict = manager._internal_list_python_classes(file_path)
    return json.dumps(result_dict, indent=2)

def list_python_functions(file_path: str) -> str:
    """
    (Low-Cost) Lists all top-level functions declared in a given Python file (methods inside classes are not included).
    @param file_path (string): The path to the Python file to analyze. REQUIRED.
    """
    manager = _CodebaseManager()
    if not manager.conn: return json.dumps({"error": "Database connection not available.", "status": "error_no_db"})
    if not file_path: return json.dumps({"error": "Missing 'file_path' parameter.", "status": "error_missing_param"})
    result_dict = manager._internal_list_python_functions(file_path)
    return json.dumps(result_dict, indent=2)

def get_python_class_details(file_path: str, class_name: str) -> str:
    """
    (Medium-Cost) Retrieves detailed information about a specific class, including its docstring and methods.
    @param file_path (string): The path to the Python file where the class is defined. REQUIRED.
    @param class_name (string): The name of the class to retrieve details for. REQUIRED.
    """
    manager = _CodebaseManager()
    if not manager.conn: return json.dumps({"error": "Database connection not available.", "status": "error_no_db"})
    if not file_path or not class_name: return json.dumps({"error": "Missing 'file_path' or 'class_name' parameter.", "status": "error_missing_param"})
    result_dict = manager._internal_get_python_class_details(file_path, class_name)
    return json.dumps(result_dict, indent=2)

def get_python_function_details(file_path: str, function_name: str) -> str:
    """
    (Medium-Cost) Retrieves detailed information about a specific function, including its signature, docstring, and any directly nested functions.
    This can find top-level functions or methods within classes.
    @param file_path (string): The path to the Python file where the function is defined. REQUIRED.
    @param function_name (string): The name of the function to retrieve details for. REQUIRED.
    """
    manager = _CodebaseManager()
    if not manager.conn: return json.dumps({"error": "Database connection not available.", "status": "error_no_db"})
    if not file_path or not function_name: return json.dumps({"error": "Missing 'file_path' or 'function_name' parameter.", "status": "error_missing_param"})
    result_dict = manager._internal_get_python_function_details(file_path, function_name)
    return json.dumps(result_dict, indent=2)

if __name__ == '__main__':
    print("--- Testing PythonAnalyzer Tool ---")
    db_path = os.environ.get("CODEBASE_DB_PATH", "project_context.db")
    if not os.path.exists(db_path):
        print(f"\nERROR: Database file '{db_path}' not found.")
    else:
        print(f"Using existing database: '{db_path}'")
        # Use a file that is known to be in the database
        test_file = "my_tools/codebase_query_tool.py"
        test_class = "_CodebaseManager"
        test_function = "_execute_query"

        print(f"\n--- Test Call 1: list_python_classes(file_path='{test_file}') ---")
        print(list_python_classes(file_path=test_file))

        print(f"\n--- Test Call 2: list_python_functions(file_path='{test_file}') ---")
        print(list_python_functions(file_path=test_file))

        print(f"\n--- Test Call 3: get_python_class_details(file_path='{test_file}', class_name='{test_class}') ---")
        print(get_python_class_details(file_path=test_file, class_name=test_class))

        print(f"\n--- Test Call 4: get_python_function_details(file_path='{test_file}', function_name='{test_function}') ---")
        print(get_python_function_details(file_path=test_file, function_name=test_function))

        print(f"\n--- Test Call 5 (Error): get_python_class_details(file_path='{test_file}', class_name='NonExistentClass') ---")
        print(get_python_class_details(file_path=test_file, class_name="NonExistentClass"))
