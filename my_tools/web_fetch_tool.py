import requests
from bs4 import BeautifulSoup
import json
import traceback

def fetch_webpage(url: str) -> str:
    """
    Fetches and extracts the main text content from a given web URL.
    Use this to dive deeper into search results rather than just reading snippets.

    @param url (string): The full URL of the webpage to fetch. REQUIRED.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        # Use a timeout to prevent the system from hanging
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        
        # Remove noisy elements that don't contribute to main content
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            element.extract()

        # Get text
        text = soup.get_text(separator='\n')

        # Clean whitespace: break into lines and remove leading/trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Drop blank lines
        text = '\n'.join(chunk for chunk in lines if chunk)

        # Truncate content to avoid context limit (e.g., 10,000 chars)
        max_chars = 10000
        is_truncated = False
        if len(text) > max_chars:
            text = text[:max_chars]
            is_truncated = True

        result = {
            "status": "success",
            "url": url,
            "title": soup.title.string.strip() if soup.title else "No Title Found",
            "content": text,
            "truncated": is_truncated
        }
        
        return json.dumps(result, indent=2)

    except requests.exceptions.RequestException as e:
        return json.dumps({"status": "error", "message": f"Failed to fetch webpage: {str(e)}"})
    except Exception as e:
        print(f"Error in fetch_webpage: {e}\n{traceback.format_exc()}")
        return json.dumps({"status": "error", "message": f"An unexpected error occurred: {str(e)}"})
