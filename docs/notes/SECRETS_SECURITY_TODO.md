# Secrets Management Security Remediation TODO

**Project:** Ontos (Unity Catalog App)  
**Created:** 2025-10-29  
**Priority:** CRITICAL - Immediate Action Required

---

## 🔴 CRITICAL - Phase 1 (Week 1) - MUST FIX BEFORE NEXT DEPLOYMENT

### [ ] SEC-001: Fix API Credential Exposure (P0-CRITICAL)
**Estimated: 4 hours**

- [ ] Modify `src/backend/src/common/config.py`:
  - [ ] Update `Settings.to_dict()` to exclude secret fields
  - [ ] Add class variable `_SECRET_FIELDS` listing all sensitive field names
  - [ ] Create new method `to_dict_safe()` with explicit exclusions
  
- [ ] Update `src/backend/src/controller/settings_manager.py`:
  - [ ] Line 645: Change `self._settings.to_dict()` to `self._settings.to_dict_safe()`
  
- [ ] Create test `src/backend/tests/test_security_secrets.py`:
  - [ ] Add `test_settings_api_no_secrets()` to verify no credentials in response
  - [ ] Add `test_settings_model_excludes_secrets()` to verify model serialization
  
- [ ] Run verification:
  ```bash
  # Test endpoint manually
  curl http://localhost:8000/api/settings | grep -iE '(password|token|secret)'
  # Should return NO matches
  
  # Run automated tests
  pytest src/backend/tests/test_security_secrets.py -v
  ```

**Acceptance Criteria:**
- `/api/settings` response contains ZERO credential fields
- All tests pass
- Manual curl command returns no sensitive patterns

---

### [ ] SEC-002: Fix Database Password Logging (P0-CRITICAL)
**Estimated: 2 hours**

- [ ] Update `src/backend/src/common/database.py`:
  - [ ] Line 612: Redact password from logged URL
  - [ ] Add URL parsing utility to mask credentials
  - [ ] Example:
    ```python
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(db_url)
    safe_netloc = f"{parsed.username}:***@{parsed.hostname}:{parsed.port}"
    safe_url = parsed._replace(netloc=safe_netloc).geturl()
    logger.info(f"> Database URL: {safe_url}")
    ```

- [ ] Audit all logging statements:
  ```bash
  cd src/backend
  grep -r "logger\.(info|debug|warning)" . | grep -iE "(password|token|secret)" | grep -v ".pyc"
  ```

- [ ] Verify logs after fix:
  - [ ] Start application
  - [ ] Check `/tmp/backend.log` for credential leaks
  - [ ] Search for patterns: `password=`, `token=`, `:***@` (redacted is OK)

**Acceptance Criteria:**
- No plaintext passwords in any log file
- Database URLs show `user:***@host` format

---

### [ ] SEC-003: Fix Git Credential Exposure (P1-HIGH)
**Estimated: 6 hours**

- [ ] Update `src/backend/src/common/config.py`:
  - [ ] Add field: `GIT_PASSWORD_SECRET: Optional[str] = Field(None, env='GIT_PASSWORD_SECRET')`
  - [ ] Add `@model_validator` to resolve secret:
    ```python
    if self.GIT_PASSWORD_SECRET and not self.GIT_PASSWORD:
        from src.workflows.shared.secrets import get_secret_value
        self.GIT_PASSWORD = get_secret_value(self.GIT_PASSWORD_SECRET)
    ```

- [ ] Update `src/backend/src/common/git.py`:
  - [ ] Remove credential passing via `env` parameter (lines 44-47, 55-58, 99-102)
  - [ ] Implement Git credential helper OR migrate to SSH keys
  - [ ] Option 1 (Credential Helper):
    ```python
    def _configure_credential_helper(self):
        # Create in-memory credential helper
        # Set git config credential.helper to custom script
        pass
    ```
  - [ ] Option 2 (SSH - Recommended):
    ```python
    def _init_repo_ssh(self):
        ssh_url = self.repo_url.replace('https://github.com/', 'git@github.com:')
        # Configure SSH key from Databricks Secret
        # Clone using SSH (no password in env)
    ```

- [ ] Update `.env.example`:
  - [ ] Add: `GIT_PASSWORD_SECRET=ontos/git_password`
  - [ ] Add comment: `# Recommended: Use GIT_PASSWORD_SECRET (not GIT_PASSWORD)`

- [ ] Test:
  - [ ] Trigger git operation (push/pull)
  - [ ] Check process list: `ps aux | grep git` → should NOT show password
  - [ ] Check logs → should NOT show password

**Acceptance Criteria:**
- Git operations work without passwords in environment variables
- `ps aux` shows no credentials in git command lines

---

## 🟠 HIGH PRIORITY - Phase 2 (Week 2-3)

