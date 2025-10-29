"""
File security utilities for safe file handling.

Provides utilities to sanitize and validate filenames to prevent:
- Path traversal attacks (../, /, \\, etc.)
- File system exploits (null bytes, special characters)
- Header injection attacks
- OS-specific reserved filenames
- Excessively long filenames
"""
import os
import re
from typing import Optional
from pathlib import Path


# Maximum filename length (common filesystem limit is 255, use conservative value)
MAX_FILENAME_LENGTH = 200

# Reserved filenames on Windows that should be rejected
WINDOWS_RESERVED_NAMES = {
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
}

# Characters that are invalid in filenames on various filesystems
INVALID_CHARS_PATTERN = re.compile(r'[<>:"|?*\x00-\x1f\x7f]')

# Pattern to detect path traversal attempts
PATH_TRAVERSAL_PATTERN = re.compile(r'\.\.|/|\\|~')


def sanitize_filename(filename: Optional[str], default: str = "file.bin") -> str:
    """
    Sanitize a filename to prevent security exploits.
    
    This function implements multiple layers of security:
    1. Extracts only the base filename (no directory components)
    2. Removes null bytes and control characters
    3. Removes path traversal sequences
    4. Removes or replaces invalid filesystem characters
    5. Prevents Windows reserved filenames
    6. Limits filename length
    7. Ensures filename is not empty
    
    Args:
        filename: The filename to sanitize (may be None or unsafe)
        default: Default filename to use if sanitization results in empty string
        
    Returns:
        A safe filename that can be used for file operations
        
    Examples:
        >>> sanitize_filename("../../etc/passwd")
        'etc_passwd'
        >>> sanitize_filename("valid_file.txt")
        'valid_file.txt'
        >>> sanitize_filename("CON.txt")  # Windows reserved
        'CON_.txt'
        >>> sanitize_filename("file<>name.txt")
        'file_name.txt'
    """
    if not filename:
        return default
    
    # Step 1: Extract basename only (strips any directory paths)
    # This handles cases like "/etc/passwd", "../../file", "C:\\windows\\file"
    filename = os.path.basename(filename)
    
    # Step 2: Remove null bytes (used in path truncation attacks)
    filename = filename.replace('\x00', '')
    
    # Step 3: Remove additional path traversal patterns that may have survived
    # Replace path separators and parent directory references
    filename = filename.replace('..', '')
    filename = filename.replace('/', '_')
    filename = filename.replace('\\', '_')
    filename = filename.replace('~', '_')
    
    # Step 4: Remove invalid filesystem characters
    # Replace with underscore to maintain readability
    filename = INVALID_CHARS_PATTERN.sub('_', filename)
    
    # Step 5: Remove leading/trailing dots and spaces (can cause issues on some filesystems)
    filename = filename.strip('. ')
    
    # Step 6: Check for Windows reserved filenames
    # Split on first dot to get name without extension
    name_part = filename.split('.')[0].upper()
    if name_part in WINDOWS_RESERVED_NAMES:
        # Add underscore to make it safe
        filename = filename.split('.')[0] + '_.' + '.'.join(filename.split('.')[1:]) if '.' in filename else filename + '_'
    
    # Step 7: Enforce maximum length
    if len(filename) > MAX_FILENAME_LENGTH:
        # Preserve extension if possible
        name, ext = os.path.splitext(filename)
        max_name_length = MAX_FILENAME_LENGTH - len(ext)
        filename = name[:max_name_length] + ext
    
    # Step 8: Final validation - ensure we have a valid filename
    if not filename or filename in ('.', '..'):
        return default
    
    # Step 9: Ensure filename doesn't start with a dot (hidden files)
    # Allow if there's a valid name after the dot
    if filename.startswith('.') and len(filename) > 1:
        filename = '_' + filename[1:]
    elif filename == '.':
        return default
        
    return filename


def sanitize_filename_for_header(filename: Optional[str], default: str = "file.bin") -> str:
    """
    Sanitize a filename for use in HTTP headers (e.g., Content-Disposition).
    
    This prevents header injection attacks by:
    1. Using the base sanitize_filename function
    2. Removing characters that could break header syntax
    3. Ensuring proper quoting
    
    Args:
        filename: The filename to sanitize
        default: Default filename to use if sanitization fails
        
    Returns:
        A safe filename suitable for HTTP headers
    """
    # First apply basic filename sanitization
    safe_name = sanitize_filename(filename, default)
    
    # Additional sanitization for headers:
    # Remove quotes, newlines, and carriage returns that could break header syntax
    safe_name = safe_name.replace('"', '_')
    safe_name = safe_name.replace("'", '_')
    safe_name = safe_name.replace('\n', '_')
    safe_name = safe_name.replace('\r', '_')
    safe_name = safe_name.replace('\t', '_')
    
    return safe_name


def validate_file_extension(filename: str, allowed_extensions: set[str]) -> bool:
    """
    Validate that a filename has an allowed extension.
    
    Args:
        filename: The filename to check
        allowed_extensions: Set of allowed extensions (e.g., {'.pdf', '.docx', '.txt'})
                           Extensions should include the dot
        
    Returns:
        True if the extension is allowed, False otherwise
        
    Examples:
        >>> validate_file_extension("document.pdf", {'.pdf', '.docx'})
        True
        >>> validate_file_extension("script.exe", {'.pdf', '.docx'})
        False
    """
    if not filename:
        return False
    
    # Get extension in lowercase for case-insensitive comparison
    _, ext = os.path.splitext(filename.lower())
    
    # Normalize allowed extensions to lowercase
    allowed_lower = {e.lower() for e in allowed_extensions}
    
    return ext in allowed_lower


def is_safe_path_component(path_component: str) -> bool:
    """
    Check if a path component is safe (doesn't contain traversal sequences).
    
    This is useful for validating entity_type and entity_id parameters
    that are used in path construction.
    
    Args:
        path_component: A component of a path to validate
        
    Returns:
        True if safe, False if it contains dangerous sequences
    """
    if not path_component:
        return False
    
    # Check for path traversal patterns
    if PATH_TRAVERSAL_PATTERN.search(path_component):
        return False
    
    # Check for null bytes
    if '\x00' in path_component:
        return False
    
    # Check it's not just dots or spaces
    if path_component.strip('. ') == '':
        return False
    
    return True


def get_safe_path(*components: str) -> str:
    """
    Safely join path components, validating each component.
    
    Args:
        *components: Path components to join
        
    Returns:
        A safely joined path
        
    Raises:
        ValueError: If any component contains dangerous sequences
    """
    safe_components = []
    
    for component in components:
        if not is_safe_path_component(component):
            raise ValueError(f"Unsafe path component detected: {component}")
        safe_components.append(component)
    
    return os.path.join(*safe_components)

