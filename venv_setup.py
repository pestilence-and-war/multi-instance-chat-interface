# venv_setup.py

import sys
import os
import subprocess
import venv

def setup_venv(project_root: str):
    """
    Checks for a virtual environment in project_root.
    If none exists, creates one named 'venv'.
    """
    venv_dir = None
    for venv_name in ['venv', '.venv', 'env']:
        potential_venv = os.path.join(project_root, venv_name)
        if os.path.isdir(potential_venv):
            venv_dir = potential_venv
            break
            
    if venv_dir:
        print(f"Virtual environment already exists at: {venv_dir}")
        return True

    print(f"Creating new virtual environment in: {project_root}")
    new_venv_path = os.path.join(project_root, 'venv')
    
    try:
        # Create virtual environment
        venv.create(new_venv_path, with_pip=True)
        print(f"Successfully created venv at {new_venv_path}")
        return True
    except Exception as e:
        print(f"Error creating virtual environment: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python venv_setup.py <project_root>")
        sys.exit(1)
        
    project_root = sys.argv[1]
    if not os.path.isdir(project_root):
        print(f"Error: {project_root} is not a valid directory.")
        sys.exit(1)
        
    if setup_venv(project_root):
        sys.exit(0)
    else:
        sys.exit(1)
