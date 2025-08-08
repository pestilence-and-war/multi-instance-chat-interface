# my_tools/code_editor.py

import ast
import os
import json
from typing import Any
from my_tools.codebase_manager import _CodebaseManager
from my_tools.path_security import _is_path_safe, _get_project_root
from my_tools.parsing_utils import _parse_python_file, _insert_file_data


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

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        if len(self.target_parts) == 1 and node.name == self.target_parts[0]:
            self.target_found_and_replaced = True
            return self.new_nodes
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        if len(self.target_parts) == 1 and node.name == self.target_parts[0]:
            self.target_found_and_replaced = True
            return self.new_nodes
        return self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
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


def _sync_db_after_file_creation(relative_path: str) -> str:
    """
    (Internal) Updates the DB after a file is created/updated. Uses a WRITE connection.
    """
    project_root = _get_project_root()
    if not project_root:
        return json.dumps({'status': 'error', 'message': 'Project root not configured.'})
    
    full_path = os.path.abspath(os.path.join(project_root, relative_path.replace('/', '\\')))
    if not os.path.exists(full_path):
        return json.dumps({'status': 'error', 'message': f'File not found: {full_path}'})

    manager = _CodebaseManager()
    try:
        # Delete old record first
        manager._execute_write_query('DELETE FROM files WHERE path = ?', (relative_path,))

        # Add new record
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        _, ext = os.path.splitext(full_path)
        file_type = ext[1:] or 'text'
        
        file_details = _parse_python_file(relative_path, content) if file_type == 'py' else {
            'path': relative_path, 'type': file_type, 'full_content': content,
            'start_lineno': 1, 'end_lineno': len(content.splitlines()), 'docstring': None
        }
        
        # This function needs a write-enabled cursor
        write_conn = manager._get_write_connection()
        if not write_conn: return json.dumps({'status': 'error', 'message': 'Could not get write-enabled DB connection.'})
        
        _insert_file_data(write_conn.cursor(), file_details)
        write_conn.commit()

        return json.dumps({'status': 'success', 'message': f"DB sync successful for '{relative_path}'."})
    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'DB sync failed for {relative_path}: {e}'})

def _sync_db_after_file_delete(relative_path: str) -> str:
    """
    (Internal) Updates the DB after a file is deleted. Uses a WRITE connection.
    """
    manager = _CodebaseManager()
    # The original DELETE FROM files is a write operation.
    manager._execute_write_query("DELETE FROM files WHERE path = ?", (relative_path,))
    # We can add more specific deletions for other tables if needed.
    return json.dumps({'status': 'success', 'message': f"DB record for '{relative_path}' deleted."})


def _sync_db_after_file_move(old_relative_path: str, new_relative_path: str) -> str:
    """
    (Internal) Updates the DB after a file is moved. Uses a WRITE connection.
    """
    delete_status = json.loads(_sync_db_after_file_delete(old_relative_path))
    refresh_status = json.loads(_sync_db_after_file_creation(new_relative_path))
    return json.dumps({
        'delete_old_record': delete_status,
        'refresh_new_record': refresh_status
    })

def _refresh_file_representation(file_path: str) -> str:
    """
    (Low-Cost) Updates the database representation for a single file that has been changed.

    This tool removes the old database entry and re-parses the live file to insert
    the new, correct representation.
    """

    project_root = _get_project_root()
    if not project_root:
        return json.dumps({'status': 'error', 'message': 'Security Error: Project root not configured.'})
    
    # Create the full, absolute path before any checks or operations.
    full_file_path = os.path.abspath(os.path.join(project_root, file_path))

    if not _is_path_safe(full_file_path):
        return json.dumps({'status': 'error', 'message': 'Security Error: Path is outside the allowed project directory.'})

    manager = _CodebaseManager()
    conn = manager._get_write_connection()
    if not conn:
        return json.dumps({'status': 'error', 'message': 'Database connection not available.'})

    if not os.path.exists(file_path):
        return json.dumps({'status': 'error', 'message': f'File not found: {file_path}'})

    project_root = _get_project_root()
    if not project_root:
        return json.dumps({'status': 'error', 'message': 'Project root could not be determined to calculate relative path.'})

    relative_path = os.path.relpath(file_path, project_root).replace("\\", "/")

    try:
        cursor = conn.cursor()
        cursor.execute('BEGIN')
        cursor.execute('DELETE FROM files WHERE path = ?', (relative_path,))

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        _, ext = os.path.splitext(file_path)
        file_type = ext[1:] or 'text'

        if file_type == 'py':
            file_details = _parse_python_file(relative_path, content)
        else:
            file_details = {
                'path': relative_path, 
                'type': file_type, 
                'full_content': content,
                'start_lineno': 1,
                'end_lineno': len(content.splitlines()),
                'docstring': None
            }

        _insert_file_data(cursor, file_details)
        conn.commit()
        return json.dumps({'status': 'success', 'message': f"Database representation for '{relative_path}' updated successfully."})
    except Exception as e:
        if conn:
            conn.rollback()
        return json.dumps({'status': 'error', 'message': f'An error occurred during refresh for {relative_path}: {e}'})

