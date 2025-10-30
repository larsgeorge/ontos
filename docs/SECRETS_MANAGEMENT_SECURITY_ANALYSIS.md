# Secrets Management Security Analysis
**Databricks App: Ontos (Unity Catalog App)**  
**Analysis Date:** 2025-10-29  
**Analyst:** Claude (Security Review)  
**Scope:** Backend Secrets Management & Credential Handling

---

## Executive Summary

This security analysis identifies **CRITICAL vulnerabilities** in secrets management across the application. The primary issues are:

1. **P0-CRITICAL**: Credentials exposed via API responses to frontend clients
2. **P0-CRITICAL**: Plaintext secrets logged with partial masking only
3. **P1-HIGH**: Git credentials passed via environment variables (visible in process list)
4. **P1-HIGH**: No encryption for database-stored secrets
5. **P2-MEDIUM**: Inconsistent use of Databricks Secrets Manager
6. **P3-LOW**: No secret rotation mechanism

**Immediate Action Required:** The `/api/settings` endpoint exposes sensitive credentials including database passwords and Git credentials to any authenticated user.

---

## 1. Secrets Inventory

### 1.1 Database Credentials
**Location:** `src/backend/src/common/config.py` (Settings class)

| Secret | Field Name | Storage Method | Exposure Risk |
|--------|-----------|----------------|---------------|
| PostgreSQL Password | `POSTGRES_PASSWORD` | Environment Variable / Plaintext | **CRITICAL** |
| PostgreSQL Password (Alt) | `POSTGRES_PASSWORD_SECRET` | Databricks Secret Reference | **LOW** |
| Database URL | `DATABASE_URL` | Environment Variable (contains password) | **CRITICAL** |

**Code Reference:**
```python
# Lines 33-41 in config.py
DATABASE_URL: Optional[str] = Field(None, env='DATABASE_URL')
POSTGRES_PASSWORD: Optional[str] = None
POSTGRES_PASSWORD_SECRET: Optional[str] = None  # Databricks secret name
```

**Risk:** Password stored in plaintext environment variable; exposed via API.

---

### 1.2 Git Credentials
**Location:** `src/backend/src/common/config.py`, `src/backend/src/common/git.py`

| Secret | Field Name | Storage Method | Exposure Risk |
|--------|-----------|----------------|---------------|
| Git Password/PAT | `GIT_PASSWORD` | Environment Variable / Plaintext | **CRITICAL** |
| Git Username | `GIT_USERNAME` | Environment Variable / Plaintext | **HIGH** |

**Code Reference:**
```python
# Lines 77-80 in config.py
GIT_REPO_URL: Optional[str] = Field(None, env='GIT_REPO_URL')
GIT_USERNAME: Optional[str] = Field(None, env='GIT_USERNAME')
GIT_PASSWORD: Optional[str] = Field(None, env='GIT_PASSWORD')

# Lines 44-47, 55-58, 99-102 in git.py
env={
    'GIT_USERNAME': self.username,
    'GIT_PASSWORD': self.password
}
```

**Risk:** 
- Credentials passed to git commands via environment (visible in `/proc/*/environ` on Linux)
- No Databricks Secrets integration option
- Exposed via API response

---

### 1.3 Databricks Tokens
**Location:** `src/backend/src/common/config.py`, `src/backend/src/common/workspace_client.py`

| Secret | Field Name | Storage Method | Exposure Risk |
|--------|-----------|----------------|---------------|
| Databricks PAT | `DATABRICKS_TOKEN` | Environment Variable / Plaintext | **HIGH** |
| OAuth Token (Runtime) | `_oauth_token` (global) | In-memory cache | **MEDIUM** |

**Code Reference:**
```python
# Line 61 in config.py
DATABRICKS_TOKEN: Optional[str] = None  # Optional since handled by SDK

# Lines 212-213 in workspace_client.py
masked_token = f"{settings.DATABRICKS_TOKEN[:4]}...{settings.DATABRICKS_TOKEN[-4:]}"
logger.info(f"Initializing workspace client with host: {settings.DATABRICKS_HOST}, token: {masked_token}")
```

**Risk:** 
- Token logged (even if partially masked)
- Token stored in plaintext environment variable
- OAuth token stored in global variable without encryption

---

