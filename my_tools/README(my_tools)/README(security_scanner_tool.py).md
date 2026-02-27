# Security Scanner Tool (`security_scanner_tool.py`)

## What It Does
Performs automated security audits on code and dependencies to identify vulnerabilities and risks.

## Functions

### `run_security_audit(path)`
Runs a multi-stage security audit on the specified file or directory.
-   **Python Audit**: Uses `bandit` to find common security issues in Python source code.
-   **Dependency Audit**: Uses `safety` to check `requirements.txt` against a database of known vulnerabilities.

## Dependencies
-   `pip install bandit safety`
