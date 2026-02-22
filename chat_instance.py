# chat_instance.py

import uuid
import datetime
import json
import threading
import os
import time
import traceback
from typing import List, Dict, Any

from api_clients.base_client import BaseApiClient
# We now rely on the new ToolManager instead of the old registry
from tool_management import ToolManager
from utils import send_text_to_audio_server

class ChatInstance:
    def __init__(self, instance_id=None, api_client_class=None, api_key=None, name=None):
        self.instance_id = instance_id or str(uuid.uuid4())
        self.name = name or f"Chat-{self.instance_id[:4]}"
        
        # Core Components
        self.tool_manager = ToolManager()
        self.api_client: BaseApiClient | None = None
        
        # State
        self.api_client_class_name = None
        self.last_used = time.time()
        self.api_key_used = None
        self.connection_error = None
        self._latest_user_content = ""
        self._latest_uploaded_files = []
        
        self.selected_model = ""
        self.available_models_list: List[str] = []
        self.system_prompt = ""
        self.chat_history = []
        self.edit_log = []
        self.generation_params = {"temperature": 0.7, "top_p": 0.95}
        
        # Threading
        self.current_generation_thread = None
        self.stop_event = threading.Event()
        self.sse_queue = None
        self.is_generating = False

        # Build initial map for auto-discovery
        self.tool_manager.build_module_map()

        if api_client_class and api_key:
            self.connect(api_client_class, api_key)
        elif api_client_class:
            self.api_client_class_name = api_client_class.__name__

    # --- Tool Delegation Methods ---

    def _sync_tools_to_client(self):
        """
        CRITICAL: Completely refreshes the API client's toolset.
        This prevents 'ghost tools' by clearing the client's state and re-registering
        only what is currently in ToolManager.
        """
        if not self.api_client: return

        print(f"Syncing {len(self.tool_manager.active_tools)} tools to client...")
        
        # 1. Clear existing client tools if the client supports it
        if hasattr(self.api_client, 'registered_tools'):
            self.api_client.registered_tools = {}
        if hasattr(self.api_client, 'tool_schemas'):
            self.api_client.tool_schemas = []

        # 2. Re-register everything from our source of truth
        for name, tool_data in self.tool_manager.active_tools.items():
            try:
                self.api_client.register_tool(
                    name, 
                    tool_data['func'], 
                    tool_data['description'], 
                    tool_data['parameters']
                )
            except Exception as e:
                print(f"Error syncing tool {name}: {e}")
                self.connection_error = f"Tool Sync Error: {e}"

    def register_tool(self, name, module_path, function_name):
        """Registers a tool and immediately syncs the API client."""
        success = self.tool_manager.register_tool(name, module_path, function_name)
        if success:
            self._sync_tools_to_client()
        return success

    def unregister_tool(self, tool_name):
        """Unregisters a tool and immediately syncs the API client."""
        self.tool_manager.unregister_tool(tool_name)
        self._sync_tools_to_client()

    # --- Connection & Config ---

    def connect(self, api_client_class, api_key):
        self.connection_error = None
        try:
            self.api_client = api_client_class(api_key=api_key)
            self.api_client_class_name = api_client_class.__name__
            self.api_key_used = api_key

            if hasattr(self.api_client, 'initialization_error') and self.api_client.initialization_error:
                raise Exception(self.api_client.initialization_error)

            # 1. Sync Tools IMMEDIATELY upon connection
            self._sync_tools_to_client()

            # 2. Fetch Models
            try:
                self.available_models_list = self.get_available_models() or []
            except Exception as e:
                print(f"Model fetch error: {e}")
                self.available_models_list = []

            # 3. Set Default Model
            if self.available_models_list and not self.selected_model:
                self.selected_model = self.available_models_list[0]
            
            return True

        except Exception as e:
            print(f"Connection Failed: {e}")
            self.connection_error = str(e)
            self.api_client = None
            return False

    def connect_api_client(self, provider_name):
        # Helper to connect using environment variables
        from chat_manager import API_CLIENT_CLASSES
        client_class = API_CLIENT_CLASSES.get(provider_name)
        env_key = f"{provider_name.upper().replace('CLIENT','').replace('.','_')}_API_KEY"
        api_key = os.getenv(env_key)
        if client_class and (api_key or provider_name == "Ollama"): # Ollama might not need a key
             return self.connect(client_class, api_key)
        self.connection_error = f"Credentials not found for {provider_name}"
        return False

    def get_available_models(self) -> List[str]:
        if self.api_client:
            return self.api_client.get_available_models()
        return []

    def set_config(self, model=None, system_prompt=None, temp=None, top_p=None):
        if model is not None: self.selected_model = model
        if system_prompt is not None: self.system_prompt = system_prompt
        if temp is not None: 
            try: self.generation_params['temperature'] = float(temp)
            except: pass
        if top_p is not None: 
            try: self.generation_params['top_p'] = float(top_p)
            except: pass

    def update_last_used(self):
        """Updates the last_used timestamp. Fixes the AttributeError crash."""
        self.last_used = time.time()

    # --- Generation Logic ---

    def start_streaming_generation(self, queue):
        if self.is_generating: return
        
        self.stop_event.clear()
        self.sse_queue = queue
        self.is_generating = True
        
        config = {"model": self.selected_model, **self.generation_params}
        messages = self._prepare_messages()

        self.current_generation_thread = threading.Thread(
            target=self._run_generation_in_thread,
            args=(messages, config),
            daemon=True
        )
        self.current_generation_thread.start()

    def _prepare_messages(self):
        msgs = []
        if self.system_prompt:
            # Only add system prompt if history doesn't already start with one
            if not self.chat_history or self.chat_history[0].get("role") != "system":
                msgs.append({"role": "system", "content": self.system_prompt})
        msgs.extend(self.chat_history)
        return msgs

    def _run_generation_in_thread(self, current_messages, config):
        max_cycles = 15
        cycles = 0
        final_type = "finish"
        final_content = ""

        try:
            while cycles < max_cycles:
                cycles += 1
                if self.stop_event.is_set(): 
                    final_type = "stopped"
                    break

                # -- API Stream Loop --
                text_buffer = ""
                thought_buffer = ""
                tool_calls = []
                cycle_finished = False

                for chunk_type, data in self.api_client.send_message_stream_yield(
                    current_messages, config, self.stop_event, instance=self
                ):
                    if self.stop_event.is_set(): break
                    
                    if chunk_type == "chunk":
                        text_buffer += data
                        self.sse_queue.put(json.dumps({"type": "chunk", "content": data}))
                    elif chunk_type == "thinking":
                        thought_buffer += data
                        self.sse_queue.put(json.dumps({"type": "thinking", "content": data}))
                    elif chunk_type == "tool_calls":
                        tool_calls = data.get("calls", [])
                        text_buffer = data.get("text", text_buffer)
                        cycle_finished = True
                    elif chunk_type == "finish":
                        text_buffer = data
                        cycle_finished = True
                    elif chunk_type == "error":
                        raise Exception(data)

                # -- Cycle Handling --
                if not tool_calls:
                    final_content = text_buffer
                    msg = {"role": "assistant", "content": final_content, "timestamp": datetime.datetime.now().isoformat()}
                    if thought_buffer:
                        msg["thoughts"] = thought_buffer
                    current_messages.append(msg)
                    break # Conversation Turn Complete
                
                # -- Tool Execution --
                final_content = text_buffer # Save partial text
                
                # 1. Add Assistant Request to History
                msg = {
                    "role": "assistant", 
                    "content": text_buffer, 
                    "tool_calls": tool_calls,
                    "timestamp": datetime.datetime.now().isoformat()
                }
                if thought_buffer:
                    msg["thoughts"] = thought_buffer
                current_messages.append(msg)
                
                self.sse_queue.put(json.dumps({"type": "status", "content": f"Executing {len(tool_calls)} tools..."}))

                # 2. Execute and Append Results
                for call in tool_calls:
                    result = self._execute_tool_safe(call["name"], call["arguments"])
                    current_messages.append({
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "name": call["name"],
                        "content": result
                    })
                    self.sse_queue.put(json.dumps({
                        "type": "tool_result", 
                        "content": {"name": call["name"], "result_preview": str(result)[:100]+"..."}
                    }))

        except Exception as e:
            final_type = "error"
            final_content = str(e)
            traceback.print_exc()

        finally:
            self.is_generating = False
            if final_type != "error":
                self.chat_history = current_messages # Commit history
            
            self.sse_queue.put(json.dumps({"type": final_type, "content": final_content}))
            self.sse_queue.put(None)
            
            # Auto-save
            from chat_manager import chat_manager
            chat_manager.save_instance_state(self.instance_id)

    def _execute_tool_safe(self, name, args):
        """Executes a tool via the API client wrapper or directly via ToolManager."""
        try:
            # Special logic for 'search_for_tool' proxy
            if name == "search_for_tool":
                return "Tool discovery is handled by the UI. Please check the 'Tools' tab."

            # Standard Execution
            func = self.tool_manager.get_tool(name)
            if not func:
                return f"Error: Tool {name} not found."
            
            return str(func(**args))
        except Exception as e:
            return f"Tool Execution Error: {e}"

    # --- State Management ---

    @property
    def tools_definitions(self):
        """Exposes tool definitions for the UI template."""
        return self.tool_manager.get_definitions()

    def get_state(self):
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
            "tools_definitions": self.tools_definitions # Use the property
        }

    @classmethod
    def from_state(cls, state, api_client_classes):
        inst = cls(instance_id=state.get("instance_id"), name=state.get("name"))
        
        # Restore simple properties
        inst.selected_model = state.get("selected_model", "")
        inst.last_used = state.get("last_used", time.time())
        inst.system_prompt = state.get("system_prompt", "")
        inst.chat_history = state.get("chat_history", [])
        inst.generation_params = state.get("generation_params", {})
        inst.available_models_list = state.get("available_models_list", [])
        
        # Restore Tools
        inst.tool_manager.load_definitions(state.get("tools_definitions", {}))
        
        # Reconnect logic
        inst.api_client_class_name = state.get("api_client_class_name")
        
        return inst
        
    def stop_generation(self):
        if self.is_generating: self.stop_event.set()

    def clear_history(self):
        self.stop_generation()
        self.chat_history = []