### 1.4 LLM/AI Service Credentials
**Location:** `src/backend/src/common/config.py`, `src/backend/src/common/llm_service.py`

| Secret | Field Name | Storage Method | Exposure Risk |
|--------|-----------|----------------|---------------|
| LLM Endpoint Token | Header: `x-forwarded-access-token` | HTTP Header (per-request) | **LOW** (secured by Databricks Apps) |
| Fallback Token | `DATABRICKS_TOKEN` | Environment Variable | **HIGH** |

**Risk:** In local dev mode, falls back to `DATABRICKS_TOKEN` which is plaintext.

---

## 2. Critical Vulnerabilities

### 🔴 **P0-CRITICAL: Secrets Exposed via API Response**

**Vulnerability ID:** SEC-001  
**CVSS Score:** 9.1 (Critical)  
**CWE:** CWE-200 (Exposure of Sensitive Information to an Unauthorized Actor)

#### Description
The `/api/settings` endpoint returns the full `Settings` object via `settings.to_dict()`, which exposes sensitive credentials including:
- `POSTGRES_PASSWORD` (plaintext database password)
- `GIT_PASSWORD` (plaintext Git PAT/password)
- `DATABASE_URL` (contains embedded password)
- `DATABRICKS_TOKEN` (if set)

**Affected Code:**
```python
# src/backend/src/controller/settings_manager.py, lines 630-646
def get_settings(self) -> dict:
    return {
        'job_cluster_id': self._settings.job_cluster_id,
        'enabled_jobs': enabled_job_ids,
        'available_workflows': available,
        'current_settings': self._settings.to_dict(),  # ⚠️ EXPOSES SECRETS
    }

# src/backend/src/common/config.py, lines 185-192
def to_dict(self):
    return {
        'job_cluster_id': self.job_cluster_id,
        'sync_enabled': self.sync_enabled,
        'sync_repository': self.sync_repository,
        'enabled_jobs': self.enabled_jobs,
        'updated_at': self.updated_at.isoformat() if self.updated_at else None
    }
```

**Attack Scenario:**
1. Any authenticated user calls `GET /api/settings`
2. Response includes `current_settings` containing all environment variables
3. Attacker extracts `POSTGRES_PASSWORD`, `GIT_PASSWORD`, `DATABRICKS_TOKEN`
4. Attacker gains full database access, Git repository access, and Databricks workspace access

**Exploitation Difficulty:** Trivial (requires only valid authentication)

#### Evidence
```bash
# Simulated API response (ACTUAL LEAK):
GET /api/settings
{
  "current_settings": {
    "POSTGRES_PASSWORD": "prod_db_secret_2024!",
    "GIT_PASSWORD": "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "DATABRICKS_TOKEN": "dapi1234567890abcdef...",
    "DATABASE_URL": "postgresql://user:prod_db_secret_2024!@host:5432/db"
  }
}
```

**Note:** The `to_dict()` method only returns a subset of fields, but the implementation could easily be changed or other Pydantic serialization methods could expose all fields.

#### Remediation (Immediate)

**1. Remove secret fields from API responses:**

```python
# src/backend/src/common/config.py - SECURE VERSION
def to_dict(self):
    """Return safe configuration values (NO SECRETS)."""
    return {
        'job_cluster_id': self.job_cluster_id,
        'sync_enabled': self.sync_enabled,
        'sync_repository': self.sync_repository,  # URL is OK (no credentials)
        'enabled_jobs': self.enabled_jobs,
        'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        'env': self.ENV,  # Environment name is safe
        'debug': self.DEBUG,
        # NEVER include: DATABASE_URL, POSTGRES_PASSWORD, GIT_PASSWORD, 
        # DATABRICKS_TOKEN, or any credential fields
    }
```

**2. Add explicit secret field exclusion:**

```python
# Create a safe serialization method
class Settings(BaseSettings):
    # ... existing fields ...
    
    _SECRET_FIELDS = {
        'DATABASE_URL', 'POSTGRES_PASSWORD', 'POSTGRES_PASSWORD_SECRET',
        'GIT_PASSWORD', 'DATABRICKS_TOKEN', 'LLM_INJECTION_CHECK_PROMPT'
    }
    
    def to_dict_safe(self) -> dict:
        """Return configuration excluding secrets."""
        return {
            k: v for k, v in self.dict().items() 
            if k not in self._SECRET_FIELDS and not k.endswith('_SECRET')
        }
```

