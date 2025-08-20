# How to Construct Advanced LLM Agent Personas

This document outlines the structure and best practices for creating effective and highly configurable personas for LLM agents within the system. A persona defines the agent's identity, capabilities, and operational parameters, turning a general model into a specialized, fine-tuned tool for a specific purpose.

## The Persona System

Personas are instantiated by the system's `EventMonitor`. Each persona is defined by a single JSON file that specifies not only its character (`system_prompt`) and capabilities (`tools`), but also the specific AI model and generation parameters it should use. This allows for precise control over an agent's behavior, creativity, and cost.

## The Persona File Structure

A persona is defined by a JSON file whose name becomes the persona's identifier (e.g., `caesar_the_decomposer.json`). This file provides the complete configuration for the agent.

### JSON Structure

A valid persona JSON file is composed of the following top-level keys:

| Key             | Type   | Description                                                                                                                                                                                                    |
| --------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `persona_name`  | String | **Required.** A human-readable name for the persona.                                                                                                                                                           |
| `model_config`  | Object | An object containing the technical configuration for the AI model. If omitted, the system's default settings will be used.                                                                                       |
| `system_prompt` | String | **Required.** The detailed instruction set that defines the LLM's character, expertise, style, and rules. This is the most critical part of the persona's identity.                                               |
| `tools`         | Array  | **Required.** A list of strings, where each string is the exact name of a tool function the agent is authorized to use (e.g., `read_file`, `create_new_task_file`).                                               |

### The `model_config` Object

This section provides granular control over the agent's underlying AI.

| Key                 | Type   | Description                                                                                                                                                                                                                                                                                            |
| ------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `provider`          | String | *Optional.* The name of the API provider (e.g., "Google"). If not specified, the system's default provider is used.                                                                                                                                                                                     |
| `model_name`        | String | *Optional.* The specific model ID to use (e.g., "gemini-2.5-pro", "gemini-2.5-flash"). Allows you to assign powerful models for complex tasks and faster, cheaper models for simple ones. If not specified, the system's default model is used.                                                              |
| `generation_params` | Object | *Optional.* An object to control the "creativity" of the model's output.                                                                                                                                                                                                                               |
| ↳ `temperature`     | Float  | *Optional.* Controls randomness. Lower values (e.g., `0.2`) make the output more deterministic and focused, ideal for code generation or factual analysis. Higher values (e.g., `1.0`) encourage more creative and diverse responses, suitable for brainstorming or content creation.                 |
| ↳ `top_p`           | Float  | *Optional.* Controls the diversity of the output by considering only the most probable words. It's an alternative way to manage randomness. A typical value is `0.95`.                                                                                                                                |

## Building a High-Quality `system_prompt`

A powerful `system_prompt` is specific, consistent, and believable. It should be constructed by combining the following components into a single, comprehensive text block:

1.  **Core Identity & Role:** Be explicit. Instead of "a helper," define "You are a meticulous quality assurance engineer..."
2.  **Knowledge Domain & Expertise:** Define the scope of what the agent knows and does not know. "Your expertise is in modern frontend development..."
3.  **Communication Style (Tone & Voice):** Define how the agent should communicate. "Your tone is professional, direct, and helpful. You communicate in clear, simple language."
4.  **Constraints & Directives:** Provide explicit rules and a "prime directive." "Your primary goal is to write code that is secure, efficient, and readable. You must not generate code that uses deprecated libraries."

## Explicit Example: `caesar_the_decomposer.json`

This is a complete example of an advanced persona file. It creates "Caesar," a strategic agent whose sole purpose is to break down large, complex requests into a series of smaller, well-defined tasks for other agents.

Notice the `model_config`: Caesar uses a powerful, reasoning-focused model (`gemini-2.5-pro`) and has a very low `temperature` (`0.2`) to ensure its output is logical, structured, and predictable, with minimal creative deviation.

```json
{
  "persona_name": "Caesar, the Strategic Project Decomposer",
  "model_config": {
    "provider": "Google",
    "model_name": "gemini-2.5-pro",
    "generation_params": {
      "temperature": 0.2
    }
  },
  "system_prompt": "You are Caesar, a highly logical and strategic AI agent. Your sole purpose is to decompose large, complex, or multi-step user requests into a series of discrete, actionable tasks. You do not perform the tasks yourself; you create the task files for other specialist agents.\n\nYour prime directive is to create a sequence of tasks that are logical, independent, and contain all necessary context for another agent to succeed. You must think through all dependencies.\n\nRULES:\n1. Your output for each task you create must be a perfectly formatted JSON object.\n2. You must use the `create_new_task_file` tool to write each task into the `tasks/0_pending/` directory.\n3. The file name for each task should be descriptive (e.g., `01_setup_database_schema.json`, `02_write_api_endpoints.json`).\n4. You must be meticulous. Do not make assumptions. If a request is unclear, your only action is to report the ambiguity.",
  "tools": [
    "create_new_task_file",
    "list_files",
    "read_file"
  ]
}```