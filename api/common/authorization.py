from typing import Optional, Dict, List

from fastapi import Depends, HTTPException, Request, status

from api.controller.authorization_manager import AuthorizationManager
from api.models.users import UserInfo
from api.common.features import FeatureAccessLevel
from api.common.logging import get_logger
# Import dependencies for user info and managers (adjust paths if needed)
# from api.routes.user_routes import get_user_details_from_sdk # REMOVE this import
# Import dependencies needed for the moved function
from databricks.sdk.errors import NotFound
from api.controller.users_manager import UsersManager
from api.common.config import Settings, get_settings # Import Settings and get_settings
# Import from the new dependencies file
from api.common.manager_dependencies import get_auth_manager, get_users_manager
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import ( # Import specific errors for handling
    Unauthenticated, PermissionDenied, NotFound as DatabricksNotFound
)
from api.common.workspace_client import get_workspace_client # Ensure this is available
from databricks.sdk.service.iam import Group # Try importing Group instead of UserGroup

logger = get_logger(__name__)

# Local Dev Mock User (keep here for the dependency function)
LOCAL_DEV_USER = UserInfo(
    email="unknown@dev.local",
    username="localdev",
    user="Local Developer",
    ip="127.0.0.1",
    groups=["admins", "local-admins", "developers"] # Added 'admins' for testing
)

