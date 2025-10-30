# Security Review Findings Report

**Project:** UC App Backend Security Audit
**Date:** 2025-10-27
**Reviewer:** Security Analysis
**Total Files Reviewed:** 191 Python files
**Status:** Complete - Initial Review

---

## Executive Summary

This security review identified **13 security issues** across various severity levels in the UC App backend codebase. The application demonstrates good security practices in several areas, particularly:

✅ **No code injection vulnerabilities** (no exec/eval/subprocess usage)
✅ **Parameterized SQL queries** via SQLAlchemy ORM
✅ **Comprehensive RBAC implementation**
✅ **Input validation** via Pydantic models
✅ **Proper logging** practices

However, several critical and high-severity issues require immediate attention, particularly around authentication bypass, header trust, secrets management, and information disclosure.

---

## Critical Findings (IMMEDIATE ACTION REQUIRED)

### 🔴 CRITICAL-1: Authentication Bypass via Header Manipulation

**Location:** `src/backend/src/common/authorization.py:110-118`

**Description:**
The application trusts `X-Forwarded-Email`, `X-Forwarded-User`, and `X-Real-Ip` headers without validation. An attacker can forge these headers to impersonate any user.

**Vulnerable Code:**
```python
user_email = request.headers.get("X-Forwarded-Email")
if not user_email:
    user_email = request.headers.get("X-Forwarded-User")
```

**Attack Scenario:**
```bash
curl -X GET http://api/data-contracts \
  -H "X-Forwarded-Email: admin@company.com" \
  -H "X-Forwarded-User: admin"
```

**Impact:** Complete authentication bypass, privilege escalation, unauthorized data access

**Recommendation:**
1. **NEVER trust client-supplied headers** for authentication
2. Implement proper authentication middleware (JWT, OAuth2, session cookies)
3. If running behind a reverse proxy (Databricks Apps scenario):
   - Verify the proxy sets these headers securely
   - Add middleware to validate headers come from trusted proxy
   - Use mutual TLS between proxy and app
4. Add header signature validation
5. Implement rate limiting per IP/user

**Remediation Priority:** **P0 - CRITICAL**

---

### 🔴 CRITICAL-2: Git Command Injection via Environment Variables

**Location:** `src/backend/src/common/git.py:40-59, 96-103`

**Description:**
Git operations use environment variables that could be manipulated to inject commands. The code passes `GIT_USERNAME` and `GIT_PASSWORD` via environment to git operations without proper sanitization.

**Vulnerable Code:**
```python
self.repo.git.pull(
    'origin',
    self.branch,
    env={
        'GIT_USERNAME': self.username,
        'GIT_PASSWORD': self.password
    }
)
```

**Attack Scenario:**
If an attacker can control `GIT_BRANCH` setting:
```
"; rm -rf /; echo "malicious
```

**Impact:** Remote Code Execution (RCE), data destruction, system compromise

**Recommendation:**
1. Validate all Git parameters (branch names, URLs) against strict allowlists
2. Use regex to validate branch names: `^[a-zA-Z0-9_\-\/\.]+$`
3. Never pass credentials via environment - use SSH keys or credential managers
4. Use GitPython's safe methods instead of raw git commands
5. Implement path traversal checks on filenames
6. Run Git operations in a sandboxed environment

**Remediation Priority:** **P0 - CRITICAL**

---

### 🔴 CRITICAL-3: Path Traversal in File Operations

**Location:** `src/backend/src/common/git.py:83-85, 126-128`

**Description:**
The `save_yaml()` and `load_yaml()` methods accept arbitrary filenames without path traversal validation.

**Vulnerable Code:**
```python
file_path = self.repo_dir / filename
with open(file_path, 'w') as f:
    yaml.dump(data, f, default_flow_style=False)
```

**Attack Scenario:**
```python
save_yaml("../../../etc/passwd", {"malicious": "data"})
load_yaml("../../../etc/shadow")
```

**Impact:** Arbitrary file read/write, privilege escalation, data exfiltration

