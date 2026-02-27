import subprocess
import json
import os

def run_security_audit(path: str) -> str:
    """
    Runs security audits on the specified path using Bandit (for Python)
    and Safety (for dependencies).

    @param path (string): The path to the directory or file to audit.
    """
    results = {"bandit": None, "safety": None}
    
    # 1. Run Bandit
    try:
        # Check if it's a python file or directory
        is_python = path.endswith('.py') or os.path.isdir(path)
        if is_python:
            # -f json for json output, -r for recursive
            cmd = ["bandit", "-r", path, "-f", "json", "-q"]
            process = subprocess.run(cmd, capture_output=True, text=True)
            try:
                results["bandit"] = json.loads(process.stdout)
            except json.JSONDecodeError:
                results["bandit"] = {"error": "Failed to parse Bandit output", "raw": process.stdout}
    except Exception as e:
        results["bandit"] = {"error": str(e)}

    # 2. Run Safety (checks requirements.txt in the path if it exists)
    try:
        req_path = os.path.join(path, "requirements.txt") if os.path.isdir(path) else None
        if req_path and os.path.exists(req_path):
            # safety check --file requirements.txt --json
            cmd = ["safety", "check", "--file", req_path, "--json"]
            process = subprocess.run(cmd, capture_output=True, text=True)
            try:
                results["safety"] = json.loads(process.stdout)
            except json.JSONDecodeError:
                 results["safety"] = {"error": "Failed to parse Safety output", "raw": process.stdout}
    except Exception as e:
        results["safety"] = {"error": str(e)}

    return json.dumps({"status": "success", "results": results}, indent=2)
