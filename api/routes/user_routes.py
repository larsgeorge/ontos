import logging
from typing import Dict

from fastapi import APIRouter, Request, Depends, HTTPException
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound

from api.models.users import UserInfo
from api.models.users import UserPermissions
from api.models.notifications import Notification, NotificationType
from api.common.config import get_settings, Settings
from api.common.logging import setup_logging, get_logger
from api.controller.authorization_manager import AuthorizationManager
from api.common.dependencies import get_auth_manager
from api.common.dependencies import get_settings_manager, get_notifications_manager
from api.controller.settings_manager import SettingsManager
from api.controller.notifications_manager import NotificationsManager
from api.common.features import FeatureAccessLevel
from api.common.authorization import get_user_details_from_sdk

setup_logging(level=logging.INFO)
logger = get_logger(__name__)

# Define router at the module level with /api prefix
router = APIRouter(prefix="/api", tags=["user"])

# Original endpoint: Get user info directly from headers (with local dev check)
@router.get("/user/info", response_model=UserInfo)
async def get_user_info_from_headers(request: Request, settings: Settings = Depends(get_settings)):
    """Get basic user information directly from request headers, or mock data if local dev."""
    logger.info("Request received for /api/user/info")

    # Check for local development environment
    if settings.ENV.upper().startswith("LOCAL"):
        logger.info("Local environment detected, returning mock user data for /user/info.")
        
        simple_mock_user = UserInfo(
            email="unknown@dev.local",
            username="localdev",
            user="Local Developer",
            ip="127.0.0.1",
            groups=None # This endpoint doesn't provide groups
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
    auth_manager: AuthorizationManager = Depends(get_auth_manager)
) -> Dict[str, FeatureAccessLevel]:
    """Get the effective feature permissions for the current user based on their groups."""
    logger.info(f"Request received for /api/user/permissions for user '{user_details.user or user_details.email}'")

    if not user_details.groups:
        logger.warning(f"User '{user_details.user or user_details.email}' has no groups. Returning empty permissions.")
        
        return {}

    try:
        effective_permissions = auth_manager.get_user_effective_permissions(user_details.groups)
        
        return effective_permissions

    except HTTPException:
        raise # Re-raise exceptions from dependencies
    except Exception as e:
        logger.error(f"Unexpected error calculating permissions for user '{user_details.user or user_details.email}': {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error calculating user permissions."
        )

# --- Role Access Request Endpoint --- 
@router.post("/user/request-role/{role_id}")
async def request_role_access(
    role_id: str,
    request: Request,
    user_details: UserInfo = Depends(get_user_details_from_sdk),
    settings_manager: SettingsManager = Depends(get_settings_manager),
    notifications_manager: NotificationsManager = Depends(get_notifications_manager)
): # Add return type hint? -> dict or status code
    """Initiates a request for a user to be added to an application role."""
    logger.info(f"User '{user_details.email}' requesting access to role ID: {role_id}")

    # Validate user email
    requester_email = user_details.email
    if not requester_email:
         logger.error("Cannot process role request: User email not found in details.")
         raise HTTPException(status_code=400, detail="User email not found, cannot process request.")

    # Get role name
    try:
        role = settings_manager.get_app_role(role_id)
        if not role:
            raise HTTPException(status_code=404, detail=f"Role with ID '{role_id}' not found.")
        role_name = role.name
    except Exception as e:
        logger.error(f"Error retrieving role {role_id}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving role details.")

    try:
        # 1. Create notification for the requester
        user_notification = Notification(
            type=NotificationType.INFO,
            title="Role Access Request Submitted",
            subtitle=f"Role: {role_name}",
            description=f"Your request to access the role '{role_name}' has been submitted for review.",
            recipient=requester_email, # Target specific user
            can_delete=True
        )
        notifications_manager.create_notification(user_notification)
        logger.info(f"Created notification for requester '{requester_email}'")

        # 2. Create notification for Admins
        admin_notification = Notification(
            type=NotificationType.ACTION_REQUIRED,
            title="Role Access Request Received",
            subtitle=f"User: {requester_email}",
            description=f"User '{requester_email}' has requested access to the role '{role_name}'.",
            recipient="Admin", # Target the Admin role/group
            can_delete=False, # Admins shouldn't delete this easily
            # TODO: Add action payload later
            # action_type="handle_role_request",
            # action_payload={"requester_email": requester_email, "role_id": role_id, "role_name": role_name}
            # Add action details
            action_type="handle_role_request",
            action_payload={"requester_email": requester_email, "role_id": role_id, "role_name": role_name}
        )
        notifications_manager.create_notification(admin_notification)
        logger.info(f"Created notification for Admin role recipients")

        return {"message": "Role access request submitted successfully."} # Or status 202 Accepted?

    except Exception as e:
        logger.error(f"Error creating notifications for role request (Role: {role_id}, User: {requester_email}): {e}", exc_info=True)
        # Don't expose internal errors directly
        raise HTTPException(status_code=500, detail="Failed to process role access request due to an internal error.")

# Register routes function simply includes the module-level router
def register_routes(app):
    """Register user routes with the FastAPI app."""
    app.include_router(router)
    logger.info("User routes registered (info and details)")
