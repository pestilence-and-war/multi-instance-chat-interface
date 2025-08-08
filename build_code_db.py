# build_code_db.py

import os
import json
import sys
import ast
import textwrap
from datetime import datetime
import re # For basic CSS parsing
import traceback # For detailed error logging
import sqlite3 ### DB MOD ###: Import the SQLite3 library

# Attempt to import HTML/CSS parsers, print warnings if not available
try:
    from bs4 import BeautifulSoup
    from bs4 import Comment # Needed to exclude comments
    import lxml # BeautifulSoup backend for speed
    HTML_PARSING_AVAILABLE = True
except ImportError:
    print("Warning: beautifulsoup4 or lxml not found. HTML parsing will be skipped.")
    print("Install with: pip install beautifulsoup4 lxml")
    HTML_PARSING_AVAILABLE = False

# Attempt to import JS parser
try:
    import esprima
    JS_PARSING_AVAILABLE = True
except ImportError:
    print("Warning: esprima library not found. JavaScript parsing within <script> tags will be skipped.")
    print("Install with: pip install esprima")
    JS_PARSING_AVAILABLE = False

### NEW PARSERS ADDED ###
# Attempt to import YAML parser
try:
    import yaml
    YAML_PARSING_AVAILABLE = True
except ImportError:
    print("Warning: PyYAML not found. YAML (.yml, .yaml) parsing will be skipped.")
    print("Install with: pip install PyYAML")
    YAML_PARSING_AVAILABLE = False

# Attempt to import TOML parser
try:
    import toml
    TOML_PARSING_AVAILABLE = True
except ImportError:
    print("Warning: toml library not found. TOML (.toml) parsing will be skipped.")
    print("Install with: pip install toml")
    TOML_PARSING_AVAILABLE = False


# --- Configuration: Define File and Directory Handling ---
# These lists and sets control which files and directories are included,
# excluded, or handled specially during the project scan.
# Place these prominently at the top so a new user can easily find and modify them.

# Define directories to exclude from traversal (os.walk will not enter these).
# This is suitable for dependency folders, build outputs, IDE configs, etc.
# These directories (and their contents) will NOT appear in the 'directory_tree'.
EXCLUDED_DIRS = {
    '__pycache__', '.git', '.svn', '.hg', # Version control and cache
    'node_modules', 'venv', '.venv', '__pypackages__', 'vendor', # Dependency directories
    'dist', 'build', # Build/distribution directories
    '.idea', '.vscode', '__pydevd_remote_debug_server__', # IDE specific directories
    'chat_sessions', 'chat_logs',# Add other directories here as needed (e.g., 'logs', 'tmp', 'instance_data')
}

# Define specific filenames to exclude regardless of the directory they are in.
# (These files will be listed in the directory_tree but WILL NOT have an entry
# in the 'files' dictionary, nor will their content be read).
EXCLUDED_FILENAMES = {
    os.path.basename(__file__), # Exclude this script itself by name
    # '.env', # Explicitly exclude environment variable files
    'build_code_json.py', 'create_context.py', 'recreate_structure.py',# Add other specific filenames here (e.g., 'package-lock.json' if not managed by INCLUDE_CONTENT_FOR_SPECIFIC_FILENAMES)
    # 'htmx.min.js' # Example, could also be handled by MANAGED_EXTENSIONS
}

# Define file extensions for files that are likely binary or sensitive.
# (These files will be listed in the directory_tree but WILL NOT have an entry
# in the 'files' dictionary, nor will their content be read).
BINARY_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico', # Images
    '.mp4', '.mp3', '.avi', '.mov', '.webm', # Media
    '.pdf', '.docx', '.xlsx', '.pptx', # Documents
    '.bin', '.exe', '.dll', '.so', '.dylib', '.o', '.a', '.lib', '.class', '.pyc', '.pyd', # Binaries/Compiled
    '.zip', '.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.rar', '.7z', # Archives
    '.sqlite', '.db', '.sql', # Databases/SQL dumps (often binary or large text dumps)
    '.pem', '.key', '.cer', '.crt', '.pfx', '.p12', # Keys/Certificates
    '.lock', '.tmp', '.bak', '.swp', # Lock/Temp/Backup/Swap files
    '.DS_Store', '.env.enc', # macOS specific / Encrypted files
    # Add other binary or sensitive extensions here
}

# Define file extensions for text files whose *content* should generally be ignored,
# preventing them from having an entry in the 'files' dictionary by default.
# Useful for very large logs, generated code/data, or non-critical configuration files
# whose content isn't needed for understanding the core project code logic.
# Use INCLUDE_CONTENT_FOR_SPECIFIC_FILENAMES to override this for specific important files.
IGNORED_TEXT_EXTENSIONS = {
    '.jsonl', # Data/Log files (unless specifically in INCLUDE_CONTENT_FOR_SPECIFIC_FILENAMES)
    '.log', '.csv', '.tsv', # Data/Log files
    '.txt', # Generic text files (unless specifically in INCLUDE_CONTENT_FOR_SPECIFIC_FILENAMES)
    # '.md', '.markdown', # Markdown (consider parsing if structure is needed, or add to INCLUDE_CONTENT_FOR_SPECIFIC_FILENAMES)
    '.ini', # Configuration files (consider parsing or adding to INCLUDE_CONTENT_FOR_SPECIFIC_FILENAMES)
    '.gitignore', '.dockerignore', '.eslintignore', # Ignore rules files
    '.editorconfig', '.gitattributes', # Config files
    # Dependency manifests - use INCLUDE_CONTENT_FOR_SPECIFIC_FILENAMES for key ones like requirements.txt or package.json
    'package-lock.json', 'yarn.lock',
    'Gemfile.lock', 'pom.xml', 'build.gradle', # Build/dependency definition files
    # Add other extensions here
}

# Define specific filenames whose *content* SHOULD be included in the 'files' dictionary,
# even if their extension is listed in IGNORED_TEXT_EXTENSIONS.
# This is the "allow list" for content inclusion of otherwise ignored text file types.
INCLUDE_CONTENT_FOR_SPECIFIC_FILENAMES = {
    'requirements.txt',
    'package.json',
    'Gemfile',
    'pyproject.toml',
    # Add other specific project-critical config/text filenames here
    # e.g., 'main_config.json', 'settings.ini'
}


# Define file extensions for files whose *content* should NOT be stored fully,
# but which *should* still have an entry in the 'files' dictionary with metadata.
# Useful for large static assets (like minified JS libraries, bundled CSS) that you want
# the LLM to know exist, but whose source you don't need to manage or diff.
# Their presence in the 'files' dict means they are 'acknowledged'.
MANAGED_EXTENSIONS = {
    '.min.js', '.bundle.js', '.css.map', '.js.map', # Example minified/bundled/map files
    # Add other extensions here for files whose content should be omitted
}

# Define specific filenames that should be 'managed' regardless of extension.
# (These files will have an entry in 'files' but with null content and metadata).
MANAGED_FILENAMES = {
    # Add specific filenames here if needed, e.g., 'large_asset.data'
}


# Define file extensions for files that should be read and parsed for structured information.
# The full content of these files WILL be stored in the JSON, along with the parsed details.
PARSEABLE_CODE_EXTENSIONS = {
    '.py',
    '.html', '.htm',
    '.css',
    '.js',
    '.json', # NEW: Added JSON
    '.yml', '.yaml', # NEW: Added YAML
    '.toml', # NEW: Added TOML
    # Add other code/markup language extensions here (e.g., '.jsx', '.ts', '.tsx', '.vue')
}