### [ ] SEC-004: Database Encryption for Future Secrets (P1-HIGH)
**Estimated: 8 hours**

- [ ] Create `src/backend/src/utils/encryption.py`:
  - [ ] Implement `SecretEncryption` class using `cryptography.fernet`
  - [ ] Retrieve encryption key from Databricks Secret: `ontos/encryption_key`
  - [ ] Implement `encrypt()` and `decrypt()` methods

- [ ] Create Databricks Secret:
  ```bash
  # Generate key
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  
  # Store in Databricks
  databricks secrets put --scope ontos --key encryption_key
  # (Paste generated key)
  ```

- [ ] Update `.env.example`:
  - [ ] Add: `APP_ENCRYPTION_KEY_SECRET=ontos/encryption_key`

- [ ] Add encrypted column support to SQLAlchemy models (for future use):
  ```python
  # Example: src/backend/src/db_models/external_integrations.py
  from src.utils.encryption import SecretEncryption
  
  class ExternalAPIDb(Base):
      api_key_encrypted = Column(String, nullable=False)
      
      @property
      def api_key(self) -> str:
          return SecretEncryption().decrypt(self.api_key_encrypted)
      
      @api_key.setter
      def api_key(self, plaintext: str):
          self.api_key_encrypted = SecretEncryption().encrypt(plaintext)
  ```

**Acceptance Criteria:**
- Encryption utility class works with Databricks Secrets
- Example model demonstrates encrypted field usage
- All tests pass

---

### [ ] SEC-005: Remove Token Logging (P1-HIGH)
**Estimated: 2 hours**

- [ ] Update `src/backend/src/common/workspace_client.py`:
  - [ ] Line 212-213: Remove token masking entirely
  - [ ] Replace with:
    ```python
    token_status = "configured" if settings.DATABRICKS_TOKEN else "using SDK default"
    logger.info(f"Initializing workspace client: {settings.DATABRICKS_HOST}, token: {token_status}")
    ```

- [ ] Audit all token-related logging:
  ```bash
  cd src/backend
  grep -r "DATABRICKS_TOKEN\|oauth_token" . | grep -i "logger\." | grep -v ".pyc"
  ```

**Acceptance Criteria:**
- No token values (even masked) appear in logs
- Logs indicate "token configured" or "token not set" status only

---

### [ ] SEC-006: Secure OAuth Token Storage (P1-HIGH)
**Estimated: 4 hours**

- [ ] Create `src/backend/src/utils/oauth_token_manager.py`:
  - [ ] Implement `OAuthTokenManager` singleton class
  - [ ] Encapsulate `_oauth_token` global variable
  - [ ] Add thread-safe token refresh logic

- [ ] Update `src/backend/src/common/database.py`:
  - [ ] Remove global `_oauth_token` variable (line 74)
  - [ ] Replace all references with `OAuthTokenManager.get_instance().get_token()`

**Acceptance Criteria:**
- OAuth token no longer stored in global variable
- Token refresh works correctly
- All database connections succeed

---

## 🟡 MEDIUM PRIORITY - Phase 3 (Week 4)

### [ ] SEC-007: Complete Databricks Secrets Integration (P2-MEDIUM)
**Estimated: 6 hours**

- [ ] Update `src/backend/src/common/config.py`:
  - [ ] Add fields:
    ```python
    GIT_PASSWORD_SECRET: Optional[str] = None
    DATABRICKS_TOKEN_SECRET: Optional[str] = None
    ```
  
  - [ ] Add `@model_validator(mode='after')` to resolve ALL secrets:
    ```python
    def resolve_secrets_from_databricks(self) -> 'Settings':
        from src.workflows.shared.secrets import get_secret_value
        
        if self.POSTGRES_PASSWORD_SECRET and not self.POSTGRES_PASSWORD:
            self.POSTGRES_PASSWORD = get_secret_value(self.POSTGRES_PASSWORD_SECRET)
        
        if self.GIT_PASSWORD_SECRET and not self.GIT_PASSWORD:
            self.GIT_PASSWORD = get_secret_value(self.GIT_PASSWORD_SECRET)
        
        if self.DATABRICKS_TOKEN_SECRET and not self.DATABRICKS_TOKEN:
            self.DATABRICKS_TOKEN = get_secret_value(self.DATABRICKS_TOKEN_SECRET)
        
        return self
    ```

- [ ] Update `.env.example`:
  - [ ] Document all `*_SECRET` fields
  - [ ] Add production example configuration

- [ ] Create Databricks Secrets:
  ```bash
  databricks secrets put --scope ontos --key git_password
  databricks secrets put --scope ontos --key databricks_token
  ```

**Acceptance Criteria:**
- All credentials support Databricks Secrets references
- Application works with secrets-only configuration (no plaintext)
- Documentation updated

---