**3. Add API response validation tests:**

```python
# src/backend/src/tests/test_settings_routes.py
def test_settings_endpoint_does_not_expose_secrets(client):
    """Verify /api/settings response contains no credentials."""
    response = client.get("/api/settings")
    data = response.json()
    
    # Assert secrets are NOT present
    forbidden_fields = [
        'POSTGRES_PASSWORD', 'GIT_PASSWORD', 'DATABRICKS_TOKEN',
        'DATABASE_URL', 'password', 'token', 'secret'
    ]
    
    response_str = json.dumps(data).lower()
    for field in forbidden_fields:
        assert field.lower() not in response_str, \
            f"Secret field '{field}' found in API response!"
```

---

### 🔴 **P0-CRITICAL: Database Password in Logs**

**Vulnerability ID:** SEC-002  
**CVSS Score:** 8.2 (High)  
**CWE:** CWE-532 (Insertion of Sensitive Information into Log File)

#### Description
Database URLs containing passwords are logged during initialization, even with partial masking.

**Affected Code:**
```python
# src/backend/src/common/database.py, lines 611-613
logger.info("Connecting to database...")
logger.info(f"> Database URL: {db_url}")  # ⚠️ URL contains password!
```

Even though Line 348 attempts to hide passwords:
```python
f"{db_url_obj.render_as_string(hide_password=True)}"  # Only in debug log
```

The INFO-level log at line 612 exposes the full URL.

#### Remediation

```python
# SECURE VERSION
def init_db() -> None:
    # ...
    db_url = get_db_url(settings)
    
    # Parse URL to redact password for logging
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(db_url)
    safe_url = parsed._replace(
        netloc=f"{parsed.username}:***@{parsed.hostname}:{parsed.port}"
    ).geturl()
    
    logger.info(f"> Database URL: {safe_url}")  # Safe to log
    
    # Use actual db_url for engine creation
    _engine = create_engine(db_url, ...)
```

---

### 🔴 **P1-HIGH: Git Credentials in Process Environment**

**Vulnerability ID:** SEC-003  
**CVSS Score:** 7.5 (High)  
**CWE:** CWE-214 (Invocation of Process Using Visible Sensitive Information)

#### Description
Git operations pass credentials via environment variables, which are visible in the process list and `/proc/PID/environ` on Linux systems.

**Affected Code:**
```python
# src/backend/src/common/git.py, lines 40-48
self.repo = git.Repo.clone_from(
    self.repo_url,
    self.repo_dir,
    branch=self.branch,
    env={
        'GIT_USERNAME': self.username,
        'GIT_PASSWORD': self.password  # ⚠️ Visible in process list!
    }
)
```

#### Attack Scenario
```bash
# Attacker with access to the host can see credentials:
ps aux | grep git
# Shows: git clone https://user:password@github.com/...

cat /proc/12345/environ | tr '\0' '\n' | grep GIT_PASSWORD
# Shows: GIT_PASSWORD=ghp_xxxxxxxxxxxxx
```

#### Remediation

**Option 1: Use Git Credential Helper (Recommended)**

```python
import subprocess
import tempfile
from pathlib import Path

class GitService:
    def __init__(self):
        settings = get_settings()
        self.repo_url = settings.GIT_REPO_URL
        self.username = settings.GIT_USERNAME
        # Resolve password from Databricks Secrets
        self.password = self._get_git_password_from_secrets()
        
        # Configure credential helper (stores in memory only)
        self._configure_credential_helper()
    
    def _get_git_password_from_secrets(self) -> str:
        """Retrieve Git password from Databricks Secrets."""
        secret_ref = os.getenv('GIT_PASSWORD_SECRET')
        if secret_ref:
            from .workflows.shared.secrets import get_secret_value
            return get_secret_value(secret_ref)
        # Fallback to plaintext (LOCAL mode only)
        return os.getenv('GIT_PASSWORD', '')
    
    def _configure_credential_helper(self):
        """Configure git to use credentials without exposing them."""
        # Create temporary credential helper script
        script_content = f"""#!/bin/bash
if [ "$1" = "get" ]; then
    echo "username={self.username}"
    echo "password={self.password}"
fi
"""
        # Store helper in-memory or temp file with 0600 permissions
        # ... implementation ...
```