### DB MOD ###: New function to create the database schema
def create_schema(cursor):
    """Creates the necessary tables and indexes for the project context database."""
    # Metadata and Directory Tree
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS metadata (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS directory_tree (
        path TEXT PRIMARY KEY
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS directories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT NOT NULL UNIQUE
    )''')

    # Core File Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT UNIQUE NOT NULL,
        type TEXT,
        full_content TEXT,
        start_lineno INTEGER,
        end_lineno INTEGER,
        message TEXT,
        error TEXT,
        docstring TEXT
    )''')

    # Python Specific Tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS python_imports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id INTEGER NOT NULL,
        import_statement TEXT,
        FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS python_classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id INTEGER NOT NULL,
        name TEXT,
        docstring TEXT,
        source_code TEXT,
        start_lineno INTEGER,
        end_lineno INTEGER,
        FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS python_functions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id INTEGER NOT NULL,
        class_id INTEGER, -- NULL for top-level functions
        parent_function_id INTEGER, -- Self-referencing key for nested functions
        name TEXT,
        signature TEXT,
        docstring TEXT,
        source_code TEXT,
        start_lineno INTEGER,
        end_lineno INTEGER,
        FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE,
        FOREIGN KEY (class_id) REFERENCES python_classes (id) ON DELETE CASCADE,
        FOREIGN KEY (parent_function_id) REFERENCES python_functions (id) ON DELETE CASCADE
    )''')
    # NEW TABLE FOR FUNCTION CALLS
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS python_function_calls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        caller_function_id INTEGER NOT NULL,
        callee_name TEXT NOT NULL,
        FOREIGN KEY (caller_function_id) REFERENCES python_functions (id) ON DELETE CASCADE
    )''')


    # HTML Specific Tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS html_elements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id INTEGER NOT NULL,
        element_type TEXT NOT NULL, -- 'form', 'link', 'image', 'htmx', 'script', 'style', etc.
        data TEXT, -- Store the detailed dictionary as JSON text
        FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS js_parsed_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        html_element_id INTEGER NOT NULL,
        item_type TEXT NOT NULL, -- 'function', 'event_listener'
        data TEXT, -- Store the detailed dictionary as JSON text
        FOREIGN KEY (html_element_id) REFERENCES html_elements (id) ON DELETE CASCADE
    )''')

    # CSS Specific Tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS css_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id INTEGER NOT NULL,
        source_code TEXT,
        start_lineno INTEGER,
        end_lineno INTEGER,
        FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS css_selectors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_id INTEGER NOT NULL,
        selector_text TEXT,
        FOREIGN KEY (rule_id) REFERENCES css_rules (id) ON DELETE CASCADE
    )''')

    # JavaScript (Standalone Files) Specific Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS javascript_constructs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id INTEGER NOT NULL,
        name TEXT,
        construct_type TEXT NOT NULL,
        source_code TEXT,
        start_lineno INTEGER,
        end_lineno INTEGER,
        FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
    )''')

    ### NEW TABLE FOR DATA FILES ###
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS parsed_data_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id INTEGER NOT NULL,
        format TEXT NOT NULL, -- e.g., 'json', 'yaml', 'toml'
        data TEXT, -- Store the parsed data as a JSON string
        FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
    )''')


    # Create Indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_path ON files (path)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_directories_path ON directories (path)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_py_classes_file_id ON python_classes (file_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_py_functions_file_id ON python_functions (file_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_html_elements_file_id ON html_elements (file_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_css_rules_file_id ON css_rules (file_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_js_constructs_file_id ON javascript_constructs (file_id)')
    # NEW INDEX FOR FUNCTION CALLS
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_py_function_calls_caller_id ON python_function_calls (caller_function_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_py_function_calls_callee_name ON python_function_calls (callee_name)')
    # NEW INDEX FOR DATA FILES
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_parsed_data_files_file_id ON parsed_data_files (file_id)')
    print("Database schema created and indexed.")


### DB MOD ###: New function to insert parsed data into the database
def insert_file_data(cursor, file_details):
    """Inserts the parsed file details dictionary into the database."""
    if not file_details or not file_details.get('path'):
        return

    # 1. Insert into the main 'files' table
    cursor.execute('''
        INSERT INTO files (path, type, full_content, start_lineno, end_lineno, message, error, docstring)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        file_details.get('path'),
        file_details.get('type'),
        file_details.get('full_content'),
        file_details.get('start_lineno'),
        file_details.get('end_lineno'),
        file_details.get('message'),
        file_details.get('error'),
        file_details.get('docstring')
    ))
    file_id = cursor.lastrowid

    # Store function_name -> function_id mappings for this file
    # Key format: "function_name" for top-level, "ClassName.methodName" for methods
    function_id_map = {}

    # 2. Insert data into type-specific tables
    file_type = file_details.get('type')
    if file_type == 'python':

        # --- NEW: Recursive inner function to insert functions and their children ---
        def _insert_functions_recursive(functions_dict, class_id, parent_function_id):
            """
            Recursively inserts functions from a dictionary into the python_functions table.
            """
            for func_name, func_data in functions_dict.items():
                cursor.execute('''
                    INSERT INTO python_functions (file_id, class_id, parent_function_id, name, signature, docstring, source_code, start_lineno, end_lineno)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    file_id,
                    class_id,
                    parent_function_id, # Link to parent function
                    func_data['name'],
                    func_data['signature'],
                    func_data['docstring'],
                    func_data['source_code'],
                    func_data['start_lineno'],
                    func_data['end_lineno']
                ))
                new_parent_id = cursor.lastrowid

                # Store the ID for the function call mapping
                # Construct a unique key for the map (e.g., "ClassName.methodName")
                map_key = f"{func_name}"
                if class_id:
                    # To get the class name, we query it back from the DB
                    # This is slightly inefficient but safe.
                    class_name_row = cursor.execute("SELECT name FROM python_classes WHERE id = ?", (class_id,)).fetchone()
                    if class_name_row:
                        map_key = f"{class_name_row[0]}.{func_name}"
                function_id_map[map_key] = new_parent_id

                # RECURSIVE CALL for any nested functions this function contains
                if func_data.get('nested_functions'):
                    _insert_functions_recursive(func_data['nested_functions'], class_id, new_parent_id)

        # --- Main Insertion Logic ---

        for imp in file_details.get('imports', []):
            cursor.execute('INSERT INTO python_imports (file_id, import_statement) VALUES (?, ?)', (file_id, imp))

        # Initial call for top-level functions
        _insert_functions_recursive(file_details.get('functions', {}), class_id=None, parent_function_id=None)

        # Insert classes and their methods
        for class_name, class_data in file_details.get('classes', {}).items():
            cursor.execute('''
                INSERT INTO python_classes (file_id, name, docstring, source_code, start_lineno, end_lineno)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (file_id, class_data['name'], class_data['docstring'], class_data['source_code'], class_data['start_lineno'], class_data['end_lineno']))
            class_id = cursor.lastrowid

            # Initial call for methods within this class
            if class_data.get('methods'):
                _insert_functions_recursive(class_data.get('methods', {}), class_id=class_id, parent_function_id=None)

        # Insert into python_function_calls using the collected raw calls and function_id_map
        for call_data in file_details.get('function_calls_raw', []):
            caller_name = call_data['caller_name']
            caller_class_name = call_data['caller_class_name']
            callee_name = call_data['callee_name']

            caller_key = f"{caller_class_name}.{caller_name}" if caller_class_name else caller_name
            caller_function_id = function_id_map.get(caller_key)

            if caller_function_id:
                cursor.execute('''
                    INSERT INTO python_function_calls (caller_function_id, callee_name)
                    VALUES (?, ?)
                ''', (caller_function_id, callee_name))
            # else: # Optional: print a warning if a caller function ID couldn't be resolved
            #     print(f"Warning: Could not resolve caller_function_id for call from '{caller_key}' to '{callee_name}' in '{file_details['path']}'")

    elif file_type == 'html':
        # These keys in file_details hold lists of dictionaries
        html_element_types = ['forms', 'links', 'images', 'htmx_elements', 'scripts', 'inline_styles', 'body_structure_preview']
        for plural_type in html_element_types:
            singular_type = plural_type[:-1] if plural_type.endswith('s') else plural_type
            for item_data in file_details.get(plural_type, []):
                # Special handling for scripts with nested parsed_js
                if singular_type == 'script' and 'parsed_js' in item_data and item_data['parsed_js']:
                    # Make a copy to avoid modifying the original dict if it's used elsewhere
                    item_data_copy = item_data.copy()
                    parsed_js_data = item_data_copy.pop('parsed_js')

                    # Insert the script element itself
                    cursor.execute('INSERT INTO html_elements (file_id, element_type, data) VALUES (?, ?, ?)',
                                   (file_id, singular_type, json.dumps(item_data_copy)))
                    element_id = cursor.lastrowid

                    # Insert the parsed JS items linked to the script element
                    for js_func in parsed_js_data.get('functions', []):
                        cursor.execute('INSERT INTO js_parsed_items (html_element_id, item_type, data) VALUES (?, ?, ?)',
                                       (element_id, 'function', json.dumps(js_func)))
                    for js_listener in parsed_js_data.get('event_listeners', []):
                        cursor.execute('INSERT INTO js_parsed_items (html_element_id, item_type, data) VALUES (?, ?, ?)',
                                       (element_id, 'event_listener', json.dumps(js_listener)))
                else:
                # For all other element types, just dump the data
                    cursor.execute('INSERT INTO html_elements (file_id, element_type, data) VALUES (?, ?, ?)',
                               (file_id, singular_type, json.dumps(item_data)))


    elif file_type == 'css':
        for rule_data in file_details.get('rules', []):
            cursor.execute('INSERT INTO css_rules (file_id, source_code, start_lineno, end_lineno) VALUES (?, ?, ?, ?)',
                           (file_id, rule_data['source_code'], rule_data['start_lineno'], rule_data['end_lineno']))
            rule_id = cursor.lastrowid
            for selector in rule_data.get('selectors', []):
                cursor.execute('INSERT INTO css_selectors (rule_id, selector_text) VALUES (?, ?)', (rule_id, selector))

    elif file_type == 'javascript':
        for construct in file_details.get('constructs', []):
            cursor.execute('''
                INSERT INTO javascript_constructs (file_id, name, construct_type, source_code, start_lineno, end_lineno)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                file_id,
                construct.get('name'),
                construct.get('construct_type'),
                construct.get('source_code'),
                construct.get('start_lineno'),
                construct.get('end_lineno')
            ))
    
    ### NEW: Handle parsed data files (JSON, YAML, TOML) ###
    elif file_type in ('json', 'yaml', 'toml'):
        if 'data' in file_details:
            try:
                # Store the parsed data as a JSON string for consistency
                data_as_json = json.dumps(file_details['data'], indent=2)
                cursor.execute('''
                    INSERT INTO parsed_data_files (file_id, format, data)
                    VALUES (?, ?, ?)
                ''', (file_id, file_type, data_as_json))
            except (TypeError, OverflowError) as e:
                # Handle cases where the data can't be serialized to JSON
                error_details = {"path": file_details['path'], "type": f"{file_type}_serialization_error", "error": str(e)}
                insert_file_data(cursor, error_details)


