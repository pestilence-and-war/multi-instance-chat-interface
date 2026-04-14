# my_tools/jailed_shell_tool.py

import subprocess
import json
import os
import sys
from my_tools.path_security import _get_project_root, _is_path_safe

def execute_command(command: str) -> str:
    """
    Executes a shell command within the project workspace.
    Use this tool to run build commands, tests, or other CLI operations.
    
    @param command (string): The command to execute (e.g., 'python app.py', 'npm test').
    """
    working_dir = _get_project_root()
    if not working_dir:
        return json.dumps({'status': 'error', 'message': 'Project root not found.'}, indent=2)

    warnings = []
    # --- Windows Compatibility Fixes ---
    if sys.platform == "win32":
        # 1. Translate python3 to python
        if command.startswith("python3 "):
            command = command.replace("python3 ", "python ", 1)
        elif command == "python3":
            command = "python"
        
        # 2. Warn about backgrounding if '&' is used (it's not backgrounding on Windows)
        if "&" in command and "start /B" not in command:
             warning_msg = "Command contains '&' on Windows. This runs sequentially, NOT in background. Use start_background_service instead."
             print(f"DEBUG: Warning - {warning_msg}")
             warnings.append(warning_msg)

    try:
        # Use Popen to have access to the child's PID for aggressive cleanup
        proc = subprocess.Popen(
            command,
            shell=True,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            env=os.environ.copy()
        )
        
        try:
            stdout, stderr = proc.communicate(timeout=45)
            
            result = {
                'status': 'success' if proc.returncode == 0 else 'error',
                'stdout': stdout.strip() if stdout else "",
                'stderr': stderr.strip() if stderr else "",
                'returncode': proc.returncode,
                'working_directory': working_dir
            }
            if warnings:
                result['warnings'] = warnings
            return json.dumps(result, indent=2)
            
        except subprocess.TimeoutExpired:
            # ON WINDOWS: kill the CHILD process tree, NOT the main app!
            if sys.platform == "win32":
                subprocess.run(f"taskkill /F /T /PID {proc.pid}", shell=True, capture_output=True)
            else:
                proc.kill()
                
            stdout, stderr = proc.communicate()
            
            result = {
                'status': 'error', 
                'message': 'Command timed out after 45 seconds. Persistent processes (like servers) are not supported in this tool. Use start_background_service instead.',
                'stdout': stdout.strip() if stdout else "",
                'stderr': stderr.strip() if stderr else ""
            }
            if warnings:
                result['warnings'] = warnings
            return json.dumps(result, indent=2)
            
    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'An unexpected error occurred: {e}'}, indent=2)

def start_background_service(command: str, instance=None) -> str:
    """
    (High-Cost) Starts a long-running process (like a web server) in the background.
    Returns the Process ID (PID) immediately so the agent can continue working.
    
    @param command (string): The command to run (e.g., 'python -m http.server 8000').
    @param instance (object): INTERNAL. The calling ChatInstance.
    """
    if not instance:
        return json.dumps({'status': 'error', 'message': 'Internal Error: No chat instance found.'})

    working_dir = _get_project_root()
    if not working_dir:
        return json.dumps({'status': 'error', 'message': 'Project root not found.'})

    # Command Translation
    if sys.platform == "win32":
        if command.startswith("python3 "):
            command = command.replace("python3 ", "python ", 1)

    try:
        # Use Popen to run without blocking
        # 'shell=True' is needed for command strings on Windows
        proc = subprocess.Popen(
            command,
            shell=True,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ.copy(),
            start_new_session=True # Decouple from parent
        )
        
        # Register in the instance
        instance._background_processes[proc.pid] = {
            "process": proc,
            "command": command,
            "started_at": datetime.now().isoformat()
        }
        
        return json.dumps({
            'status': 'success',
            'message': f"Service started successfully.",
            'pid': proc.pid,
            'command': command
        }, indent=2)
        
    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'Failed to start service: {e}'})

def stop_service(pid: int, instance=None) -> str:
    """
    Stops a background service using its Process ID (PID).
    
    @param pid (integer): The PID of the service to stop.
    @param instance (object): INTERNAL. The calling ChatInstance.
    """
    if not instance:
        return json.dumps({'status': 'error', 'message': 'Internal Error: No chat instance found.'})

    if pid not in instance._background_processes:
        return json.dumps({'status': 'error', 'message': f'PID {pid} not found in this session.'})

    try:
        proc_data = instance._background_processes.pop(pid)
        proc = proc_data['process']
        
        if sys.platform == "win32":
            subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, capture_output=True)
        else:
            proc.terminate()
            
        return json.dumps({
            'status': 'success',
            'message': f"Service {pid} ({proc_data['command']}) stopped."
        }, indent=2)
    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'Error stopping service: {e}'})

def list_active_services(instance=None) -> str:
    """
    Lists all background services currently running in this chat session.
    
    @param instance (object): INTERNAL. The calling ChatInstance.
    """
    if not instance:
        return json.dumps({'status': 'error', 'message': 'Internal Error: No chat instance found.'})

    services = []
    # Clean up dead processes first
    to_remove = []
    for pid, data in instance._background_processes.items():
        if data['process'].poll() is not None:
            to_remove.append(pid)
        else:
            services.append({
                "pid": pid,
                "command": data['command'],
                "started_at": data['started_at']
            })
            
    for pid in to_remove:
        del instance._background_processes[pid]
        
    return json.dumps({
        'status': 'success',
        'active_services': services
    }, indent=2)

def _run_jailed_command(command: str, working_dir: str) -> str:
    """
    (Internal Engine) Executes a command in the JEA sandbox.
    (Deprecated) Kept for internal reference.
    """
    escaped_command = command.replace("'", "''")
    full_ps_command = f"""
        Invoke-Command -ComputerName localhost -ConfigurationName JailedPowerShell -ScriptBlock {{
            Set-Location -LiteralPath '{working_dir}';
            {escaped_command}
        }}
    """
    final_command = ["powershell.exe", "-NoProfile", "-Command", full_ps_command]
    try:
        process = subprocess.run(final_command, capture_output=True, text=True, encoding='utf-8', timeout=30)
        return json.dumps({'status': 'success' if not process.stderr else 'error', 'stdout': process.stdout.strip(), 'stderr': process.stderr.strip()}, indent=2)
    except Exception as e:
        return json.dumps({'status': 'error', 'message': str(e)}, indent=2)

def jailed_pytest(test_file: str) -> str:
    """(High-Cost) Safely executes pytest against a specific test file within the project workspace.
    This tool runs 'pytest' using the current Python environment and returns the output.

    @param test_file (string): The project-relative path to the pytest file (e.g., 'invariant_tests.py'). REQUIRED.
    """
    from my_tools.path_security import _get_project_root, _is_path_safe

    project_root = _get_project_root()
    if not project_root:
        return json.dumps({'status': 'error', 'message': 'Project root not found.'}, indent=2)

    full_path = os.path.abspath(os.path.join(project_root, test_file))
    if not _is_path_safe(full_path):
        return json.dumps({'status': 'error', 'message': f'Security Error: Path "{test_file}" is outside the workspace.'}, indent=2)

    if not os.path.exists(full_path):
        return json.dumps({'status': 'error', 'message': f'Test file not found: {test_file}'}, indent=2)

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "PYTHONPATH": ""} 
        )

        return json.dumps({
            'status': 'success' if result.returncode == 0 else 'fail',
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }, indent=2)

    except subprocess.TimeoutExpired:
        return json.dumps({'status': 'error', 'message': 'Test execution timed out.'}, indent=2)
    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'Unexpected error during pytest execution: {e}'}, indent=2)
