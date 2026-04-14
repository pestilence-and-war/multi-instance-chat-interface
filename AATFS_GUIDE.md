# The Digital Office Framework (AATFS)

This guide provides a comprehensive overview of the **Digital Office Framework**, the core architectural philosophy of the Autonomous Agent Task Force System (AATFS). This framework enables a team of AI agents to collaborate on complex projects with high fidelity, data integrity, and autonomous error correction.

## 1. Core Concept: The Digital Office

The AATFS transforms a single LLM into an "Office" composed of specialized domain experts (Personas). Unlike standard chat systems, these agents do not work in isolation; they share a **Project Journal** and follow a strict **Orchestration Protocol** to deliver final products.

The entire system is managed via the **Project Manager (PM)** or specialized "Directors" (e.g., Creative Director, Game Director), who act as the orchestrators of the project lifecycle.

## 2. The Shared Project Journal & Kanban Board

The **Project Journal** is the "Source of Truth" for the entire office. It is a shared, searchable, and persistent space where all specialists record their progress, findings, and deliverables.

-   **Master_Plan (The State Machine)**: A versioned entry containing a strict **Kanban Checklist** (`[ ]` for pending, `[x]` for completed). This allows the system to recover from failures and resume work exactly where it left off.
-   **Research_Findings**: Raw data, facts, and the **Source Manifest**.
-   **Final_Draft**: The primary output (e.g., a blog post, script, or code).
-   **Editor_Feedback / Test_Report**: Critiques, audit results, and rejection reasons.
-   **Technical_Architecture**: System designs and implementation plans.

## 3. The Specialist Workflow: Read-Modify-Write (RMW)

To maintain context and prevent "cascade failures," all specialists follow the **RMW Protocol**:

1.  **READ PREVIOUS**: Specialists must read the previous draft and any feedback before starting.
2.  **MODIFY (FULL REWRITE)**: Specialists perform a *complete rewrite* of the deliverable, integrating the new findings or fixes into the existing context.
3.  **WRITE VERSIONED**: Specialists save their new work to a new version (e.g., `v2`, `v3`) to preserve the "Paper Trail."

## 4. Data Integrity: The Source Manifest & Anchors

To eliminate hallucinations, the office follows a strict data anchoring protocol:

-   **The Source Manifest**: Every `Research_Findings` entry *must* end with a list of verified URLs used.
-   **Anti-Fraud Mandate**: Agents are forbidden from "simulating" or "mocking" work. Reports are considered fraudulent and rejected if they lack raw JSON tool output (e.g., from `execute_command`).
-   **Top-Line Anchors**: Agents must identify and verify "anchor" metrics before deriving or calculating any sub-metrics.

## 5. The "Diagnostic Loop" (Autonomous Error Correction)

The **Diagnostic Loop** is orchestrated by the **Project Manager** in response to feedback from the **Editor** or **Test Engineer**.

1.  **Orchestration**: The PM hires a Specialist and an Auditor.
2.  **Audit**: The Auditor compares the work to the research and rules. They issue a `PASS` or `FAIL`.
3.  **Triage**: If a `FAIL` occurs, the PM reads the **Editor_Feedback** or **[FRAUD_DETECTED]** tag.
4.  **Correction**: The PM re-delegates the specific fix to the Specialist with the exact failure reason.
5.  **Finalization**: The project only completes when the Auditor issues a `PASS`.

## 6. Recursive Planning

Complex goals are handled via **Recursive Strategy**:
1.  The PM hires a **Strategist** using the `develop_project_strategy` tool.
2.  The Strategist analyzes the goal and decomposes it into a versioned **Master_Plan**.
3.  The PM then executes each milestone in the plan sequentially.

## 7. Staffing & Offices

To manage complexity, the AATFS uses **Offices** (pre-staffed departments). Instead of hiring agents one by one, the **Architect** can deploy an entire specialized group:

-   **Software Studio**: Full-stack engineering (PM, Developer, Test Engineer, etc.).
-   **Marketing Agency**: Brand and content (Creative Director, Writer, Visual Researcher).
-   **Research Lab**: Deep-dive analysis (Strategist, Researcher, Financial Analyst).

Offices are defined in `personas/office_registry.json` and instantiated via `deploy_office`.

## 8. Global Telemetry Dashboard

The **📡 Office Telemetry** dashboard provides a real-time, detached view of all office activity.
-   **System Events**: Logs of delegations, tool calls, and errors.
-   **Live Agent Stream**: Real-time text and "Thinking" output from even headless sub-agents.
-   **Transparency**: Allows the user to monitor "Anti-Fraud" compliance and intervene if an agent goes off-track.

## 9. Operational Standards

-   **Windows-Aware**: Shell tools automatically handle path security and command translation (e.g., `python3` to `python`).
-   **Background Services**: Long-running tasks (like web servers) must use `start_background_service` to prevent hanging the orchestration loop.
-   **Context Efficiency**: Orchestrators receive **truncated summaries** of specialist outputs. Full data must be read from the Journal.
-   **Markdown First**: All entries use Markdown for structure.
-   **Silence is Mandatory**: High-level orchestrators often output only tool calls to ensure speed and focus.
