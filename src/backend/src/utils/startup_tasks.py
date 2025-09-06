import logging
from pathlib import Path
from typing import Optional, Dict, List
import json # Import json for parsing

from fastapi import FastAPI
from sqlalchemy.orm import Session

from src.common.config import get_settings, Settings
from src.common.logging import get_logger
from src.common.database import init_db, get_session_factory, Base, engine
from src.common.workspace_client import get_workspace_client
from src.common.features import FeatureAccessLevel, APP_FEATURES, get_feature_config
from src.models.settings import AppRoleCreate, AppRole as AppRoleApi
from src.common.config import Settings
from src.controller.settings_manager import SettingsManager
from src.controller.jobs_manager import JobsManager

# Import Managers needed for instantiation
from src.controller.data_products_manager import DataProductsManager
from src.controller.data_asset_reviews_manager import DataAssetReviewManager
from src.controller.data_contracts_manager import DataContractsManager
from src.controller.business_glossaries_manager import BusinessGlossariesManager
from src.controller.search_manager import SearchManager
from src.controller.users_manager import UsersManager
from src.controller.authorization_manager import AuthorizationManager
from src.controller.notifications_manager import NotificationsManager
from src.controller.audit_manager import AuditManager
from src.controller.data_domains_manager import DataDomainManager # Import new manager
from src.controller.tags_manager import TagsManager # Import TagsManager
from src.controller.semantic_models_manager import SemanticModelsManager

# Import repositories (needed for manager instantiation)
from src.repositories.settings_repository import AppRoleRepository
from src.repositories.audit_log_repository import AuditLogRepository
from src.repositories.data_asset_reviews_repository import DataAssetReviewRepository
from src.repositories.data_products_repository import DataProductRepository
from src.repositories.data_domain_repository import DataDomainRepository # Import new repo
# Import repository for semantic models
from src.repositories.semantic_models_repository import SemanticModelsRepository
# Import the required DB model
from src.db_models.settings import AppRoleDb
# Import the AuditLog DB model
from src.db_models.audit_log import AuditLogDb
# Import the DataAssetReviewRequestDb DB model
from src.db_models.data_asset_reviews import DataAssetReviewRequestDb
# Import the DataProductDb DB model
from src.db_models.data_products import DataProductDb, InfoDb, InputPortDb, OutputPortDb

# Import Demo Data Loader
# from src.utils.demo_data_loader import load_demo_data # Removed unused import
# Import the search registry (decorator is still useful for intent)
# from src.common.search_registry import SEARCHABLE_ASSET_MANAGERS # Not strictly needed for this approach
# Import the CORRECT base class for type checking
from src.common.search_interfaces import SearchableAsset

# Import repositories that managers might need
from src.repositories.data_products_repository import data_product_repo
from src.repositories.settings_repository import app_role_repo
# Import tag repositories
from src.repositories.tags_repository import (
    tag_namespace_repo, tag_repo, tag_namespace_permission_repo, entity_tag_repo
)