# --- PUBLIC-FACING TOOLS ---

def apply_code_modification(file_path: str, target_identifier: str, new_code: str) -> str:
    """
    (High-Cost) Modifies a Python file by replacing a function or class with new code.

    This tool operates directly on the file system. It parses the file into an
    Abstract Syntax Tree (AST), finds the specified target node (class, function, or method),
    and replaces it with the new code provided. After successfully modifying the file,
    it automatically updates the internal project database to reflect the changes.

    @param file_path (string): The path to the Python file to modify. REQUIRED.
    @param target_identifier (string): The identifier of the code to replace (e.g., "MyClass" or "MyClass.my_method"). REQUIRED.
    @param new_code (string): The new Python code block to insert. The code must be a valid, complete definition for a class, function, or method. REQUIRED.

    Returns:
        string: A JSON string with the status of the operation (success, warning, or error) and a descriptive message.
    """

    project_root = _get_project_root()
    if not project_root:
        return json.dumps({'status': 'error', 'message': 'Security Error: Project root not configured.'})
    
    # Create the full, absolute path before any checks or operations.
    full_file_path = os.path.abspath(os.path.join(project_root, file_path))

    if not _is_path_safe(full_file_path):
        return json.dumps({'status': 'error', 'message': 'Security Error: Path is outside the allowed project directory.'})
    if not os.path.exists(full_file_path):
        return json.dumps({'status': 'error', 'message': f'File not found: {file_path}'})
    try:
        ast.parse(new_code)
    except SyntaxError as e:
        return json.dumps({'status': 'error', 'message': f'Syntax error in new_code: {e}'})
    try:
        with open(full_file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        original_tree = ast.parse(source_code)
    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'Failed to read or parse {file_path}: {e}'})

    transformer = _CodeTransformer(target_identifier, new_code)
    new_tree = transformer.visit(original_tree)

    if not transformer.target_found_and_replaced:
        return json.dumps({'status': 'error', 'message': f"Target '{target_identifier}' not found in {file_path}."})

    try:
        modified_code = ast.unparse(new_tree)
    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'AST unparsing failed: {e}'})

    original_lines = [line.strip() for line in source_code.strip().splitlines()]
    modified_lines = [line.strip() for line in modified_code.strip().splitlines()]

    if original_lines == modified_lines:
        return json.dumps({
            'status': 'error',
            'message': 'Internal Tool Error: Code modification resulted in no changes. The AST transformation failed silently.'
        })
    try:
        with open(full_file_path, 'w', encoding='utf-8') as f:
            f.write(modified_code)
    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'Failed to write modified code to {file_path}: {e}'})

    refresh_status_json = refresh_status_json = _sync_db_after_file_creation(file_path)
    status_data = json.loads(refresh_status_json)

    if status_data['status'] == 'success':
        return json.dumps({
            'status': 'success',
            'message': f"Successfully modified '{file_path}' and updated the project database."
        }, indent=2)
    else:
        return json.dumps({
            'status': 'warning',
            'message': f"Successfully modified '{file_path}', but failed to update the project database. Reason: {status_data.get('message', 'Unknown')}"
        }, indent=2)


