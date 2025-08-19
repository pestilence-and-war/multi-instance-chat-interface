# my_tools/persona_manager.py
import json
import os
from typing import Dict, Any

# Securely import necessary helpers from other modules
from my_tools.path_security import _get_project_root, _is_path_safe
from my_tools.code_editor import _sync_db_after_file_creation
from my_tools.jailed_file_manager import jailed_delete_file

# --- Internal Helper Functions ---

def _get_persona_path(persona_name: str) -> Dict[str, Any]:
    """
    (Internal Engine) Safely constructs and validates the file path for a given persona.
    """
    project_root = _get_project_root()
    if not project_root:
        return {"status": "error", "message": "Security Error: Project root not configured."}

    # Sanitize persona_name to prevent path traversal attacks (e.g., "../" in the name)
    sanitized_name = os.path.basename(f"{persona_name}.json")
    if not persona_name or sanitized_name != f"{persona_name}.json":
        return {"status": "error", "message": f"Invalid persona name provided: '{persona_name}'."}

    personas_dir = os.path.join(project_root, 'personas')
    full_path = os.path.abspath(os.path.join(personas_dir, sanitized_name))

    if not _is_path_safe(full_path):
        return {"status": "error", "message": "Security Error: Path is outside the allowed project directory."}
    
    return {"status": "success", "path": full_path, "relative_path": os.path.join('personas', sanitized_name)}

# --- Public Tool Functions ---

def list_personas() -> str:
    """
    (Low-Cost) Lists all available personas in the 'personas' directory.
    
    Returns:
        str: A JSON string containing a list of persona names.
    """
    project_root = _get_project_root()
    if not project_root:
        return json.dumps({"status": "error", "message": "Project root not configured."})
        
    personas_dir = os.path.join(project_root, 'personas')
    if not os.path.isdir(personas_dir):
        return json.dumps({"status": "success", "personas": []}, indent=2)
    
    try:
        persona_files = [f.replace('.json', '') for f in os.listdir(personas_dir) if f.endswith('.json')]
        return json.dumps({"status": "success", "personas": persona_files}, indent=2)
    except OSError as e:
        return json.dumps({"status": "error", "message": f"Failed to list personas: {e}"}, indent=2)

def get_persona_details(persona_name: str) -> str:
    """
    (Low-Cost) Retrieves the full configuration details for a specific persona.

    @param persona_name (string): The name of the persona to retrieve. REQUIRED.

    Returns:
        str: A JSON string containing the persona's details or an error message.
    """
    path_result = _get_persona_path(persona_name)
    if path_result["status"] == "error":
        return json.dumps(path_result, indent=2)
    
    full_path = path_result["path"]
    if not os.path.exists(full_path):
        return json.dumps({"status": "error", "message": f"Persona '{persona_name}' not found."}, indent=2)

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return json.dumps({"status": "success", "persona_details": data}, indent=2)
    except (json.JSONDecodeError, IOError) as e:
        return json.dumps({"status": "error", "message": f"Failed to read or parse persona file: {e}"}, indent=2)

def create_persona(persona_name: str, persona_data: str) -> str:
    """
    (Medium-Cost) Safely creates a new persona file with the given data.
    This tool creates a .json file in the 'personas' directory. It will not
    overwrite an existing persona file. On success, it registers the new
    file in the project database.

    @param persona_name (string): The name for the new persona (e.g., "Python_Developer"). REQUIRED.
    @param persona_data (string): A valid JSON string representing the persona's configuration. REQUIRED.
    
    Returns:
        string: A JSON string with the status of the operation.
    """
    path_result = _get_persona_path(persona_name)
    if path_result["status"] == "error":
        return json.dumps(path_result, indent=2)
    
    full_path = path_result["path"]
    relative_path = path_result["relative_path"]

    if os.path.exists(full_path):
        return json.dumps({'status': 'error', 'message': f'Persona "{persona_name}" already exists.'})

    try:
        content = json.loads(persona_data)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2)
    except json.JSONDecodeError:
        return json.dumps({'status': 'error', 'message': 'Invalid JSON string provided for persona_data.'})
    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'An unexpected error occurred during file write: {e}'})

    # Sync with the project database
    refresh_status_json = _sync_db_after_file_creation(relative_path)
    status_data = json.loads(refresh_status_json)

    if status_data['status'] == 'success':
        return json.dumps({'status': 'success', 'message': f"Successfully created persona '{persona_name}' and updated the project database."})
    else:
        return json.dumps({'status': 'warning', 'message': f"Successfully created persona file, but failed to update the project database. Reason: {status_data.get('message', 'Unknown')}"})

    return jailed_delete_file(path=relative_path)

def instantiate_persona(persona_name: str, chat_manager_instance) -> tuple:
    """
    (Internal Engine) Creates a new chat instance from a persona file.
    This is not an LLM tool, but a helper for the Flask app.
    """
    details_json = get_persona_details(persona_name)
    details = json.loads(details_json)

    if details.get("status") != "success":
        return None, details.get("message", "Failed to get persona details.")

    persona_config = details.get("persona_details", {})
    
    # Create a new instance
    new_instance = chat_manager_instance.create_instance(
        provider_name=persona_config.get("api_client_class_name"),
        api_key=None  # Assuming API keys are handled globally or are not in persona file
    )
    if not new_instance:
        return None, "Failed to create a new chat instance."

    # Apply persona configuration
    new_instance.name = persona_config.get("name", f"New {persona_name}")
    new_instance.set_config(
        model=persona_config.get("selected_model"),
        system_prompt=persona_config.get("system_prompt"),
        temp=persona_config.get("generation_params", {}).get("temperature"),
        top_p=persona_config.get("generation_params", {}).get("top_p")
    )
    new_instance.tools_definitions = persona_config.get("tools_definitions", {})
    
    chat_manager_instance.save_instance_state(new_instance.instance_id)

    return new_instance, f"Successfully instantiated persona '{persona_name}'."
