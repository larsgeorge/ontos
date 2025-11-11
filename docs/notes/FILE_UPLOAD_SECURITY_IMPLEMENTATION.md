# File Upload Security Implementation

## Overview

This document describes the security measures implemented to prevent file upload vulnerabilities, specifically path traversal attacks and related exploits.

## Vulnerability Assessment

### Original Vulnerability

The application had critical security vulnerabilities in file upload handling:

1. **Path Traversal (CWE-22)**: User-supplied filenames were used directly in file paths without sanitization
2. **Header Injection (CWE-113)**: Filenames were inserted into HTTP headers without proper escaping
3. **File System Exploits**: No protection against special characters, null bytes, or OS-specific reserved names

### Attack Vectors

**Before Fix:**
```python
# VULNERABLE CODE - DO NOT USE
filename = file.filename or "document.bin"  # Directly from user
dest_path = f"{volume_fs_base}/{base_dir}/{filename}"  # Path traversal possible!
```

**Exploitation Examples:**
- `../../etc/passwd` → Access sensitive files
- `../../../.ssh/id_rsa` → Access SSH keys
- `CON.txt` (Windows) → Device file access
- `file\x00.txt` → Null byte truncation
- `file.txt"\r\nX-Header: evil` → Header injection

## Security Solution

### 1. File Security Module

Created `/src/backend/src/common/file_security.py` with comprehensive security functions:

#### `sanitize_filename(filename, default="file.bin")`
Sanitizes filenames through multiple security layers:

1. **Path Component Extraction**: Uses `os.path.basename()` to strip directory paths
2. **Null Byte Removal**: Eliminates `\x00` characters used in truncation attacks
3. **Path Traversal Prevention**: Removes `..`, `/`, `\`, `~` sequences
4. **Invalid Character Filtering**: Removes `< > : " | ? * \x00-\x1f \x7f`
5. **Windows Reserved Names**: Modifies `CON`, `PRN`, `AUX`, `COM1-9`, `LPT1-9`
6. **Length Enforcement**: Limits to 200 characters (preserving extension)
7. **Leading/Trailing Cleanup**: Removes dots and spaces
8. **Hidden File Handling**: Converts leading dots to underscores
9. **Empty String Protection**: Returns default if result is empty

**Example:**
```python
sanitize_filename("../../etc/passwd")  # Returns: "etc_passwd"
sanitize_filename("CON.txt")           # Returns: "CON_.txt"
sanitize_filename(".hidden")           # Returns: "_hidden"
```

#### `sanitize_filename_for_header(filename, default="file.bin")`
Additional sanitization for HTTP headers:

1. Applies all base sanitization
2. Removes quotes (`"`, `'`)
3. Removes newlines (`\r`, `\n`)
4. Removes tabs (`\t`)

**Prevents:**
```python
# Attack: 'file.txt"\r\nX-Evil-Header: malicious'
# Result: 'file.txt__X-Evil-Header__malicious'
```

#### `validate_file_extension(filename, allowed_extensions)`
Validates file extensions against whitelist (case-insensitive).

#### `is_safe_path_component(path_component)`
Validates individual path components don't contain:
- Path traversal patterns
- Path separators
- Null bytes
- Only dots/spaces

#### `get_safe_path(*components)`
Safely joins path components with validation.

### 2. Fixed Endpoints

#### `/api/entities/{entity_type}/{entity_id}/documents` (POST)
**File:** `src/backend/src/routes/metadata_routes.py`

**Changes:**
```python
# Import security module
from src.common.file_security import sanitize_filename, sanitize_filename_for_header, is_safe_path_component

# Validate path parameters
if not is_safe_path_component(entity_type) or not is_safe_path_component(entity_id):
    raise HTTPException(status_code=400, detail="Invalid entity_type or entity_id")

# Sanitize filename
raw_filename = file.filename or "document.bin"
filename = sanitize_filename(raw_filename, default="document.bin")

# Now safe to use in path
dest_path = f"{volume_fs_base}/{base_dir}/{filename}"
```

#### `/api/documents/{id}/content` (GET)
**File:** `src/backend/src/routes/metadata_routes.py`