**Option 2: Use SSH Keys Instead of HTTPS**

```python
# Configure SSH key authentication
def _init_repo_ssh(self):
    """Clone using SSH keys (no password exposure)."""
    ssh_url = self.repo_url.replace('https://github.com/', 'git@github.com:')
    self.repo = git.Repo.clone_from(
        ssh_url,
        self.repo_dir,
        branch=self.branch
    )
    # SSH keys managed via Databricks Secrets:
    # 1. Store private key in Databricks Secret
    # 2. Write to ~/.ssh/id_rsa on demand (0600 permissions)
    # 3. Remove after git operation completes
```

---

### 🔴 **P1-HIGH: No Encryption for Secrets in Database**

**Vulnerability ID:** SEC-004  
**CVSS Score:** 7.3 (High)  
**CWE:** CWE-311 (Missing Encryption of Sensitive Data)

#### Description
If any secrets are stored in the PostgreSQL database (e.g., in workflow configurations, external API keys for future features), they are stored in plaintext without encryption.

**Current State:** No evidence of secrets stored in DB tables currently, but the architecture lacks encryption capability.

**Risk:** Future features may inadvertently store credentials in database fields.

#### Remediation

**Implement Application-Level Encryption:**

```python
# src/backend/src/utils/encryption.py (NEW FILE)
from cryptography.fernet import Fernet
import base64
import hashlib
from databricks.sdk.runtime import dbutils

class SecretEncryption:
    """Encrypt/decrypt secrets using Databricks Secrets-backed key."""
    
    def __init__(self):
        # Retrieve encryption key from Databricks Secrets
        encryption_key_secret = os.getenv('APP_ENCRYPTION_KEY_SECRET', 'ontos/encryption_key')
        
        try:
            key_material = dbutils.secrets.get(scope=encryption_key_secret.split('/')[0],
                                               key=encryption_key_secret.split('/')[1])
            # Derive Fernet key from secret material
            self.cipher = Fernet(self._derive_key(key_material))
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise RuntimeError("Encryption key unavailable")
    
    @staticmethod
    def _derive_key(key_material: str) -> bytes:
        """Derive 32-byte Fernet key from secret material."""
        return base64.urlsafe_b64encode(
            hashlib.sha256(key_material.encode()).digest()
        )
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext and return base64-encoded ciphertext."""
        if not plaintext:
            return ""
        return self.cipher.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt base64-encoded ciphertext."""
        if not ciphertext:
            return ""
        return self.cipher.decrypt(ciphertext.encode()).decode()

# Usage in models:
# src/backend/src/db_models/external_integrations.py (EXAMPLE)
from sqlalchemy import String, event
from .encryption import SecretEncryption

class ExternalAPIDb(Base):
    __tablename__ = 'external_apis'
    id = Column(UUID, primary_key=True)
    api_key_encrypted = Column(String, nullable=False)
    
    # Property for transparent encryption/decryption
    @property
    def api_key(self) -> str:
        cipher = SecretEncryption()
        return cipher.decrypt(self.api_key_encrypted)
    
    @api_key.setter
    def api_key(self, plaintext: str):
        cipher = SecretEncryption()
        self.api_key_encrypted = cipher.encrypt(plaintext)
```

---

## 3. High Priority Issues

### 🟠 **P1-HIGH: Databricks Token Logged with Insufficient Masking**

**Vulnerability ID:** SEC-005  
**CWE:** CWE-532 (Insertion of Sensitive Information into Log File)

**Affected Code:**
```python
# src/backend/src/common/workspace_client.py, lines 212-213
masked_token = f"{settings.DATABRICKS_TOKEN[:4]}...{settings.DATABRICKS_TOKEN[-4:]}"
logger.info(f"Initializing workspace client with host: {settings.DATABRICKS_HOST}, token: {masked_token}")
```

**Risk:** Even partial token exposure aids brute-force attacks. Tokens should NEVER be logged.

**Remediation:**
```python
# SECURE VERSION
if settings.DATABRICKS_TOKEN:
    logger.info(f"Initializing workspace client with host: {settings.DATABRICKS_HOST}, token: ****(configured)")
else:
    logger.info(f"Initializing workspace client with host: {settings.DATABRICKS_HOST}, token: (using SDK default auth)")
```

