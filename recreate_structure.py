import os
import json
import sys

def create_file_structure_from_json(json_filepath="project_context.json", output_dir="."):
    """
    Recreates a file structure from a JSON file.

    Args:
        json_filepath (str): The path to the JSON file. Defaults to "project_context.json".
        output_dir (str): The root directory where the file structure will be recreated.
                         Defaults to the current directory.
    """
    try:
        with open(json_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {json_filepath}")
        return
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return

    for filepath, content in data.items():
        # Create the directory structure
        full_filepath = os.path.join(output_dir, filepath)
        os.makedirs(os.path.dirname(full_filepath), exist_ok=True)  # Create parent directories if they don't exist

        try:
            with open(full_filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Created: {full_filepath}")
        except Exception as e:
            print(f"Error writing to {full_filepath}: {e}")

if __name__ == "__main__":
    # Get the JSON file path and output directory from command-line arguments
    if len(sys.argv) > 1:
        json_file_path = sys.argv[1]
    else:
        json_file_path = "project_context.json"  # Default JSON file

    if len(sys.argv) > 2:
        output_directory = sys.argv[2]
    else:
        output_directory = "."  # Default output directory

    create_file_structure_from_json(json_file_path, output_directory)
