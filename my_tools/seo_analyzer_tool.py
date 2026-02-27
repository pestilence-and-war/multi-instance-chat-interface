import json
import re
import os
import math
from typing import Dict, Any, List

def analyze_seo_readability(file_path: str) -> str:
    """
    Analyzes a Markdown or text file for SEO best practices and readability.
    Calculates keyword density, header structure, and Flesch Reading Ease.

    @param file_path (string): Path to the Markdown or text file.
    """
    if not os.path.exists(file_path):
        return json.dumps({"status": "error", "message": f"File not found: {file_path}"})

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 1. Basic Stats
        words = re.findall(r'\w+', content.lower())
        word_count = len(words)
        sentences = re.split(r'[.!?]+', content)
        sentences = [s for s in sentences if s.strip()]
        sentence_count = len(sentences)
        
        # 2. Readability (Simplified Flesch Reading Ease)
        # Score = 206.835 - 1.015 * (total words / total sentences) - 84.6 * (total syllables / total words)
        def count_syllables(word):
            word = word.lower()
            count = 0
            vowels = "aeiouy"
            if word[0] in vowels:
                count += 1
            for index in range(1, len(word)):
                if word[index] in vowels and word[index - 1] not in vowels:
                    count += 1
            if word.endswith("e"):
                count -= 1
            if count == 0:
                count = 1
            return count

        syllable_count = sum(count_syllables(w) for w in words)
        
        if word_count > 0 and sentence_count > 0:
            readability_score = 206.835 - 1.015 * (word_count / sentence_count) - 84.6 * (syllable_count / word_count)
        else:
            readability_score = 0

        # 3. SEO - Header Structure
        headers = re.findall(r'^(#{1,6})\s+(.*)$', content, re.MULTILINE)
        h1_count = len([h for h in headers if h[0] == '#'])
        
        # 4. SEO - Keyword Density (Top 5 keywords)
        stopwords = {'the', 'and', 'a', 'to', 'of', 'in', 'is', 'it', 'for', 'on', 'with', 'that', 'as', 'are', 'be', 'this', 'by', 'at', 'or', 'an'}
        filtered_words = [w for w in words if w not in stopwords and len(w) > 2]
        freq_map = {}
        for w in filtered_words:
            freq_map[w] = freq_map.get(w, 0) + 1
        
        sorted_keywords = sorted(freq_map.items(), key=lambda x: x[1], reverse=True)[:5]
        keyword_density = {k: round((v / word_count) * 100, 2) for k, v in sorted_keywords} if word_count > 0 else {}

        results = {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "readability_score": round(readability_score, 2),
            "readability_level": _get_readability_level(readability_score),
            "headers": {
                "total": len(headers),
                "h1_count": h1_count,
                "structure": [{"level": len(h[0]), "text": h[1]} for h in headers]
            },
            "top_keywords": keyword_density
        }

        return json.dumps({"status": "success", "results": results}, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def _get_readability_level(score: float) -> str:
    if score >= 90: return "Very Easy (5th grade)"
    if score >= 80: return "Easy (6th grade)"
    if score >= 70: return "Fairly Easy (7th grade)"
    if score >= 60: return "Standard (8th-9th grade)"
    if score >= 50: return "Fairly Difficult (10th-12th grade)"
    if score >= 30: return "Difficult (College)"
    return "Very Difficult (College Graduate)"
