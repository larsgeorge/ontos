"""
Unit tests for file_security module

Tests file security utilities including:
- Filename sanitization
- Header-safe filename sanitization
- File extension validation
- Path component safety checks
- Safe path joining
"""
import pytest

from src.common.file_security import (
    sanitize_filename,
    sanitize_filename_for_header,
    validate_file_extension,
    is_safe_path_component,
    get_safe_path,
    MAX_FILENAME_LENGTH,
)


class TestFileSecurity:
    """Test suite for file security utilities"""

    # sanitize_filename tests
    def test_sanitize_filename_valid_name(self):
        """Test sanitizing a valid filename."""
        result = sanitize_filename("document.pdf")
        assert result == "document.pdf"

    def test_sanitize_filename_path_traversal(self):
        """Test sanitizing path traversal attempts."""
        result = sanitize_filename("../../etc/passwd")
        assert ".." not in result
        assert "/" not in result
        # os.path.basename extracts 'passwd' from '../../etc/passwd'
        assert result == "passwd"

    def test_sanitize_filename_with_directory(self):
        """Test extracting basename from path."""
        result = sanitize_filename("/var/www/file.txt")
        assert result == "file.txt"

    def test_sanitize_filename_windows_path(self):
        """Test handling Windows paths."""
        result = sanitize_filename("C:\\Users\\test\\file.txt")
        # On Unix, backslashes are not path separators, so they get replaced with _
        assert result == "C__Users_test_file.txt"

    def test_sanitize_filename_invalid_chars(self):
        """Test removing invalid filesystem characters."""
        result = sanitize_filename("file<>name.txt")
        assert "<" not in result
        assert ">" not in result
        assert result == "file__name.txt"

    def test_sanitize_filename_null_bytes(self):
        """Test removing null bytes."""
        result = sanitize_filename("file\x00name.txt")
        assert "\x00" not in result
        assert result == "filename.txt"

    def test_sanitize_filename_windows_reserved(self):
        """Test handling Windows reserved names."""
        result = sanitize_filename("CON.txt")
        assert result == "CON_.txt"
        
        result = sanitize_filename("PRN.log")
        assert result == "PRN_.log"

    def test_sanitize_filename_too_long(self):
        """Test truncating excessively long filenames."""
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name)
        assert len(result) <= MAX_FILENAME_LENGTH
        assert result.endswith(".txt")

    def test_sanitize_filename_empty_string(self):
        """Test handling empty string."""
        result = sanitize_filename("")
        assert result == "file.bin"

    def test_sanitize_filename_none(self):
        """Test handling None input."""
        result = sanitize_filename(None)
        assert result == "file.bin"

    def test_sanitize_filename_custom_default(self):
        """Test using custom default filename."""
        result = sanitize_filename("", default="custom.txt")
        assert result == "custom.txt"

    def test_sanitize_filename_only_dots(self):
        """Test handling filenames with only dots."""
        result = sanitize_filename("..")
        assert result == "file.bin"
        
        result = sanitize_filename(".")
        assert result == "file.bin"

    def test_sanitize_filename_hidden_file(self):
        """Test handling hidden files (starting with dot)."""
        result = sanitize_filename(".hidden")
        # Leading dots are stripped in step 5
        assert result == "hidden"

    def test_sanitize_filename_leading_trailing_spaces(self):
        """Test removing leading/trailing spaces."""
        result = sanitize_filename("  file.txt  ")
        assert result == "file.txt"

    # sanitize_filename_for_header tests
    def test_sanitize_filename_for_header_valid(self):
        """Test sanitizing valid filename for headers."""
        result = sanitize_filename_for_header("document.pdf")
        assert result == "document.pdf"

    def test_sanitize_filename_for_header_quotes(self):
        """Test removing quotes from filename."""
        result = sanitize_filename_for_header('file"name.txt')
        assert '"' not in result
        assert result == "file_name.txt"

    def test_sanitize_filename_for_header_newlines(self):
        """Test removing newlines from filename."""
        result = sanitize_filename_for_header("file\nname.txt")
        assert "\n" not in result
        assert result == "file_name.txt"

    def test_sanitize_filename_for_header_carriage_return(self):
        """Test removing carriage returns from filename."""
        result = sanitize_filename_for_header("file\rname.txt")
        assert "\r" not in result
        assert result == "file_name.txt"

    def test_sanitize_filename_for_header_tabs(self):
        """Test removing tabs from filename."""
        result = sanitize_filename_for_header("file\tname.txt")
        assert "\t" not in result
        assert result == "file_name.txt"

    def test_sanitize_filename_for_header_combined_attacks(self):
        """Test handling combined header injection attempts."""
        result = sanitize_filename_for_header('../../"file\n\rname".txt')
        assert ".." not in result
        assert '"' not in result
        assert "\n" not in result
        assert "\r" not in result

    # validate_file_extension tests
    def test_validate_file_extension_allowed(self):
        """Test validating allowed file extension."""
        result = validate_file_extension("document.pdf", {".pdf", ".docx"})
        assert result is True

    def test_validate_file_extension_not_allowed(self):
        """Test rejecting disallowed file extension."""
        result = validate_file_extension("script.exe", {".pdf", ".docx"})
        assert result is False

    def test_validate_file_extension_case_insensitive(self):
        """Test case-insensitive extension validation."""
        result = validate_file_extension("document.PDF", {".pdf"})
        assert result is True

    def test_validate_file_extension_no_extension(self):
        """Test validating filename without extension."""
        result = validate_file_extension("readme", {".txt"})
        assert result is False

    def test_validate_file_extension_empty_filename(self):
        """Test validating empty filename."""
        result = validate_file_extension("", {".txt"})
        assert result is False

    # is_safe_path_component tests
    def test_is_safe_path_component_valid(self):
        """Test validating safe path component."""
        assert is_safe_path_component("data_products") is True
        assert is_safe_path_component("report-2024") is True
        assert is_safe_path_component("file_123") is True

    def test_is_safe_path_component_path_traversal(self):
        """Test rejecting path traversal in component."""
        assert is_safe_path_component("..") is False
        assert is_safe_path_component("../etc") is False
        assert is_safe_path_component("data/../etc") is False

    def test_is_safe_path_component_slashes(self):
        """Test rejecting slashes in component."""
        assert is_safe_path_component("data/products") is False
        assert is_safe_path_component("data\\products") is False

    def test_is_safe_path_component_null_byte(self):
        """Test rejecting null bytes in component."""
        assert is_safe_path_component("data\x00products") is False

    def test_is_safe_path_component_empty(self):
        """Test rejecting empty component."""
        assert is_safe_path_component("") is False
        assert is_safe_path_component("   ") is False

    def test_is_safe_path_component_only_dots(self):
        """Test rejecting components with only dots."""
        assert is_safe_path_component(".") is False
        assert is_safe_path_component("...") is False

    def test_is_safe_path_component_tilde(self):
        """Test rejecting tilde in component."""
        assert is_safe_path_component("~") is False
        assert is_safe_path_component("~/data") is False

    # get_safe_path tests
    def test_get_safe_path_valid_components(self):
        """Test joining valid path components."""
        result = get_safe_path("data", "products", "report.pdf")
        assert "data" in result
        assert "products" in result
        assert "report.pdf" in result

    def test_get_safe_path_single_component(self):
        """Test handling single component."""
        result = get_safe_path("data")
        assert result == "data"

    def test_get_safe_path_unsafe_component(self):
        """Test rejecting unsafe component."""
        with pytest.raises(ValueError) as exc_info:
            get_safe_path("data", "../etc", "file.txt")
        assert "Unsafe path component" in str(exc_info.value)

    def test_get_safe_path_slash_in_component(self):
        """Test rejecting component with slash."""
        with pytest.raises(ValueError) as exc_info:
            get_safe_path("data", "sub/dir", "file.txt")
        assert "Unsafe path component" in str(exc_info.value)

    def test_get_safe_path_null_byte(self):
        """Test rejecting component with null byte."""
        with pytest.raises(ValueError) as exc_info:
            get_safe_path("data", "sub\x00dir", "file.txt")
        assert "Unsafe path component" in str(exc_info.value)

    def test_get_safe_path_empty_component(self):
        """Test rejecting empty component."""
        with pytest.raises(ValueError) as exc_info:
            get_safe_path("data", "", "file.txt")
        assert "Unsafe path component" in str(exc_info.value)