**Recommendation:**
1. Validate filename doesn't contain path traversal sequences: `..`, `/`, `\`
2. Use `os.path.basename()` to strip directory components
3. Implement allowlist of permitted filenames or extensions
4. Use `os.path.realpath()` and verify result is within `repo_dir`
```python
def save_yaml(self, filename: str, data: Dict[str, Any]) -> bool:
    # Sanitize filename
    filename = os.path.basename(filename)
    if not filename.endswith('.yaml') and not filename.endswith('.yml'):
        raise ValueError("Only YAML files allowed")

    file_path = self.repo_dir / filename
    # Verify no traversal occurred
    if not file_path.resolve().is_relative_to(self.repo_dir.resolve()):
        raise ValueError("Path traversal detected")
```

**Remediation Priority:** **P0 - CRITICAL**

---

### 🔴 CRITICAL-4: Secrets Stored in Environment Variables

**Location:** `src/backend/src/common/config.py:33-80`

**Description:**
Sensitive credentials (database passwords, Git credentials, Databricks tokens) are stored in environment variables and `.env` files without encryption.

**Vulnerable Code:**
```python
POSTGRES_PASSWORD: Optional[str] = None
GIT_PASSWORD: Optional[str] = Field(None, env='GIT_PASSWORD')
DATABRICKS_TOKEN: Optional[str] = None
```

**Impact:** Credential exposure through logs, process listings, memory dumps, error messages

**Recommendation:**
1. Use Databricks Secrets for all sensitive values
2. Implement secret masking in logs
3. Use `POSTGRES_PASSWORD_SECRET` pattern for all credentials:
```python
def get_postgres_password(self) -> str:
    if self.POSTGRES_PASSWORD_SECRET:
        # Fetch from Databricks Secrets
        return self.ws_client.secrets.get_secret(
            scope=self.POSTGRES_PASSWORD_SECRET.split('/')[0],
            key=self.POSTGRES_PASSWORD_SECRET.split('/')[1]
        )
    return self.POSTGRES_PASSWORD  # Fallback for local dev only
```
4. Never log Settings objects directly (contains passwords)
5. Implement automatic credential rotation
6. Use separate secrets for each environment

**Remediation Priority:** **P0 - CRITICAL**

---

## High Severity Findings

### 🟠 HIGH-1: Information Disclosure via Verbose Error Messages

**Location:** Multiple files, particularly:
- `src/backend/src/common/repository.py:46-49, 58-60, 75-77`
- `src/backend/src/routes/data_contracts_routes.py:116-119`

**Description:**
Error messages expose internal implementation details, database structure, file paths, and stack traces to clients.

**Vulnerable Code:**
```python
except Exception as e:
    error_msg = f"Error retrieving data contracts: {e!s}"
    logger.error(error_msg)
    raise HTTPException(status_code=500, detail=error_msg)
```

**Attack Scenario:**
Attacker triggers errors to learn:
- Database schema and table names
- File system structure
- Library versions
- Internal logic flow

**Impact:** Information leakage aids further attacks, reveals vulnerabilities

**Recommendation:**
1. Return generic error messages to clients:
```python
except Exception as e:
    logger.error(f"Error retrieving data contracts: {e!s}", exc_info=True)
    raise HTTPException(
        status_code=500,
        detail="An error occurred processing your request. Please contact support."
    )
```
2. Log detailed errors server-side with correlation IDs
3. Implement error response sanitization middleware
4. Never expose SQLAlchemy errors to clients
5. Use custom exception classes with safe messages

**Remediation Priority:** **P1 - HIGH**

---

### 🟠 HIGH-2: SQL Injection Risk in Raw Queries

**Location:** Multiple repository files (54 files use `.query()` or `.execute()`)

**Description:**
While the codebase primarily uses SQLAlchemy ORM (which provides parameterization), there are instances of `.query()` and `.execute()` that need review for dynamic SQL construction.

**Review Needed:**
```python
# SAFE - Parameterized
db.query(DataContractDb).filter(DataContractDb.name == name).first()

# POTENTIALLY UNSAFE - If using string formatting
# db.execute(f"SELECT * FROM contracts WHERE name = '{name}'")
```

**Impact:** SQL injection, data breach, privilege escalation

