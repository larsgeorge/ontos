# SQL Injection Security Fix - Unity Catalog Operations

## Summary

This document describes the security improvements made to prevent SQL injection vulnerabilities in Unity Catalog operations across the application. The solution includes both security hardening and code modularization for reusability.

## Problem

The original implementation used raw SQL DDL statements with string interpolation to create tables, making the code vulnerable to SQL injection attacks:

```python
# VULNERABLE CODE (removed)
ws.sql.execute(f"CREATE TABLE IF NOT EXISTS {full_name} ({columns_sql})")
```

This approach concatenated user-provided input directly into SQL statements, allowing potential attackers to:
- Inject malicious SQL commands
- Bypass access controls
- Manipulate or exfiltrate data
- Disrupt database operations

## Solution

We implemented a comprehensive security solution with three phases:

### Phase 1: Security Hardening

Replaced vulnerable SQL DDL with secure Databricks SDK APIs, implementing key security components.

### Phase 2: Code Modularization

Refactored all security utilities into a shared module (`src/backend/src/common/unity_catalog_utils.py`) for reuse across routes and managers.

### Phase 3: PostgreSQL Security

Extended security protections to PostgreSQL database initialization, preventing SQL injection in Lakebase operations.

## Security Components

### 1. Unity Catalog Input Sanitization (`sanitize_uc_identifier`)

A validation function that ensures Unity Catalog identifiers (catalog, schema, table, and column names) meet strict requirements:

- Must start with a letter or underscore
- Can only contain letters, digits, and underscores
- Cannot exceed 255 characters
- Raises `ValueError` for invalid input

```python
def sanitize_uc_identifier(identifier: str, max_length: int = 255) -> str:
    """Sanitize and validate a Unity Catalog identifier."""
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
        raise ValueError("Invalid identifier")
    return identifier
```

### 1b. PostgreSQL Input Sanitization (`sanitize_postgres_identifier`)

A validation function that ensures PostgreSQL identifiers (database, schema, user names) meet strict requirements:

- Must start with a letter or underscore
- Can only contain letters, digits, underscores, and dollar signs
- Cannot exceed 63 characters (PostgreSQL NAMEDATALEN limit)
- Cannot be a PostgreSQL reserved keyword (e.g., `select`, `table`, `user`)
- Raises `ValueError` for invalid input

```python
def sanitize_postgres_identifier(identifier: str, max_length: int = 63) -> str:
    """Sanitize and validate a PostgreSQL identifier."""
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_$]*$', identifier):
        raise ValueError("Invalid PostgreSQL identifier")
    if identifier.lower() in POSTGRES_RESERVED:
        raise ValueError("Cannot use reserved keyword")
    return identifier
```

This function protects against SQL injection in PostgreSQL DDL operations that cannot use parameterized queries (like `CREATE DATABASE`).

### 2. Type Mapping (`_map_logical_type_to_column_type`)

Maps logical data types to Databricks `ColumnTypeName` enum values, ensuring type safety:

```python
def _map_logical_type_to_column_type(logical_type: str) -> ColumnTypeName:
    """Map logical type to Databricks ColumnTypeName enum."""
    # Returns proper enum values like ColumnTypeName.STRING, ColumnTypeName.LONG, etc.
```

### 3. Safe Table Creation (`_create_table_safe`)

A wrapper function that uses the Databricks SDK's type-safe API instead of raw SQL:

```python
def _create_table_safe(ws, catalog_name, schema_name, table_name, columns):
    """Create table using Databricks SDK API (safe from SQL injection)."""
    # Sanitizes all identifiers
    # Builds ColumnInfo objects with proper types
    # Uses ws.tables.create() API
```

## Changes Made

### Modified Endpoints

1. **`/api/self-service/create`** (line ~492-500)
   - Replaced SQL DDL with `_create_table_safe()`
   - Added identifier sanitization for catalog, schema, and table names
   
2. **`/api/self-service/deploy/{contract_id}`** (line ~622-647)
   - Replaced SQL DDL with `_create_table_safe()`
   - Added identifier sanitization for all parsed names

### SDK API Usage

Now using the official Databricks SDK APIs:

