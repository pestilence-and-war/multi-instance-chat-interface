import json
import requests
import os
from typing import List, Optional

def search_assets(query: str, asset_type: str = "image", limit: int = 5) -> str:
    """
    Searches for public domain or creative commons assets (images, icons).
    Uses the Tavily search API to find relevant assets from curated sources.

    @param query (string): The search term for the asset.
    @param asset_type (string): Type of asset: 'image', 'icon', 'font'. Defaults to 'image'.
    @param limit (integer): Number of results to return.
    """
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    if not TAVILY_API_KEY:
         return json.dumps({"status": "error", "message": "TAVILY_API_KEY not found."})

    # Craft a query that targets free asset sites
    curated_sites = {
        "image": "site:unsplash.com OR site:pexels.com OR site:pixabay.com",
        "icon": "site:flaticon.com OR site:thenounproject.com OR site:icons8.com",
        "font": "site:fonts.google.com OR site:fontspace.com OR site:dafont.com"
    }
    
    site_filter = curated_sites.get(asset_type, "")
    full_query = f"{query} {site_filter}"

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": full_query,
        "search_depth": "basic",
        "max_results": limit
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        assets = []
        for result in data.get("results", []):
            assets.append({
                "title": result.get("title"),
                "url": result.get("url"),
                "content": result.get("content")
            })
            
        return json.dumps({"status": "success", "asset_type": asset_type, "assets": assets}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})
