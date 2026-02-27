import json
import os
from git import Repo, exc
from typing import List, Optional

def git_status() -> str:
    """
    Returns the current status of the git repository (staged, unstaged, untracked files).
    """
    try:
        repo = Repo(".", search_parent_directories=True)
        status = {
            "branch": repo.active_branch.name,
            "is_dirty": repo.is_dirty(),
            "untracked_files": repo.untracked_files,
            "staged_files": [item.a_path for item in repo.index.diff("HEAD")],
            "unstaged_changes": [item.a_path for item in repo.index.diff(None)]
        }
        return json.dumps({"status": "success", "data": status}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def git_diff(file_path: Optional[str] = None) -> str:
    """
    Returns the diff of unstaged changes. Optionally for a specific file.

    @param file_path (string): Optional path to a specific file to diff.
    """
    try:
        repo = Repo(".", search_parent_directories=True)
        diff_text = repo.git.diff(file_path) if file_path else repo.git.diff()
        return json.dumps({"status": "success", "diff": diff_text})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def git_commit_history(limit: int = 5) -> str:
    """
    Returns a list of recent commits.

    @param limit (integer): Number of recent commits to return. Defaults to 5.
    """
    try:
        repo = Repo(".", search_parent_directories=True)
        commits = []
        for commit in repo.iter_commits(max_count=limit):
            commits.append({
                "hash": commit.hexsha,
                "author": commit.author.name,
                "date": commit.authored_datetime.isoformat(),
                "message": commit.message.strip()
            })
        return json.dumps({"status": "success", "commits": commits}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})