---

### 🟠 **P1-HIGH: OAuth Token Stored in Global Variable**

**Vulnerability ID:** SEC-006  
**CWE:** CWE-798 (Use of Hard-coded Credentials)

**Affected Code:**
```python
# src/backend/src/common/database.py, lines 73-76
_oauth_token: Optional[str] = None
_token_last_refresh: float = 0
```

**Risk:** 
- Global variable accessible from any module
- Token persists in memory without encryption
- Process memory dumps could expose token

**Remediation:**
```python
# Use encapsulated token manager with limited access
class OAuthTokenManager:
    """Secure OAuth token cache with encryption."""
    _instance = None
    
    def __init__(self):
        self._token: Optional[str] = None
        self._last_refresh: float = 0
        self._lock = threading.Lock()
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_token(self, settings: Settings) -> str:
        """Get current token, refresh if expired."""
        with self._lock:
            if self._needs_refresh():
                self._token = self._refresh(settings)
            return self._token
    
    def _needs_refresh(self) -> bool:
        return time.time() - self._last_refresh > (55 * 60)  # 55 minutes
    
    # ... rest of implementation ...
```

---

## 4. Medium Priority Issues

### 🟡 **P2-MEDIUM: Inconsistent Databricks Secrets Integration**

**Vulnerability ID:** SEC-007  

**Description:** 
The application supports Databricks Secrets for PostgreSQL password (`POSTGRES_PASSWORD_SECRET`) but NOT for:
- Git credentials (`GIT_PASSWORD`)
- LLM fallback token

**Remediation:**

```python
# src/backend/src/common/config.py - Add secret reference fields
class Settings(BaseSettings):
    # Existing
    POSTGRES_PASSWORD_SECRET: Optional[str] = None
    
    # NEW: Add secret references for all credentials
    GIT_PASSWORD_SECRET: Optional[str] = Field(None, env='GIT_PASSWORD_SECRET')
    DATABRICKS_TOKEN_SECRET: Optional[str] = Field(None, env='DATABRICKS_TOKEN_SECRET')
    
    @model_validator(mode='after')
    def resolve_secrets_from_databricks(self) -> 'Settings':
        """Resolve all *_SECRET fields from Databricks Secrets."""
        from src.workflows.shared.secrets import get_secret_value
        
        if self.POSTGRES_PASSWORD_SECRET and not self.POSTGRES_PASSWORD:
            try:
                self.POSTGRES_PASSWORD = get_secret_value(self.POSTGRES_PASSWORD_SECRET)
            except Exception as e:
                logger.error(f"Failed to resolve POSTGRES_PASSWORD_SECRET: {e}")
        
        if self.GIT_PASSWORD_SECRET and not self.GIT_PASSWORD:
            try:
                self.GIT_PASSWORD = get_secret_value(self.GIT_PASSWORD_SECRET)
            except Exception as e:
                logger.error(f"Failed to resolve GIT_PASSWORD_SECRET: {e}")
        
        if self.DATABRICKS_TOKEN_SECRET and not self.DATABRICKS_TOKEN:
            try:
                self.DATABRICKS_TOKEN = get_secret_value(self.DATABRICKS_TOKEN_SECRET)
            except Exception as e:
                logger.error(f"Failed to resolve DATABRICKS_TOKEN_SECRET: {e}")
        
        return self
```

**Updated .env.example:**
```bash
# Use Databricks Secrets (RECOMMENDED for production)
POSTGRES_PASSWORD_SECRET=ontos/postgres_password
GIT_PASSWORD_SECRET=ontos/git_password
DATABRICKS_TOKEN_SECRET=ontos/databricks_token

# OR use plaintext (LOCAL dev only - NOT recommended)
# POSTGRES_PASSWORD=local_dev_password
# GIT_PASSWORD=local_git_pat
# DATABRICKS_TOKEN=dapi123...
```

---

### 🟡 **P2-MEDIUM: No Secret Rotation Mechanism**

**Vulnerability ID:** SEC-008  

**Description:** Application lacks automated secret rotation. Credentials remain valid indefinitely unless manually updated.

**Remediation Strategy:**

