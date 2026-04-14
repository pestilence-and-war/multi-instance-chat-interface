from flask import Flask, render_template, request, Response, stream_with_context, jsonify, session, url_for, send_from_directory
import json
import queue
import time
import os
import sys
import subprocess
import datetime
from chat_manager import chat_manager, API_CLIENT_CLASSES, DEFAULT_PROVIDER
from chat_instance import ChatInstance
from utils import markdown_to_html, format_timestamp
import utils
import dotenv
import importlib
import importlib.util

# --- Persona Integration ---
# Import the module directly, not a class
from my_tools import persona_manager
from my_tools.codebase_manager import _CodebaseManager

dotenv.load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

# --- Project Root Configuration ---
CONFIG_FILE = "project_config.json"

def load_project_root():
    """Loads the target project root from config file if available."""
    # Resolve config file path relative to this script
    app_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(app_dir, CONFIG_FILE)

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                root = config.get('project_root')
                if root and os.path.isdir(root):
                    print(f"Setting target project root to: {root}")
                    # Only set the environment variable for tools to use
                    os.environ["CODEBASE_DB_PATH"] = root
        except Exception as e:
            print(f"Error loading project config: {e}")

# Load project root before initializing chat_manager
load_project_root()

# --- Jinja Filters & Context ---
@app.template_filter('markdown')
def markdown_filter(s):
    return markdown_to_html(s or "")

@app.template_filter('format_time')
def format_time_filter(s):
    return format_timestamp(s)

@app.context_processor
def inject_global_context():
    # Use the env var as the source of truth for the UI
    current_root = os.environ.get("CODEBASE_DB_PATH", os.getcwd())
    return dict(
        utils=utils,
        API_CLIENT_CLASSES=API_CLIENT_CLASSES,
        DEFAULT_PROVIDER=DEFAULT_PROVIDER,
        providers=list(API_CLIENT_CLASSES.keys()),
        available_personas=json.loads(persona_manager.list_personas()).get('personas', []),
        current_project_root=current_root
    )

# === Main Routes ===

@app.route('/config/project-root', methods=['POST'])
def set_project_root():
    new_root = request.form.get('project_root')
    if not new_root:
        return "<span class='text-red-500'>Error: No path provided.</span>", 400
    
    # Resolve to absolute path immediately
    new_root = os.path.abspath(new_root)

    if not os.path.isdir(new_root):
        return f"<span class='text-red-500'>Error: Directory '{new_root}' does not exist.</span>", 400
    
    try:
        # Update environment variable for tools
        os.environ["CODEBASE_DB_PATH"] = new_root
        
        # Reset database connections to ensure new path is used
        try:
             _CodebaseManager.reset_connections()
        except Exception as e:
             print(f"Warning: Failed to reset codebase manager connections: {e}")
        
        # Persist to config
        app_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(app_dir, CONFIG_FILE)
        
        with open(config_path, 'w') as f:
            json.dump({'project_root': new_root}, f)
            
        # --- NEW: Monitor Safety ---
        global monitor_process
        monitor_msg = ""
        if monitor_process is not None and monitor_process.poll() is None:
            monitor_process.terminate()
            monitor_process = None
            monitor_msg = " (Monitor stopped - please restart it for the new workspace)"
        
        return f"<span class='text-green-500'>Success! Target set to {new_root}.{monitor_msg}</span>"
    except Exception as e:
        return f"<span class='text-red-500'>Error: {e}</span>", 500

