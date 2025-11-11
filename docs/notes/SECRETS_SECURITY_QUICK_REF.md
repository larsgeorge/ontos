# 🔴 SECRETS SECURITY - IMMEDIATE ACTION CARD

**Project:** Ontos (Unity Catalog App)  
**Date:** 2025-10-29  
**Status:** CRITICAL VULNERABILITIES DETECTED

---

## ⚠️ URGENT: Fix Within 48 Hours

### 🔴 SEC-001: API Exposes All Credentials (CRITICAL)

**The Problem:**
```bash
curl http://localhost:8000/api/settings
# Returns: ALL passwords, tokens, secrets in plaintext!
```

**Quick Fix (30 minutes):**

1. Edit `src/backend/src/common/config.py` - Add this method:

```python
def to_dict(self):
    """Return SAFE configuration values (NO SECRETS)."""
    return {
        'job_cluster_id': self.job_cluster_id,
        'sync_enabled': self.sync_enabled,
        'sync_repository': self.sync_repository,
        'enabled_jobs': self.enabled_jobs,
        'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        # NEVER include: DATABASE_URL, POSTGRES_PASSWORD, GIT_PASSWORD, 
        # DATABRICKS_TOKEN, or any credential fields
    }
```

2. Test immediately:
```bash
# Should return ZERO matches:
curl http://localhost:8000/api/settings | grep -iE '(password|token|secret|dapi|ghp_)'
```

3. Deploy emergency hotfix

---

### 🔴 SEC-002: Passwords in Logs (CRITICAL)

**Quick Fix (15 minutes):**

Edit `src/backend/src/common/database.py` around line 612:

```python
# OLD (INSECURE):
logger.info(f"> Database URL: {db_url}")

# NEW (SECURE):
from urllib.parse import urlparse
parsed = urlparse(db_url)
safe_netloc = f"{parsed.username}:***@{parsed.hostname}:{parsed.port}" if parsed.username else parsed.netloc
safe_url = parsed._replace(netloc=safe_netloc).geturl()
logger.info(f"> Database URL: {safe_url}")
```

Test:
```bash
# Should show user:***@host format:
tail -f /tmp/backend.log | grep "Database URL"
```

---

## 📋 Complete Fix Checklist (Today)

- [ ] Fix SEC-001 (API exposure) - 30 min
- [ ] Fix SEC-002 (logging) - 15 min
- [ ] Test both fixes - 15 min
- [ ] Deploy hotfix to production - 30 min
- [ ] Verify in production logs - 15 min
- [ ] Notify security team - 5 min

**Total Time:** ~2 hours

---

## 📊 Full Vulnerability Summary

| ID | Issue | Priority | Fix Time |
|----|-------|----------|----------|
| SEC-001 | API exposes credentials | P0-CRITICAL | 4 hrs |
| SEC-002 | Passwords in logs | P0-CRITICAL | 2 hrs |
| SEC-003 | Git creds in env vars | P1-HIGH | 6 hrs |
| SEC-004 | No DB encryption | P1-HIGH | 8 hrs |
| SEC-005 | Token logging | P1-HIGH | 2 hrs |
| SEC-006 | OAuth token insecure | P1-HIGH | 4 hrs |
| SEC-007 | Incomplete secrets integration | P2-MEDIUM | 6 hrs |
| SEC-008 | No rotation | P2-MEDIUM | 12 hrs |
| SEC-009 | No validation | P3-LOW | 3 hrs |

**Total Remediation:** ~47 hours (6 developer days over 4 weeks)

---

## 🔍 Quick Verification Commands

```bash
# 1. Check API response for secrets (should be ZERO matches):
curl -s http://localhost:8000/api/settings | grep -iEo '(password|token|secret|dapi|ghp_)[:=][^,}"]*'

# 2. Check logs for plaintext credentials (should be ZERO matches):
grep -iE '(password|token)=[^*]' /tmp/backend.log | grep -v "password=\*\*\*"

# 3. Check process list for git credentials (should be ZERO matches):
ps aux | grep git | grep -iE '(password|token)='

# 4. Run security test suite:
pytest src/backend/tests/test_security_secrets.py -v
```

---

## 📚 Full Documentation

1. **Detailed Analysis** (60 pages):  
   `SECRETS_MANAGEMENT_SECURITY_ANALYSIS.md`

2. **Step-by-Step TODO** (20 pages):  
   `SECRETS_SECURITY_TODO.md`

3. **Executive Summary** (10 pages):  
   `SECRETS_SECURITY_SUMMARY.md`

4. **This Quick Reference**:  
   `SECRETS_SECURITY_QUICK_REF.md`

---

## 🚨 Incident Response (If Breach Suspected)

1. **Immediately rotate ALL credentials:**
   ```bash
   # PostgreSQL
   ALTER USER app_user WITH PASSWORD 'new_random_password';
   
   # GitHub PAT
   # → Go to GitHub Settings → Developer Settings → Revoke & Create New
   
   # Databricks Token
   # → Go to Databricks User Settings → Access Tokens → Revoke & Create New
   ```

2. **Update Databricks Secrets:**
   ```bash
   databricks secrets put --scope ontos --key postgres_password
   databricks secrets put --scope ontos --key git_password
   databricks secrets put --scope ontos --key databricks_token
   ```

3. **Restart application** to pick up new secrets

4. **Audit access logs** for suspicious activity

5. **Notify security team** immediately

---

## 📞 Contacts

- **Security Team:** [security@yourcompany.com]
- **DevOps On-Call:** [devops-oncall@yourcompany.com]
- **Databricks Support:** [support@databricks.com]

---

## 🎯 Success Criteria (After Fixes)

✅ **All checks must pass:**

1. API endpoint returns ZERO credential fields
2. Log files contain ZERO plaintext passwords
3. Process list shows ZERO credentials in git commands
4. All security tests pass (`pytest test_security_secrets.py`)
5. Static analysis shows ZERO high-severity findings (`semgrep --config=p/secrets`)
6. Code review approved by security team
7. Penetration test shows no credential extraction possible

---

**REMEMBER: Security is not optional. Fix SEC-001 and SEC-002 TODAY.**

---

**Document Version:** 1.0  
**Last Updated:** 2025-10-29  
**Next Review:** After Phase 1 completion (1 week)
