from flask import Flask, render_template, request, Response, stream_with_context, jsonify, session, url_for, send_from_directory
import json
import queue
import time
import os
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

dotenv.load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

# --- Jinja Filters & Context ---
@app.template_filter('markdown')
def markdown_filter(s):
    return markdown_to_html(s or "")

@app.template_filter('format_time')
def format_time_filter(s):
    return format_timestamp(s)

@app.context_processor
def inject_global_context():
    return dict(
        utils=utils,
        API_CLIENT_CLASSES=API_CLIENT_CLASSES,
        DEFAULT_PROVIDER=DEFAULT_PROVIDER,
        providers=list(API_CLIENT_CLASSES.keys()),
        available_personas=json.loads(persona_manager.list_personas()).get('personas', [])
    )

# === Main Routes ===

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
    instance = chat_manager.create_instance(provider_name=provider, api_key=api_key)

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
            top_p=data.get('top_p')
        )
        chat_manager.save_instance_state(instance_id)
        return render_template('partials/status_update.html', instance_id=instance_id, message="Config updated.")
    except Exception as e:
        return render_template('partials/status_update.html', instance_id=instance_id, message=f"Error: {e}", is_error=True)

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
                    message_json = sse_message_queue.get(timeout=120)
                except queue.Empty:
                     yield f"data: {json.dumps({'type': 'error', 'content': 'Stream timed out.'})}\n\n"
                     break
                if message_json is None:
                    break
                yield f"data: {message_json}\n\n"
                sse_message_queue.task_done()
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
        tool_call_id = request.form.get(prefix + 'tool_call_id')
        if tool_call_id:
            tool_name = request.form.get(prefix + 'tool_name')
            tool_arguments = request.form.get(prefix + 'tool_arguments')
            tool_calls = [{"id": tool_call_id, "function": {"name": tool_name, "arguments": tool_arguments}, "type": "function"}]
            msg_data["tool_calls"] = tool_calls
        tool_result = request.form.get(prefix + 'tool_result')
        if tool_result:
            msg_data["tool_call_id"] = tool_call_id
            msg_data["content"] = tool_result
            msg_data["role"] = "tool"
        edited_history.append(msg_data)
    instance.chat_history = edited_history
    chat_manager.save_instance_state(instance)
    return render_template('partials/status_update.html', message="Context edited and saved.", instance_id=instance_id)

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

@app.route('/chat/<instance_id>/tools/discover', methods=['GET'])
def discover_tools_route(instance_id):
    instance = chat_manager.get_instance(instance_id)
    if not instance: return "Not Found", 404
    available_modules = instance.discover_tool_modules(directory="my_tools")
    return render_template('partials/_tool_discovery_step1.html', instance=instance, modules=available_modules)

@app.route('/chat/<instance_id>/tools/scan-module', methods=['GET'])
def scan_module_route(instance_id):
    instance = chat_manager.get_instance(instance_id)
    if not instance: return "Not Found", 404
    module_path = request.args.get('module_path')
    if not module_path: return "Module path is required.", 400
    unregistered_tools = instance.get_unregistered_tools_in_module(module_path)
    return render_template('partials/_tool_discovery_step2.html', instance=instance, module_path=module_path, tools=unregistered_tools)

@app.route('/chat/<instance_id>/tools/register-batch', methods=['POST'])
def register_batch_route(instance_id):
    instance = chat_manager.get_instance(instance_id)
    if not instance: return "Not Found", 404
    if instance.is_generating: return Response(status=409, response="Cannot change tools while generating.")
    module_path = request.form.get('module_path')
    function_names = request.form.getlist('function_names')
    if not module_path or not function_names:
        return render_template('partials/tools_manager.html', instance=instance, status_message="Error: Module and at least one function must be selected.", is_error=True)
    success_count = 0
    fail_count = 0
    failed_tools = []
    for func_name in function_names:
        success = instance.register_tool_from_config(name=func_name, module_path=module_path, function_name=func_name)
        if success:
            success_count += 1
        else:
            fail_count += 1
            failed_tools.append(func_name)
    chat_manager.save_instance_state(instance_id)
    status_message = f"Registered {success_count} tool(s)."
    is_error = False
    if fail_count > 0:
        status_message += f" Failed to register {fail_count}: {', '.join(failed_tools)}."
        is_error = True
    return render_template('partials/tools_manager.html', instance=instance, status_message=status_message, is_error=is_error)

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

@app.route('/chat/<instance_id>/tools/<tool_name>', methods=['DELETE'])
def unregister_tool_route(instance_id, tool_name):
    instance = chat_manager.get_instance(instance_id)
    if not instance: return Response("Instance Not Found", status=404)
    if instance.is_generating: return Response(status=409, response="Cannot change tools while generating.")
    tool_name = tool_name.strip()
    if tool_name in instance.tools_definitions:
        try:
            del instance.tools_definitions[tool_name]
            if instance.api_client and tool_name in instance.api_client.registered_tools:
                del instance.api_client.registered_tools[tool_name]
                new_tool_schemas = []
                for s in instance.api_client.tool_schemas:
                    schema_name = None
                    if hasattr(s, 'name'):
                        schema_name = s.name
                    elif isinstance(s, dict):
                        schema_name = s.get('name')
                    if schema_name != tool_name:
                        new_tool_schemas.append(s)
                instance.api_client.tool_schemas = new_tool_schemas
            chat_manager.save_instance_state(instance_id)
            return render_template('partials/tools_manager.html', instance=instance, status_message=f"Tool '{tool_name}' unregistered.", is_error=False)
        except Exception as e:
             instance = chat_manager.get_instance(instance_id)
             return render_template('partials/tools_manager.html', instance=instance, status_message=f"Error unregistering {tool_name}: {e}", is_error=True), 500
    else:
         return render_template('partials/tools_manager.html', instance=instance, status_message=f"Tool '{tool_name}' not found.", is_error=True), 404

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

if __name__ == '__main__':
    os.makedirs("chat_sessions", exist_ok=True)
    os.makedirs("chat_logs", exist_ok=True)
    os.makedirs("my_tools", exist_ok=True)
    os.makedirs("personas", exist_ok=True) # --- Persona Integration: Ensure personas dir exists ---
    if not os.path.exists("my_tools/__init__.py"):
        with open("my_tools/__init__.py", "w") as f:
            pass
    app.run(debug=True, threaded=True, port=5000)