@app.route('/project/build-db', methods=['POST'])
def build_project_db():
    target_root = os.environ.get("CODEBASE_DB_PATH", os.getcwd())
    app_dir = os.path.dirname(os.path.abspath(__file__))
    
    # --- Step 1: Ensure venv exists ---
    venv_script = os.path.join(app_dir, 'venv_setup.py')
    print(f"Ensuring venv for {target_root} using {venv_script}...")
    try:
        venv_result = subprocess.run(
            [sys.executable, venv_script, target_root],
            cwd=app_dir,
            capture_output=True,
            text=True,
            check=True
        )
        print("Venv Setup Output:", venv_result.stdout)
    except Exception as e:
        print(f"Warning: Venv setup failed: {e}")
        # We continue anyway, but the build might fail or use global python

    # --- Step 2: Build Database ---
    script_path = os.path.join(app_dir, 'build_code_db.py')
    print(f"Building DB for {target_root} using {script_path}...")
    
    # Release any existing locks
    try:
        _CodebaseManager.reset_connections()
    except Exception as e:
        print(f"Warning: Failed to reset codebase manager connections before build: {e}")

    try:
        # Run the build script
        # We set cwd to app_dir to ensure any local imports in the script works (if any)
        # But we pass target_root as the argument.
        result = subprocess.run(
            [sys.executable, script_path, target_root], 
            cwd=app_dir,
            capture_output=True, 
            text=True, 
            check=True,
            timeout=120 # Prevent hanging indefinitely
        )
        print("DB Build Output:", result.stdout)
        return f"<span class='text-green-500'>Database built successfully! ({len(result.stdout)} chars output)</span>"
    except subprocess.TimeoutExpired:
        return f"<span class='text-red-500'>Build Timed Out (> 120s). Check server logs.</span>", 504
    except subprocess.CalledProcessError as e:
        print("DB Build Error:", e.stderr)
        return f"<span class='text-red-500'>Build Failed: {e.stderr[:200]}...</span>", 500
    except Exception as e:
        return f"<span class='text-red-500'>Error: {e}</span>", 500

@app.route('/')
def index():
    try:
        sorted_instances = chat_manager.get_all_instances_sorted()
        initial_instance_obj = sorted_instances[0] if sorted_instances else None
        print(f"Rendering index. Sorted instance IDs: {[inst.instance_id for inst in sorted_instances]}")
        return render_template(
            'index.html',
            active_instance_objects=sorted_instances,
            initial_instance=initial_instance_obj
        )
    except Exception as e:
        import traceback
        print(f"ERROR in '/' route: {e}\n{traceback.format_exc()}")
        return "<h1>Server Error</h1><p>Could not load chat interface.</p>", 500

@app.route('/personas/instantiate', methods=['POST'])
def instantiate_persona_route():
    persona_name = request.form.get('persona_name')
    
    if not persona_name:
        return "<div class='text-red-500 p-4'>Error: Persona name not provided.</div>", 400

    # The instantiate_persona function now lives in the module and needs the chat_manager passed to it
    instance, message = persona_manager.instantiate_persona(persona_name, chat_manager)

    if not instance:
        return f"<div class='text-red-500 p-4'>{message}</div>", 500

    # This response is designed for HTMX. It renders the new chat instance view
    # and sends an event to the frontend to add the new tab.
    response_html = render_template('chat_instance.html', instance=instance)
    response = Response(response_html)
    response.headers['HX-Trigger'] = json.dumps({
        "addTab": {"id": instance.instance_id, "name": instance.name}
    })
    return response, 200


@app.route('/chat/new', methods=['POST'])
def new_chat():
    provider = request.form.get('provider', DEFAULT_PROVIDER)
    api_key = request.form.get('api_key')

    print(f"Creating new chat with provider: {provider}")
    instance = chat_manager.create_instance(provider_name=provider, api_key=api_key, caller="User")

    if not instance:
        error_msg = "Failed to create instance. Check provider/key settings."
        return f"<div class='text-red-500 p-4'>{error_msg}</div>", 400

    response_html = render_template('chat_instance.html', instance=instance)
    response = Response(response_html)
    response.headers['HX-Trigger'] = json.dumps({
        "addTab": {"id": instance.instance_id, "name": f"{provider[:4]} {instance.instance_id[:4]}"}
    })
    return response, 200