# --- Helper Functions for Python AST Parsing ---

class PythonCallExtractor(ast.NodeVisitor):
    """
    AST visitor to extract function/method calls from Python code.
    It tracks the current function/class context to link calls to their callers.
    """
    def __init__(self):
        self.collected_calls = []
        # Use a stack to manage nested function/class contexts
        # Each element is (current_function_name, current_class_name)
        self.context_stack = [(None, None)] # (function_name, class_name)

    @property
    def current_function_name(self):
        return self.context_stack[-1][0]

    @property
    def current_class_name(self):
        return self.context_stack[-1][1]

    def visit_FunctionDef(self, node):
        # Push current context, set new function context
        self.context_stack.append((node.name, self.current_class_name))
        self.generic_visit(node) # Visit children nodes
        self.context_stack.pop() # Restore previous context

    def visit_AsyncFunctionDef(self, node):
        # Same as FunctionDef for async functions
        self.context_stack.append((node.name, self.current_class_name))
        self.generic_visit(node)
        self.context_stack.pop()

    def visit_ClassDef(self, node):
        # Push current context, set new class context (function name becomes None for class body)
        self.context_stack.append((None, node.name))
        self.generic_visit(node)
        self.context_stack.pop()

    def visit_Call(self, node):
        # Only record calls if we are inside a function/method
        if self.current_function_name:
            callee_name = None
            if isinstance(node.func, ast.Name):
                # Direct function call: e.g., my_function()
                callee_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                # Method call: e.g., obj.method() or Class.static_method()
                callee_name = node.func.attr

            if callee_name:
                self.collected_calls.append({
                    "caller_name": self.current_function_name,
                    "caller_class_name": self.current_class_name,
                    "callee_name": callee_name
                })
        self.generic_visit(node) # Important: continue visiting children

def get_docstring(node):
    """
    Safely extracts the docstring from a Python AST node (FunctionDef, ClassDef, Module).

    Args:
        node: An AST node object.

    Returns:
        The docstring string, or None if no docstring is found or the node type is not applicable.
    """
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
        return ast.get_docstring(node)
    return None

def get_signature(node):
    """
    Constructs a string representation of a Python function or method signature
    from its AST node. Includes parameters with annotations and defaults, and return annotation.

    Args:
        node: An AST node of type ast.FunctionDef, ast.AsyncFunctionDef, or ast.Lambda.

    Returns:
        A string representing the signature (e.g., "(self, name: str) -> None"),
        or None if the node type is not a function/method/lambda.
    """
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        return None

    args = []
    unparse_available = sys.version_info >= (3, 9)
    def safe_unparse(n):
        if unparse_available:
            try: return ast.unparse(n).strip()
            except Exception: pass
        if isinstance(n, ast.Name): return n.id
        if isinstance(n, ast.Constant): return repr(n.value)
        return f"<{type(n).__name__}>"

    if hasattr(ast.arguments, 'posonlyargs') and node.args.posonlyargs:
        for arg in node.args.posonlyargs:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {safe_unparse(arg.annotation)}"
            args.append(arg_str)
        args.append('/')

    num_defaults = len(node.args.defaults) if node.args.defaults else 0
    for i, arg in enumerate(node.args.args):
        arg_str = arg.arg
        if arg.annotation:
            arg_str += f": {safe_unparse(arg.annotation)}"
        default_index = i - (len(node.args.args) - num_defaults)
        if default_index >= 0 and default_index < num_defaults and node.args.defaults[default_index] is not None:
            arg_str += f"={safe_unparse(node.args.defaults[default_index])}"
        args.append(arg_str)

    if node.args.vararg:
        arg_str = f"*{node.args.vararg.arg}"
        if node.args.vararg.annotation:
            arg_str += f": {safe_unparse(node.args.vararg.annotation)}"
        args.append(arg_str)

    if hasattr(ast.arguments, 'kwonlyargs') and node.args.kwonlyargs:
        if not node.args.vararg and (node.args.args or (hasattr(ast.arguments, 'posonlyargs') and node.args.posonlyargs)): # Add * if kwonlyargs exist, no *args, but there are other args
            pass # No explicit '*' needed if regular or pos-only args exist, the syntax implies it
        elif not node.args.vararg: # Only kw-only args, or kw-only after pos-only args that ended with /
            args.append('*')

        for i, arg in enumerate(node.args.kwonlyargs):
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {safe_unparse(arg.annotation)}"
            if node.args.kw_defaults and i < len(node.args.kw_defaults) and node.args.kw_defaults[i] is not None:
                arg_str += f"={safe_unparse(node.args.kw_defaults[i])}"
            args.append(arg_str)

    if node.args.kwarg:
        arg_str = f"**{node.args.kwarg.arg}"
        if node.args.kwarg.annotation:
            arg_str += f": {safe_unparse(node.args.kwarg.annotation)}"
        args.append(arg_str)

    signature_str = "(" + ", ".join(args) + ")"
    if node.returns:
        try:
            return_annotation_str = safe_unparse(node.returns)
            if return_annotation_str:
                signature_str += f" -> {return_annotation_str}"
        except Exception:
            pass
    return signature_str


def get_source_segment(source_code, node):
    """
    Extracts the exact source code string for a given Python AST node,
    including any preceding decorators.
    """
    lines = source_code.splitlines(keepends=True)
    source_lines_str = "".join(lines)

    if hasattr(ast, 'get_source_segment'):
        if sys.version_info >= (3, 11):
             try:
                 return ast.get_source_segment(source_lines_str, node, extend_past_eol=True)
             except TypeError:
                   return ast.get_source_segment(source_lines_str, node)
        elif sys.version_info >= (3, 8):
            core_segment = ast.get_source_segment(source_lines_str, node)
            if core_segment is None: return None

            start_lineno_idx = node.lineno - 1
            decorator_start_lineno_idx = start_lineno_idx
            for i in range(start_lineno_idx - 1, -1, -1):
                line = lines[i].strip()
                if line.startswith('@'):
                    decorator_start_lineno_idx = i
                elif line and not line.startswith('#'): # Stop if non-decorator, non-comment
                    break
                elif not line and i < decorator_start_lineno_idx -1: # Stop on blank line unless it's right before decorators
                    break

            end_index = (node.end_lineno if hasattr(node, 'end_lineno') else node.lineno)
            full_segment_lines = lines[decorator_start_lineno_idx : end_index]
            return "".join(full_segment_lines).strip()

    # Fallback for older Python versions (< 3.8)
    start_lineno_idx = node.lineno - 1
    end_lineno_idx = node.end_lineno - 1 if hasattr(node, 'end_lineno') else start_lineno_idx

    decorator_start_lineno_idx = start_lineno_idx
    for i in range(start_lineno_idx - 1, -1, -1):
        line = lines[i].strip()
        if line.startswith('@'):
            decorator_start_lineno_idx = i
        elif line and not line.startswith('#'):
            break
        elif not line and i < decorator_start_lineno_idx - 1:
            break
    segment = "".join(lines[decorator_start_lineno_idx : end_lineno_idx + 1])
    return segment.strip()


