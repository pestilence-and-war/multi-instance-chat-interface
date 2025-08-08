# my_tools/python_analyzer.py

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

def _helper_list_python_classes(manager: _CodebaseManager, file_path: str) -> Dict[str, Any]:
    """Helper to retrieve a list of classes for a given file."""
    file_id = _helper_get_file_id(manager, file_path)
    if file_id is None:
        return {"file_path": file_path, "error": "File not found or DB connection failed.", "status": "error_not_found"}

    query = "SELECT name, start_lineno, end_lineno FROM python_classes WHERE file_id = ? ORDER BY start_lineno"
    cursor = manager._execute_read_query(query, (file_id,))
    if not cursor:
        return {"error": "DB query failed for classes.", "status": "error_db_query"}

    classes = [dict(row) for row in cursor.fetchall()]
    return {"file_path": file_path, "classes": classes, "status": "success"}

def _helper_list_python_functions(manager: _CodebaseManager, file_path: str) -> Dict[str, Any]:
    """Helper to retrieve a list of top-level functions for a given file."""
    file_id = _helper_get_file_id(manager, file_path)
    if file_id is None:
        return {"file_path": file_path, "error": "File not found or DB connection failed.", "status": "error_not_found"}

    query = "SELECT name, signature, start_lineno, end_lineno FROM python_functions WHERE file_id = ? AND class_id IS NULL ORDER BY start_lineno"
    cursor = manager._execute_read_query(query, (file_id,))
    if not cursor:
        return {"error": "DB query failed for functions.", "status": "error_db_query"}

    functions = [dict(row) for row in cursor.fetchall()]
    return {"file_path": file_path, "functions": functions, "status": "success"}

def _helper_get_python_class_details(manager: _CodebaseManager, file_path: str, class_name: str) -> Dict[str, Any]:
    """Helper to retrieve detailed information about a specific class."""
    file_id = _helper_get_file_id(manager, file_path)
    if file_id is None:
        return {"file_path": file_path, "error": "File not found or DB connection failed.", "status": "error_not_found"}

    class_cursor = manager._execute_read_query(
        "SELECT id, name, docstring, start_lineno, end_lineno FROM python_classes WHERE file_id = ? AND name = ?", (file_id, class_name)
    )
    if not class_cursor:
        return {"error": "DB query failed for class details.", "status": "error_db_query"}
    class_data = class_cursor.fetchone()

    if not class_data:
        return {"file_path": file_path, "class_name": class_name, "error": "Class not found in file.", "status": "error_not_found"}

    class_details = dict(class_data)
    class_id = class_details.pop('id')

    methods_cursor = manager._execute_read_query(
        "SELECT name, signature, docstring, start_lineno, end_lineno FROM python_functions WHERE class_id = ? ORDER BY start_lineno", (class_id,)
    )
    if methods_cursor:
        class_details['methods'] = [dict(row) for row in methods_cursor.fetchall()]
    else:
        class_details['methods'] = [] # Ensure methods key exists

    return {"file_path": file_path, "class_name": class_name, "details": class_details, "status": "success"}

def _helper_get_python_function_details(manager: _CodebaseManager, file_path: str, function_name: str) -> Dict[str, Any]:
    """Helper to retrieve detailed information about a specific function."""
    file_id = _helper_get_file_id(manager, file_path)
    if file_id is None:
        return {"file_path": file_path, "error": "File not found or DB connection failed.", "status": "error_not_found"}

    query = """
        SELECT f.id, f.name, f.signature, f.docstring, f.start_lineno, f.end_lineno, c.name as class_name
        FROM python_functions f
        LEFT JOIN python_classes c ON f.class_id = c.id
        WHERE f.file_id = ? AND f.name = ?
    """
    cursor = manager._execute_read_query(query, (file_id, function_name))
    if not cursor:
        return {"error": "DB query failed for function details.", "status": "error_db_query"}

    func_data = cursor.fetchall()
    if not func_data:
        return {"file_path": file_path, "function_name": function_name, "error": "Function not found in file.", "status": "error_not_found"}

    results = []
    for row in func_data:
        func_details = dict(row)
        function_id = func_details.pop('id')

        nested_functions_cursor = manager._execute_read_query(
            "SELECT name, signature, start_lineno, end_lineno FROM python_functions WHERE parent_function_id = ? ORDER BY start_lineno",
            (function_id,)
        )

        nested_functions_list = []
        if nested_functions_cursor:
            nested_functions_list = [dict(r) for r in nested_functions_cursor.fetchall()]

        func_details['nested_functions'] = nested_functions_list
        results.append(func_details)

    return {"file_path": file_path, "function_name": function_name, "details": results, "status": "success"}

