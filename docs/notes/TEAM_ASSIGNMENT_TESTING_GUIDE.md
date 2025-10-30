# Team Assignment Testing Guide

## What Was Fixed

The issue was that the "Import from Team" button wasn't appearing after assigning a team to a contract. This was due to **two async race conditions**:

### 1. Missing `await` in `fetchDetails()`
In the `fetchDetails()` function, we were calling `fetchOwnerTeamName()` but not awaiting it. This meant that the owner team name state wasn't being set before the UI re-rendered.

**Fixed by:**
- Adding `await` before `fetchOwnerTeamName(contractData.owner_team_id)` in `fetchDetails()`
- Clearing the `ownerTeamName` state when there's no `owner_team_id`

### 2. Button visibility logic
The button was only showing when BOTH `contract.owner_team_id` AND `ownerTeamName` were truthy. Since `ownerTeamName` might not be loaded immediately, the button would remain hidden.

**Fixed by:**
- Changed the conditional rendering to only check for `contract.owner_team_id`
- Made the button disabled (not hidden) while `ownerTeamName` is loading
- Added a helpful tooltip

### 3. Dialog rendering condition
The `ImportTeamMembersDialog` was only rendered when BOTH `owner_team_id` and `ownerTeamName` existed.

**Fixed by:**
- Removed the `ownerTeamName` check from the dialog rendering condition
- Fallback to showing `owner_team_id` if `ownerTeamName` isn't loaded yet

## How to Test

### Manual Testing Steps:

1. **Navigate to a Data Contract**
   - Go to http://localhost:5173/data-contracts
   - Click on any existing contract

2. **Verify Initial State**
   - Scroll to the "Team Members" section
   - The "Import from Team" button should NOT be visible if no owner team is assigned

3. **Assign an Owner Team**
   - Click the "Edit Metadata" button (top right)
   - Find the "Owner Team" dropdown field
   - Select a team from the dropdown (not "None")
   - Click "Save Changes"

4. **Verify Button Appears**
   - After the dialog closes and the page refreshes
   - Scroll to the "Team Members" section
   - The "Import from Team" button should now be visible next to "Add Member"
   - The button should be enabled (not grayed out)

5. **Import Team Members**
   - Click the "Import from Team" button
   - A dialog should open showing all members from the selected team
   - All members should be selected (checked) by default
   - Each member should have a role dropdown (default from their `app_role_override`)
   - Customize roles if desired
   - Click "Import X Members"

6. **Verify Import Success**
   - The dialog should close
   - The team members should now appear in the "Team Members" section
   - A success toast should show the number of imported members
   - The contract's customProperties should now include:
     - `assignedTeamId`: The team's UUID
     - `assignedTeamName`: The team's name
     - `assignedTeamDate`: ISO timestamp of import

7. **Verify Owner Display**
   - Scroll to the top "Core Metadata Card"
   - The "Owner:" field should show the team name (clickable link)
   - Clicking it should navigate to `/teams/{team_id}`

### Testing Edge Cases:

1. **Removing Owner Team**
   - Edit metadata and set owner team to "None"
   - Save
   - The "Import from Team" button should disappear

2. **Changing Owner Team**
   - Assign Team A
   - Import some members
   - Edit metadata and change to Team B
   - The "Import from Team" button should still work
   - Importing from Team B should add to existing members (not replace)

3. **Independent Editing**
   - After importing team members
   - Edit/delete individual members via "Add Member" / edit buttons
   - Changes should persist independently of the source team
   - The customProperties should still show the original import metadata

## Backend Verification

To verify the backend is working:

```bash
# 1. Create or update a contract with owner_team_id
curl -X PUT http://localhost:8000/api/data-contracts/{contract_id} \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Contract",
    "version": "1.0.0",
    "status": "draft",
    "owner_team_id": "{team_id}"
  }'

# 2. Fetch team members for import
curl http://localhost:8000/api/data-contracts/{contract_id}/import-team-members?team_id={team_id}

# Expected response:
# [
#   {
#     "member_identifier": "user@example.com",
#     "member_name": "user@example.com",
#     "member_type": "user",
#     "suggested_role": "engineer"
#   }
# ]

# 3. Verify contract has owner_team_id
curl http://localhost:8000/api/data-contracts/{contract_id}
# Should include: "owner_team_id": "{team_id}"
```

## Files Modified

1. **src/frontend/src/views/data-contract-details.tsx**
   - Fixed async race condition in `fetchDetails()` by adding `await`
   - Cleared `ownerTeamName` when no owner team is set
   - Updated `handleUpdateMetadata` to await team name fetch
   - Changed "Import from Team" button visibility logic
   - Made button disabled while loading instead of hidden
   - Added tooltip to button
   - Removed `ownerTeamName` requirement from dialog rendering

2. **Previous changes (already implemented):**
   - Backend: `data_contracts_routes.py`, `data_contracts_manager.py`, `data_contracts_api.py`
   - Frontend: `import-team-members-dialog.tsx`, `data-contract-basic-form-dialog.tsx`, `team-member-form-dialog.tsx`, `data-contract.ts`

## Expected Behavior Summary

✅ Button appears immediately after assigning owner team  
✅ Button is disabled while team name loads (very brief, < 1 second)  
✅ Button is enabled once team name is loaded  
✅ Clicking button opens dialog with team members  
✅ Imported members are added to contract's ODCS team array  
✅ Import metadata stored in customProperties  
✅ Owner team displayed as clickable link in metadata section  
✅ Independent editing of imported members works correctly  

