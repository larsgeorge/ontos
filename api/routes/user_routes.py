import logging

from fastapi import APIRouter, Request, Depends, HTTPException
from databricks.sdk import WorkspaceClient
# We don't need DatabricksUser or SDK errors directly in the route anymore
# from databricks.sdk.service.iam import User as DatabricksUser 
from databricks.sdk.errors import NotFound # Keep NotFound for manager exception handling

from api.models.users import UserInfo 
from api.common.config import get_settings, Settings 
from api.common.logging import setup_logging, get_logger
from api.common.workspace_client import get_workspace_client # Need the client getter for the manager
from api.controller.users_manager import UsersManager # Import the new manager

setup_logging(level=logging.INFO)
logger = get_logger(__name__)

# Define router at the module level with /api prefix
router = APIRouter(prefix="/api", tags=["user"])

# --- Mock Data for Local Dev ---
LOCAL_DEV_USER = UserInfo(
    email="unknown@dev.local",
    username="localdev",
    user="Local Developer",
    ip="127.0.0.1",
    groups=["local-admins", "developers"]
)

# --- Dependency Provider for UsersManager ---
def get_users_manager(
    ws_client: WorkspaceClient = Depends(get_workspace_client) # Inject SDK client
) -> UsersManager:
    """Dependency provider for the UsersManager."""
    return UsersManager(ws_client=ws_client)

# Original endpoint: Get user info directly from headers (with local dev check)
@router.get("/user/info", response_model=UserInfo)
async def get_user_info_from_headers(request: Request, settings: Settings = Depends(get_settings)): # Inject settings
    """Get basic user information directly from request headers, or mock data if local dev."""
    logger.info("Request received for /api/user/info")
    
    # Check for local development environment
    if settings.ENV.upper().startswith("LOCAL"):
        logger.info("Local environment detected, returning mock user data for /user/info.")
        return LOCAL_DEV_USER
        
    # Original logic for non-local environments
    headers = request.headers
    logger.info("Non-local environment, reading headers for /user/info.")
    user_info = UserInfo(
        email=headers.get("X-Forwarded-Email"),
        username=headers.get("X-Forwarded-User"), 
        user=headers.get("X-Forwarded-User"), 
        ip=headers.get("X-Real-Ip")
    )
    logger.info(f"User information from headers: email={user_info.email}, username={user_info.username}, user={user_info.user}, ip={user_info.ip}")
    return user_info

# New endpoint: Get detailed user info using UsersManager (with local dev check)
@router.get("/user/details", response_model=UserInfo)
async def get_user_details_from_sdk(
    request: Request, 
    settings: Settings = Depends(get_settings), 
    manager: UsersManager = Depends(get_users_manager) # Inject the manager
): 
    """
    Retrieves detailed user information via SDK using UsersManager, or mock data if local dev.
    """
    logger.info("Request received for /api/user/details")

    # Check for local development environment
    if settings.ENV.upper().startswith("LOCAL"):
        logger.info("Local environment detected, returning mock user data for /user/details.")
        return LOCAL_DEV_USER

    # Original logic for non-local environments 
    logger.info("Non-local environment, proceeding with SDK lookup via UsersManager for /user/details.")
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
        # Handle specific NotFound error from the manager
        logger.warning(f"User not found via manager for email {user_email}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        # Handle configuration errors (e.g., missing ws_client)
        logger.error(f"Configuration error in UsersManager: {e}")
        raise HTTPException(status_code=500, detail="Server configuration error retrieving user details.")
    except RuntimeError as e:
        # Handle wrapped SDK or unexpected errors from the manager
        logger.error(f"Runtime error from UsersManager for {user_email}: {e}", exc_info=True) 
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user details: {e}")
    except HTTPException: 
        # Re-raise potential 400 from header check above
        raise
    except Exception as e:
        # Catch any other unexpected errors in the route handler itself
        logger.error(f"Unexpected error in /user/details route handler for {user_email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred processing the request.")

# Register routes function simply includes the module-level router
def register_routes(app):
    """Register user routes with the FastAPI app."""
    app.include_router(router)
    logger.info("User routes registered (info and details)")
