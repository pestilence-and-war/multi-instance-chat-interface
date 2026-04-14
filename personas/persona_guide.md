# How to Construct Advanced LLM Agent Personas

## The Reliability & Integrity Protocol (v2)

To eliminate friction points like Apology Loops and Context Dilution, all personas must follow these rules:

### 1. Base Title Versioning (System-Managed)
Do not attempt to calculate or increment version numbers (v1, v2). Use simple base titles (e.g., `Research_Findings`, `Final_Draft`). The system's `add_to_project_journal` tool will automatically append a version suffix, maintaining an immutable history.

### 2. The Patch-Don't-Rewrite Constraint
If hired to "Fix" or "Update" an entry:
1.  **READ RESEARCH:** Fetch the latest Research Findings.
2.  **READ PREVIOUS:** Fetch the previous draft.
3.  **READ FEEDBACK (LAST):** Fetch `Editor_Feedback` (MUST BE LAST in the context).
4.  **PRECISE PATCHING:** PRESERVE the exact structure of approved text. ONLY mutate the specific segments identified in the feedback.
5.  **FULL OUTPUT:** You MUST output the ENTIRE document with the patches integrated.

### 3. The "Action-Only" Mandate (Anti-Simulation)
To prevent agents from "faking" work:
-   **NO SIMULATION:** You are forbidden from using words like "simulate", "assume", "mock", or "placeholder" in your output.
-   **RAW PROOF:** A report is considered FRAUDULENT if it does not contain the raw JSON output from a tool call (e.g., the `stdout` from `execute_command`).
-   **EMPIRICAL VERIFICATION:** Never assume a file exists. Use `list_files` to verify it in the current turn.

### 4. The "Quote-First" Audit (Rule for Editors)
1.  **QUOTE-FIRST:** Before issuing a VERDICT, you MUST write out a direct quote of every number found in the draft, followed by the matching source text from the Research.
2.  **VERDICT (XML ONLY):** Your final response MUST be: `<VERDICT>FAIL</VERDICT> <REASON>...</REASON>` or `<VERDICT>PASS</VERDICT>`.
3.  **ROUTING TAGS:** Include `[SOURCE_FAIL]`, `[NARRATIVE_FAIL]`, or `[FRAUD_DETECTED]`.

---

## Global System Rules

### 5. Context Efficiency
-   **Truncated Memory:** Be aware that orchestrators (PMs) only see a **500-character summary** of your conversational output. You MUST save all important data to the Journal or Disk.
-   **Summary Reading:** Use `read_project_journal` to get a list of entries and `read_journal_entry` to fetch specific ones. Do not attempt to read the whole journal at once.

### 6. Participation in the State Machine
If you are an orchestrator (PM or Director):
-   **KANBAN STATUS:** You MUST use the `update_milestone_status` tool to mark milestones as `IN_PROGRESS` or `COMPLETED`. 
-   **RESUMPTION:** Always check the `Master_Plan` at the start of a session to see where the office left off.

---

## The Office Abstraction Layer

### 7. Defining Offices
Offices are groups of personas deployed to a workspace at once. They are defined in `personas/office_registry.json`.

**How to add a new Office:**
1.  Add a new key to `office_registry.json`.
2.  Define the `"description"` and the `"roles"` (list of persona names).
3.  Ensure the persona names match the JSON filenames in the `personas/` bank.

### 8. Staffing with Seed Personas
Always use the foundational "Seed Personas" (`Project Manager`, `Strategist`, `Developer`, `Researcher`) when building a new Office group. Only create a custom persona if the task is highly domain-specific.
