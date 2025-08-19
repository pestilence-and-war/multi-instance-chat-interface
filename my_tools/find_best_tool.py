# find_best_tool.py
# This is the "Proxy" tool. It's safe to scan and simple to load.

# We need to add the parent directory to the path so we can import from 'tool_vdb'
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now we can import the REAL logic from its separate, safe location
from tool_vdb.query_tools import find_similar_tools

def search_for_tool(user_query: str) -> list:
    """
    Finds the most relevant tool to answer a user's request.

    Use this function when you need to find a capability to perform a specific task
    like reading a file, running code, or fetching web content. The input should
    be a short, direct command or description of the needed action.

    @param user_query (str): A concise description of the task to perform. Required.

    Returns:
        list: A list of the most relevant tools' specifications, ranked by similarity.
    """
    # This proxy function's only job is to call the real engine.
    return find_similar_tools(user_query)
