# Deployment Policy System - Implementation Summary

## Overview

Successfully implemented a comprehensive deployment policy system that enforces catalog/schema restrictions for Unity Catalog deployments based on user roles and group memberships.

## Key Features Implemented

### 1. Backend Foundation

#### DeploymentPolicy Model (`src/backend/src/models/settings.py`)
```python
class DeploymentPolicy(BaseModel):
    allowed_catalogs: List[str]      # Catalogs user can deploy to
    allowed_schemas: List[str]       # Schemas user can deploy to
    default_catalog: Optional[str]   # Default catalog for UI
    default_schema: Optional[str]    # Default schema for UI
    require_approval: bool           # Require admin approval
    can_approve_deployments: bool    # Can approve deployment requests
```

#### DeploymentPolicyManager (`src/backend/src/controller/deployment_policy_manager.py`)
- **Policy Resolution**: Merges policies from all user's group roles
- **Template Variables**: Supports `{username}`, `{email}`, `{team}`, `{domain}`
- **Pattern Matching**: Wildcards (`*`, `user_*`) and regex (`^pattern$`)
- **Validation**: Ensures deployment targets match policy rules
- **Approval Authority**: Verifies approvers have access to requested catalogs

#### API Endpoint (`src/backend/src/routes/user_routes.py`)
- `GET /api/user/deployment-policy` - Returns effective policy for current user

#### Request Validation (`src/backend/src/routes/data_contracts_routes.py`)
- `POST /api/data-contracts/{id}/request-deploy` - Validates catalog/schema before creating request

### 2. Database Schema

#### AppRole Extension (`src/backend/src/db_models/settings.py`)
```python
deployment_policy = Column(
    JSONB,
    nullable=True,
    comment="Deployment policy for this role (catalog/schema restrictions)"
)
```

### 3. Frontend Implementation

#### TypeScript Types (`src/frontend/src/types/deployment-policy.ts`)
- `DeploymentPolicy` interface matching backend model

#### Role Management UI (`src/frontend/src/components/settings/role-form-dialog.tsx`)
- **Tabbed Interface**: Organized into General, Permissions, and Deployment tabs
  - Solves dialog height/scrolling issues by separating concerns
  - Each tab content fits comfortably within dialog viewport
- Inputs for allowed catalogs/schemas (comma-separated)
- Default catalog/schema selection
- Approval settings checkboxes
- Template variable documentation

#### Request Dialog (`src/frontend/src/components/data-contracts/request-contract-action-dialog.tsx`)
- Fetches deployment policy on deploy option selection
- Replaces text inputs with dropdowns showing allowed catalogs/schemas
- Pre-populates defaults from policy
- Shows policy summary banner
- Displays helpful validation messages

## Template Variables

### Supported Variables
- `{username}` - Email prefix (jdoe@company.com → jdoe)
- `{email}` - Full email address
- `{team}` - Primary team name (future enhancement)
- `{domain}` - User's assigned domain (future enhancement)

### Example Usage
```json
{
  "allowed_catalogs": [
    "{username}_sandbox",
    "shared_dev",
    "prod_catalog"
  ],
  "allowed_schemas": [
    "{username}_schema",
    "default",
    "*"
  ],
  "default_catalog": "{username}_sandbox",
  "default_schema": "default",
  "require_approval": true,
  "can_approve_deployments": false
}
```

For user `jdoe@company.com`, this resolves to:
- allowed_catalogs: `["jdoe_sandbox", "shared_dev", "prod_catalog"]`
- default_catalog: `"jdoe_sandbox"`

## Pattern Matching Examples

### Wildcards
- `*` - Matches any catalog/schema
- `user_*` - Matches `user_jdoe`, `user_alice`, etc.
- `*_sandbox` - Matches `jdoe_sandbox`, `team_sandbox`, etc.

### Regex
- `^prod_.*$` - Matches catalogs starting with `prod_`
- `^[a-z]+_sandbox$` - Matches lowercase names ending with `_sandbox`

### Exact Match
- `my_catalog` - Matches only `my_catalog`

## Policy Resolution Algorithm

1. **Check Role Override**: If user has explicit role override applied, use that role's policy
2. **Collect Group Policies**: Gather policies from all roles assigned to user's groups
3. **Merge Policies**: Union of allowed catalogs/schemas (most permissive wins)
4. **Resolve Templates**: Replace `{username}`, `{email}`, etc. with actual values
5. **Return Effective Policy**: Final policy with all transformations applied

## Validation Flow

