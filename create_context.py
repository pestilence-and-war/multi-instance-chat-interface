import os
import json
import sys

#System tool for creaing full project context to LLMs
#It is the older version of the DB creation tool currently used with tools

def directory_to_json(root_dir=".", output_filename="project_context.json"):
    """
    Converts a directory and its contents to a JSON file, excluding specific
    directories, files, and file types based on predefined lists.

    Args:
        root_dir (str): The root directory to process (relative to the current directory). Defaults to ".".
        output_filename (str): The name of the output JSON file. Defaults to "project_context.json".
    """
    data = {}
    script_filepath = os.path.abspath(__file__)

    # Define directories to exclude from traversal
    excluded_dirs = {
        '__pycache__', '.git', '.svn', '.hg', # Version control
        'node_modules', 'venv', '.venv', '__pypackages__', 'vendor', # Dependency directories
        'dist', 'build', # Build/distribution directories
        '.idea', '.vscode' # IDE specific directories
    }

    # Define specific filenames to exclude regardless of location
    # Added '.env' here for explicit exclusion
    excluded_filenames = {
        'htmx.min.js',
        'recreate_structure.py',
        '.env' # Explicitly exclude the file named .env
    }

    # Define file extensions to exclude (case-insensitive check will be used)
    # Includes user-requested, existing, and common sensitive/binary/irrelevant types
    # Keeping '.env' here still excludes files like 'config.env'
    excluded_extensions = {
        '.json', '.jsonl', '.log', '.txt', # User requested + existing log/text
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico', # Images
        '.mp4', '.mp3', '.avi', '.mov', # Media
        '.pdf', '.docx', '.xlsx', '.pptx', # Documents
        '.bin', '.exe', '.dll', '.so', '.dylib', '.o', '.a', '.lib', '.class', '.pyc', # Binaries/Compiled
        '.zip', '.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.rar', '.7z', # Archives
        '.sqlite', '.db', '.sql', # Databases/SQL dumps
        '.pem', '.key', '.cer', '.crt', '.pfx', # Keys/Certificates
        '.lock', '.tmp', '.bak', # Lock/Temp/Backup files
        '.DS_Store' # macOS specific file
    }

    for subdir, dirs, files in os.walk(root_dir):
        # Exclude specified directories BEFORE processing their contents
        # Modify dirs in-place to prevent os.walk from descending into them
        dirs[:] = [d for d in dirs if d not in excluded_dirs]

        for file in files:
            filepath = os.path.join(subdir, file)
            absolute_filepath = os.path.abspath(filepath)

            # Exclude the script itself by its absolute path
            if absolute_filepath == script_filepath:
                continue

            # Exclude specific filenames (including the explicit .env)
            if file in excluded_filenames:
                print(f"Excluding specific file: {filepath}")
                continue

            # Exclude files by extension (case-insensitive) - handles files like config.env
            _, file_extension = os.path.splitext(file)
            if file_extension.lower() in excluded_extensions:
                print(f"Excluding file type: {filepath}")
                continue

            try:
                # Attempt to read the file content
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Use forward slashes consistently for paths, relative to root_dir
                relative_filepath = os.path.relpath(filepath, root_dir).replace("\\", "/")
                data[relative_filepath] = content

            except UnicodeDecodeError:
                 # Catch files that are likely binary or not UTF-8 text
                 print(f"Skipping binary or non-UTF-8 file: {filepath}")
            except Exception as e:
                # Catch any other reading errors
                print(f"Error reading {filepath}: {e}")

    # Write the JSON data to the output file, overwriting if it exists
    try:
        with open(output_filename, 'w', encoding='utf-8') as outfile:
            json.dump(data, outfile, indent=2)
        print(f"\nSuccessfully wrote project context to '{output_filename}'")
        print(f"Excluded {len(excluded_dirs)} directory types, {len(excluded_filenames)} specific files, and {len(excluded_extensions)} file extension types.")
    except Exception as e:
        print(f"Error writing to '{output_filename}': {e}")


if __name__ == "__main__":
    # Get the root directory from command-line arguments, or default to current directory
    if len(sys.argv) > 1:
        root_directory = sys.argv[1]
    else:
        root_directory = "."

    # Call the function
    directory_to_json(root_directory)