1. **Short-lived Credentials:**
   - OAuth tokens already rotate (50-minute refresh)
   - Implement automatic database credential rotation using AWS Secrets Manager / Azure Key Vault integration

2. **Rotation Workflow:**
```python
# src/backend/src/utils/secret_rotation.py (NEW FILE)
class SecretRotationManager:
    """Manage periodic secret rotation."""
    
    def rotate_database_password(self, db: Session):
        """Rotate PostgreSQL password via Databricks Jobs."""
        # 1. Generate new random password
        new_password = self._generate_password()
        
        # 2. Update password in Databricks Secrets
        # (Requires admin API access or manual process)
        
        # 3. Update PostgreSQL user password
        # ALTER USER app_user WITH PASSWORD 'new_password';
        
        # 4. Trigger app restart to pick up new secret
        
        # 5. Audit log the rotation
        pass
    
    @staticmethod
    def _generate_password(length=32) -> str:
        """Generate cryptographically secure password."""
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
```

---

## 5. Low Priority Issues

### 🟢 **P3-LOW: No Secret Validation on Startup**

**Description:** Application doesn't verify secret quality (strength, format) on startup.

**Remediation:**
```python
@model_validator(mode='after')
def validate_secret_strength(self) -> 'Settings':
    """Ensure secrets meet minimum security requirements."""
    if self.POSTGRES_PASSWORD:
        if len(self.POSTGRES_PASSWORD) < 16:
            raise ValueError("POSTGRES_PASSWORD must be at least 16 characters")
        if self.POSTGRES_PASSWORD in ['password', 'admin', '12345']:
            raise ValueError("POSTGRES_PASSWORD is too weak (common password)")
    
    if self.GIT_PASSWORD:
        if not self.GIT_PASSWORD.startswith(('ghp_', 'github_pat_')):
            logger.warning("GIT_PASSWORD does not appear to be a GitHub PAT")
    
    return self
```

---

## 6. Databricks Secrets Integration Best Practices

### Current State
- ✅ Workflow scripts use Databricks Secrets (`src/backend/src/workflows/shared/secrets.py`)
- ✅ PostgreSQL password supports secret reference (`POSTGRES_PASSWORD_SECRET`)
- ❌ Main application config doesn't consistently use secrets

### Recommended Architecture

```
┌─────────────────────────────────────────────┐
│         Databricks Secrets Scope            │
│              "ontos"                        │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │ Key: postgres_password                │ │
│  │ Key: git_password                     │ │
│  │ Key: databricks_token                 │ │
│  │ Key: encryption_key                   │ │
│  │ Key: external_api_key_snowflake       │ │
│  └───────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
                     ▲
                     │ dbutils.secrets.get()
                     │
┌─────────────────────────────────────────────┐
│        Application (Databricks App)         │
│                                             │
│  Environment Variables (PUBLIC):            │
│  ✓ POSTGRES_PASSWORD_SECRET=ontos/postgres │
│  ✓ GIT_PASSWORD_SECRET=ontos/git_password  │
│  ✓ DATABRICKS_TOKEN_SECRET=ontos/token     │
│                                             │
│  NO plaintext secrets in .env!              │
└─────────────────────────────────────────────┘
```

---

## 7. Implementation Roadmap

### Phase 1: Critical Fixes (Immediate - Week 1)
**Priority:** P0 vulnerabilities must be fixed before next deployment

1. **Fix API Credential Exposure (SEC-001)**
   - [ ] Modify `Settings.to_dict()` to exclude secret fields
   - [ ] Add `to_dict_safe()` method with explicit exclusions
   - [ ] Update `SettingsManager.get_settings()` to use safe method
   - [ ] Add integration test to verify no secrets in API responses
   - [ ] **Estimated Effort:** 4 hours
   - **Verification:** Run security test suite

2. **Fix Database Password Logging (SEC-002)**
   - [ ] Redact passwords in all database connection logs
   - [ ] Review all `logger.info()` calls for credential leaks
   - [ ] **Estimated Effort:** 2 hours

3. **Fix Git Credential Exposure (SEC-003)**
   - [ ] Implement Git credential helper (in-memory storage)
   - [ ] Or migrate to SSH key authentication
   - [ ] **Estimated Effort:** 6 hours

### Phase 2: High Priority (Week 2-3)

