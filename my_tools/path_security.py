# my_tools/path_security.py
import os

def _get_project_root() -> str | None:
    """
    Determines the project's root workspace directory based on the 
    CODEBASE_DB_PATH environment variable.
    """
    # <<< FIX: The environment variable IS the project root.
    workspace_path = os.environ.get("CODEBASE_DB_PATH")

    if not workspace_path:
        return None

    # <<< FIX: We just need to validate it's a real directory.
    absolute_workspace_path = os.path.abspath(workspace_path)
    if not os.path.isdir(absolute_workspace_path):
        return None

    return absolute_workspace_path

def _is_path_safe(path_to_check: str) -> bool:
    """
    Ensures the path is within the project directory defined by _get_project_root()
    and prevents directory traversal attacks.
    """
    project_root = _get_project_root()
    if not project_root:
        return False

    # This logic is correct and does not need to change.
    requested_path = os.path.realpath(os.path.abspath(path_to_check))
    safe_root = os.path.realpath(project_root)
    return os.path.commonpath([safe_root, requested_path]) == safe_root

# This function is no longer needed as the logic is in the codebase_manager,
# but we can leave it in case other tools use it.
def get_db_path() -> str | None:
    """Gets the absolute path to the project database."""
    project_root = _get_project_root()
    if not project_root:
        return None
    return os.path.join(project_root, "project_context.db")