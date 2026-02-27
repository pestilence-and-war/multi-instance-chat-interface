# Git Manager Tool (`git_manager_tool.py`)

## What It Does
Provides a high-level interface for interacting with the Git version control system within the active project workspace. It allows agents to track progress, view changes, and understand the project's commit history.

## Functions

### `git_status()`
Returns the current status of the repository, including staged, unstaged, and untracked files.

### `git_diff(file_path=None)`
Returns the diff of unstaged changes. Can be filtered by a specific file.

### `git_commit_history(limit=5)`
Returns a list of the most recent commits, including hashes, authors, dates, and messages.

## Dependencies
-   `pip install gitpython`
-   A valid Git installation must be present on the system.
