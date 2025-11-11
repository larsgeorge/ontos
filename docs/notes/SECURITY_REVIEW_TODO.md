# Security Review Todo List

**Project:** UC App Backend Security Audit
**Date Started:** 2025-10-27
**Total Python Files:** 191
**Status:** In Progress

---

## Overview

This security review focuses on identifying critical vulnerabilities in the backend codebase, including:
- Input validation and injection vulnerabilities (SQL, code, command)
- Authentication and authorization flaws
- Information disclosure through verbose errors or data exposure
- API security issues
- File system vulnerabilities
- Secrets management
- Third-party dependency risks

---

## Review Categories

### 1. Entry Points & API Routes (HIGH PRIORITY)
**Status:** Pending

#### Routes to Review
- [ ] `routes/data_contracts_routes.py` - Data contract CRUD operations
- [ ] `routes/data_products_routes.py` - Data product CRUD operations
- [ ] `routes/access_requests_routes.py` - Access request handling
- [ ] `routes/security_routes.py` - Security features endpoints
- [ ] `routes/security_features_routes.py` - Additional security endpoints
- [ ] `routes/settings_routes.py` - Settings management (HIGH RISK)
- [ ] `routes/workspace_routes.py` - Workspace operations
- [ ] `routes/metadata_routes.py` - Metadata operations
- [ ] `routes/tags_routes.py` - Tag operations
- [ ] `routes/search_routes.py` - Search functionality
- [ ] `routes/catalog_commander_routes.py` - File operations (HIGH RISK)
- [ ] `routes/entitlements_routes.py` - Permission management
- [ ] `routes/compliance_routes.py` - Compliance checks
- [ ] `routes/master_data_management_routes.py` - MDM operations
- [ ] `routes/notifications_routes.py` - Notification handling
- [ ] `routes/change_log_routes.py` - Change tracking
- [ ] `routes/business_glossary_routes.py` - Glossary management
- [ ] `routes/comments_routes.py` - Comment handling
- [ ] `routes/data_asset_reviews_routes.py` - Review workflow
- [ ] `routes/estate_manager_routes.py` - Estate management
- [ ] `routes/semantic_links_routes.py` - Semantic linking
- [ ] `routes/semantic_models_routes.py` - Model management

**Key Security Checks:**
- Request parameter validation
- SQL injection prevention
- Command injection risks
- Path traversal vulnerabilities
- CORS configuration
- Rate limiting implementation
- Input sanitization

---

### 2. Authentication & Authorization (CRITICAL)
**Status:** Pending

- [ ] `common/authorization.py` - Permission checking logic
- [ ] `controller/authorization_manager.py` - Authorization management
- [ ] `controller/users_manager.py` - User management and group checking
- [ ] `common/deps.py` - Dependency injection for auth
- [ ] Review token/session handling mechanisms
- [ ] Check for privilege escalation vectors
- [ ] Verify group membership validation
- [ ] Review RBAC implementation
- [ ] Check for broken access control

**Key Security Checks:**
- Authentication bypass vulnerabilities
- Authorization logic flaws
- Session management security
- Token validation and expiration
- Permission checking completeness
- Horizontal/vertical privilege escalation

---

### 3. Database Operations (HIGH PRIORITY)
**Status:** Pending

#### Repository Layer
- [ ] `repositories/data_contracts_repository.py`
- [ ] `repositories/data_products_repository.py`
- [ ] `repositories/data_asset_reviews_repository.py`
- [ ] `repositories/metadata_repository.py`
- [ ] `repositories/tags_repository.py`
- [ ] `repositories/compliance_repository.py`
- [ ] `repositories/comments_repository.py`
- [ ] `repositories/semantic_models_repository.py`
- [ ] `repositories/semantic_links_repository.py`
- [ ] `repositories/data_domain_repository.py`
- [ ] `repositories/change_log_repository.py`
- [ ] `repositories/notification_repository.py`
- [ ] `repositories/workflow_installations_repository.py`
- [ ] `repositories/workflow_job_runs_repository.py`