```python
from databricks.sdk.service.catalog import (
    ColumnInfo,
    ColumnTypeName,
    TableType,
    DataSourceFormat,
)

# Safe API call
ws.tables.create(
    name=table_name,
    catalog_name=catalog_name,
    schema_name=schema_name,
    table_type=TableType.MANAGED,
    data_source_format=DataSourceFormat.DELTA,
    columns=column_infos,
    storage_location=None
)
```

## Security Benefits

1. **SQL Injection Prevention**: No user input is concatenated into SQL strings
2. **Type Safety**: Using enum types instead of string literals
3. **Input Validation**: All identifiers validated before use
4. **API-Level Protection**: Databricks SDK handles escaping and parameterization
5. **Clear Error Messages**: Invalid input is rejected with descriptive errors

## Testing Recommendations

1. **Positive Tests**: Verify legitimate table/schema/catalog creation still works
2. **Negative Tests**: Attempt SQL injection payloads and verify they're rejected:
   - Table names with SQL keywords: `users; DROP TABLE important_data--`
   - Special characters: `test'; DELETE FROM users--`
   - Multi-statement attacks: `valid_name; GRANT ALL PRIVILEGES`
3. **Edge Cases**: Test maximum length, special valid characters (underscores)
4. **Integration Tests**: End-to-end tests with real Unity Catalog

## Migration Notes

- **Backward Compatible**: Behavior unchanged for valid inputs
- **Error Handling**: Invalid identifiers now return HTTP 400 with descriptive messages
- **Performance**: SDK API may have slight overhead vs raw SQL, but negligible
- **Idempotency**: Table creation still checks for existence before creating

## Shared Module: `unity_catalog_utils.py`

To promote code reuse and consistency, all Unity Catalog security utilities have been consolidated into a shared module.

### Module Location
`src/backend/src/common/unity_catalog_utils.py`

### Exported Functions

1. **`sanitize_uc_identifier(identifier, max_length=255)`**
   - Validates Unity Catalog identifier names
   - Raises `ValueError` for invalid identifiers
   - Used for all catalog, schema, table, and column names

2. **`map_logical_type_to_column_type(logical_type)`**
   - Maps logical types to Databricks `ColumnTypeName` enum
   - Returns type-safe enum values
   - Defaults to `STRING` for unknown types

3. **`ensure_catalog_exists(ws, catalog_name, comment=None, properties=None)`**
   - Idempotent catalog creation
   - Returns sanitized catalog name
   - Handles existence checks gracefully

4. **`ensure_schema_exists(ws, catalog_name, schema_name, comment=None, properties=None)`**
   - Idempotent schema creation
   - Returns full schema name (catalog.schema)
   - Validates both catalog and schema names

5. **`create_table_safe(ws, catalog_name, schema_name, table_name, columns, ...)`**
   - Secure table creation using SDK APIs
   - Sanitizes all identifiers
   - Builds type-safe column definitions
   - Checks for table existence before creating
   - Supports custom table types, formats, and storage locations

6. **`ensure_catalog_and_schema_exist(ws, catalog_name, schema_name, ...)`**
   - Convenience function for parent creation
   - Ensures catalog exists before creating schema
   - Returns tuple of (catalog_name, full_schema_name)

### Usage Example

```python
from src.common.unity_catalog_utils import (
    sanitize_uc_identifier,
    ensure_catalog_and_schema_exist,
    create_table_safe
)

# Ensure parents exist
catalog_name, full_schema_name = ensure_catalog_and_schema_exist(
    ws=workspace_client,
    catalog_name="my_catalog",
    schema_name="my_schema"
)

# Create table with validated columns
columns = [
    {'name': 'id', 'logicalType': 'integer', 'required': True},
    {'name': 'name', 'logicalType': 'string'},
    {'name': 'created_at', 'logicalType': 'timestamp'}
]

table_full_name = create_table_safe(
    ws=workspace_client,
    catalog_name=catalog_name,
    schema_name="my_schema",
    table_name="my_table",
    columns=columns,
    comment="Example table"
)
```

### Integration Points

The shared module is currently used in:

1. **`src/backend/src/routes/self_service_routes.py`**
   - `POST /api/self-service/create` - Creates catalogs, schemas, tables
   - `POST /api/self-service/deploy/{contract_id}` - Deploys data contracts

