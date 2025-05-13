import logging
from pathlib import Path
from typing import Optional, Dict, List
import json # Import json for parsing

from fastapi import FastAPI
from sqlalchemy.orm import Session

from api.common.config import get_settings, Settings
from api.common.logging import get_logger
from api.common.database import init_db, get_session_factory, Base, engine
from api.common.workspace_client import get_workspace_client
from api.common.features import FeatureAccessLevel, APP_FEATURES, get_feature_config
from api.models.settings import AppRoleCreate, AppRole as AppRoleApi
from api.common.config import Settings
from api.controller.settings_manager import SettingsManager

# Import Managers needed for instantiation
from api.controller.data_products_manager import DataProductsManager
from api.controller.data_asset_reviews_manager import DataAssetReviewManager
from api.controller.data_contracts_manager import DataContractsManager
from api.controller.business_glossaries_manager import BusinessGlossariesManager
from api.controller.search_manager import SearchManager
from api.controller.users_manager import UsersManager
from api.controller.authorization_manager import AuthorizationManager
from api.controller.notifications_manager import NotificationsManager
from api.controller.audit_manager import AuditManager
from api.controller.data_domains_manager import DataDomainManager # Import new manager

# Import repositories (needed for manager instantiation)
from api.repositories.settings_repository import AppRoleRepository
from api.repositories.audit_log_repository import AuditLogRepository
from api.repositories.data_asset_reviews_repository import DataAssetReviewRepository
from api.repositories.data_products_repository import DataProductRepository
from api.repositories.data_domain_repository import DataDomainRepository # Import new repo
# Import the required DB model
from api.db_models.settings import AppRoleDb
# Import the AuditLog DB model
from api.db_models.audit_log import AuditLog
# Import the DataAssetReviewRequestDb DB model
from api.db_models.data_asset_reviews import DataAssetReviewRequestDb
# Import the DataProductDb DB model
from api.db_models.data_products import DataProductDb

# Import Demo Data Loader
# from api.utils.demo_data_loader import load_demo_data # Removed unused import
# Import the search registry (decorator is still useful for intent)
# from api.common.search_registry import SEARCHABLE_ASSET_MANAGERS # Not strictly needed for this approach
# Import the CORRECT base class for type checking
from api.common.search_interfaces import SearchableAsset

logger = get_logger(__name__)

def initialize_database(settings: Settings): # Keep settings param for future use if needed
    """Initializes the database by calling the main init_db function."""
    logger.info("Triggering database initialization...")
    try:
        init_db() # Call the function from common.database
        logger.info("Database initialization routine completed successfully.")
    except ConnectionError as e:
        logger.critical(f"Database connection/initialization failed: {e}", exc_info=True)
        raise RuntimeError("Application cannot start without database connection.") from e
    except Exception as e:
        logger.critical(f"An unexpected error occurred during database initialization: {e}", exc_info=True)
        raise RuntimeError("Application cannot start due to database initialization error.") from e