def parse_python_file(filepath, content):
    """
    Parses a Python file's content to extract structured information, including nested functions.
    """
    file_data = {
        "path": filepath, "type": "python", "imports": [], "classes": {}, "functions": {},
        "start_lineno": 1, "end_lineno": len(content.splitlines()), "full_content": content,
        "function_calls_raw": [] # To store collected calls before DB insertion
    }
    if not content.strip():
        file_data["message"] = "File is empty or contains only whitespace."
        return file_data

    try:
        tree = ast.parse(content)
        module_docstring = get_docstring(tree)
        if module_docstring:
             file_data["docstring"] = module_docstring
    except SyntaxError as e:
        print(f"Syntax error in {filepath}: {e}")
        file_data.update({"type": "python_error", "error": str(e)})
        return file_data
    except Exception as e:
        print(f"Unexpected parsing error in {filepath}: {e}")
        file_data.update({"type": "python_error", "error": str(e)})
        return file_data

    # Use the call extractor to find all function calls
    call_extractor = PythonCallExtractor()
    call_extractor.visit(tree)
    file_data["function_calls_raw"] = call_extractor.collected_calls

    # --- NEW: Recursive inner function to parse any block of nodes ---
    def _parse_body(nodes, is_class_body=False):
        """
        Recursively parses a list of AST nodes (like the body of a module, function, or class).
        Returns a tuple of (functions_dict, classes_dict).
        """
        functions_found = {}
        classes_found = {}

        for node in nodes:
            # 1. Handle Functions and AsyncFunctions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = node.name
                source_seg = get_source_segment(content, node)

                # RECURSIVE CALL: Parse the body of this function for nested functions
                nested_functions, _ = _parse_body(node.body, is_class_body)

                functions_found[func_name] = {
                    "type": "method" if is_class_body else "function",
                    "name": func_name,
                    "signature": get_signature(node),
                    "docstring": get_docstring(node),
                    "source_code": textwrap.dedent(source_seg) if source_seg else None,
                    "start_lineno": node.lineno,
                    "end_lineno": node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
                    "nested_functions": nested_functions # Store the nested functions dict here
                }

            # 2. Handle Classes (only if we are not already in a class)
            elif isinstance(node, ast.ClassDef) and not is_class_body:
                class_name = node.name
                class_source_seg = get_source_segment(content, node)

                # RECURSIVE CALL: Parse the class body to get methods
                methods_found, _ = _parse_body(node.body, is_class_body=True)

                classes_found[class_name] = {
                    "type": "class",
                    "name": class_name,
                    "docstring": get_docstring(node),
                    "source_code": textwrap.dedent(class_source_seg) if class_source_seg else None,
                    "start_lineno": node.lineno,
                    "end_lineno": node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
                    "methods": methods_found # Store methods found in the class body
                }

            # 3. Handle Imports (only at the top level of the module)
            elif isinstance(node, (ast.Import, ast.ImportFrom)) and not is_class_body:
                try:
                    if sys.version_info >= (3, 9):
                        import_str = ast.unparse(node).strip()
                    else: # Manual fallback
                        if isinstance(node, ast.Import):
                            names = [n.name + (f" as {n.asname}" if n.asname else "") for n in node.names]
                            import_str = f"import {', '.join(names)}"
                        elif isinstance(node, ast.ImportFrom):
                            module = node.module if node.module else ""
                            names = [n.name + (f" as {n.asname}" if n.asname else "") for n in node.names]
                            level = '.' * node.level if node.level else ''
                            import_str = f"from {level}{module} import {', '.join(names)}"
                    file_data["imports"].append(import_str)
                except Exception as e:
                    print(f"Warning: Could not process import node in {filepath}: {ast.dump(node)[:100]}... - {e}")
                    file_data["imports"].append(f"# Error processing import: {ast.dump(node)[:100]}...")

        return functions_found, classes_found

    # --- Initial call to start parsing from the module's top-level body ---
    top_level_functions, top_level_classes = _parse_body(tree.body)
    file_data["functions"] = top_level_functions
    file_data["classes"] = top_level_classes

    return file_data



# --- Helper Functions for HTML Parsing ---

def _get_element_ancestry(tag, stop_at_tag=None):
    path = []
    for parent in tag.parents:
        if stop_at_tag and parent is stop_at_tag: break
        if parent.name in ['html', 'body'] and parent.parent is None: break
        if parent.name is None: continue
        tag_repr = parent.name
        if parent.get('id'): tag_repr += f"#{parent['id']}"
        classes = parent.get('class')
        if isinstance(classes, list) and classes: tag_repr += f".{'.'.join(classes)}"
        path.append(tag_repr)
    path.reverse()
    return path



