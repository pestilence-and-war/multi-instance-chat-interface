# Multi-Instance AI Chat Interface

This project is a sophisticated, web-based chat application designed to manage multiple, simultaneous chat sessions with a variety of AI providers. It features a dynamic, tabbed interface built with HTMX for a seamless user experience, a powerful and extensible tool integration system, and a customizable frontend with multiple themes.

The application is architected to be provider-agnostic, allowing users to connect to different AI APIs like Google Gemini, Ollama, and OpenRouter within the same session manager.

## Key Features

*   **Multi-Instance Management:** Open, close, rename, and manage multiple chat sessions in a clean, tabbed interface. Each session maintains its own isolated context, configuration, and toolset.
*   **Provider Agnostic:** Ships with clients for Google, Ollama, and OpenRouter. The modular design in `api_clients/` makes it straightforward to extend support to other AI API providers.
*   **Secure Python-Native File Tools:** A suite of file system tools (create, delete, move) that are **OS-agnostic** and secure by design. They utilize strict path validation logic within Python to ensure operations are confined to the active project workspace (`CODEBASE_DB_PATH`), preventing access to system files on Linux, macOS, and Windows without requiring complex OS-level sandboxes.
*   **Project Root Switching:** Change the active target workspace directory dynamically from the UI without restarting the application. This allows you to seamless switch between working on different projects.
*   **Database Builder:** Initialize or refresh the `project_context.db` knowledge graph directly from the UI. This powers the code analysis tools and ensures the AI has the latest view of your project structure.
*   **Dynamic Tool System:**
    *   **Discovery:** Automatically discovers Python tool modules from the `my_tools/` directory.
    *   **Inspection:** Scans modules to view available functions, their signatures, and docstrings directly in the UI.
    *   **Registration:** Register or unregister specific functions for use by a chat instance on the fly.
*   **Full Context Control:** A powerful context editor allows users to view, edit, or delete any message within a chat's history.
*   **Dynamic UI with HTMX:** The entire frontend is built using HTMX, creating a responsive, single-page application feel without the complexity of a large JavaScript framework.
*   **Theming Engine:** Switch between multiple themes (`hotseat`, `80s_theme`, `zen_gardens`) instantly.
*   **Markdown & Code Formatting:** Renders Markdown and provides syntax highlighting in real-time as the AI streams its response. Includes a reliable "copy to clipboard" button for code blocks.
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
    *   `markdown`, `pymdownx-superfences`, `bleach`
    *   `bs4` (Beautiful Soup) & `esprima` (For HTML/JS parsing)
    *   `geopy`, `pandas`, `openmeteo-requests`

## Project Structure

```
.
├── api_clients/        # Handles connections to external AI providers.
├── chat_logs/          # Stores chat history logs.
├── chat_sessions/      # Saved session data (JSON).
├── my_tools/           # Directory for custom, user-defined Python tools.
│   ├── jailed_file_manager.py  # Cross-platform secure file system tools.
│   └── SafeExecutor.ps1      # (Legacy/Windows-Only) PowerShell security gate.
├── static/             # Compiled CSS, JavaScript, and assets.
├── templates/          # Flask HTML templates (Jinja2).
├── tool_vdb/           # Vector database for semantic tool searching.
├── .env                # Environment variables (API keys, secrets).
├── app.py              # Main Flask application.
├── chat_instance.py    # Represents a single chat session state.
├── chat_manager.py     # Manages all active chat instances.
├── tool_management.py  # Discovers and loads tools dynamically.
├── run_waitress.py     # Production entry point.
├── utils.py            # Utility functions.
├── run_app_as_jea_user.bat # (Legacy/Windows-Only) Secure sandbox launcher.
└── SETUP.md            # Setup guide.
```

## Setup and Installation

### System Requirements
*   **Cross-Platform:** Works on Windows, Linux, and macOS.
*   Python 3.10+.

### Installation Steps

1.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Create a Virtual Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Frontend Dependencies:**
    ```bash
    npm install
    ```

5.  **Configure Environment Variables:**
    Create a `.env` file in the project root.
    ```
    FLASK_SECRET_KEY='a_very_secret_key'
    GOOGLE_API_KEY='your_google_api_key_here'
    OPENROUTER_API_KEY='your_key_here'
    # Required for code analysis tools
    CODEBASE_DB_PATH='/absolute/path/to/your/project'
    ```

6.  **Build CSS:**
    ```bash
    npm run build:css
    ```

7.  **Run the Application:**
    
    For development:
    ```bash
    flask run --debug
    ```
    
    For production (recommended):
    ```bash
    python run_waitress.py
    ```
    The application will be available at `http://127.0.0.1:8080` (Waitress) or `http://127.0.0.1:5000` (Flask).

### Optional: Legacy Windows Sandbox
If you are on Windows and explicitly require the deprecated JEA (Just Enough Administration) sandbox for shell execution, refer to `SETUP.md` for the original `run_app_as_jea_user.bat` workflow. Note that the core file manager tools no longer require this.

## Usage Guide

*   **Project Context:** Use the "Project Root" input at the top of the page to point the tools to the directory you want to work on. Click "Set" to confirm.
*   **Build Database:** Click "Build DB" to scan the selected project and create the searchable context database. This is required for tools like "Project Explorer" or "Search Code".
*   **Creating a Chat:** Select a provider from the dropdown and click "+ New Chat".
*   **Tool System:** Use the "Tools" (wrench icon) panel to discover and register Python functions from `my_tools` as usable tools for your chat session.