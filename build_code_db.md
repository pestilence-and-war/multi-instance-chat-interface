# README for build_code_db.py

## What It Does

This script is a powerful code-to-database parser. It walks through the project directory, reads source files (Python, HTML, CSS, JavaScript), and builds a structured, queryable SQLite database named `project_context.db`.

The purpose of this database is to provide a comprehensive, detailed representation of the entire codebase's structure. It is used by other tools to understand the project's layout, find function definitions, analyze code, and more. It is **not** a vector database for semantic search.

## How to Use

Run the script from the project's root directory:

```bash
# To scan the current directory
python build_code_db.py

# To scan a specific directory
python build_code_db.py /path/to/your/project
```

The script will create (or overwrite) a file named `project_context.db` in the directory where you run the command.

## Configuration

Configuration is handled directly within the script itself. Open `build_code_db.py` and edit the configuration lists and sets at the top of the file to match your project's needs.

Key configuration variables include:

- `EXCLUDED_DIRS`: A set of directory names to completely ignore during the scan (e.g., `node_modules`, `venv`).
- `EXCLUDED_FILENAMES`: A set of specific filenames to ignore (e.g., `.env`).
- `BINARY_EXTENSIONS`: File extensions for binary files whose content should not be read.
- `IGNORED_TEXT_EXTENSIONS`: File extensions for text files whose content is generally not useful to parse (e.g., `.log`, `.csv`), unless they are on the allow list.
- `INCLUDE_CONTENT_FOR_SPECIFIC_FILENAMES`: An "allow list" to force the inclusion of specific, important files that might otherwise be ignored by their extension (e.g., `requirements.txt`, `package.json`).
- `PARSEABLE_CODE_EXTENSIONS`: The list of file types the script knows how to parse structurally (e.g., `.py`, `.html`).

## Dependencies

The script uses standard Python libraries. However, for full parsing capabilities, certain third-party libraries are required. The script will print a warning if they are not found.

- **For HTML/CSS Parsing**: `beautifulsoup4`, `lxml`
- **For JavaScript Parsing**: `esprima`

Install them via pip:
```bash
pip install beautifulsoup4 lxml esprima
```
