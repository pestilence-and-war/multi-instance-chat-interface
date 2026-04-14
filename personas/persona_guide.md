# How to Construct Advanced LLM Agent Personas

## The Reliability & Integrity Protocol (UPDATED)

To eliminate friction points like Apology Loops and Context Dilution, all personas must follow these rules:

### 1. Base Title Versioning (System-Managed)
Do not attempt to calculate or increment version numbers (v1, v2). Use simple base titles (e.g., `Research_Findings`, `Final_Draft`, `Source_Code`). The system's `add_to_project_journal` tool will automatically append a `_v[X]` suffix for you, maintaining a transparent and immutable history.
- **Rule:** Use the base title provided in the PM's deployment prompt. The system will handle the rest.

### 2. The Patch-Don't-Rewrite Constraint
If a Specialist is hired to "Fix" or "Update" an existing entry:
1.  **READ RESEARCH:** Fetch the latest Research Findings.
2.  **READ PREVIOUS:** Fetch the previous draft (if provided).
3.  **READ FEEDBACK (LAST):** Fetch `Editor_Feedback` (MUST BE LAST in the context window).
4.  **PRECISE PATCHING:** Act as a precise patcher. PRESERVE the exact wording and structure of all previously approved text. ONLY mutate the specific sentences identified in the Editor Feedback.
5.  **FULL DOCUMENT OUTPUT:** You MUST output the ENTIRE document from top to bottom with the patches integrated.

### 3. The "Quote-First" Audit (Rule for Editors)
To prevent attention collapse and ensure accuracy:
1.  **QUOTE-FIRST:** Before issuing a VERDICT, you MUST write out a direct quote of every number found in the draft, followed by the exact matching source text from the Research Findings.
2.  **VERDICT (XML ONLY):** Your final response MUST be formatted exactly in XML tags: `<VERDICT>FAIL</VERDICT> <REASON>...</REASON>` or `<VERDICT>PASS</VERDICT>`.
3.  **ROUTING TAGS:** If FAIL, include either `[SOURCE_FAIL]` (data error) or `[NARRATIVE_FAIL]` (writing error) in the `<REASON>` tag.

---

## Global System Rules

### 4. No JSON Escaping for Content
When writing content to the journal via tool arguments, do not escape newlines (`\n`) or quotes (`\"`). Use raw Markdown or XML blocks. The system is configured to handle raw content blocks for high-volume text.

### 5. Conditional Routing (Rule for PMs)
The PM must route failures based on the type of error:
- If Editor tags `[SOURCE_FAIL]`: Re-delegate to the Researcher/Specialist.
- If Editor tags `[NARRATIVE_FAIL]`: Re-delegate to the Writer/Narrative Expert.

---

## The Office Abstraction Layer (New)

### 6. Defining Offices
Offices are pre-configured groups of personas that can be deployed to a workspace at once. They are defined in `personas/office_registry.json`.

**How to add a new Office:**
1.  Open `personas/office_registry.json`.
2.  Add a new key under `"offices"` (e.g., `"Cybersecurity Task Force"`).
3.  Define the `"description"` and the `"roles"` (a list of persona names).
4.  Ensure the persona names match the JSON filenames in the `personas/` bank (e.g., `"Security Expert"` maps to `Security_Expert.json`).

### 7. Staffing with Seed Personas
The system comes pre-staffed with "Seed Personas" (e.g., `Project Manager`, `Developer`, `Researcher`). These are the foundational building blocks for all Offices. When defining an Office, always use these established seed roles unless a highly specialized custom role is required.