def parse_javascript_content(js_code: str, html_filepath: str = None) -> dict:
    """
    Parses JavaScript code to extract functions and addEventListener calls
    using a manual recursive walk to access parent nodes.
    html_filepath is optional, for context in error messages.
    """
    if not JS_PARSING_AVAILABLE:
        return {"error": "JavaScript parsing skipped: esprima not installed.", "source_file_context": html_filepath}
    if not js_code.strip():
        return {"message": "Script content is empty or whitespace.", "source_file_context": html_filepath}

    functions_found = []
    event_listeners_found = []

    def get_source_from_js_node(node, code_str):
        if hasattr(node, 'range') and isinstance(node.range, list) and len(node.range) == 2:
            start_idx, end_idx = node.range
            return code_str[start_idx:end_idx]
        elif hasattr(node, 'loc') and node.loc and \
             hasattr(node.loc, 'start') and hasattr(node.loc.start, 'index') and \
             hasattr(node.loc, 'end') and hasattr(node.loc.end, 'index'):
            start_idx = node.loc.start.index
            end_idx = node.loc.end.index
            return code_str[start_idx:end_idx]
        return "/* Source unavailable */"

    def custom_js_walk(node, parent_node=None):
        if node is None or not hasattr(node, 'type'): # Ensure it's a valid AST node
            return

        # --- Main Logic for Identifying JS Constructs ---
        if node.type == esprima.Syntax.FunctionDeclaration:
            func_name = node.id.name if hasattr(node, 'id') and node.id else None
            source_code = get_source_from_js_node(node, js_code)
            functions_found.append({
                "type": "function_declaration", "name": func_name, "source_code": source_code,
                "start_lineno": node.loc.start.line, "end_lineno": node.loc.end.line
            })
        elif node.type in [esprima.Syntax.FunctionExpression, esprima.Syntax.ArrowFunctionExpression]:
            func_name = None
            if parent_node:
                if parent_node.type == esprima.Syntax.VariableDeclarator and \
                   node == getattr(parent_node, 'init', None) and \
                   hasattr(parent_node, 'id') and getattr(parent_node.id, 'type', None) == esprima.Syntax.Identifier:
                    func_name = parent_node.id.name
                elif parent_node.type == esprima.Syntax.MethodDefinition and \
                     node == getattr(parent_node, 'value', None) and \
                     hasattr(parent_node, 'key') and getattr(parent_node.key, 'type', None) == esprima.Syntax.Identifier:
                    func_name = parent_node.key.name
                elif parent_node.type == esprima.Syntax.Property and \
                     node == getattr(parent_node, 'value', None) and \
                     hasattr(parent_node, 'key'): # Key could be Identifier or Literal
                    if getattr(parent_node.key, 'type', None) == esprima.Syntax.Identifier:
                        func_name = parent_node.key.name
                    # If key is Literal (e.g. "myFunc": function(){}), func_name remains None or could be parent_node.key.value
            source_code = get_source_from_js_node(node, js_code)
            functions_found.append({
                "type": "function_expression" if node.type == esprima.Syntax.FunctionExpression else "arrow_function_expression",
                "name": func_name, "source_code": source_code,
                "start_lineno": node.loc.start.line, "end_lineno": node.loc.end.line
            })
        elif node.type == esprima.Syntax.CallExpression and \
             hasattr(node.callee, 'type') and node.callee.type == esprima.Syntax.MemberExpression and \
             hasattr(node.callee, 'property') and getattr(node.callee.property, 'type', None) == esprima.Syntax.Identifier and \
             node.callee.property.name == 'addEventListener' and \
             hasattr(node, 'arguments') and len(node.arguments) >= 2:

            target_source = get_source_from_js_node(node.callee.object, js_code)
            event_arg = node.arguments[0]
            event_type = event_arg.value if hasattr(event_arg, 'value') and event_arg.type == esprima.Syntax.Literal else "<??>"
            handler_arg = node.arguments[1]
            handler_source = get_source_from_js_node(handler_arg, js_code)
            handler_name = handler_arg.name if hasattr(handler_arg, 'name') and handler_arg.type == esprima.Syntax.Identifier else None
            full_call_source = get_source_from_js_node(node, js_code)

            event_listeners_found.append({
                "target": target_source, "event_type": event_type,
                "handler_source": handler_source, "handler_type": handler_arg.type, "handler_name": handler_name,
                "source_code": full_call_source,
                "start_lineno": node.loc.start.line, "end_lineno": node.loc.end.line
            })

        # --- Recursive Traversal of Children ---
        child_prop_names = []
        node_type = node.type
        if node_type in [esprima.Syntax.Program, esprima.Syntax.BlockStatement, esprima.Syntax.ClassBody]: child_prop_names.append('body')
        elif node_type == esprima.Syntax.ExpressionStatement: child_prop_names.append('expression')
        elif node_type == esprima.Syntax.IfStatement: child_prop_names.extend(['test', 'consequent', 'alternate'])
        elif node_type == esprima.Syntax.LabeledStatement: child_prop_names.append('body')
        elif node_type == esprima.Syntax.WithStatement: child_prop_names.extend(['object', 'body'])
        elif node_type == esprima.Syntax.SwitchStatement: child_prop_names.extend(['discriminant', 'cases'])
        elif node_type in [esprima.Syntax.ReturnStatement, esprima.Syntax.ThrowStatement, esprima.Syntax.YieldExpression, esprima.Syntax.AwaitExpression, esprima.Syntax.SpreadElement, esprima.Syntax.UnaryExpression, esprima.Syntax.UpdateExpression]: child_prop_names.append('argument')
        elif node_type == esprima.Syntax.TryStatement: child_prop_names.extend(['block', 'handler', 'finalizer'])
        elif node_type == esprima.Syntax.CatchClause: child_prop_names.extend(['param', 'body'])
        elif node_type in [esprima.Syntax.WhileStatement, esprima.Syntax.DoWhileStatement]: child_prop_names.extend(['test', 'body'])
        elif node_type == esprima.Syntax.ForStatement: child_prop_names.extend(['init', 'test', 'update', 'body'])
        elif node_type in [esprima.Syntax.ForInStatement, esprima.Syntax.ForOfStatement]: child_prop_names.extend(['left', 'right', 'body'])
        elif node_type in [esprima.Syntax.FunctionDeclaration, esprima.Syntax.FunctionExpression, esprima.Syntax.ArrowFunctionExpression]:
            if hasattr(node, 'id') and node.id: child_prop_names.append('id')
            if hasattr(node, 'params'): child_prop_names.append('params')
            if hasattr(node, 'body'): child_prop_names.append('body')
        elif node_type == esprima.Syntax.VariableDeclaration: child_prop_names.append('declarations')
        elif node_type == esprima.Syntax.VariableDeclarator: child_prop_names.extend(['id', 'init'])
        elif node_type in [esprima.Syntax.ArrayExpression, esprima.Syntax.ArrayPattern]: child_prop_names.append('elements')
        elif node_type in [esprima.Syntax.ObjectExpression, esprima.Syntax.ObjectPattern]: child_prop_names.append('properties')
        elif node_type == esprima.Syntax.Property: child_prop_names.extend(['key', 'value'])
        elif node_type == esprima.Syntax.SequenceExpression: child_prop_names.append('expressions')
        elif node_type in [esprima.Syntax.BinaryExpression, esprima.Syntax.LogicalExpression, esprima.Syntax.AssignmentExpression]: child_prop_names.extend(['left', 'right'])
        elif node_type == esprima.Syntax.ConditionalExpression: child_prop_names.extend(['test', 'consequent', 'alternate'])
        elif node_type in [esprima.Syntax.CallExpression, esprima.Syntax.NewExpression]: child_prop_names.extend(['callee', 'arguments'])
        elif node_type == esprima.Syntax.MemberExpression: child_prop_names.extend(['object', 'property'])
        elif node_type == esprima.Syntax.SwitchCase: child_prop_names.extend(['test', 'consequent'])
        elif node_type == esprima.Syntax.TemplateLiteral: child_prop_names.extend(['quasis', 'expressions'])
        elif node_type == esprima.Syntax.TaggedTemplateExpression: child_prop_names.extend(['tag', 'quasi'])
        elif node_type in [esprima.Syntax.ClassDeclaration, esprima.Syntax.ClassExpression]:
            if hasattr(node, 'id') and node.id: child_prop_names.append('id')
            if hasattr(node, 'superClass') and node.superClass: child_prop_names.append('superClass')
            child_prop_names.append('body')
        elif node_type == esprima.Syntax.MethodDefinition: child_prop_names.extend(['key', 'value'])
        elif node_type == esprima.Syntax.ImportDeclaration: child_prop_names.extend(['specifiers', 'source'])
        elif node_type in [esprima.Syntax.ExportNamedDeclaration, esprima.Syntax.ExportDefaultDeclaration]:
            if hasattr(node, 'declaration'): child_prop_names.append('declaration')
            if hasattr(node, 'specifiers'): child_prop_names.append('specifiers')
            if hasattr(node, 'source'): child_prop_names.append('source')
        elif node_type == esprima.Syntax.ExportAllDeclaration: child_prop_names.append('source')

        for prop_name in child_prop_names:
            child_value = getattr(node, prop_name, None)
            if child_value is None:
                continue
            if isinstance(child_value, list):
                for item in child_value:
                    custom_js_walk(item, node)
            else:
                custom_js_walk(child_value, node)

    try:
        tree = esprima.parseScript(js_code, {"loc": True, "range": True, "comment": False, "tokens": False})
        custom_js_walk(tree)

        return {
            "functions": functions_found,
            "event_listeners": event_listeners_found,
            "source_file_context": html_filepath # Also add context on success
        }
    except esprima.Error as e:
        error_message = getattr(e, 'message', str(e))
        line_num_str = str(getattr(e, 'lineNumber', 'N/A'))
        col_num_str = str(getattr(e, 'column', 'N/A'))

        context_msg = f" in inline script of '{html_filepath}'" if html_filepath else ""

        if f"(line {line_num_str}, column {col_num_str})" in error_message:
            print(f"JavaScript Parse Error{context_msg}: {error_message}")
        else:
            print(f"JavaScript Parse Error{context_msg}: {error_message} (line {line_num_str}, column {col_num_str})")

        return {
            "error": f"JavaScript syntax error{context_msg}: {error_message}",
            "full_content_on_error": js_code,
            "source_file_context": html_filepath
        }
    except Exception as e:
        context_msg = f" in inline script of '{html_filepath}'" if html_filepath else ""
        print(f"Unexpected JavaScript parsing error{context_msg}: {e}")
        # import traceback
        # print(traceback.format_exc()) # Uncomment for full traceback during debugging
        return {
            "error": f"Unexpected JavaScript parsing error{context_msg}: {str(e)}",
            "full_content_on_error": js_code,
            "source_file_context": html_filepath
        }

