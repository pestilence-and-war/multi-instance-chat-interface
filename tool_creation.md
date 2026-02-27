# How to Create a New Tool for the System

This document provides the specification and a template for creating new, functional tools that can be dynamically registered and used by the AI. Adhering to this structure is essential for ensuring your tool is discovered and executed correctly.

---
### Core Principles
---

1.  **Standard Python:** Tools are standard Python functions within a `.py` file placed in the `my_tools/` directory.
2.  **Self-Contained:** Each file should be self-contained or rely only on standard libraries or packages listed in `requirements.txt`.
3.  **Structured Docstrings:** The system parses the function's docstring to understand its purpose and parameters. **The format must be followed exactly.**
4.  **Type Hinting:** All function parameters must have Python type hints (e.g., `param: str`, `count: int`).
5.  **JSON String Output:** Every tool function **must** return a JSON formatted string. This is the standard interface for passing data and errors back to the system.
6.  **Database Access:** For tools that need to query the codebase context (files, classes, functions), use the provided `_CodebaseManager` singleton to interact with the `project_context.db` SQLite database.
7.  **Error Handling:** Never let a tool crash. Gracefully catch all potential exceptions and return a structured JSON error message.

---
### Tool File Template (`my_new_tool.py`)
---

Below is a complete template. Use the "Database-Enabled" version for tools that need codebase context, and the "Stateless" version for simpler tools.

#### Version 1: Database-Enabled Tool (for accessing project context)

```python
# my_tools/my_contextual_tool.py

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
        except sqlite3.Error:
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

# --- Public Tool Function ---
def get_file_type_example(file_path: str) -> str:
    """
    (Low-Cost) A brief description of what the tool does.

    @param file_path (string): The relative path to the file to inspect. REQUIRED.
    """
    manager = _CodebaseManager()
    if not manager.conn:
        return json.dumps({"error": "Database connection not available.", "status": "error_no_db"})

    if not file_path:
        return json.dumps({"error": "Missing 'file_path' parameter.", "status": "error_missing_param"})

    try:
        # Example logic
        result_dict = {"file_path": file_path, "status": "success"}
    except Exception as e:
        result_dict = {"error": f"An unexpected error occurred: {e}", "status": "error_unexpected"}

    return json.dumps(result_dict, indent=2)
```

#### Version 2: Stateless Tool (e.g., a calculator)

```python
# my_tools/my_simple_tool.py

import json

def simple_tool_example(text_input: str, uppercase: bool = False) -> str:
    """
    (Low-Cost) An example of a simple, stateless tool.

    @param text_input (string): The text to process. REQUIRED.
    @param uppercase (boolean): If true, converts to uppercase. Defaults to False.
    """
    if not text_input:
        return json.dumps({"error": "Missing 'text_input' parameter.", "status": "error_missing_param"})

    try:
        result = text_input.upper() if uppercase else text_input
        result_dict = {"output": result, "status": "success"}
    except Exception as e:
        result_dict = {"error": str(e), "status": "error_unexpected"}

    return json.dumps(result_dict, indent=2)
```

---
### Docstring Format Specification
---

The docstring is parsed automatically. Follow this format precisely:

```python
"""
(Cost-Hint) One-line summary.

Longer description of capabilities and usage.

@param param_name (python_type): Description. Use REQUIRED for mandatory args.
"""
```

### JSON Return Structure
All tools MUST return a JSON string with a `status` key.

-   **Success**: `{"status": "success", ...}`
-   **Error**: `{"status": "error_type", "error": "message"}`
