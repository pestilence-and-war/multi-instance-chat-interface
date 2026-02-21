import datetime
import markdown
import bleach
from markdown.extensions.codehilite import CodeHiliteExtension
from pymdownx import highlight, superfences, emoji
import requests
def markdown_to_html(md_text):
    """Converts Markdown to HTML with full formatting support"""
    if not md_text:
        return ''
    try:
        extensions = ['markdown.extensions.extra', 'markdown.extensions.tables', 'markdown.extensions.smarty', 'markdown.extensions.nl2br', 'pymdownx.superfences', 'pymdownx.highlight']
        extension_configs = {'pymdownx.highlight': {'css_class': 'codehilite', 'guess_lang': True, 'use_pygments': True}}
        html = markdown.markdown(md_text, extensions=extensions, extension_configs=extension_configs, output_format='html5')
        allowed_tags = {'p', 'pre', 'code', 'span', 'div', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'br', 'hr', 'img', 'strong', 'em', 'blockquote', 'del', 'ins', 'sub', 'sup', 'a', 'figure', 'figcaption', 'mark', 'small'}
        allowed_attrs = {'span': ['class'], 'div': ['class'], 'code': ['class'], 'pre': [], 'img': ['src', 'alt', 'title'], 'a': ['href', 'title'], '*': ['id']}
        safe_html = bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs, strip=False)
        return safe_html
    except Exception as e:
        print(f'Markdown conversion error: {e}')
        return f'<pre>{bleach.clean(str(md_text))}</pre>'

def format_timestamp(iso_timestamp_str):
    """Formats ISO timestamp string nicely."""
    if not iso_timestamp_str or iso_timestamp_str == 'Edited':
        return 'Edited'
    try:
        if 'T' in iso_timestamp_str:
            dt = datetime.datetime.fromisoformat(iso_timestamp_str.replace('Z', '+00:00'))
        else:
            dt = datetime.datetime.fromisoformat(iso_timestamp_str)
        return dt.strftime('%H:%M:%S')
    except ValueError as e:
        print(f'Timestamp parsing error: {e}')
        return iso_timestamp_str

# ---final process text ouput for local tts---

def send_text_to_audio_server(text_to_speak):
    """
    Sends the completed text to the audio server if it's running.
    Fails silently if the server is not available.
    """
    # The URL of our new audio server's endpoint
    url = "http://localhost:5000/generate-audio"
    
    # The payload format our server will expect
    payload = {"text": text_to_speak}
    
    try:
        # Send the request with a timeout to prevent it from hanging
        response = requests.post(url, json=payload, timeout=5)
        
        # Check if the server accepted the request
        if response.status_code == 200:
            print(f"Successfully sent {len(text_to_speak)} chars to audio server.")
        else:
            print(f"Audio server returned an error: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        # This will catch connection errors, timeouts, etc.
        # It's important so your chat app doesn't crash if the audio server isn't running.
        print(f"Could not connect to audio server: {e}")