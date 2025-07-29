import os

def get_project_root() -> str | None:
    """
    Determines the project's root directory based on the CODEBASE_DB_PATH 
    environment variable. Returns None if the variable is not set or the path is invalid.
    This makes the security context explicit and required.
    """
    db_path = os.environ.get("CODEBASE_DB_PATH")

    if not db_path:
        # The environment variable is the single source of truth. If it's not set,
        # we cannot determine the project root.
        return None

    # Ensure the database file actually exists at the given path.
    absolute_db_path = os.path.abspath(db_path)
    if not os.path.exists(absolute_db_path):
        return None

    # The project root is the directory containing the database file.
    project_root = os.path.dirname(absolute_db_path)
    return project_root

def is_path_safe(path_to_check: str) -> bool:
    """
    Ensures the path is within the project directory defined by get_project_root()
    and prevents directory traversal attacks.
    """
    project_root = get_project_root()

    if not project_root:
        # If we couldn't determine the project root, no path can be considered safe.
        return False

    # Get the absolute, canonical path of the user-provided path.
    # os.path.realpath resolves any symbolic links.
    requested_path = os.path.realpath(os.path.abspath(path_to_check))

    # Get the absolute, canonical path of the project root.
    safe_root = os.path.realpath(project_root)

    # The safest way to check if the requested path is a subdirectory of 
    # (or the same as) the project root.
    return os.path.commonpath([safe_root, requested_path]) == safe_root

def get_db_path() -> str | None:
    """
    Gets the absolute path to the project database from the environment variable.
    Returns None if the variable is not set.
    """
    db_path = os.environ.get('CODEBASE_DB_PATH')
    if not db_path:
        return None
    return os.path.abspath(db_path)
