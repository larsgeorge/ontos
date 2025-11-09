"""
Unit tests for sanitization utilities

Tests HTML/Markdown sanitization including:
- XSS prevention
- Allowed tags preservation
- Malicious script removal
"""
import pytest

from src.common.sanitization import sanitize_markdown_input


class TestSanitization:
    """Test suite for sanitization utilities"""

    def test_sanitize_simple_text(self):
        """Test sanitization of plain text."""
        result = sanitize_markdown_input("Hello World")
        assert result == "Hello World"

    def test_sanitize_allowed_tags(self):
        """Test that allowed tags are preserved."""
        input_text = "<b>bold</b> <i>italic</i> <strong>strong</strong>"
        result = sanitize_markdown_input(input_text)
        assert "<b>bold</b>" in result
        assert "<i>italic</i>" in result
        assert "<strong>strong</strong>" in result

    def test_sanitize_script_tag(self):
        """Test that script tags are removed."""
        input_text = "<script>alert('xss')</script>Safe text"
        result = sanitize_markdown_input(input_text)
        assert "<script>" not in result
        # Note: bleach strips tags but keeps text content
        assert "Safe text" in result

    def test_sanitize_onclick_attribute(self):
        """Test that onclick attributes are removed."""
        input_text = '<a href="#" onclick="alert(\'xss\')">Click</a>'
        result = sanitize_markdown_input(input_text)
        assert "onclick" not in result
        assert "Click" in result

    def test_sanitize_allowed_link(self):
        """Test that allowed link attributes are preserved."""
        input_text = '<a href="https://example.com" title="Example">Link</a>'
        result = sanitize_markdown_input(input_text)
        assert "href" in result
        assert "https://example.com" in result
        assert "title" in result

    def test_sanitize_iframe_tag(self):
        """Test that iframe tags are removed."""
        input_text = '<iframe src="malicious.com"></iframe>Safe content'
        result = sanitize_markdown_input(input_text)
        assert "<iframe" not in result
        assert "Safe content" in result

    def test_sanitize_img_tag(self):
        """Test that img tags are removed (not in allowed list)."""
        input_text = '<img src="image.png" onerror="alert(\'xss\')">Text'
        result = sanitize_markdown_input(input_text)
        assert "<img" not in result
        assert "Text" in result

    def test_sanitize_list_tags(self):
        """Test that list tags are preserved."""
        input_text = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        result = sanitize_markdown_input(input_text)
        assert "<ul>" in result
        assert "<li>Item 1</li>" in result

    def test_sanitize_code_tags(self):
        """Test that code and pre tags are preserved."""
        input_text = "<pre><code>print('hello')</code></pre>"
        result = sanitize_markdown_input(input_text)
        assert "<pre>" in result
        assert "<code>" in result
        assert "print" in result

    def test_sanitize_blockquote(self):
        """Test that blockquote tags are preserved."""
        input_text = "<blockquote>Quoted text</blockquote>"
        result = sanitize_markdown_input(input_text)
        assert "<blockquote>Quoted text</blockquote>" in result

    def test_sanitize_empty_string(self):
        """Test sanitization of empty string."""
        result = sanitize_markdown_input("")
        assert result == ""

    def test_sanitize_mixed_content(self):
        """Test sanitization of mixed safe and unsafe content."""
        input_text = """
        <h1>Title</h1>
        <p>Safe paragraph</p>
        <script>malicious()</script>
        <b>Bold text</b>
        <a href="javascript:void(0)">Bad link</a>
        """
        result = sanitize_markdown_input(input_text)
        assert "<script>" not in result
        # Note: bleach strips tags but keeps text content
        assert "<p>Safe paragraph</p>" in result
        assert "<b>Bold text</b>" in result
        # h1 is not in allowed tags
        assert "<h1>" not in result

    def test_sanitize_nested_tags(self):
        """Test sanitization of nested tags."""
        input_text = "<p><strong><em>Nested text</em></strong></p>"
        result = sanitize_markdown_input(input_text)
        assert "<p>" in result
        assert "<strong>" in result
        assert "<em>" in result
        assert "Nested text" in result