# --- Dependency to get CURRENT END USER --- 
async def get_current_user(
    request: Request, 
    settings: Settings = Depends(get_settings)
) -> UserInfo:
    """Dependency to get END USER info (email, groups) primarily from request headers.
       Uses UsersManager to get full details for the header-identified user.
       Falls back to LOCAL_DEV_USER if configured for local/mocking.
    """
    client_ip: Optional[str] = None
    if request.client:
        client_ip = request.client.host

    # Handle local development and mock user scenarios first
    if settings.ENV.upper().startswith("LOCAL") or settings.MOCK_USER_DETAILS:
        logger.info("get_current_user: LOCAL/MOCK environment, returning LOCAL_DEV_USER.")
        local_dev_user_with_ip = LOCAL_DEV_USER.model_copy(update={"ip": client_ip or LOCAL_DEV_USER.ip})
        return local_dev_user_with_ip

    # Try to get the end-user\'s email from Databricks-injected headers
    user_email_from_header = request.headers.get("Databricks-User-Email") or request.headers.get("X-Databricks-User-Email")

    if not user_email_from_header:
        logger.error("get_current_user: User email not found in Databricks request headers. Cannot identify end-user.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="User identity not found in request headers. Ensure the app is run within Databricks App environment."
        )
    
    logger.info(f"get_current_user: User email from header: {user_email_from_header}. Fetching details via UsersManager.")

    users_manager: Optional[UsersManager] = getattr(request.app.state, 'users_manager', None)
    if not users_manager:
        logger.critical("get_current_user: UsersManager not found in app.state. Cannot fetch user details.")
        raise HTTPException(status_code=503, detail="User management service is not available.")

    try:
        end_user_info = users_manager.get_user_details_by_email(user_email_from_header, real_ip=client_ip)
        logger.info(f"get_current_user: Successfully fetched details for {end_user_info.username} via UsersManager.")
        return end_user_info
    except NotFound:
        logger.error(f"get_current_user: User '{user_email_from_header}' identified from header not found in Databricks workspace by UsersManager.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"User {user_email_from_header} not found in workspace.")
    except ValueError as ve:
        logger.error(f"get_current_user: ValueError from UsersManager for {user_email_from_header}: {ve}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(ve))
    except RuntimeError as re:
        logger.error(f"get_current_user: RuntimeError from UsersManager for {user_email_from_header}: {re}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(re))
    except Exception as e:
        logger.error(f"get_current_user: Unexpected error fetching details for {user_email_from_header} via UsersManager: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve detailed user information.")

# get_user_details_from_sdk can be defined before or after get_current_user, but before PermissionChecker if it were used by it (it is not)
async def get_user_details_from_sdk(
    request: Request,
    settings_override: Optional[Settings] = None,
) -> UserInfo:
    """Fetches user details (username, groups, email) from Databricks SDK or returns mock data.
    
    Prioritizes settings_override. If not provided, attempts to get settings via Depends mechanism
    (primarily for route context) or falls back to request.app.state.settings (for middleware context).
    """
    current_settings = settings_override
    if not current_settings:
        # Try to get from request.app.state if available (e.g., in middleware or already resolved routes)
        current_settings = getattr(request.app.state, 'settings', None)
        
    if not current_settings:
        # If settings are still not available, it's a critical configuration error.
        # This function expects settings to be available either via override or app.state.settings.
        logger.critical("get_user_details_from_sdk: Settings not available through override or request.app.state.settings.")
        raise HTTPException(status_code=503, detail="Application configuration for settings not available.")

    if current_settings.ENV.upper().startswith("LOCAL") or current_settings.MOCK_USER_DETAILS:
        logger.info("Local environment or MOCK_USER_DETAILS=True detected, returning LOCAL_DEV_USER.")
        return LOCAL_DEV_USER # Use the predefined LOCAL_DEV_USER object
    
    # In a real Databricks App environment, use the SDK
    # Get WorkspaceClient here to avoid making it a top-level param that middleware has to resolve
    try:
        # Correctly pass current_settings to get_workspace_client
        ws_client = get_workspace_client(settings=current_settings) 
    except Exception as e:
        logger.error(f"Failed to get WorkspaceClient in get_user_details_from_sdk: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Workspace client configuration error.")

    try:
        current_user_sdk = ws_client.current_user.me()
        
        groups: List[str] = []
        if current_user_sdk.groups:
            # Assuming current_user_sdk.groups is a list of Group objects with a 'display' attribute
            groups = [group.display for group in current_user_sdk.groups if group.display]
        
        # Attempt to get client IP from request
        client_ip: Optional[str] = None
        if request.client:
            client_ip = request.client.host

        user_info = UserInfo(
            username=current_user_sdk.user_name,
            email=current_user_sdk.emails[0].value if current_user_sdk.emails and len(current_user_sdk.emails) > 0 else None,
            groups=groups,
            user=current_user_sdk.display_name,
            active=current_user_sdk.active,
            ip=client_ip # Populate IP from request
        )
        logger.debug(f"Fetched user details from SDK: {user_info.username}, Groups: {user_info.groups}, IP: {user_info.ip}")
        return user_info

    except Unauthenticated as e:
        logger.error(f"Databricks SDK Unauthenticated error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Databricks authentication failed: {e}")
    except PermissionDenied as e:
        logger.error(f"Databricks SDK PermissionDenied error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Databricks permission denied: {e}")
    except DatabricksNotFound as e:
        logger.error(f"Databricks SDK NotFound error (e.g., user not found): {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Databricks resource not found: {e}")
    except Exception as e:
        logger.error(f"Unexpected error fetching user details from Databricks SDK: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve user information from Databricks.")


class PermissionChecker:
    """FastAPI Dependency to check user permissions for a feature."""
    def __init__(self, feature_id: str, required_level: FeatureAccessLevel):
        self.feature_id = feature_id
        self.required_level = required_level
        logger.debug(f"PermissionChecker initialized for feature '{self.feature_id}' requiring level '{self.required_level.value}'")

    async def __call__(
        self,
        request: Request, # Inject request to potentially access app state
        user_details: UserInfo = Depends(get_current_user), # Now get_current_user is defined
        auth_manager: AuthorizationManager = Depends(get_auth_manager)
    ):
        """Performs the permission check when the dependency is called."""
        logger.debug(f"Checking permission for feature '{self.feature_id}' (level: '{self.required_level.value}') for user '{user_details.user or user_details.email}'")

        if not user_details.groups:
            logger.warning(f"User '{user_details.user or user_details.email}' has no groups. Denying access for '{self.feature_id}'.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no assigned groups, cannot determine permissions."
            )

        try:
            effective_permissions = auth_manager.get_user_effective_permissions(user_details.groups)
            has_required_permission = auth_manager.has_permission(
                effective_permissions,
                self.feature_id,
                self.required_level
            )

            if not has_required_permission:
                user_level = effective_permissions.get(self.feature_id, FeatureAccessLevel.NONE)
                logger.warning(
                    f"Permission denied for user '{user_details.user or user_details.email}' "
                    f"on feature '{self.feature_id}'. Required: '{self.required_level.value}', Found: '{user_level.value}'"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions for feature '{self.feature_id}'. Required level: {self.required_level.value}."
                )

            logger.debug(f"Permission granted for user '{user_details.user or user_details.email}' on feature '{self.feature_id}'")
            # If permission is granted, the dependency resolves successfully (returns None implicitly)
            return

        except HTTPException:
            raise # Re-raise exceptions from dependencies (like 503 from get_auth_manager)
        except Exception as e:
            logger.error(f"Unexpected error during permission check for feature '{self.feature_id}': {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error checking user permissions."
            )

# --- Pre-configured Dependency Instances (Optional but convenient) ---
# You can create instances here for common permission levels

def require_admin(feature_id: str) -> PermissionChecker:
    return PermissionChecker(feature_id, FeatureAccessLevel.ADMIN)

def require_read_write(feature_id: str) -> PermissionChecker:
    return PermissionChecker(feature_id, FeatureAccessLevel.READ_WRITE)

def require_read_only(feature_id: str) -> PermissionChecker:
    return PermissionChecker(feature_id, FeatureAccessLevel.READ_ONLY)

# Example for a feature-specific check
def require_data_product_read() -> PermissionChecker:
    return PermissionChecker('data-products', FeatureAccessLevel.READ_ONLY) 