@app.route('/chat/<instance_id>', methods=['GET'])
def get_chat_instance(instance_id):
    instance = chat_manager.get_instance(instance_id)
    if not instance:
        return "<div class='text-red-500 p-4'>Chat instance not found.</div>", 404
    
    instance.update_last_used()
    chat_manager.save_instance_state(instance_id)
    
    print(f"Rendering chat instance {instance_id}. Model: '{instance.selected_model}'")
    return render_template('chat_instance.html', instance=instance)

# ... (rest of the file remains the same)
# Omitting the rest of the file for brevity as no further changes are needed there.
# All other routes from the original app.py would follow here.
# ...
@app.route('/chat/<instance_id>/close', methods=['DELETE'])
def close_chat_instance(instance_id):
    removed = chat_manager.remove_instance(instance_id)
    if removed: return "", 200
    else: return "Instance not found", 404

@app.route('/chat/<instance_id>/rename', methods=['POST'])
def rename_chat(instance_id):
    data = request.json
    new_name = data.get('new_name')
    if not new_name:
        return jsonify({"status": "error", "message": "New name not provided."}), 400
    instance = chat_manager.get_instance(instance_id)
    if not instance:
        return jsonify({"status": "error", "message": "Chat instance not found."}), 404
    instance.name = new_name
    chat_manager.save_instance_state(instance_id)
    return jsonify({"status": "success", "new_name": new_name})

@app.route('/chat/<instance_id>/config', methods=['POST'])
def update_config(instance_id):
    instance = chat_manager.get_instance(instance_id)
    if not instance: return "Not Found", 404
    if instance.is_generating: return Response(status=409, response="Cannot change config while generating.")
    instance.update_last_used()
    data = request.form
    try:
        instance.set_config(
            model=data.get('model'),
            system_prompt=data.get('system_prompt'),
            temp=data.get('temperature'),
            top_p=data.get('top_p'),
            max_turns=data.get('max_turns'),
            thinking=data.get('thinking') == 'on' # Checkbox value is 'on' if checked
        )
        chat_manager.save_instance_state(instance_id)
        return render_template('partials/status_update.html', instance_id=instance_id, message="Config updated.")
    except Exception as e:
        return render_template('partials/status_update.html', instance_id=instance_id, message=f"Error: {e}", is_error=True)

@app.route('/chat/<instance_id>/apply_persona', methods=['POST'])
def apply_persona(instance_id):
    instance = chat_manager.get_instance(instance_id)
    if not instance: return "Not Found", 404
    if instance.is_generating: return Response(status=409, response="Cannot change persona while generating.")
    
    persona_name = request.form.get('persona_name')
    if not persona_name:
        return render_template('partials/status_update.html', instance_id=instance_id, message="No persona selected.", is_error=True)

    try:
        # 1. Get Persona Details
        from my_tools import persona_manager
        details_json = persona_manager.get_persona_details(persona_name)
        details = json.loads(details_json)
        
        if details.get("status") == "error":
            return render_template('partials/status_update.html', instance_id=instance_id, message=f"Persona '{persona_name}' not found.", is_error=True)

        # 2. Update Instance Config (Keep current model and provider)
        model_config = details.get("model_config", {})
        instance.set_config(
            system_prompt=details.get("system_prompt"),
            # We specifically DO NOT override instance.selected_model here
            # to respect the user's UI selection.
            temp=model_config.get("generation_params", {}).get("temperature"),
            thinking=model_config.get("generation_params", {}).get("thinking")
        )

        # 3. Clear and Register Tools
        # We unregister all current tools first for a clean swap
        for tool_name in list(instance.tool_manager.active_tools.keys()):
            instance.unregister_tool(tool_name)
            
        instance.tool_manager.build_module_map()
        for tool_name in details.get("tools", []):
            module_path = instance.tool_manager.tool_module_map.get(tool_name)
            if module_path:
                instance.register_tool(name=tool_name, module_path=module_path, function_name=tool_name)

        instance.name = f"{persona_name} Mode"
        chat_manager.save_instance_state(instance_id)
        
        # Return the whole instance block to refresh the UI with new prompt/tools
        return render_template('chat_instance.html', instance=instance)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return render_template('partials/status_update.html', instance_id=instance_id, message=f"Apply Error: {e}", is_error=True)