def initialize_managers(app: FastAPI):
    """Initializes and stores manager instances directly in app.state."""
    logger.info("Initializing manager singletons...")
    settings = get_settings()
    session_factory = get_session_factory() # Assumes DB is initialized
    db_session = None
    ws_client = None

    try:
        # --- Initialize Workspace Client --- 
        logger.info("Attempting to initialize WorkspaceClient...")
        ws_client = get_workspace_client(settings=settings)
        if not ws_client:
            raise RuntimeError("Failed to initialize Databricks WorkspaceClient (returned None).")
        logger.info("WorkspaceClient initialized successfully.")

        # --- Initialize DB Session --- 
        db_session = session_factory()

        # --- Define Data Directory --- 
        data_dir = Path(__file__).parent.parent / "data"
        if not data_dir.is_dir():
            logger.warning(f"Data directory not found: {data_dir}. Some managers might fail.")

        # --- Initialize Repositories --- 
        logger.debug("Initializing repositories...")
        app_role_repo = AppRoleRepository(model=AppRoleDb)
        # Pass the DB model to the repository constructor
        audit_repo = AuditLogRepository(model=AuditLog)
        data_asset_review_repo = DataAssetReviewRepository(model=DataAssetReviewRequestDb)
        data_product_repo = DataProductRepository(model=DataProductDb)
        data_domain_repo = DataDomainRepository()
        # Add other repos if needed
        logger.debug("Repositories initialized.")

        # --- Instantiate and Store Managers Directly on app.state --- 
        logger.debug("Instantiating managers...")
        
        # Store the global settings object on app.state for easy access
        app.state.settings = settings
        logger.info(f"Stored global settings object on app.state.settings: {type(app.state.settings)}")

        # Instantiate SettingsManager first, passing settings
        app.state.settings_manager = SettingsManager(db=db_session, settings=settings, workspace_client=ws_client)

        # Instantiate other managers, passing the settings_manager instance if needed
        audit_manager = AuditManager(settings=settings, db_session=db_session)
        app.state.users_manager = UsersManager(ws_client=ws_client)
        app.state.audit_manager = audit_manager
        app.state.authorization_manager = AuthorizationManager(
            settings_manager=app.state.settings_manager 
        )
        app.state.notifications_manager = NotificationsManager(settings_manager=app.state.settings_manager)

        # Feature Managers
        app.state.data_asset_review_manager = DataAssetReviewManager(
            db=db_session, 
            ws_client=ws_client,
            notifications_manager=app.state.notifications_manager 
        )
        app.state.data_products_manager = DataProductsManager(
            db=db_session,
            ws_client=ws_client,
            notifications_manager=app.state.notifications_manager
        )
        app.state.data_domain_manager = DataDomainManager(repository=data_domain_repo)
        app.state.data_contracts_manager = DataContractsManager(data_dir=data_dir)
        app.state.business_glossaries_manager = BusinessGlossariesManager(data_dir=data_dir)
        notifications_manager = getattr(app.state, 'notifications_manager', None)
        # Add other managers: Compliance, Estate, MDM, Security, Entitlements, Catalog Commander...

        # --- Instantiate Search Manager --- 
        # Dynamically collect manager instances that inherit from SearchableAsset
        # Iterate directly over the values stored in app.state._state dictionary
        searchable_managers_instances = []
        logger.debug("--- Scanning app.state._state.values() for SearchableAsset instances ---")
        
        if hasattr(app.state, '_state') and isinstance(app.state._state, dict):
            for manager_instance in app.state._state.values():
                # Log the type of each instance found in _state
                manager_type = type(manager_instance)
                logger.debug(f"Checking instance in app.state._state: Type={manager_type.__name__}")

                # Check if it's an instance of the SearchableAsset base class
                if isinstance(manager_instance, SearchableAsset):
                    # Check if it implements the required method (good practice)
                    if hasattr(manager_instance, 'get_search_index_items') and callable(getattr(manager_instance, 'get_search_index_items')):
                        searchable_managers_instances.append(manager_instance)
                        logger.debug(f"   Added searchable manager instance: Type={manager_type.__name__}")
                    else:
                        logger.warning(f"Manager instance of type {manager_type.__name__} inherits from SearchableAsset but does not implement 'get_search_index_items' method.")
        else:
            logger.error("Could not find or access app.state._state dictionary to scan for managers.")

        logger.info(f"Found {len(searchable_managers_instances)} managers inheriting from SearchableAsset by checking app.state._state.values().")
        app.state.search_manager = SearchManager(searchable_managers=searchable_managers_instances)
        logger.info("SearchManager initialized.")

        logger.info("All managers instantiated and stored in app.state.")
        
        # --- Ensure default roles exist using the manager method --- 
        app.state.settings_manager.ensure_default_roles_exist()

        # --- Commit session potentially used for default role creation --- 
        # This commit is crucial AFTER all managers are initialized AND 
        # default roles are potentially created by the SettingsManager
        db_session.commit()
        logger.info("Manager initialization and default role creation transaction committed.")

    except Exception as e:
        logger.critical(f"Failed during application startup (manager init or default roles): {e}", exc_info=True)
        if db_session: db_session.rollback() # Rollback if any part fails
        raise RuntimeError("Failed to initialize application managers or default roles.") from e
    finally:
        if db_session:
            db_session.close()
            logger.info("DB session for manager instantiation closed.")

def load_initial_data(app: FastAPI) -> None:
    """Loads initial demo data if configured."""
    settings: Settings = get_settings()
    if not settings.APP_DEMO_MODE:
        logger.info("APP_DEMO_MODE is disabled. Skipping initial data loading.")
        return

    logger.info("APP_DEMO_MODE is enabled. Loading initial data...")
    db_session_factory = get_session_factory()
    if not db_session_factory:
        logger.error("Cannot load initial data: Database session factory not available.")
        return
    
    db: Session = db_session_factory()
    try:
        # Get managers directly from app.state
        settings_manager = getattr(app.state, 'settings_manager', None)
        auth_manager = getattr(app.state, 'authorization_manager', None)
        data_asset_review_manager = getattr(app.state, 'data_asset_review_manager', None)
        data_product_manager = getattr(app.state, 'data_products_manager', None) # Corrected name
        data_domain_manager = getattr(app.state, 'data_domain_manager', None)
        data_contracts_manager = getattr(app.state, 'data_contracts_manager', None) # Add
        business_glossaries_manager = getattr(app.state, 'business_glossaries_manager', None) # Add
        notifications_manager = getattr(app.state, 'notifications_manager', None) # Add this line
        # Add other managers as needed

        # Call load_initial_data for each manager that has it
        if settings_manager and hasattr(settings_manager, 'load_initial_data'):
            settings_manager.load_initial_data(db)
        if auth_manager and hasattr(auth_manager, 'load_initial_data'):
            auth_manager.load_initial_data(db)
        if data_asset_review_manager and hasattr(data_asset_review_manager, 'load_initial_data'):
            data_asset_review_manager.load_initial_data(db)
        if data_product_manager and hasattr(data_product_manager, 'load_initial_data'):
            data_product_manager.load_initial_data(db)
        if data_domain_manager and hasattr(data_domain_manager, 'load_initial_data'):
            data_domain_manager.load_initial_data(db)
        if data_contracts_manager and hasattr(data_contracts_manager, 'load_initial_data'):
            data_contracts_manager.load_initial_data(db)
        if business_glossaries_manager and hasattr(business_glossaries_manager, 'load_initial_data'):
            business_glossaries_manager.load_initial_data(db)
        if notifications_manager and hasattr(notifications_manager, 'load_initial_data'):
            notifications_manager.load_initial_data(db)
        
        # No final commit needed here if managers commit internally or role creation already committed
        logger.info("Initial data loading process completed for all managers.")

    except Exception as e:
        logger.exception(f"Error during initial data loading: {e}")
        db.rollback()
    finally:
        db.close() 