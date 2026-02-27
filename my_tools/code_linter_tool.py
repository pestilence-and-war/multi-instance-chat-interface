import subprocess
import json
import os
from typing import Dict, Any

def lint_code(file_path: str) -> str:
    """
    Runs linter (ruff for Python, eslint for JavaScript) on a specific file.
    Returns a JSON string with the results.

    @param file_path (string): The path to the file to lint.
    """
    if not os.path.exists(file_path):
        return json.dumps({"status": "error", "message": f"File not found: {file_path}"})

    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if ext == '.py':
            # Run ruff
            result = subprocess.run(
                ["ruff", "check", file_path, "--format", "json"],
                capture_output=True, text=True
            )
            # Ruff exits with non-zero if it finds issues, but we want the JSON
            try:
                issues = json.loads(result.stdout)
                return json.dumps({"status": "success", "linter": "ruff", "issues": issues}, indent=2)
            except json.JSONDecodeError:
                if result.stderr:
                    return json.dumps({"status": "error", "linter": "ruff", "message": result.stderr})
                return json.dumps({"status": "success", "linter": "ruff", "issues": [], "message": "No issues found."})

        elif ext in ['.js', '.ts', '.jsx', '.tsx']:
            # Run eslint
            # Assuming eslint is in node_modules/.bin/eslint or globally
            eslint_path = os.path.join("node_modules", ".bin", "eslint")
            if not os.path.exists(eslint_path):
                eslint_path = "eslint" # Try global

            result = subprocess.run(
                [eslint_path, file_path, "--format", "json"],
                capture_output=True, text=True
            )
            try:
                issues = json.loads(result.stdout)
                return json.dumps({"status": "success", "linter": "eslint", "issues": issues}, indent=2)
            except json.JSONDecodeError:
                if result.stderr:
                    return json.dumps({"status": "error", "linter": "eslint", "message": result.stderr})
                return json.dumps({"status": "success", "linter": "eslint", "issues": [], "message": "No issues found."})

        else:
            return json.dumps({"status": "error", "message": f"Unsupported file type for linting: {ext}"})

    except Exception as e:
        return json.dumps({"status": "error", "message": f"Linter execution failed: {str(e)}"})
