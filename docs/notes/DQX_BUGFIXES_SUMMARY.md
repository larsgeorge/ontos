# DQX Profiling Bug Fixes and Refactoring Summary

## Date: October 22, 2025

This document summarizes the bug fixes and architectural refactoring applied to the DQX profiling integration after the initial OAuth migration.

## Architecture Refactoring (Latest)

### Background
The DQX profiling logic was scattered across the controller (`data_contracts_routes.py`) instead of being centralized in the manager. Additionally, a timeout workaround was implemented instead of leveraging the existing JobsManager's job tracking capabilities.

### Changes Made

1. **Moved All Business Logic to Manager**
   - Created comprehensive DQX profiling methods in `DataContractsManager`:
     - `start_profiling()`: Start DQX profiling workflow
     - `get_profile_runs()`: Get profiling runs with JobsManager integration
     - `get_profile_suggestions()`: Get quality check suggestions
     - `accept_suggestions()`: Accept and convert suggestions to quality rules
     - `reject_suggestions()`: Reject suggestions
     - `update_suggestion()`: Update suggestion before acceptance

2. **Integrated with JobsManager**
   - `get_profile_runs()` now queries JobsManager for real-time job status
   - Automatically updates profiling run status when job terminates
   - No more timeout workarounds - uses actual Databricks job state

3. **Simplified Route Endpoints**
   - All routes now act as thin marshalling layers
   - Business logic delegated to manager methods
   - Consistent error handling across all endpoints

### Benefits
- **Separation of Concerns**: Routes handle FastAPI marshalling, manager handles business logic
- **Accurate Job Tracking**: Leverages JobsManager instead of timeout workarounds  
- **Consistency**: All data contract operations follow the same pattern
- **Maintainability**: Business logic centralized in one place
- **Extensibility**: Easy to add more profiling sources beyond DQX

---

---

## Bug #1: Incorrect DQX Data Structure Parsing

### Problem
DQX was returning quality check suggestions with column names shown as empty in the UI, all checks appearing as "Table-level" instead of property-level, and wrong dimensions (e.g., "accuracy" instead of "completeness").

### Root Cause
The DQX library returns a **nested structure**, not the flat structure we were expecting:

```python
{
  'check': {
    'function': 'is_not_null',           # ← The actual rule type
    'arguments': {'column': 'id'}         # ← Column is nested here!
  },
  'name': 'id_is_null',                   # ← Human-readable name
  'criticality': 'error'                  # ← Severity level
}
```

Our code was trying to access `check.get('column')` which doesn't exist - the column is actually at `check['check']['arguments']['column']`.

### Solution
Updated `insert_suggestion()` and `profile_and_generate_suggestions()` functions to properly parse the nested structure:

```python
if isinstance(dq_profile, dict) and 'check' in dq_profile:
    # New nested format
    check_info = dq_profile.get('check', {})
    rule_name = check_info.get('function', '')
    arguments = check_info.get('arguments', {})
    column_name = arguments.get('column', '')
    params = arguments
    description = dq_profile.get('name', '')
    severity_map = {'error': 'error', 'warn': 'warning', 'info': 'info'}
    severity = severity_map.get(dq_profile.get('criticality', 'error'), 'error')
```

### Files Changed
- `src/backend/src/workflows/dqx_profile_datasets/dqx_profile_datasets.py`

---

## Bug #2: UI Not Auto-Updating (No Polling)

### Problem
After a DQX profiling job completed, the UI didn't show the pending suggestions until the page was manually refreshed.

### Root Cause
The `fetchProfileRuns` function was being used in a `useEffect` before it was defined, causing React to skip setting up the polling interval. Additionally, it wasn't wrapped in `useCallback`, causing unnecessary re-renders.

### Solution
1. **Moved function definition** before the `useEffect` that uses it
2. **Wrapped in `useCallback`** to stabilize the function reference
3. **Added proper dependencies**: `[contractId, isProfilingRunning, toast]`
4. **Added console logging** for debugging
5. **Added toast notifications** when profiling completes or fails

```typescript
const fetchProfileRuns = useCallback(async () => {
  if (!contractId) return
  try {
    const res = await fetch(`/api/data-contracts/${contractId}/profile-runs`)
    // ... check for status changes and show notifications
  } catch (e) {
    console.warn('Failed to fetch profile runs:', e)
    setIsProfilingRunning(false)
  }
}, [contractId, isProfilingRunning, toast])

useEffect(() => {
  if (!isProfilingRunning || !contractId) return
  
  console.log('Starting profiling poll interval...')
  const pollInterval = setInterval(() => {
    console.log('Polling for profiling updates...')
    fetchProfileRuns()
  }, 5000) // Poll every 5 seconds
  
  return () => {
    console.log('Stopping profiling poll interval')
    clearInterval(pollInterval)
  }
}, [isProfilingRunning, contractId, fetchProfileRuns])
```

