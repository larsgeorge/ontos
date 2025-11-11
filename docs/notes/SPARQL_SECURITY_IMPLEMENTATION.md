# SPARQL Security Implementation

## Overview

This document describes the security measures implemented to protect the SPARQL query endpoint from injection attacks and abuse.

## Security Issue

The SPARQL endpoint at `/api/semantic-models/query` was previously vulnerable to:

- **SPARQL Injection**: Attackers could execute arbitrary queries
- **No Authentication**: Anyone could query the semantic graph
- **No Authorization**: No permission checks were enforced
- **Resource Exhaustion**: Complex queries could cause denial of service
- **Information Disclosure**: Unrestricted data access
- **No Audit Trail**: Query attempts were not logged

## Implemented Security Measures

### 1. Query Validation (`src/backend/src/common/sparql_validator.py`)

A comprehensive SPARQL query validator that enforces:

#### Read-Only Queries
- ✅ **Allowed**: `SELECT`, `ASK`, `DESCRIBE`, `CONSTRUCT`
- ❌ **Blocked**: `INSERT`, `DELETE`, `UPDATE`, `DROP`, `CLEAR`, `CREATE`, `LOAD`, `COPY`, `MOVE`, `ADD`

#### Query Limits
- **Max Query Length**: 10,000 characters
- **Max Triple Patterns**: 100 patterns
- **Max UNION Clauses**: 20
- **Max OPTIONAL Clauses**: 30

#### Features
- Case-insensitive keyword detection
- Support for PREFIX declarations
- Complexity estimation
- Query sanitization for logging

### 2. Manager-Level Security (`src/backend/src/controller/semantic_models_manager.py`)

Enhanced the `query()` method with:

#### Validation
```python
def query(self, sparql: str, max_results: int = 1000, timeout_seconds: int = 30)
```

- Validates all queries before execution
- Rejects invalid queries with descriptive errors

#### Timeout Protection
- **Default timeout**: 30 seconds
- Uses Unix signals (SIGALRM) on supported platforms
- Prevents long-running queries from blocking the server

#### Result Limiting
- **Max results**: 1,000 rows by default
- Prevents memory exhaustion
- Logs when results are truncated

#### Comprehensive Logging
- Logs all query attempts (sanitized)
- Logs validation failures
- Logs execution time and result counts
- Uses appropriate log levels (INFO, WARNING, ERROR)

### 3. Route-Level Security (`src/backend/src/routes/semantic_models_routes.py`)

Protected the endpoint with:

#### Authentication
```python
current_user: CurrentUserDep
```
- Requires valid user session
- Extracts user identity from request

#### Authorization
```python
_: bool = Depends(PermissionChecker("semantic-models", FeatureAccessLevel.READ_WRITE))
```
- Requires `READ_WRITE` permission on `semantic-models` feature
- Integrates with existing RBAC system

#### Audit Logging
```python
audit_manager: AuditManagerDep
db: DBSessionDep
```
- Logs successful queries with user, IP address, timestamp, query length, result count
- Logs failed queries with error details and success=False flag
- Logs validation failures
- Creates comprehensive audit trail using `log_action()` method

### 4. Testing (`src/backend/tests/test_sparql_security.py`)

Comprehensive test suite covering:

- ✅ Valid queries (SELECT, ASK, DESCRIBE, CONSTRUCT)
- ✅ Queries with PREFIX declarations
- ✅ Queries with FILTER, OPTIONAL, UNION
- ❌ Forbidden keywords (INSERT, DELETE, etc.)
- ❌ Empty queries
- ❌ Queries without valid type
- ❌ Excessively long queries
- ❌ Too many UNION/OPTIONAL clauses
- ❌ Overly complex queries

**Test Results**: All 13 tests passing ✓

## Security Improvements Summary

| Aspect | Before | After |
|--------|--------|-------|
| Authentication | ❌ None | ✅ Required |
| Authorization | ❌ None | ✅ Permission-based |
| Query Validation | ❌ None | ✅ Comprehensive |
| Write Operations | ❌ Possible | ✅ Blocked |
| Query Timeout | ❌ None | ✅ 30 seconds |
| Result Limiting | ❌ Unlimited | ✅ 1,000 rows |
| Audit Logging | ❌ Minimal | ✅ Comprehensive |
| Injection Protection | ❌ Vulnerable | ✅ Protected |

## Usage Example

### Valid Query
```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?concept ?label
WHERE {
    ?concept a skos:Concept .
    ?concept rdfs:label ?label .
}
LIMIT 50
```

**Result**: ✅ Accepted and executed

### Invalid Query (Injection Attempt)
```sparql
INSERT DATA {
    <http://attacker.com/malicious> <http://evil.com/prop> "data" .
}
```

**Result**: ❌ Rejected with error: "Query contains forbidden keyword: INSERT"

## Configuration

### Adjustable Limits

In `src/backend/src/common/sparql_validator.py`:
```python
MAX_QUERY_LENGTH = 10000      # Maximum characters
MAX_TRIPLE_PATTERNS = 100     # Maximum complexity
MAX_UNIONS = 20               # Maximum UNION clauses
MAX_OPTIONALS = 30            # Maximum OPTIONAL clauses
```

In route call:
```python
manager.query(sparql, max_results=1000, timeout_seconds=30)
```

## Monitoring

### Logs to Monitor

1. **Warning Level**: Query attempts
   ```
   SPARQL query execution attempt by user 'user@example.com': query_length=245
   ```

2. **Info Level**: Successful execution
   ```
   SPARQL query executed successfully by 'user@example.com': 42 results returned
   ```

3. **Error Level**: Validation/execution failures
   ```
   SPARQL query validation/execution failed for user 'user@example.com': Query contains forbidden keyword: DELETE
   ```

### Audit Trail

Check audit logs for:
- `feature="semantic-models"`
- `action="SPARQL_QUERY"` (success)
- `action="SPARQL_QUERY_FAILED"` (validation failure)
- `action="SPARQL_QUERY_ERROR"` (execution error)

## Threat Model

### Threats Mitigated

1. ✅ **SPARQL Injection**: Validation blocks malicious queries
2. ✅ **Unauthorized Access**: Authentication and authorization required
3. ✅ **Data Modification**: Write operations blocked
4. ✅ **Denial of Service**: Timeouts and complexity limits
5. ✅ **Information Disclosure**: Authorization controls access
6. ✅ **Lack of Accountability**: Comprehensive audit logging

### Remaining Considerations

1. **Rate Limiting**: Consider adding rate limiting per user (e.g., 10 queries/minute)
2. **Query Result Caching**: Cache common queries to reduce load
3. **Advanced Complexity Analysis**: More sophisticated query cost estimation
4. **Windows Support**: Timeout protection only works on Unix-like systems

## References

- OWASP SPARQL Injection: https://owasp.org/www-community/attacks/SPARQL_Injection
- W3C SPARQL 1.1 Query Language: https://www.w3.org/TR/sparql11-query/
- RDFLib Security: https://rdflib.readthedocs.io/

## Maintenance

### Regular Reviews

1. Monitor audit logs for suspicious patterns
2. Review and adjust limits based on legitimate use cases
3. Update validator rules as new attack vectors are discovered
4. Keep RDFLib library updated for security patches

### Testing

Run security tests regularly:
```bash
cd src/backend
python -m pytest tests/test_sparql_security.py -v
```

## Contact

For security concerns or to report vulnerabilities, contact the security team.

---

**Status**: ✅ Implemented and Tested  
**Date**: 2025-10-29  
**Priority**: HIGH - Security Critical

