# my_tools/code_searcher.py

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
            # Connect in read-only mode for safety. URI=True allows mode=ro.
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

    def _internal_search_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = params.get("search_query")
        file_path = params.get("file_path")
        case_sensitive = params.get("case_sensitive", False)

        # This check is now in the public function, but internal check is good practice
        if not query:
            return {"error": "Missing 'search_query' parameter.", "status": "error_missing_param"}

        # NOTE: Using LIKE is slow for large datasets. A real-world production system
        # would use SQLite's FTS5 (Full-Text Search) extension for this.
        # This implementation is for correctness and simplicity based on the original tool.
        sql = "SELECT path, full_content FROM files WHERE full_content IS NOT NULL"
        sql_params = []
        if file_path:
            sql += " AND path = ?"
            sql_params.append(file_path)

        cursor = self._execute_query(sql, tuple(sql_params))
        if not cursor:
            return {"error": "Database query failed.", "status": "error_db_query"}

        results = []
        search_term = query if case_sensitive else query.lower()

        all_rows = cursor.fetchall()
        # If a file_path was specified but we got no rows, the file doesn't exist or has no content.
        if file_path and not all_rows:
            return {"file_path": file_path, "error": "File not found or has no searchable content.", "status": "error_not_found"}

        for row in all_rows:
            content, current_fp = row["full_content"], row["path"]
            if not isinstance(content, str):
                continue

            lines = content.splitlines()
            for i, line_text in enumerate(lines):
                line_to_search = line_text if case_sensitive else line_text.lower()
                if search_term in line_to_search:
                    results.append({
                        "file_path": current_fp,
                        "line_number": i + 1,
                        "line_content": line_text.strip()
                    })

        return {
            "query": query,
            "file_path_filter": file_path,
            "case_sensitive": case_sensitive,
            "results": results,
            "status": "success"
        }

# --- Public Tool Function ---
def search_code(
    search_query: str,
    file_path: Optional[str] = None,
    case_sensitive: bool = False
) -> str:
    """
    Performs a text search across file contents, returning all matching lines.

    This tool is ideal for finding specific strings, keywords, function calls, or comments
    across the codebase. It can search within all files or be restricted to a single file.

    @param search_query (string): The text string to search for. This is a REQUIRED parameter.
    @param file_path (string): The relative path to a specific file to limit the search to. If omitted, all files will be searched. Example: "src/main.py".
    @param case_sensitive (boolean): Specifies if the search should be case-sensitive. Defaults to False (case-insensitive).
    """
    manager = _CodebaseManager()
    if not manager.conn:
        return json.dumps({"error": "Database connection not available. Please run the context creation script.", "status": "error_no_db"})

    if not search_query:
        return json.dumps({"error": "Missing required parameter 'search_query'.", "status": "error_missing_param"})

    params = {
        "search_query": search_query,
        "file_path": file_path,
        "case_sensitive": case_sensitive
    }
    result_dict = manager._internal_search_code(params)

    return json.dumps(result_dict, indent=2)

if __name__ == '__main__':
    print("--- Testing CodeSearcher Tool ---")
    db_path = os.environ.get("CODEBASE_DB_PATH", "project_context.db")
    if not os.path.exists(db_path):
        print(f"\nERROR: Database file '{db_path}' not found.")
        print("Please run the database creation script first.")
    else:
        print(f"Using existing database: '{db_path}'")
        test_file = "my_tools/codebase_query_tool.py"

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM files WHERE path=?", (test_file,))
        file_exists = cursor.fetchone()[0] > 0
        conn.close()

        if not file_exists:
             print(f"\nWARNING: The test file '{test_file}' was not found in your database.")
             print("Tests may fail. Please edit the 'test_file' variable.")

        test_calls = [
            # 1. Broad, case-insensitive search across all files
            {"search_query": "database"},
            # 2. Broad, case-sensitive search across all files
            {"search_query": "CodebaseManager", "case_sensitive": True},
            # 3. Focused, case-insensitive search in a specific file
            {"search_query": "cursor", "file_path": test_file},
            # 4. Focused, case-sensitive search for a term that might not exist in that case
            {"search_query": "CURSOR", "file_path": test_file, "case_sensitive": True},
            # 5. Search in a file that does not exist
            {"search_query": "test", "file_path": "non_existent_file.py"},
            # 6. Search for a query that likely won't be found
            {"search_query": "supercalifragilisticexpialidocious"},
            # 7. Test missing search_query parameter
            {"search_query": ""},
        ]

        for i, params in enumerate(test_calls):
            print(f"\n--- Test Call {i+1}: {params} ---")
            result_json_str = search_code(**params)

            try:
                parsed_result = json.loads(result_json_str)
                print(json.dumps(parsed_result, indent=2))
            except json.JSONDecodeError:
                print("ERROR: Result is not valid JSON!")
                print(result_json_str)
