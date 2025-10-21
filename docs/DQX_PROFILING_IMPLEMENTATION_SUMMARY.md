# DQX Profiling Integration - Implementation Summary

## Overview
Successfully integrated Databricks Labs DQX profiler into the data contracts feature, allowing users to auto-generate quality check suggestions from Unity Catalog datasets.

## What Was Implemented

### Backend Components

#### 1. Database Models (`src/backend/src/db_models/data_contracts.py`)
- **DataProfilingRunDb**: Tracks profiling runs (DQX, LLM, manual sources)
  - Stores run metadata, status, summary stats
  - Links to contract and suggestions
- **SuggestedQualityCheckDb**: Stores quality check suggestions
  - Generic design to support multiple sources (DQX, LLM, manual)
  - Contains all ODCS quality check fields
  - Tracks status (pending, accepted, rejected)
  - Includes AI-specific fields (confidence_score, rationale)

#### 2. Repositories
- **data_profiling_runs_repository.py**: CRUD operations for profiling runs
- **suggested_quality_checks_repository.py**: CRUD operations for suggestions
  - Includes bulk accept/reject operations

#### 3. Background Workflow (`src/backend/src/workflows/dqx_profile_datasets/`)
- **dqx_profile_datasets.yaml**: Workflow definition with DQX environment
- **dqx_profile_datasets.py**: Profiling script that:
  - Uses OAuth authentication for Lakebase Postgres
  - Connects to Postgres to load contract schemas
  - Initializes Spark and DQX profiler
  - Profiles selected Unity Catalog tables
  - Generates quality rule suggestions
  - Maps DQX format to ODCS format
  - Stores suggestions in database

#### 4. API Endpoints (`src/backend/src/routes/data_contracts_routes.py`)
Five new endpoints:
- **POST `/api/data-contracts/{contract_id}/profile`**: Start profiling
- **GET `/api/data-contracts/{contract_id}/profile-runs`**: Get profile runs with counts
- **GET `/api/data-contracts/{contract_id}/profile-runs/{run_id}/suggestions`**: Get suggestions
- **POST `/api/data-contracts/{contract_id}/suggestions/accept`**: Accept suggestions (bulk)
- **PUT `/api/data-contracts/{contract_id}/suggestions/{suggestion_id}`**: Edit suggestion
- **POST `/api/data-contracts/{contract_id}/suggestions/reject`**: Reject suggestions (bulk)

#### 5. JobsManager Enhancement (`src/backend/src/controller/jobs_manager.py`)
- Updated `run_job()` method to accept optional `job_parameters` dict
- Passes parameters to Databricks run_now() API

### Frontend Components

#### 1. TypeScript Types (`src/frontend/src/types/data-contract.ts`)
- **DataProfilingRun**: Type for profiling run metadata
- **SuggestedQualityCheck**: Type for quality check suggestions

#### 2. Schema Selection Dialog (`src/frontend/src/components/data-contracts/dqx-schema-select-dialog.tsx`)
- Allows users to select which schemas to profile
- Shows schema details (name, physical name, column count)
- Select All / Deselect All functionality
- Triggers profiling workflow

#### 3. Suggestions Review Dialog (`src/frontend/src/components/data-contracts/dqx-suggestions-dialog.tsx`)
- Displays quality check suggestions in a data table
- Groups suggestions by schema (tabs for multiple schemas)
- Bulk selection and actions
- Accept/Reject with version bump support
- Individual edit capability
- Integrates with CreateVersionDialog for semver

#### 4. Data Contract Details Integration (`src/frontend/src/views/data-contract-details.tsx`)
- Added "Profile with DQX" button in schemas section
- Shows pending suggestions count as alert banner
- "Review Suggestions" button to open dialog
- Fetches profile runs on page load
- Poll for updates after profiling starts

## User Flow

1. **User navigates to Data Contract details page**
   - System automatically checks for pending suggestions

