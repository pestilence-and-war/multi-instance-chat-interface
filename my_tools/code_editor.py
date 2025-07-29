import ast
import sqlite3
import os
import json
from my_tools.parsing_utils import parse_python_file, insert_file_data

class _CodeTransformer(ast.NodeTransformer):
    """
    An AST transformer that finds and replaces a specific class or function node
    with new nodes derived from the provided 'new_code'.
    Internal class, prefixed with an underscore.
    """

    def __init__(self, target_identifier: str, new_code: str):
        self.target_parts = target_identifier.split('.')
        self.new_nodes = ast.parse(new_code).body
        self.target_found_and_replaced = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> any:
        if len(self.target_parts) == 1 and node.name == self.target_parts[0]:
            self.target_found_and_replaced = True
            return self.new_nodes
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> any:
        if len(self.target_parts) == 1 and node.name == self.target_parts[0]:
            self.target_found_and_replaced = True
            return self.new_nodes
        return self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> any:
        if len(self.target_parts) == 1 and node.name == self.target_parts[0]:
            self.target_found_and_replaced = True
            return self.new_nodes
        elif len(self.target_parts) == 2 and node.name == self.target_parts[0]:
            method_found = False
            new_body = []
            for child_node in node.body:
                if isinstance(child_node, (ast.FunctionDef, ast.AsyncFunctionDef)) and child_node.name == self.target_parts[1]:
                    new_body.extend(self.new_nodes)
                    method_found = True
                else:
                    new_body.append(child_node)
            if method_found:
                node.body = new_body
                self.target_found_and_replaced = True
            return self.generic_visit(node)
        return self.generic_visit(node)

def debug_write_file(file_path: str, content: str) -> str:
    """
    (Temporary Debugging Tool) Writes a simple string to a file.

    This tool is for diagnostic purposes only. It bypasses all complex parsing
    and directly tests the file system's write capability within the tool's
    execution environment. It includes the standard safety checks.

    Args:
        file_path (str): The absolute path to the file to write.
        content (str): The string content to write to the file.

    Returns:
        A JSON string with the status of the operation.
    """
    from my_tools.path_security import is_path_safe
    import json
    import os

    if not is_path_safe(file_path):
        return json.dumps({
            'status': 'error',
            'message': 'Security Error: Path is outside the allowed project directory.'
        })

    try:
        # The core of the test: attempt to write the content to the specified file.
        # The 'w' mode will create the file if it doesn't exist, or overwrite it if it does.
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        # If any error occurs during the write, report it.
        return json.dumps({
            'status': 'error',
            'message': f'An unexpected error occurred during file write: {e}'
        })

    # If the try block completes without error, report success.
    return json.dumps({
        'status': 'success',
        'message': f"Successfully wrote to '{file_path}'. Verification is needed."
    })

