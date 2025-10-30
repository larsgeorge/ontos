# DQX Profiling OAuth Migration Summary

## Overview
Migrated the DQX profiling workflow from password-based authentication to OAuth authentication for Lakebase Postgres access.

## Changes Made

### 1. Workflow Definition (`src/backend/src/workflows/dqx_profile_datasets/dqx_profile_datasets.yaml`)

**Removed Parameters:**
- `postgres_user` - No longer needed (OAuth uses service principal)
- `postgres_password_secret` - No longer needed (OAuth generates tokens dynamically)

**Remaining Parameters:**
- `contract_id` - Data contract identifier
- `schema_names` - JSON array of schemas to profile
- `profile_run_id` - Profiling run identifier
- `lakebase_instance_name` - Lakebase instance name for OAuth (e.g., "ontos")
- `postgres_host` - Lakebase Postgres host
- `postgres_db` - Database name
- `postgres_port` - Database port (default: 5432)
- `postgres_schema` - Database schema (default: public)

### 2. Python Script (`src/backend/src/workflows/dqx_profile_datasets/dqx_profile_datasets.py`)

**Added Functions:**
- `get_oauth_token(ws_client, instance_name)` - Generates OAuth token via Databricks SDK

**Removed Functions:**
- `_parse_secret_ref()` - No longer needed (password-based auth removed)
- `get_secret_value()` - No longer needed (password-based auth removed)
- `extract_instance_name()` - No longer needed (instance name now passed as parameter)

**Simplified Functions:**
- `build_db_url()` - Now OAuth-only, simplified parameters
  - Removed: `user`, `password_secret` parameters
  - Added: `instance_name`, `ws_client` parameters (required)
  - Returns: `(connection_url, auth_user)` tuple
  
- `create_engine_from_params()` - Now OAuth-only
  - Removed: `user`, `password_secret` parameters
  - Added: `instance_name`, `ws_client` parameters (required)

**Updated main():**
- Initializes `WorkspaceClient` early in the flow
- Added `--lakebase_instance_name` argument (required) - the actual instance name for OAuth
- Removed `--postgres_user` and `--postgres_password_secret` arguments
- Passes `instance_name` and `ws_client` to database connection functions
- **Fixed exit codes:** Now properly exits with `sys.exit(1)` on errors instead of `return`
  - This ensures Databricks marks failed jobs as "Failed" instead of "Succeeded"

### 3. API Route (`src/backend/src/routes/data_contracts_routes.py`)

**Updated job_params:**
Added to job parameters:
- `lakebase_instance_name` - from `settings.LAKEBASE_INSTANCE_NAME`

Removed from job parameters:
- `postgres_user`
- `postgres_password_secret`

### 4. Documentation (`docs/DQX_PROFILING_IMPLEMENTATION_SUMMARY.md`)

**Updated sections:**
- Background Workflow description - Now mentions OAuth only
- Key Features - Changed "Authentication Flexibility" to "OAuth Authentication"
- Installation & Setup - Simplified authentication section

## OAuth Authentication Flow

1. **Workflow starts** → Databricks job runs Python script
2. **Initialize WorkspaceClient** → Connects to Databricks workspace
3. **Use instance name** → Takes instance name from job parameter (e.g., "ontos")
4. **Generate OAuth credentials** → Calls `ws_client.database.generate_database_credential(instance_names=["ontos"])`
5. **Connect to database** → Uses service principal username + OAuth token
6. **Profile tables** → Workflow continues normally

**Important:** The `lakebase_instance_name` parameter should match the instance name configured in your environment (e.g., "ontos"), NOT the hostname UUID.

## Example Log Output

```
Job Parameters:
  Contract ID: 07ca5b26-278d-421c-9e3a-fbad275ab3a9
  Schema names: ['table_a']
  Profile run ID: eb8117c4-1792-4d40-b19f-004206d94612
  Lakebase instance name: ontos

Initializing Databricks Workspace Client...
✓ Workspace client initialized

Connecting to database...
  POSTGRES_HOST: instance-4e8da72e-cd0e-4553-8888-d10d709ac735.database.cloud.databricks.com
  POSTGRES_DB: app_ontos
  POSTGRES_PORT: 5432
  POSTGRES_DB_SCHEMA: app_ontos
  LAKEBASE_INSTANCE_NAME: ontos
  Authentication: OAuth (Lakebase Postgres)
  Generating OAuth token for instance: ontos
  Service Principal: 150d07c5-159c-4656-ab3a-8db778804b6b
  ✓ Successfully generated OAuth token
  Using OAuth user: 150d07c5-159c-4656-ab3a-8db778804b6b
  Connection URL (token redacted): postgresql+psycopg2://150d07c5-159c-4656-ab3a-8db778804b6b:****@instance-4e8da72e-cd0e-4553-8888-d10d709ac735.database.cloud.databricks.com:5432/app_ontos?options=-csearch_path%3Dapp_ontos
✓ Database connection established successfully
```

