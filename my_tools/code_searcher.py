# my_tools/code_searcher.py

import json
from typing import Optional, Dict, Any

from my_tools.codebase_manager import _CodebaseManager

# --- Helper Function (Business Logic) ---

def _helper_search_code(manager: _CodebaseManager, search_query: str, file_path: Optional[str], case_sensitive: bool) -> Dict[str, Any]:
    """
    Performs the core logic of fetching file content and searching for a term.
    """
    # NOTE: Using Python to search line-by-line is not the most performant method for large
    # codebases. A production system would likely use a full-text search engine like SQLite's FTS5.
    # This implementation maintains the original tool's functionality.

    sql = "SELECT path, full_content FROM files WHERE full_content IS NOT NULL"
    sql_params = []
    if file_path:
        sql += " AND path = ?"
        sql_params.append(file_path)

    cursor = manager._execute_read_query(sql, tuple(sql_params))
    if not cursor:
        return {"error": "Database query failed. The database might be unavailable.", "status": "error_db_query"}

    results = []
    search_term = search_query if case_sensitive else search_query.lower()

    all_rows = cursor.fetchall()
    # If a file_path was specified but we got no rows, the file doesn't exist or has no searchable content.
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
        "query": search_query,
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
    if not search_query:
        return json.dumps({"error": "Missing required parameter 'search_query'.", "status": "error_missing_param"}, indent=2)

    manager = _CodebaseManager()
    result_dict = _helper_search_code(manager, search_query, file_path, case_sensitive)

    return json.dumps(result_dict, indent=2)

if __name__ == '__main__':
    import os
    print("--- Testing CodeSearcher Tool ---")

    workspace_dir = os.environ.get("CODEBASE_DB_PATH", ".")
    db_path = os.path.join(workspace_dir, "project_context.db")

    if not os.path.exists(db_path):
        print(f"\nERROR: Database file '{os.path.abspath(db_path)}' not found.")
        print("Please run the database creation script first.")
    else:
        print(f"Using database found at: '{os.path.abspath(db_path)}'")

        # Use a file that is known to be in the database from previous refactoring steps.
        test_file = "my_tools/python_analyzer.py"

        test_calls = [
            # 1. Broad, case-insensitive search for a common term
            {"search_query": "manager"},
            # 2. Broad, case-sensitive search
            {"search_query": "_CodebaseManager", "case_sensitive": True},
            # 3. Focused, case-insensitive search in a specific file
            {"search_query": "cursor", "file_path": test_file},
            # 4. Focused, case-sensitive search for a term that won't be found in that case
            {"search_query": "CURSOR", "file_path": test_file, "case_sensitive": True},
            # 5. Search in a file that does not exist
            {"search_query": "test", "file_path": "non_existent_file.py"},
            # 6. Search for a query that likely won't be found
            {"search_query": "a_very_unlikely_search_term_xyz123"},
            # 7. Test missing search_query parameter
            {"search_query": ""},
        ]

        for i, params in enumerate(test_calls):
            print(f"\n--- Test Call {i+1}: {params} ---")
            result_json_str = search_code(**params)

            try:
                # Truncate long results for cleaner test output
                parsed_result = json.loads(result_json_str)
                if parsed_result.get("status") == "success" and "results" in parsed_result:
                    if len(parsed_result["results"]) > 5:
                        parsed_result["results"] = parsed_result["results"][:5] + [{"...": "truncated for display"}]
                print(json.dumps(parsed_result, indent=2))
            except json.JSONDecodeError:
                print("ERROR: Result is not valid JSON!")
                print(result_json_str)