@app.route('/chat/<instance_id>/send', methods=['POST'])
def send_user_message(instance_id):
    instance = chat_manager.get_instance(instance_id)
    if not instance: return "Not Found", 404
    if instance.is_generating: return Response(status=409, response="Already generating.")
    instance.update_last_used()
    user_content = request.form.get('user_input', '').strip()
    saved_files_metadata = []
    instance_files_to_process = []

    uploaded_files = request.files.getlist('files')
    for file_storage in uploaded_files:
        if not file_storage or file_storage.filename == '': continue
        safe_filename = "".join(c for c in file_storage.filename if c.isalnum() or c in (' ', '.', '_', '-')).strip()
        if not safe_filename: safe_filename = "uploaded_file"
        filename = f"upload_{int(time.time()*1000)}_{safe_filename}"
        save_path = os.path.join('chat_sessions', filename)
        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            file_storage.save(save_path)
            file_meta = {'path': save_path, 'mimetype': file_storage.mimetype or 'application/octet-stream', 'filename': safe_filename}
            saved_files_metadata.append(file_meta)
            instance_files_to_process.append(file_meta)
        except Exception as e:
            print(f"Error saving file {file_storage.filename}: {e}")

    if not user_content and not instance_files_to_process:
        return Response(status=204)

    instance._latest_user_content = user_content
    instance._latest_uploaded_files = instance_files_to_process

    user_msg = {"role": "user", "content": user_content, "timestamp": datetime.datetime.now().isoformat(), "files": saved_files_metadata}
    instance.chat_history.append(user_msg)
    chat_manager.save_instance_state(instance_id)

    user_html = render_template('partials/message_turn.html', msg=user_msg)
    stream_id = f"stream-{instance_id}-{int(time.time()*1000)}"
    stream_placeholder_html = f'<div id="{stream_id}" class="assistant-streaming-placeholder"></div>'

    response_html = user_html + stream_placeholder_html
    response = Response(response_html)
    response.headers['HX-Trigger'] = json.dumps({f"startSSE-{instance_id}": {"target_id": stream_id}})
    return response

@app.route('/chat/<instance_id>/stream')
def stream_response(instance_id):
    instance = chat_manager.get_instance(instance_id)
    if not instance:
        return Response("data: "+json.dumps({"type":"error", "content":"Chat instance not found."})+"\n\n", status=404, mimetype='text/event-stream')

    sse_message_queue = queue.Queue()
    instance.start_streaming_generation(sse_message_queue)

    @stream_with_context
    def generate_sse():
        try:
            while True:
                try:
                    # Shorter timeout to allow sending heartbeats
                    message_json = sse_message_queue.get(timeout=15)
                    if message_json is None:
                        break
                    yield f"data: {message_json}\n\n"
                    sse_message_queue.task_done()
                except queue.Empty:
                    # Send an SSE heartbeat (comment) to keep the connection alive
                    yield ": heartbeat\n\n"
        except Exception as e:
             yield f"data: {json.dumps({'type': 'error', 'content': f'SSE generator error: {e}'})}\n\n"
        finally:
             pass
    headers = {'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache'}
    return Response(generate_sse(), headers=headers)

@app.route('/chat/<instance_id>/stop', methods=['POST'])
def stop_generation(instance_id):
    instance = chat_manager.get_instance(instance_id)
    if not instance: return "Not Found", 404
    instance.stop_generation()
    return render_template('partials/status_update.html', message="Stop requested.", instance_id=instance_id)

