# Complete Data Contracts Routes Refactoring Plan

**Date**: October 22, 2025
**Goal**: Move ALL business logic from routes to manager

## Current State: 60 Routes Total

### Already Refactored (3 routes) ✓
1. `POST /data-contracts` - create_contract
2. `PUT /data-contracts/{id}` - update_contract  
3. `POST /data-contracts/upload` - upload_contract

### Routes Requiring Refactoring (34 routes)

#### Phase 1: Version Management (5 routes) - HIGH PRIORITY
**Impact**: ~200 lines of complex cloning logic

1. **`POST /data-contracts/{id}/clone`** (line 3161)
   - **Current**: ~180 lines cloning all relationships manually
   - **Move to**: `manager.clone_contract_for_new_version()`
   - **Logic**: Iterate all relationships, create new records with new IDs

2. **`POST /data-contracts/{id}/versions`** (line 1567)
   - **Current**: Simple version increment
   - **Move to**: `manager.create_new_version()`

3. **`POST /data-contracts/compare`** (line 3339)
   - **Current**: Uses ContractChangeAnalyzer
   - **Move to**: `manager.compare_contracts()`

4. **`GET /data-contracts/{id}/versions`** (line 3104)
   - **Current**: Database queries to build version lineage
   - **Move to**: `manager.get_contract_versions()`

5. **`GET /data-contracts/{id}/version-history`** (line 3390)
   - **Current**: Database queries with recursive lineage
   - **Move to**: `manager.get_version_history()`

#### Phase 2: Workflow Handlers (6 routes) - HIGH PRIORITY
**Impact**: ~400 lines of notification/change log orchestration

6. **`POST /data-contracts/{id}/request-review`** (line 268)
   - **Current**: Create notification, asset review, change log
   - **Move to**: `manager.request_steward_review()`

7. **`POST /data-contracts/{id}/request-publish`** (line 393)
   - **Current**: Create notification, change log
   - **Move to**: `manager.request_publish()`

8. **`POST /data-contracts/{id}/request-deploy`** (line 487)
   - **Current**: Deployment policy validation, notification, change log
   - **Move to**: `manager.request_deploy()`

9. **`POST /data-contracts/{id}/handle-review`** (line 624)
   - **Current**: Update status, mark notification handled, notify requester, change log
   - **Move to**: `manager.handle_review_response()`

10. **`POST /data-contracts/{id}/handle-publish`** (line 755)
    - **Current**: Update published flag, mark notification handled, notify requester, change log
    - **Move to**: `manager.handle_publish_response()`

11. **`POST /data-contracts/{id}/handle-deploy`** (line 867)
    - **Current**: Trigger deployment, update status, mark notification handled, notify requester, change log
    - **Move to**: `manager.handle_deploy_response()`

#### Phase 3: Simple Workflow Transitions (3 routes) - MEDIUM PRIORITY
**Impact**: ~150 lines of status update logic

12. **`POST /data-contracts/{id}/submit`** (line 133) - ALREADY REFACTORED ✓
    - Uses `manager.transition_status()` ✓

13. **`POST /data-contracts/{id}/approve`** (line 177)
    - **Current**: Status check, update, audit
    - **Move to**: `manager.approve_contract()` or use `transition_status()`

14. **`POST /data-contracts/{id}/reject`** (line 213)
    - **Current**: Status check, update, audit
    - **Move to**: `manager.reject_contract()` or use `transition_status()`

#### Phase 4: Nested Resource CRUD (18 routes) - MEDIUM PRIORITY
**Impact**: ~500 lines of CRUD operations

I already added these methods to manager but NEVER refactored the routes:

**Custom Properties (3 routes)**
15. `POST /data-contracts/{id}/custom-properties` (1827) - Use `manager.create_custom_property()`
16. `PUT /data-contracts/{id}/custom-properties/{prop_id}` (1869) - Use `manager.update_custom_property()`
17. `DELETE /data-contracts/{id}/custom-properties/{prop_id}` (1917) - Use `manager.delete_custom_property()`

