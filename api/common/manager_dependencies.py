# api/common/manager_dependencies.py

from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

# Import manager classes
from api.controller.authorization_manager import AuthorizationManager
from api.controller.settings_manager import SettingsManager
from api.controller.users_manager import UsersManager
from api.controller.notifications_manager import NotificationsManager
from api.controller.audit_manager import AuditManager
from api.controller.data_asset_reviews_manager import DataAssetReviewManager
from api.controller.data_products_manager import DataProductsManager

# Import other dependencies needed by these providers
from api.common.database import get_db
from api.common.workspace_client import get_workspace_client
from databricks.sdk import WorkspaceClient
from api.common.logging import get_logger

logger = get_logger(__name__)

# --- Manager Dependency Providers --- #

# Note: These functions now primarily rely on fetching singletons from app.state
# This assumes managers are correctly initialized and stored during app startup.

def get_settings_manager(request: Request) -> SettingsManager:
    settings_manager = getattr(request.app.state, 'settings_manager', None)
    if not settings_manager:
        logger.critical("SettingsManager not found in application state during request!")
        raise HTTPException(status_code=503, detail="Settings service not configured.")
    return settings_manager

def get_auth_manager(request: Request) -> AuthorizationManager:
    auth_manager = getattr(request.app.state, "auth_manager", None)
    if not auth_manager:
        logger.critical("AuthorizationManager not found in application state during request!")
        raise HTTPException(status_code=503, detail="Authorization service not configured.")
    return auth_manager

def get_users_manager(request: Request) -> UsersManager:
    users_manager = getattr(request.app.state, "users_manager", None)
    if not users_manager:
        logger.critical("UsersManager not found in application state during request!")
        raise HTTPException(status_code=503, detail="User details service not configured.")
    return users_manager

def get_notifications_manager(request: Request) -> NotificationsManager:
    manager_instances = getattr(request.app.state, "manager_instances", None)
    if not manager_instances:
        logger.critical("Manager instances dictionary not found in application state!")
        raise HTTPException(status_code=503, detail="Notification service not available.")

    notifications_manager = manager_instances.get('notifications')
    if not notifications_manager:
        logger.critical("NotificationsManager not found in application state during request!")
        raise HTTPException(status_code=503, detail="Notification service not configured.")
    return notifications_manager

def get_audit_manager(request: Request) -> AuditManager:
    audit_manager = getattr(request.app.state, 'audit_manager', None)
    if not audit_manager:
        logger.critical("AuditManager not found in application state during request!")
        raise HTTPException(status_code=503, detail="Audit service not configured.")
    return audit_manager

def get_data_asset_review_manager(request: Request) -> DataAssetReviewManager:
    """Dependency provider for DataAssetReviewManager from app state."""
    manager_instances = getattr(request.app.state, "manager_instances", None)
    if not manager_instances or 'data_asset_reviews' not in manager_instances:
        logger.critical("DataAssetReviewManager not found in application state manager_instances!")
        raise HTTPException(status_code=503, detail="Data Asset Review service not available.")
    return manager_instances['data_asset_reviews']

def get_data_products_manager(request: Request) -> DataProductsManager:
    """Dependency provider for DataProductsManager from app state."""
    # Assumes DataProductsManager is stored in app.state.manager_instances["data_products"]
    # during startup, similar to other managers.
    manager_instances = getattr(request.app.state, "manager_instances", None)
    if not manager_instances:
        logger.critical("Manager instances dictionary not found in application state!")
        raise HTTPException(status_code=503, detail="Data Products service not available (no managers dict).")
    
    data_products_manager = manager_instances.get('data_products')
    if not data_products_manager:
        logger.critical("DataProductsManager not found in application state manager_instances!")
        raise HTTPException(status_code=503, detail="Data Products service not configured.")
    
    # --- Verify Dependencies were injected during startup (Optional but helpful) ---
    # This check assumes __init__ sets _notifications_manager. 
    # It helps catch startup configuration errors earlier.
    if not getattr(data_products_manager, '_notifications_manager', None):
        logger.critical("DataProductsManager found, but NotificationsManager dependency seems missing!")
        # You might raise an exception here, or just log the warning if it can operate without it
        # raise HTTPException(status_code=503, detail="Data Products service is misconfigured (missing notifications).")
    
    return data_products_manager

# --- Add other manager getters if needed --- #
# Example:
# def get_data_products_manager(request: Request) -> DataProductsManager:
#     manager_instances = getattr(request.app.state, "manager_instances", None)
#     if not manager_instances or 'data_products' not in manager_instances:
#         logger.critical("DataProductsManager not found in application state!")
#         raise HTTPException(status_code=503, detail="Data Products service not available.")
#     return manager_instances['data_products'] 