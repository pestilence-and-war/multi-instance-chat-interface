# my_tools/grokipedia_tool.py
import json
import os
from typing import Dict, Any, Optional

try:
    from grokipedia_api import GrokipediaClient
    from grokipedia_api.exceptions import GrokipediaNotFoundError, GrokipediaAPIError
except ImportError:
    # Fallback if library not yet installed
    GrokipediaClient = None

def grokipedia_search(query: str, limit: int = 5) -> str:
    """
    Searches Grokipedia for articles related to a topic.
    Returns a list of matching entries with their titles and virtual URLs.
    The researcher should review this list and then use 'grokipedia_read' to fetch the content of the best match.

    @param query (string): The search term or topic. REQUIRED.
    @param limit (integer): Maximum number of results to return. Defaults to 5.
    """
    if GrokipediaClient is None:
        return json.dumps({"status": "error", "message": "Grokipedia API library not installed. Please check requirements.txt."})

    print(f"   [GROKIPEDIA]: Searching for '{query}'...")
    
    try:
        with GrokipediaClient() as client:
            response = client.search(query, limit=limit)
            valid_hits = response.get('results', [])
            
            if not valid_hits:
                return json.dumps({"status": "success", "results": [], "message": f"No entries found for '{query}'."})
            
            results = []
            for hit in valid_hits:
                title = hit.get('title', 'Unknown Title')
                slug = hit.get('slug', '')
                views = hit.get('viewCount', 0)
                virtual_url = f"https://grokipedia.com/entry/{slug}"
                
                results.append({
                    "title": title,
                    "slug": slug,
                    "views": views,
                    "url": virtual_url
                })
            
            return json.dumps({"status": "success", "results": results}, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "message": f"Grokipedia Search Error: {e}"})

def grokipedia_read(url_or_slug: str) -> str:
    """
    Fetches the full content of a Grokipedia article.
    Use this tool after finding a relevant article with 'grokipedia_search'.

    @param url_or_slug (string): The virtual URL from the search result or the raw slug. REQUIRED.
    """
    if GrokipediaClient is None:
        return json.dumps({"status": "error", "message": "Grokipedia API library not installed."})

    # Extract Slug
    slug = url_or_slug
    if "grokipedia.com/entry/" in url_or_slug:
        slug = url_or_slug.split("entry/")[1].strip()
    elif "/" in url_or_slug:
        slug = url_or_slug.split("/")[-1]

    print(f"   [GROKIPEDIA]: Reading article '{slug}'...")

    try:
        with GrokipediaClient() as client:
            page_data = client.get_page(slug, include_content=True)
            
            if not page_data or 'page' not in page_data:
                return json.dumps({"status": "error", "message": "Article content empty or not found."})

            page = page_data['page']
            title = page.get('title', 'Unknown')
            content = page.get('content', '')
            
            citations = page.get('citations', [])
            citation_list = [f"- {c.get('title', 'Ref')} ({c.get('url', '')})" for c in citations[:5]]
            
            full_text = f"""TITLE: {title}

{content}"""
            if citation_list:
                full_text += "\n\n[CITATIONS]:\n" + "\n".join(citation_list)
            
            # Return truncated to avoid context overflow but enough for a 20B model
            return full_text[:5000]

    except Exception as e:
        return json.dumps({"status": "error", "message": f"Grokipedia Read Error: {e}"})
