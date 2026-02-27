# my_tools/orchestration.py

import json
import os
import logging
from typing import Dict, Any

# Internal imports from the app
from chat_manager import chat_manager
from my_tools.persona_manager import get_persona_details

logger = logging.getLogger(__name__)

def delegate_task(persona_name: str, task_description: str, instance=None) -> str:
    """
    (High-Cost) Delegates a specific sub-task to a specialist persona within the same model context.
    The specialist will execute the task and return their findings or deliverable path.
    This tool is used by the Project Manager to orchestrate the digital office.

    @param persona_name (string): The name of the specialist persona (e.g., 'Researcher', 'Writer', 'Developer'). REQUIRED.
    @param task_description (string): A detailed description of the task, including all necessary context and instructions. REQUIRED.
    @param instance (object): INTERNAL. The calling ChatInstance. DO NOT provide this manually.
    """
    logger.info(f"Delegating task to '{persona_name}': {task_description[:100]}...")

    # 1. Inherit Model and Provider from parent if available
    # This prevents VRAM thrashing and "Model Not Found" errors by sticking to the user's selection.
    if instance and instance.api_client:
        # Extract provider from class name (e.g., 'OllamaClient' -> 'Ollama')
        provider_name = instance.api_client_class_name.replace('Client', '')
        model_name = instance.selected_model
        logger.info(f"Inheriting parent context: {provider_name} / {model_name}")
    else:
        # Fallback to defaults only if parent is not connected
        provider_name = "Ollama"
        model_name = "gpt-oss:20b"
        logger.warning(f"No parent instance found for delegation. Falling back to: {provider_name} / {model_name}")

    spec_instance = None
    try:
        # 2. Get Persona Details
        details_str = get_persona_details(persona_name)
        details = json.loads(details_str)
        if details.get("status") == "error":
             return json.dumps({"status": "error", "message": f"Specialist '{persona_name}' not found."})

        # 3. Create a temporary ChatInstance
        spec_instance = chat_manager.create_instance(provider_name=provider_name)
        if not spec_instance:
            return json.dumps({"status": "error", "message": "Failed to create specialist instance."})

        spec_instance.name = f"DELEGATE_{persona_name}"
        
        # 4. Configure with Persona's prompt but PARENT'S model/provider
        model_config = details.get("model_config", {})
        spec_instance.set_config(
            system_prompt=details.get("system_prompt", "You are a helpful assistant."),
            model=model_name,
            temp=model_config.get("generation_params", {}).get("temperature", 0.7)
        )

        # 5. Register specialist's tools
        spec_instance.tool_manager.build_module_map()
        for tool_name in details.get("tools", []):
            module_path = spec_instance.tool_manager.tool_module_map.get(tool_name)
            if module_path:
                logger.info(f"Registering tool '{tool_name}' from '{module_path}' for specialist...")
                success = spec_instance.register_tool(name=tool_name, module_path=module_path, function_name=tool_name)
                if not success:
                    logger.error(f"Failed to register tool '{tool_name}' for specialist.")
            else:
                logger.warning(f"Tool '{tool_name}' NOT FOUND in module map for specialist.")

        # 6. Execute the task (Headless)
        result = spec_instance.execute_headless_turn(task_description)

        if result['status'] == 'success':
            return json.dumps({
                "status": "success",
                "specialist": persona_name,
                "output": result['content']
            }, indent=2)
        else:
            return json.dumps({
                "status": "error",
                "specialist": persona_name,
                "message": result['content']
            }, indent=2)

    except Exception as e:
        logger.error(f"Delegation Error: {e}")
        import traceback
        traceback.print_exc()
        return json.dumps({"status": "error", "message": str(e)})
    finally:
        if spec_instance:
            chat_manager.remove_instance(spec_instance.instance_id)