from src.common.search_registry import SEARCHABLE_ASSET_MANAGERS
from src.common.config import get_settings
from src.common.logging import get_logger

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
        audit_repo = AuditLogRepository(model=AuditLogDb)
        data_asset_review_repo = DataAssetReviewRepository(model=DataAssetReviewRequestDb)
        data_product_repo = DataProductRepository(model=DataProductDb)
        data_domain_repo = DataDomainRepository()
        semantic_models_repo = SemanticModelsRepository(model=None)  # model unused due to singleton instance
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
        # Back-reference for progress notifications
        app.state.settings_manager.set_notifications_manager(app.state.notifications_manager)
        # Make jobs_manager accessible via app.state
        app.state.jobs_manager = app.state.settings_manager._jobs

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
        app.state.semantic_models_manager = SemanticModelsManager(db=db_session, data_dir=Path(__file__).parent.parent / "data")
        app.state.business_glossaries_manager = BusinessGlossariesManager(data_dir=data_dir, semantic_models_manager=app.state.semantic_models_manager)
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

        # Instantiate and store TagsManager
        try:
            tags_manager = TagsManager(
                namespace_repo=tag_namespace_repo,
                tag_repository=tag_repo,
                permission_repo=tag_namespace_permission_repo
                # entity_assoc_repo will be used when integrating with other features
            )
            app.state.tags_manager = tags_manager
            SEARCHABLE_ASSET_MANAGERS.append(tags_manager) # Register for search
            logger.info("TagsManager initialized and registered for search.")

            # Ensure default tag namespace exists (using a new session for this setup task)
            with session_factory() as setup_db:
                try:
                    tags_manager.get_or_create_default_namespace(setup_db, user_email="system@startup.ucapp")
                    logger.info("Default tag namespace ensured.")
                except Exception as e_ns:
                    logger.error(f"Failed to ensure default tag namespace: {e_ns}", exc_info=True)
                    # Decide if this is a fatal error for startup

        except Exception as e:
            logger.error(f"Error initializing TagsManager: {e}", exc_info=True)
            # Decide if this is a fatal error

        # --- Instantiate MetadataManager (if it exists and needs to be in app.state) --- 
        # This was removed in previous steps as tag CRUD moved to TagsManager
        # If MetadataManager still has other responsibilities, initialize it here.
        # For now, assuming it's not strictly needed for basic app startup if its main role was tags.
        # if hasattr(app.state, 'ws_client'): # Example: if it needs ws_client
        #     metadata_manager = MetadataManager(ws_client=app.state.ws_client)
        #     app.state.metadata_manager = metadata_manager
        #     SEARCHABLE_ASSET_MANAGERS.append(metadata_manager) # If it's searchable
        #     logger.info("MetadataManager initialized.")

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
        semantic_models_manager = getattr(app.state, 'semantic_models_manager', None)
        if semantic_models_manager and hasattr(semantic_models_manager, 'load_initial_data'):
            semantic_models_manager.load_initial_data(db)
            # After loading semantic models, make sure business glossaries manager is connected
            business_glossaries_manager = getattr(app.state, 'business_glossaries_manager', None)
            if business_glossaries_manager and hasattr(business_glossaries_manager, 'set_semantic_models_manager'):
                business_glossaries_manager.set_semantic_models_manager(semantic_models_manager)
        if notifications_manager and hasattr(notifications_manager, 'load_initial_data'):
            notifications_manager.load_initial_data(db)
        
        # Load demo timeline entries after all entities are created
        if data_domain_manager and hasattr(data_domain_manager, 'load_demo_timeline_entries'):
            data_domain_manager.load_demo_timeline_entries(db)
        
        # No final commit needed here if managers commit internally or role creation already committed
        logger.info("Initial data loading process completed for all managers.")

    except Exception as e:
        logger.exception(f"Error during initial data loading: {e}")
        db.rollback()
    finally:
        db.close() 

async def startup_event_handler(app: FastAPI):
    logger.info("Executing application startup event handler...")
    try:
        initialize_database() # Step 1: Setup Database
        logger.info("Database initialization sequence complete.")

        # Step 2: Initialize managers (requires ws_client to be set up if managers need it)
        # Create a temporary session for manager initializations that require DB access (like default namespace)
        # Note: Managers themselves should request sessions via DBSessionDep for their operational methods.
        initialize_managers(app) # Pass the app to store managers in app.state
        logger.info("Managers initialization sequence complete.")

        # Step 3: Load initial data (requires managers to be initialized)
        # This function now creates its own session for data loading operations.
        load_initial_data(app) 
        logger.info("Initial data loading sequence complete.")

        logger.info("Application startup event handler finished successfully.")
    except Exception as e:
        logger.critical(f"CRITICAL ERROR during application startup: {e}", exc_info=True)
        # Depending on the severity, you might want to prevent the app from starting
        # or raise the exception to let FastAPI handle it (which might stop the server).
        # For now, just logging critically.

async def shutdown_event_handler(app: FastAPI):
    # Implement shutdown logic here
    logger.info("Executing application shutdown event handler...")
    # Add any necessary cleanup or resource release logic here
    logger.info("Application shutdown event handler finished successfully.") 