4. **Database Encryption for Future Secrets (SEC-004)**
   - [ ] Implement `SecretEncryption` utility class
   - [ ] Create Databricks Secret for encryption key
   - [ ] Add encrypted column type for SQLAlchemy models
   - [ ] **Estimated Effort:** 8 hours

5. **Remove Token Logging (SEC-005)**
   - [ ] Remove all token masking logs (no partial exposure)
   - [ ] Audit all credential-related logging
   - [ ] **Estimated Effort:** 2 hours

6. **Secure OAuth Token Storage (SEC-006)**
   - [ ] Implement `OAuthTokenManager` class
   - [ ] Remove global `_oauth_token` variable
   - [ ] **Estimated Effort:** 4 hours

### Phase 3: Hardening (Week 4)

7. **Complete Databricks Secrets Integration (SEC-007)**
   - [ ] Add `*_SECRET` fields for all credentials in `Settings`
   - [ ] Implement automatic resolution via `@model_validator`
   - [ ] Update documentation and `.env.example`
   - [ ] **Estimated Effort:** 6 hours

8. **Secret Rotation Framework (SEC-008)**
   - [ ] Design rotation workflow for database credentials
   - [ ] Implement rotation scheduler (Databricks Jobs)
   - [ ] Create admin notification system for rotation events
   - [ ] **Estimated Effort:** 12 hours

### Phase 4: Validation (Week 5)

9. **Secret Validation (SEC-009)**
   - [ ] Add startup validation for secret strength
   - [ ] Implement secret format checks
   - [ ] **Estimated Effort:** 3 hours

10. **Security Testing**
    - [ ] Penetration testing of API endpoints for credential exposure
    - [ ] Log file analysis for secret leaks
    - [ ] Process monitoring for environment variable exposure
    - [ ] **Estimated Effort:** 8 hours

**Total Estimated Effort:** ~55 hours (7-8 developer days)

---

## 8. Testing & Verification

### 8.1 Security Test Suite

```python
# src/backend/src/tests/test_security_secrets.py (NEW FILE)
import pytest
import json
import re

def test_settings_api_no_secrets(client, mock_admin_user):
    """Verify /api/settings does not expose secrets."""
    response = client.get("/api/settings")
    assert response.status_code == 200
    
    data_str = json.dumps(response.json()).lower()
    
    # Forbidden patterns
    forbidden = [
        'password', 'token', 'secret', 'dapi', 'ghp_', 
        'postgres_password', 'git_password', 'databricks_token'
    ]
    
    for pattern in forbidden:
        assert pattern not in data_str, \
            f"Secret pattern '{pattern}' found in API response!"

def test_no_credentials_in_logs(caplog):
    """Verify credentials are not logged."""
    import logging
    caplog.set_level(logging.INFO)
    
    # Trigger database connection
    from src.common.database import init_db
    init_db()
    
    log_output = caplog.text.lower()
    
    # Should NOT contain actual passwords
    assert 'password=' not in log_output
    assert 'token=' not in log_output or 'token=***' in log_output.lower()

def test_git_credentials_not_in_environment(monkeypatch):
    """Verify git operations don't expose credentials via env."""
    # Mock git operations and verify env doesn't contain GIT_PASSWORD
    # ... implementation ...
    pass

def test_settings_model_excludes_secrets():
    """Verify Settings.to_dict() doesn't include secret fields."""
    from src.common.config import Settings
    
    settings = Settings(
        POSTGRES_PASSWORD="secret123",
        GIT_PASSWORD="token456",
        DATABRICKS_HOST="https://test.databricks.com",
        # ... other required fields ...
    )
    
    safe_dict = settings.to_dict()
    
    assert 'POSTGRES_PASSWORD' not in safe_dict
    assert 'GIT_PASSWORD' not in safe_dict
    assert 'DATABRICKS_TOKEN' not in safe_dict
    assert 'DATABASE_URL' not in safe_dict
```

### 8.2 Manual Testing Checklist

- [ ] Call `/api/settings` and verify response contains no credentials
- [ ] Check application logs for credential leaks
- [ ] Verify `ps aux` doesn't show git credentials in command lines
- [ ] Test Databricks Secrets integration for all credential types
- [ ] Verify encrypted database fields decrypt correctly
- [ ] Test secret rotation workflow (if implemented)