@app.route('/chat/<instance_id>/clear', methods=['POST'])
def clear_chat(instance_id):
    instance = chat_manager.get_instance(instance_id)
    if not instance: return "Not Found", 404
    instance.clear_history()
    chat_manager.save_instance_state(instance_id)
    return render_template('chat_instance.html', instance=instance)

@app.route('/chat/<instance_id>/edit', methods=['GET'])
def get_edit_context_form(instance_id):
    instance = chat_manager.get_instance(instance_id)
    if not instance: return "Not Found", 404
    if instance.is_generating: return "Cannot edit while generating", 409
    return render_template('partials/context_editor.html', instance=instance)

@app.route('/chat/<instance_id>/edit', methods=['POST'])
def save_edited_context(instance_id):
    instance = chat_manager.get_instance(instance_id)
    if not instance: return "Not Found", 404
    if instance.is_generating: return "Cannot edit while generating", 409

    original_history = [msg.copy() for msg in instance.chat_history]
    edited_history = []
    form_keys = list(request.form.keys())
    indices = set()
    for key in form_keys:
        if key.startswith('msg_') and key.endswith('_role'):
            idx_str = key[len('msg_'):-len('_role')]
            if idx_str.startswith('new_'):
                try: idx_val = float(idx_str[len('new_'):]) + 0.5
                except ValueError: continue
            else:
                try: idx_val = int(idx_str)
                except ValueError: continue
            indices.add((idx_val, idx_str))
    sorted_indices = sorted(indices, key=lambda item: item[0])

    for _, idx_str in sorted_indices:
        prefix = f"msg_{idx_str}_"
        role = request.form.get(prefix + 'role', '').strip().lower()
        content = request.form.get(prefix + 'content', '')
        timestamp = request.form.get(prefix + 'timestamp', '')
        if role not in ['user', 'assistant', 'system', 'tool']:
            print(f"Warning: Unexpected role '{role}' found in edit context. Preserving as is.")
        if content.strip() == '' and idx_str.startswith('new_'): continue
        msg_data = {"role": role, "content": content, "timestamp": timestamp}
        
        # --- Handle Thoughts ---
        thoughts = request.form.get(prefix + 'thoughts')
        if thoughts:
             msg_data["thoughts"] = thoughts

        tool_call_id = request.form.get(prefix + 'tool_call_id')
        if tool_call_id:
            if role == 'assistant':
                tool_name = request.form.get(prefix + 'tool_name')
                tool_arguments = request.form.get(prefix + 'tool_arguments')
                
                # Attempt to parse arguments as JSON
                try:
                    tool_args_parsed = json.loads(tool_arguments)
                except (json.JSONDecodeError, TypeError):
                    tool_args_parsed = tool_arguments

                # Use flat structure: {id, name, arguments}
                tool_calls = [{"id": tool_call_id, "name": tool_name, "arguments": tool_args_parsed, "type": "function"}]
                msg_data["tool_calls"] = tool_calls
            elif role == 'tool':
                msg_data["tool_call_id"] = tool_call_id
        edited_history.append(msg_data)
    instance.chat_history = edited_history
    chat_manager.save_instance_state(instance)
    return render_template('partials/status_update.html', message="Context edited and saved.", instance_id=instance_id)

