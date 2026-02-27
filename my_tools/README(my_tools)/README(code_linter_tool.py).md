# Code Linter Tool (`code_linter_tool.py`)

## What It Does
This tool runs static analysis on source code files to identify potential bugs, stylistic issues, and formatting errors.

-   **Python**: Uses `ruff` for extremely fast linting and formatting checks.
-   **JavaScript/TypeScript**: Uses `eslint` to identify common errors and enforce style rules.

## Functions

### `lint_code(file_path)`
Runs the appropriate linter based on the file extension.
-   **Parameters**:
    -   `file_path` (string): The path to the file to lint.
-   **Returns**: A JSON string containing the linter used and a list of identified issues.

## Dependencies
-   **Python**: `pip install ruff`
-   **JavaScript**: `npm install eslint` (local or global)
