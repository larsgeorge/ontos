import uuid # Import uuid
from datetime import datetime # Import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Request, Depends, HTTPException
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound

from src.models.users import UserInfo
from src.models.users import UserPermissions
from src.models.notifications import Notification, NotificationType
from src.common.config import get_settings, Settings
from src.controller.authorization_manager import AuthorizationManager
from src.common.dependencies import get_auth_manager, get_db # Import get_db
from src.common.dependencies import get_settings_manager, get_notifications_manager
from src.controller.settings_manager import SettingsManager
from pydantic import BaseModel
from src.controller.notifications_manager import NotificationsManager
from src.common.features import FeatureAccessLevel
from src.common.authorization import get_user_details_from_sdk
from sqlalchemy.orm import Session # Import Session

from src.common.logging import get_logger
from src.common.deployment_dependencies import get_deployment_policy_manager
from src.controller.deployment_policy_manager import DeploymentPolicyManager

logger = get_logger(__name__)

# Define router at the module level with /api prefix
router = APIRouter(prefix="/api", tags=["user"])

# Original endpoint: Get user info directly from headers (with local dev check)
@router.get("/user/info", response_model=UserInfo)
async def get_user_info_from_headers(request: Request, settings: Settings = Depends(get_settings)):
    """Get basic user information directly from request headers, or mock data if local dev."""
    logger.info("Request received for /api/user/info")

    # Check for local development environment
    if settings.ENV.upper().startswith("LOCAL") or getattr(settings, "MOCK_USER_DETAILS", False):
        # Build from overrides consistent with get_user_details_from_sdk
        email = settings.MOCK_USER_EMAIL or "unknown@dev.local"
        username = settings.MOCK_USER_USERNAME or "localdev"
        name = settings.MOCK_USER_NAME or "Local Developer"
        ip = settings.MOCK_USER_IP or "127.0.0.1"
        logger.info(
            f"Local/mock /user/info: using overrides(email={email}, username={username}, user={name}, ip={ip})"
        )
        simple_mock_user = UserInfo(
            email=email,
            username=username,
            user=name,
            ip=ip,
            groups=None # This endpoint doesn't include groups
        )
        return simple_mock_user

    # Original logic for non-local environments
    headers = request.headers
    logger.info("Non-local environment, reading headers for /user/info.")
    user_info = UserInfo(
        email=headers.get("X-Forwarded-Email"),
        username=headers.get("X-Forwarded-User"),
        user=headers.get("X-Forwarded-User"),
        ip=headers.get("X-Real-Ip"),
        groups=None # Headers don't contain groups
    )
    logger.info(f"User information from headers: email={user_info.email}, username={user_info.username}, user={user_info.user}, ip={user_info.ip}")
    return user_info

# --- User Details Endpoint (using the dependency) --- 
@router.get("/user/details", response_model=UserInfo)
async def get_user_details(
    user_info: UserInfo = Depends(get_user_details_from_sdk)
) -> UserInfo:
    """Returns detailed user information obtained via the SDK (or mock data)."""
    # The dependency get_user_details_from_sdk handles fetching or mocking.
    # We just return the result provided by the dependency.
    # The dependency also handles raising HTTPException on errors.
    logger.info(f"Returning user details for '{user_info.user or user_info.email}' from dependency.")
    return user_info

# --- User Permissions Endpoint --- 

@router.get("/user/permissions", response_model=UserPermissions)
async def get_current_user_permissions(
    request: Request,
    user_details: UserInfo = Depends(get_user_details_from_sdk),
    auth_manager: AuthorizationManager = Depends(get_auth_manager),
    settings_manager: SettingsManager = Depends(get_settings_manager)
) -> Dict[str, FeatureAccessLevel]:
    """Get the effective feature permissions for the current user based on their groups."""
    logger.info(f"Request received for /api/user/permissions for user '{user_details.user or user_details.email}'")

    if not user_details.groups:
        logger.warning(f"User '{user_details.user or user_details.email}' has no groups. Returning empty permissions.")
        
        return {}

    try:
        # Apply override if set for this user
        applied_role_id = settings_manager.get_applied_role_override_for_user(user_details.email)
        if applied_role_id:
            role_perms = settings_manager.get_feature_permissions_for_role_id(applied_role_id)
            return role_perms
        # Otherwise compute from groups
        return auth_manager.get_user_effective_permissions(user_details.groups)

    except HTTPException:
        raise # Re-raise exceptions from dependencies
    except Exception as e:
        logger.error(f"Unexpected error calculating permissions for user '{user_details.user or user_details.email}': {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error calculating user permissions."
        )

# --- Role override endpoints ---
class RoleOverrideRequest(BaseModel):
    role_id: Optional[str] = None

@router.post("/user/role-override")
async def set_role_override(
    payload: RoleOverrideRequest,
    user_details: UserInfo = Depends(get_user_details_from_sdk),
    settings_manager: SettingsManager = Depends(get_settings_manager)
):
    """Set or clear the applied role override for the current user.

    Body: { "role_id": "<uuid>" } or { "role_id": null } to clear.
    """
    role_id = payload.role_id
    try:
        settings_manager.set_applied_role_override_for_user(user_details.email, role_id)
        return {"status": "ok"}
    except ValueError as e:
        logger.error("Invalid role override request for user %s: %s", user_details.email, e)
        raise HTTPException(status_code=400, detail="Invalid role override request")