### [ ] SEC-008: Secret Rotation Framework (P2-MEDIUM)
**Estimated: 12 hours**

- [ ] Design rotation workflow document:
  - [ ] Define rotation schedule (e.g., every 90 days)
  - [ ] Document manual rotation steps
  - [ ] Design automated rotation workflow

- [ ] Create `src/backend/src/utils/secret_rotation.py`:
  - [ ] Implement `SecretRotationManager` class
  - [ ] Add password generation utility
  - [ ] Add audit logging for rotations

- [ ] Create Databricks Job for rotation:
  - [ ] Define job YAML in `src/backend/src/workflows/rotate_secrets/`
  - [ ] Implement rotation workflow script
  - [ ] Add notification on rotation success/failure

- [ ] Test rotation workflow:
  - [ ] Manually trigger rotation
  - [ ] Verify application picks up new credentials
  - [ ] Verify audit logs record rotation

**Acceptance Criteria:**
- Rotation workflow documented
- Manual rotation process tested
- Automated rotation job created (optional)

---

## 🟢 LOW PRIORITY - Phase 4 (Week 5+)

### [ ] SEC-009: Secret Validation (P3-LOW)
**Estimated: 3 hours**

- [ ] Update `src/backend/src/common/config.py`:
  - [ ] Add `@model_validator` for secret strength checks:
    ```python
    def validate_secret_strength(self) -> 'Settings':
        if self.POSTGRES_PASSWORD:
            if len(self.POSTGRES_PASSWORD) < 16:
                raise ValueError("POSTGRES_PASSWORD must be >= 16 chars")
        
        if self.GIT_PASSWORD:
            if not self.GIT_PASSWORD.startswith(('ghp_', 'github_pat_')):
                logger.warning("GIT_PASSWORD may not be a valid GitHub PAT")
        
        return self
    ```

- [ ] Add startup warnings for weak secrets

**Acceptance Criteria:**
- Application refuses to start with weak passwords
- Warnings logged for suspicious credential formats

---

## Testing & Verification Checklist

### After Each Fix:
- [ ] Run security test suite:
  ```bash
  pytest src/backend/tests/test_security_secrets.py -v
  ```

- [ ] Manual API verification:
  ```bash
  # Should return NO sensitive data
  curl http://localhost:8000/api/settings | jq . | grep -iE '(password|token|secret|dapi)'
  ```

- [ ] Log file audit:
  ```bash
  # Should find ZERO matches
  grep -iE '(password|token|secret)=.*[^*]' /tmp/backend.log
  ```

- [ ] Process inspection:
  ```bash
  # Should NOT show credentials
  ps aux | grep -E '(git|python)' | grep -iE '(password|token)'
  ```

### Final Security Audit (After All Phases):
- [ ] Run static analysis:
  ```bash
  # Install Semgrep
  pip install semgrep
  
  # Scan for secrets
  semgrep --config=p/secrets src/backend/
  ```

- [ ] Run TruffleHog:
  ```bash
  # Install TruffleHog
  pip install trufflehog
  
  # Scan Git history
  trufflehog git file://. --only-verified
  ```

- [ ] Manual penetration testing:
  - [ ] Attempt to extract credentials from API endpoints
  - [ ] Review all log files for credential leaks
  - [ ] Check Git commit history for accidentally committed secrets

---

## Quick Reference Commands

```bash
# Start dev server (after fixes)
cd src/backend
source venv/bin/activate
hatch -e dev run uvicorn src.app:app --reload

# Monitor logs for credential leaks (in another terminal)
tail -f /tmp/backend.log | grep -iE --color '(password|token|secret)'

# Test API endpoint
curl -s http://localhost:8000/api/settings | python -m json.tool

# Check process environment
ps eww $(pgrep -f "python.*app.py") | tr ' ' '\n' | grep -iE '(PASSWORD|TOKEN|SECRET)'

# Run security tests
pytest src/backend/tests/test_security_secrets.py -v --tb=short

# Scan for hardcoded secrets
semgrep --config=p/secrets src/backend/ --exclude "*.pyc" --exclude "tests/"
```

---

## Progress Tracking

- [ ] Phase 1 Complete (CRITICAL - Week 1)
- [ ] Phase 2 Complete (HIGH - Week 2-3)
- [ ] Phase 3 Complete (MEDIUM - Week 4)
- [ ] Phase 4 Complete (LOW - Week 5+)
- [ ] Final Security Audit Passed
- [ ] Documentation Updated
- [ ] Team Training Completed

**Total Estimated Effort:** ~55 hours (7-8 developer days)

---

## Contact for Questions

- **Security Lead:** [Your Security Team]
- **DevOps Lead:** [Your DevOps Team]
- **Databricks Platform:** [Your Platform Team]

---

**Created by:** Claude Security Review  
**Last Updated:** 2025-10-29
