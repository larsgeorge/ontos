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
from api.controller.data_domains_manager import DataDomainManager
# Add imports for other managers if they need dependency getters
from api.controller.data_contracts_manager import DataContractsManager
from api.controller.business_glossaries_manager import BusinessGlossariesManager
from api.controller.search_manager import SearchManager

# Import other dependencies needed by these providers
from api.common.database import get_db
from api.common.workspace_client import get_workspace_client
from databricks.sdk import WorkspaceClient
from api.common.logging import get_logger

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

def get_business_glossaries_manager(request: Request) -> BusinessGlossariesManager:
    manager = getattr(request.app.state, 'business_glossaries_manager', None)
    if not manager:
        logger.critical("BusinessGlossariesManager not found in application state during request!")
        raise HTTPException(status_code=503, detail="Business Glossary service not configured.")
    return manager

def get_search_manager(request: Request) -> SearchManager:
    manager = getattr(request.app.state, 'search_manager', None)
    if not manager:
        logger.critical("SearchManager not found in application state during request!")
        raise HTTPException(status_code=503, detail="Search service not configured.")
    return manager

# Add getters for Compliance, Estate, MDM, Security, Entitlements, Catalog Commander managers when they are added

# --- Add other manager getters if needed --- #
# Example:
# def get_data_products_manager(request: Request) -> DataProductsManager:
#     manager_instances = getattr(request.app.state, "manager_instances", None)
#     if not manager_instances or 'data_products' not in manager_instances:
#         logger.critical("DataProductsManager not found in application state!")
#         raise HTTPException(status_code=503, detail="Data Products service not available.")
#     return manager_instances['data_products'] 