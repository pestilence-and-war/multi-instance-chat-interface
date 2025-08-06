# Multi-Instance AI Chat Interface

This project is a sophisticated, web-based chat application designed to manage multiple, simultaneous chat sessions with a variety of AI providers. It features a dynamic, tabbed interface built with HTMX for a seamless user experience, a powerful and extensible tool integration system, and a customizable frontend with multiple themes.

The application is architected to be provider-agnostic, allowing users to connect to different AI APIs like Google Gemini, Ollama, and OpenRouter within the same session manager.

## Key Features

*   **Multi-Instance Management:** Open, close, rename, and manage multiple chat sessions in a clean, tabbed interface. Each session maintains its own isolated context, configuration, and toolset.
*   **Provider Agnostic:** Ships with clients for Google, Ollama, and OpenRouter. The modular design in `api_clients/` makes it straightforward to extend support to other AI API providers.
*   **Secure Sandboxed File System Tools:** A suite of tools allowing the LLM to safely perform file system operations (create, delete, move files and directories). This is achieved through a robust, multi-layer security model:
    *   **User Isolation:** A dedicated, low-privilege local user (`JeaToolUser`) runs the commands.
    *   **Directory Jailing:** Operations are restricted to a "jailed" workspace (`C:\SandboxedWorkspaces`), preventing any access to system files.
    *   **Command Whitelisting:** A PowerShell security gate validates every command against a hardcoded list of safe operations.
*   **Dynamic Tool System:**
    *   **Discovery:** Automatically discovers Python tool modules from the `my_tools/` directory.
    *   **Inspection:** Scans modules to view available functions, their signatures, and docstrings directly in the UI.
    *   **Registration:** Register or unregister specific functions for use by a chat instance on the fly, allowing for precise control over the tools available to the AI.
*   **Full Context Control:** A powerful context editor allows users to view, edit, or delete any message within a chat's history. This provides fine-grained control to steer the conversation and correct the AI's behavior.
*   **Dynamic UI with HTMX:** The entire frontend is built using HTMX, creating a responsive, single-page application feel without the complexity of a large JavaScript framework. UI elements are updated dynamically by swapping HTML fragments from the server.
*   **Theming Engine:** Switch between multiple themes, including light and dark modes (`hotseat`, `80s_theme`, `zen_gardens`). The system is designed to be easily extensible with new user-created themes.
*   **Markdown & Code Formatting:** Renders Markdown and provides syntax highlighting for over 300 languages in code blocks, complete with a "copy to clipboard" button.
*   **File Uploads:** Attach files to messages for the AI to use.

## Tech Stack

*   **Backend:** Python 3, Flask, Waitress (as a production-ready WSGI server)
*   **Frontend:** HTML5, Tailwind CSS, JavaScript, HTMX, htmx-ext (for SSE), HyperScript
*   **API Clients:** `google-genai`, `requests`
*   **Core Python Dependencies:**
    *   `flask`, `waitress`
    *   `python-dotenv`
    *   `requests`, `requests-cache`, `retry-requests`
    *   `google-generativeai`, `openai`
    *   `markdown`, `pymdownx-superfences`, `bleach` (For Markdown rendering)
    *   `bs4` (Beautiful Soup) & `esprima` (For HTML/JS parsing in tools)
    *   `geopy`, `pandas`, `openmeteo-requests` (For the weather tool)

## Project Structure

The project is organized into several key directories and modules:

```
.
├── api_clients/        # Handles connections to external AI providers (Google, Ollama, etc.)
├── chat_logs/          # Stores chat history logs for persistence.
├── chat_sessions/      # Saved session data (in JSON format) and uploaded files.
├── my_tools/           # Directory for custom, user-defined Python tools.
│   ├── jailed_file_manager.py  # Sandboxed file system tools.
│   └── SafeExecutor.ps1      # PowerShell security gate for jailed tools.
├── server_logs.txt     # Log file for the running server process, useful for debugging.
├── static/             # Compiled CSS, JavaScript, and other assets.
├── templates/          # Flask HTML templates (Jinja2), including partials for HTMX.
├── tool_vdb/           # Vector database for semantic tool searching.
├── .env                # Environment variables (API keys, secrets).
├── app.py              # Main Flask application: handles all routing and core logic.
├── chat_instance.py    # Defines the ChatInstance class, representing a single chat session state.
├── chat_manager.py     # Manages all active chat instances and their lifecycles.
├── tool_registry.py    # Discovers and loads tools from the my_tools/ directory.
├── run_waitress.py     # Production-ready entry point using the Waitress WSGI server.
├── utils.py            # Utility functions used across the application.
├── run_app_as_jea_user.bat # NEW: Launcher for running the app with the secure sandbox.
├── Setup-Simple-Sandbox.ps1  # One-time script to create the sandbox user and directory.
├── Fix-Project-Permissions.ps1 # One-time script to grant sandbox user permissions.
└── SETUP.md            # Detailed guide for setting up the secure sandbox environment.
```

## Frontend Architecture

The frontend is built with a modern, server-driven approach.