@app.route('/chat/<instance_id>/save_persona', methods=['POST'])
def save_persona(instance_id):
    instance = chat_manager.get_instance(instance_id)
    if not instance: return "Not Found", 404
    
    data = request.form
    persona_name = data.get('new_persona_name')
    competency = data.get('new_persona_competency') or "Custom created persona."
    
    if not persona_name:
        return render_template('partials/status_update.html', instance_id=instance_id, message="Persona name is required.", is_error=True)

    try:
        # 1. Prepare Persona Data
        system_prompt = data.get('system_prompt') or instance.system_prompt
        model = data.get('model') or instance.selected_model
        # Get provider from instance
        provider = instance.api_client_class_name.replace('Client', '') if instance.api_client_class_name else DEFAULT_PROVIDER
        
        # Get params, ensuring types are correct
        try:
            temp = float(data.get('temperature', 0.7))
            top_p = float(data.get('top_p', 0.95))
            thinking = data.get('thinking', 'off') == 'on'
        except (ValueError, TypeError):
            temp, top_p, thinking = 0.7, 0.95, True

        # Get currently registered tools
        tools = list(instance.tool_manager.registered_tools.keys())

        persona_dict = {
            "persona_name": persona_name,
            "model_config": {
                "provider": provider,
                "model_name": model,
                "generation_params": {
                    "temperature": temp,
                    "top_p": top_p,
                    "thinking": thinking
                }
            },
            "system_prompt": system_prompt,
            "tools": tools
        }

        # 2. Save Persona File using persona_manager
        from my_tools import persona_manager
        result_json = persona_manager.create_persona(persona_name, json.dumps(persona_dict), overwrite=True)
        result = json.loads(result_json)
        
        if result.get('status') == 'error':
            return render_template('partials/status_update.html', instance_id=instance_id, message=f"Save Error: {result.get('message')}", is_error=True)

        # 3. Update role_registry.json
        app_root = os.path.dirname(os.path.abspath(__file__))
        registry_path = os.path.join(app_root, 'personas', 'role_registry.json')
        
        if os.path.exists(registry_path):
            with open(registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            # Check if already exists, if so update competency
            roles = registry.get("roles", [])
            found = False
            for role in roles:
                if role['name'] == persona_name:
                    role['competency'] = competency
                    role['tools'] = tools
                    found = True
                    break
            
            if not found:
                roles.append({
                    "name": persona_name,
                    "file": f"{persona_name}.json",
                    "competency": competency,
                    "tools": tools
                })
            
            registry['roles'] = roles
            with open(registry_path, 'w', encoding='utf-8') as f:
                json.dump(registry, f, indent=2)

        return render_template('partials/status_update.html', instance_id=instance_id, message=f"Persona '{persona_name}' saved and registered.")

    except Exception as e:
        import traceback
        traceback.print_exc()
        return render_template('partials/status_update.html', instance_id=instance_id, message=f"Unexpected Error: {e}", is_error=True)

@app.route('/chat/<instance_id>/save', methods=['POST'])
def save_chat_state(instance_id):
    filename = chat_manager.save_instance_state(instance_id)
    if filename:
        return render_template('partials/status_update.html', message="Session saved.", instance_id=instance_id)
    else:
        return render_template('partials/status_update.html', message="Error saving session.", instance_id=instance_id, is_error=True)

@app.route('/chat/<instance_id>/last_message', methods=['GET'])
def get_last_message(instance_id):
    instance = chat_manager.get_instance(instance_id)
    if not instance or not instance.chat_history:
        return "", 204
    last_msg = instance.chat_history[-1]
    rendered = render_template('partials/message_turn.html', msg=last_msg)
    response = Response(rendered)
    return response

@app.route('/chat/<instance_id>/connect', methods=['POST'])
def connect_instance(instance_id):
    instance = chat_manager.get_instance(instance_id)
    if not instance: return "Not Found", 404
    provider_name = request.form.get('provider')
    model_name = request.form.get('model')
    try:
        instance.connect_api_client(provider_name)
        instance.selected_model = model_name
        chat_manager.save_instance_state(instance_id)
        instance.connection_error = None
    except Exception as e:
        instance.connection_error = str(e)
    return render_template('chat_instance.html', instance=instance)

@app.route('/chat/<instance_id>/tools', methods=['GET'])
def get_tools_form(instance_id):
    instance = chat_manager.get_instance(instance_id)
    if not instance: return "Not Found", 404
    return render_template('partials/tools_manager.html', instance=instance)

# Update these routes in app.py

@app.route('/chat/<instance_id>/tools/discover', methods=['GET'])
def discover_tools_route(instance_id):
    instance = chat_manager.get_instance(instance_id)
    if not instance: return "Not Found", 404
    # Use generic listdir or tool_manager logic
    modules = instance.tool_manager.tool_module_map.values()
    # De-duplicate
    modules = list(set(modules))
    return render_template('partials/_tool_discovery_step1.html', instance=instance, modules=modules)

@app.route('/chat/<instance_id>/tools/scan-module', methods=['GET'])
def scan_module_route(instance_id):
    instance = chat_manager.get_instance(instance_id)
    if not instance: return "Not Found", 404
    module_path = request.args.get('module_path')
    # Use ToolManager
    unregistered_tools = instance.tool_manager.scan_module_for_tools(module_path)
    return render_template('partials/_tool_discovery_step2.html', instance=instance, module_path=module_path, tools=unregistered_tools)

@app.route('/chat/<instance_id>/tools/register-batch', methods=['POST'])
def register_batch_route(instance_id):
    instance = chat_manager.get_instance(instance_id)
    if not instance: return "Not Found", 404
    module_path = request.form.get('module_path')
    function_names = request.form.getlist('function_names')
    
    success_count = 0
    for func_name in function_names:
        # Calls ChatInstance.register_tool which handles the Sync
        if instance.register_tool(func_name, module_path, func_name):
            success_count += 1
            
    chat_manager.save_instance_state(instance_id)
    return render_template('partials/tools_manager.html', instance=instance, status_message=f"Registered {success_count} tools.")

@app.route('/chat/<instance_id>/tools/<tool_name>', methods=['DELETE'])
def unregister_tool_route(instance_id, tool_name):
    instance = chat_manager.get_instance(instance_id)
    if not instance: return "Not Found", 404
    
    # Calls ChatInstance.unregister_tool which handles the Sync
    instance.unregister_tool(tool_name)
    
    chat_manager.save_instance_state(instance_id)
    return render_template('partials/tools_manager.html', instance=instance, status_message=f"Tool {tool_name} removed.")

@app.route('/chat/<instance_id>/tools/register-manual', methods=['POST'])
def register_tool_route_manual(instance_id):
    instance = chat_manager.get_instance(instance_id)
    if not instance: return "Not Found", 404
    if instance.is_generating: return Response(status=409, response="Cannot change tools while generating.")
    tool_name = request.form.get('tool_name', '').strip()
    module_path = request.form.get('module_path', '').strip()
    function_name = request.form.get('function_name', '').strip()
    status_message = ""
    is_error = False
    if not tool_name or not module_path or not function_name:
        status_message = "Error: Tool name, module path, and function name are required."
        is_error = True
    else:
        try:
            spec = importlib.util.find_spec(module_path)
            if spec is None:
                 raise ModuleNotFoundError()
        except ModuleNotFoundError:
             status_message = f"Error: Module '{module_path}' not found or invalid."
             is_error = True
        except Exception as e:
             status_message = f"Error checking module '{module_path}': {e}"
             is_error = True
        if not is_error:
            success = instance.register_tool_from_config(name=tool_name, module_path=module_path, function_name=function_name)
            if success:
                chat_manager.save_instance_state(instance_id)
                status_message = f"Tool '{tool_name}' registered manually."
            else:
                status_message = instance.connection_error or f"Failed to register tool '{tool_name}'. Check logs."
                instance.connection_error = None
                is_error = True
    return render_template('partials/tools_manager.html', instance=instance, status_message=status_message, is_error=is_error)

# --- Event Monitor Controls ---

@app.route('/api/models/<provider>')
def get_provider_models(provider):
    """Returns available models for a given provider."""
    try:
        client_class = API_CLIENT_CLASSES.get(provider)
        if not client_class:
             return jsonify({"error": "Provider not found", "models": []}), 404
        
        # 1. Resolve API Key
        env_var_name = f"{provider.upper().replace('CLIENT','').replace('.','_')}_API_KEY"
        api_key = os.getenv(env_var_name)
        
        # 2. Instantiate (Handle missing key gracefully for local providers like Ollama)
        try:
            # Some clients might require api_key in init, others (Ollama) might not strictly need it
            # We pass it if we have it, or a dummy if strictly required by signature but not used (logic depends on client)
            if api_key:
                client = client_class(api_key=api_key)
            else:
                # Try instantiating without arguments if possible, or with dummy
                try:
                    client = client_class() 
                except TypeError:
                    client = client_class(api_key="dummy_key_for_listing")
        except Exception as e:
             print(f"Error instantiating {provider}: {e}")
             return jsonify({"status": "error", "message": f"Init failed: {e}", "models": []}), 500

        # 3. Fetch Models
        try:
            # Prefer the explicit method call defined in subclasses
            if hasattr(client, 'get_available_models'):
                models = client.get_available_models()
            elif hasattr(client, 'available_models'):
                models = client.available_models
            else:
                models = ["default-model"] # Fallback
            
            return jsonify({"status": "success", "models": models})
        except Exception as e:
             print(f"Error fetching models for {provider}: {e}")
             return jsonify({"status": "error", "message": str(e), "models": []}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "models": []}), 500