def parse_js_file(filepath, content):
    """
    Parses a standalone JavaScript file's content to extract structured information.
    """
    file_data = {
        "path": filepath, "type": "javascript", "constructs": [],
        "start_lineno": 1, "end_lineno": len(content.splitlines()), "full_content": content
    }
    if not content.strip():
        file_data["message"] = "File is empty or contains only whitespace."
        return file_data
    if not JS_PARSING_AVAILABLE:
        file_data.update({"type": "javascript_skipped", "message": "JavaScript parsing skipped: esprima not installed."})
        return file_data

    # Use the existing JS parser, passing the filepath for error context
    parsed_js = parse_javascript_content(content, html_filepath=filepath)

    if "error" in parsed_js:
        file_data.update({
            "type": "javascript_error",
            "error": parsed_js["error"]
        })
        return file_data

    # Combine functions and event listeners into a single list of constructs
    for func in parsed_js.get('functions', []):
        file_data['constructs'].append({
            'name': func.get('name'),
            'construct_type': func.get('type'),
            'source_code': func.get('source_code'),
            'start_lineno': func.get('start_lineno'),
            'end_lineno': func.get('end_lineno')
        })

    for listener in parsed_js.get('event_listeners', []):
        # Create a representative name for the event listener for easier identification
        listener_name = f"{listener.get('target', 'unknown_target')}.addEventListener('{listener.get('event_type', 'unknown_event')}')"
        file_data['constructs'].append({
            'name': listener_name,
            'construct_type': 'event_listener',
            'source_code': listener.get('source_code'),
            'start_lineno': listener.get('start_lineno'),
            'end_lineno': listener.get('end_lineno')
        })

    return file_data


def parse_html_file(filepath, content):
    """
    Parses an HTML file's content for structure, forms, links, scripts, styles, etc.
    """
    file_data = {
        "path": filepath, "type": "html", "title": None, "forms": [], "links": [],
        "images": [], "htmx_elements": [], "scripts": [], "inline_styles": [],
        "body_structure_preview": [],
        "start_lineno": 1, "end_lineno": len(content.splitlines()), "full_content": content
    }
    if not content.strip():
        file_data["message"] = "File is empty or contains only whitespace."
        return file_data
    if not HTML_PARSING_AVAILABLE:
        file_data.update({"type": "html_skipped", "message": "HTML parsing skipped: beautifulsoup4 or lxml not installed."})
        return file_data

    try:
        soup = BeautifulSoup(content, 'lxml') # Removed from_encoding
        for comment_node in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment_node.extract()

        if soup.title and soup.title.string:
            file_data["title"] = soup.title.string.strip()

        for form in soup.find_all('form'):
            form_data = {"id": form.get('id'), "action": form.get('action'), "method": form.get('method'), "inputs": [], "ancestry_path": _get_element_ancestry(form, soup.body)}
            for input_tag in form.select('input, textarea, select'):
                form_data["inputs"].append({
                    "tag": input_tag.name, "type": input_tag.get('type'), "name": input_tag.get('name'),
                    "id": input_tag.get('id'), "value": input_tag.get('value'),
                    "placeholder": input_tag.get('placeholder'), "required": input_tag.get('required') is not None
                })
            file_data["forms"].append(form_data)

        for link in soup.find_all('a'):
            link_data = {"text": link.get_text(strip=True), "href": link.get('href'), "ancestry_path": _get_element_ancestry(link, soup.body)}
            if link_data["text"] or link_data["href"]: file_data["links"].append(link_data)

        for img in soup.find_all('img'):
            img_data = {"src": img.get('src'), "alt": img.get('alt'), "width": img.get('width'), "height": img.get('height'), "ancestry_path": _get_element_ancestry(img, soup.body)}
            if img_data["src"]: file_data["images"].append(img_data)

        htmx_attrs_regex = re.compile(r'^hx-.+')
        for element in soup.find_all(lambda tag: any(htmx_attrs_regex.match(attr) for attr in tag.attrs if isinstance(attr, str))):
             file_data["htmx_elements"].append({
                 "tag": element.name, "id": element.get('id'), "classes": element.get('class'),
                 "hx_attributes": {attr: value for attr, value in element.attrs.items() if isinstance(attr, str) and htmx_attrs_regex.match(attr)},
                 "text_snippet": (element.get_text(strip=True)[:100] + "...") if element.get_text(strip=True) else None,
                 "ancestry_path": _get_element_ancestry(element, soup.body)
             })

        for script_tag in soup.find_all('script'):
            start_line_html = script_tag.sourceline if hasattr(script_tag, 'sourceline') and isinstance(script_tag.sourceline, int) else None
            end_line_html = (start_line_html + len(str(script_tag).splitlines()) - 1) if start_line_html is not None else None

            script_data = {
                "src": script_tag.get('src'), "type": script_tag.get('type', 'text/javascript'),
                "content": None, "parsed_js": None,
                "start_lineno_html": start_line_html, "end_lineno_html": end_line_html,
                "ancestry_path": _get_element_ancestry(script_tag, soup.body)
            }
            if script_tag.string:
                inline_content = script_tag.string.strip()
                script_data["content"] = inline_content
                if JS_PARSING_AVAILABLE and inline_content:
                    if script_tag.string:
                        inline_content = script_tag.string.strip()
                        script_data["content"] = inline_content
                    # Pass the HTML filepath for context in case of JS errors
                    script_data["parsed_js"] = parse_javascript_content(inline_content, html_filepath=filepath)
                    if script_data["parsed_js"] and isinstance(script_data["parsed_js"], dict) and start_line_html is not None:
                        for item_list_key in ["functions", "event_listeners"]:
                            for item in script_data["parsed_js"].get(item_list_key, []):
                                if item.get("start_lineno") is not None: # Original line no from esprima
                                    item["start_lineno_file"] = item["start_lineno"] + start_line_html - 1
                                    item["end_lineno_file"] = item["end_lineno"] + start_line_html - 1
                                else: # Should not happen if esprima provides loc
                                    item["start_lineno_file"] = None
                                    item["end_lineno_file"] = None
            if script_data.get("src") or script_data.get("content"):
                file_data["scripts"].append(script_data)

        for style_tag in soup.find_all('style'):
            if style_tag.string:
                start_line_html = style_tag.sourceline if hasattr(style_tag, 'sourceline') and isinstance(style_tag.sourceline, int) else None
                end_line_html = (start_line_html + len(str(style_tag).splitlines()) - 1) if start_line_html is not None else None
                file_data["inline_styles"].append({
                    "type": style_tag.get('type', 'text/css'), "content": style_tag.string.strip(),
                    "start_lineno_html": start_line_html, "end_lineno_html": end_line_html,
                    "ancestry_path": _get_element_ancestry(style_tag, soup.body)
                })

        relevant_selectors_body_children = 'body > div, body > section, body > article, body > main, body > aside, body > nav, body > header, body > footer, body > form, body > ul, body > ol, body > table, body > h1, body > h2, body > h3'
        if soup.body:
            for element in soup.body.select(relevant_selectors_body_children):
                file_data["body_structure_preview"].append({
                    "tag": element.name, "id": element.get('id'), "classes": element.get('class'),
                    "text_snippet": (element.get_text(strip=True)[:100] + "...") if element.get_text(strip=True) else None,
                    "ancestry_path": _get_element_ancestry(element, soup.body)
                })
            if not file_data["body_structure_preview"]: # Fallback
                for element in soup.body.select('div[id], section[id], article[id], nav[id], header[id], footer[id], form[id]'):
                    preview_data = {
                        "tag": element.name, "id": element.get('id'), "classes": element.get('class'),
                        "text_snippet": (element.get_text(strip=True)[:100] + "...") if element.get_text(strip=True) else None,
                        "ancestry_path": _get_element_ancestry(element, soup.body)
                    }
                    if preview_data not in file_data["body_structure_preview"]:
                        file_data["body_structure_preview"].append(preview_data)
    except Exception as e:
        print(f"Error parsing HTML file {filepath}: {e}")
        # print(traceback.format_exc()) # Uncomment for debugging
        file_data.update({"type": "html_error", "error": str(e)})
    return file_data

# --- Helper Function for Basic CSS Parsing ---

def parse_css_file(filepath, content):
    """
    Performs basic parsing of a CSS file's content to extract rules.
    """
    file_data = {
        "path": filepath, "type": "css", "rules": [],
        "start_lineno": 1, "end_lineno": len(content.splitlines()), "full_content": content
    }
    if not content.strip():
        file_data["message"] = "File is empty or contains only whitespace."
        return file_data

    content_no_comments = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    rule_pattern = re.compile(r'\s*([^}]*?)\s*{([^}]*)}\s*', re.DOTALL)

    for match in rule_pattern.finditer(content): # Iterate on original content for line numbers
        selectors_raw = match.group(1).strip()
        full_rule_text = match.group(0).strip() # The entire matched rule text

        if selectors_raw:
            # Calculate line numbers based on match position in original content
            start_lineno = 1 + content[:match.start()].count('\n')
            end_lineno = start_lineno + full_rule_text.count('\n')

            rule_data = {
                "selectors": [s.strip() for s in selectors_raw.split(',') if s.strip()],
                "source_code": full_rule_text,
                "start_lineno": start_lineno,
                "end_lineno": end_lineno
            }
            file_data["rules"].append(rule_data)
    return file_data

