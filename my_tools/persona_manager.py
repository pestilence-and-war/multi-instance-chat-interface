# my_tools/persona_manager.py
import json
import os
from typing import Dict, Any

# Securely import necessary helpers from other modules
from my_tools.path_security import _get_project_root, _is_path_safe
from my_tools.code_editor import _sync_db_after_file_creation
from my_tools.jailed_file_manager import jailed_delete_file

# --- Internal Helper Functions ---

def _get_app_root_personas_dir() -> str:
    """
    (Internal) Resolves the 'personas' directory relative to this script.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_root = os.path.dirname(current_dir)
    return os.path.join(app_root, 'personas')

def _get_workspace_personas_dir() -> str | None:
    """
    (Internal) Resolves the 'personas' directory within the current target project.
    """
    project_root = _get_project_root()
    if not project_root:
        return None
    return os.path.join(project_root, 'personas')

def _get_persona_path(persona_name: str) -> Dict[str, Any]:
    """
    (Internal Engine) Safely constructs and validates the file path for a given persona.
    """
    # Sanitize persona_name to prevent path traversal attacks (e.g., "../" in the name)
    sanitized_name = os.path.basename(f"{persona_name}.json")
    if not persona_name or sanitized_name != f"{persona_name}.json":
        return {"status": "error", "message": f"Invalid persona name provided: '{persona_name}'."}

    personas_dir = _get_app_root_personas_dir()
    full_path = os.path.abspath(os.path.join(personas_dir, sanitized_name))

    # Security check: Ensure the path is actually inside the personas dir
    if not full_path.startswith(os.path.abspath(personas_dir)):
        return {"status": "error", "message": "Security Error: Path is outside the allowed personas directory."}
    
    return {"status": "success", "path": full_path, "relative_path": os.path.join('personas', sanitized_name)}

def list_personas() -> str:
    """
    (Low-Cost) Lists all available personas from both the central library and the local workspace.
    
    Returns:
        str: A JSON string containing a list of unique persona names.
    """
    all_personas = set()
    
    # 1. Check App Root (The Bank)
    app_dir = _get_app_root_personas_dir()
    if os.path.isdir(app_dir):
        try:
            for f in os.listdir(app_dir):
                if f.endswith('.json'):
                    all_personas.add(f.replace('.json', ''))
        except OSError: pass

    # 2. Check Workspace (The Office)
    workspace_dir = _get_workspace_personas_dir()
    if workspace_dir and os.path.isdir(workspace_dir):
        try:
            for f in os.listdir(workspace_dir):
                if f.endswith('.json'):
                    all_personas.add(f.replace('.json', ''))
        except OSError: pass
    
    return json.dumps({
        "status": "success", 
        "personas": sorted(list(all_personas))
    }, indent=2)

def get_persona_details(persona_name: str) -> str:
    """
    Reads the JSON configuration file for a given persona.
    Checks the workspace first, then falls back to the central repository.

    @param persona_name (string): The name of the persona to read. Required.
    @return (string): A JSON string of the persona's configuration, or an error JSON if not found.
    """
    # 1. Try Workspace First
    workspace_dir = _get_workspace_personas_dir()
    filename = f"{persona_name}.json"
    
    if workspace_dir:
        workspace_path = os.path.join(workspace_dir, filename)
        if os.path.exists(workspace_path):
            try:
                with open(workspace_path, 'r', encoding='utf-8') as f:
                    return json.dumps(json.load(f))
            except Exception as e:
                logger.error(f"Error reading workspace persona: {e}")

    # 2. Fallback to App Root
    app_dir = _get_app_root_personas_dir()
    app_path = os.path.join(app_dir, filename)
    
    if os.path.exists(app_path):
        try:
            with open(app_path, 'r', encoding='utf-8') as f:
                return json.dumps(json.load(f))
        except Exception as e:
            return json.dumps({"status": "error", "message": f"Error reading central persona: {e}"})

    return json.dumps({"status": "error", "message": f"Persona '{persona_name}' not found."})

def deploy_agent(persona_name: str) -> str:
    """
    (Medium-Cost) Copies a specialist persona from the central repository to the current office workspace.
    Use this during office setup to ensure the project is self-contained.

    @param persona_name (string): The name of the persona to deploy (e.g., "Writer", "Project Manager"). REQUIRED.
    """
    import shutil
    
    app_dir = _get_app_root_personas_dir()
    workspace_dir = _get_workspace_personas_dir()
    
    if not workspace_dir:
        return json.dumps({"status": "error", "message": "No workspace configured. Use setup_digital_office_structure first."})
    
    os.makedirs(workspace_dir, exist_ok=True)
    
    safe_filename = persona_name.replace(" ", "_") + ".json"
    src_path = os.path.join(app_dir, safe_filename)
    dest_path = os.path.join(workspace_dir, safe_filename)
    
    if not os.path.exists(src_path):
        # Alt check
        src_path = os.path.join(app_dir, persona_name + ".json")
        if not os.path.exists(src_path):
            return json.dumps({"status": "error", "message": f"Source persona '{persona_name}' not found in central repository."})
            
    try:
        shutil.copy2(src_path, dest_path)
        return json.dumps({"status": "success", "message": f"Agent '{persona_name}' deployed to workspace personas/ folder."})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Deployment failed: {e}"})

def create_persona(persona_name: str, persona_data: str, overwrite: bool = False) -> str:
    """
    (Medium-Cost) Safely creates and 'hires' a new persona for the office.
    Saves the persona to the local project workspace.

    @param persona_name (string): The name for the new persona (e.g., "Python_Developer"). REQUIRED.
    @param persona_data (string): A valid JSON string representing the persona's configuration. REQUIRED.
    @param overwrite (boolean): If True, will overwrite an existing persona of the same name. Defaults to False.
    """
    # 1. Determine destination (Workspace preferred)
    target_dir = _get_workspace_personas_dir() or _get_app_root_personas_dir()
    
    # 2. Construct path
    sanitized_name = os.path.basename(f"{persona_name}.json")
    full_path = os.path.join(target_dir, sanitized_name)

    if os.path.exists(full_path) and not overwrite:
        return json.dumps({'status': 'error', 'message': f'Persona "{persona_name}" already exists. Set overwrite=True to update it.'})

    try:
        content = json.loads(persona_data)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2)
        
        return json.dumps({
            'status': 'success', 
            'message': f"Persona '{persona_name}' created and hired into the workspace."
        })
    except json.JSONDecodeError:
        return json.dumps({'status': 'error', 'message': 'Invalid JSON string provided for persona_data.'})
    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'An unexpected error occurred: {e}'})


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
