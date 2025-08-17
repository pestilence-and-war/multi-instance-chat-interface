#chat_instance.py

import uuid
import datetime
import json
import threading
import os
import importlib
import inspect
import time
from api_clients.base_client import BaseApiClient
from typing import List, Dict, Any, Tuple, Generator, Callable
import traceback
from tool_registry import TOOL_REGISTRY

def get_params_from_docstring(func: Callable) -> Tuple[str, Dict[str, Any]]:
    """
    Parses a basic description and parameter schema from a function's docstring.
    Format expected:
    First line: Description.
    Following lines: @param param_name (type): description
    """
    doc = inspect.getdoc(func)
    if not doc:
        return "No description provided.", {"type": "object", "properties": {}}

    lines = doc.strip().split('\n')
    description = lines[0].strip()
    parameters = {"type": "object", "properties": {}, "required": []}
    param_details = {} # Store full description for parsing required/enum

    for line in lines[1:]:
        line = line.strip()
        if line.startswith("@param"):
            try:
                # param_info_part: "location (string)"
                # param_desc: "The city and state... Required."
                param_info_part, param_desc = line[len("@param"):].split(":", 1)
                param_info_part = param_info_part.strip()
                param_desc = param_desc.strip()

                # name_type_part: ["location ", "string)"]
                name_type_part = param_info_part.split("(", 1)
                param_name = name_type_part[0].strip()

                param_type = "string" # Default type
                if len(name_type_part) > 1:
                     # type_part: "string)"
                    type_part = name_type_part[1].strip()
                    if type_part.endswith(")"):
                        param_type = type_part[:-1].strip().lower()
                    else: # Handle cases without closing parenthesis cleanly
                        param_type = type_part.strip().lower()

                param_schema = {"type": param_type, "description": param_desc}

                # Basic enum detection
                enum_keyword = "enum:"
                if enum_keyword in param_desc.lower():
                    try:
                        # Extract values after "enum:" potentially followed by spaces
                        enum_str = param_desc.lower().split(enum_keyword)[1].strip()
                        # Assume comma-separated, take first word if space follows
                        enum_values_str = enum_str.split(' ')[0]
                        enum_values = [val.strip() for val in enum_values_str.split(',') if val.strip()]
                        if enum_values:
                            param_schema["enum"] = enum_values
                    except Exception as e_enum:
                        print(f"Warning: Could not parse enum for {param_name}: {e_enum}")


                parameters["properties"][param_name] = param_schema

                if "required" in param_desc.lower():
                    parameters["required"].append(param_name)

            except Exception as e:
                print(f"Warning: Could not parse @param line: '{line}'. Error: {e}")

    if not parameters["required"]:
        del parameters["required"]

    return description, parameters

