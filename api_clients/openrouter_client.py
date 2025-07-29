# api_clients/openrouter_client.py
import requests # Add requests for get_available_models
import json
import threading
import os
from openai import OpenAI, APIError, APIConnectionError, RateLimitError # Keep OpenAI library
from .base_client import BaseApiClient
from typing import List, Dict, Any, Tuple, Generator, Callable
import logging

logger = logging.getLogger(__name__)

class OpenRouterClient(BaseApiClient):
    BASE_URL = "https://openrouter.ai/api/v1"
    

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.openai_client = None
        self.initialization_error = None
        try:
            # Configure the OpenAI client to point to OpenRouter
            self.openai_client = OpenAI(
                base_url=self.BASE_URL,
                api_key=self.api_key,
                default_headers={
                    "HTTP-Referer": os.getenv("APP_REFERER", "http://localhost:5000"),
                    "X-Title": os.getenv("APP_TITLE", "WebMultiChat"),
                },
                timeout=300.0,
            )
            # self._check_connection() # You can keep or remove this OpenAI lib based check
            logger.info("OpenRouterClient initialized using OpenAI SDK for chat operations.")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client for OpenRouter: {e}", exc_info=True)
            self.initialization_error = str(e)

    def _check_connection(self): # This method uses the OpenAI client
        """Optional: Check connection by listing models (may use quota)."""
        if not self.openai_client:
            self.initialization_error = "OpenAI client for OpenRouter not created."
            return False
        try:
            self.openai_client.models.list() # Simple API call using the OpenAI library
            logger.info("OpenRouter connection check successful (listed models via OpenAI SDK).")
            self.initialization_error = None
            return True
        except Exception as e:
            logger.warning(f"OpenRouter connection check via OpenAI SDK failed: {e}")
            # Don't overwrite initialization_error if client itself initialized fine
            # self.initialization_error = f"Connection Check Failed: {e}"
            return False

    def format_tool_schema(self, name: str, description: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats tool info into the OpenAI function/tool schema structure.
        (This method remains unchanged)
        """
        if not description:
             logger.warning(f"Tool '{name}' provided to OpenRouterClient has no description.")
        if not parameters or not parameters.get("properties"):
             logger.warning(f"Tool '{name}' provided to OpenRouterClient has no parameters defined.")

        return {
            "name": name,
            "description": description or f"Tool named {name}",
            "parameters": parameters or {"type": "object", "properties": {}}
        }

    # --- NEW get_available_models METHOD ---
    def get_available_models(self) -> list[str]:
        """
        Fetches available models from OpenRouter API.
        It can be further filtered (e.g., for free models) if desired.
        """
        model_ids = []
        models_url = f"{self.BASE_URL}/models"
        # OpenRouter API key might be needed for /models endpoint too,
        # though some public info endpoints don't require it.
        # It's good practice to send it if available.
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            # Add a timeout to the request
            response = requests.get(models_url, headers=headers, timeout=10) # 10 second timeout
            response.raise_for_status()
            data = response.json()

            if "data" in data and isinstance(data["data"], list):
                for model_info in data["data"]:
                    model_id = model_info.get("id")
                    if model_id:
                        pricing = model_info.get("pricing")
                        if (pricing and isinstance(pricing, dict) and
                            "prompt" in pricing and "completion" in pricing):
                            try:
                                prompt_cost = float(pricing["prompt"])
                                completion_cost = float(pricing["completion"])
                                if prompt_cost == 0.0 and completion_cost == 0.0:
                                    model_ids.append(model_id)
                            except (ValueError, TypeError):
                                logger.warning(f"Could not parse pricing for model {model_id}. Pricing: {pricing}")
                                continue
                        # --- MODIFICATION: Include ALL models, not just free ---
                        # You can add filtering logic here if needed (e.g. based on pricing or context_length)
                        # Example: Filtering for models supporting a certain context length
                        # context_length = model_info.get("context_length")
                        # if context_length and context_length >= 8000:
                        #    model_ids.append(model_id)

                        # For now, let's add all models that have an ID
                        model_ids.append(model_id)

                        # --- Original Free Model Filtering Logic (can be uncommented if desired) ---
                        # pricing = model_info.get("pricing")
                        # if (pricing and isinstance(pricing, dict) and
                        #     "prompt" in pricing and "completion" in pricing):
                        #     try:
                        #         prompt_cost = float(pricing["prompt"])
                        #         completion_cost = float(pricing["completion"])
                        #         if prompt_cost == 0.0 and completion_cost == 0.0:
                        #             model_ids.append(model_id)
                        #     except (ValueError, TypeError):
                        #         logger.warning(f"Could not parse pricing for model {model_id}. Pricing: {pricing}")
                        #         continue
            else:
                logger.warning(f"OpenRouter /models response missing 'data' list: {data}")


        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching models from OpenRouter API: {models_url}")
            return [] # Return empty on timeout
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching models from OpenRouter API: {e}")
            return [] # Return empty on other request errors
        except json.JSONDecodeError:
             logger.error(f"Error decoding JSON response from OpenRouter models endpoint.")
             return []
        except Exception as e: # Catch any other unexpected errors
             logger.error(f"An unexpected error occurred while fetching models from OpenRouter: {e}", exc_info=True)
             return []

        if not model_ids:
            logger.warning("No models fetched from OpenRouter API. Check connection or API response.")
            # Optionally, fall back to a hardcoded list if desired
            # return self.KNOWN_MODELS_FALLBACK
        else:
            logger.info(f"Fetched {len(model_ids)} models from OpenRouter.")

        return sorted(list(set(model_ids))) # Return unique, sorted models

    # --- send_message_stream_yield METHOD (using OpenAI library - from your existing codebase) ---
    def send_message_stream_yield(self,
                                messages: List[Dict[str, Any]],
                                config: Dict[str, Any],
                                stop_event: threading.Event,
                                instance=None
                                ) -> Generator[Tuple[str, Any], None, None]:

        if not self.openai_client or self.initialization_error:
             error_msg = self.initialization_error or "OpenRouter client not initialized."
             logger.error(f"OpenRouter send_message_stream_yield: {error_msg}")
             yield ("error", f"Client Error: {error_msg}"); return

        model_name = config.get("model")
        if not model_name:
            logger.error("OpenRouter send_message_stream_yield: No model specified.")
            yield ("error", "No model specified."); return

        # --- Prepare Tools for OpenAI format ---
        openai_tools = None
        if self.tool_schemas:
            openai_tools = [{"type": "function", "function": schema} for schema in self.tool_schemas]
            logger.info(f"Providing {len(openai_tools)} tools to OpenRouter model {model_name}")

        # --- Prepare Messages for OpenAI format ---
        api_messages = []
        # (Logic for preparing api_messages for OpenAI client - from your existing codebase)
        # This includes handling roles (user, assistant, tool) and tool_calls structure
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            files_data = msg.get("files") # Get files if present

            # OpenAI image input format for user messages:
            # "content": [
            #   {"type": "text", "text": "What’s in this image?"},
            #   {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,{base64_image}"}}
            # ]
            current_content_parts = []

            # Add text part
            if content:
                current_content_parts.append({"type": "text", "text": content})

            # Add image parts (if any and role is user)
            if role == "user" and files_data:
                if instance and hasattr(instance, '_latest_uploaded_files') and instance._latest_uploaded_files:
                    # Use instance's latest files if available (for current turn)
                    files_to_process = instance._latest_uploaded_files
                    instance._latest_uploaded_files = [] # Clear after processing
                else:
                    # Use files from history
                    files_to_process = files_data

                for file_info in files_to_process:
                    if 'image' in file_info.get('mimetype', ''):
                        file_path = file_info.get('path')
                        if file_path and os.path.exists(file_path):
                            try:
                                import base64
                                with open(file_path, "rb") as image_file:
                                    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                                current_content_parts.append({
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{file_info['mimetype']};base64,{base64_image}"
                                    }
                                })
                                logger.info(f"Added image {file_info.get('filename')} to OpenRouter request.")
                            except Exception as e:
                                logger.error(f"Error processing image file {file_path} for OpenRouter: {e}")
                        else:
                            logger.warning(f"Image file path not found or invalid: {file_path}")
                    # else: # Handle other file types if model supports it differently
                    #    logger.info(f"Skipping non-image file {file_info.get('filename')} for OpenRouter content.")


            if role == "tool":
                api_messages.append({
                    "role": "tool",
                    "tool_call_id": msg.get("tool_call_id", f"tool_{msg.get('name', 'unknown')}_{int(threading.TIMEOUT_MAX * 1000)}"), # Ensure an ID
                    "name": msg.get("name"), # Some models might prefer name here
                    "content": str(content)
                })
            elif role == "assistant":
                 assistant_msg = {"role": "assistant"}
                 # Content can be None/empty if only tool calls
                 if content:
                     assistant_msg["content"] = content

                 if msg.get("tool_calls"):
                      # Ensure format matches OpenAI's expected structure
                      processed_tool_calls = []
                      for tc in msg["tool_calls"]:
                          # Arguments should already be a string (JSON string) for OpenAI client
                          # If they are dicts, they need to be json.dumps'd
                          args_for_api = tc.get("arguments", {})
                          if isinstance(args_for_api, dict):
                              args_for_api = json.dumps(args_for_api)

                          processed_tool_calls.append({
                               "id": tc.get("id"),
                               "type": "function", # Assuming 'function' type
                               "function": {"name": tc.get("name"), "arguments": args_for_api}
                          })
                      assistant_msg["tool_calls"] = processed_tool_calls

                 # Only append if it has content OR tool_calls
                 if "content" in assistant_msg or "tool_calls" in assistant_msg:
                    api_messages.append(assistant_msg)

            elif role in ["user", "system"]:
                if current_content_parts: # If images were added, content is a list
                    api_messages.append({"role": role, "content": current_content_parts})
                elif content: # Just text content
                    api_messages.append({"role": role, "content": content})
                # If no content and no parts (e.g. system prompt is empty), don't append.
            else:
                logger.warning(f"Skipping message with unknown role for OpenRouter: {role}")


        if not api_messages and not openai_tools: # Check if there's anything to send
            logger.warning("OpenRouter: No messages or tools to send to API.")
            yield ("error", "No messages or tools to send."); return

        # logger.debug(f"OpenRouter API Messages: {json.dumps(api_messages, indent=2)}")

        # --- API Call using self.openai_client ---
        try:
            stream = self.openai_client.chat.completions.create(
                model=model_name,
                messages=api_messages,
                tools=openai_tools if openai_tools else None,
                tool_choice="auto",
                temperature=config.get("temperature", 0.7),
                top_p=config.get("top_p", 1.0),
                stream=True,
                # max_tokens=config.get("max_tokens"), # Optional
            )

            accumulated_text = ""
            # For aggregating tool call arguments that might come in multiple chunks
            current_tool_calls_agg: Dict[int, Dict[str, Any]] = {}

            for chunk in stream:
                if stop_event.is_set():
                    logger.info("Stop event detected during OpenRouter stream.")
                    yield ("stopped", accumulated_text); return

                delta = chunk.choices[0].delta if chunk.choices and len(chunk.choices) > 0 else None
                finish_reason = chunk.choices[0].finish_reason if chunk.choices and len(chunk.choices) > 0 else None

                if delta:
                    if delta.content:
                        accumulated_text += delta.content
                        yield ("chunk", delta.content)

                    if delta.tool_calls:
                        for tool_call_chunk in delta.tool_calls:
                            index = tool_call_chunk.index # Tool call index in the list of calls

                            if index not in current_tool_calls_agg:
                                # First time we see this tool call index
                                if tool_call_chunk.id: # ID comes in the first chunk
                                    current_tool_calls_agg[index] = {
                                        "id": tool_call_chunk.id,
                                        "type": tool_call_chunk.type or "function", # Should be 'function'
                                        "function": {
                                            "name": tool_call_chunk.function.name if tool_call_chunk.function else "",
                                            "arguments": tool_call_chunk.function.arguments if tool_call_chunk.function else ""
                                        }
                                    }
                                else: # Should not happen if ID is always first
                                    current_tool_calls_agg[index] = { "function": { "arguments": "" }}
                            else:
                                # Subsequent chunk for an existing tool call, append arguments
                                if tool_call_chunk.function and tool_call_chunk.function.arguments:
                                     current_tool_calls_agg[index]["function"]["arguments"] += tool_call_chunk.function.arguments


                if finish_reason:
                    logger.info(f"OpenRouter stream finished. Reason: {finish_reason}")
                    if finish_reason == "tool_calls":
                        final_tool_calls = []
                        for index, tool_info_agg in sorted(current_tool_calls_agg.items()):
                             try:
                                 # Arguments should be a complete JSON string now
                                 parsed_args = json.loads(tool_info_agg["function"]["arguments"])
                             except json.JSONDecodeError:
                                 logger.error(f"Failed to parse JSON arguments for tool {tool_info_agg['function'].get('name')}: {tool_info_agg['function']['arguments']}")
                                 parsed_args = {"error": "failed to parse arguments", "raw_arguments": tool_info_agg["function"]["arguments"]}
                             final_tool_calls.append({
                                 "id": tool_info_agg["id"],
                                 "type": tool_info_agg.get("type", "function"),
                                 "name": tool_info_agg["function"].get("name"), # Get name from aggregated info
                                 "arguments": parsed_args
                             })
                        yield ("tool_calls", {"calls": final_tool_calls, "text": accumulated_text})
                    elif finish_reason == "stop":
                        yield ("finish", accumulated_text)
                    elif finish_reason == "length":
                        yield ("finish", accumulated_text + "\n[MAX TOKENS REACHED]") # Indicate truncation
                    elif finish_reason == "content_filter":
                         yield ("error", "Content filtered by API.")
                    else:
                        logger.warning(f"OpenRouter generation stopped by model for unknown reason: {finish_reason}")
                        yield ("error", f"Generation stopped: {finish_reason}")
                    return

        except APIError as e:
            logger.error(f"OpenRouter API Error: {e.status_code} - {e.message}", exc_info=True)
            yield ("error", f"API Error ({e.status_code}): {e.message}")
        except APIConnectionError as e:
            logger.error(f"OpenRouter Connection Error: {e}", exc_info=True)
            yield ("error", "Network connection error.")
        except RateLimitError as e:
            logger.error(f"OpenRouter Rate Limit Error: {e}", exc_info=True)
            yield ("error", "Rate limit exceeded. Please check your OpenRouter plan and usage.")
        except Exception as e:
            logger.error(f"Unexpected Error during OpenRouter stream: {e}", exc_info=True)
            yield ("error", f"Unexpected Client Error: {type(e).__name__} - {e}")
        finally:
            logger.info("OpenRouterClient send_message_stream_yield finished.")

# No __main__ needed here as it's part of a larger application