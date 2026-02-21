# my_tools/file_reader.py

import json
from typing import Optional

from my_tools.codebase_manager import _CodebaseManager

# --- Helper Functions (Business Logic) ---

def _helper_get_file_id(manager: _CodebaseManager, file_path: str) -> Optional[int]:
    """Given a file path, queries the DB for its unique ID."""
    cursor = manager._execute_read_query("SELECT id FROM files WHERE path = ?", (file_path,))
    if cursor:
        row = cursor.fetchone()
        return row['id'] if row else None
    return None

# --- Public Tool Functions ---

def get_file_content(file_path: str) -> str:
    """
    (High-Cost) Retrieves the full raw content of a specific file.

    This tool should be used sparingly, only when a complete understanding of the file is necessary.
    For more targeted needs, prefer 'get_code_block' or 'get_line_content'.

    @param file_path (string): The full path to the file you want to read.
    """
    if not file_path:
        return json.dumps({"error": "Missing 'file_path' parameter.", "status": "error_missing_param"}, indent=2)

    manager = _CodebaseManager()
    cursor = manager._execute_read_query("SELECT full_content, message, error FROM files WHERE path = ?", (file_path,))
    if not cursor:
        return json.dumps({"error": "Database query failed.", "status": "error_db_query"}, indent=2)

    row = cursor.fetchone()
    if not row:
        return json.dumps({"file_path": file_path, "error": "File not found in codebase.", "status": "error_not_found"}, indent=2)

    content = row["full_content"]
    if content is not None:
        return json.dumps({"file_path": file_path, "content": content, "status": "success"}, indent=2)
    else:
        message = row["message"] or "Content not available or file is binary/managed."
        if row["error"]:
            message = f"Error state for file: {row['error']}"
        return json.dumps({"file_path": file_path, "error": message, "status": "no_content"}, indent=2)

def get_code_block(file_path: str, start_line: int, end_line: int) -> str:
    """
    (Mid-Cost) Reads a specific block of text. 
    
    Use this ONLY after using structure tools (metadata, call graph) to locate the exact lines.
    Do not use this for exploring; use it for verification.

    @param file_path (string): The path to the file.
    @param start_line (integer): The starting line number of the block to retrieve (inclusive).
    @param end_line (integer): The ending line number of the block to retrieve (inclusive).
    """
    if not file_path:
        return json.dumps({"error": "Missing 'file_path' parameter.", "status": "error_missing_param"}, indent=2)
    if not (isinstance(start_line, int) and isinstance(end_line, int) and 1 <= start_line <= end_line):
        return json.dumps({"file_path": file_path, "error": "Invalid 'start_line' or 'end_line'. Must be positive integers with start <= end.", "status": "error_invalid_input"}, indent=2)

    content_response_str = get_file_content(file_path)
    content_response = json.loads(content_response_str)

    if content_response.get("status") != "success":
        return content_response_str

    content = content_response.get("content", "")
    lines = content.splitlines(keepends=True)
    if start_line <= end_line <= len(lines):
        code_block = "".join(lines[start_line - 1 : end_line])
        return json.dumps({"file_path": file_path, "start_line": start_line, "end_line": end_line, "code_block": code_block, "status": "success"}, indent=2)
    else:
        return json.dumps({"file_path": file_path, "start_line": start_line, "end_line": end_line, "error": "Line numbers out of bounds.", "status": "error_out_of_bounds"}, indent=2)

def get_line_content(file_path: str, line_number: int) -> str:
    """
    (Low-Cost) Retrieves a single line of content from a file.

    Useful for examining a specific line of code or text.

    @param file_path (string): The path to the file.
    @param line_number (integer): The specific line number to retrieve.
    """
    return get_code_block(file_path=file_path, start_line=line_number, end_line=line_number)

