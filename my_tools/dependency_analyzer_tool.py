import json
import subprocess
import os
from typing import Dict, Any

def analyze_dependencies(project_path: str = ".") -> str:
    """
    Analyzes project dependencies for outdated packages or known vulnerabilities.
    Checks requirements.txt (Python) or package.json (Node.js).

    @param project_path (string): Path to the project root. Defaults to current directory.
    """
    results = {"python": None, "nodejs": None}
    
    # 1. Python Analysis (requirements.txt)
    req_path = os.path.join(project_path, "requirements.txt")
    if os.path.exists(req_path):
        try:
            # Check for vulnerabilities using Safety
            safety_cmd = ["safety", "check", "--file", req_path, "--json"]
            safety_proc = subprocess.run(safety_cmd, capture_output=True, text=True)
            try:
                vulnerabilities = json.loads(safety_proc.stdout)
            except:
                vulnerabilities = {"message": "No vulnerabilities found or parse error."}
            
            results["python"] = {
                "file": "requirements.txt",
                "vulnerabilities": vulnerabilities
            }
        except Exception as e:
            results["python"] = {"error": str(e)}

    # 2. Node.js Analysis (package.json)
    pkg_path = os.path.join(project_path, "package.json")
    if os.path.exists(pkg_path):
        try:
            # Run npm audit
            audit_cmd = ["npm", "audit", "--json"]
            # npm audit might return non-zero exit code if vulnerabilities are found
            audit_proc = subprocess.run(audit_cmd, capture_output=True, text=True, cwd=project_path, shell=True)
            try:
                audit_data = json.loads(audit_proc.stdout)
            except:
                audit_data = {"message": "Parsing npm audit failed.", "raw": audit_proc.stdout}
            
            results["nodejs"] = {
                "file": "package.json",
                "audit": audit_data
            }
        except Exception as e:
            results["nodejs"] = {"error": str(e)}

    if results["python"] is None and results["nodejs"] is None:
        return json.dumps({"status": "error", "message": "No dependency files (requirements.txt or package.json) found."})

    return json.dumps({"status": "success", "results": results}, indent=2)
