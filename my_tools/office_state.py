# my_tools/office_state.py
import json
import os
import re
from datetime import datetime
from my_tools.path_security import _get_project_root

JOURNAL_FILE = "project_journal.json"

def _get_journal_path():
    root = _get_project_root()
    if not root: return None
    return os.path.join(root, JOURNAL_FILE)

def _get_latest_version(journal, base_title):
    """Helper to find the highest version suffix for a base_title."""
    pattern = re.compile(rf"^{re.escape(base_title)}_v(\d+)$")
    versions = []
    for entry in journal.keys():
        if entry == base_title:
            versions.append(0)
        match = pattern.match(entry)
        if match:
            versions.append(int(match.group(1)))
    
    if not versions:
        return None
    return max(versions)

def add_to_project_journal(entry_title: str, content: str, auto_increment: bool = True) -> str:
    """
    Adds a major update or finding to the shared project journal. 
    By default, it auto-increments the version (e.g., 'Draft' becomes 'Draft_v1', then 'Draft_v2').

    @param entry_title (string): The base title for this entry (e.g., 'Research_Findings'). REQUIRED.
    @param content (string): The actual data or text to store. REQUIRED.
    @param auto_increment (boolean): If True (default), appends/increments a _v[X] suffix.
    """
    path = _get_journal_path()
    if not path: return json.dumps({"status": "error", "message": "No project root set."})

    journal = {}
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                journal = json.load(f)
        except: journal = {}

    final_title = entry_title
    if auto_increment:
        latest = _get_latest_version(journal, entry_title)
        if latest is None:
            # If the exact base_title doesn't exist, we can use base_title_v1
            final_title = f"{entry_title}_v1"
        else:
            final_title = f"{entry_title}_v{latest + 1}"

    journal[final_title] = {
        "timestamp": datetime.now().isoformat(),
        "content": content
    }

    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(journal, f, indent=2)
        return json.dumps({
            "status": "success", 
            "message": f"Entry added to journal as '{final_title}'.",
            "actual_title": final_title
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def get_project_state() -> str:
    """
    Returns a summary of the latest versions of all documents in the journal.
    Use this at the start of a task to see the current 'State of Record'.
    """
    path = _get_journal_path()
    if not path or not os.path.exists(path):
        return json.dumps({"status": "success", "state": {}, "message": "Journal is empty."})

    try:
        with open(path, 'r', encoding='utf-8') as f:
            journal = json.load(f)
        
        state = {}
        # Identify base titles by stripping _v[X]
        for entry in journal.keys():
            base = re.sub(r'_v\d+$', '', entry)
            latest = _get_latest_version(journal, base)
            state[base] = f"{base}_v{latest}" if latest > 0 else base
            
        return json.dumps({"status": "success", "state": state}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def read_project_journal() -> str:
    """
    Retrieves a list of all entry titles and their metadata (timestamp, length, preview) from the shared project journal, 
    WITHOUT loading the full content to save context window. 
    Use `read_journal_entry(entry_title)` to read the actual content of a specific entry.
    """
    path = _get_journal_path()
    if not path or not os.path.exists(path):
        return json.dumps({"status": "success", "entries": {}, "message": "Journal is empty."})

    try:
        with open(path, 'r', encoding='utf-8') as f:
            journal = json.load(f)
            
        entries_summary = {}
        for title, data in journal.items():
            content = data.get("content", "")
            entries_summary[title] = {
                "timestamp": data.get("timestamp", ""),
                "length": len(content),
                "preview": content[:100] + ("..." if len(content) > 100 else "")
            }
            
        return json.dumps({
            "status": "success", 
            "message": "Use read_journal_entry(entry_title) to view full content.",
            "entries": entries_summary
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def read_journal_entry(entry_title: str) -> str:
    """
    Retrieves a specific entry from the project journal.
    If you pass a base name like 'Draft', it will attempt to find the latest version.

    @param entry_title (string): The title (or base title) of the entry to read. REQUIRED.
    """
    path = _get_journal_path()
    if not path or not os.path.exists(path):
        return json.dumps({"status": "error", "message": "Journal not found."})

    try:
        with open(path, 'r', encoding='utf-8') as f:
            journal = json.load(f)
        
        target = entry_title
        if entry_title not in journal:
            latest = _get_latest_version(journal, entry_title)
            if latest is not None:
                target = f"{entry_title}_v{latest}" if latest > 0 else entry_title
        
        if target in journal:
            return json.dumps({
                "status": "success",
                "entry_title": target,
                "content": journal[target].get("content", ""),
                "timestamp": journal[target].get("timestamp", "")
            }, indent=2)
        else:
            return json.dumps({"status": "error", "message": f"Entry '{entry_title}' not found (tried latest version as well)."})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def archive_journal_entry(entry_title: str, file_path: str) -> str:
    """
    Saves a specific journal entry directly to a file in the project. 

    @param entry_title (string): The title (or base title) of the entry to save. REQUIRED.
    @param file_path (string): The project-relative path where the file should be saved. REQUIRED.
    """
    path = _get_journal_path()
    if not path or not os.path.exists(path):
        return json.dumps({"status": "error", "message": "Journal not found."})

    try:
        with open(path, 'r', encoding='utf-8') as f:
            journal = json.load(f)
        
        target = entry_title
        if entry_title not in journal:
            latest = _get_latest_version(journal, entry_title)
            if latest is not None:
                target = f"{entry_title}_v{latest}" if latest > 0 else entry_title
        
        if target not in journal:
            return json.dumps({"status": "error", "message": f"Entry '{entry_title}' not found in journal."})
        
        content = journal[target].get("content", "")
        
        from my_tools.jailed_file_manager import jailed_create_file
        return jailed_create_file(file_path, content)

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def update_milestone_status(milestone_name: str, status: str) -> str:
    """
    (Low-Cost) Updates the status of a specific milestone in the 'Master_Plan' journal entry.
    Use this to track progress (e.g., changing '[ ]' to '[x]' or adding 'Status: IN_PROGRESS').

    @param milestone_name (string): A unique substring of the milestone to update (e.g., 'Milestone 2'). REQUIRED.
    @param status (string): The new status to apply. Must be 'IN_PROGRESS', 'COMPLETED', or 'FAILED'. REQUIRED.
    """
    path = _get_journal_path()
    if not path or not os.path.exists(path):
        return json.dumps({"status": "error", "message": "Journal not found."})

    try:
        with open(path, 'r', encoding='utf-8') as f:
            journal = json.load(f)
        
        # Find the latest Master_Plan
        target = "Master_Plan"
        latest = _get_latest_version(journal, "Master_Plan")
        if latest is not None:
            target = f"Master_Plan_v{latest}" if latest > 0 else "Master_Plan"
        
        if target not in journal:
            return json.dumps({"status": "error", "message": "Master_Plan not found in journal."})
            
        content = journal[target].get("content", "")
        lines = content.split('\n')
        updated = False
        
        for i, line in enumerate(lines):
            # Find the line that looks like a milestone and contains the name
            if milestone_name.lower() in line.lower() and ("- [" in line or "Milestone" in line):
                # 1. Update Checkbox
                if status == 'COMPLETED':
                    lines[i] = line.replace("- [ ]", "- [x]").replace("- []", "- [x]")
                else:
                    lines[i] = line.replace("- [x]", "- [ ]").replace("- [X]", "- [ ]")
                
                # 2. Update Status Text (e.g., *Status: ...*)
                import re
                if "*Status:*" in lines[i] or "*Status*" in lines[i]:
                    lines[i] = re.sub(r'\*Status:[^*]*\*', f'*Status: {status}*', lines[i])
                else:
                    # Append status if not present
                    lines[i] = lines[i].strip() + f" - *Status: {status}*"
                
                updated = True
                break
                
        if not updated:
            return json.dumps({"status": "error", "message": f"Milestone containing '{milestone_name}' not found in the Master_Plan."})

        new_content = '\n'.join(lines)
        
        # Save as a new version
        return add_to_project_journal("Master_Plan", new_content)

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})
