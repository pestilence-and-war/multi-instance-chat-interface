### `my_tools/html_analyzer.py`

#### HTML Analyzer Tool for AI Chat Interface

This tool empowers your AI models to inspect and understand the structural elements within HTML files. It allows for the listing of all recognized structural elements or filtering for specific types like forms, links, scripts, or HTMX-specific attributes. This capability is vital for tasks related to frontend development, such as understanding page structure, identifying interactive components, or analyzing content.

**Purpose:** To enable AI models to parse HTML content and list specific structural elements, facilitating web development and content analysis tasks.

**Key Function:**

*   **`list_html_elements(file_path: str, element_type: Optional[str] = None) -> str`**
    *   **Description:** Lists all structural elements or a specific type of element from an HTML file. This tool can be used to find all forms, links, scripts, or HTMX-specific attributes within a given HTML file.
    *   **Parameters:**
        *   `file_path` (string): The path to the HTML file to analyze. (Required)
        *   `element_type` (string, optional): The specific type of element to filter for. Valid types include: `'form'`, `'link'`, `'script'`, `'htmx'`. If omitted, all recognized structural elements are returned.
    *   **Returns:** A string (JSON format) containing the details of the found HTML elements.

**How it Solves a Problem:**
Manually sifting through complex HTML to find specific elements can be tedious and error-prone. This `list_html_elements` tool allows the AI to programmatically locate and extract relevant parts of an HTML document, greatly speeding up tasks such as identifying interactive components, extracting content from specific sections, or checking for the presence of certain UI elements, especially those leveraging HTMX.