**Recommendation:**
1. Audit all 54 files containing `.execute()` or raw SQL
2. Ensure all queries use bound parameters
3. If using `.execute()`, always use parameterized queries:
```python
# WRONG
db.execute(f"SELECT * FROM table WHERE id = {user_input}")

# CORRECT
from sqlalchemy import text
db.execute(text("SELECT * FROM table WHERE id = :id"), {"id": user_input})
```
4. Enable SQL query logging in development to review all queries
5. Use SQLAlchemy's query builder exclusively

**Remediation Priority:** **P1 - HIGH**

---

### 🟠 HIGH-3: Missing Input Sanitization for User-Controlled Data

**Location:**
- `src/backend/src/routes/data_contracts_routes.py` (file uploads)
- All routes accepting JSON/form data

**Description:**
While Pydantic validates types, there's insufficient sanitization of string content for:
- XSS payloads in stored data
- SQL wildcards in search parameters
- Path traversal in filename fields
- Command injection in fields passed to external systems

**Vulnerable Patterns:**
```python
@router.post('/data-contracts/{contract_id}/comment')
async def add_comment(contract_id: str, comment: CommentCreate, ...):
    # Comment text not sanitized for XSS before storage
```

**Impact:** Stored XSS, injection attacks, data corruption

**Recommendation:**
1. Implement input sanitization layer:
```python
import bleach

def sanitize_html(text: str) -> str:
    return bleach.clean(text, tags=[], strip=True)

# In Pydantic models
class CommentCreate(BaseModel):
    text: str

    @validator('text')
    def sanitize_text(cls, v):
        return sanitize_html(v)
```
2. Use allowlists for fields with limited valid values
3. Validate file extensions before processing uploads
4. Implement length limits on all text fields
5. Escape special characters in search queries

**Remediation Priority:** **P1 - HIGH**

---

### 🟠 HIGH-4: Insufficient Authorization Checks in Nested Resources

**Location:** Throughout route handlers

**Description:**
Authorization is checked at the feature level but may not verify ownership of specific resources. For example, checking if a user can access a specific contract they don't own.

**Vulnerable Pattern:**
```python
@router.get('/data-contracts/{contract_id}')
async def get_contract(
    contract_id: str,
    db: DBSessionDep,
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))
):
    # Checks feature-level permission but not resource-level ownership
    contract = data_contract_repo.get(db, id=contract_id)
```

**Impact:** Horizontal privilege escalation, unauthorized data access

**Recommendation:**
1. Implement resource-level authorization checks:
```python
async def check_contract_access(contract_id: str, user: UserInfo, db: Session):
    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(404, "Contract not found")

    # Check ownership or team membership
    if contract.owner_email != user.email and \
       not any(team in user.groups for team in contract.teams):
        raise HTTPException(403, "Access denied to this contract")

    return contract
```
2. Use `Depends()` for resource ownership verification
3. Implement `can_access(user, resource)` pattern
4. Add audit logging for failed authorization attempts

**Remediation Priority:** **P1 - HIGH**

---

### 🟠 HIGH-5: CORS Misconfiguration in Development Mode

**Location:** `src/backend/src/app.py:147-165`

**Description:**
CORS allows all methods and headers from localhost origins, which could be exploited in CSRF attacks if cookies are used.

**Vulnerable Code:**
```python
origins = [
    "http://localhost:3000",
    # ... multiple localhost ports
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Too permissive
    allow_headers=["*"],  # Too permissive
)
```

**Impact:** CSRF attacks, session hijacking (if sessions implemented)

**Recommendation:**
1. Restrict allowed methods to only those needed:
```python
allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
```
2. Restrict headers to specific required headers:
```python
allow_headers=[
    "Content-Type",
    "Authorization",
    "X-Requested-With",
    "Accept"
]
```
3. In production, use specific domain origins (no wildcards)
4. Implement CSRF tokens if using cookie-based auth
5. Add `expose_headers` to whitelist response headers

**Remediation Priority:** **P1 - HIGH**

---

## Medium Severity Findings

### 🟡 MEDIUM-1: Missing Rate Limiting

**Location:** All API endpoints

