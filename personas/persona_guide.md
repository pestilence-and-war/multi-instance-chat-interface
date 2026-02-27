# How to Construct Advanced LLM Agent Personas

## The Versioning & Integrity Protocol (NEW)

To prevent data loss through overwriting and to maintain a "Paper Trail" for the Editor and PM, all personas must follow these rules:

### 1. Versioned Entry Naming
Never overwrite a technical or narrative entry. Use a version suffix:
- `Final_Draft_v1`, `Final_Draft_v2`
- `Research_Findings_v1`, `Research_Findings_v2`
- **Rule:** The specialist must report the EXACT name of the new version to the PM in their final response.

### 2. The Read-Modify-Write (RMW) Protocol
If a Specialist is hired to "Fix" or "Update" an existing entry:
1.  **READ PREVIOUS:** You MUST call `read_journal_entry` for the previous version (e.g., `v1`).
2.  **READ FEEDBACK:** You MUST call `read_journal_entry` for `Editor_Feedback`.
3.  **FULL SYNTHESIS:** You MUST output the **entire** document/report in the new entry (e.g., `v2`). Never output just the correction.

### 3. The "Side-by-Side" Audit (Rule for Editors)
When auditing a revision (e.g., `v2`):
1.  Call `read_journal_entry` for BOTH the previous version (`v1`) and the new version (`v2`).
2.  Verify that the fix was applied AND that no previous data was accidentally deleted during the rewrite.

---

## Standard Journal Entry Titles
Specialists should always check their instructions for specific entry titles. 
- `Research_Findings_v[X]`: Raw data and Source Manifest.
- `Final_Draft_v[X]`: The primary full-length content.
- `Editor_Feedback`: Detailed critique and rejection reasons.
- `Project_Plan`: High-level steps from the PM.

### 4. Diagnostic Loop (Rule for PMs)
If a specialist returns a `FAIL`:
- **Archive the Fail:** Use `archive_journal_entry` to save the "Fail" state to a file (e.g., `audit_trail/fail_v1.md`) before delegating the fix.
- **Version Control:** Explicitly tell the specialist: "Read [Entry]_v1 and 'Editor_Feedback', then save the full updated work to [Entry]_v2."