*   **HTMX:** Instead of a large client-side framework, this application uses HTMX to make AJAX requests and swap out sections of the page with HTML rendered by the Flask server. This keeps the frontend logic simple and located directly in the HTML templates. The `templates/partials/` directory contains the HTML fragments used for these dynamic updates.
*   **Tailwind CSS:** The project uses Tailwind for its utility-first CSS workflow. The `static/css/input.css` file contains the base Tailwind directives. During the build process, `tailwind.config.js` instructs Tailwind to scan all `*.html` and `*.js` files for class names and generate a highly optimized `static/css/style.css` file containing only the necessary styles.
*   **Theming:** The theme system (`theme_manager.js`) dynamically loads different CSS files from the `static/css/themes/` directory and updates the DOM to apply the new styles, allowing for instant theme switching.

## Setup and Installation

### System Requirements
*   The new **Secure Sandboxed File System Tools** feature requires **Windows 10/11** and **PowerShell 5.1+** with Administrator access for a one-time setup.
*   The rest of the application is cross-platform.

### Installation Steps

1.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Create a Virtual Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install Python Dependencies:**
    It is recommended to create a `requirements.txt` file from the "Tech Stack" section above and install via pip.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Frontend Dependencies:**
    This project uses Node.js and `npm` to manage the Tailwind CSS build process.
    ```bash
    npm install
    ```

5.  **Set Up Secure Sandbox (Required for File System Tools on Windows):**
    To enable the powerful and safe file system tools, you must perform a one-time setup to create the sandboxed environment.
    *   **For detailed instructions, please follow the guide in `SETUP.md`.**
    *   In summary, you will need to run two PowerShell scripts as an Administrator from the project root:
        1.  `.\Setup-Simple-Sandbox.ps1` (to create the user and jailed directory)
        2.  `.\Fix-Project-Permissions.ps1` (to grant the app necessary read permissions)

6.  **Configure Environment Variables:**
    Create a `.env` file in the project root. The `CODEBASE_DB_PATH` is required for the built-in tools that analyze a project's source code (including its own code).
    ```
    FLASK_SECRET_KEY='a_very_secret_key'
    GOOGLE_API_KEY='your_google_api_key_here'
    OPENROUTER_API_KEY='your_key_here'
    OLLAMA_API_KEY='your_ollama_key_here' # Can be set to None
    TAVILY_API_KEY='your_tavily_key_here'

    # Required for code analysis tools
    CODEBASE_DB_PATH='full_path_to_project_context.db'
    ```

7.  **Build CSS:**
    Compile the Tailwind CSS. The `--watch` flag will automatically rebuild the CSS when you make changes to template or JS files.
    ```bash
    npm run build:css
    ```

8.  **Run the Application:**

    *   **With Secure Sandbox (Recommended on Windows):**
        1.  Double-click the `run_app_as_jea_user.bat` file in the project root.
        2.  A terminal will prompt you for the password of the `JeaToolUser` you created during setup.
        3.  After entering the password, the Waitress server will start in a hidden background process and the launcher window will close.
        4.  The application will be available at `http://127.0.0.1:5000/`.
        5.  **To stop the server**, open Task Manager (`Ctrl+Shift+Esc`), go to the "Details" tab, find the `python.exe` process running as `JeaToolUser`, and click "End task".

    *   **Without Sandbox (Legacy / Non-Windows):**
        > **Note:** The secure file system tools will **not** be available in this mode.
        For development, use the standard Flask command (in a separate terminal):
        ```bash
        flask run --debug
        ```
        For a more production-like environment, use the included Waitress runner:
        ```bash
        python run_waitress.py
        ```
        The application will be available at `http://127.0.0.1:8080`.

## Usage Guide

*   **Creating a Chat:** Select a provider from the dropdown menu and click "+ New Chat".
*   **Switching Chats:** Click on the tabs at the top to switch between active chat sessions.
*   **Editing Context:** Click the "Edit Context" button to modify or delete any message in the current chat history. Click "Save Context" to apply changes.
*   **Managing Tools:** Click the "Tools" button (wrench icon) to open the tool management panel for the current session.

### Tool System Workflow

The application features a powerful system for adding custom tools that the AI can use. This includes built-in tools like the `jailed_file_manager.py` for safe file operations.

1.  **Create a Tool:** Add a new Python file (e.g., `my_calculator.py`) inside the `my_tools/` directory.
2.  **Write a Function:** Define a standard Python function within that file. The function **must** have a docstring and type hints for its arguments, as this information is used by the AI.
    ```python
    # my_tools/my_calculator.py
    def add(a: int, b: int) -> int:
        """Adds two integers together."""
        return a + b
    ```
3.  **Register the Tool:**
    *   In the web UI, open the "Tools" panel for a chat instance.
    *   Click "Discover Tools" to find your new module (`my_tools/my_calculator.py`).
    *   Click "Scan Module" to see the `add` function and its documentation.
    *   Select the `add` function and click "Register Selected Tools".
4.  **Use the Tool:** The AI model can now call this tool when appropriate during a chat conversation. The application will execute the function with the arguments provided by the model and return the result.