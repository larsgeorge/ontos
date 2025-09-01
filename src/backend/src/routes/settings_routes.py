import logging
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime

from databricks.sdk import WorkspaceClient
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session

from ..common.workspace_client import get_workspace_client
from ..controller.settings_manager import SettingsManager
from ..models.settings import AppRole, AppRoleCreate
from ..common.database import get_db
from ..common.dependencies import get_settings_manager, get_notifications_manager
from ..models.settings import HandleRoleRequest
from ..models.notifications import Notification, NotificationType
from ..controller.notifications_manager import NotificationsManager

# Configure logging
from src.common.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["settings"])

SETTINGS_FEATURE_ID = "settings" # Define a feature ID for settings

@router.get('/settings')
async def get_settings_route(manager: SettingsManager = Depends(get_settings_manager)):
    """Get all settings including available job clusters"""
    try:
        settings_data = manager.get_settings() # Renamed variable to avoid conflict
        return settings_data
    except Exception as e:
        logger.error(f"Error getting settings: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put('/settings')
async def update_settings(
    settings_payload: dict, # Renamed to avoid conflict with module
    manager: SettingsManager = Depends(get_settings_manager)
):
    """Update settings"""
    try:
        updated = manager.update_settings(settings_payload)
        return updated.to_dict()
    except Exception as e:
        logger.error(f"Error updating settings: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/settings/health')
async def health_check(manager: SettingsManager = Depends(get_settings_manager)):
    """Check if the settings API is healthy"""
    try:
        manager.list_available_workflows()
        logger.info("Workflows health check successful")
        return {"status": "healthy"}
    except Exception as e:
        error_msg = f"Workflows health check failed: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get('/settings/job-clusters')
async def list_job_clusters(manager: SettingsManager = Depends(get_settings_manager)):
    """List all available job clusters"""
    try:
        clusters = manager.get_job_clusters()
        return [{
            'id': cluster.id,
            'name': cluster.name,
            'node_type_id': cluster.node_type_id,
            'autoscale': cluster.autoscale,
            'min_workers': cluster.min_workers,
            'max_workers': cluster.max_workers
        } for cluster in clusters]
    except Exception as e:
        logger.error(f"Error fetching job clusters: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

# --- RBAC Routes ---

@router.get("/settings/features", response_model=Dict[str, Dict[str, Any]])
async def get_features_config(manager: SettingsManager = Depends(get_settings_manager)):
    """Get the application feature configuration including allowed access levels."""
    try:
        features = manager.get_features_with_access_levels()
        return features
    except Exception as e:
        logger.error(f"Error getting features configuration: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/settings/roles", response_model=List[AppRole])
async def list_roles(manager: SettingsManager = Depends(get_settings_manager)):
    """List all application roles."""
    try:
        roles = manager.list_app_roles()
        return roles
    except Exception as e:
        logger.error(f"Error listing roles: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/settings/roles", response_model=AppRole, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: AppRoleCreate = Body(..., embed=False),
    manager: SettingsManager = Depends(get_settings_manager),
    db: Session = Depends(get_db)
):
    """Create a new application role."""
    try:
        created_role = manager.create_app_role(db=db, role_data=role_data)
        
        # --- Add created ID to request.state for audit logging --- 
        if created_role and hasattr(created_role, 'id'):
            request.state.audit_created_resource_id = str(created_role.id)
        # -----------------------------------------------------------
            
        return created_role
    except ValueError as e:
        logger.warning(f"Validation error creating role '{role_data.name}': {e!s}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating role '{role_data.name}': {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/settings/roles/{role_id}", response_model=AppRole)
async def get_role(
    role_id: str,
    manager: SettingsManager = Depends(get_settings_manager)
):
    """Get a specific application role by ID."""
    try:
        role = manager.get_app_role(role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        return role
    except Exception as e:
        logger.error(f"Error getting role '{role_id}': {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/settings/roles/{role_id}", response_model=AppRole)
async def update_role(
    role_id: str,
    role_data: AppRole = Body(..., embed=False),
    manager: SettingsManager = Depends(get_settings_manager)
):
    """Update an existing application role."""
    try:
        updated_role = manager.update_app_role(role_id, role_data)
        if updated_role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        return updated_role
    except ValueError as e:
        logger.warning(f"Validation error updating role '{role_id}': {e!s}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating role '{role_id}': {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/settings/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: str,
    manager: SettingsManager = Depends(get_settings_manager)
):
    """Delete an application role."""
    try:
        deleted = manager.delete_app_role(role_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        return None # Return None for 204
    except ValueError as e: # Catch potential error like deleting admin role
        logger.warning(f"Error deleting role '{role_id}': {e!s}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting role '{role_id}': {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Role Request Handling --- 
@router.post("/settings/roles/handle-request", status_code=status.HTTP_200_OK)
async def handle_role_request_decision(
    request_data: HandleRoleRequest = Body(...),
    db: Session = Depends(get_db), # Inject DB Session
    settings_manager: SettingsManager = Depends(get_settings_manager),
    notifications_manager: NotificationsManager = Depends(get_notifications_manager)
):
    """Handles the admin decision (approve/deny) for a role access request."""
    logger.info(f"Handling role request decision for user '{request_data.requester_email}' and role ID '{request_data.role_id}'. Approved: {request_data.approved}")

    # 1. Get Role Name (for notification)
    try:
        # Pass db session if settings_manager methods require it (assuming get_app_role does)
        role = settings_manager.get_app_role(request_data.role_id)
        if not role:
             logger.error(f"Role ID '{request_data.role_id}' not found while handling decision.")
             raise HTTPException(status_code=404, detail=f"Role with ID '{request_data.role_id}' not found.")
        role_name = role.name
    except Exception as e:
        logger.error(f"Error retrieving role {request_data.role_id} during decision handling: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving role details.")

    # 2. TODO: Implement actual access grant/modification logic here if needed
    #    This might involve: 
    #    - Calling SettingsManager to update AppRoleDb.assigned_groups (if groups are managed directly)
    #    - Triggering an external workflow (e.g., ITSM ticket, Databricks SCIM API call)
    #    - For now, we only send the notification.
    if request_data.approved:
        logger.info(f"Role request APPROVED for {request_data.requester_email} (Role: {role_name}). (Actual group assignment logic is currently skipped). ")
        # Example (if managing groups directly):
        # try:
        #    settings_manager.add_user_group_to_role(request_data.role_id, request_data.requester_group) # Need user's group?
        # except ValueError as e:
        #    raise HTTPException(status_code=400, detail=str(e))
    else:
        logger.info(f"Role request DENIED for {request_data.requester_email} (Role: {role_name}).")

    # 3. Create notification for the requester
    try:
        decision_title = f"Role Request { 'Approved' if request_data.approved else 'Denied' }"
        decision_subtitle = f"Role: {role_name}"
        decision_description = (
            f"Your request for the role '{role_name}' has been { 'approved' if request_data.approved else 'denied' }."
            + (f"\n\nAdmin Message: {request_data.message}" if request_data.message else "")
        )
        notification_type = NotificationType.SUCCESS if request_data.approved else NotificationType.WARNING

        # Provide placeholder ID and created_at for Pydantic validation
        placeholder_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        requester_notification = Notification(
            id=placeholder_id,
            created_at=now,
            type=notification_type,
            title=decision_title,
            subtitle=decision_subtitle,
            description=decision_description,
            recipient=request_data.requester_email,
            can_delete=True
        )
        # Pass DB session to create_notification
        notifications_manager.create_notification(db=db, notification=requester_notification)
        logger.info(f"Sent decision notification to requester '{request_data.requester_email}'")

        # 4. Mark the original admin notification as handled (read)
        handled_payload = {
            "requester_email": request_data.requester_email,
            "role_id": request_data.role_id
        }
        # Pass DB session to handle_actionable_notification
        handled = notifications_manager.handle_actionable_notification(
            db=db, # Pass the session
            action_type="handle_role_request",
            action_payload=handled_payload
        )
        if handled:
             logger.info("Marked original admin notification for role request as handled.")
        else:
             logger.warning("Could not find the original admin notification to mark as handled.")

        # Commit happens within handle_actionable_notification now, no explicit commit needed here
        # db.commit() # REMOVE this if commit is in handle_actionable_notification
        return {"message": f"Role request decision processed successfully for {request_data.requester_email}."}

    except Exception as e:
        logger.error(f"Error during notification handling for role request (Role: {request_data.role_id}, User: {request_data.requester_email}): {e}", exc_info=True)
        db.rollback() # Rollback on any exception during this block
        raise HTTPException(status_code=500, detail="Failed to send decision notification due to an internal error.")

# --- Registration --- 

def register_routes(app):
    """Register routes with the app"""
    app.include_router(router)
    logger.info("Settings routes registered")
