# Multi-Instance AI Digital Office Interface

A sophisticated, web-based platform designed to manage multiple, simultaneous AI agent sessions within an extensible "Digital Office" framework. Architected with Python, Flask, and HTMX, it enables high-fidelity collaboration between specialized AI personas (Project Managers, Developers, Researchers) using a shared Project Journal and advanced tool integration.

The application is provider-agnostic, seamlessly connecting to Google Gemini, Ollama, and OpenRouter to power an autonomous agent team.

## Key Architecture

### 1. The Autonomous Agent Task Force System (AATFS)
The core of the interface is the **AATFS**, a "headless office" philosophy where specialized agents collaborate on complex projects.
-   **Persona System**: Over 20+ specialized AI personas (Architect, PM, Developer, Security Expert) with unique system prompts and toolsets.
-   **Shared Project Journal**: A centralized source of truth where agents store research, drafts, and technical specs.
-   **Diagnostic Loop**: An autonomous error-correction workflow where the Project Manager triages Auditor feedback to re-delegate fixes.

### 2. Secure, Cross-Platform Tooling
A powerful suite of Python-native tools designed for safe project manipulation:
-   **Jailed File Manager**: OS-agnostic file operations (create, delete, move) with strict path validation to confine agents to the workspace.
-   **Codebase Explorer**: Built-in SQLite database parser (`build_code_db.py`) and vector search (`tool_vdb`) for structural and semantic code analysis.
-   **Multi-Language Analysis**: Specialized tools for linting, security scanning, and structural analysis of Python, JS, HTML, and CSS.

### 3. Dynamic HTMX Frontend
A responsive, single-page experience without the overhead of heavy JavaScript frameworks:
-   **Multi-Instance Tabs**: Manage multiple, isolated chat sessions simultaneously.
-   **Live Context Editor**: View, edit, or remove any message in the chat history for granular context control.
-   **Theming Engine**: Instant switching between themes (e.g., Hotseat, 80s Theme, Zen Gardens).

## Tech Stack

-   **Backend**: Python 3.10+, Flask, Waitress
-   **Frontend**: HTML5, Tailwind CSS, HTMX, Hyperscript
-   **AI Providers**: `google-genai`, `ollama`, `openrouter`
-   **Code Analysis**: `beautifulsoup4`, `lxml`, `esprima`
-   **Specialized Tooling**: `ruff`, `bandit`, `safety`, `gitpython`, `tavily-python`

## Project Structure

```
.
├── api_clients/        # Provider-agnostic AI API connectors.
├── my_tools/           # Extensible Python tool library for AI agents.
│   ├── README(my_tools)/ # Detailed documentation for each tool.
│   └── jailed_file_manager.py # OS-agnostic secure file operations.
├── personas/           # JSON-defined AI agent identities and toolsets.
├── static/             # Compiled Tailwind CSS and JavaScript assets.
├── templates/          # Jinja2 HTML templates for the HTMX UI.
├── tool_vdb/           # Vector database for semantic tool discovery.
├── app.py              # Main Flask application and server logic.
├── chat_instance.py    # Isolated state management for each chat session.
├── project_config.json # Global workspace and provider configuration.
└── AATFS_GUIDE.md      # Deep-dive into the Autonomous Agent workflow.
```

## Setup and Installation

### 1. Install Dependencies
```bash
# Python (Virtual Environment recommended)
pip install -r requirements.txt

# Node.js (For Tailwind CSS)
npm install
npm run build:css
```

### 2. Configure Environment
Create a `.env` file in the root directory:
```ini
FLASK_SECRET_KEY='your_secret_key'
GOOGLE_API_KEY='your_api_key'
TAVILY_API_KEY='your_search_key'
```

### 3. Launch the Office
```bash
# Production Mode (Waitress)
python run_waitress.py

# Development Mode (Flask)
flask run --debug
```
Access the application at `http://127.0.0.1:8080`.

## Documentation

-   **[AATFS_GUIDE.md](AATFS_GUIDE.md)**: Understanding the Digital Office and Diagnostic Loop protocols.
-   **[my_tools/README(my_tools)/](my_tools/README(my_tools)/)**: Detailed documentation for the agent tool library.
-   **[personas/persona_guide.md](personas/persona_guide.md)**: How to create and manage specialized AI agents.
-   **[setup.md](setup.md)**: Detailed cross-platform installation instructions.
