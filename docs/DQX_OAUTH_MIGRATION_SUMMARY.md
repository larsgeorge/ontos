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
- `postgres_host` - Lakebase Postgres host
- `postgres_db` - Database name
- `postgres_port` - Database port (default: 5432)
- `postgres_schema` - Database schema (default: public)

### 2. Python Script (`src/backend/src/workflows/dqx_profile_datasets/dqx_profile_datasets.py`)

**Added Functions:**
- `extract_instance_name(postgres_host)` - Extracts instance name from Lakebase host
- `get_oauth_token(ws_client, instance_name)` - Generates OAuth token via Databricks SDK

**Removed Functions:**
- `_parse_secret_ref()` - No longer needed
- `get_secret_value()` - No longer needed

**Simplified Functions:**
- `build_db_url()` - Now OAuth-only, simplified parameters
  - Removed: `user`, `password_secret` parameters
  - Added: `ws_client` parameter (required)
  - Returns: `(connection_url, auth_user)` tuple
  
- `create_engine_from_params()` - Now OAuth-only
  - Removed: `user`, `password_secret` parameters
  - Added: `ws_client` parameter (required)

**Updated main():**
- Initializes `WorkspaceClient` early in the flow
- Removed `--postgres_user` and `--postgres_password_secret` arguments
- Passes `ws_client` to database connection functions

### 3. API Route (`src/backend/src/routes/data_contracts_routes.py`)

**Updated job_params:**
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
3. **Extract instance name** → Parses Lakebase Postgres host URL
4. **Generate OAuth credentials** → Calls `ws_client.database.generate_database_credential()`
5. **Connect to database** → Uses service principal username + OAuth token
6. **Profile tables** → Workflow continues normally

## Example Log Output

```
Initializing Databricks Workspace Client...
✓ Workspace client initialized

Connecting to database...
  POSTGRES_HOST: instance-4e8da72e-cd0e-4553-8888-d10d709ac735.database.cloud.databricks.com
  POSTGRES_DB: app_ontos
  POSTGRES_PORT: 5432
  POSTGRES_DB_SCHEMA: app_ontos
  Authentication: OAuth (Lakebase Postgres)
  Instance name: instance-4e8da72e-cd0e-4553-8888-d10d709ac735
  Generating OAuth token for instance: instance-4e8da72e-cd0e-4553-8888-d10d709ac735
  Service Principal: <service-principal-name>
  ✓ Successfully generated OAuth token
  Using OAuth user: <service-principal-name>
  Connection URL (token redacted): postgresql+psycopg2://<user>:****@<host>:5432/app_ontos?options=-csearch_path%3Dapp_ontos
✓ Database connection established successfully
```

## Deployment Steps

To deploy these changes:

1. **Update workflow in Databricks**
   - Go to Settings > Jobs & Workflows
   - Find the `dqx_profile_datasets` workflow
   - Delete or update the existing installation
   - Re-install the workflow from the updated YAML and Python files

2. **No backend restart required**
   - API changes are backward compatible
   - Frontend needs no changes

3. **Test the workflow**
   - Navigate to a Data Contract
   - Click "Profile with DQX"
   - Select schemas and start profiling
   - Monitor job logs for OAuth authentication

## Benefits

✅ **No secrets management** - OAuth tokens generated dynamically
✅ **Better security** - Tokens are short-lived and per-request
✅ **Service principal identity** - Clear audit trail
✅ **Simplified configuration** - Fewer parameters to manage
✅ **Native Databricks integration** - Uses platform OAuth capabilities

## Files Modified

- ✅ `src/backend/src/workflows/dqx_profile_datasets/dqx_profile_datasets.yaml`
- ✅ `src/backend/src/workflows/dqx_profile_datasets/dqx_profile_datasets.py`
- ✅ `src/backend/src/routes/data_contracts_routes.py`
- ✅ `docs/DQX_PROFILING_IMPLEMENTATION_SUMMARY.md`
- ✅ `docs/DQX_OAUTH_MIGRATION_SUMMARY.md` (new)

## Migration Complete ✅

The DQX profiling workflow now uses OAuth exclusively for Lakebase Postgres authentication.

