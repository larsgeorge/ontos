"""
HTML/Markdown sanitization utilities for preventing XSS attacks.

This module provides centralized sanitization functions using bleach
to clean user input and LLM-generated content before rendering in the UI.
"""

import bleach

# HTML/Markdown sanitization configuration
ALLOWED_TAGS = [
    'a', 'b', 'i', 'em', 'strong',
    'p', 'ul', 'ol', 'li',
    'blockquote', 'code', 'pre'
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title']
}


def sanitize_markdown_input(user_input: str) -> str:
    """
    Sanitize markdown/HTML input to prevent XSS attacks.

    Args:
        user_input: String containing potentially unsafe HTML/markdown content

    Returns:
        Sanitized string with only allowed HTML tags and attributes

    Example:
        >>> sanitize_markdown_input("<script>alert('xss')</script><b>safe</b>")
        "<b>safe</b>"
    """
    return bleach.clean(
        user_input,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )
