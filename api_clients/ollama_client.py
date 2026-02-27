# api_clients/ollama_client.py
import requests
import json
import threading
import time # For generating tool call IDs
import logging
from .base_client import BaseApiClient
from typing import List, Dict, Any, Tuple, Generator, Callable # For type hints
import os

logger = logging.getLogger(__name__)

class OllamaClient(BaseApiClient):
    """
    Client for interacting with a local Ollama instance.
    Assumes Ollama is running on http://localhost:11434 by default.
    """
    BASE_URL = "http://localhost:11434" # Set your Ollama URL if different

    def __init__(self, api_key=None):
        """
        Initializes the OllamaClient.
        api_key is not strictly required for local Ollama but kept for interface consistency.
        """
        super().__init__(api_key) # api_key will be stored in self.api_key
        self.initialization_error = None # Add initialization_error attribute
        self._check_connection() # Optional: Add a connection check

    def _check_connection(self):
        """Attempts a basic API call to check connection."""
        try:
            # A lightweight call, like listing models
            self.get_available_models() # This already handles connection errors
            # If get_available_models doesn't raise an error and returns something, connection is likely fine
            if not hasattr(self, 'initialization_error') or not self.initialization_error:
                 logger.info("Ollama connection check successful (listed models).")
                 self.initialization_error = None
        except Exception as e:
            # get_available_models already logs, so we just ensure error is set
            if not self.initialization_error: # Only set if not already set by get_models
                self.initialization_error = f"Connection Check Failed: {e}"
            logger.warning(f"Ollama connection check failed during init: {self.initialization_error}")


    def get_available_models(self) -> list[str]:
        """
        Fetches available models from the local Ollama instance.
        """
        models_url = f"{self.BASE_URL}/api/tags"
        available_models = []
        current_error = None

        try:
            response = requests.get(models_url, timeout=5) # Add timeout
            response.raise_for_status()
            data = response.json()

            if "models" in data and isinstance(data["models"], list):
                for model_info in data["models"]:
                    model_name = model_info.get("name")
                    if model_name:
                        available_models.append(model_name)
            else:
                 msg = f"Unexpected response format from Ollama API tags: {data}"
                 logger.warning(msg)
                 current_error = msg

        except requests.exceptions.ConnectionError:
            msg = f"Could not connect to Ollama at {self.BASE_URL}. Is Ollama running?"
            logger.error(msg)
            current_error = msg
            # return [] # Don't return yet, set error and return at end
        except requests.exceptions.Timeout:
            msg = f"Timeout connecting to Ollama at {self.BASE_URL} for models list."
            logger.error(msg)
            current_error = msg
        except requests.exceptions.RequestException as e:
            msg = f"Error fetching models from Ollama API: {e}"
            logger.error(msg)
            current_error = msg
        except json.JSONDecodeError:
             msg = "Error decoding JSON response from Ollama tags endpoint."
             logger.error(msg)
             current_error = msg
        except Exception as e:
             msg = f"An unexpected error occurred while fetching Ollama models: {e}"
             logger.error(msg, exc_info=True)
             current_error = msg

        if current_error:
            self.initialization_error = current_error # Store error for instance status
            return [] # Return empty list on error

        if not available_models:
             logger.warning("No models found via Ollama API /api/tags.")

        return sorted(list(set(available_models))) # Return unique, sorted models


    def format_tool_schema(self, name: str, description: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats tool info into the Ollama/OpenAI compatible function schema structure.
        Ollama's tool format is very similar to OpenAI's.
        """
        if not description:
            logger.warning(f"Tool '{name}' provided to OllamaClient has no description.")
        
        # Only warn if parameters are completely missing or malformed, 
        # but ALLOW valid empty-properties schema for 0-argument tools.
        if parameters is None:
             logger.warning(f"Tool '{name}' provided to OllamaClient has None parameters.")
        elif not isinstance(parameters, dict):
             logger.warning(f"Tool '{name}' provided to OllamaClient has invalid parameters type: {type(parameters)}")

        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description or f"Tool named {name}", # Add default if missing
                "parameters": parameters or {"type": "object", "properties": {}} # Ensure parameters exists
            }
        }

    def send_message_stream_yield(self, messages: list, config: dict, stop_event: threading.Event, instance=None):
        model_name = config.get("model")
        if not model_name:
            yield ("error", "No model specified for Ollama.")
            return

        ollama_options = {} # Initialize ollama_options before any loops

        ollama_options["think"] = True

        # Prepare API messages, including tool role and assistant tool_calls
        api_messages = []

        # --- NEW: Tool Silence Instruction ---
        if self.tool_schemas:
            api_messages.append({
                "role": "system",
                "content": "STRICT RULE: You are in tool-calling mode. Output ONLY the necessary tool calls. Do NOT provide an internal monologue, explanations, or conversational filler. Your entire output should be the tool call sequence or the final JSON."
            })

        for msg in messages:

            role = msg.get("role")
            content = msg.get("content")

            if role == "tool":
                # --- FIXED: Pass tool_call_id to Ollama if available ---
                # This links the result back to the specific call, preventing context loss.
                tool_msg = {
                    "role": "tool",
                    "name": msg.get("name"),
                    "content": str(content)
                }
                if msg.get("tool_call_id"):
                    tool_msg["tool_call_id"] = msg.get("tool_call_id")
                
                api_messages.append(tool_msg)

            elif role == "assistant":
                assistant_msg = {"role": "assistant", "content": content or ""}
                if msg.get("tool_calls"):
                    processed_tool_calls = []
                    for tc in msg["tool_calls"]:
                        args_for_api = tc.get("arguments", {})
                        if not isinstance(args_for_api, dict):
                            try:
                                args_for_api = json.loads(args_for_api)
                                if not isinstance(args_for_api, dict):
                                    logger.warning(f"Ollama: Parsed tool call arguments but not a dict: {args_for_api}. Forcing to empty dict.")
                                    args_for_api = {}
                            except (json.JSONDecodeError, TypeError):
                                logger.warning(f"Ollama: Tool call arguments for '{tc.get('name')}' were a string but not valid JSON: '{args_for_api}'. Using empty dict.")
                                args_for_api = {}
                        
                        # --- FIXED: Include the 'id' and 'type' in the tool call definition ---
                        tool_call_def = {
                            "type": "function",
                            "function": {
                                "name": tc.get("name"),
                                "arguments": args_for_api
                            }
                        }
                        if tc.get("id"):
                            tool_call_def["id"] = tc.get("id")
                            
                        processed_tool_calls.append(tool_call_def)
                    
                    assistant_msg["tool_calls"] = processed_tool_calls
                api_messages.append(assistant_msg)

            elif role in ["user", "system"]:
                # --- RESTORED: Image and File Upload Logic ---
                msg_content_parts = []
                if content:
                    msg_content_parts.append(content)
                images_base64 = []
                files_to_process = []
                if role == "user":
                    if instance and hasattr(instance, '_latest_uploaded_files') and instance._latest_uploaded_files:
                        files_to_process = instance._latest_uploaded_files
                        instance._latest_uploaded_files = []
                    elif msg.get("files"):
                        files_to_process = msg.get("files", [])
                for file_info in files_to_process:
                     if 'image' in file_info.get('mimetype', ''):
                        file_path = file_info.get('path')
                        if file_path and os.path.exists(file_path):
                            try:
                                import base64
                                with open(file_path, "rb") as image_file:
                                    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                                    images_base64.append(base64_image)
                                logger.info(f"Added image {file_info.get('filename')} to Ollama request.")
                            except Exception as e: logger.error(f"Error image {file_path} for Ollama: {e}")
                        else: logger.warning(f"Image path not found: {file_path}")
                final_content = "\n".join(msg_content_parts).strip() if msg_content_parts else ""
                message_payload = {"role": role, "content": final_content}
                if images_base64: message_payload["images"] = images_base64
                api_messages.append(message_payload)
            else:
                logger.warning(f"OllamaClient: Skipping message with unknown role: {role}")


        # Prepare Ollama specific options FROM THE 'config' ARGUMENT
        ollama_param_map = {
            "temperature": "temperature",
            "top_p": "top_p",
            "top_k": "top_k",
            "max_tokens": "num_predict",
        }

        for gen_param_key, ollama_key in ollama_param_map.items():
            if config.get(gen_param_key) is not None:
                 ollama_options[ollama_key] = config[gen_param_key]

        # Handle stop sequences separately
        if config.get("stop_sequences"):
            stops = config["stop_sequences"]
            if isinstance(stops, str) and stops.strip():
                ollama_options["stop"] = [stops.strip()]
            elif isinstance(stops, list) and all(isinstance(s, str) for s in stops):
                ollama_options["stop"] = [s for s in stops if s.strip()] 
            if "stop" in ollama_options and not ollama_options["stop"]: 
                 del ollama_options["stop"]


        data = {
            "model": model_name,
            "messages": api_messages,
            "stream": True,
            "options": ollama_options 
        }

        if self.tool_schemas:
            # DEBUG: Print the names of tools actually sent to the model
            tool_names = [t['function']['name'] for t in self.tool_schemas]
            print(f"DEBUG: Sending tools to Ollama: {tool_names}") 
            
            data["tools"] = self.tool_schemas
            logger.info(f"OllamaClient: Providing {len(self.tool_schemas)} tools definition to {model_name}.")

        headers = {"Content-Type": "application/json"}
        full_response_content = ""
        accumulated_tool_calls = []

        try:
            response = requests.post(
                f"{self.BASE_URL}/api/chat", headers=headers, json=data, stream=True, timeout=300
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if stop_event.is_set():
                    logger.info("Ollama Client: Stop event detected.")
                    yield ("stopped", full_response_content); return

                if line:
                    decoded_line = line.decode('utf-8')
                    try:
                        chunk = json.loads(decoded_line)
                        if "error" in chunk:
                            logger.error(f"Ollama API stream error: {chunk['error']}")
                            yield ("error", f"Ollama API Error: {chunk['error']}"); return
                        message_chunk = chunk.get("message", {})

                        if message_chunk.get("thinking"):
                            yield ("thinking", message_chunk.get("thinking"))
                            continue # Skip the rest so it doesn't mess up content processing
                        
                        # Handle standard content
                        if message_chunk.get("role") == "assistant":
                            chunk_text = message_chunk.get("content")
                            if chunk_text:
                                full_response_content += chunk_text
                                yield ("chunk", chunk_text)
                        
                        # Handle tool calls in response
                        if message_chunk.get("tool_calls"):
                            for tc_ollama in message_chunk["tool_calls"]:
                                if "function" in tc_ollama:
                                    func_data = tc_ollama["function"]
                                    # Generate ID if missing, or use provided ID
                                    call_id = f"ollama_{func_data.get('name', 'tool')}_{int(time.time()*1000)}_{len(accumulated_tool_calls)}"
                                    # --- FIXED: Check if Ollama provided an explicit ID (e.g. from Llama 3.1) ---
                                    # NOTE: The chunk usually doesn't have the ID, it's aggregated. 
                                    # But if 'tc_ollama' has 'id', we should use it? 
                                    # Usually Ollama streams parts, but 'tool_calls' in chunks are often complete objects in newer versions.
                                    # We'll stick to generating one if missing to be safe.
                                    
                                    accumulated_tool_calls.append({
                                        "id": call_id, 
                                        "type": "function",
                                        "name": func_data.get("name"),
                                        "arguments": func_data.get("arguments", {})
                                    })
                        
                        if chunk.get("done") is True:
                            if accumulated_tool_calls:
                                yield ("tool_calls", {"calls": accumulated_tool_calls, "text": full_response_content})
                            else:
                                yield ("finish", full_response_content)
                            return
                    except json.JSONDecodeError:
                        logger.warning(f"Ollama JSON Decode Error in stream: {decoded_line}")
                        continue
            if not stop_event.is_set():
                 logger.warning("Ollama stream ended without 'done: true' marker.")
                 if accumulated_tool_calls: yield ("tool_calls", {"calls": accumulated_tool_calls, "text": full_response_content})
                 else: yield ("finish", full_response_content)
        except requests.exceptions.ConnectionError:
            yield ("error", f"Connection Error: Could not connect to Ollama at {self.BASE_URL}.")
        except requests.exceptions.Timeout:
            yield ("error", f"Timeout connecting to Ollama at {self.BASE_URL}.")
        except requests.exceptions.HTTPError as e:
            error_detail = f"HTTP Error: {e.response.status_code}"
            try:
                error_json = e.response.json(); error_detail += f" - {error_json.get('error', e.response.text)}"
            except json.JSONDecodeError: error_detail += f" - {e.response.text}"
            yield ("error", error_detail)
        except requests.exceptions.RequestException as e:
            yield ("error", f"Network/Request Error: {e}")
        except Exception as e:
            logger.error(f"Unexpected Error in Ollama Client: {e}", exc_info=True)
            yield ("error", f"Unexpected Client Error: {type(e).__name__} - {e}")
        finally:
             logger.info("OllamaClient send_message_stream_yield finished.")