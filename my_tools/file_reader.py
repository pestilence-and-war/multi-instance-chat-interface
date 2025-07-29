# my_tools/file_reader.py

import json
import os
import sqlite3
from typing import Dict, Any, Optional

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

# --- Public Tool Functions ---

def get_file_content(file_path: str) -> str:
    """
    (High-Cost) Retrieves the full raw content of a specific file.

    This tool should be used sparingly, only when a complete understanding of the file is necessary.
    For more targeted needs, prefer 'get_code_block' or 'get_line_content'.

    @param file_path (string): The full path to the file you want to read.
    """
    manager = _CodebaseManager()
    if not manager.conn:
        return json.dumps({"error": "Database connection not available.", "status": "error_no_db"})

    if not file_path:
        return json.dumps({"error": "Missing 'file_path' parameter.", "status": "error_missing_param"})

    cursor = manager._execute_query("SELECT full_content, message, error FROM files WHERE path = ?", (file_path,))
    if not cursor:
        return json.dumps({"error": "Database query failed.", "status": "error_db_query"})

    row = cursor.fetchone()
    if not row:
        return json.dumps({"file_path": file_path, "error": "File not found in codebase.", "status": "error_not_found"})

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
    (Low-Cost) Extracts a specific multi-line block of code from a file.

    This is the preferred tool for reading targeted sections of a file, such as functions or classes.

    @param file_path (string): The path to the file.
    @param start_line (integer): The starting line number of the block to retrieve (inclusive).
    @param end_line (integer): The ending line number of the block to retrieve (inclusive).
    """
    manager = _CodebaseManager()
    if not manager.conn:
        return json.dumps({"error": "Database connection not available.", "status": "error_no_db"})

    if not file_path:
        return json.dumps({"error": "Missing 'file_path' parameter.", "status": "error_missing_param"})
    if not (isinstance(start_line, int) and isinstance(end_line, int) and 1 <= start_line <= end_line):
        return json.dumps({"file_path": file_path, "error": "Invalid 'start_line' or 'end_line'. Must be positive integers with start <= end.", "status": "error_invalid_input"})

    # This operation still needs the full content to slice, but the key difference
    # is the reduced output size and the explicit user intent for a smaller section.
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
    manager = _CodebaseManager()
    if not manager.conn:
        return json.dumps({"error": "Database connection not available.", "status": "error_no_db"})

    # This can be optimized by using get_code_block to fetch just one line
    return get_code_block(file_path=file_path, start_line=line_number, end_line=line_number)

def get_file_metadata(file_path: str) -> str:
    """
    (Low-Cost) Provides a summary of a file's metadata from the project database.

    This includes file type, line counts, and summaries of contained objects (like classes and functions).

    @param file_path (string): The path to the file.
    """
    manager = _CodebaseManager()
    if not manager.conn:
        return json.dumps({"error": "Database connection not available.", "status": "error_no_db"})

    if not file_path:
        return json.dumps({"error": "Missing 'file_path' parameter.", "status": "error_missing_param"})

    file_id = manager._get_file_id(file_path)
    if not file_id:
        return json.dumps({"file_path": file_path, "error": "File not found.", "status": "error_not_found"})

    query = """
        SELECT
            f.path, f.type, f.start_lineno, f.end_lineno, f.message, f.error,
            (SELECT COUNT(*) FROM python_imports WHERE file_id = f.id) as import_count,
            (SELECT COUNT(*) FROM python_classes WHERE file_id = f.id) as class_summary_count,
            (SELECT COUNT(*) FROM python_functions WHERE file_id = f.id AND class_id IS NULL) as function_summary_count,
            (SELECT COUNT(*) FROM html_elements WHERE file_id = f.id) as html_element_count,
            (SELECT COUNT(*) FROM css_rules WHERE file_id = f.id) as css_rule_count,
            (SELECT COUNT(*) FROM javascript_constructs WHERE file_id = f.id) as javascript_construct_count
        FROM
            files f
        WHERE
            f.id = ?
    """
    cursor = manager._execute_query(query, (file_id,))
    if not cursor:
        return json.dumps({"error": "DB query failed for metadata.", "status": "error_db_query"})

    row = cursor.fetchone()
    if not row:
        return json.dumps({"file_path": file_path, "error": "File not found after getting ID.", "status": "error_not_found"})

    return json.dumps({"file_path": file_path, "metadata": dict(row), "status": "success"}, indent=2)

if __name__ == '__main__':
    print("--- Testing Refactored file_reader Tool ---")
    db_path = os.environ.get("CODEBASE_DB_PATH", "project_context.db")
    if not os.path.exists(db_path):
        print(f"\nERROR: Database file '{db_path}' not found.")
    else:
        print(f"Using existing database: '{db_path}'")
        # Use a file that is likely to exist in the project for testing
        test_file = "my_tools/file_reader.py" 

        print("\n--- Test Call 1: get_file_content ---")
        print(get_file_content(file_path=test_file))

        print("\n--- Test Call 2: get_file_metadata ---")
        print(get_file_metadata(file_path=test_file))

        print("\n--- Test Call 3: get_line_content ---")
        print(get_line_content(file_path=test_file, line_number=15))

        print("\n--- Test Call 4: get_code_block ---")
        print(get_code_block(file_path=test_file, start_line=10, end_line=20))
