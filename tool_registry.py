# In a new file, e.g., tool_registry.py
import os
import importlib.util
import inspect

def load_tools_from_directory(directory="my_tools"):
    """
    Scans the 'my_tools' directory, imports all the Python functions,
    and returns a dictionary mapping tool names to callable functions.
    This does NOT depend on the VDB. It's for the backend's execution.
    """
    tool_registry = {}

    # We need to add the project root to the path for imports to work
    project_root = os.path.abspath(os.path.join(directory, '..'))
    import sys
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    for filename in os.listdir(directory):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = filename[:-3]
            module_path = f"{os.path.basename(directory)}.{module_name}"

            try:
                module = importlib.import_module(module_path)
                for name, func in inspect.getmembers(module, inspect.isfunction):
                    # Register public functions from the module
                    if not name.startswith('_') and func.__module__ == module.__name__:
                        print(f"Registering tool: {name}")
                        tool_registry[name] = func
            except Exception as e:
                print(f"Could not load tools from {module_path}: {e}")

    return tool_registry

# Create a global registry when the application starts
TOOL_REGISTRY = load_tools_from_directory()
