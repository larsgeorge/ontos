from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime

from databricks.sdk import WorkspaceClient
from fastapi import APIRouter, Depends, HTTPException, status, Body, Request, BackgroundTasks
from sqlalchemy.orm import Session

from ..common.workspace_client import get_workspace_client
from ..controller.settings_manager import SettingsManager
from ..models.settings import AppRole, AppRoleCreate
from ..common.database import get_db
from ..common.dependencies import (
    get_settings_manager,
    get_notifications_manager,
    AuditManagerDep,
    AuditCurrentUserDep,
    DBSessionDep,
)
from ..models.settings import HandleRoleRequest
from ..models.notifications import Notification, NotificationType
from ..controller.notifications_manager import NotificationsManager
from ..common.config import get_settings
from ..common.sanitization import sanitize_markdown_input

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
    request: Request,
    background_tasks: BackgroundTasks,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    settings_payload: dict, # Renamed to avoid conflict with module
    manager: SettingsManager = Depends(get_settings_manager)
):
    """Update settings"""
    success = False
    details = {}
    try:
        logger.info(f"Received settings update request: {settings_payload}")
        logger.info(f"job_cluster_id in payload: {settings_payload.get('job_cluster_id')}")

        # Track what settings changed
        if 'job_cluster_id' in settings_payload:
            details['job_cluster_id'] = settings_payload.get('job_cluster_id')
        if 'sync_enabled' in settings_payload:
            details['sync_enabled'] = settings_payload.get('sync_enabled')
        if 'sync_repository' in settings_payload:
            details['sync_repository'] = settings_payload.get('sync_repository')
        if 'enabled_jobs' in settings_payload:
            details['enabled_jobs'] = settings_payload.get('enabled_jobs')

        updated = manager.update_settings(settings_payload)
        success = True
        return updated.to_dict()
    except Exception as e:
        logger.error(f"Error updating settings: {e!s}")
        details['exception'] = str(e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        background_tasks.add_task(
            audit_manager.log_action_background,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            feature=SETTINGS_FEATURE_ID,
            action="UPDATE",
            success=success,
            details=details
        )

@router.get('/settings/llm')
async def get_llm_config():
    """Get LLM configuration (publicly accessible for UI)"""
    try:
        app_settings = get_settings()
        return {
            "enabled": app_settings.LLM_ENABLED,
            "endpoint": app_settings.LLM_ENDPOINT,
            "disclaimer_text": sanitize_markdown_input(app_settings.LLM_DISCLAIMER_TEXT) if app_settings.LLM_DISCLAIMER_TEXT else None,
            # Do not expose system_prompt or injection_check_prompt to frontend
        }
    except Exception as e:
        logger.error(f"Error getting LLM config: {e!s}")
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
    request: Request,
    background_tasks: BackgroundTasks,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    role_data: AppRoleCreate = Body(..., embed=False),
    manager: SettingsManager = Depends(get_settings_manager)
):
    """Create a new application role."""
    success = False
    details = {"role_name": role_data.name}
    try:
        created_role = manager.create_app_role(db=db, role_data=role_data)
        success = True
        if created_role and hasattr(created_role, 'id'):
            details["created_role_id"] = str(created_role.id)
        return created_role
    except ValueError as e:
        logger.warning(f"Validation error creating role '{role_data.name}': {e!s}")
        details["exception"] = str(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating role '{role_data.name}': {e!s}")
        details["exception"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        background_tasks.add_task(
            audit_manager.log_action_background,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            feature=SETTINGS_FEATURE_ID,
            action="CREATE",
            success=success,
            details=details
        )

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
    request: Request,
    background_tasks: BackgroundTasks,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    role_data: AppRole = Body(..., embed=False),
    manager: SettingsManager = Depends(get_settings_manager)
):
    """Update an existing application role."""
    success = False
    details = {"role_id": role_id, "role_name": role_data.name}
    try:
        updated_role = manager.update_app_role(role_id, role_data)
        if updated_role is None:
            details["exception"] = "Role not found"
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        success = True
        return updated_role
    except ValueError as e:
        logger.warning(f"Validation error updating role '{role_id}': {e!s}")
        details["exception"] = str(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating role '{role_id}': {e!s}")
        details["exception"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        background_tasks.add_task(
            audit_manager.log_action_background,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            feature=SETTINGS_FEATURE_ID,
            action="UPDATE",
            success=success,
            details=details
        )

@router.delete("/settings/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    manager: SettingsManager = Depends(get_settings_manager)
):
    """Delete an application role."""
    success = False
    details = {"deleted_role_id": role_id}
    try:
        deleted = manager.delete_app_role(role_id)
        if not deleted:
            details["exception"] = "Role not found"
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        success = True
        return None # Return None for 204
    except ValueError as e: # Catch potential error like deleting admin role
        logger.warning(f"Error deleting role '{role_id}': {e!s}")
        details["exception"] = str(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting role '{role_id}': {e!s}")
        details["exception"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        background_tasks.add_task(
            audit_manager.log_action_background,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            feature=SETTINGS_FEATURE_ID,
            action="DELETE",
            success=success,
            details=details
        )

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


# --- Compliance mapping (object-type policies) ---

@router.get('/settings/compliance-mapping')
async def get_compliance_mapping():
    """Return compliance mapping YAML content as JSON.

    See structure documented in self_service_routes._load_compliance_mapping.
    """
    try:
        from src.common.config import get_config_manager
        cfg = get_config_manager()
        data = cfg.load_yaml('compliance_mapping.yaml')
        return data or {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        logger.error(f"Error loading compliance mapping: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put('/settings/compliance-mapping')
async def save_compliance_mapping(
    payload: Dict[str, Any] = Body(...),
    manager: SettingsManager = Depends(get_settings_manager)
):
    """Persist compliance mapping to YAML."""
    try:
        from src.common.config import get_config_manager
        cfg = get_config_manager()
        cfg.save_yaml('compliance_mapping.yaml', payload)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error saving compliance mapping: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


# --- User Guide ---

@router.get('/user-guide')
async def get_user_guide():
    """Serve the USER-GUIDE.md content"""
    from pathlib import Path
    
    # Path navigates up from routes/settings_routes.py to src/docs
    # __file__ = src/backend/src/routes/settings_routes.py
    # .parent.parent.parent.parent = src/
    guide_path = Path(__file__).parent.parent.parent.parent / "docs" / "USER-GUIDE.md"
    
    # Resolve to absolute path for better error reporting
    resolved_path = guide_path.resolve()
    
    logger.debug(f"Looking for user guide at: {resolved_path}")
    
    if not guide_path.exists():
        logger.error(f"User guide not found. Checked path: {resolved_path}")
        logger.error(f"Current __file__: {Path(__file__).resolve()}")
        logger.error(f"Parent directories: {[p for p in Path(__file__).parents]}")
        raise HTTPException(status_code=404, detail="User guide not found")
    
    try:
        content = guide_path.read_text(encoding="utf-8")
        logger.info(f"Successfully loaded user guide ({len(content)} chars)")
        return {"content": content}
    except Exception as e:
        logger.error(f"Error reading user guide from {resolved_path}: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))