#### Base Classes
- [ ] `common/repository.py` - Base CRUD repository (CRITICAL)
- [ ] `common/database.py` - Database connection and session management

**Key Security Checks:**
- SQL injection via raw queries
- Parameterized query usage
- ORM misuse leading to injection
- Mass assignment vulnerabilities
- Insufficient input validation before DB operations
- Transaction handling and ACID properties

---

### 4. Business Logic & Controllers (HIGH PRIORITY)
**Status:** Pending

- [ ] `controller/data_contracts_manager.py` - Contract validation and ODCS parsing
- [ ] `controller/data_products_manager.py` - Product management
- [ ] `controller/settings_manager.py` - Settings and config (HIGH RISK)
- [ ] `controller/catalog_commander_manager.py` - File operations (HIGH RISK)
- [ ] `controller/entitlements_manager.py` - Permission assignments
- [ ] `controller/security_features_manager.py` - Security controls
- [ ] `controller/compliance_manager.py` - Compliance validation
- [ ] `controller/master_data_management_manager.py` - MDM integration
- [ ] `controller/notifications_manager.py` - Notification delivery
- [ ] `controller/search_manager.py` - Search indexing and queries
- [ ] `controller/metadata_manager.py` - Metadata extraction
- [ ] `controller/tags_manager.py` - Tag management
- [ ] `controller/comments_manager.py` - Comment handling
- [ ] `controller/change_log_manager.py` - Change tracking

**Key Security Checks:**
- Business logic bypass
- Race conditions
- State management issues
- Insecure deserialization
- TOCTOU (Time-of-check to time-of-use) vulnerabilities

---

### 5. Data Validation & Serialization (MEDIUM PRIORITY)
**Status:** Pending

#### Pydantic Models (API Layer)
- [ ] `models/data_contracts.py` - Contract data models
- [ ] `models/data_products.py` - Product data models
- [ ] `models/settings.py` - Settings models
- [ ] `models/users.py` - User models
- [ ] `models/entitlements.py` - Permission models
- [ ] `models/security_features.py` - Security models
- [ ] `models/compliance.py` - Compliance models
- [ ] `models/metadata.py` - Metadata models
- [ ] `models/tags.py` - Tag models
- [ ] `models/comments.py` - Comment models
- [ ] `models/notifications.py` - Notification models
- [ ] `models/semantic_models.py` - Semantic model definitions
- [ ] `models/semantic_links.py` - Semantic link definitions

#### Validation Logic
- [ ] `common/odcs_validation.py` - ODCS schema validation (HIGH RISK)

**Key Security Checks:**
- Insufficient input validation
- Type coercion vulnerabilities
- Regex DoS (ReDoS)
- XML/JSON parsing vulnerabilities
- Schema validation bypass
- Mass assignment via extra fields

---

### 6. File System Operations (CRITICAL)
**Status:** Pending

- [ ] `common/git.py` - Git operations (CRITICAL - command injection risk)
- [ ] `controller/catalog_commander_manager.py` - File copy/move operations
- [ ] Any file upload/download endpoints
- [ ] Configuration file reading/writing
- [ ] Log file operations

**Key Security Checks:**
- Path traversal (../ sequences)
- Arbitrary file read/write
- Command injection via file operations
- Insecure file permissions
- Symbolic link attacks
- Directory traversal

---

### 7. External Integrations (HIGH PRIORITY)
**Status:** Pending

- [ ] `utils/workspace_client.py` - Databricks SDK client setup
- [ ] `controller/master_data_management_manager.py` - Zingg.ai integration
- [ ] Git repository integration (in settings)
- [ ] Workflow/job execution

**Key Security Checks:**
- API credential exposure
- Insecure SDK usage
- SSRF (Server-Side Request Forgery)
- Unsafe API parameter passing
- Webhook vulnerabilities

---

### 8. Secrets & Configuration Management (CRITICAL)
**Status:** Pending

- [ ] `common/config.py` - Configuration loading
- [ ] `.env` file usage
- [ ] Database connection strings
- [ ] API keys and tokens
- [ ] Databricks credentials

