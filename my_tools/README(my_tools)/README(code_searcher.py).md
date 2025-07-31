### `my_tools/code_searcher.py`

#### Code Searcher Tool for AI Chat Interface

This tool provides a powerful text search capability across your project's codebase. It allows your AI models to quickly locate specific strings, keywords, function calls, or comments within one or all files. This is essential for tasks like finding where a variable is defined, identifying all occurrences of a particular function, or locating specific pieces of text within documentation or configuration files.

**Purpose:** To enable AI models to efficiently search through the content of project files for specific text patterns, aiding in code comprehension, debugging, and information retrieval.

**Key Function:**

*   **`search_code(search_query: str, file_path: Optional[str] = None, case_sensitive: bool = False) -> str`**
    *   **Description:** Performs a text search across file contents, returning all matching lines. This tool is ideal for finding specific strings, keywords, function calls, or comments across the codebase. It can search within all files or be restricted to a single file.
    *   **Parameters:**
        *   `search_query` (string): The text string to search for. (Required)
        *   `file_path` (string, optional): The relative path to a specific file to limit the search to. If omitted, all files will be searched. Example: `"src/main.py"`.
        *   `case_sensitive` (boolean, optional): Specifies if the search should be case-sensitive. Defaults to `False` (case-insensitive).
    *   **Returns:** A string (JSON format) containing all lines that match the search query.

**How it Solves a Problem:**
Manually searching through many files for specific text is time-consuming and prone to human error, especially in large projects. This `search_code` tool allows the AI to instantly locate relevant code snippets or information, making it an indispensable asset for debugging, refactoring, understanding unfamiliar codebases, or simply finding specific references quickly.