### NEW PARSING FUNCTIONS FOR DATA FILES ###

def parse_json_file(filepath, content):
    """
    Parses a JSON file's content.
    """
    line_count = len(content.splitlines())
    file_data = {
        "path": filepath, "type": "json", "data": None,
        "start_lineno": 1, "end_lineno": line_count, "full_content": content
    }
    if not content.strip():
        file_data["message"] = "File is empty or contains only whitespace."
        return file_data
    try:
        file_data["data"] = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"JSON syntax error in {filepath}: {e}")
        file_data.update({"type": "json_error", "error": str(e)})
    return file_data

def parse_yaml_file(filepath, content):
    """
    Parses a YAML file's content.
    """
    line_count = len(content.splitlines())
    file_data = {
        "path": filepath, "type": "yaml", "data": None,
        "start_lineno": 1, "end_lineno": line_count, "full_content": content
    }
    if not content.strip():
        file_data["message"] = "File is empty or contains only whitespace."
        return file_data
    if not YAML_PARSING_AVAILABLE:
        file_data.update({"type": "yaml_skipped", "message": "YAML parsing skipped: PyYAML not installed."})
        return file_data
    try:
        file_data["data"] = yaml.safe_load(content)
    except yaml.YAMLError as e:
        print(f"YAML syntax error in {filepath}: {e}")
        file_data.update({"type": "yaml_error", "error": str(e)})
    return file_data

def parse_toml_file(filepath, content):
    """
    Parses a TOML file's content.
    """
    line_count = len(content.splitlines())
    file_data = {
        "path": filepath, "type": "toml", "data": None,
        "start_lineno": 1, "end_lineno": line_count, "full_content": content
    }
    if not content.strip():
        file_data["message"] = "File is empty or contains only whitespace."
        return file_data
    if not TOML_PARSING_AVAILABLE:
        file_data.update({"type": "toml_skipped", "message": "TOML parsing skipped: toml library not installed."})
        return file_data
    try:
        file_data["data"] = toml.loads(content)
    except toml.TomlDecodeError as e:
        print(f"TOML syntax error in {filepath}: {e}")
        file_data.update({"type": "toml_error", "error": str(e)})
    return file_data


# --- Main Directory Processing Function (Modified for DB) ---

