# Changelog

## [Unreleased] - 2026-02-20

### Added
- **Dynamic Project Root Switching:** Users can now change the target project directory (workspace) directly from the UI without restarting the application. The application state (chat history) is preserved.
- **Database Builder UI:** Added a "Build DB" button to the main interface, allowing users to generate or refresh the `project_context.db` for the active workspace on demand.
- **Real-Time Markdown Streaming:** Chat responses now render Markdown (including code blocks and syntax highlighting) in real-time as they stream, rather than waiting for completion.
- **Smart Auto-Scrolling:** The chat window now only auto-scrolls if the user is already at the bottom of the feed, preventing scroll-jumping while reading history.

### Changed
- **Cross-Platform File Management:** Refactored `my_tools/jailed_file_manager.py` to use native Python `os` and `shutil` libraries instead of PowerShell/JEA. This makes file operations (create, delete, move) compatible with Linux and macOS while maintaining path security.
- **Tool Discovery & Registration:**
    - Fixed a bug where registered tools were not visible in the "Manage Tools" UI.
    - Updated `find_similar_tools` docstrings to ensure parameters are correctly parsed and exposed to the LLM.
    - Suppressed benign warnings for tools with no parameters (e.g., `get_project_summary`).
- **Copy Button Logic:** Fixed a race condition in the "Copy" button that caused the "Copied!" feedback to flicker or disappear prematurely.
- **Application Structure:** Decoupled the application's internal runtime directory (where `personas` and `app.py` live) from the user's target workspace. The application no longer changes its working directory (`os.chdir`), improving stability.

### Removed
- **JEA Dependency for File Ops:** `SafeExecutor.ps1` is no longer used for file management tasks, reducing the dependency on Windows-specific security features for basic operations.

### Security
- **Path Validation:** Implemented strict Python-level path validation (`_is_path_safe`) in `jailed_file_manager.py` to ensure all file operations are confined to the `CODEBASE_DB_PATH`.
