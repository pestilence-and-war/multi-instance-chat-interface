### `my_tools/css_analyzer.py`

#### CSS Analyzer Tool for AI Chat Interface

This tool allows your AI models to inspect and understand the structure of CSS files within your project. Specifically, it can list all defined CSS rules and their selectors. This capability is vital for tasks related to frontend development, such as debugging styling issues, understanding existing stylesheets, refactoring CSS, or ensuring consistent design patterns.

**Purpose:** To enable AI models to parse and analyze CSS files, providing insights into styling rules and their application.

**Key Function:**

*   **`list_css_rules(file_path: str) -> str`**
    *   **Description:** Lists all rules and their selectors from a given CSS file.
    *   **Parameters:**
        *   `file_path` (string): The path to the CSS file to analyze. (Required)
    *   **Returns:** A string (JSON format) detailing the CSS rules and their selectors found in the file.

**How it Solves a Problem:**
Understanding a complex CSS file by eye can be challenging. This `list_css_rules` tool provides a structured overview of the stylesheet's components, allowing the AI to quickly grasp the styling logic. This is particularly useful when the AI is assisting with frontend tasks, such as identifying redundant rules, suggesting optimizations, or ensuring that new components adhere to existing design system conventions.