# --- Public Tool Functions ---

def list_python_classes(file_path: str) -> str:
    """
    (Low-Cost) Lists all classes declared in a given Python file.
    @param file_path (string): The path to the Python file to analyze. REQUIRED.
    """
    if not file_path:
        return json.dumps({"error": "Missing 'file_path' parameter.", "status": "error_missing_param"}, indent=2)
    manager = _CodebaseManager()
    result_dict = _helper_list_python_classes(manager, file_path)
    return json.dumps(result_dict, indent=2)

def list_python_functions(file_path: str) -> str:
    """
    (Low-Cost) Lists all top-level functions declared in a given Python file (methods inside classes are not included).
    @param file_path (string): The path to the Python file to analyze. REQUIRED.
    """
    if not file_path:
        return json.dumps({"error": "Missing 'file_path' parameter.", "status": "error_missing_param"}, indent=2)
    manager = _CodebaseManager()
    result_dict = _helper_list_python_functions(manager, file_path)
    return json.dumps(result_dict, indent=2)

def get_python_class_details(file_path: str, class_name: str) -> str:
    """
    (Medium-Cost) Retrieves detailed information about a specific class, including its docstring and methods.
    @param file_path (string): The path to the Python file where the class is defined. REQUIRED.
    @param class_name (string): The name of the class to retrieve details for. REQUIRED.
    """
    if not file_path or not class_name:
        return json.dumps({"error": "Missing 'file_path' or 'class_name' parameter.", "status": "error_missing_param"}, indent=2)
    manager = _CodebaseManager()
    result_dict = _helper_get_python_class_details(manager, file_path, class_name)
    return json.dumps(result_dict, indent=2)

def get_python_function_details(file_path: str, function_name: str) -> str:
    """
    (Medium-Cost) Retrieves detailed information about a specific function, including its signature, docstring, and any directly nested functions.
    This can find top-level functions or methods within classes.
    @param file_path (string): The path to the Python file where the function is defined. REQUIRED.
    @param function_name (string): The name of the function to retrieve details for. REQUIRED.
    """
    if not file_path or not function_name:
        return json.dumps({"error": "Missing 'file_path' or 'function_name' parameter.", "status": "error_missing_param"}, indent=2)
    manager = _CodebaseManager()
    result_dict = _helper_get_python_function_details(manager, file_path, function_name)
    return json.dumps(result_dict, indent=2)


if __name__ == '__main__':
    import os
    print("--- Testing PythonAnalyzer Tool ---")
    # The CODEBASE_DB_PATH env var is used by the manager automatically.
    # We just check for the DB's existence to provide a helpful message.
    workspace_dir = os.environ.get("CODEBASE_DB_PATH", ".")
    db_path = os.path.join(workspace_dir, "project_context.db")

    if not os.path.exists(db_path):
        print(f"\nERROR: Database file '{os.path.abspath(db_path)}' not found.")
    else:
        print(f"Using database found at: '{os.path.abspath(db_path)}'")

        # Test against the codebase_manager.py file as it's guaranteed to have a class.
        test_file = "my_tools/codebase_manager.py"
        test_class = "_CodebaseManager"
        test_function = "_get_connection" # A method within the class

        print(f"\n--- Test Call 1: list_python_classes(file_path='{test_file}') ---")
        print(list_python_classes(file_path=test_file))

        print(f"\n--- Test Call 2: list_python_functions(file_path='{test_file}') ---")
        print(list_python_functions(file_path=test_file)) # Should be empty as it has no top-level functions

        print(f"\n--- Test Call 3: get_python_class_details(file_path='{test_file}', class_name='{test_class}') ---")
        print(get_python_class_details(file_path=test_file, class_name=test_class))

        print(f"\n--- Test Call 4: get_python_function_details(file_path='{test_file}', function_name='{test_function}') ---")
        print(get_python_function_details(file_path=test_file, function_name=test_function))

        print(f"\n--- Test Call 5 (Error): get_python_class_details(file_path='{test_file}', class_name='NonExistentClass') ---")
        print(get_python_class_details(file_path=test_file, class_name="NonExistentClass"))
