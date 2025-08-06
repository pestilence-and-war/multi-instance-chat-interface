# Project Sandbox Setup Guide

This guide explains how to set up the secure sandboxed environment required to use the advanced file system tools in this project. This setup creates a special, low-privilege user account and a "jailed" directory, allowing an LLM to safely create, modify, and delete files within a designated project workspace without any risk to your main system files.

### Prerequisites

*   Windows 10 or Windows 11.
*   Administrator access on your machine to run the setup scripts.
*   PowerShell 5.1 or later (this is standard on modern Windows).

---

## Part 1: One-Time Environment Setup

This part only needs to be performed once on your machine. It creates the permanent user and sandbox directory.

### Step 1: Run the Sandbox Setup Script

This script creates the dedicated user (`JeaToolUser`) and the sandboxed directory (`C:\SandboxedWorkspaces`) and applies the strict permissions that prevent the user from accessing anything outside that directory.

1.  Navigate to the root directory of this project in a PowerShell terminal.
2.  You must run this script as an Administrator. Right-click the PowerShell icon and select "Run as Administrator," then navigate to the project directory.
3.  Run the setup script:
    ```powershell
    .\Setup-Simple-Sandbox.ps1
    ```
4.  You will be prompted to enter a new, strong password for the `JeaToolUser` account. Choose a secure password and **remember it**. This is the password you will use to launch the application.

### Step 2: Grant Project Permissions

The sandboxed user (`JeaToolUser`) needs permission to read your application's files, specifically the Python interpreter inside your virtual environment (`venv`). This script grants the necessary "Read & Execute" permissions.

1.  Ensure you are still in an **Administrator PowerShell** window in the project's root directory.
2.  Run the permissions script:
    ```powershell
    .\Fix-Project-Permissions.ps1
    ```
3.  This will apply the permissions recursively to your project folder. The script will tell you when it's complete.

The environment is now fully configured.

---

## Part 2: Running the Application

With the sandbox configured, you will now launch the application using a special launcher script. This is the new, permanent way to run the app.

**You will no longer run `python app.py` or `python run_waitress.py` directly unless not using the tools that require sandboxing.**

### How to Launch

1.  In the project's root directory, find the file `run_app_as_jea_user.bat`.
2.  **Double-click `run_app_as_jea_user.bat`**.
3.  A terminal window will appear and Windows will securely prompt you to enter the password for the `JeaToolUser`.
4.  Enter the password you created in Part 1, Step 1.
5.  The Waitress server will start in a **separate, hidden background process**. The launcher window will close itself after a few seconds.

Your application is now running. You can access it in your web browser at `http://127.0.0.1:5000/`.

### How to Stop the Server

Because the server is running as another user in the background, you cannot stop it with `Ctrl+C`. You must use the Windows Task Manager until I figure out a streamlined solution.

1.  Open Task Manager (`Ctrl+Shift+Esc`).
2.  Go to the **"Details"** tab.
3.  Sort by "User name" and find the `python.exe` process that is running as `JeaToolUser`.
4.  Select that process and click **"End task"**.

---

## How It All Works: The Security Model

This setup provides a robust, multi-layer security model:

1.  **The Launcher (`run_app_as_jea_user.bat`)**: This is the "Ignition Key." It uses the trusted `runas` command to start the entire Python application process as our low-privilege `JeaToolUser`.
2.  **User Isolation (`JeaToolUser`)**: This is our "Untrusted Intern." This user account, by design, has no rights or permissions anywhere on your system *except* for the two places we explicitly granted them: your project folder (to run the app) and the sandbox (to do its work).
3.  **Directory Jailing (`C:\SandboxedWorkspaces`)**: This is the "Designated Workbench." It is the only place where the `JeaToolUser` has permission to write, modify, or delete files. Any attempt to operate outside this directory (e.g., in `C:\Windows`) will be blocked by the operating system.
4.  **Command Whitelisting (`SafeExecutor.ps1`)**: This is the "Rule Book." Even though the user is jailed, this script provides a final layer of protection by checking every command against a pre-approved list (`New-Item`, `Remove-Item`, etc.). This prevents the execution of more dangerous commands like `Stop-Process` or `Invoke-WebRequest`, even within the sandbox.