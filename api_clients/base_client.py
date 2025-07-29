# api_clients/base_client.py
from abc import ABC, abstractmethod
import threading
import json
from typing import List, Dict, Any, Tuple, Generator, Callable

class BaseApiClient(ABC):
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Store tool definitions (name -> function) provided by ChatInstance
        self.registered_tools: Dict[str, Callable] = {}
        # Store tool schemas formatted for the specific API
        self.tool_schemas: List[Any] = [] # Type depends on subclass implementation (e.g., dict or specific SDK object)

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Return a list of model identifiers available for this client."""
        pass

    @abstractmethod
    def send_message_stream_yield(self,
                                messages: List[Dict[str, Any]],
                                config: Dict[str, Any],
                                stop_event: threading.Event,
                                instance=None # Keep instance reference if needed
                                ) -> Generator[Tuple[str, Any], None, None]: # Yield type changed to Any for tool data
        """
        Send messages and yield ('type', 'content') tuples.
        Types: 'chunk', 'error', 'finish', 'tool_calls', 'stopped'.
               Optionally: 'tool_call', 'tool_result' for UI feedback during execution.
        Checks stop_event periodically.
        Handles the API interaction for potential tool calls.
        """
        pass

    @abstractmethod
    def format_tool_schema(self, name: str, description: str, parameters: Dict[str, Any]) -> Any:
        """
        Formats a tool definition into the schema object/dict expected by the specific API provider.
        Must be implemented by subclasses.
        """
        pass

    def register_tool(self, name: str, func: Callable, description: str, parameters: Dict[str, Any]):
        """
        Registers a tool function AND its schema. Called by ChatInstance.
        """
        if name in self.registered_tools:
            print(f"Warning: Re-registering tool '{name}' in API Client")
        self.registered_tools[name] = func
        try:
            # Format and store the schema using the subclass's implementation
            schema = self.format_tool_schema(name, description, parameters)
            # Avoid duplicate schemas if re-registering
            existing_schema_index = -1
            for i, s_existing in enumerate(self.tool_schemas):
                current_schema_name = None
                if hasattr(s_existing, 'name'): # For objects like Google's FunctionDeclaration
                    current_schema_name = s_existing.name
                elif isinstance(s_existing, dict): # For dict-based schemas like OpenAI/Ollama
                    # Check for different possible structures OpenRouter/Ollama might use
                    if "function" in s_existing and isinstance(s_existing["function"], dict) and "name" in s_existing["function"]:
                        current_schema_name = s_existing["function"]["name"] # e.g. Ollama style
                    elif "name" in s_existing:
                        current_schema_name = s_existing["name"] # e.g. OpenRouter style
                
                if current_schema_name == name:
                    existing_schema_index = i
                    break

            if existing_schema_index != -1:
                self.tool_schemas[existing_schema_index] = schema
            else:
                self.tool_schemas.append(schema)
            print(f"API Client: Tool '{name}' registered with schema.")
        except Exception as e:
             print(f"API Client Error: Failed to format/register schema for tool '{name}': {e}")
             # Optionally remove the function if schema formatting fails?
             # if name in self.registered_tools: del self.registered_tools[name]
             raise # Re-raise the error to signal failure

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Executes a registered tool function with the provided arguments.
        Returns the result as a string (preferably JSON).
        """
        if tool_name not in self.registered_tools:
            print(f"Error: Attempted to execute unknown tool '{tool_name}'")
            return json.dumps({"error": f"Tool '{tool_name}' not found."})

        func = self.registered_tools[tool_name]
        print(f"--- Executing tool '{tool_name}' with args: {arguments} ---")
        try:
            # Ensure arguments is a dict before passing
            if not isinstance(arguments, dict):
                 raise TypeError(f"Arguments for tool '{tool_name}' must be a dictionary, got {type(arguments)}")

            result = func(**arguments)
            print(f"--- Tool '{tool_name}' executed. Result: {result} ---")
            # Ensure result is serializable (often string or JSON string)
            if not isinstance(result, str):
                try:
                    return json.dumps(result)
                except TypeError:
                    print(f"Warning: Tool '{tool_name}' result is not JSON serializable, converting to string.")
                    return str(result) # Fallback
            return result
        except Exception as e:
            import traceback
            print(f"--- Error executing tool '{tool_name}': {e}\n{traceback.format_exc()} ---")
            return json.dumps({"error": f"Error during tool execution: {str(e)}"})