class ChatInstance:
    def __init__(self, instance_id=None, api_client_class=None, api_key=None, name=None):
        self.instance_id = instance_id or str(uuid.uuid4())
        self.name = name or f"Chat-{self.instance_id[:4]}"
        self.api_client: BaseApiClient | None = None
        self.api_client_class_name = None
        self.last_used = time.time()
        self.api_key_used = None
        self.connection_error = None
        self.tools_definitions: Dict[str, Dict[str, Any]] = {}
        self._latest_user_content = ""
        self._latest_uploaded_files = []

        # Initialize selected_model before connect might overwrite it
        self.selected_model = "" # Ensure it has a default value
        self.available_models_list: List[str] = []

        if api_client_class and api_key:
            self.connect(api_client_class, api_key)
        elif api_client_class:
            self.api_client_class_name = api_client_class.__name__

        # Ensure other attributes have defaults
        self.system_prompt = ""
        self.chat_history = []
        self.edit_log = []
        self.generation_params = {"temperature": 0.7, "top_p": 0.95}
        self.current_generation_thread = None
        self.stop_event = threading.Event()
        self.sse_queue = None
        self.is_generating = False
        self.tool_function_to_module_map = self._build_tool_module_map()

    def _build_tool_module_map(self) -> Dict[str, str]:
        """
        Scans all tool modules and creates a mapping from each function name
        to its module path. This is used for auto-registration.
        """
        mapping = {}
        # We reuse the existing discovery logic.
        module_paths = self.discover_tool_modules(directory="my_tools")
        for module_path in module_paths:
            try:
                module = importlib.import_module(module_path)
                for name, func in inspect.getmembers(module, inspect.isfunction):
                    if not name.startswith('_') and func.__module__ == module.__name__:
                        # We exclude the proxy tool itself from being a target for registration.
                        if name != 'search_for_tool':
                            mapping[name] = module_path
            except Exception as e:
                print(f"Warning: Could not inspect module {module_path} for mapping: {e}")
        print(f"Built tool-to-module map with {len(mapping)} functions.")
        return mapping

    def discover_tool_modules(self, directory: str = "my_tools") -> List[str]:
        """
        Scans a directory for Python files to find potential tool modules.

        @param directory (string): The directory to scan for tool files.
        @return (list): A list of module paths (e.g., ['my_tools.project_explorer', 'my_tools.file_reader']).
        """
        print(f"Discovering tool modules in '{directory}'...")
        modules = []
        if not os.path.isdir(directory):
            print(f"Warning: Tool directory '{directory}' not found.")
            return []

        for filename in os.listdir(directory):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                module_path = f"{directory}.{module_name}"
                modules.append(module_path)

        print(f"Found {len(modules)} potential tool modules.")
        return modules

    def get_unregistered_tools_in_module(self, module_path: str) -> List[Dict[str, Any]]:
        """
        Inspects a module and returns a list of public functions that are not yet registered.

        @param module_path (string): The full module path to inspect (e.g., 'my_tools.project_explorer').
        @return (list): A list of dictionaries, where each dict contains the 'name' and 'description' of an unregistered tool.
        """
        unregistered_tools = []
        print(f"Scanning '{module_path}' for unregistered tools...")
        try:
            spec = importlib.util.find_spec(module_path)
            if spec is None:
                raise ModuleNotFoundError(f"Module '{module_path}' not found during scan.")

            module = importlib.import_module(module_path)

            for name, func in inspect.getmembers(module, inspect.isfunction):
                # Check if public and not already registered
                if not name.startswith('_') and name not in self.tools_definitions:
                    # Extract the first line of the docstring as a short description for the user
                    docstring = inspect.getdoc(func)
                    short_description = docstring.split('\n')[0] if docstring else "No description available."
                    unregistered_tools.append({
                        "name": name,
                        "description": short_description
                    })

            print(f"Found {len(unregistered_tools)} unregistered tools in '{module_path}'.")
            return unregistered_tools

        except Exception as e:
            print(f"Error scanning module {module_path}: {e}")
            return [] # Return empty list on error

    def register_tool_from_config(self, name: str, module_path: str, function_name: str):
        """Registers a tool by dynamically importing the function."""
        print(f"Attempting to register tool '{name}' from {module_path}.{function_name}")
        try:
            # Check if module exists first using find_spec for safety
            spec = importlib.util.find_spec(module_path)
            if spec is None:
                raise ModuleNotFoundError(f"Module '{module_path}' not found.")

            module = importlib.import_module(module_path)
            func = getattr(module, function_name)
            if not callable(func):
                raise TypeError(f"{function_name} in {module_path} is not callable.")

            # Automatically get description and parameters from docstring
            description, parameters = get_params_from_docstring(func)
            if not description: print(f"Warning: Tool '{name}' has no docstring description.")
            if not parameters.get("properties"): print(f"Warning: Tool '{name}' has no parsable parameters in docstring.")

            # Store the full definition
            self.tools_definitions[name] = {
                'func': func,
                'description': description,
                'parameters': parameters,
                'source_module': module_path,
                'source_function': function_name
            }

            # Register with the active API client if connected
            if self.api_client:
                # This call might raise an error if schema formatting fails
                self.api_client.register_tool(name, func, description, parameters)

            print(f"Successfully registered tool '{name}'")
            self.connection_error = None # Clear any previous tool error on success
            return True
        except (ModuleNotFoundError, AttributeError, TypeError, ValueError) as e:
            error_msg = f"Tool Error ({name}): {e}"
            print(error_msg, f"Module: {module_path}, Function: {function_name}")
            self.connection_error = error_msg # Set error for UI feedback
            return False
        except Exception as e: # Catch other potential errors during registration
            error_msg = f"Unexpected Tool Error ({name}): {e}"
            print(f"{error_msg}\n{traceback.format_exc()}")
            self.connection_error = error_msg
            return False

    def register_tools_from_module(self, module_path: str):
        """
        Discovers and registers all public functions in a given module as tools.

        A function is considered public if its name does not start with an underscore '_'.
        The tool name will be the same as the function name.
        """
        print(f"Attempting to discover and register all tools from module '{module_path}'...")
        try:
            spec = importlib.util.find_spec(module_path)
            if spec is None:
                raise ModuleNotFoundError(f"Module to scan '{module_path}' not found.")

            module = importlib.import_module(module_path)
            functions_to_register = [
                (name, func) for name, func in inspect.getmembers(module, inspect.isfunction)
                if not name.startswith('_')
            ]

            if not functions_to_register:
                print(f"Warning: No public functions found in '{module_path}'.")
                return True # Not a failure, just nothing to do.

            success_all = True
            for name, func in functions_to_register:
                # The tool name is the function's own name.
                # We reuse the existing, robust registration logic.
                if not self.register_tool_from_config(name=name, module_path=module_path, function_name=name):
                    success_all = False # If any tool fails, the whole module is considered a failure.

            if success_all:
                print(f"Successfully registered all {len(functions_to_register)} tools from '{module_path}'.")
            else:
                print(f"Failed to register one or more tools from '{module_path}'.")

            return success_all

        except (ModuleNotFoundError, ImportError) as e:
            error_msg = f"Module Scan Error: {e}"
            print(error_msg)
            self.connection_error = error_msg
            return False
        except Exception as e:
            error_msg = f"Unexpected Module Scan Error: {e}"
            print(f"{error_msg}\n{traceback.format_exc()}")
            self.connection_error = error_msg
            return False

    def execute_tool_call(self, tool_name: str, arguments: dict):
        """
        Executes a tool call using the central tool registry.
        """
        print(f"Attempting to execute tool '{tool_name}' with args: {arguments}")

        # Look up the function in our registry
        if tool_name not in TOOL_REGISTRY:
            return f"Error: Tool '{tool_name}' not found or is not available."

        tool_function = TOOL_REGISTRY[tool_name]

        try:
            # Execute the function with the model-provided arguments
            result = tool_function(**arguments)
            return result
        except Exception as e:
            return f"Error executing tool '{tool_name}': {e}"

    def connect(self, api_client_class, api_key):
        self.connection_error = None
        try:
            self.api_client = api_client_class(api_key=api_key)
            self.api_client_class_name = api_client_class.__name__
            self.api_key_used = api_key



            if hasattr(self.api_client, 'initialization_error') and self.api_client.initialization_error:
                self.connection_error = f"API Client Init Error: {self.api_client.initialization_error}"
                print(f"Instance {self.instance_id}: Connection FAILED during client init: {self.connection_error}")
                self.api_client = None
                self.api_client_class_name = None
                self.api_key_used = None
                self.selected_model = ""
                return False

            # Fetch available models after successful connection
            try:
                models = self.get_available_models()
                self.available_models_list = models if models else []
                print(f"Instance {self.instance_id}: Available models fetched and stored: {self.available_models_list}") # LOG

            except Exception as e:
                model_error = f"Error fetching models: {e}"
                print(f"Instance {self.instance_id}: {model_error}")
                self.connection_error = self.connection_error +f"; {model_error}" if self.connection_error else model_error
                self.available_models_list = []

            if self.available_models_list and not self.selected_model:
                self.selected_model = self.available_models_list[0]
                print(f"Instance {self.instance_id}: Default model selected: {self.selected_model}") # LOG
            elif not self.available_models_list and self.selected_model:
                # If we failed to get models but had one selected (e.g. from loaded state), clear it
                print(f"Instance {self.instance_id}: No models available after connect, clearing selection '{self.selected_model}'.")
                self.selected_model = ""
            elif not self.available_models_list:
                 print(f"Instance {self.instance_id}: No models available after connect.")

            # Register any pre-existing tools (from loaded state) with the new client
            if self.api_client and not self.connection_error: # Only if client seems ok
                for name, definition in self.tools_definitions.items():
                    try:
                        self.api_client.register_tool(
                            name,
                            definition['func'],
                            definition['description'],
                            definition['parameters']
                         )
                    except Exception as e:
                        print(f"Error re-registering tool '{name}' during connect: {e}")
                        # Don't necessarily fail the whole connection for a tool error
                        self.connection_error = self.connection_error or "" + f" Tool Reg Error: {e};"

            print(f"Instance {self.instance_id}: Connection attempt finished using {self.api_client_class_name}. Error: {self.connection_error}")
            return not self.connection_error # Success if no error string is set

        except Exception as e:
            # Catch errors during client instantiation itself
            print(f"Instance {self.instance_id}: Connection FAILED during __init__: {e}")
            self.connection_error = str(e)
            self.api_client = None
            self.api_client_class_name = None
            self.api_key_used = None
            self.selected_model = ""
            return False

    def connect_api_client(self, provider_name):
        """Connects this instance to the API client for the given provider name."""
        from chat_manager import API_CLIENT_CLASSES
        client_class = API_CLIENT_CLASSES.get(provider_name)
        if not client_class:
            raise ValueError(f"Provider '{provider_name}' not found.")

        env_var_name = f"{provider_name.upper().replace('CLIENT','').replace('.','_')}_API_KEY"
        api_key = os.getenv(env_var_name)
        if not api_key:
            raise ValueError(f"API key for provider '{provider_name}' not found in environment variable '{env_var_name}'.")

        success = self.connect(client_class, api_key)
        if not success:
            raise RuntimeError(f"Failed to connect to provider '{provider_name}'. Reason: {self.connection_error}")

    def get_available_models(self) -> List[str]:
        if self.api_client:
            try:
                # This is the actual API call
                models = self.api_client.get_available_models()
                print(f"API Call: get_available_models for {self.instance_id} returned: {models}") # LOG API call
                return models
            except Exception as e:
                print(f"Error calling api_client.get_available_models for {self.instance_id}: {e}")
                # Let connect() handle storing the error in connection_error
                raise # Re-raise the exception so connect() knows it failed
        else:
            print(f"get_available_models called for {self.instance_id} but no api_client connected.")
            return [] # Return empty list if no client

    def set_config(self, model=None, system_prompt=None, temp=None, top_p=None):

        print(f"Instance {self.instance_id} set_config called:")
        if model is not None:
            print(f"  - Setting model to: '{model}' (was '{self.selected_model}')")
            self.selected_model = model

        if system_prompt is not None:
            print(f"  - Setting system_prompt (length: {len(system_prompt)})")
            self.system_prompt = system_prompt

        if temp is not None:
            try:
                new_temp = float(temp)
                print(f"  - Setting temperature to: {new_temp}")
                self.generation_params['temperature'] = new_temp
            except ValueError:
                print(f"  - Invalid temperature value received: {temp}.")
        if top_p is not None:
            try:
                new_topp = float(top_p)
                print(f"  - Setting top_p to: {new_topp}")
                self.generation_params['top_p'] = new_topp
            except ValueError:
                print(f"  - Invalid top_p value received: {top_p}.")

    def add_user_message(self, content):
        user_msg = {"role": "user", "content": content, "timestamp": datetime.datetime.now().isoformat()}
        self.chat_history.append(user_msg)
        return user_msg

    def _prepare_messages_for_api(self) -> List[Dict[str, Any]]:
        """Prepares messages, adding system prompt if needed."""
        messages = []
        if self.system_prompt:
            # Avoid duplicate system prompts if user edited history
            if not self.chat_history or self.chat_history[0].get("role") != "system":
                 messages.append({"role": "system", "content": self.system_prompt})

        messages.extend(self.chat_history) # Add the main history
        return messages

    def start_streaming_generation(self, queue):
        print(f"Instance {self.instance_id} start_streaming_generation:")
        print(f"  - Checking API Client: {'Set' if self.api_client else 'None'}")
        print(f"  - Checking Selected Model: '{self.selected_model}'")

        if not self.api_client or not self.selected_model:
            error_msg = "Not connected" if not self.api_client else "No model selected"
            queue.put(json.dumps({"type": "error", "content": error_msg}))
            queue.put(None)
            return

        if self.is_generating:
            queue.put(json.dumps({"type": "error", "content": "Already generating."}))
            queue.put(None)
            return

        self.stop_event.clear()
        self.sse_queue = queue
        self.is_generating = True

        messages_to_send = self._prepare_messages_for_api()
        if not messages_to_send or all(m.get('role') == 'system' for m in messages_to_send):
            queue.put(json.dumps({"type": "error", "content": "No user/assistant messages to send."})); queue.put(None); self.is_generating = False; return

        config = {
            "model": self.selected_model,
            **self.generation_params
        }
        print(f"  - Starting generation thread with model: {self.selected_model}, temp: {config.get('temperature')}, top_p: {config.get('top_p')}")

        self.current_generation_thread = threading.Thread(
            target=self._run_generation_in_thread,
            args=(messages_to_send, config),
            daemon=True
        )
        self.current_generation_thread.start()

    def _run_generation_in_thread(self, initial_messages, config):
        """Handles the conversation loop, including tool execution cycles."""
        current_messages = initial_messages[:] # Work on a copy
        max_tool_cycles = 5 # Magic number is based on API limits from Google Free and cost control
        cycles = 0
        final_event_type = "finish" # Default
        final_assistant_content = "" # Accumulate final text across cycles if needed

        try:
            while cycles < max_tool_cycles:
                cycles += 1
                print(f"\n--- Generation Cycle {cycles} ---")
                if self.stop_event.is_set():
                    print("Stop event set before API call."); final_event_type = "stopped"; break
                if not self.api_client:
                    raise ConnectionError("API Client lost during generation cycle.")

                print(f"Sending {len(current_messages)} messages to API client...")
                # Store text/calls specifically from this cycle's API response
                accumulated_text_this_api_call = ""
                tool_calls_from_api = []
                error_this_api_call = None
                stopped_this_api_call = False
                client_finished_normally = False

                # Call the API Client's generator
                for chunk_type, content_data in self.api_client.send_message_stream_yield(
                    current_messages, config, self.stop_event, instance=self
                ):
                    if self.stop_event.is_set(): # Check frequently
                         print("Stop event detected during client yield."); stopped_this_api_call = True; break

                    if chunk_type == "chunk":
                        accumulated_text_this_api_call += content_data
                        self.sse_queue.put(json.dumps({"type": "chunk", "content": content_data}))
                    elif chunk_type == "tool_calls":
                        # Received tool requests from the API client
                        tool_calls_from_api = content_data.get("calls", [])
                        accumulated_text_this_api_call = content_data.get("text", accumulated_text_this_api_call) # Capture any text before calls
                        client_finished_normally = True # Client finished this turn
                        print(f"Received {len(tool_calls_from_api)} tool call requests.")
                        break # Exit inner loop to process tools
                    elif chunk_type == "finish":
                        accumulated_text_this_api_call = content_data # Final text
                        client_finished_normally = True # Client finished this turn
                        print("Received 'finish' signal (text only).")
                        break # Exit inner loop, conversation over
                    elif chunk_type == "error":
                        error_this_api_call = content_data
                        ccumulated_text_this_api_call = content_data # Partial text
                        print(f"Received 'error' from client: {error_this_api_call}")
                        break # Exit inner loop on error
                    elif chunk_type == "stopped":
                        stopped_this_api_call = True
                        accumulated_text_this_api_call = content_data # Partial text
                        print("Received 'stopped' signal from client.")
                        break # Exit inner loop

                    # Handle UI feedback events if client yields them
                    elif chunk_type in ["tool_call", "tool_result", "status"]:
                        self.sse_queue.put(json.dumps({"type": chunk_type, "content": content_data}))


                # --- Post API Call Processing for this Cycle ---
                if self.stop_event.is_set() or stopped_this_api_call:
                    final_event_type = "stopped"; final_assistant_content = accumulated_text_this_api_call + " [Stopped]"; break
                if error_this_api_call:
                    final_event_type = "error"; final_assistant_content = error_this_api_call; break
                if not client_finished_normally:
                    final_event_type = "error"; final_assistant_content = "API stream ended unexpectedly."; break

                # --- If Tools Were Called ---
                if tool_calls_from_api:
                    final_assistant_content = accumulated_text_this_api_call # Store text from this turn

                     # 1. Add Assistant's request message to history
                    assistant_request_msg = {
                        "role": "assistant", "content": final_assistant_content,
                        "tool_calls": tool_calls_from_api, # Store structured calls
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                    current_messages.append(assistant_request_msg)
                    self.sse_queue.put(json.dumps({"type": "status", "content": f"Executing {len(tool_calls_from_api)} tool(s)..."}))

                     # 2. Execute Tools and Create Result Messages
                    tool_result_messages = []
                    for tool_call in tool_calls_from_api:
                        tool_name = tool_call["name"]
                        arguments = tool_call["arguments"]
                        # Execute using API client's method (which calls registered func)
                        raw_tool_result_str = self.api_client.execute_tool(tool_name, arguments)
                        # This will be the content passed back to the LLM in the tool_result message
                        final_content_for_llm = raw_tool_result_str # Default to the raw result

                        if tool_name == 'search_for_tool':
                            try:
                                # 1. Load the result from the tool. It's a list of schemas.
                                discovered_schemas = json.loads(raw_tool_result_str)

                                # 2. Ensure the result is actually a list before processing.
                                if not isinstance(discovered_schemas, list):
                                    raise TypeError("Tool 'search_for_tool' did not return a list of schemas.")

                                registration_count = 0
                                valid_schemas_for_llm = []

                                # 3. Iterate DIRECTLY over the list of discovered schemas.
                                for schema in discovered_schemas:
                                    if isinstance(schema, dict):
                                        # Add the valid schema to the list we'll show the LLM.
                                        valid_schemas_for_llm.append(schema)

                                        # Get the function name to find its module path.
                                        new_tool_name = schema.get("function", {}).get("name")
                                        module_path = self.tool_function_to_module_map.get(new_tool_name)

                                        if new_tool_name and module_path:
                                            # Use the existing, robust registration logic.
                                            success = self.register_tool_from_config(
                                                name=new_tool_name,
                                                module_path=module_path,
                                                function_name=new_tool_name
                                            )
                                            if success:
                                                registration_count += 1

                                # 4. Construct the final message for the LLM based on what was registered.
                                if registration_count > 0:
                                    status_msg = f"Dynamically registered {registration_count} new tool(s)."
                                    self.sse_queue.put(json.dumps({"type": "status", "content": status_msg}))

                                    schemas_json_for_llm = json.dumps(valid_schemas_for_llm, indent=2)
                                    final_content_for_llm = f"""I have found and successfully enabled {registration_count} new tool(s) that match your query.

                        The specifications for these newly available tools are:
                        {schemas_json_for_llm}

                        Please examine these new tools. Based on the user's original request, select the most appropriate tool from this new set and call it in your next turn to solve the user's problem.""".strip()
                                else:
                                    final_content_for_llm = "No new tools were found that match the query. Please try rephrasing your request or ask about a different capability."

                            except (json.JSONDecodeError, TypeError) as e:
                                print(f"Warning: 'search_for_tool' result was invalid or could not be processed: {e}")
                                final_content_for_llm = "The tool search returned an invalid format. Please try again."
                            except Exception as e:
                                print(f"Error during auto-registration or formatting: {e}")
                                final_content_for_llm = f"An error occurred while processing the tool search results: {e}"

                        # This part remains the same, outside the 'if' block
                        tool_result_messages.append({
                            "role": "tool",
                            "name": tool_name,
                            "content": final_content_for_llm
                        })
                        self.sse_queue.put(json.dumps({"type": "tool_result", "content": {"name": tool_name, "result_preview": raw_tool_result_str[:200] + "..."}}))

                    # 3. Add results to messages for the *next* API call
                    current_messages.extend(tool_result_messages)

                    # 4. Continue the outer loop
                    continue

                else:
                    # No tool calls - generation finished normally with text
                    final_assistant_content = accumulated_text_this_api_call
                    final_event_type = "finish"
                    # Add the final assistant message
                    current_messages.append({
                        "role": "assistant", "content": final_assistant_content,
                        "timestamp": datetime.datetime.now().isoformat()
                    })
                    break # Exit the outer loop

        except Exception as e:
            import traceback
            print(f"Thread Error [{self.instance_id}]: {e}\n{traceback.format_exc()}")
            final_event_type = "error"
            final_assistant_content = f"Internal Error: {e}"

        finally:
            # --- Finalization ---
            self.is_generating = False
            self.current_generation_thread = None

            # Update the official chat history ONLY if no error occurred or was stopped early
            if final_event_type not in ["error"]: # Include 'stopped' here? Maybe only save on 'finish'.
                self.chat_history = current_messages[:] # Persist the final state including tool calls/results

            # Send final SSE event
            if final_event_type == "error":
                self.sse_queue.put(json.dumps({"type": "error", "content": final_assistant_content}))
            else:
                # Send 'finish' or 'stopped' with the final accumulated text
                self.sse_queue.put(json.dumps({"type": final_event_type, "content": final_assistant_content}))

            self.sse_queue.put(None) # Signal end

            # Save State
            try:
                from chat_manager import chat_manager
                chat_manager.save_instance_state(self.instance_id)
                self.save_edit_log()
            except Exception as e:
                print(f"Error saving state/log after generation: {e}")

    def stop_generation(self):
        if self.is_generating:
            print(f"Instance {self.instance_id}: Stop requested.")
            self.stop_event.set()

    def clear_history(self):
        self.stop_generation()
        self.chat_history = []
        self.edit_log = []
        print(f"Instance {self.instance_id}: History Cleared.")

    def update_history_after_edit(self, edited_history, original_history):
        self.log_edits(original_history, edited_history)
        self.chat_history = edited_history

    def log_edits(self, original, new):
        timestamp = datetime.datetime.now().isoformat()
        changed_indices = []
        max_len = max(len(original), len(new))
        for i in range(max_len):
            o_msg = original[i] if i < len(original) else None
            n_msg = new[i] if i < len(new) else None
            if o_msg != n_msg:
                changed_indices.append({
                    "index": i,
                    "original": o_msg,
                    "new": n_msg
                })

        log_entry = {
            "timestamp": timestamp,
            "type": "context_edit",
            "original_length": len(original),
            "edited_length": len(new),
            "changes": changed_indices
        }
        self.edit_log.append(log_entry)
        self.save_edit_log()

    def save_edit_log(self, filename=None):
        if not self.edit_log: return
        filename = filename or f"chat_log_{self.instance_id}_edits.jsonl"
        log_dir = "chat_logs"
        if not os.path.exists(log_dir): os.makedirs(log_dir)
        filepath = os.path.join(log_dir, filename)
        try:
            with open(filepath, "a", encoding="utf-8") as f:
                for entry in self.edit_log:
                    f.write(json.dumps(entry) + "\n")
            self.edit_log = []
            print(f"Edit log appended to {filepath}")
        except Exception as e:
            print(f"Error saving edit log {filepath}: {e}")

    def get_state(self) -> Dict[str, Any]:
        # Ensure tool definitions are saved correctly
        persistent_tools = {
            name: {
                "description": definition["description"],
                "parameters": definition["parameters"],
                "source_module": definition["source_module"],
                "source_function": definition["source_function"]
            } for name, definition in self.tools_definitions.items()
        }
        return {
            "instance_id": self.instance_id,
            "name": self.name,
            "last_used": self.last_used,
            "api_client_class_name": self.api_client_class_name,
            "selected_model": self.selected_model,
            "available_models_list": self.available_models_list,
            "system_prompt": self.system_prompt,
            "chat_history": self.chat_history,
            "generation_params": self.generation_params,
            "edit_log_filename": f"chat_log_{self.instance_id}_edits.jsonl",
            "tools_definitions": persistent_tools # SAVE TOOLS
        }

    @classmethod
    def from_state(cls, state: Dict[str, Any], api_client_classes: Dict[str, type]) -> 'ChatInstance':
        instance_id = state.get("instance_id")
        print(f"--- Loading instance {instance_id} from state ---")
        instance = cls(instance_id=instance_id, name=state.get("name"))

        # Load basic attributes
        instance.selected_model = state.get("selected_model", "")
        instance.last_used = state.get("last_used", time.time())
        instance.available_models_list = state.get("available_models_list", [])
        instance.system_prompt = state.get("system_prompt", "You are a helpful assistant.")
        instance.chat_history = state.get("chat_history", [])
        instance.generation_params = state.get("generation_params", {"temperature": 0.7, "top_p": 0.95})
        instance.api_client_class_name = state.get("api_client_class_name")

        # Load and register tools BEFORE connecting client
        saved_tools = state.get("tools_definitions", {})
        for name, definition in saved_tools.items():
            module_path = definition.get("source_module")
            func_name = definition.get("source_function")
            if module_path and func_name:
                success = instance.register_tool_from_config(name, module_path, func_name)
                if not success:
                    print(f"Warning: Failed to re-register tool '{name}' for loaded instance {instance_id}.")
            else:
                print(f"Warning: Incomplete tool definition for '{name}' in state for {instance_id}.")

        # Connect API client (will register loaded tools with client if successful)
        client_name = state.get("api_client_class_name")
        ApiClientClass = api_client_classes.get(client_name)
        api_key = None
        if client_name:
            provider_key_name = client_name.replace('Client','').upper().replace('.','_')
            env_var_name = f"{provider_key_name}_API_KEY"
            api_key = os.getenv(env_var_name)

        if ApiClientClass and api_key:
            print(f"Attempting to connect loaded instance {instance_id} using {client_name}")
            instance.connect(ApiClientClass, api_key) # connect() handles tool registration now
            if instance.connection_error:
                print(f"Warning: Reconnect issue for {client_name} on instance {instance.instance_id}: {instance.connection_error}")
        elif instance.api_client_class_name:
            print(f"Warning: Class '{instance.api_client_class_name}' or API key not found for {instance.instance_id}. Instance remains disconnected.")
            # In this case, instance.available_models_list retains the value loaded from state.

        print(f"Instance {instance_id} loading complete. Model: '{instance.selected_model}', Stored Models: {instance.available_models_list}, Tools: {list(instance.tools_definitions.keys())}, Connected: {instance.api_client is not None}")
        return instance
    
    def update_last_used(self):
        """Updates the last_used timestamp to the current time."""
        self.last_used = time.time()