**Support Channels (3 routes)**
18. `POST /data-contracts/{id}/support` (1985)
19. `PUT /data-contracts/{id}/support/{channel_id}` (2043)
20. `DELETE /data-contracts/{id}/support/{channel_id}` (2105)

**Pricing (1 route)**
21. `PUT /data-contracts/{id}/pricing` (2184)

**Roles (3 routes)**
22. `POST /data-contracts/{id}/roles` (2267)
23. `PUT /data-contracts/{id}/roles/{role_id}` (2330)
24. `DELETE /data-contracts/{id}/roles/{role_id}` (2397)

**Authoritative Definitions - Contract Level (3 routes)**
25. `POST /data-contracts/{id}/authoritative-definitions` (2466)
26. `PUT /data-contracts/{id}/authoritative-definitions/{def_id}` (2508)
27. `DELETE /data-contracts/{id}/authoritative-definitions/{def_id}` (2555)

**Authoritative Definitions - Schema Level (3 routes)**
28. `POST /data-contracts/{id}/schemas/{schema_id}/authoritative-definitions` (2620)
29. `PUT /data-contracts/{id}/schemas/{schema_id}/authoritative-definitions/{def_id}` (2663)
30. `DELETE /data-contracts/{id}/schemas/{schema_id}/authoritative-definitions/{def_id}` (2711)

**Authoritative Definitions - Property Level (3 routes)**
31. `POST /data-contracts/{id}/schemas/{schema_id}/properties/{prop_id}/authoritative-definitions` (2778)
32. `PUT /data-contracts/{id}/schemas/{schema_id}/properties/{prop_id}/authoritative-definitions/{def_id}` (2822)
33. `DELETE /data-contracts/{id}/schemas/{schema_id}/properties/{prop_id}/authoritative-definitions/{def_id}` (2871)

**Tags (3 routes)**
34. `POST /data-contracts/{id}/tags` (2938)
35. `PUT /data-contracts/{id}/tags/{tag_id}` (2986)
36. `DELETE /data-contracts/{id}/tags/{tag_id}` (3047)

#### Phase 5: Comments (1 route) - LOW PRIORITY
37. **`POST /data-contracts/{id}/comments`** (line 1497)
    - **Current**: Direct db.add()
    - **Move to**: `manager.add_comment()`

### Routes That Are OK As-Is (23 routes)
These are simple GET operations or already properly delegate to manager:

- GET operations (fetching data): 16 routes
- DQX profiling endpoints (already use manager): 6 routes
- DELETE contract (already uses manager): 1 route

## Implementation Strategy

### Step 1: Phase 1 - Version Management
- Add 5 methods to manager
- Refactor 5 routes
- Test version cloning, comparison, history

### Step 2: Phase 2 - Workflow Handlers
- Add 6 methods to manager
- Refactor 6 routes
- Test notification flow, change logs

### Step 3: Phase 3 - Simple Transitions
- Add 2 methods to manager
- Refactor 2 routes (1 already done)

### Step 4: Phase 4 - Nested Resource CRUD
- Add missing manager methods
- Refactor 18 routes systematically

### Step 5: Phase 5 - Comments
- Add 1 method to manager
- Refactor 1 route

## Success Criteria

- All 37 routes refactored
- Routes contain ONLY:
  - Request parsing
  - Manager method calls
  - Response formatting
  - Error translation
  - Audit logging
- Manager contains ALL:
  - Validation
  - Database operations
  - Transaction management
  - Business logic
  - Error handling
- All files compile without errors
- No breaking changes

## Verification Process

For EACH route refactored:
1. Read the route code to understand the logic
2. Extract business logic to manager method
3. Simplify route to call manager
4. Verify file compiles
5. Check linter
6. Document in this file

## Progress Tracking

- [ ] Phase 1: Version Management (5 routes)
- [ ] Phase 2: Workflow Handlers (6 routes)
- [ ] Phase 3: Simple Transitions (2 routes)
- [ ] Phase 4: Nested Resource CRUD (18 routes)
- [ ] Phase 5: Comments (1 route)
- [ ] Final verification and documentation

