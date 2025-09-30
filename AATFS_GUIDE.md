# Autonomous Agent Task Force System (AATFS) Guide

This document provides a comprehensive overview of the Autonomous Agent Task Force System (AATFS), a headless, multi-agent framework designed to automate complex development workflows.

## 1. Core Concept

The AATFS operates as a "headless office" where AI-powered agents collaborate to complete tasks defined by a user. It uses a file-based queueing system to manage tasks and orchestrate the interactions between different agent personas, such as the "Project Manager," "Developer," and "Test Engineer."

The entire system is driven by the `event_monitor.py` script, which acts as the central event loop, watching for changes in the task system and triggering the appropriate agents to perform their roles.

## 2. The Task Directory Structure

The heart of the AATFS is the `tasks/` directory. Each subdirectory represents a specific stage in the lifecycle of a task. Task files are simple JSON documents that are moved between these directories as they progress through the workflow.

-   **`tasks/0_pending/`**
    -   **Purpose:** The initial queue for all new tasks. When a new project is defined, the Project Manager breaks it down into smaller, actionable tasks and places them here.

-   **`tasks/1_assigned/`**
    -   **Purpose:** Contains tasks that have been assigned to a specialist agent (e.g., a Developer). The agent responsible for the task will work on it while the task file resides here.

-   **`tasks/2_testing/`**
    -   **Purpose:** The quality assurance queue. When a developer creates a deliverable, the corresponding task is moved here to await validation by the Test Engineer.

-   **`tasks/3_review/`**
    -   **Purpose:** (For `stepped` mode) Tasks that require human intervention or approval are placed here. The system pauses until the user manually resolves the review.

-   **`tasks/4_done/`**
    -   **Purpose:** The final destination for successfully completed and verified tasks.

-   **`tasks/5_failed/`**
    -   **Purpose:** A general failure queue. Tasks are moved here if they fail due to system errors or exceed their maximum retry count at any stage.

-   **`tasks/6_failed_test/`**
    -   **Purpose:** An archive for tasks that have failed the testing phase. After a Test Engineer submits a FAIL report, the Project Manager moves the original task here for analysis and creates a new bug-fix task.

## 3. The "Test and Correct" Workflow Lifecycle

The AATFS implements a robust feedback loop to ensure the quality of the work produced. This workflow is orchestrated by the Project Manager in response to deliverables created by other agents.

1.  **Task Creation:** A user provides a high-level goal. The **Project Manager** persona is triggered, breaking the goal into one or more task files and placing them in `tasks/0_pending/`.

2.  **Assignment:** The `event_monitor.py` script triggers the **Project Manager** to assign a task. The PM moves a task from `0_pending` to `tasks/1_assigned/`.

3.  **Development:** The monitor detects the new task in `1_assigned` and triggers the assigned **Developer** persona. The developer reads the task, writes the necessary code, and saves their work to the `archive/deliverables/` directory.

4.  **Queue for Testing:** The monitor detects the new deliverable and triggers the **Project Manager**. The PM identifies the completed development task in `1_assigned` and moves it to `tasks/2_testing/`.

5.  **Testing:** The monitor detects the new task in `2_testing` and triggers the **Test Engineer** persona. The Test Engineer analyzes the original task requirements and the developer's deliverable, runs automated tests, and creates a `Test_Report_...` deliverable.

6.  **Triage and Resolution:** The monitor detects the test report and triggers the **Project Manager** again.
    -   **If the report is `Test_Report_PASS_...`**: The PM moves the task from `2_testing` to `4_done`. **The task is complete.**
    -   **If the report is `Test_Report_FAIL_...`**:
        a. The PM moves the failed task from `2_testing` to `6_failed_test` for archival.
        b. The PM creates a *new* bug-fix task in `0_pending/`, instructing the developer to fix the issue described in the FAIL report. The cycle then repeats from Step 2.

This automated "test and correct" loop allows the agent team to autonomously identify and resolve its own errors, leading to a much higher quality of final output.