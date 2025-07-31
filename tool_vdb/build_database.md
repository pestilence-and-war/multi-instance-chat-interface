# README for tool_vdb/build_database.py

## What It Does

This script builds a **vector database** of the available tools (functions) in the `my_tools` directory. It inspects the Python files, extracts the function signatures and docstrings, and then uses a language model to create a vector embedding for each tool's description.

The purpose of this database is to enable **semantic search for tools**. It allows the AI to find the most relevant tool for a user's request based on the meaning of the request, not just keywords. This is a "smart sync" script; it only updates tools that are new or have changed since the last run.

## How to Use

Run the script from the project's root directory:

```bash
python tool_vdb/build_database.py
```

The script will connect to the ChromaDB vector store, scan the `my_tools` directory, and update the database with any new, modified, or deleted tools.

## Configuration

All configuration is handled in the `tool_vdb/config.ini` file.

Key configuration variables include:

- **`[Paths]`**:
    - `VECTOR_DB_PATH`: The relative path to the directory where the ChromaDB vector store is kept.
    - `TOOLS_DIRECTORY`: The relative path to the directory containing the tools to be indexed.
- **`[Models]`**:
    - `EMBEDDING_MODEL`: The name of the Ollama model to use for creating the vector embeddings (e.g., `nomic-embed-text`).

## Dependencies

The script requires several third-party libraries:

- `ollama`: To connect to the Ollama service for generating embeddings.
- `chromadb`: The client for the vector database.

Install them via pip:
```bash
pip install ollama chromadb
```

**Important**: You must have the Ollama service running and the specified embedding model (`nomic-embed-text` by default) available locally.
```bash
ollama run nomic-embed-text
```
