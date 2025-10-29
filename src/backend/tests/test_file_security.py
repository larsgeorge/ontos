"""
Tests for file security utilities.

Tests the filename sanitization and validation functions to ensure
they properly prevent path traversal and other security exploits.
"""
import pytest
from src.common.file_security import (
    sanitize_filename,
    sanitize_filename_for_header,
    validate_file_extension,
    is_safe_path_component,
    get_safe_path,
)


class TestSanitizeFilename:
    """Test filename sanitization function."""
    
    def test_valid_filename_unchanged(self):
        """Valid filenames should pass through unchanged."""
        assert sanitize_filename("document.pdf") == "document.pdf"
        assert sanitize_filename("my_file_123.txt") == "my_file_123.txt"
        assert sanitize_filename("report-2023.xlsx") == "report-2023.xlsx"
    
    def test_path_traversal_prevention(self):
        """Path traversal attempts should be sanitized."""
        # Basic path traversal - os.path.basename extracts only final component
        assert sanitize_filename("../../etc/passwd") == "passwd"
        assert sanitize_filename("../../../secret.txt") == "secret.txt"
        
        # Absolute paths - basename extracts final component
        assert sanitize_filename("/etc/passwd") == "passwd"
        assert sanitize_filename("/var/log/system.log") == "system.log"
        
        # Windows paths - on Unix, backslashes aren't path separators, get replaced with _
        # This is still secure - prevents path traversal
        assert sanitize_filename("C:\\Windows\\System32\\config") == "C__Windows_System32_config"
        # .. gets removed, backslashes become underscores
        assert sanitize_filename("..\\..\\windows\\file.txt") == "__windows_file.txt"
    
    def test_null_byte_removal(self):
        """Null bytes should be removed."""
        assert sanitize_filename("file\x00.txt") == "file.txt"
        assert sanitize_filename("mali\x00cious.pdf") == "malicious.pdf"
    
    def test_special_characters_removed(self):
        """Special filesystem characters should be replaced."""
        assert sanitize_filename("file<test>.txt") == "file_test_.txt"
        assert sanitize_filename('file"name".pdf') == "file_name_.pdf"
        assert sanitize_filename("file:name.doc") == "file_name.doc"
        assert sanitize_filename("file|name.txt") == "file_name.txt"
        assert sanitize_filename("file*name.txt") == "file_name.txt"
        assert sanitize_filename("file?name.txt") == "file_name.txt"
    
    def test_windows_reserved_names(self):
        """Windows reserved filenames should be modified."""
        assert sanitize_filename("CON.txt") == "CON_.txt"
        assert sanitize_filename("PRN.log") == "PRN_.log"
        assert sanitize_filename("AUX") == "AUX_"
        assert sanitize_filename("NUL.dat") == "NUL_.dat"
        assert sanitize_filename("COM1.txt") == "COM1_.txt"
        assert sanitize_filename("LPT1.txt") == "LPT1_.txt"
    
    def test_leading_trailing_dots_spaces(self):
        """Leading/trailing dots and spaces should be removed."""
        assert sanitize_filename("  file.txt  ") == "file.txt"
        assert sanitize_filename("..file.txt") == "file.txt"
        assert sanitize_filename("...hidden") == "hidden"
    
    def test_hidden_files_converted(self):
        """Hidden files (starting with dot) are stripped of leading dots."""
        # Leading dots and spaces are stripped, making hidden files visible
        assert sanitize_filename(".hidden") == "hidden"
        assert sanitize_filename(".gitignore") == "gitignore"
        # This prevents hidden file creation while still being safe
    
    def test_empty_or_none_uses_default(self):
        """Empty or None filenames should use default."""
        assert sanitize_filename(None) == "file.bin"
        assert sanitize_filename("") == "file.bin"
        assert sanitize_filename(None, default="default.txt") == "default.txt"
        assert sanitize_filename("", default="custom.dat") == "custom.dat"
    
    def test_length_limit_enforced(self):
        """Very long filenames should be truncated."""
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name)
        assert len(result) <= 200
        # Should preserve extension
        assert result.endswith(".txt")
    
    def test_only_dots_uses_default(self):
        """Filenames that are only dots should use default."""
        assert sanitize_filename(".") == "file.bin"
        assert sanitize_filename("..") == "file.bin"
        assert sanitize_filename("...") == "file.bin"
    
    def test_complex_attack_vectors(self):
        """Test complex combined attack vectors."""
        # Path traversal with null bytes - basename extracts final component
        assert sanitize_filename("../../etc\x00/passwd") == "passwd"
        
        # Mixed separators - basename extracts based on OS path separator
        # On Unix, only / is a separator, backslashes become underscores
        assert sanitize_filename("../..\\path/to\\file.txt") == "to_file.txt"
        
        # Hidden file with path traversal - basename extracts, leading dot stripped
        assert sanitize_filename("../../.ssh/id_rsa") == "id_rsa"


