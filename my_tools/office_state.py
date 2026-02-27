# my_tools/office_state.py
import json
import os
from datetime import datetime
from my_tools.path_security import _get_project_root

JOURNAL_FILE = "project_journal.json"

def _get_journal_path():
    root = _get_project_root()
    if not root: return None
    return os.path.join(root, JOURNAL_FILE)

def add_to_project_journal(entry_title: str, content: str) -> str:
    """
    (Low-Cost) Adds a major update or finding to the shared project journal. 
    Use this to store research findings, draft content, or editor feedback so other specialists can see it.

    @param entry_title (string): A clear title for this entry (e.g., 'Research_Findings', 'First_Draft'). REQUIRED.
    @param content (string): The actual data or text to store. REQUIRED.
    """
    path = _get_journal_path()
    if not path: return json.dumps({"status": "error", "message": "No project root set."})

    journal = {}
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                journal = json.load(f)
        except: journal = {}

    journal[entry_title] = {
        "timestamp": datetime.now().isoformat(),
        "content": content
    }

    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(journal, f, indent=2)
        return json.dumps({"status": "success", "message": f"Entry '{entry_title}' added to journal."})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def read_project_journal() -> str:
    """
    (Low-Cost) Retrieves all entries from the shared project journal.
    Specialists should use this for a full overview, but prefer read_journal_entry for specific data.
    """
    path = _get_journal_path()
    if not path or not os.path.exists(path):
        return json.dumps({"status": "success", "journal": {}, "message": "Journal is empty."})

    try:
        with open(path, 'r', encoding='utf-8') as f:
            journal = json.load(f)
        return json.dumps({"status": "success", "journal": journal}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def read_journal_entry(entry_title: str) -> str:
    """
    (Low-Cost) Retrieves a specific entry from the project journal.
    Use this to save context tokens by only reading what is relevant to your task (e.g., 'Research_Findings').

    @param entry_title (string): The title of the entry to read. REQUIRED.
    """
    path = _get_journal_path()
    if not path or not os.path.exists(path):
        return json.dumps({"status": "error", "message": "Journal not found."})

    try:
        with open(path, 'r', encoding='utf-8') as f:
            journal = json.load(f)
        
        if entry_title in journal:
            return json.dumps({
                "status": "success",
                "entry_title": entry_title,
                "content": journal[entry_title].get("content", ""),
                "timestamp": journal[entry_title].get("timestamp", "")
            }, indent=2)
        else:
            return json.dumps({"status": "error", "message": f"Entry '{entry_title}' not found."})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def archive_journal_entry(entry_title: str, file_path: str) -> str:
    """
    (Medium-Cost) Saves a specific journal entry directly to a file in the project. 
    Use this to 'archive' a final draft or report without needing to copy-paste the text.

    @param entry_title (string): The title of the entry to save (e.g., 'Final_Draft'). REQUIRED.
    @param file_path (string): The project-relative path where the file should be saved. REQUIRED.
    """
    path = _get_journal_path()
    if not path or not os.path.exists(path):
        return json.dumps({"status": "error", "message": "Journal not found."})

    try:
        with open(path, 'r', encoding='utf-8') as f:
            journal = json.load(f)
        
        if entry_title not in journal:
            return json.dumps({"status": "error", "message": f"Entry '{entry_title}' not found in journal."})
        
        content = journal[entry_title].get("content", "")
        
        # Use existing jailed_create_file logic indirectly or just write here
        from my_tools.jailed_file_manager import jailed_create_file
        return jailed_create_file(file_path, content)

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})