def apply_code_modification(file_path: str, target_identifier: str, new_code: str) -> str:
    """
    (High-Cost) Modifies a Python file by replacing a function or class with new code.

    This tool operates directly on the file system using an Abstract Syntax Tree (AST)
    for precise modification. After using this tool, you MUST call 'refresh_file_representation'
    on the same file_path to update the project's database.

    Args:
        file_path (str): The path to the Python file to modify.
        target_identifier (str): The identifier of the code to replace (e.g., "MyClass" or "MyClass.my_method").
        new_code (str): The new Python code to insert.

    Returns:
        A JSON string with the status of the operation.
    """
    from my_tools.path_security import is_path_safe
    import json
    import os
    import ast

    # --- Start of existing code ---
    if not is_path_safe(file_path):
        return json.dumps({'status': 'error', 'message': 'Security Error: Path is outside the allowed project directory.'})
    if not os.path.exists(file_path):
        return json.dumps({'status': 'error', 'message': f'File not found: {file_path}'})
    try:
        ast.parse(new_code)
    except SyntaxError as e:
        return json.dumps({'status': 'error', 'message': f'Syntax error in new_code: {e}'})
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        original_tree = ast.parse(source_code)
    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'Failed to read or parse {file_path}: {e}'})

    # This is the internal transformer class you provided earlier
    transformer = _CodeTransformer(target_identifier, new_code)
    new_tree = transformer.visit(original_tree)

    if not transformer.target_found_and_replaced:
        return json.dumps({'status': 'error', 'message': f"Target '{target_identifier}' not found in {file_path}."})

    # --- NEW DIAGNOSTIC CODE ---
    try:
        modified_code = ast.unparse(new_tree)
    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'AST unparsing failed: {e}'})

    # Compare the original source with the newly generated code.
    # We normalize them by stripping whitespace from each line to avoid false negatives.
    original_lines = [line.strip() for line in source_code.strip().splitlines()]
    modified_lines = [line.strip() for line in modified_code.strip().splitlines()]

    if original_lines == modified_lines:
        return json.dumps({
            'status': 'error',
            'message': 'Internal Tool Error: Code modification resulted in no changes. The AST transformation failed silently.'
        })
    # --- END OF NEW DIAGNOSTIC CODE ---
    try:
        modified_code = ast.unparse(new_tree)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modified_code)
    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'Failed to write modified code to {file_path}: {e}'})
    return json.dumps({'status': 'success', 'message': f"File '{file_path}' modified. You MUST now call 'refresh_file_representation' to sync the database."}, indent=2)

def refresh_file_representation(file_path: str) -> str:
    """
    (High-Cost) Updates the database representation for a single file that has been changed.

    This tool removes the old database entry and re-parses the live file to insert
    the new, correct representation. It is a necessary follow-up to 'apply_code_modification'.

    Args:
        file_path (str): The path to the file to refresh.

    Returns:
        A JSON string with the status of the operation.
    """
    
    import json
    import os
    import sqlite3
    from my_tools.path_security import is_path_safe, get_db_path, get_project_root
    from my_tools.parsing_utils import parse_python_file, insert_file_data
    if not is_path_safe(file_path):
        return json.dumps({'status': 'error', 'message': 'Security Error: Path is outside the allowed project directory. Ensure CODEBASE_DB_PATH is set correctly.'})

    db_path = get_db_path() # Use the new, reliable utility
    if not db_path:
        # This check is now explicit and clear.
        return json.dumps({'status': 'error', 'message': 'Database path could not be determined. Ensure CODEBASE_DB_PATH is set.'})

    if not os.path.exists(file_path):
        return json.dumps({'status': 'error', 'message': f'File not found: {file_path}'})
    
    project_root = get_project_root()
    if not project_root:
        return json.dumps({'status': 'error', 'message': 'Project root could not be determined to calculate relative path.'})
    relative_path = os.path.relpath(file_path, project_root).replace("\\", "/")
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('BEGIN')

        # --- MODIFIED: Use the relative_path for the DELETE operation ---
        cursor.execute('DELETE FROM files WHERE path = ?', (relative_path,))
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        _, ext = os.path.splitext(file_path)

        if ext == '.py':
            # --- MODIFIED: Pass the relative_path to the parser to ensure it's stored correctly ---
            file_details = parse_python_file(relative_path, content)
        else:
            # Handle other file types if necessary, ensuring relative_path is used
            file_details = {
                'path': relative_path, 
                'type': ext[1:] or 'text', 
                'full_content': content,
                'start_lineno': 1,
                'end_lineno': len(content.splitlines()),
                'docstring': None
            }

        insert_file_data(cursor, file_details)

        conn.commit()
        return json.dumps({'status': 'success', 'message': f"Database representation for '{relative_path}' updated successfully."})
    except Exception as e:
        if conn:
            conn.rollback()
        # Provide more context in the error message
        return json.dumps({'status': 'error', 'message': f'An error occurred during refresh for {relative_path}: {e}'})
    finally:
        if conn:
            conn.close()