def find_and_replace_code_block(file_path: str, start_line_content: str, end_line_content: str, new_code_block: str) -> str:
    """
    (Medium-Cost) Finds a code block by its start and end lines and replaces it.

    This tool reads a file and searches for the first line that exactly matches 'start_line_content'.
    From that point, it searches for the first subsequent line that exactly matches 'end_line_content'.
    The entire block, including the start and end lines, is then replaced with the 'new_code_block'.
    After a successful replacement, the tool automatically updates the project database.

    @param file_path (string): The path to the file to modify. REQUIRED.
    @param start_line_content (string): The exact text of the line where the block to be replaced begins. REQUIRED.
    @param end_line_content (string): The exact text of the line where the block to be replaced ends. REQUIRED.
    @param new_code_block (string): The new code to insert in place of the old block. REQUIRED.

    Returns:
        string: A JSON string with the status of the operation (success, warning, or error) and a descriptive message.
    """

    project_root = _get_project_root()
    if not project_root:
        return json.dumps({'status': 'error', 'message': 'Security Error: Project root not configured.'})
    
    # Create the full, absolute path before any checks or operations.
    full_file_path = os.path.abspath(os.path.join(project_root, file_path))

    if not _is_path_safe(full_file_path):
        return json.dumps({'status': 'error', 'message': 'Security Error: Path is outside the allowed project directory.'})
    if not os.path.exists(full_file_path):
        return json.dumps({'status': 'error', 'message': f'File not found: {file_path}.'})

    try:
        with open(full_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        start_index = next((i for i, line in enumerate(lines) if start_line_content.strip() == line.strip()), -1)
        if start_index == -1:
            return json.dumps({'status': 'error', 'message': f'Could not find the start line: "{start_line_content}"'})

        end_index = next((i for i, line in enumerate(lines[start_index:], start=start_index) if end_line_content.strip() == line.strip()), -1)
        if end_index == -1:
            return json.dumps({'status': 'error', 'message': f'Could not find the end line: "{end_line_content}" after the start line.'})

        new_lines = lines[:start_index]
        new_lines.append(new_code_block + ('\n' if not new_code_block.endswith('\n') else ''))
        new_lines.extend(lines[end_index + 1:])

        with open(full_file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'An unexpected error occurred during find and replace: {e}'})

    refresh_status_json = _sync_db_after_file_creation(file_path)
    status_data = json.loads(refresh_status_json)

    if status_data['status'] == 'success':
        return json.dumps({'status': 'success', 'message': f"Successfully replaced code block in '{file_path}' and updated the database."}, indent=2)
    else:
        return json.dumps({'status': 'warning', 'message': f"Successfully replaced code block in '{file_path}', but failed to update the database. Reason: {status_data.get('message', 'Unknown')}"}, indent=2)



def create_or_update_file_safely(file_path: str, content: str, overwrite: bool = False) -> str:
    """
    (High-Cost) Safely creates a new file or updates an existing one with provided content.

    This tool writes content to a specified file path. It includes several safety features:
    - It checks that the path is within the allowed project directory.
    - By default, it prevents overwriting existing files unless 'overwrite' is set to True.
    - If the file is a Python file (.py), it validates the syntax of the content before writing.
    - On success, it automatically creates or updates the file's representation in the project database.

    @param file_path (string): The project-relative path to the file to create or update. REQUIRED.
    @param content (string): The full content to write to the file. REQUIRED.
    @param overwrite (boolean): Set to True to allow overwriting an existing file. Optional. Defaults to False.

    Returns:
        string: A JSON string with the status of the operation (success, warning, or error) and a descriptive message.
    """

    project_root = _get_project_root()
    if not project_root:
        return json.dumps({'status': 'error', 'message': 'Security Error: Project root not configured.'})
    
    # Create the full, absolute path before any checks or operations.
    full_file_path = os.path.abspath(os.path.join(project_root, file_path))

    if not _is_path_safe(full_file_path):
        return json.dumps({'status': 'error', 'message': 'Security Error: Path is outside the allowed project directory.'})

    if os.path.exists(full_file_path) and not overwrite:
        return json.dumps({'status': 'error', 'message': f'File "{file_path}" already exists. Set overwrite=True to allow modification.'})

    if file_path.endswith('.py'):
        try:
            ast.parse(content)
        except SyntaxError as e:
            return json.dumps({'status': 'error', 'message': f'Syntax error in new Python code: {e}'})

    try:
        os.makedirs(os.path.dirname(full_file_path), exist_ok=True)
        with open(full_file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'An unexpected error occurred during file write: {e}'})

    refresh_status_json = _sync_db_after_file_creation(file_path)
    status_data = json.loads(refresh_status_json)

    if status_data['status'] == 'success':
        return json.dumps({'status': 'success', 'message': f"Successfully wrote to '{file_path}' and updated the project database."})
    else:
        return json.dumps({'status': 'warning', 'message': f"Successfully wrote to '{file_path}', but failed to update the project database. Reason: {status_data.get('message', 'Unknown')}"})
