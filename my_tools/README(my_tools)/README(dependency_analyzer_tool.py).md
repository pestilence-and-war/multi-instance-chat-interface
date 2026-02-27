# Dependency Analyzer Tool (`dependency_analyzer_tool.py`)

## What It Does
Inspects the project's dependency manifest files (`requirements.txt` for Python, `package.json` for Node.js) to identify outdated packages or known security vulnerabilities.

## Functions

### `analyze_dependencies(project_path='.')`
Scans the project root for manifest files and runs security audits.
-   **Python**: Uses `safety` to check for vulnerable packages in `requirements.txt`.
-   **Node.js**: Runs `npm audit` to identify vulnerabilities in the `node_modules` tree.

## Dependencies
-   **Python**: `pip install safety`
-   **Node.js**: `npm` must be installed.
