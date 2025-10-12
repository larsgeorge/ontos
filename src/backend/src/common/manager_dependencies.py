# api/common/manager_dependencies.py

from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

# Import manager classes
from src.controller.authorization_manager import AuthorizationManager
from src.controller.settings_manager import SettingsManager
from src.controller.users_manager import UsersManager
from src.controller.notifications_manager import NotificationsManager
from src.controller.audit_manager import AuditManager
from src.controller.data_asset_reviews_manager import DataAssetReviewManager
from src.controller.data_products_manager import DataProductsManager
from src.controller.data_domains_manager import DataDomainManager
# Add imports for other managers if they need dependency getters
from src.controller.data_contracts_manager import DataContractsManager
from src.controller.semantic_models_manager import SemanticModelsManager
from src.controller.search_manager import SearchManager
from src.controller.semantic_models_manager import SemanticModelsManager
from src.controller.metadata_manager import MetadataManager
from src.controller.comments_manager import CommentsManager
from src.controller.jobs_manager import JobsManager

# Import other dependencies needed by these providers
from src.common.database import get_db
from src.common.workspace_client import get_workspace_client
from databricks.sdk import WorkspaceClient
from src.common.logging import get_logger

logger = get_logger(__name__)

# --- Manager Dependency Providers (Fetching directly from app.state) --- #

def get_settings_manager(request: Request) -> SettingsManager:
    manager = getattr(request.app.state, 'settings_manager', None)
    if not manager:
        logger.critical("SettingsManager not found in application state during request!")
        raise HTTPException(status_code=503, detail="Settings service not configured.")
    return manager

def get_auth_manager(request: Request) -> AuthorizationManager:
    manager = getattr(request.app.state, "authorization_manager", None) # Corrected attribute name
    if not manager:
        logger.critical("AuthorizationManager not found in application state during request!")
        raise HTTPException(status_code=503, detail="Authorization service not configured.")
    return manager

def get_users_manager(request: Request) -> UsersManager:
    manager = getattr(request.app.state, "users_manager", None)
    if not manager:
        logger.critical("UsersManager not found in application state during request!")
        raise HTTPException(status_code=503, detail="User details service not configured.")
    return manager

def get_notifications_manager(request: Request) -> NotificationsManager:
    manager = getattr(request.app.state, "notifications_manager", None)
    if not manager:
        logger.critical("NotificationsManager not found in application state during request!")
        raise HTTPException(status_code=503, detail="Notification service not configured.")
    return manager

def get_audit_manager(request: Request) -> AuditManager:
    manager = getattr(request.app.state, 'audit_manager', None)
    if not manager:
        logger.critical("AuditManager not found in application state during request!")
        raise HTTPException(status_code=503, detail="Audit service not configured.")
    return manager

def get_data_asset_review_manager(request: Request) -> DataAssetReviewManager:
    manager = getattr(request.app.state, "data_asset_review_manager", None)
    if not manager:
        logger.critical("DataAssetReviewManager not found in application state!")
        raise HTTPException(status_code=503, detail="Data Asset Review service not available.")
    return manager

def get_data_products_manager(request: Request) -> DataProductsManager:
    manager = getattr(request.app.state, "data_products_manager", None)
    if not manager:
        logger.critical("DataProductsManager not found in application state!")
        raise HTTPException(status_code=503, detail="Data Products service not configured.")
    return manager

def get_data_domain_manager(request: Request) -> DataDomainManager:
    manager = getattr(request.app.state, 'data_domain_manager', None)
    if not manager:
        logger.critical("DataDomainManager not found in application state during request!")
        raise HTTPException(status_code=503, detail="Data Domain service not configured.")
    return manager

# --- Add getters for other managers stored in app.state --- #
def get_data_contracts_manager(request: Request) -> DataContractsManager:
    manager = getattr(request.app.state, 'data_contracts_manager', None)
    if not manager:
        logger.critical("DataContractsManager not found in application state during request!")
        raise HTTPException(status_code=503, detail="Data Contracts service not configured.")
    return manager

def get_semantic_models_manager(request: Request) -> SemanticModelsManager:
    manager = getattr(request.app.state, 'semantic_models_manager', None)
    if not manager:
        logger.critical("SemanticModelsManager not found in application state during request!")
        raise HTTPException(status_code=503, detail="Semantic Models service not configured.")
    return manager

def get_search_manager(request: Request) -> SearchManager:
    manager = getattr(request.app.state, 'search_manager', None)
    if not manager:
        logger.critical("SearchManager not found in application state during request!")
        raise HTTPException(status_code=503, detail="Search service not configured.")
    return manager

def get_semantic_models_manager(request: Request) -> SemanticModelsManager:
    manager = getattr(request.app.state, 'semantic_models_manager', None)
    if not manager:
        logger.critical("SemanticModelsManager not found in application state during request!")
        raise HTTPException(status_code=503, detail="Semantic Models service not configured.")
    return manager

def get_metadata_manager(request: Request) -> MetadataManager:
    manager = getattr(request.app.state, 'metadata_manager', None)
    if not manager:
        # Instantiate lazily and cache on app.state
        manager = MetadataManager()
        setattr(request.app.state, 'metadata_manager', manager)
        logger.info("Initialized MetadataManager and stored on app.state.metadata_manager")
    return manager

def get_comments_manager(request: Request) -> CommentsManager:
    manager = getattr(request.app.state, 'comments_manager', None)
    if not manager:
        # Instantiate lazily and cache on app.state
        manager = CommentsManager()
        setattr(request.app.state, 'comments_manager', manager)
        logger.info("Initialized CommentsManager and stored on app.state.comments_manager")
    return manager

def get_jobs_manager(request: Request) -> JobsManager:
    """Get JobsManager from SettingsManager.

    JobsManager is owned by SettingsManager, so we access it via settings_manager._jobs
    """
    settings_manager = getattr(request.app.state, 'settings_manager', None)
    if not settings_manager:
        logger.critical("SettingsManager not found in application state during request!")
        raise HTTPException(status_code=503, detail="Settings service not configured.")

    jobs_manager = getattr(settings_manager, '_jobs', None)
    if not jobs_manager:
        logger.critical("JobsManager not found in SettingsManager!")
        raise HTTPException(status_code=503, detail="Jobs service not configured.")

    return jobs_manager

# Add getters for Compliance, Estate, MDM, Security, Entitlements, Catalog Commander managers when they are added

# --- Add other manager getters if needed --- #
# Example:
# def get_data_products_manager(request: Request) -> DataProductsManager:
#     manager_instances = getattr(request.app.state, "manager_instances", None)
#     if not manager_instances or 'data_products' not in manager_instances:
#         logger.critical("DataProductsManager not found in application state!")
#         raise HTTPException(status_code=503, detail="Data Products service not available.")
#     return manager_instances['data_products'] 