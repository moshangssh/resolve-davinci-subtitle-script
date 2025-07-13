import re

def clean_html(raw_html: str) -> str:
    """
    Removes HTML tags from a string.
    """
    clean_re = re.compile('<.*?>')
    clean_text = re.sub(clean_re, '', raw_html)
    return clean_text