@app.route('/api/monitor/logs')
def stream_monitor_logs():
    """Streams the monitor_logs.txt file via SSE."""
    log_file = "monitor_logs.txt"
    app_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(app_dir, log_file)

    def generate():
        # Wait for file to exist
        retries = 0
        while not os.path.exists(log_path) and retries < 10:
            time.sleep(0.5)
            retries += 1
            
        if not os.path.exists(log_path):
             yield f"data: {json.dumps({'content': 'Log file not found.'})}\n\n"
             return

        with open(log_path, 'r') as f:
            # Go to end of file initially to show only new logs? 
            # Or show last N lines? Let's show last 20 lines then stream.
            lines = f.readlines()
            for line in lines[-20:]:
                yield f"data: {json.dumps({'content': line.strip()})}\n\n"
            
            f.seek(0, 2) # Go to end
            
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.5)
                    continue
                yield f"data: {json.dumps({'content': line.strip()})}\n\n"

    headers = {'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache'}
    return Response(generate(), headers=headers)


@app.route('/chat_sessions/<path:filename>')
def serve_uploaded_file(filename):
    upload_folder = 'chat_sessions'
    file_path = os.path.abspath(os.path.join(upload_folder, filename))
    upload_dir_abs = os.path.abspath(upload_folder)
    if not file_path.startswith(upload_dir_abs):
        return "Forbidden", 403
    if not os.path.exists(file_path):
        return "Not Found", 404
    return send_from_directory(upload_folder, filename)

# --- Telemetry Dashboard ---

@app.route('/telemetry/poll')
def telemetry_poll():
    """Returns the current telemetry buffer as JSON for polling."""
    # Convert deque to list for JSON serialization
    events = list(chat_manager.telemetry_buffer)
    return jsonify({
        "status": "success",
        "events": events
    })

@app.route('/telemetry/view')
def telemetry_view():
    """Renders the telemetry dashboard partial."""
    return render_template('partials/telemetry.html')

if __name__ == '__main__':
    os.makedirs("chat_sessions", exist_ok=True)
    os.makedirs("chat_logs", exist_ok=True)
    os.makedirs("my_tools", exist_ok=True)
    os.makedirs("personas", exist_ok=True) # --- Persona Integration: Ensure personas dir exists ---
    if not os.path.exists("my_tools/__init__.py"):
        with open("my_tools/__init__.py", "w") as f:
            pass
    app.run(debug=True, threaded=True, port=5000)

