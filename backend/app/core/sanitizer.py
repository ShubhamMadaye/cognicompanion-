"""
CogniCompanion — Input Sanitizer
=================================
Protects against Cross-Site Scripting (XSS) and content injection
in freeform notes, descriptions, and user inputs.
"""

import html
import re

DANGEROUS_PATTERNS = [
    re.compile(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", re.IGNORECASE | re.DOTALL),
    re.compile(r"<\s*iframe[^>]*>.*?<\s*/\s*iframe\s*>", re.IGNORECASE | re.DOTALL),
    re.compile(r"<\s*object[^>]*>.*?<\s*/\s*object\s*>", re.IGNORECASE | re.DOTALL),
    re.compile(r"<\s*embed[^>]*>", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"vbscript\s*:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),  # onmouseover, onload, onerror, etc.
]


def sanitize_text(value: str | None) -> str | None:
    """
    Sanitizes user input string by stripping scripts, dangerous event handlers,
    and escaping HTML special characters.
    """
    if not value or not isinstance(value, str):
        return value

    cleaned = value
    for pattern in DANGEROUS_PATTERNS:
        cleaned = pattern.sub("", cleaned)

    # Escape HTML to prevent injection when rendered
    return html.escape(cleaned.strip(), quote=True)