def get_file_metadata(file_path: str) -> str:
    """
    (Low-Cost) Returns file stats and a PREVIEW of the code structure (Function/Class names).
    
    Use this tool SECOND, after identifying interesting files in the directory tree.
    It tells you WHAT is in the file (e.g., specific function names, API routes, class definitions)
    without the high token cost of reading the actual code. 
    
    @param file_path (string): The path to the file.
    """
    if not file_path:
        return json.dumps({"error": "Missing 'file_path' parameter.", "status": "error_missing_param"}, indent=2)

    manager = _CodebaseManager()
    file_id = _helper_get_file_id(manager, file_path)
    if not file_id:
        return json.dumps({"file_path": file_path, "error": "File not found.", "status": "error_not_found"}, indent=2)

    # 1. Base Metadata Query (Counts)
    query = """
        SELECT
            f.path, f.type, f.start_lineno, f.end_lineno, f.message, f.error,
            (SELECT COUNT(*) FROM python_imports WHERE file_id = f.id) as import_count,
            (SELECT COUNT(*) FROM python_classes WHERE file_id = f.id) as class_summary_count,
            (SELECT COUNT(*) FROM python_functions WHERE file_id = f.id) as function_summary_count, -- Removed 'AND class_id IS NULL' to count all
            (SELECT COUNT(*) FROM html_elements WHERE file_id = f.id) as html_element_count,
            (SELECT COUNT(*) FROM css_rules WHERE file_id = f.id) as css_rule_count,
            (SELECT COUNT(*) FROM javascript_constructs WHERE file_id = f.id) as javascript_construct_count
        FROM
            files f
        WHERE
            f.id = ?
    """
    cursor = manager._execute_read_query(query, (file_id,))
    if not cursor:
        return json.dumps({"error": "DB query failed for metadata.", "status": "error_db_query"}, indent=2)

    row = cursor.fetchone()
    if not row:
        return json.dumps({"file_path": file_path, "error": "File not found after getting ID.", "status": "error_not_found"}, indent=2)

    metadata = dict(row)

    # 2. Semantic Preview (Names of Symbols)
    if metadata.get("type") == "python":
        try:
            # --- FIXED: Fetch ALL functions and join with classes to get methods ---
            # We select the function name, its decorators, and the parent class name (if any)
            func_query = """
                SELECT pf.name, pf.decorators, pc.name as class_name 
                FROM python_functions pf
                LEFT JOIN python_classes pc ON pf.class_id = pc.id
                WHERE pf.file_id = ?
            """
            func_cursor = manager._execute_read_query(func_query, (file_id,))
            
            functions = []
            if func_cursor:
                for f in func_cursor.fetchall():
                    # Format: "MyClass.my_method" or just "my_function"
                    display_name = f"{f['class_name']}.{f['name']}" if f['class_name'] else f['name']
                    
                    # Append decorators if they exist (crucial for Flask routes)
                    if f['decorators']:
                        display_name += f" [{f['decorators']}]"
                    
                    functions.append(display_name)

            # Fetch Classes
            class_query = "SELECT name FROM python_classes WHERE file_id = ?"
            class_cursor = manager._execute_read_query(class_query, (file_id,))
            classes = class_cursor.fetchall() if class_cursor else []

            metadata["structure_preview"] = {
                "functions": functions, # Now contains methods like 'ChatInstance.register_tools_from_module'
                "classes": [c["name"] for c in classes]
            }
        except Exception as e:
            metadata["structure_preview_error"] = str(e)

    return json.dumps({"file_path": file_path, "metadata": metadata, "status": "success"}, indent=2)

if __name__ == '__main__':
    import os
    print("--- Testing file_reader Tool ---")
    workspace_dir = os.environ.get("CODEBASE_DB_PATH", ".")
    db_path = os.path.join(workspace_dir, "project_context.db")

    if not os.path.exists(db_path):
        print(f"\nERROR: Database file '{os.path.abspath(db_path)}' not found.")
    else:
        print(f"Using database found at: '{os.path.abspath(db_path)}'")
        # Use a file that is likely to exist in the project for testing
        test_file = "my_tools/file_reader.py" 

        print("\n--- Test Call 1: get_file_content ---")
        content_result = json.loads(get_file_content(file_path=test_file))
        print(f"Status of get_file_content: {content_result.get('status')}")
        assert content_result.get('status') == 'success'

        print("\n--- Test Call 2: get_file_metadata (Should include structure_preview) ---")
        print(get_file_metadata(file_path=test_file))

        print("\n--- Test Call 3: get_line_content (testing line 20) ---")
        print(get_line_content(file_path=test_file, line_number=20))