import datetime
import markdown
import bleach
from markdown.extensions.codehilite import CodeHiliteExtension
from pymdownx import highlight, superfences, emoji

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
