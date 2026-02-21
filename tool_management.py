# tool_management.py
import inspect
import importlib
import importlib.util
import os
import traceback
from typing import Dict, Any, List, Callable, Tuple

def get_params_from_docstring(func: Callable) -> Tuple[str, Dict[str, Any]]:
    """
    Parses a basic description and parameter schema from a function's docstring.
    """
    doc = inspect.getdoc(func)
    if not doc:
        return "No description provided.", {"type": "object", "properties": {}}

    lines = doc.strip().split('\n')
    description = lines[0].strip()
    parameters = {"type": "object", "properties": {}, "required": []}

    for line in lines[1:]:
        line = line.strip()
        if line.startswith("@param"):
            try:
                # Format: @param name (type): description
                param_info_part, param_desc = line[len("@param"):].split(":", 1)
                param_info_part = param_info_part.strip()
                param_desc = param_desc.strip()

                name_type_part = param_info_part.split("(", 1)
                param_name = name_type_part[0].strip()

                param_type = "string"
                if len(name_type_part) > 1:
                    type_part = name_type_part[1].strip()
                    param_type = type_part[:-1].strip().lower() if type_part.endswith(")") else type_part.strip().lower()

                param_schema = {"type": param_type, "description": param_desc}
                
                # Enum detection
                if "enum:" in param_desc.lower():
                    try:
                        enum_str = param_desc.lower().split("enum:")[1].strip()
                        enum_values_str = enum_str.split(' ')[0]
                        enum_values = [val.strip() for val in enum_values_str.split(',') if val.strip()]
                        if enum_values:
                            param_schema["enum"] = enum_values
                    except: pass

                parameters["properties"][param_name] = param_schema

                if "required" in param_desc.lower():
                    parameters["required"].append(param_name)

            except Exception as e:
                print(f"Warning: Could not parse @param line: '{line}'. Error: {e}")

    if not parameters["required"]:
        del parameters["required"]

    return description, parameters

class ToolManager:
    def __init__(self):
        self.active_tools: Dict[str, Dict[str, Any]] = {} 
        self.tool_module_map: Dict[str, str] = {}

    def get_tool(self, name: str) -> Callable | None:
        return self.active_tools.get(name, {}).get('func')

    def get_definitions(self) -> Dict[str, Any]:
        return {
            name: {
                "description": data["description"],
                "parameters": data["parameters"],
                "source_module": data["source_module"],
                "source_function": data["source_function"]
            }
            for name, data in self.active_tools.items()
        }

    def load_definitions(self, saved_definitions: Dict[str, Any]):
        for name, def_data in saved_definitions.items():
            try:
                self.register_tool(
                    name=name,
                    module_path=def_data["source_module"],
                    function_name=def_data["source_function"]
                )
            except Exception as e:
                print(f"Failed to restore tool {name}: {e}")

    def scan_module_for_tools(self, module_path: str) -> List[Dict[str, Any]]:
        potential_tools = []
        try:
            if importlib.util.find_spec(module_path) is None:
                return []
            
            module = importlib.import_module(module_path)
            for name, func in inspect.getmembers(module, inspect.isfunction):
                if not name.startswith('_') and name not in self.active_tools:
                    doc = inspect.getdoc(func)
                    desc = doc.split('\n')[0] if doc else "No description available."
                    potential_tools.append({"name": name, "description": desc})
        except Exception as e:
            print(f"Error scanning {module_path}: {e}")
        return potential_tools

    def register_tool(self, name: str, module_path: str, function_name: str) -> bool:
        try:
            module = importlib.import_module(module_path)
            func = getattr(module, function_name)
            
            description, parameters = get_params_from_docstring(func)
            
            self.active_tools[name] = {
                "func": func,
                "description": description,
                "parameters": parameters,
                "source_module": module_path,
                "source_function": function_name,
                "schema": {
                    "name": name,
                    "description": description,
                    "parameters": parameters
                }
            }
            return True
        except Exception as e:
            print(f"Tool Registration Error ({name}): {e}")
            traceback.print_exc()
            return False

    def unregister_tool(self, name: str):
        if name in self.active_tools:
            del self.active_tools[name]

    def build_module_map(self, directory="my_tools"):
        self.tool_module_map = {}
        if not os.path.exists(directory): return

        for filename in os.listdir(directory):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_path = f"{directory}.{filename[:-3]}"
                try:
                    module = importlib.import_module(module_path)
                    for name, func in inspect.getmembers(module, inspect.isfunction):
                        if not name.startswith('_'):
                             self.tool_module_map[name] = module_path
                except: pass