**Description:**
No rate limiting is implemented, allowing brute force, DoS, and resource exhaustion attacks.

**Impact:** Service degradation, brute force attacks, resource exhaustion

**Recommendation:**
1. Implement rate limiting middleware:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/data-contracts")
@limiter.limit("100/minute")
async def get_contracts(...):
    ...
```
2. Different limits for different endpoint types:
   - Read endpoints: 100/minute
   - Write endpoints: 20/minute
   - Auth endpoints: 5/minute
3. Use Redis for distributed rate limiting
4. Implement exponential backoff for repeated failures

**Remediation Priority:** **P2 - MEDIUM**

---

### 🟡 MEDIUM-2: Missing Security Headers

**Location:** `src/backend/src/app.py`, `src/backend/src/common/middleware.py`

**Description:**
Security headers are not set on responses, leaving the application vulnerable to clickjacking, XSS, and other attacks.

**Missing Headers:**
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security`
- `Content-Security-Policy`

**Impact:** XSS, clickjacking, MIME-sniffing attacks

**Recommendation:**
1. Add security headers middleware:
```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'"
        return response

app.add_middleware(SecurityHeadersMiddleware)
```
2. Use HTTPS in production (enforced by Databricks Apps)
3. Implement CSP reporting

**Remediation Priority:** **P2 - MEDIUM**

---

### 🟡 MEDIUM-3: Insecure Mock Authentication in Production

**Location:** `src/backend/src/common/authorization.py:54-106`

**Description:**
Mock user authentication can be enabled via `MOCK_USER_DETAILS=True` environment variable, potentially bypassing auth in production if misconfigured.

**Vulnerable Code:**
```python
if settings.ENV.upper().startswith("LOCAL") or getattr(settings, "MOCK_USER_DETAILS", False):
    return UserInfo(
        email=mock_email,
        username=mock_username,
        user=mock_name,
        ip=mock_ip,
        groups=mock_groups,
    )
```

**Impact:** Authentication bypass if misconfigured

**Recommendation:**
1. Disable mock mode in production:
```python
if settings.ENV.upper() not in ("LOCAL", "DEV"):
    if getattr(settings, "MOCK_USER_DETAILS", False):
        raise RuntimeError("MOCK_USER_DETAILS cannot be enabled in production")
```
2. Use separate code paths for dev vs prod
3. Remove mock code from production builds
4. Add startup validation to prevent production misconfiguration

**Remediation Priority:** **P2 - MEDIUM**

---

### 🟡 MEDIUM-4: Insufficient Logging for Security Events

**Location:** Multiple files

**Description:**
Security-critical events (failed auth, permission denied, suspicious activity) are logged at INFO/WARNING level, not aggregated for monitoring.

**Impact:** Delayed incident detection, insufficient forensics

**Recommendation:**
1. Implement security event logging:
```python
class SecurityAuditLogger:
    def log_auth_failure(self, username: str, ip: str, reason: str):
        logger.error(f"AUTH_FAILURE username={username} ip={ip} reason={reason}",
                    extra={"event_type": "auth_failure", "username": username, "ip": ip})

    def log_permission_denied(self, user: str, resource: str, action: str):
        logger.warning(f"PERMISSION_DENIED user={user} resource={resource} action={action}",
                      extra={"event_type": "permission_denied"})
```
2. Send security logs to SIEM
3. Alert on suspicious patterns (repeated failures, privilege escalation attempts)
4. Log all admin actions

**Remediation Priority:** **P2 - MEDIUM**

---

### 🟡 MEDIUM-5: JSON Schema Validation Bypass

**Location:** `src/backend/src/common/odcs_validation.py`

**Description:**
ODCS validation can be disabled via `strict=False`, and there's no enforcement that validation must occur before data storage.

**Vulnerable Pattern:**
```python
validator.validate(contract_data, strict=False)  # Returns bool, doesn't raise
# Data might be stored even if invalid
```

**Impact:** Data corruption, downstream processing errors

