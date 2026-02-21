# Setup Guide

This guide covers the installation and configuration of the Multi-Instance AI Chat Interface. The application is designed to be cross-platform and runs on Windows, Linux, and macOS.

### Prerequisites

*   **Python 3.10** or higher.
*   **Node.js** and **npm** (for building the frontend styles).
*   **Git**.

---

## Part 1: General Setup

These steps are required for all users.

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd <repo-directory>
```

### 2. Create a Virtual Environment

It is highly recommended to run the application in an isolated environment.

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```powershell
python -m venv venv
venv\Scripts\activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Frontend Dependencies & Build CSS

This project uses Tailwind CSS, which needs to be compiled.

```bash
npm install
npm run build:css
```
*(Note: You can use `npm run watch` during development to auto-rebuild CSS on changes.)*

### 5. Configure Environment Variables

Create a file named `.env` in the root directory of the project. This file will hold your API keys and configuration.

```ini
# Security
FLASK_SECRET_KEY='change_this_to_a_random_string'

# AI Providers (Fill in the ones you want to use)
GOOGLE_API_KEY='your_google_api_key'
OPENROUTER_API_KEY='your_openrouter_key'
OLLAMA_API_KEY='your_ollama_key' # Optional if running locally
TAVILY_API_KEY='your_tavily_key'

# Project Context Configuration
# This is the path to the directory you want the AI to analyze and edit.
# On Windows, use double backslashes (\\) or forward slashes (/).
CODEBASE_DB_PATH='/absolute/path/to/your/project/workspace'
```

---

## Part 2: Running the Application

### For Production (Recommended)
Use the included Waitress server for a robust, multi-threaded experience.

```bash
python run_waitress.py
```
Access the app at: `http://127.0.0.1:8080`

### For Development
Use the Flask development server for debugging and auto-reloading.

```bash
flask run --debug
```
Access the app at: `http://127.0.0.1:5000`

---

## Part 3: Optional Legacy Windows Sandbox

> **Note:** The core file management tools (`create_file`, `delete_file`, etc.) have been updated to be OS-agnostic and secure by default. You **do not** need this sandbox setup for normal operation.

This section is only relevant if you are on Windows and explicitly wish to use the legacy `jailed_shell_tool.py` which relies on PowerShell JEA (Just Enough Administration) to run arbitrary shell commands.

### 1. Run the Sandbox Setup Script
*Requires Administrator PowerShell.*

```powershell
.\Setup-Simple-Sandbox.ps1
```
Follow the prompts to create the `JeaToolUser` and password.

### 2. Grant Permissions
*Requires Administrator PowerShell.*

```powershell
.\Fix-Project-Permissions.ps1
```

### 3. Launching with JEA
To run the application inside this sandbox, do not use the standard python command. Instead:

1.  Double-click `run_app_as_jea_user.bat`.
2.  Enter the `JeaToolUser` password when prompted.
3.  The server will start in the background. Stop it via Windows Task Manager.