class TestSanitizeFilenameForHeader:
    """Test filename sanitization for HTTP headers."""
    
    def test_basic_sanitization(self):
        """Should apply basic filename sanitization."""
        assert sanitize_filename_for_header("../../file.txt") == "file.txt"
    
    def test_quote_removal(self):
        """Quotes should be removed for header safety."""
        assert sanitize_filename_for_header('file"name.txt') == "file_name.txt"
        assert sanitize_filename_for_header("file'name.txt") == "file_name.txt"
    
    def test_newline_removal(self):
        """Newlines and carriage returns should be removed."""
        assert sanitize_filename_for_header("file\nname.txt") == "file_name.txt"
        assert sanitize_filename_for_header("file\rname.txt") == "file_name.txt"
        assert sanitize_filename_for_header("file\r\nname.txt") == "file__name.txt"
    
    def test_tab_removal(self):
        """Tabs should be removed."""
        assert sanitize_filename_for_header("file\tname.txt") == "file_name.txt"
    
    def test_header_injection_prevention(self):
        """Should prevent header injection attacks."""
        # Attempt to inject additional headers
        malicious = 'file.txt"\r\nX-Evil-Header: malicious'
        result = sanitize_filename_for_header(malicious)
        assert "\r" not in result
        assert "\n" not in result
        assert '"' not in result


class TestValidateFileExtension:
    """Test file extension validation."""
    
    def test_allowed_extensions(self):
        """Allowed extensions should return True."""
        allowed = {'.pdf', '.docx', '.txt'}
        assert validate_file_extension("document.pdf", allowed) is True
        assert validate_file_extension("file.docx", allowed) is True
        assert validate_file_extension("readme.txt", allowed) is True
    
    def test_disallowed_extensions(self):
        """Disallowed extensions should return False."""
        allowed = {'.pdf', '.docx', '.txt'}
        assert validate_file_extension("script.exe", allowed) is False
        assert validate_file_extension("file.sh", allowed) is False
        assert validate_file_extension("payload.bin", allowed) is False
    
    def test_case_insensitive(self):
        """Extension checking should be case-insensitive."""
        allowed = {'.pdf'}
        assert validate_file_extension("file.PDF", allowed) is True
        assert validate_file_extension("file.Pdf", allowed) is True
        assert validate_file_extension("file.pdf", allowed) is True
    
    def test_empty_filename(self):
        """Empty filename should return False."""
        allowed = {'.pdf'}
        assert validate_file_extension("", allowed) is False
        assert validate_file_extension(None, allowed) is False
    
    def test_no_extension(self):
        """Files without extension should return False."""
        allowed = {'.pdf'}
        assert validate_file_extension("noextension", allowed) is False


class TestIsSafePathComponent:
    """Test path component safety validation."""
    
    def test_safe_components(self):
        """Safe path components should return True."""
        assert is_safe_path_component("uploads") is True
        assert is_safe_path_component("data-products") is True
        assert is_safe_path_component("entity123") is True
        assert is_safe_path_component("my_folder") is True
    
    def test_path_traversal_detected(self):
        """Path traversal should be detected."""
        assert is_safe_path_component("..") is False
        assert is_safe_path_component("../etc") is False
        assert is_safe_path_component("folder/../etc") is False
    
    def test_path_separators_detected(self):
        """Path separators should be detected."""
        assert is_safe_path_component("folder/subfolder") is False
        assert is_safe_path_component("folder\\subfolder") is False
    
    def test_null_bytes_detected(self):
        """Null bytes should be detected."""
        assert is_safe_path_component("folder\x00") is False
        assert is_safe_path_component("\x00malicious") is False
    
    def test_empty_or_whitespace(self):
        """Empty or whitespace-only components should be rejected."""
        assert is_safe_path_component("") is False
        assert is_safe_path_component("   ") is False
        assert is_safe_path_component("...") is False