2. **`src/backend/src/common/database.py`**
   - `ensure_catalog_schema_exists()` - Unity Catalog initialization
   - `ensure_database_and_schema_exist()` - PostgreSQL Lakebase initialization
   - Creates required catalog/schema for application metadata storage
   - Uses secure, idempotent operations during startup
   - Validates all PostgreSQL identifiers before use

Future integration opportunities:
- Data products deployment
- Workflow table creation
- Any manager that creates Unity Catalog objects

## PostgreSQL Security Enhancements

### Problem: PostgreSQL DDL with String Interpolation

The `ensure_database_and_schema_exist()` function used string interpolation for PostgreSQL DDL:

```python
# VULNERABLE - String interpolation in SQL
result = conn.execute(text(
    f"SELECT 1 FROM pg_database WHERE datname = '{target_db}'"
))
conn.execute(text(f'CREATE DATABASE "{target_db}"'))
conn.execute(text(f'CREATE SCHEMA "{target_schema}"'))
```

While these values come from configuration (not direct user input), this is still vulnerable if:
- Configuration files are compromised
- Environment variables are manipulated
- Service principal names contain malicious characters

### Solution: Validation + Parameterized Queries

**1. Identifier Validation**

All PostgreSQL identifiers are validated before use:

```python
# Validate identifiers from configuration
target_db = sanitize_postgres_identifier(settings.POSTGRES_DB)
target_schema = sanitize_postgres_identifier(settings.POSTGRES_DB_SCHEMA)
username = sanitize_postgres_identifier(username)
```

**2. Parameterized SELECT Queries**

```python
# BEFORE: String interpolation (vulnerable)
result = conn.execute(text(
    f"SELECT 1 FROM pg_database WHERE datname = '{target_db}'"
))

# AFTER: Parameterized query (secure)
result = conn.execute(
    text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
    {"dbname": target_db}
)
```

**3. Validated DDL Statements**

For DDL statements that cannot be parameterized (like `CREATE DATABASE`), validation provides protection:

```python
# Safe after validation - identifiers validated against strict rules
conn.execute(text(f'CREATE DATABASE "{target_db}"'))
conn.execute(text(f'CREATE SCHEMA "{target_schema}"'))
conn.execute(text(
    f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{target_schema}" '
    f'GRANT ALL ON TABLES TO "{username}"'
))
```

### Defense in Depth

This approach provides multiple layers of security:

1. **Configuration validation** - Identifiers validated at startup
2. **Parameterized queries** - Used wherever possible
3. **Reserved keyword checking** - Prevents use of SQL keywords
4. **Length limits** - Enforces PostgreSQL NAMEDATALEN limit (63 chars)
5. **Character restrictions** - Only safe characters allowed

### Benefits

- ✅ **Protects against compromised configuration** - Invalid values rejected at startup
- ✅ **Prevents reserved keyword injection** - Keywords like `DROP`, `SELECT` blocked
- ✅ **Clear error messages** - Detailed validation errors for debugging
- ✅ **No behavior changes** - Fully backward compatible with valid configurations
- ✅ **Performance** - Validation overhead is negligible (startup only)

## References

### Unity Catalog
- [Databricks SDK - Schemas API](https://databricks-sdk-py.readthedocs.io/en/latest/workspace/catalog/schemas.html)
- [Databricks SDK - Tables API](https://databricks-sdk-py.readthedocs.io/en/latest/workspace/catalog/tables.html)

### PostgreSQL
- [PostgreSQL SQL Keywords](https://www.postgresql.org/docs/current/sql-keywords-appendix.html)
- [PostgreSQL Identifiers](https://www.postgresql.org/docs/current/sql-syntax-lexical.html#SQL-SYNTAX-IDENTIFIERS)
- [psycopg2 SQL Composition](https://www.psycopg.org/docs/sql.html)

### Security
- [OWASP SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)

## Dates

- **Phase 1 - Security Hardening**: October 29, 2025
- **Phase 2 - Code Modularization**: October 29, 2025
- **Phase 3 - PostgreSQL Security**: October 29, 2025