@router.get("/user/role-override")
async def get_role_override(
    user_details: UserInfo = Depends(get_user_details_from_sdk),
    settings_manager: SettingsManager = Depends(get_settings_manager)
):
    """Return the currently applied role override id for the user (or null)."""
    role_id = settings_manager.get_applied_role_override_for_user(user_details.email)
    return {"role_id": role_id}

@router.get("/user/actual-role")
async def get_actual_role(
    user_details: UserInfo = Depends(get_user_details_from_sdk),
    settings_manager: SettingsManager = Depends(get_settings_manager)
):
    """Return the canonical role determined from the user's groups (ignores override)."""
    role = settings_manager.get_canonical_role_for_groups(user_details.groups)
    return {"role": role.dict() if role else None}

# --- Role Access Request Endpoint --- 
@router.post("/user/request-role/{role_id}")
async def request_role_access(
    role_id: str,
    request: Request,
    db: Session = Depends(get_db), # Inject DB session
    user_details: UserInfo = Depends(get_user_details_from_sdk),
    settings_manager: SettingsManager = Depends(get_settings_manager),
    notifications_manager: NotificationsManager = Depends(get_notifications_manager)
): 
    """Initiates a request for a user to be added to an application role."""
    logger.info(f"User '{user_details.email}' requesting access to role ID: {role_id}")

    requester_email = user_details.email
    if not requester_email:
         logger.error("Cannot process role request: User email not found in details.")
         raise HTTPException(status_code=400, detail="User email not found, cannot process request.")

    try:
        role = settings_manager.get_app_role(role_id)
        if not role:
            raise HTTPException(status_code=404, detail=f"Role with ID '{role_id}' not found.")
        role_name = role.name
    except Exception as e:
        logger.error(f"Error retrieving role {role_id}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving role details.")

    # Generate placeholder values for required fields
    placeholder_id = str(uuid.uuid4()) # Generate a unique placeholder ID
    now = datetime.utcnow()

    try:
        # 1. Create notification for the requester
        user_notification = Notification(
            id=placeholder_id, # Provide placeholder
            created_at=now, # Provide placeholder
            type=NotificationType.INFO,
            title="Role Access Request Submitted",
            subtitle=f"Role: {role_name}",
            description=f"Your request to access the role '{role_name}' has been submitted for review.",
            recipient=requester_email, 
            can_delete=True
        )
        # Pass db session to the manager
        notifications_manager.create_notification(db=db, notification=user_notification)
        logger.info(f"Created notification for requester '{requester_email}'")

        # 2. Create notification for Admins
        admin_notification = Notification(
            id=str(uuid.uuid4()), # Generate another placeholder ID
            created_at=now, # Provide placeholder
            type=NotificationType.ACTION_REQUIRED,
            title="Role Access Request Received",
            subtitle=f"User: {requester_email}",
            description=f"User '{requester_email}' has requested access to the role '{role_name}'.",
            recipient="Admin", 
            can_delete=False, 
            action_type="handle_role_request",
            action_payload={"requester_email": requester_email, "role_id": role_id, "role_name": role_name}
        )
        # Pass db session to the manager
        notifications_manager.create_notification(db=db, notification=admin_notification)
        logger.info(f"Created notification for Admin role recipients")

        db.commit() # Commit the transaction after both notifications are added
        return {"message": "Role access request submitted successfully."} 

    except Exception as e:
        logger.error(f"Error creating notifications for role request (Role: {role_id}, User: {requester_email}): {e}", exc_info=True)
        db.rollback() # Rollback the transaction on error
        raise HTTPException(status_code=500, detail="Failed to process role access request due to an internal error.")


# --- Deployment Policy Endpoint ---

@router.get("/user/deployment-policy")
async def get_user_deployment_policy(
    user_details: UserInfo = Depends(get_user_details_from_sdk),
    deployment_manager: DeploymentPolicyManager = Depends(get_deployment_policy_manager)
):
    """Get current user's deployment policy (allowed catalogs/schemas).
    
    Returns the effective deployment policy after:
    - Resolving role overrides
    - Merging policies from all user's groups
    - Resolving template variables ({username}, {email}, etc.)
    """
    try:
        policy = deployment_manager.get_effective_policy(user_details)
        
        logger.info(
            f"Retrieved deployment policy for {user_details.email}: "
            f"{len(policy.allowed_catalogs)} catalogs, "
            f"require_approval={policy.require_approval}"
        )
        
        return policy.dict()
    
    except Exception as e:
        logger.error(f"Error retrieving deployment policy for {user_details.email}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve deployment policy"
        )


# Register routes function simply includes the module-level router
def register_routes(app):
    """Register user routes with the FastAPI app."""
    app.include_router(router)
    logger.info("User routes registered (info and details)")