class TestGetSafePath:
    """Test safe path joining."""
    
    def test_safe_components_joined(self):
        """Safe components should be joined properly."""
        result = get_safe_path("uploads", "documents", "file.txt")
        assert result == "uploads/documents/file.txt" or result == "uploads\\documents\\file.txt"
    
    def test_unsafe_component_raises_error(self):
        """Unsafe components should raise ValueError."""
        with pytest.raises(ValueError, match="Unsafe path component"):
            get_safe_path("uploads", "..", "etc")
        
        with pytest.raises(ValueError, match="Unsafe path component"):
            get_safe_path("uploads", "folder/subfolder")
        
        with pytest.raises(ValueError, match="Unsafe path component"):
            get_safe_path("folder\x00malicious", "file.txt")
    
    def test_single_component(self):
        """Single safe component should work."""
        result = get_safe_path("uploads")
        assert result == "uploads"
    
    def test_empty_component_raises_error(self):
        """Empty components should raise ValueError."""
        with pytest.raises(ValueError, match="Unsafe path component"):
            get_safe_path("uploads", "", "file.txt")


class TestRealWorldScenarios:
    """Test real-world attack scenarios."""
    
    def test_scenario_document_upload(self):
        """Simulate document upload with malicious filename."""
        # User uploads file with path traversal in filename
        uploaded_filename = "../../../../../../etc/passwd"
        safe_name = sanitize_filename(uploaded_filename)
        
        # Safe name should not allow directory traversal
        assert ".." not in safe_name
        assert "/" not in safe_name
        assert "\\" not in safe_name
        # os.path.basename extracts only the final component
        assert safe_name == "passwd"
    
    def test_scenario_header_injection(self):
        """Simulate attempt to inject headers via filename."""
        # Malicious filename trying to inject headers
        malicious_filename = 'report.pdf"\r\nContent-Type: text/html\r\n\r\n<script>alert("XSS")</script>'
        safe_name = sanitize_filename_for_header(malicious_filename)
        
        # Should not contain characters that could inject headers
        assert "\r" not in safe_name
        assert "\n" not in safe_name
        assert '"' not in safe_name
    
    def test_scenario_windows_device_file(self):
        """Simulate attempt to access Windows device files."""
        # Trying to access COM port or other device
        device_files = ["CON", "PRN", "AUX", "COM1", "LPT1"]
        for device in device_files:
            safe_name = sanitize_filename(f"{device}.txt")
            # Should be modified to prevent device access by appending underscore
            # CON.txt becomes CON_.txt (still starts with CON but is not the device)
            assert safe_name == f"{device}_.txt"
    
    def test_scenario_hidden_ssh_key(self):
        """Simulate attempt to access hidden SSH keys."""
        malicious = "../../../.ssh/id_rsa"
        safe_name = sanitize_filename(malicious)
        
        # Should not maintain directory structure - basename extracts final component
        assert safe_name == "id_rsa"
    
    def test_scenario_null_byte_truncation(self):
        """Simulate null byte truncation attack."""
        # Attempt to use null byte to truncate filename
        # (some systems interpret filename.txt\x00.jpg as filename.txt)
        malicious = "malicious.php\x00.txt"
        safe_name = sanitize_filename(malicious)
        
        # Null byte should be removed
        assert "\x00" not in safe_name
        assert safe_name == "malicious.php.txt"
    
    def test_scenario_unicode_normalization(self):
        """Test that unicode filenames are handled safely."""
        # While we don't normalize unicode, ensure no crashes
        unicode_name = "fichier_français.pdf"
        safe_name = sanitize_filename(unicode_name)
        assert safe_name == "fichier_français.pdf"
    
    def test_scenario_very_long_filename(self):
        """Simulate extremely long filename attack."""
        # Very long filename that could cause buffer overflow
        long_name = "a" * 1000 + ".txt"
        safe_name = sanitize_filename(long_name)
        
        # Should be truncated to safe length
        assert len(safe_name) <= 200
        # Extension should be preserved
        assert safe_name.endswith(".txt")