2. **User clicks "Profile with DQX" button** (in Schemas section)
   - DqxSchemaSelectDialog opens
   - User selects schemas to profile
   - User clicks "Profile N Schemas"

3. **System starts background profiling**
   - Creates DataProfilingRunDb record
   - Triggers Databricks workflow with parameters
   - Returns success message
   - User receives toast notification

4. **DQX profiling runs in background**
   - Workflow profiles selected Unity Catalog tables
   - Generates quality rule suggestions
   - Stores suggestions in database
   - Updates run status to 'completed'

5. **User receives notification** (when complete)
   - System shows alert banner with suggestion count
   - User clicks "Review Suggestions"

6. **DqxSuggestionsDialog opens**
   - Displays suggestions grouped by schema
   - User can select suggestions to accept/reject
   - User can edit suggestions before accepting

7. **User accepts suggestions**
   - If contract not in draft, system prompts for version bump
   - Selected suggestions converted to quality checks
   - Suggestions marked as 'accepted'
   - Contract updated

## Key Features

### Generic Design
- Tables and code support multiple sources (DQX, LLM, manual)
- Future-proof for additional quality check generation methods

### Version Control
- Automatic version bump detection
- Semver support via CreateVersionDialog
- Only required for non-draft contracts

### User Experience
- Single vs multiple schema display optimization
- Bulk operations for efficiency
- Real-time pending count display
- Clear status indicators

### Data Mapping
- DQX profile format → ODCS quality check format
- Proper dimension mapping (completeness, conformity, etc.)
- Rule type translation (is_not_null, min_max, etc.)

### OAuth Authentication
- OAuth token generation using Databricks SDK for Lakebase Postgres
- Automatic credential generation per workflow run
- Secure authentication without stored secrets
- Service principal-based access control

## Installation & Setup

1. **Install workflow via Settings > Jobs & Workflows UI**
   - Workflow: `dqx_profile_datasets`
   - Requires DQX package in Databricks environment

2. **Database tables auto-create** in dev mode on server restart
   - `data_profiling_runs`
   - `suggested_quality_checks`

3. **Postgres authentication** from Databricks workflow environment
   - Uses OAuth authentication for Lakebase Postgres
   - Automatically generates credentials via Databricks SDK
   - No manual secret configuration required

## Testing Recommendations

- Test profiling with various Unity Catalog table types
- Verify error handling when tables don't exist
- Test version bump workflow
- Test permission checks
- Test with single and multiple schemas
- Test bulk accept/reject operations
- Verify notification delivery
- Test pending suggestions display

## Future Enhancements

- Support for LLM-generated suggestions
- Manual suggestion creation
- Suggestion editing UI improvements
- Profile history view
- Custom profiling options in UI
- Scheduled profiling

## Files Modified/Created

### Backend
- ✅ `src/backend/src/db_models/data_contracts.py` (modified)
- ✅ `src/backend/src/repositories/data_profiling_runs_repository.py` (created)
- ✅ `src/backend/src/repositories/suggested_quality_checks_repository.py` (created)
- ✅ `src/backend/src/workflows/dqx_profile_datasets/dqx_profile_datasets.yaml` (created)
- ✅ `src/backend/src/workflows/dqx_profile_datasets/dqx_profile_datasets.py` (created)
- ✅ `src/backend/src/routes/data_contracts_routes.py` (modified)
- ✅ `src/backend/src/controller/jobs_manager.py` (modified)

### Frontend
- ✅ `src/frontend/src/types/data-contract.ts` (modified)
- ✅ `src/frontend/src/components/data-contracts/dqx-schema-select-dialog.tsx` (created)
- ✅ `src/frontend/src/components/data-contracts/dqx-suggestions-dialog.tsx` (created)
- ✅ `src/frontend/src/views/data-contract-details.tsx` (modified)

## Status
✅ **Implementation Complete** - All planned features implemented and tested for linter errors.

