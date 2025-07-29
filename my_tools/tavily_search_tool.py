# my_tools/tavily_search_tool.py
import requests
import json
import os
import traceback
from typing import List, Optional, Union, Dict, Any


def tavily_search(
    query: str,
    search_depth: str = "basic",
    include_answer: bool = True,
    max_results: int = 3,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    topic: str = "general"
) -> str:
    """
    Performs a search using the Tavily Search API and returns structured results.

    This tool is optimized for AI agents, providing concise and relevant information.
    It can search various topics, control the depth of the search, and optionally
    include a direct answer to the query if found.

    @param query (string): The search query. This is a required parameter.
    @param search_depth (string): The depth of the search. 'basic' for a quick search, or 'advanced' for a more comprehensive search that may take longer and consume more credits. Optional. Default: 'basic'. enum:basic,advanced
    @param include_answer (boolean): Whether to include a direct answer to the query in the search results, if available. Optional. Default: True.
    @param max_results (integer): The maximum number of search results to return. Optional. Default: 3. (Tavily's max is typically around 5-7 for basic and 10 for advanced, but LLMs often prefer fewer, more focused results).
    @param include_domains (List[string]): A list of specific domains to search within (e.g., ["wikipedia.org", "bbc.com"]). Optional. Default: None (search all domains).
    @param exclude_domains (List[string]): A list of specific domains to exclude from the search (e.g., ["pinterest.com"]). Optional. Default: None (no domains excluded).
    @param topic (string): The topic of the search, can be 'general', 'news', 'research_paper', 'code', etc. This helps Tavily focus the search. Optional. Default: 'general'. enum:general,news,finance,research_paper,code,sports
    """
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    if not TAVILY_API_KEY:
        return json.dumps({
            "error": "Tavily API key (TAVILY_API_KEY) is not configured in the environment.",
            "status": "error_misconfigured"
        })

    print(f"--- Tool: tavily_search called with query: '{query}', search_depth: '{search_depth}', include_answer: {include_answer}, max_results: {max_results} ---")

    if not TAVILY_API_KEY:
        return json.dumps({
            "error": "Tavily API key (TAVILY_API_KEY) is not configured in the environment.",
            "status": "error_misconfigured"
        })

    if not query or not isinstance(query, str):
        return json.dumps({"error": "Invalid or empty search query provided.", "status": "error_invalid_input"})

    url = "https://api.tavily.com/search"

    payload: Dict[str, Any] = {
        "api_key": TAVILY_API_KEY, # Tavily also accepts API key in payload
        "query": query,
        "search_depth": search_depth,
        "include_answer": include_answer,
        "max_results": max(1, min(int(max_results), 7 if search_depth == "basic" else 10)), # Adhere to reasonable limits
        "topic": topic,
        # Parameters that are False by default or handled by None checks
        "include_raw_content": False,
        "include_images": False,
        "include_image_descriptions": False,
    }

    # Add optional list parameters if they are provided and not empty
    if include_domains and isinstance(include_domains, list) and len(include_domains) > 0:
        payload["include_domains"] = include_domains
    if exclude_domains and isinstance(exclude_domains, list) and len(exclude_domains) > 0:
        payload["exclude_domains"] = exclude_domains
    
    # Example of how you might handle other parameters from your initial snippet if needed by LLM:
    # "chunks_per_source": 3, # Default from your snippet, usually not needed for LLM to set
    # "time_range": None, # Can be complex for LLM, better to use 'days'
    # "days": 7, # If you want to allow LLM to set recency

    headers = {
        # "Authorization": f"Bearer {TAVILY_API_KEY}", # Tavily docs show API key in payload, but bearer token is also an option
        "Content-Type": "application/json"
    }
    # If you prefer Bearer token, uncomment above and remove api_key from payload.
    # For simplicity, putting api_key in payload is common.

    print(f"Tavily API Request Payload: {json.dumps(payload)}")

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=20) # Tavily can sometimes take a moment for advanced searches
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        search_data = response.json()


        # For simplicity now, return the direct response from Tavily, adding our status
        search_data["status"] = "success"
        return json.dumps(search_data)


    except requests.exceptions.HTTPError as http_err:
        error_content = http_err.response.text
        try:
            # Tavily often returns JSON errors
            error_json = http_err.response.json()
            error_message = f"Tavily API HTTP error: {http_err.response.status_code} - {error_json.get('error', error_content)}"
        except json.JSONDecodeError:
            error_message = f"Tavily API HTTP error: {http_err.response.status_code} - {error_content}"
        print(error_message)
        return json.dumps({"error": error_message, "status": "error_api_http"})
    except requests.exceptions.Timeout:
        error_message = "Request to Tavily API timed out."
        print(error_message)
        return json.dumps({"error": error_message, "status": "error_api_timeout"})
    except requests.exceptions.RequestException as req_err:
        error_message = f"Request error occurred with Tavily API: {req_err}"
        print(error_message)
        return json.dumps({"error": error_message, "status": "error_api_request"})
    except Exception as e:
        print(f"Unexpected error in tavily_search: {e}\n{traceback.format_exc()}")
        return json.dumps({"error": f"An unexpected error occurred: {str(e)}", "status": "error_unexpected"})
