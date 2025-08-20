# How to Create Tasks for LLM Agents

This guide provides instructions on how to correctly format and create tasks for agents operating within the automated task workflow system.

## Task System Overview

The system manages tasks through a series of directories. Your primary role in task creation is to place a new task file in the `tasks/0_pending/` directory. The system's `EventMonitor` will automatically detect this new file and assign it to the appropriate agent.

-   **`tasks/0_pending/`**: New tasks are placed here as `.json` files.
-   **`tasks/1_assigned/`**: The Project Manager agent moves tasks here for a specialist agent to execute.
-   **`tasks/3_review/`**: In "stepped" mode, completed tasks are moved here for human review.
-   **`tasks/4_done/`**: Completed and approved tasks are moved here.
-   **`tasks/5_failed/`**: Tasks that fail after multiple retries are moved here.

## The Task File

A task must be defined as a single JSON file with a descriptive name (e.g., `refactor_database_module.json`). This file must contain all the necessary information for an agent to understand and execute the objective.

### JSON Structure

A valid task JSON file must contain the following top-level keys:

| Key             | Type   | Description                                                                                             | Example                                             |
| --------------- | ------ | ------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| `persona`       | String | **Required.** The name of the specialist persona who should perform the task.                           | `"Senior Python Developer"`                         |
| `objective`     | String | **Required.** A clear, verb-driven statement of what the agent needs to accomplish.                     | `"Refactor the attached Python script..."`          |
| `context`       | String | **Required.** All necessary background information, including code snippets, error messages, or reasoning. | `"The current function is slow because..."`         |
| `output_path`   | String | **Required.** The exact file path where the deliverable should be saved.                                | `"src/core/refactored_utils.py"`                    |
| `output_format` | String | A description of the desired structure for the deliverable.                                             | `"Your output should be the complete, refactored Python file."` |
| `constraints`   | Array  | A list of explicit "do nots" or limitations the agent must adhere to.                                   | `["Do not change the function signatures."]`          |

### Explicit Example: `refactor_api_service.json`

Here is a complete example of a high-quality task file. This task instructs a specialist agent to optimize a slow function in a Python script.

```json
{
  "persona": "Surge, the Senior Python Engineer",
  "objective": "Refactor the `process_data` function in the file `services/data_processor.py` to improve performance.",
  "context": "The current `process_data` function is slow because it processes a list of items sequentially, with each item involving a simulated slow operation. The goal is to modify the function to process the data in parallel. You should use Python's built-in `concurrent.futures` module for this. The content of the file is provided here:\n\n```python\n# Content of services/data_processor.py\nimport time\n\ndef process_data(data_list):\n  results = []\n  for item in data_list:\n    # Simulates a slow I/O bound operation\n    time.sleep(1)\n    results.append(item * 2)\n  return results\n```",
  "output_path": "archive/deliverables/refactored_data_processor.py",
  "output_format": "Your deliverable must be the complete, refactored `services/data_processor.py` file content, saved to the specified output path.",
  "constraints": [
    "Do not introduce any external libraries other than what is available in the standard Python library.",
    "Do not change the function's signature (its name and arguments).",
    "Ensure the logic of the slow operation (item * 2) remains the same."
  ]
}
```

By following this structure, you provide the agent with a clear, unambiguous, and actionable task, dramatically increasing the likelihood of a successful and accurate result.