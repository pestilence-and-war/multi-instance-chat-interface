# my_tools/parsing_utils.py
import ast
import sys

def _get_source_segment(source_code, node):
    """A compatibility wrapper for ast.get_source_segment."""
    if sys.version_info >= (3, 8):
        return ast.get_source_segment(source_code, node)
    else:
        # Basic fallback for older Python versions.
        lines = source_code.splitlines()
        start = node.lineno - 1
        end = node.end_lineno if hasattr(node, 'end_lineno') else start
        return '\n'.join(lines[start:end])

def _parse_python_file(filepath: str, content: str) -> dict:
    """
    Parses the content of a Python file and extracts structured data.

    Args:
        filepath (str): The path of the file (for context).
        content (str): The source code to parse.

    Returns:
        A dictionary containing the file's structure.
    """
    file_data = {"path": filepath, "type": "python", "imports": [], "classes": {}, "functions": {}, "full_content": content}
    try:
        tree = ast.parse(content)
        # Add parent pointers to each node, which is required by some parsing logic.
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                child.parent = node
        file_data["docstring"] = ast.get_docstring(tree)
    except SyntaxError as e:
        file_data.update({"type": "python_error", "error": str(e)})
        return file_data

    # Extract top-level constructs
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            file_data["imports"].append(ast.unparse(node).strip())
        elif isinstance(node, ast.FunctionDef):
            func_name = node.name
            file_data["functions"][func_name] = {
                "name": func_name,
                "signature": ast.unparse(node.args),
                "docstring": ast.get_docstring(node),
                "source_code": _get_source_segment(content, node),
                "start_lineno": node.lineno,
                "end_lineno": node.end_lineno
            }
        elif isinstance(node, ast.ClassDef):
            class_name = node.name
            file_data["classes"][class_name] = {
                "name": class_name,
                "docstring": ast.get_docstring(node),
                "source_code": _get_source_segment(content, node),
                "start_lineno": node.lineno,
                "end_lineno": node.end_lineno,
                "methods": {}
            }
            # Extract methods within the class
            for sub_node in node.body:
                if isinstance(sub_node, ast.FunctionDef):
                    method_name = sub_node.name
                    file_data["classes"][class_name]["methods"][method_name] = {
                        "name": method_name,
                        "signature": ast.unparse(sub_node.args),
                        "docstring": ast.get_docstring(sub_node),
                        "source_code": _get_source_segment(content, sub_node),
                        "start_lineno": sub_node.lineno,
                        "end_lineno": sub_node.end_lineno
                    }
    return file_data

def _insert_file_data(cursor, file_details: dict):
    """
    Inserts structured file data into the database.

    Args:
        cursor: A database cursor object.
        file_details (dict): The structured data from _parse_python_file.
    """
    cursor.execute('INSERT INTO files (path, type, full_content, docstring, start_lineno, end_lineno) VALUES (?, ?, ?, ?, ?, ?)',
                   (file_details['path'], file_details['type'], file_details.get('full_content'), file_details.get('docstring'), 1, len(file_details.get('full_content', '').splitlines())))
    file_id = cursor.lastrowid

    if file_details['type'] == 'python':
        for imp in file_details.get('imports', []):
            cursor.execute('INSERT INTO python_imports (file_id, import_statement) VALUES (?, ?)', (file_id, imp))
        for class_data in file_details.get('classes', {}).values():
            cursor.execute('INSERT INTO python_classes (file_id, name, docstring, source_code, start_lineno, end_lineno) VALUES (?, ?, ?, ?, ?, ?)',
                           (file_id, class_data['name'], class_data['docstring'], class_data['source_code'], class_data['start_lineno'], class_data['end_lineno']))
            class_id = cursor.lastrowid
            for method_data in class_data.get('methods', {}).values():
                cursor.execute('INSERT INTO python_functions (file_id, class_id, name, signature, docstring, source_code, start_lineno, end_lineno) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                               (file_id, class_id, method_data['name'], method_data['signature'], method_data['docstring'], method_data['source_code'], method_data['start_lineno'], method_data['end_lineno']))
        for func_data in file_details.get('functions', {}).values():
            cursor.execute('INSERT INTO python_functions (file_id, name, signature, docstring, source_code, start_lineno, end_lineno) VALUES (?, ?, ?, ?, ?, ?, ?)',
                           (file_id, func_data['name'], func_data['signature'], func_data['docstring'], func_data['source_code'], func_data['start_lineno'], func_data['end_lineno']))
