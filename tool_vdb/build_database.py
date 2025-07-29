# build_database.py
import os
import importlib.util
import inspect
import json
import ollama
import chromadb # The new, package-friendly library
import configparser
import sys
import hashlib

# --- Configuration ---

# Get the directory where the current script is located (i.e., .../tool_vdb)
script_dir = os.path.dirname(os.path.abspath(__file__))

# Get the project root directory by going one level up from the script's directory
project_root = os.path.dirname(script_dir)

# The config file is located right next to the script
config_path = os.path.join(script_dir, 'config.ini')

config = configparser.ConfigParser()
config.read(config_path)

if 'Paths' not in config:
    raise ValueError("Error: '[Paths]' section not found in config.ini.")
if 'Models' not in config:
     raise ValueError("Error: '[Models]' section not found in config.ini.")

# --- Build ABSOLUTE paths from the PROJECT ROOT ---
# This is the key change. We join the project root with the simple paths from the config.

# Path for the vector database (e.g., C:\...\web_chat_app2\tool_vdb\vdb_data)
db_path_from_config = config['Paths']['VECTOR_DB_PATH']
DB_PATH = os.path.join(project_root, db_path_from_config)

# Path for the tools directory (e.g., C:\...\web_chat_app2\my_tools)
tools_dir_from_config = config['Paths']['TOOLS_DIRECTORY']
TOOLS_DIRECTORY = os.path.join(project_root, tools_dir_from_config) # Needed in build_database.py

# --- Other Settings ---
COLLECTION_NAME = "tools"
MODEL_NAME = config['Models']['EMBEDDING_MODEL']

# Ensure the database directory exists before trying to use it
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# --- Part 1: Your Tool Extraction Logic ---
# (This function is still perfect and does not need to change)
def extract_tool_data(directory: str):
    """
    Scans a directory for Python files, inspects them for public functions,
    and extracts a detailed JSON Schema for each tool.
    """

    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    all_tools_data = []
    abs_directory = os.path.abspath(directory)
    if not os.path.isdir(abs_directory):
        print(f"Error: Directory '{abs_directory}' not found.")
        return []
    
    module_parent_dir = os.path.basename(abs_directory)

    for filename in os.listdir(abs_directory):
        # We add the proxy tool exclusion here
        if filename.endswith('.py') and not filename.startswith('__') and filename != 'find_best_tool.py':
            module_name = filename[:-3]
            # Adjust module path logic to handle nested directories if necessary
            module_path_for_import = f"{module_parent_dir}.{module_name}"
            
            try:
                spec = importlib.util.find_spec(module_path_for_import)
                if not spec or not spec.loader: continue
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                for name, func in inspect.getmembers(module, inspect.isfunction):
                    if not name.startswith('_') and func.__module__ == module.__name__:
                        
                        full_docstring = inspect.getdoc(func) or "No description provided."
                        main_description = full_docstring.split('\n')[0] # The first line is the main description
                        
                        # --- JSON Schema Generation ---
                        schema = {
                            "type": "function",
                            "function": {
                                "name": name,
                                "description": main_description,
                                "parameters": {
                                    "type": "object",
                                    "properties": {},
                                    "required": [],
                                }
                            }
                        }

                        # --- Parameter Inspection ---
                        sig = inspect.signature(func)
                        param_docs = {line.split(' ')[1]: " ".join(line.split(' ')[2:]) for line in full_docstring.split('\n') if line.strip().startswith('@param')}

                        for param in sig.parameters.values():
                            param_name = param.name
                            param_type = "string" # Default to string
                            if param.annotation is not inspect.Parameter.empty and hasattr(param.annotation, '__name__'):
                                # A simple mapping from Python types to JSON Schema types
                                type_map = {
                                    "str": "string",
                                    "int": "integer",
                                    "float": "number",
                                    "bool": "boolean",
                                    "list": "array",
                                    "dict": "object",
                                }
                                param_type = type_map.get(param.annotation.__name__.lower(), "string")

                            schema["function"]["parameters"]["properties"][param_name] = {
                                "type": param_type,
                                "description": param_docs.get(param_name, "") # Get param description from docstring
                            }

                            # Check if the parameter is required (i.e., has no default value)
                            if param.default is inspect.Parameter.empty:
                                schema["function"]["parameters"]["required"].append(param_name)

                        tool_info = {
                            "id": name,
                            "description": full_docstring, # We embed the full docstring for richer context
                            "spec": json.dumps(schema, indent=2)
                        }
                        all_tools_data.append(tool_info)

            except Exception as e:
                print(f"Error processing {module_path_for_import}: {e}")

    return all_tools_data