**Changes:**
```python
# Sanitize filename for Content-Disposition header
safe_filename = sanitize_filename_for_header(doc.original_filename, default="document.bin")
headers = {"Content-Disposition": f"inline; filename=\"{safe_filename}\""}
```

#### `/api/data-products/upload` (POST)
**File:** `src/backend/src/routes/data_product_routes.py`

**Changes:**
```python
# Sanitize for logging and validation
raw_filename = file.filename or "upload.bin"
safe_filename = sanitize_filename(raw_filename, default="upload.bin")

# Use sanitized filename throughout
if not (safe_filename.lower().endswith('.yaml') or safe_filename.lower().endswith('.json')):
    raise HTTPException(...)
```

#### `/api/data-contracts/upload` (POST)
**File:** `src/backend/src/routes/data_contracts_routes.py`

**Changes:**
```python
# Sanitize filename
raw_filename = file.filename or "uploaded_contract"
safe_filename = sanitize_filename(raw_filename, default="uploaded_contract")

# Use in audit logging and processing
details_for_audit = {"params": {"filename": safe_filename}}
```

#### `/api/data-contracts/{contract_id}/odcs/export` (GET)
**File:** `src/backend/src/routes/data_contracts_routes.py`

**Changes:**
```python
# Sanitize generated filename for header
raw_filename = f"{(db_obj.name or 'contract').lower().replace(' ', '_')}-odcs.yaml"
safe_filename = sanitize_filename_for_header(raw_filename, default="contract-odcs.yaml")
headers = {'Content-Disposition': f'attachment; filename="{safe_filename}"'}
```

#### `_upload_document()` (Seeding Utility)
**File:** `src/backend/src/utils/metadata_seed_loader.py`

**Changes:**
```python
# Sanitize filename from YAML configuration
safe_filename = sanitize_filename(original_filename, default="document.bin")
dest_path = f"{dest_dir}/{safe_filename}"
```

### 3. Test Coverage

Created comprehensive test suite: `/src/backend/tests/test_file_security.py`

**Test Categories:**
- Valid filename passthrough
- Path traversal prevention
- Null byte removal
- Special character handling
- Windows reserved names
- Length limits
- Header injection prevention
- Real-world attack scenarios

**Run Tests:**
```bash
cd src/backend
pytest tests/test_file_security.py -v
```

## Security Checklist

### Before Fix ❌
- [ ] Filenames validated before use
- [ ] Path traversal prevention
- [ ] Null byte protection
- [ ] Special character filtering
- [ ] Length limits enforced
- [ ] Header injection prevention
- [ ] OS-specific protections

### After Fix ✅
- [x] Filenames validated before use
- [x] Path traversal prevention
- [x] Null byte protection
- [x] Special character filtering
- [x] Length limits enforced
- [x] Header injection prevention
- [x] OS-specific protections

## Best Practices Applied

1. **Defense in Depth**: Multiple layers of validation
2. **Whitelist Approach**: Only allow safe characters/patterns
3. **Fail Securely**: Default to safe values on error
4. **Consistent Application**: Centralized security module
5. **Comprehensive Testing**: Full test coverage of edge cases

## OWASP Compliance

This implementation addresses:
- **A01:2021 – Broken Access Control**: Prevents unauthorized file access via path traversal
- **A03:2021 – Injection**: Prevents header injection attacks
- **A04:2021 – Insecure Design**: Implements secure-by-design file handling

## References

- CWE-22: Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')
- CWE-113: Improper Neutralization of CRLF Sequences in HTTP Headers
- CWE-73: External Control of File Name or Path
- OWASP File Upload Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html

## Audit Trail

**Date:** 2025-10-29  
**Issue:** #34 - File upload security vulnerabilities  
**Branch:** security/issue_34  
**Reviewer:** [Pending]  
**Status:** Implementation Complete, Awaiting Review

## Future Enhancements

Consider implementing:
1. **File Content Validation**: Verify MIME types match extensions
2. **Virus Scanning**: Integrate antivirus scanning for uploads
3. **Size Limits**: Enforce maximum file sizes
4. **Rate Limiting**: Prevent upload flooding
5. **File Type Restrictions**: Whitelist allowed file types per endpoint
6. **Storage Encryption**: Encrypt files at rest

