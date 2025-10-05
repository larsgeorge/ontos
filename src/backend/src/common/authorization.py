from typing import Optional, Dict, List

from fastapi import Depends, HTTPException, Request, status

from src.controller.authorization_manager import AuthorizationManager
from src.models.users import UserInfo
from src.common.features import FeatureAccessLevel
from src.common.logging import get_logger
from src.common.database import get_db
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
    # Check for local development environment or explicit mock flag
    if settings.ENV.upper().startswith("LOCAL") or getattr(settings, "MOCK_USER_DETAILS", False):
        logger.info("Local/mock user mode detected, returning mock user data for dependency.")
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


async def get_user_groups(user_email: str) -> List[str]:
    """Get user groups for the given user email."""
    # Get settings directly instead of using dependency injection
    settings = get_settings()

    if settings.ENV.upper().startswith("LOCAL"):
        # Return mock groups for local development
        return LOCAL_DEV_USER.groups

    # In production, you would get groups from the user details
    # For now, returning empty list as fallback
    return []


async def get_user_team_role_overrides(user_identifier: str, user_groups: List[str], request: Request) -> Optional[str]:
    """Get the highest team role override for a user."""
    try:
        # Get teams manager from app state
        teams_manager = getattr(request.app.state, 'teams_manager', None)
        if not teams_manager:
            logger.debug("Teams manager not available in app state")
            return None

        # Get database session
        db = next(get_db())
        try:
            # Get teams where user is a member
            user_teams = teams_manager.get_teams_for_user(db, user_identifier)

            # Collect all role overrides for this user across teams
            role_overrides = []
            for team in user_teams:
                for member in team.members:
                    if member.member_identifier == user_identifier and member.app_role_override:
                        role_overrides.append(member.app_role_override)

            # Also check group memberships
            for team in user_teams:
                for member in team.members:
                    if member.member_identifier in user_groups and member.app_role_override:
                        role_overrides.append(member.app_role_override)

            if not role_overrides:
                return None

            # Return the highest role override (assuming role names have hierarchical order)
            # For now, just return the first one found - in practice you'd need proper role hierarchy
            logger.debug(f"Found team role overrides for user {user_identifier}: {role_overrides}")
            return role_overrides[0]

        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Error checking team role overrides for user {user_identifier}: {e}")
        return None


async def check_user_project_access(user_identifier: str, user_groups: List[str], project_id: str, request: Request) -> bool:
    """Check if a user has access to a specific project."""
    try:
        # Get projects manager from app state
        projects_manager = getattr(request.app.state, 'projects_manager', None)
        if not projects_manager:
            logger.debug("Projects manager not available in app state")
            return False

        # Get database session
        db = next(get_db())
        try:
            # Check if user has access to the project
            return projects_manager.check_user_project_access(db, user_identifier, user_groups, project_id)
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Error checking project access for user {user_identifier} to project {project_id}: {e}")
        return False


class ProjectAccessChecker:
    """FastAPI Dependency to check user access to a specific project."""
    def __init__(self, project_id_param: str = "project_id"):
        self.project_id_param = project_id_param
        logger.debug(f"ProjectAccessChecker initialized for parameter '{self.project_id_param}'")

    async def __call__(
        self,
        request: Request,
        user_details: UserInfo = Depends(get_user_details_from_sdk)
    ):
        """Performs the project access check when the dependency is called."""
        # Extract project_id from path parameters
        project_id = request.path_params.get(self.project_id_param)
        if not project_id:
            logger.warning(f"Project ID parameter '{self.project_id_param}' not found in request")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project ID parameter '{self.project_id_param}' not found"
            )

        logger.debug(f"Checking project access for user '{user_details.email}' to project '{project_id}'")

        user_groups = user_details.groups or []
        has_access = await check_user_project_access(
            user_details.email,
            user_groups,
            project_id,
            request
        )

        if not has_access:
            logger.warning(
                f"Project access denied for user '{user_details.email}' to project '{project_id}'"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to project '{project_id}'"
            )

        logger.debug(f"Project access granted for user '{user_details.email}' to project '{project_id}'")
        return


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
            # Check for team role overrides
            team_role_override = await get_user_team_role_overrides(
                user_details.email,
                user_details.groups or [],
                request
            )

            # Check if an explicit role override is applied for this user
            applied_role_id = None
            try:
                settings_manager = getattr(request.app.state, 'settings_manager', None)
                if settings_manager:
                    applied_role_id = settings_manager.get_applied_role_override_for_user(user_details.email)
            except Exception:
                applied_role_id = None

            if applied_role_id and settings_manager:
                # Build effective permissions directly from the selected role
                effective_permissions = settings_manager.get_feature_permissions_for_role_id(applied_role_id)
            else:
                effective_permissions = auth_manager.get_user_effective_permissions(
                    user_details.groups,
                    team_role_override
                )
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

# Project access convenience functions
def require_project_access(project_id_param: str = "project_id") -> ProjectAccessChecker:
    return ProjectAccessChecker(project_id_param) 