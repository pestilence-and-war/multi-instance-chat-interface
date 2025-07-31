### `my_tools/call_graph_analyzer.py`

#### Call Graph Analyzer Tools for AI Chat Interface

This module provides tools for analyzing the call relationships between functions within your Python codebase. These tools are invaluable for understanding code flow, identifying dependencies, and assessing the impact of potential changes. By allowing the AI to query function callers and callees, it can gain a deeper understanding of the project's architecture and assist with refactoring, debugging, or feature development.

**Purpose:** To enable AI models to analyze and understand the calling relationships (call graphs) within Python code, facilitating architectural comprehension and code modification tasks.

**Key Functions:**

1.  **`get_function_callers(file_path: str, function_name: str) -> str`**
    *   **Description:** (High-Cost) Finds all functions that call a specified function. This helps understand the impact of changing a function, as it shows all its entry points.
    *   **Parameters:**
        *   `file_path` (string): The path to the Python file where the target function is defined. (Required)
        *   `function_name` (string): The name of the target function (the "callee"). (Required)
    *   **Returns:** A string (JSON format) detailing the functions that call the specified function.

2.  **`get_function_callees(file_path: str, function_name: str) -> str`**
    *   **Description:** (High-Cost) Finds all functions that are called by a specified function. This helps understand what a function does by showing its dependencies and sub-tasks.
    *   **Parameters:**
        *   `file_path` (string): The path to the Python file where the target function is defined. (Required)
        *   `function_name` (string): The name of the target function (the "caller"). (Required)
    *   **Returns:** A string (JSON format) detailing the functions called by the specified function.

**How it Solves a Problem:**
Manually tracing function calls across a large codebase is time-consuming and error-prone. These tools allow the AI to quickly map out dependencies, identify where a function is used, or understand the sub-operations a function performs. This is critical for tasks like refactoring code, debugging issues by tracing execution paths, or ensuring that changes to one part of the system don't unintentionally break others.