# Multi-Instance AI Chat Interface

This project is a sophisticated, web-based chat application designed to manage multiple, simultaneous chat sessions with a variety of AI providers. It features a dynamic, tabbed interface built with HTMX for a seamless user experience, a powerful and extensible tool integration system, and a customizable frontend with multiple themes.

The application is architected to be provider-agnostic, allowing users to connect to different AI APIs like Google Gemini, Ollama, and OpenRouter within the same session manager.

### From Frustration to Features: The Story of This App

This project didn't start with a grand vision. It started with a practical problem: I wanted to help my fiancée study for her NCLEX nursing exam. My initial idea was simple: use an AI to generate practice questions.

I quickly hit a wall. The AI models, for all their power, struggled with the multi-step reasoning and domain-specific accuracy required for medical training. I couldn't in good conscience build a tool that might give prospective nurses faulty information. That initial project was a failure.

But in the process, I had built a simple, Python-only chat interface to prototype with. As I spent late nights testing prompts, I ran headfirst into a new, more solvable problem: managing the conversation context was a nightmare. If the AI went off track, correcting it was tedious. The pure Python format had run its course.

That frustration was the spark for *this* application.

From that point on, the project grew organically. Every major feature you see below wasn't part of a master plan, but was born from a real, practical need I encountered while using the tool myself.

### The Problems and The Solutions

#### 1. The Problem: The AI Has a Mind of Its Own (And a Bad Memory)
A conversation would be going great, and then one wrong turn would derail the entire context, forcing a restart.

**The Solution: Full Context Control**
A powerful context editor allows you to view, edit, or delete any message—user or AI—within a chat's history. This gives you fine-grained control to prune bad branches of conversation and steer the AI back on course.

#### 2. The Problem: Juggling Different Conversations and Ideas
I was constantly experimenting with different prompts, system instructions, and even different AIs. A single chat window was chaos.

**The Solution: Multi-Instance Management**
A clean, tabbed interface to manage multiple, simultaneous chat sessions. Each session maintains its own isolated context, configuration, and toolset, keeping your work organized.

#### 3. The Problem: No Single AI is Perfect (And I Don't Like Being Locked In)
Some models are great at creative writing, others excel at code generation. I wanted the freedom to use the best tool for the job without swapping applications.

**The Solution: A Provider-Agnostic Core**
The application is architected to be provider-agnostic. It ships with clients for Google, Ollama, and OpenRouter, and the modular design in `api_clients/` makes it easy to add others.

#### 4. The Problem: The AI is Trapped in its Digital Box
An AI can't browse the web, run code, or interact with local files. I needed it to *do things*.

**The Solution: A Dynamic, Discoverable Tool System**
The app's superpower. You write simple Python functions in the `my_tools/` directory, and the AI can discover and use them. The UI lets you inspect available tools and register them to specific chat sessions on the fly.

#### 5. The Problem: I Needed a Web UI Without the JavaScript Headaches
The command line was too limiting, but I didn't want to get bogged down in a heavy frontend framework.

**The Solution: A Server-First Frontend with HTMX**
The entire frontend is built using HTMX, creating a responsive, single-page application feel without the complexity. The Flask server renders HTML fragments and swaps them into the page, keeping the frontend simple and fast.

---

### Other Key Features
*   **Theming Engine:** Switch between multiple themes, including light and dark modes.
*   **Markdown & Code Formatting:** Renders Markdown and provides syntax highlighting for over 300 languages, with a "copy to clipboard" button.
*   **File Uploads:** Attach files to messages for the AI to use.