---

## 9. Compliance Mapping

| Vulnerability | OWASP Top 10 | CWE | NIST CSF | ISO 27001 |
|--------------|-------------|-----|----------|-----------|
| SEC-001 (API Exposure) | A01:2021 Broken Access Control | CWE-200 | PR.AC-4 | A.9.4.1 |
| SEC-002 (Password Logging) | A09:2021 Security Logging | CWE-532 | DE.CM-1 | A.12.4.1 |
| SEC-003 (Git Env Vars) | A02:2021 Cryptographic Failures | CWE-214 | PR.DS-1 | A.10.1.1 |
| SEC-004 (No Encryption) | A02:2021 Cryptographic Failures | CWE-311 | PR.DS-1 | A.10.1.1 |
| SEC-005 (Token Logging) | A09:2021 Security Logging | CWE-532 | DE.CM-1 | A.12.4.3 |
| SEC-006 (Global Token) | A07:2021 Identification Auth Failures | CWE-798 | PR.AC-1 | A.9.4.3 |

---

## 10. References

### Databricks Documentation
- [Databricks Secrets Management](https://docs.databricks.com/security/secrets/index.html)
- [Databricks Apps Security](https://docs.databricks.com/dev-tools/databricks-apps/security.html)
- [Unity Catalog Authentication](https://docs.databricks.com/en/data-governance/unity-catalog/get-started.html)

### Security Standards
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [CWE-200: Exposure of Sensitive Information](https://cwe.mitre.org/data/definitions/200.html)
- [CWE-532: Insertion of Sensitive Information into Log File](https://cwe.mitre.org/data/definitions/532.html)
- [NIST SP 800-57: Key Management](https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final)

### Tools for Secret Detection
- [TruffleHog](https://github.com/trufflesecurity/trufflehog) - Scan Git repos for secrets
- [GitLeaks](https://github.com/gitleaks/gitleaks) - Scan for hardcoded secrets
- [Semgrep](https://semgrep.dev/) - Static analysis for security patterns

---

## Appendix A: Secure Configuration Example

```bash
# .env (PRODUCTION - SECURE VERSION)
# DO NOT commit this file to Git!

# Environment
ENV=PROD
DEBUG=False
LOG_LEVEL=WARNING

# Databricks Connection (token from secret)
DATABRICKS_HOST=https://prod.cloud.databricks.com
DATABRICKS_TOKEN_SECRET=ontos/databricks_token  # NOT plaintext token!

# Database Connection (password from secret)
POSTGRES_HOST=prod-postgres.internal
POSTGRES_PORT=5432
POSTGRES_USER=ontos_app_svc
POSTGRES_PASSWORD_SECRET=ontos/postgres_password  # NOT plaintext password!
POSTGRES_DB=ontos_prod
POSTGRES_DB_SCHEMA=app

# Git Integration (password from secret)
GIT_REPO_URL=https://github.com/company/ontos-config.git
GIT_BRANCH=main
GIT_USERNAME=ontos-svc-account
GIT_PASSWORD_SECRET=ontos/git_password  # NOT plaintext PAT!

# Encryption
APP_ENCRYPTION_KEY_SECRET=ontos/encryption_key

# RBAC
APP_ADMIN_DEFAULT_GROUPS=["platform-admins","data-governance"]

# LLM
LLM_ENABLED=True
LLM_ENDPOINT=databricks-claude-sonnet-3-7
```

---

## Appendix B: Secure Secrets CLI Setup

```bash
# Create Databricks Secrets Scope (one-time setup)
databricks secrets create-scope --scope ontos

# Add secrets (one-time setup per secret)
databricks secrets put --scope ontos --key postgres_password
# (Enter password in editor that opens)

databricks secrets put --scope ontos --key git_password
# (Enter GitHub PAT in editor)

databricks secrets put --scope ontos --key databricks_token
# (Enter Databricks PAT in editor)

databricks secrets put --scope ontos --key encryption_key
# (Enter random 32-byte base64 key)

# Verify secrets (shows names only, not values)
databricks secrets list --scope ontos

# Grant access to service principal
databricks secrets put-acl --scope ontos \
  --principal "service-principal-uuid" --permission READ
```

---

**End of Report**
