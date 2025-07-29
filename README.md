# Multi-Instance Chat Interface

This project is a web-based chat application that allows users to manage multiple, simultaneous chat sessions with various AI providers. It features a dynamic, tabbed interface for easy switching between conversations, a robust tool integration system, and a customizable theme.

## Key Features

*   **Multi-Instance Management:** Open and manage multiple chat sessions in a tabbed interface.
*   **Provider Agnostic:** Connect to different AI API providers (e.g., Google Gemini, OpenAI, etc.).
*   **Tool Integration:** Dynamically discover, register, and use custom tools within chat sessions.
*   **Dynamic UI:** Built with HTMX for a seamless, single-page application feel without complex JavaScript frameworks.
*   **Theming:** Switch between light and dark themes.
*   **Markdown & Code Formatting:** Renders Markdown and provides syntax highlighting with a "copy" button for code blocks.
*   **File Uploads:** Attach files to your messages.
*   **Context Editing:** Full control to edit and save the chat history of any session.

## Tech Stack

*   **Backend:** Python 3, Flask
*   **Frontend:** HTML5, Tailwind CSS, JavaScript, HTMX
*   **API Clients:** `google-genai` (and can be extended to others)
*   **Dependencies:** `requests`, `python-dotenv`, `markdown`, `Pygments`, `bleach`

## Project Structure

.
├── api_clients/ # Handles connections to external AI providers
├── chat_logs/ # Stores chat history logs
├── chat_sessions/ # Saved session data and uploaded files
├── my_tools/ # Directory for custom, user-defined Python tools
├── static/
│ ├── css/ # CSS files, including Tailwind output
│ └── js/ # JavaScript files
├── templates/ # Flask HTML templates (Jinja2)
├── .env # Environment variables (API keys, secrets)
├── app.py # Main Flask application entry point
├── chat_instance.py # Defines the ChatInstance class
├── chat_manager.py # Manages all active chat instances
├── tool_registry.py # Discovers and loads tools from the my_tools directory
└── requrements.txt # Python package dependencies
## Setup and Installation

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
    ```bash
    pip install -r requrements.txt
    ```

4.  **Install Frontend Dependencies:**
    This project uses Tailwind CSS via a Node.js script.
    ```bash
    npm install
    ```

5.  **Configure Environment Variables:**
    Create a `.env` file in the project root and add your API keys:
    ```
    FLASK_SECRET_KEY='a_very_secret_key'
    GOOGLE_API_KEY='your_google_api_key_here'
    OPENROUTER_API_KEY='your_key_here'
    Ollama_API_KEY=None
    TAVILY_API_KEY='your_tavily_key_here'

    CODEBASE_DB_PATH='full_path_to_"project_contex.db"'
    #for read/write tools using the db created from the 'build_code_db.py' script
    # Add other provider API keys as needed
    ```

6.  **Build CSS:**
    Compile the Tailwind CSS. The `--watch` flag will automatically rebuild the CSS when you make changes to the input files.
    ```bash
    npm run build:css
    ```

7.  **Run the Application:**
    Open a new terminal, activate the virtual environment, and run the Flask app (e.g., waitress by using run_waitress.py file included).
    ```bash
    flask run --debug
    ```
    The application will be available at `http://127.0.0.1:5000`.

## Usage

*   **Creating a Chat:** Select a provider from the dropdown and click "+ New Chat".
*   **Switching Chats:** Click on the tabs at the top to switch between active chat sessions.
*   **Using Tools:** The system can be configured to use tools. See the "Tool System" section below.
*   **Editing Context:** Click the "Edit Context" button to modify or delete messages in the current chat history.

## Tool System

The application features a powerful system for adding custom tools that the AI can use.

1.  **Create a Tool:** Add a new Python file (e.g., `my_calculator.py`) inside the `my_tools/` directory.
2.  **Write a Function:** Define a standard Python function within that file. The function should have a clear purpose and type hints for its arguments.
    ```python
    # my_tools/my_calculator.py
    def add(a: int, b: int) -> int:
        """Adds two integers together."""
        return a + b
    ```
3.  **Register the Tool:**
    *   In the web UI, go to the "Tools" section of a chat instance.
    *   Click "Discover Tools" to find your new module (`my_tools/my_calculator.py`).
    *   Scan the module to see the `add` function.
    *   Select the `add` function and click "Register Selected Tools".
4.  **Use the Tool:** The AI model can now call this tool when appropriate during a chat conversation. The application will execute the function and return the result to the model.
