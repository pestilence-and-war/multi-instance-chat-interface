import subprocess
import json
import os
import shlex
from my_tools.path_security import get_project_root # Use your existing helper

def execute_jailed_command(command: str) -> str:
    """
    (High-Risk) Executes a command within a highly restricted, sandboxed PowerShell environment.

    This tool operates within a JEA (Just Enough Administration) endpoint, which strictly
    whitelists allowed commands. The working directory is dynamically and safely determined
    by the CODEBASE_DB_PATH environment variable.

    Args:
        command (str): The PowerShell command to execute (e.g., "ls", "New-Item test.txt").

    Returns:
        A JSON string containing the command's stdout and stderr.
    """
    # The parent directory where all sandboxed projects must reside.
    # This MUST match the directory you configured in PowerShell.
    SANDBOX_ROOT = "C:\\SandboxedWorkspaces"

    # The name of the JEA endpoint we registered.
    JEA_ENDPOINT_NAME = "JailedPowerShell"

    # 1. Determine the project directory using your existing, trusted function.
    project_directory = get_project_root()
    if not project_directory:
        return json.dumps({
            'status': 'error',
            'message': 'Could not determine project root. Is CODEBASE_DB_PATH set in your .env file?'
        }, indent=2)

    # 2. **CRITICAL SECURITY CHECK**: Ensure the determined path is within our sandbox.
    # We resolve both paths to their canonical form to prevent traversal attacks (e.g., '..\\').
    safe_root = os.path.realpath(SANDBOX_ROOT)
    requested_path = os.path.realpath(project_directory)

    if os.path.commonpath([safe_root, requested_path]) != safe_root:
        return json.dumps({
            'status': 'security_error',
            'message': f"FATAL: The project path '{requested_path}' is outside the designated sandbox root '{safe_root}'. Operation aborted."
        }, indent=2)

    # 3. Construct and execute the PowerShell command.
    # The inner command is enclosed in single quotes to be treated as a literal string.
    escaped_command = command.replace("'", "''")

    # We now pass the DYNAMIC, VALIDATED project directory to Set-Location.
    full_ps_command = (
        f"Enter-PSSession -ConfigurationName {JEA_ENDPOINT_NAME} -Command {{"
        f"Set-Location -LiteralPath '{requested_path}';" # <-- The dynamic part!
        f" {escaped_command} "
        f"}}"
    )

    final_command = ["powershell.exe", "-NoProfile", "-Command", full_ps_command]

    try:
        process = subprocess.run(
            final_command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=30
        )
        return json.dumps({
            'status': 'success',
            'stdout': process.stdout.strip(),
            'stderr': process.stderr.strip(),
            'working_directory': requested_path
        }, indent=2)

    except subprocess.TimeoutExpired:
        return json.dumps({
            'status': 'error',
            'message': 'Command timed out after 30 seconds.'
        }, indent=2)
    except Exception as e:
        return json.dumps({
            'status': 'error',
            'message': f'An unexpected error occurred: {e}'
        }, indent=2)