### Files Changed
- `src/frontend/src/views/data-contract-details.tsx`

---

## Bug #3: Jobs Stuck in "Running" Status

### Problem
When a DQX profiling job crashed (e.g., due to database connection issues), the status remained as "running" in the database even though the job had failed. This caused:
1. The UI to show a perpetual spinner
2. No error notification to the user
3. Unable to determine what went wrong

### Root Cause
When the database connection pool fails during execution, the error handling code tries to update the status to "failed" using the same broken connection, which fails silently. The job then exits without updating the status.

### Solution - Part 1: Retry Status Update with New Connection
Updated the main exception handler to retry status updates with a fresh database connection if the original engine fails:

```python
except Exception as e:
    print(f"✗ Workflow failed with error: {e}")
    traceback.print_exc()
    
    try:
        update_profiling_run_status(engine, profile_run_id, "failed", error_message=str(e))
    except Exception as update_error:
        print(f"Warning: Failed to update run status with existing engine: {update_error}")
        print("Attempting to create new database connection to update status...")
        try:
            # Create fresh engine for status update
            new_engine = create_engine_from_params(...)
            update_profiling_run_status(new_engine, profile_run_id, "failed", error_message=str(e))
            print("✓ Successfully updated status to 'failed' with new connection")
            new_engine.dispose()
        except Exception as final_error:
            print(f"✗ Failed to update run status even with new connection: {final_error}")
    
    sys.exit(1)
```

### Solution - Part 2: Automatic Timeout Detection
Added logic to the `get_profile_runs` API endpoint to automatically detect and mark stuck jobs as failed:

```python
# Check if run is stuck (running for > 1 hour)
if run.status == 'running' and run.started_at:
    started_at = run.started_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    
    time_elapsed = datetime.now(timezone.utc) - started_at
    if time_elapsed > timedelta(hours=1):
        logger.warning(f"Profiling run {run.id} has been running for {time_elapsed}, marking as failed")
        run.status = 'failed'
        run.error_message = f"Job timed out after {time_elapsed.total_seconds()/60:.1f} minutes. The job may have crashed or lost connection."
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
```

This ensures that:
- **New failures** are properly recorded even if the connection is broken
- **Existing stuck jobs** are automatically detected and marked as failed
- **The UI** will eventually show the error (within 1 hour + polling interval)

### Files Changed
- `src/backend/src/workflows/dqx_profile_datasets/dqx_profile_datasets.py`
- `src/backend/src/routes/data_contracts_routes.py`

---

## Testing Results

After applying all fixes:

✅ **DQX Data Parsing**: Column names appear correctly, proper levels assigned, correct dimensions  
✅ **UI Polling**: Live updates every 5 seconds, toast notifications on completion/failure  
✅ **Status Tracking**: Failed jobs properly marked, stuck jobs auto-detected after 1 hour  
✅ **Error Handling**: Robust error handling with connection retry logic  
✅ **User Experience**: Real-time progress indicator, no page refresh needed  

---

## Configuration

### Timeout Settings
- **Auto-timeout threshold**: 1 hour (3600 seconds)
- **Polling interval**: 5 seconds
- **Timeout error message**: "Job timed out after X.X minutes. The job may have crashed or lost connection."

### Modifying Timeout
To change the auto-timeout threshold, edit this line in `data_contracts_routes.py`:

```python
if time_elapsed > timedelta(hours=1):  # ← Change this value
```

### Modifying Poll Interval
To change the polling frequency, edit this line in `data-contract-details.tsx`:

```typescript
}, 5000) // Poll every 5 seconds ← Change this value (milliseconds)
```

---

## Related Documentation

- [DQX OAuth Migration Summary](./DQX_OAUTH_MIGRATION_SUMMARY.md)
- [DQX Profiling Implementation Summary](./DQX_PROFILING_IMPLEMENTATION_SUMMARY.md)

---

## Future Improvements

1. **Databricks Job Monitoring**: Add direct integration with Databricks Jobs API to get real-time job status instead of relying on timeouts
2. **Manual Recovery**: Add UI button to manually retry or mark jobs as failed
3. **Job Logs Integration**: Show Databricks job logs directly in the UI
4. **Notifications**: Email/Slack notifications when profiling completes or fails
5. **Progress Tracking**: Show more granular progress (e.g., "Profiling table 2 of 5")