def build_project_database(root_dir=".", output_filename="project_context.db"):
    """
    Walks a directory tree, processes files, and builds a structured SQLite database.
    """
    ### DB MOD ###: Remove the project_data dict and set up DB connection
    if os.path.exists(output_filename):
        os.remove(output_filename)
        print(f"Removed existing database '{output_filename}'.")

    try:
        conn = sqlite3.connect(output_filename)
        cursor = conn.cursor()
        create_schema(cursor)
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return

    directory_tree_list = []

    excluded_filenames_set = set(EXCLUDED_FILENAMES)
    managed_filenames_set = set(MANAGED_FILENAMES)
    include_content_filenames_set = set(INCLUDE_CONTENT_FOR_SPECIFIC_FILENAMES)

    # Counters for summary
    excluded_dir_count = 0
    excluded_filename_count = 0
    excluded_binary_ext_count = 0
    excluded_ignored_text_ext_count = 0
    managed_count = 0
    skipped_non_utf8_count = 0
    parsing_error_count = 0
    included_by_allow_list_count = 0
    processed_file_count = 0
    skipped_parsing_setup = {}

    for subdir, dirs, files_in_dir in os.walk(root_dir, followlinks=False):
        original_dirs = list(dirs)
        dirs[:] = [d for d in original_dirs if d not in EXCLUDED_DIRS]
        excluded_dir_count += len(original_dirs) - len(dirs)

        relative_subdir = os.path.relpath(subdir, root_dir).replace("\\", "/")
        if relative_subdir == "." and root_dir == ".":
            if "./" not in directory_tree_list: directory_tree_list.append("./")
        elif relative_subdir != ".":
            directory_tree_list.append(f"{relative_subdir}/")
            cursor.execute("INSERT OR IGNORE INTO directories (path) VALUES (?)", (f"{relative_subdir}/",))

        for file_name in files_in_dir:
            filepath = os.path.join(subdir, file_name)
            relative_filepath = os.path.relpath(filepath, root_dir).replace("\\", "/")
            directory_tree_list.append(relative_filepath)

            # 1. Check EXCLUDED_FILENAMES
            if file_name in excluded_filenames_set:
                excluded_filename_count += 1
                continue

            _, file_extension = os.path.splitext(file_name)
            file_extension_lower = file_extension.lower()

            # 2. Check BINARY_EXTENSIONS
            if file_extension_lower in BINARY_EXTENSIONS:
                excluded_binary_ext_count += 1
                continue

            # 3. Check MANAGED_FILENAMES or MANAGED_EXTENSIONS
            if file_name in managed_filenames_set or file_extension_lower in MANAGED_EXTENSIONS:
                managed_count += 1
                line_count_m = 1
                try:
                    with open(filepath, 'rb') as f_bytes:
                        line_count_m = f_bytes.read().count(b'\n') + 1
                except Exception: pass

                ### DB MOD ###: Insert managed file entry into the DB
                managed_entry = {
                    "path": relative_filepath, "type": "managed_static",
                    "message": "Content managed externally or omitted for brevity.",
                    "full_content": None, "start_lineno": 1, "end_lineno": max(1, line_count_m)
                }
                insert_file_data(cursor, managed_entry)
                processed_file_count += 1
                continue

            # --- Try to read and process content ---
            content = None
            file_details = None
            processed_this_file = False # Flag to indicate if file was handled

            # 4. Check INCLUDE_CONTENT_FOR_SPECIFIC_FILENAMES (Allow List)
            if file_name in include_content_filenames_set:
                included_by_allow_list_count +=1
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    line_count = max(1, len(content.splitlines()))

                    if file_extension_lower in PARSEABLE_CODE_EXTENSIONS:
                        if file_extension_lower == '.py': file_details = parse_python_file(relative_filepath, content)
                        elif file_extension_lower in ('.html', '.htm'):
                            if HTML_PARSING_AVAILABLE: file_details = parse_html_file(relative_filepath, content)
                            else:
                                file_details = {"path": relative_filepath, "type": "html_skipped", "message": "HTML parsing skipped: libraries missing.", "full_content": content, "start_lineno": 1, "end_lineno": line_count}
                                skipped_parsing_setup['html'] = skipped_parsing_setup.get('html', 0) + 1
                        elif file_extension_lower == '.css': file_details = parse_css_file(relative_filepath, content)
                        elif file_extension_lower == '.js':
                            if JS_PARSING_AVAILABLE: file_details = parse_js_file(relative_filepath, content)
                            else:
                                file_details = {"path": relative_filepath, "type": "javascript_skipped", "message": "JS parsing skipped: esprima missing.", "full_content": content, "start_lineno": 1, "end_lineno": line_count}
                                skipped_parsing_setup['javascript'] = skipped_parsing_setup.get('javascript', 0) + 1
                        ### NEW: Handle data files on allow list ###
                        elif file_extension_lower == '.json': file_details = parse_json_file(relative_filepath, content)
                        elif file_extension_lower in ('.yml', '.yaml'):
                            if YAML_PARSING_AVAILABLE: file_details = parse_yaml_file(relative_filepath, content)
                            else:
                                file_details = {"path": relative_filepath, "type": "yaml_skipped", "message": "YAML parsing skipped: library missing.", "full_content": content, "start_lineno": 1, "end_lineno": line_count}
                                skipped_parsing_setup['yaml'] = skipped_parsing_setup.get('yaml', 0) + 1
                        elif file_extension_lower == '.toml':
                            if TOML_PARSING_AVAILABLE: file_details = parse_toml_file(relative_filepath, content)
                            else:
                                file_details = {"path": relative_filepath, "type": "toml_skipped", "message": "TOML parsing skipped: library missing.", "full_content": content, "start_lineno": 1, "end_lineno": line_count}
                                skipped_parsing_setup['toml'] = skipped_parsing_setup.get('toml', 0) + 1
                        else: # Should not be reached if PARSEABLE_CODE_EXTENSIONS is well-defined
                            file_details = {"path": relative_filepath, "type": "unhandled_parseable_on_allow_list", "full_content": content, "start_lineno": 1, "end_lineno": line_count}
                    else: # Not parseable, but on allow list - store as generic text
                        file_details = {"path": relative_filepath, "type": file_extension_lower[1:] if file_extension_lower else "plaintext", "full_content": content, "start_lineno": 1, "end_lineno": line_count}

                    if "error" in file_details.get("type", ""): parsing_error_count += 1

                    ### DB MOD ###: Insert data instead of appending to dict
                    insert_file_data(cursor, file_details)
                    processed_file_count += 1
                    processed_this_file = True

                except UnicodeDecodeError:
                    skipped_non_utf8_count += 1
                    line_count_rb = 1
                    try:
                        with open(filepath, 'rb') as fb: line_count_rb = max(1, fb.read().count(b'\n') + 1)
                    except Exception: pass
                    error_details = {"path": relative_filepath, "type": "skipped_non_utf8", "message": "File on allow-list skipped due to non-UTF-8 encoding.", "start_lineno": 1, "end_lineno": line_count_rb}
                    insert_file_data(cursor, error_details)
                    processed_file_count += 1
                    processed_this_file = True
                except Exception as e:
                    parsing_error_count +=1
                    line_count_rb = 1
                    try:
                        with open(filepath, 'rb') as fb: line_count_rb = max(1, fb.read().count(b'\n') + 1)
                    except Exception: pass
                    error_details = {"path": relative_filepath, "type": "read_error_on_allow_list", "error": str(e), "message": f"Error reading allow-listed file: {e}", "start_lineno": 1, "end_lineno": line_count_rb}
                    insert_file_data(cursor, error_details)
                    processed_file_count += 1
                    processed_this_file = True

            if processed_this_file:
                continue # Move to the next file

            # 5. Check IGNORED_TEXT_EXTENSIONS (only if not processed by allow list)
            if file_extension_lower in IGNORED_TEXT_EXTENSIONS:
                excluded_ignored_text_ext_count += 1
                continue

            # 6. Default processing for other text files (parseable or generic)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                line_count = max(1, len(content.splitlines()))

                if file_extension_lower in PARSEABLE_CODE_EXTENSIONS:
                    if file_extension_lower == '.py': file_details = parse_python_file(relative_filepath, content)
                    elif file_extension_lower in ('.html', '.htm'):
                        if HTML_PARSING_AVAILABLE: file_details = parse_html_file(relative_filepath, content)
                        else:
                            file_details = {"path": relative_filepath, "type": "html_skipped", "message": "HTML parsing skipped: libraries missing.", "full_content": content, "start_lineno": 1, "end_lineno": line_count}
                            skipped_parsing_setup['html'] = skipped_parsing_setup.get('html', 0) + 1
                    elif file_extension_lower == '.css': file_details = parse_css_file(relative_filepath, content)
                    elif file_extension_lower == '.js':
                        if JS_PARSING_AVAILABLE: file_details = parse_js_file(relative_filepath, content)
                        else:
                            file_details = {"path": relative_filepath, "type": "javascript_skipped", "message": "JS parsing skipped: esprima missing.", "full_content": content, "start_lineno": 1, "end_lineno": line_count}
                            skipped_parsing_setup['javascript'] = skipped_parsing_setup.get('javascript', 0) + 1
                    ### NEW: Handle data files ###
                    elif file_extension_lower == '.json': file_details = parse_json_file(relative_filepath, content)
                    elif file_extension_lower in ('.yml', '.yaml'):
                        if YAML_PARSING_AVAILABLE: file_details = parse_yaml_file(relative_filepath, content)
                        else:
                            file_details = {"path": relative_filepath, "type": "yaml_skipped", "message": "YAML parsing skipped: library missing.", "full_content": content, "start_lineno": 1, "end_lineno": line_count}
                            skipped_parsing_setup['yaml'] = skipped_parsing_setup.get('yaml', 0) + 1
                    elif file_extension_lower == '.toml':
                        if TOML_PARSING_AVAILABLE: file_details = parse_toml_file(relative_filepath, content)
                        else:
                            file_details = {"path": relative_filepath, "type": "toml_skipped", "message": "TOML parsing skipped: library missing.", "full_content": content, "start_lineno": 1, "end_lineno": line_count}
                            skipped_parsing_setup['toml'] = skipped_parsing_setup.get('toml', 0) + 1
                    else: # Should not be reached
                        file_details = {"path": relative_filepath, "type": "unhandled_parseable", "full_content": content, "start_lineno": 1, "end_lineno": line_count}
                else: # Generic text file not caught by any other rule
                    file_details = {"path": relative_filepath, "type": file_extension_lower[1:] if file_extension_lower else "plaintext", "full_content": content, "start_lineno": 1, "end_lineno": line_count}

                if "error" in file_details.get("type", ""): parsing_error_count += 1

                ### DB MOD ###: Insert data instead of appending to dict
                insert_file_data(cursor, file_details)
                processed_file_count += 1

            except UnicodeDecodeError:
                skipped_non_utf8_count += 1
                line_count_rb = 1
                try:
                    with open(filepath, 'rb') as fb: line_count_rb = max(1, fb.read().count(b'\n') + 1)
                except Exception: pass
                error_details = {"path": relative_filepath, "type": "skipped_non_utf8", "message": "File skipped due to non-UTF-8 encoding.", "start_lineno": 1, "end_lineno": line_count_rb}
                insert_file_data(cursor, error_details)
                processed_file_count += 1
            except Exception as e:
                parsing_error_count +=1
                line_count_rb = 1
                try:
                    with open(filepath, 'rb') as fb: line_count_rb = max(1, fb.read().count(b'\n') + 1)
                except Exception: pass
                error_details = {"path": relative_filepath, "type": "read_error", "error": str(e), "message": f"Error reading file: {e}", "start_lineno": 1, "end_lineno": line_count_rb}
                insert_file_data(cursor, error_details)
                processed_file_count += 1

    ### DB MOD ###: Finalize the database
    try:
        # Insert metadata
        cursor.execute("INSERT INTO metadata (key, value) VALUES (?, ?)", ('root_directory', os.path.abspath(root_dir)))
        cursor.execute("INSERT INTO metadata (key, value) VALUES (?, ?)", ('generated_time', datetime.now().isoformat()))
        cursor.execute("INSERT INTO metadata (key, value) VALUES (?, ?)", ('description', "Structured code context for LLM interaction and project diffing/recreation."))

        # Insert directory tree
        for path in sorted(directory_tree_list):
            cursor.execute("INSERT INTO directory_tree (path) VALUES (?)", (path,))

        conn.commit()
    except sqlite3.Error as e:
        print(f"Error during database finalization: {e}")
    finally:
        conn.close()

    print(f"\nSuccessfully wrote structured project context to '{output_filename}'")
    print(f"Summary of Exclusions/Inclusions:")
    print(f"  - {excluded_dir_count} directories skipped during walk (not in directory_tree).")
    print(f"  - {excluded_filename_count} specific files excluded from 'files' table.")
    print(f"  - {excluded_binary_ext_count} binary files by extension excluded from 'files' table.")
    print(f"  - {included_by_allow_list_count} files had content included via specific filename allow-list.")
    print(f"  - {excluded_ignored_text_ext_count} files by extension had content ignored (not on allow-list).")
    print(f"  - {managed_count} files managed (metadata only, no full content).")
    print(f"Processing Summary:")
    if skipped_non_utf8_count:
        print(f"  - Skipped reading {skipped_non_utf8_count} non-UTF-8 text files (entry added to 'files' with error type).")
    if parsing_error_count:
        print(f"  - Encountered {parsing_error_count} files with syntax, parsing, or read errors (entry added to 'files' with error type).")
    for lang, count in skipped_parsing_setup.items():
        print(f"  - Skipped parsing {count} {lang.upper()} files due to missing libraries (entry added to 'files' with full content).")
    print(f"  - Total file entries in database: {processed_file_count}.")
    print(f"  - Full directory tree recorded: {len(directory_tree_list)} entries.")


if __name__ == "__main__":
    root_directory = sys.argv[1] if len(sys.argv) > 1 else "."
    build_project_database(root_directory)