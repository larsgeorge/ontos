from fastapi import Request, HTTPException, status, Depends
from typing import Optional

from api.controller.authorization_manager import AuthorizationManager
from api.controller.settings_manager import SettingsManager
from api.controller.users_manager import UsersManager
from api.common.logging import get_logger
# Import DB session dependency
from api.common.database import get_db
from sqlalchemy.orm import Session
# Import Workspace Client dependency
from api.common.workspace_client import get_workspace_client
from databricks.sdk import WorkspaceClient

logger = get_logger(__name__)

# --- Manager Dependency Providers ---

def get_settings_manager(
    db: Session = Depends(get_db),
    client: Optional[WorkspaceClient] = Depends(get_workspace_client)
) -> SettingsManager:
    """Dependency provider for SettingsManager, injecting DB session and WorkspaceClient."""
    # Attempt to get from state first (if singleton pattern is fully enforced)
    # settings_manager = request.app.state.get("settings_manager")
    # if settings_manager:
    #     return settings_manager
    # Fallback to creating - though this might bypass the singleton pattern
    # logger.warning("Creating new SettingsManager instance via dependency, check singleton pattern.")
    # This should ideally use the singleton from app.state, but FastAPI dependencies
    # are often resolved before app state is fully populated in all contexts.
    # Relying on app.state within the dependency provider itself requires injecting `request`.
    # For simplicity now, let's assume the startup guarantees the state is set,
    # or we accept potentially new instances if called outside request context (less ideal).

    # Let's stick to direct instantiation for now, matching how other managers were likely intended
    # to be injected before the singleton pattern was fully applied.
    # Reverting to direct instantiation as singletons via Depends is complex
    return SettingsManager(db=db, workspace_client=client)

def get_auth_manager(
    request: Request, # Inject request to access app state
    settings_manager: SettingsManager = Depends(get_settings_manager) # Depend on settings manager
) -> AuthorizationManager:
    """Dependency provider for AuthorizationManager."""
    # Use the singleton stored in app.state
    # Corrected access using getattr
    auth_manager = getattr(request.app.state, "auth_manager", None)
    if not auth_manager:
        # Raise error if not found in state - implies startup issue
        logger.critical("AuthorizationManager not found in application state during request!")
        raise HTTPException(status_code=503, detail="Authorization service not configured.")
    return auth_manager

def get_users_manager(
    request: Request, # Inject request to access app state
    ws_client: Optional[WorkspaceClient] = Depends(get_workspace_client)
) -> UsersManager:
    """Dependency provider for UsersManager."""
    # Use the singleton stored in app.state
    # Corrected access using getattr
    users_manager = getattr(request.app.state, "users_manager", None)
    if not users_manager:
        # Raise error if not found in state - implies startup issue
        logger.critical("UsersManager not found in application state during request!")
        raise HTTPException(status_code=503, detail="User details service not configured.")
    return users_manager 