# --- Part 2: Main Database Indexing Logic with ChromaDB ---

def main():
    """
    Performs a smart synchronization between tool files on disk and the ChromaDB database.
    Only new, updated, or deleted tools are processed.
    """
    print("--- Starting Smart Sync for Tool Database ---")

    # 1. Setup ChromaDB client
    print(f"\n[1/5] Connecting to ChromaDB client at '{DB_PATH}'...")
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )
    
    # 2. Get the current state of tools on disk
    print(f"\n[2/5] Scanning for tools in '{TOOLS_DIRECTORY}' directory...")
    disk_tools = {tool['id']: tool for tool in extract_tool_data(TOOLS_DIRECTORY)}
    print(f"Found {len(disk_tools)} tools on disk.")

    # 3. Get the current state of tools in the database
    print("\n[3/5] Fetching existing tool fingerprints from database...")
    db_tools = collection.get(include=["metadatas"])
    db_tool_fingerprints = {db_id: db_meta.get('fingerprint') for db_id, db_meta in zip(db_tools['ids'], db_tools['metadatas'])}
    print(f"Found {len(db_tool_fingerprints)} tools in the database.")

    # 4. Determine what has changed
    print("\n[4/5] Comparing disk tools to database to find changes...")
    tools_to_upsert = []
    
    for tool_id, tool_data in disk_tools.items():
        # Create a fingerprint from the parts that define the tool's behavior and schema
        content_to_hash = tool_data['description'] + tool_data['spec']
        current_fingerprint = hashlib.sha256(content_to_hash.encode()).hexdigest()
        
        # If tool is new or has changed, add it to the list for upserting
        if db_tool_fingerprints.get(tool_id) != current_fingerprint:
            print(f"  - Change detected for '{tool_id}'. Queued for update/insertion.")
            tool_data['fingerprint'] = current_fingerprint # Add the new fingerprint
            tools_to_upsert.append(tool_data)

    # Determine which tools were deleted
    ids_on_disk = set(disk_tools.keys())
    ids_in_db = set(db_tool_fingerprints.keys())
    ids_to_delete = list(ids_in_db - ids_on_disk)

    # 5. Execute database operations
    print("\n[5/5] Executing database operations...")
    if tools_to_upsert:
        print(f"  - Upserting {len(tools_to_upsert)} new or modified tools...")
        # Prepare data for batch upsert
        ids = [t['id'] for t in tools_to_upsert]
        documents = [t['description'] for t in tools_to_upsert]
        metadatas = [{"spec": t['spec'], "fingerprint": t['fingerprint']} for t in tools_to_upsert]
        
        # --- THIS IS THE CORRECTED EMBEDDING LOGIC ---
        print("    - Generating embeddings with Ollama (this may take a moment)...")
        ollama_client = ollama.Client()
        embeddings = []
        for doc in documents:
            # Call the embedding function once per document
            response = ollama_client.embeddings(model=MODEL_NAME, prompt=doc)
            embeddings.append(response['embedding'])
        print("    - Embeddings generated.")
        
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
        print("  - Upsert complete.")
    else:
        print("  - No tools needed to be added or updated.")

    if ids_to_delete:
        print(f"  - Deleting {len(ids_to_delete)} tools removed from disk: {ids_to_delete}")
        collection.delete(ids=ids_to_delete)
        print("  - Deletion complete.")
    else:
        print("  - No tools needed to be deleted.")

    print("\n--- Smart Sync Complete! ---")
    print(f"Database now contains {collection.count()} tools.")

if __name__ == "__main__":
    main()