**Key Security Checks:**
- Secrets in code or version control
- Insecure secret storage
- Environment variable leakage
- Configuration injection
- Credential rotation mechanisms

---

### 9. Error Handling & Logging (MEDIUM PRIORITY)
**Status:** Pending

- [ ] `common/logging.py` - Logging configuration
- [ ] `common/errors.py` - Error handling
- [ ] `common/audit_logging.py` - Audit logging
- [ ] Exception handling in routes and controllers

**Key Security Checks:**
- Verbose error messages exposing stack traces
- Information leakage in logs
- Sensitive data in log files
- Insufficient error handling
- Log injection vulnerabilities

---

### 10. Workflow & Background Jobs (MEDIUM PRIORITY)
**Status:** Pending

- [ ] `workflows/copy_table/copy_table.py`
- [ ] `workflows/data_contract_validation/data_contract_validation.py`
- [ ] `workflows/stage_dataset_events/stage_dataset_events.py`
- [ ] Job execution and parameter handling

**Key Security Checks:**
- Command injection in job parameters
- Insecure deserialization of job data
- Race conditions in background tasks
- Job hijacking vulnerabilities

---

### 11. Application Initialization & Middleware (HIGH PRIORITY)
**Status:** Pending

- [ ] `app.py` - FastAPI application setup
- [ ] `common/middleware.py` - Custom middleware
- [ ] `utils/startup_tasks.py` - Initialization logic
- [ ] `common/app_state.py` - Application state management

**Key Security Checks:**
- CORS misconfigurations
- Missing security headers
- Insecure middleware ordering
- State pollution vulnerabilities
- Startup script injection

---

### 12. Search & Query Functionality (MEDIUM PRIORITY)
**Status:** Pending

- [ ] `common/search.py` - Search implementation
- [ ] `common/search_interfaces.py` - Search interfaces
- [ ] `common/search_registry.py` - Search registry
- [ ] `controller/search_manager.py` - Search manager

**Key Security Checks:**
- Search query injection
- Information disclosure via search
- Access control bypass in search results
- ReDoS in search patterns

---

### 13. Database Models & Schema (LOW PRIORITY)
**Status:** Pending

- [ ] Review all `db_models/*.py` for sensitive data handling
- [ ] Check for secure defaults
- [ ] Verify proper indexing for security-critical queries

---

### 14. Test Files (INFORMATIONAL)
**Status:** Pending

- [ ] Review test files for security test coverage
- [ ] Identify missing security test cases
- [ ] Check for credentials or secrets in test files

---

## High-Risk Areas Summary

### 🔴 CRITICAL (Review First)
1. Authentication & Authorization (`common/authorization.py`, `controller/authorization_manager.py`)
2. File System Operations (`common/git.py`, catalog commander)
3. Settings Management (`controller/settings_manager.py`)
4. Database Base Repository (`common/repository.py`)
5. Secrets Management (`common/config.py`)
6. Input Validation (`common/odcs_validation.py`)

### 🟡 HIGH (Review Second)
1. All API Routes (user input entry points)
2. All Repository classes (SQL injection potential)
3. All Controller classes (business logic flaws)
4. External integrations (Databricks SDK, Git)
5. Application initialization (`app.py`, middleware)

### 🟢 MEDIUM (Review Third)
1. Pydantic models (validation logic)
2. Error handling and logging
3. Search functionality
4. Workflow jobs

---

## Review Progress Tracking

**Total Items:** ~150+
**Completed:** 0
**In Progress:** 0
**Critical Issues Found:** 0
**High Issues Found:** 0
**Medium Issues Found:** 0
**Low Issues Found:** 0

---

## Notes

- Focus on user-controlled input flows
- Check for proper authorization at every endpoint
- Verify all database queries use parameterization
- Look for command execution with user input
- Check for information leakage in responses
- Verify CORS and security headers
- Check for proper secrets management

---

## Next Steps

1. Start with CRITICAL items in order
2. Document findings in `SECURITY_REVIEW_FINDINGS.md`
3. Create POC exploits for verified vulnerabilities
4. Prioritize remediation recommendations
5. Create GitHub issues for each finding