### Tech Stack
*   **Backend:** Python 3, Flask, Waitress (as a production-ready WSGI server)
*   **Frontend:** HTML5, Tailwind CSS, JavaScript, HTMX, htmx-ext (for SSE), HyperScript
*   **API Clients:** google-genai, requests
*   **Core Python Dependencies:**
    *   `flask`, `waitress`
    *   `python-dotenv`
    *   `requests`, `requests-cache`, `retry-requests`
    *   `google-generativeai`, `openai`
    *   `markdown`, `pymdownx-superfences`, `bleach` (For Markdown rendering)
    *   `bs4` (Beautiful Soup) & `esprima` (For HTML/JS parsing in tools)
    *   `geopy`, `pandas`, `openmeteo-requests` (For the weather tool)

### Project Structure
```
.
├── api_clients/        # Handles connections to external AI providers
├── chat_logs/          # Stores chat history logs for persistence
├── chat_sessions/      # Saved session data (JSON) and uploaded files
├── my_tools/           # Directory for custom, user-defined Python tools
├── static/             # Compiled CSS, JavaScript, and other assets
├── templates/          # Flask HTML templates (Jinja2), including partials for HTMX
├── tool_vdb/           # Vector database for semantic tool searching
├── .env                # Environment variables (API keys, secrets)
├── app.py              # Main Flask application: routing and core logic
├── chat_instance.py    # ChatInstance class representing a single session state
├── chat_manager.py     # Manages all active chat instances
├── tool_registry.py    # Discovers and loads tools from my_tools/
├── run_waitress.py     # Production-ready entry point using Waitress
└── utils.py            # Utility functions
```

### Frontend Architecture
The frontend uses a modern, server-driven approach with **HTMX**, which makes AJAX requests and swaps sections of the page with HTML rendered by the Flask server. This keeps the frontend logic simple and located in the HTML templates. **Tailwind CSS** is used for the utility-first CSS workflow. The **Theming System** (`theme_manager.js`) dynamically loads different CSS files to allow for instant theme switching.

### Setup and Installation
1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/pestilence-and-war/multi-instance-chat-interface.git
    cd multi-instance-chat-interface
    ```

2.  **Create a Virtual Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Frontend Dependencies:**
    ```bash
    npm install
    ```

5.  **Configure Environment Variables:** Create a `.env` file in the project root and add your API keys. The `CODEBASE_DB_PATH` is required for the built-in code analysis tools.
    ```env
    FLASK_SECRET_KEY='a_very_secret_key'
    GOOGLE_API_KEY='your_google_api_key_here'
    OPENROUTER_API_KEY='your_key_here'
    OLLAMA_API_KEY='your_ollama_key_here' # Can be set to None
    TAVILY_API_KEY='your_tavily_key_here'

    # Required for code analysis tools
    CODEBASE_DB_PATH='full_path_to_project_context.db'
    ```

6.  **Build CSS:**
    ```bash
    # For a one-time build
    npm run build:css

    # To watch for changes and rebuild automatically
    npm run watch:css
    ```

7.  **Run the Application:**
    *   For development (in a separate terminal): `flask run --debug`
    *   For a production-like environment: `python run_waitress.py`

The application will be available at `http://127.0.0.1:8080`.

### Usage Guide
*   **Creating a Chat:** Select a provider from the dropdown and click `+ New Chat`.
*   **Switching Chats:** Click on the tabs at the top.
*   **Editing Context:** Click the "Edit Context" button to modify history.
*   **Managing Tools:** Click the "Tools" button (wrench icon) to manage tools for the current session.

### Tool System Workflow
1.  **Create a Tool:** Add a new Python file (e.g., `my_calculator.py`) inside the `my_tools/` directory.
2.  **Write a Function:** Define a standard Python function within that file. It **must** have a docstring and type hints.
    ```python
    # my_tools/my_calculator.py
    def add(a: int, b: int) -> int:
        """Adds two integers together."""
        return a + b
    ```
3.  **Register the Tool:** In the UI's "Tools" panel, "Discover Tools" to find your new module, "Scan Module" to see the function, select it, and "Register Selected Tools".
4.  **Use the Tool:** The AI model can now call this tool during a chat. The application will execute it and return the result.