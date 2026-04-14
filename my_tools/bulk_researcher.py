# my_tools/bulk_researcher.py
import json
import os
import time
from typing import List, Dict, Any
from my_tools.jailed_file_manager import _resolve_and_validate_path
from my_tools.code_editor import _sync_db_after_file_creation
from my_tools.tavily_search_tool import tavily_search
from my_tools.grokipedia_tool import grokipedia_read, grokipedia_search

def bulk_researcher(queries: List[str], target_dir: str = "research", file_prefix: str = "topic") -> str:
    """
    (High-Cost) Iteratively researches multiple topics and saves them as individual JSON artifacts.
    This tool manages its own loop to prevent LLM context OOM and ensures cleaner data by 
    prioritizing Grokipedia content found via Tavily/Grokipedia search.

    @param queries (List[string]): A list of search queries or topics to research. REQUIRED.
    @param target_dir (string): The directory to save JSON artifacts. Defaults to 'research'.
    @param file_prefix (string): Prefix for the saved filenames. Defaults to 'topic'.
    """
    results = []
    
    # Ensure directory exists
    abs_dir = _resolve_and_validate_path(target_dir)
    if not abs_dir:
        return json.dumps({"status": "error", "message": f"Security Error: Path '{target_dir}' is outside workspace."})
    os.makedirs(abs_dir, exist_ok=True)

    processed_count = 0
    errors = []

    for i, query in enumerate(queries):
        print(f"--- Bulk Researcher: Processing {i+1}/{len(queries)}: {query} ---")
        
        # Raw user query will now be used directly.
        search_query = query
        topic_name = query
        filename = f"{file_prefix}_{int(time.time())}_{i}.json"
        target_path = os.path.join(target_dir, filename)
        
        raw_content = ""
        source_url = ""
        
        try:
            # 1. Try Grokipedia search first
            g_search_res = json.loads(grokipedia_search(search_query, limit=1))
            if g_search_res.get('status') == 'success' and g_search_res.get('results'):
                best_match = g_search_res['results'][0]
                source_url = best_match['url']
                raw_content = grokipedia_read(source_url)
            
            # 2. Fallback to Tavily-targeted Grokipedia
            if not raw_content or raw_content.startswith('{"status": "error"'):
                t_search_res = json.loads(tavily_search(f"site:grokipedia.com {search_query}", max_results=2))
                if t_search_res.get('status') == 'success' and t_search_res.get('results'):
                    grok_link = next((r['url'] for r in t_search_res['results'] if "grokipedia.com" in r['url']), None)
                    if grok_link:
                        source_url = grok_link
                        raw_content = grokipedia_read(source_url)
            
            # 3. Final Fallback: General Tavily
            if not raw_content or raw_content.startswith('{"status": "error"'):
                 t_search_res = json.loads(tavily_search(search_query, max_results=1))
                 if t_search_res.get('status') == 'success' and t_search_res.get('results'):
                     best_res = t_search_res['results'][0]
                     source_url = best_res['url']
                     raw_content = best_res.get('content', "No content found.")

            if raw_content:
                import re
                # 1. Strip TITLE: [Title] prefix
                cleaned_content = re.sub(r'^TITLE:.*?\n+', '', raw_content, flags=re.MULTILINE)
                # 2. Strip Wiki-style citations: [1], [2], [https://...]
                cleaned_content = re.sub(r'\[\]\(http[s]?://.*?\)', '', cleaned_content)
                cleaned_content = re.sub(r'\[\d+\]', '', cleaned_content)
                # 3. Strip Markdown images: ![...](...)
                cleaned_content = re.sub(r'!\[.*?\]\(.*?\)', '', cleaned_content)
                # 4. Strip internal wiki links but keep text: [Text](/page/Link) -> Text
                cleaned_content = re.sub(r'\[(.*?)\]\(/page/.*?\)', r'\1', cleaned_content)
                # 5. Collapse excessive whitespace
                cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content).strip()
                
                artifact = {
                    "topic": topic_name,
                    "milestone": topic_name, # Alias for backward compatibility with older personas
                    "source_url": source_url,
                    "raw_blurb": cleaned_content
                }
                
                full_save_path = os.path.join(abs_dir, filename)
                with open(full_save_path, 'w', encoding='utf-8') as f:
                    json.dump(artifact, f, indent=2)
                
                _sync_db_after_file_creation(os.path.join(target_dir, filename))
                processed_count += 1
                results.append({"query": query, "status": "success", "file": target_path})
            else:
                errors.append({"query": query, "error": "No content could be harvested."})

        except Exception as e:
            errors.append({"query": query, "error": str(e)})
            print(f"Error processing {query}: {e}")

    return json.dumps({
        "status": "success" if processed_count > 0 else "failure",
        "processed": processed_count,
        "total": len(queries),
        "results": results,
        "errors": errors
    }, indent=2)