```
User submits deployment request
    ↓
Fetch user's effective deployment policy
    ↓
Validate catalog against allowed_catalogs
    ↓
Validate schema against allowed_schemas (if specified)
    ↓
If valid: Create notification for approver
If invalid: Return 403 with error message
```

## Approver Authority Validation

When an admin approves a deployment request:
1. Fetch approver's deployment policy
2. Check `can_approve_deployments = true`
3. Verify approver has access to the requested catalog/schema
4. If authorized: Execute deployment
5. If not authorized: Reject with permission error

## Testing Scenarios

### 1. Template Variable Resolution
**Setup**: Create role with policy:
```json
{
  "allowed_catalogs": ["{username}_sandbox"],
  "default_catalog": "{username}_sandbox"
}
```
**Test**: User `alice@company.com` should see `alice_sandbox` as the only available catalog

### 2. Wildcard Matching
**Setup**: Create role with policy:
```json
{
  "allowed_catalogs": ["dev_*", "shared_*"],
  "allowed_schemas": ["*"]
}
```
**Test**: User can deploy to `dev_team1`, `dev_analytics`, `shared_prod`, but NOT to `prod_main`

### 3. Policy Merging
**Setup**: 
- Role A: `allowed_catalogs = ["catalog_a"]`
- Role B: `allowed_catalogs = ["catalog_b"]`
- User belongs to groups assigned to both roles

**Test**: User should see both `catalog_a` and `catalog_b` in dropdown

### 4. Validation Enforcement
**Setup**: User has policy with `allowed_catalogs = ["sandbox"]`

**Test**: Attempting to deploy to `production` should return 403 error

### 5. Approval Authority
**Setup**: 
- User A requests deployment to `prod_catalog`
- Admin B has policy with `allowed_catalogs = ["dev_catalog"]`

**Test**: Admin B should NOT be able to approve the request (lacks access to `prod_catalog`)

## Security Considerations

1. **Service Principal Permissions**: The app service principal handles all UC CREATE operations, not end-users
2. **Policy Enforcement**: All validation happens server-side, client-side is for UX only
3. **Approver Authority**: Approvers can only approve deployments to catalogs they have access to
4. **Audit Logging**: All deployment requests and approvals are logged with user and target details

## Edge Cases Handled

1. **No Policy Defined**: Returns restrictive default (no catalogs allowed, requires approval)
2. **Empty Allowed Catalogs**: Blocks all deployments for that role
3. **Conflicting Policies**: Most permissive wins (union of allowed resources)
4. **Invalid Regex**: Logs error and treats as non-match
5. **Missing Template Variables**: Falls back to placeholder values (e.g., "default_team")

## Future Enhancements

1. **Team-Based Templates**: Resolve `{team}` from user's primary team assignment
2. **Domain-Based Templates**: Resolve `{domain}` from data domain ownership
3. **Time-Based Restrictions**: Allow deployments only during certain hours/days
4. **Resource Quotas**: Limit number of deployments per user/team
5. **Policy Inheritance**: Hierarchical policies (org → team → user)
6. **Admin Dashboard**: Visualize who has access to which catalogs
7. **Policy Testing Tool**: Preview policy resolution for any user
8. **Compliance Reporting**: Track deployment patterns and policy violations

## Files Modified/Created

### Backend
- ✅ `src/backend/src/models/settings.py` - Added `DeploymentPolicy` model
- ✅ `src/backend/src/db_models/settings.py` - Added `deployment_policy` column to `AppRole`
- ✅ `src/backend/src/controller/deployment_policy_manager.py` - New manager class
- ✅ `src/backend/src/common/deployment_dependencies.py` - New dependency injection
- ✅ `src/backend/src/routes/user_routes.py` - Added `/user/deployment-policy` endpoint
- ✅ `src/backend/src/routes/data_contracts_routes.py` - Added validation to `request-deploy`

### Frontend
- ✅ `src/frontend/src/types/deployment-policy.ts` - New TypeScript types
- ✅ `src/frontend/src/types/settings.ts` - Added `deployment_policy` to `AppRole`
- ✅ `src/frontend/src/components/settings/role-form-dialog.tsx` - Added policy configuration UI
- ✅ `src/frontend/src/components/data-contracts/request-contract-action-dialog.tsx` - Added policy-driven dropdowns

## Conclusion

The deployment policy system is fully implemented and ready for testing. It provides:
- ✅ Flexible policy definition with templates and wildcards
- ✅ Role-based access control for deployments
- ✅ User-friendly UI with policy-driven dropdowns
- ✅ Server-side validation and enforcement
- ✅ Approval workflow integration
- ✅ Comprehensive error handling and logging

Next step: Test in development environment and gather user feedback.

