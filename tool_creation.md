# Engineering New Agent Tools (v2)

Agent tools are the hands and eyes of the Digital Office. Follow these standards to ensure tools are reliable, safe, and context-aware.

## 1. Tool Structure
All tools must be standard Python functions. The system uses docstrings to generate the JSON schemas for the LLM.

```python
def my_custom_tool(argument_a: str, instance=None) -> str:
    """
    Description of what the tool does for the agent.
    
    @param argument_a (string): Explanation of the argument.
    @param instance (object): INTERNAL. Provides access to the calling agent's state.
    """
    # implementation...
    return json.dumps({"status": "success", "result": "..."})
```

## 2. Advanced Features

### Context Inheritance (`instance`)
If a tool function includes an `instance` argument, the system will automatically inject the calling `ChatInstance` object. This allows your tool to:
-   **Inherit Credentials**: Access the agent's active provider/model (essential for vision or delegation).
-   **Access State**: Read `instance.name`, `instance.chat_history`, or `instance._background_processes`.

### Background Services
Tools that start long-running processes (like servers) must use `subprocess.Popen` and register the PID in `instance._background_processes`.
-   **Never block**: Tools must return a result within 60 seconds.
-   **Windows Safety**: Always use `taskkill /F /T` for cleanup to ensure child process trees are removed.

## 3. Formatting & Returns
-   **Return JSON**: Always return a JSON string.
-   **No Hallucination**: If a tool fails, return a JSON error object with a helpful message. Do not print to the console; return the data so the agent can read it.
-   **Proof-of-Life**: For execution tools, always include the `stdout` and `stderr` in the return object to satisfy the **Anti-Fraud Mandate**.

## 4. Registration
1.  Place your script in `my_tools/`.
2.  Open the **Tools** tab in the UI.
3.  Click **"Discover Tools"** -> **"Scan Module"**.
4.  Select your functions and click **"Register Selected Tools"**.
