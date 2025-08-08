# my_tools/jailed_shell_tool.py

import subprocess
import json
import os
from my_tools.path_security import _get_project_root

def _run_jailed_command(command: str, working_dir: str) -> str:
    """
    (Internal Engine) Executes a command in the JEA sandbox.
    This function is NOT a tool for the LLM. It assumes the process
    is already running as the correct user ('JeaToolUser').
    """
    escaped_command = command.replace("'", "''")

    # This is the simplest possible command. No credentials needed because our
    # identity is already correct.
    full_ps_command = f"""
        Invoke-Command -ComputerName localhost -ConfigurationName JailedPowerShell -ScriptBlock {{
            Set-Location -LiteralPath '{working_dir}';
            {escaped_command}
        }}
    """
    
    final_command = ["powershell.exe", "-NoProfile", "-Command", full_ps_command]

    try:
        process = subprocess.run(
            final_command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=30
        )
        stdout_str = process.stdout.strip()
        stderr_str = process.stderr.strip()

        if "Access is denied" in stderr_str:
            stderr_str += "\\n\\n[HELPFUL_ERROR] 'Access Denied' usually means the script is NOT running as 'JeaToolUser'. Please use the 'run_app_as_jea_user.bat' script to launch the application."

        return json.dumps({
            'status': 'success' if not stderr_str else 'error',
            'stdout': stdout_str,
            'stderr': stderr_str,
            'working_directory': working_dir
        }, indent=2)
    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'An unexpected error occurred: {e}'}, indent=2)