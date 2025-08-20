1.  **Adding Metadata for Traceability**: For better logging, debugging, and tracking, a `metadata` object is crucial.
2.  **Introducing Priority**: Not all tasks are created equal. A `priority` field allows the system to address urgent or critical tasks first.
3.  **Defining Dependencies**: This is the most powerful addition. A `dependencies` array allows you to build complex workflows where one task cannot start until others are complete.
4.  **Specifying Success Criteria**: Instead of just relying on the creation of a file, `success_criteria` gives the Project Manager persona a concrete checklist to validate the deliverable, enabling a "Quality Assurance" step.

Here is the recreated guide for creating tasks, incorporating these updated best practices.

***

# How to Create Advanced Tasks for LLM Agents

This guide provides instructions on how to correctly format and create tasks for agents operating within the automated task workflow system. This advanced structure allows for complex dependency chains, task prioritization, and explicit quality assurance.

## Task System Overview

The system manages tasks through a series of directories. Your role is to create a task file in `tasks/0_pending/`. The system's `EventMonitor` will detect, prioritize, and assign these tasks based on their configuration.

*   **`tasks/0_pending/`**: New tasks are placed here as `.json` files.
*   **`tasks/1_assigned/`**: The Project Manager agent moves tasks here for a specialist agent to execute.
*   **`tasks/3_review/`**: In "stepped" mode, completed tasks are moved here for review against their `success_criteria`.
*   **`tasks/4_done/`**: Completed and verified tasks are moved here, unblocking any dependent tasks.
*   **`tasks/5_failed/`**: Tasks that fail are moved here.

## The Enhanced Task File Structure

A task must be a single JSON file with a descriptive name (e.g., `02_create_api_endpoints.json`). To enable advanced workflows, the file should include the following structure:

| Key                 | Type   | Description                                                                                                                                                             |
| ------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `metadata`          | Object | **Required.** Contains data for tracking and logging.                                                                                                                   |
| ↳ `task_id`         | String | A unique identifier for the task (e.g., a UUID).                                                                                                                        |
| ↳ `created_by`      | String | The name of the agent or user who created the task (e.g., "Caesar").                                                                                                      |
| ↳ `timestamp`       | String | The ISO 8601 timestamp of when the task was created.                                                                                                                      |
| `priority`          | Number | *Optional.* A numeric priority (e.g., 1-5, with 1 being the highest). The system will assign higher-priority tasks first. Defaults to a medium priority if omitted.     |
| `persona`           | String | **Required.** The name of the specialist persona who should perform the task.                                                                                           |
| `objective`         | String | **Required.** A clear, verb-driven statement of what the agent needs to accomplish.                                                                                     |
| `context`           | String | **Required.** All necessary background information, including code snippets, error messages, or reasoning.                                                              |
| `dependencies`      | Array  | *Optional.* A list of task filenames that MUST be completed (i.e., exist in `tasks/4_done/`) before this task can be assigned.                                            |
| `output_path`       | String | **Required.** The exact file path where the deliverable should be saved.                                                                                                |
| `success_criteria`  | Array  | *Optional.* A list of specific, verifiable conditions that the deliverable must meet to be considered "done". This is used by the Project Manager during the review step. |
| `constraints`       | Array  | *Optional.* A list of explicit "do nots" or limitations the agent must adhere to.                                                                                       |

### Explicit Example: `02_implement_user_auth_endpoints.json`

Here is a complete example of an advanced task file. This task instructs a developer persona to build API endpoints, but it has several key features:
*   It is **high priority**.
*   It **depends on** the database schema being completed first.
*   It has very **specific success criteria** for the Project Manager to verify.

```json
{
  "metadata": {
    "task_id": "a4b1c2d3-e4f5-g6h7-i8j9-k0l1m2n3o4p5",
    "created_by": "Caesar, the Strategic Project Decomposer",
    "timestamp": "2025-08-20T18:00:00Z"
  },
  "priority": 1,
  "persona": "Jules, the Senior Python Engineer",
  "objective": "Implement the user authentication API endpoints using Flask.",
  "context": "The database schema for the 'users' table has been designed and the model is defined in 'src/models/user.py'. Your task is to create the server-side logic for user registration, login, and logout. You will need to read the user model to understand the required fields.",
  "dependencies": [
    "01_design_database_schema.json"
  ],
  "output_path": "archive/deliverables/auth_routes.py",
  "success_criteria": [
    "The deliverable must contain three distinct Flask routes: '/register', '/login', and '/logout'.",
    "The '/register' route must hash the user's password before saving it to the database.",
    "The '/login' route must return a JSON Web Token (JWT) upon successful authentication.",
    "All routes must include error handling for invalid input or database errors."
  ],
  "constraints": [
    "Do not store passwords in plain text.",
    "Use the existing database connection from 'src/database.py'.",
    "Do not add any new external library dependencies to the project."
  ]
}
```

### Impact on the System

Adopting this enhanced structure would require modifications to the `EventMonitor`'s logic. Specifically, the `handle_pending_tasks` function would need to be updated to:
1.  Parse all pending tasks.
2.  Sort them based on the `priority` field.
3.  For each task, check if all filenames listed in its `dependencies` array exist in the `tasks/4_done/` directory before assigning it.

By implementing these changes, you transform the system from a simple task executor into a sophisticated workflow engine capable of managing complex, multi-step projects with greater reliability and control.