## Configuration Requirements

Before deploying, ensure that `LAKEBASE_INSTANCE_NAME` is set in your environment:

```bash
# In your .env or environment configuration
LAKEBASE_INSTANCE_NAME=ontos  # or whatever your instance name is
```

This environment variable should already be configured if you're using Lakebase Postgres with OAuth elsewhere in your application.

## Deployment Steps

To deploy these changes:

1. **Ensure environment variable is set**
   - Verify `LAKEBASE_INSTANCE_NAME` is configured in your backend environment
   - This should match the instance name you use for Lakebase (e.g., "ontos")

2. **Update workflow in Databricks**
   - Go to Settings > Jobs & Workflows
   - Find the `dqx_profile_datasets` workflow
   - Delete or update the existing installation
   - Re-install the workflow from the updated YAML and Python files

3. **No backend restart required** (if variable already exists)
   - API changes are backward compatible
   - Frontend needs no changes
   - If adding `LAKEBASE_INSTANCE_NAME` for the first time, restart backend

4. **Test the workflow**
   - Navigate to a Data Contract
   - Click "Profile with DQX"
   - Select schemas and start profiling
   - Monitor job logs for OAuth authentication with correct instance name

## Bug Fixes

### 1. Exit Code Handling
**Problem:** The workflow was using `return` instead of `sys.exit(1)` when errors occurred. This caused Python to exit with code 0 (success), making Databricks mark failed jobs as "Succeeded".

**Solution:** Changed all error paths to use `sys.exit(1)`:
- Workspace client initialization failure → `sys.exit(1)`
- Database connection failure → `sys.exit(1)`
- Main workflow exception handler → `sys.exit(1)`

**Impact:** Failed jobs will now properly show as "Failed" in Databricks, making it easier to monitor and debug workflow issues.

### 2. Instance Name Resolution
**Problem:** The code was trying to extract the instance name from the Lakebase Postgres hostname (e.g., `instance-4e8da72e-cd0e-4553-8888-d10d709ac735.database.cloud.databricks.com`), but the OAuth API requires the configured instance name (e.g., "ontos"), not the UUID. This caused "Database instance is not found" errors.

**Solution:** Added `lakebase_instance_name` as a required job parameter:
- Backend passes `settings.LAKEBASE_INSTANCE_NAME` to the workflow
- Workflow accepts `--lakebase_instance_name` argument
- OAuth token generation uses the actual instance name instead of parsing the hostname

**Impact:** OAuth authentication now works correctly with Lakebase Postgres instances.

### 3. DQX Return Type Compatibility
**Problem:** The DQX library returns quality check suggestions as dictionaries, but the code was trying to access them as objects with attributes (e.g., `check.name`). This caused `AttributeError: 'dict' object has no attribute 'name'`.

**Solution:** Updated `insert_suggestion()` and property extraction to handle both dict and object formats:
- Check if the DQX profile is a dict or object using `isinstance()`
- Use dict access (`dq_profile.get("name")`) for dicts
- Use attribute access (`getattr(dq_profile, "name")`) for objects
- Added debug logging to track which format is being processed

**Impact:** Quality check suggestions are now properly inserted into the database regardless of DQX version or return format.

## Benefits

✅ **No secrets management** - OAuth tokens generated dynamically
✅ **Better security** - Tokens are short-lived and per-request
✅ **Service principal identity** - Clear audit trail
✅ **Simplified configuration** - Fewer parameters to manage
✅ **Native Databricks integration** - Uses platform OAuth capabilities
✅ **Proper error reporting** - Failed jobs now correctly marked as failed

## Files Modified

- ✅ `src/backend/src/workflows/dqx_profile_datasets/dqx_profile_datasets.yaml`
- ✅ `src/backend/src/workflows/dqx_profile_datasets/dqx_profile_datasets.py`
- ✅ `src/backend/src/routes/data_contracts_routes.py`
- ✅ `docs/DQX_PROFILING_IMPLEMENTATION_SUMMARY.md`
- ✅ `docs/DQX_OAUTH_MIGRATION_SUMMARY.md` (new)

## Migration Complete ✅

The DQX profiling workflow now uses OAuth exclusively for Lakebase Postgres authentication.

