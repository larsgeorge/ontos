from typing import Optional, Dict, List

from fastapi import Depends, HTTPException, Request, status

from src.controller.authorization_manager import AuthorizationManager
from src.models.users import UserInfo
from src.common.features import FeatureAccessLevel
from src.common.logging import get_logger
# Import dependencies for user info and managers (adjust paths if needed)
# from src.routes.user_routes import get_user_details_from_sdk # REMOVE this import
# Import dependencies needed for the moved function
from databricks.sdk.errors import NotFound
from src.controller.users_manager import UsersManager
from src.common.config import get_settings, Settings
# Import from the new dependencies file
from src.common.manager_dependencies import get_auth_manager, get_users_manager

logger = get_logger(__name__)

# Local Dev Mock User (keep here for the dependency function)
LOCAL_DEV_USER = UserInfo(
    email="unknown@dev.local",
    username="localdev",
    user="Local Developer",
    ip="127.0.0.1",
    groups=["admins", "local-admins", "developers"] # Added 'admins' for testing
)

async def get_user_details_from_sdk(
    request: Request,
    settings: Settings = Depends(get_settings),
    manager: UsersManager = Depends(get_users_manager)
) -> UserInfo:
    """
    Retrieves detailed user information via SDK using UsersManager, or mock data if local dev.
    (Moved from user_routes.py to break circular import)
    """
    # Check for local development environment
    if settings.ENV.upper().startswith("LOCAL"):
        logger.info("Local environment detected, returning mock user data for dependency.")
        # Ensure mock user has groups for testing permissions
        return LOCAL_DEV_USER

    # Logic for non-local environments
    logger.debug("Non-local environment, proceeding with SDK lookup via UsersManager.")
    user_email = request.headers.get("X-Forwarded-Email")
    if not user_email:
        user_email = request.headers.get("X-Forwarded-User")

    if not user_email:
        logger.error("Could not find user email in request headers (X-Forwarded-Email or X-Forwarded-User) for SDK lookup.")
        raise HTTPException(status_code=400, detail="User email not found in request headers for SDK lookup.")

    real_ip = request.headers.get("X-Real-Ip")

    try:
        # Call the manager method
        user_info_response = manager.get_user_details_by_email(user_email=user_email, real_ip=real_ip)
        return user_info_response

    except NotFound as e:
        logger.warning(f"User not found via manager for email {user_email}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.error(f"Configuration error in UsersManager: {e}")
        raise HTTPException(status_code=500, detail="Server configuration error retrieving user details.")
    except RuntimeError as e:
        logger.error(f"Runtime error from UsersManager for {user_email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user details: {e}")
    except HTTPException:
        raise # Re-raise potential 400 from header check above
    except Exception as e:
        logger.error(f"Unexpected error in get_user_details_from_sdk dependency for {user_email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred processing the user details request.")


class PermissionChecker:
    """FastAPI Dependency to check user permissions for a feature."""
    def __init__(self, feature_id: str, required_level: FeatureAccessLevel):
        self.feature_id = feature_id
        self.required_level = required_level
        logger.debug(f"PermissionChecker initialized for feature '{self.feature_id}' requiring level '{self.required_level.value}'")

    async def __call__(
        self,
        request: Request, # Inject request to potentially access app state
        user_details: UserInfo = Depends(get_user_details_from_sdk), # Now uses local function
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