# tool_vdb/query_tools.py
import chromadb
import ollama
import json
import sys
import os
import configparser

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

# --- Main Function ---


def find_similar_tools(query_text: str, n_results: int = 3) -> list:
    """
    Finds tools in the ChromaDB collection that are semantically similar to a query
    and returns their full JSON Schema specifications.

    Args:
        query_text: The user's natural language query about the task to perform.
        n_results: The number of top tools to return.

    Returns:
        A list of JSON Schema dictionaries, where each dictionary describes a
        tool that the language model can use. Returns an empty list on error.
    """
    try:
        # 1. Setup ChromaDB client and get collection
        client = chromadb.PersistentClient(path=DB_PATH)
        collection = client.get_collection(name=COLLECTION_NAME)

        # 2. Health Check and Embedding Generation
        try:
            ollama_client = ollama.Client()
            query_embedding = ollama_client.embeddings(
                model=MODEL_NAME,
                prompt=query_text
            )['embedding']
        except Exception as e:
            print(f"\n--- Ollama Connection Error ---\nDetails: {e}\n")
            return [] # Exit gracefully

        # 3. Query the collection
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
        )

        # 4. Process the results into a clean list of JSON Schemas
        #    This is the key change.
        tool_schemas = []
        if not results.get('ids') or not results['ids'][0]:
            return [] # No results found

        for metadata in results['metadatas'][0]:
            # The full JSON schema is stored as a string in the 'spec' metadata field.
            # We parse it back into a Python dictionary.
            spec_string = metadata.get('spec')
            if spec_string:
                tool_schemas.append(json.loads(spec_string))
        
        return tool_schemas

    except Exception as e:
        print(f"An error occurred during tool search: {e}")
        print(f"Please ensure the database at '{DB_PATH}' exists and is populated.")
        return []


if __name__ == "__main__":
    # --- The test block below is also updated for the new output format ---

    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} \"<your query>\"")
        sys.exit(1)

    user_query = " ".join(sys.argv[1:])
    
    print(f"🔍 Searching for tools related to: \"{user_query}\"")
    print(f"(Using database at: {DB_PATH})")
    
    # The function now returns a list of schemas directly
    found_tool_schemas = find_similar_tools(user_query)

    if found_tool_schemas:
        print(f"\n✅ Found {len(found_tool_schemas)} relevant tool schemas:")
        # We pretty-print the JSON so it's easy to read in the terminal
        print(json.dumps(found_tool_schemas, indent=2))
    else:
        print("\n❌ No relevant tools were found in the database.")