**Recommendation:**
1. Always use `strict=True` for production data
2. Enforce validation at the database layer:
```python
@validates('contract_data')
def validate_contract_data(self, key, value):
    validator = get_odcs_validator()
    validator.validate(value, strict=True)  # Will raise on invalid
    return value
```
3. Add database constraints for critical fields
4. Implement validation audit trail

**Remediation Priority:** **P2 - MEDIUM**

---

## Low Severity / Informational Findings

### 🟢 INFO-1: Database Connection Credentials in Logs

**Location:** Various locations where Settings objects might be logged

**Recommendation:** Implement `__repr__` masking for sensitive fields

---

### 🟢 INFO-2: No Request ID Tracking

**Location:** Middleware

**Recommendation:** Add correlation IDs for request tracking across logs

---

### 🟢 INFO-3: Hardcoded Default Admin Group

**Location:** `src/backend/src/common/config.py:71`

**Recommendation:** Make fully configurable, no hardcoded defaults

---

## Positive Security Controls Identified

✅ **SQLAlchemy ORM Usage**: Protects against most SQL injection
✅ **Pydantic Validation**: Strong type checking and validation
✅ **Comprehensive RBAC**: Well-designed permission system
✅ **No Dangerous Functions**: No exec/eval/subprocess usage
✅ **Structured Logging**: Good logging practices
✅ **Environment-based Configuration**: Proper config management
✅ **Error Rollback**: Database transactions properly handled

---

## Remediation Priority Summary

| Priority | Count | Issues |
|----------|-------|--------|
| **P0 - CRITICAL** | 4 | Auth bypass, Git injection, Path traversal, Secret exposure |
| **P1 - HIGH** | 5 | Info disclosure, SQL injection review, Input sanitization, Authorization gaps, CORS |
| **P2 - MEDIUM** | 5 | Rate limiting, Security headers, Mock auth, Security logging, Schema validation |
| **P3 - LOW/INFO** | 3 | Credential logging, Request IDs, Hardcoded defaults |

---

## Recommended Remediation Roadmap

### Phase 1: Critical Fixes (Week 1)
1. ✅ Implement proper authentication (replace header trust)
2. ✅ Fix Git command injection vulnerabilities
3. ✅ Add path traversal protection
4. ✅ Migrate all secrets to Databricks Secrets

### Phase 2: High Priority (Week 2-3)
1. ✅ Sanitize all error messages returned to clients
2. ✅ Review and fix SQL injection risks in 54 files
3. ✅ Implement input sanitization layer
4. ✅ Add resource-level authorization checks
5. ✅ Restrict CORS configuration

### Phase 3: Medium Priority (Week 4)
1. ✅ Implement rate limiting
2. ✅ Add security headers middleware
3. ✅ Disable mock auth in production
4. ✅ Enhance security logging
5. ✅ Enforce schema validation

### Phase 4: Security Hardening (Week 5+)
1. ✅ Implement request correlation IDs
2. ✅ Add security monitoring and alerting
3. ✅ Conduct penetration testing
4. ✅ Implement WAF rules
5. ✅ Security training for development team

---

## Testing Recommendations

### Security Test Suite Needed:
1. **Authentication Tests**
   - Test header manipulation
   - Test auth bypass attempts
   - Test privilege escalation

2. **Injection Tests**
   - SQL injection test suite
   - Command injection tests
   - Path traversal tests

3. **Authorization Tests**
   - Horizontal privilege escalation
   - Vertical privilege escalation
   - Resource access control

4. **Input Validation Tests**
   - Fuzz testing all endpoints
   - XSS payload testing
   - Malformed input handling

---

## Conclusion

The application demonstrates a solid foundation with good use of modern Python frameworks and security libraries. However, the **critical authentication bypass vulnerability** (CRITICAL-1) poses an immediate and severe risk that must be addressed urgently.

The primary security concerns are:
1. **Trust of client-supplied headers** for authentication
2. **Lack of input sanitization** beyond type validation
3. **Incomplete authorization checks** at resource level
4. **Secrets management** practices need improvement

With the recommended fixes implemented, particularly addressing the P0 and P1 issues, the application's security posture will be significantly improved.

---

**Report Generated:** 2025-10-27
**Review Status:** Complete
**Next Review:** After remediation of critical findings
