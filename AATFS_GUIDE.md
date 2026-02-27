# The Digital Office Framework (AATFS)

This guide provides a comprehensive overview of the **Digital Office Framework**, the core architectural philosophy of the Autonomous Agent Task Force System (AATFS). This framework enables a team of AI agents to collaborate on complex projects with high fidelity, data integrity, and autonomous error correction.

## 1. Core Concept: The Digital Office

The AATFS transforms a single LLM into an "Office" composed of specialized domain experts (Personas). Unlike standard chat systems, these agents do not work in isolation; they share a **Project Journal** and follow a strict **Orchestration Protocol** to deliver final products.

The entire system is managed via the **Project Manager (PM)** or specialized "Directors" (e.g., Creative Director, Game Director), who act as the orchestrators of the project lifecycle.

## 2. The Shared Project Journal

The **Project Journal** is the "Source of Truth" for the entire office. It is a shared, searchable, and persistent space where all specialists record their progress, findings, and deliverables.

-   **Research_Findings_v1**: Raw data, facts, and the **Source Manifest**.
-   **Financial_Analysis_v1**: Budgetary and numerical findings.
-   **Final_Draft_v1**: The primary output (e.g., a blog post, script, or code).
-   **Editor_Feedback**: Critiques, audit results, and rejection reasons.
-   **Technical_Architecture**: System designs and implementation plans.

## 3. The Specialist Workflow: Read-Modify-Write (RMW)

To maintain context and prevent "cascade failures," all specialists follow the **RMW Protocol**:

1.  **READ PREVIOUS**: Specialists must read the previous draft (v1, v2) and any feedback (Editor_Feedback) before starting.
2.  **MODIFY (FULL REWRITE)**: Specialists perform a *complete rewrite* of the deliverable, integrating the new findings or fixes into the existing context.
3.  **WRITE VERSIONED**: Specialists save their new work to a new version (e.g., `Final_Draft_v2`) to preserve the "Paper Trail."

## 4. Data Integrity: The Source Manifest & Anchors

To eliminate hallucinations, the office follows a strict data anchoring protocol:

-   **The Source Manifest**: Every `Research_Findings` entry *must* end with a list of verified URLs used.
-   **Data Snippets**: Researchers provide literal quotes (snippets) from sources to "anchor" all numerical and factual claims.
-   **Top-Line Anchors**: Agents must identify and verify "anchor" metrics (e.g., Total Revenue) before deriving or calculating any sub-metrics.

## 5. The "Diagnostic Loop" (Autonomous Error Correction)

The most powerful feature of the AATFS is the **Diagnostic Loop**, orchestrated by the **Project Manager** in response to feedback from the **Editor** or **Test Engineer**.

1.  **Orchestration**: The PM hires a Specialist (e.g., Writer) and an Auditor (e.g., Editor).
2.  **Audit**: The Auditor compares the work to the research and rules. They issue a `PASS` or `FAIL`.
3.  **Triage**: If a `FAIL` occurs, the PM does not guess the reason. They read the **Editor_Feedback**.
4.  **Correction**: The PM re-delegates the specific fix to the Specialist, providing them with the exact failure reason and context.
5.  **Finalization**: The project only completes when the Auditor issues a `PASS`.

## 6. Staffing & Roles

The AATFS includes a diverse bank of personas, each with unique toolsets:

| Role | Competency |
| :--- | :--- |
| **Project Manager** | CEO and lead orchestrator. Staffs teams and manages the Diagnostic Loop. |
| **Architect** | High-level system design and initial workspace setup. |
| **Researcher** | Deep information gathering using Tavily and Grokipedia. |
| **Financial Analyst** | Budgeting, forecasting, and math-verified data analysis. |
| **Developer** | Full-stack implementation and code auditing. |
| **Editor** | Quality assurance, hallucination checks, and final polishing. |

## 7. Operational Standards

-   **Markdown First**: All journal entries and reports must use Markdown for clarity and structure.
-   **No Overwriting**: Always use versioned suffixes (`v1`, `v2`) to maintain a clear audit trail.
-   **Silence is Mandatory**: High-level orchestrators (Architect) often output only tool calls to ensure speed and focus.
