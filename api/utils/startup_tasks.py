import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from sqlalchemy.orm import Session

from api.common.config import get_settings, Settings
from api.common.logging import get_logger
from api.common.database import init_db, get_session_factory
from api.common.workspace_client import get_workspace_client

# Import Managers needed for instantiation
from api.controller.data_products_manager import DataProductsManager
from api.controller.data_asset_reviews_manager import DataAssetReviewManager
from api.controller.data_contracts_manager import DataContractsManager
from api.controller.business_glossaries_manager import BusinessGlossariesManager
from api.controller.search_manager import SearchManager
from api.controller.settings_manager import SettingsManager
from api.controller.users_manager import UsersManager
from api.controller.authorization_manager import AuthorizationManager
from api.controller.notifications_manager import NotificationsManager

# Import Demo Data Loader
from api.utils.demo_data_loader import load_demo_data
# Import the search registry
from api.common.search_registry import SEARCHABLE_ASSET_MANAGERS

logger = get_logger(__name__)

def initialize_database():
    """Initializes the database connection, creates catalog/schema, and tables."""
    logger.info("Initializing database...")
    try:
        init_db()
        logger.info("Database initialization complete.")
    except ConnectionError as e:
        logger.critical(f"Database connection/initialization failed: {e}", exc_info=True)
        # Re-raise as a more specific startup error if needed, or let FastAPI handle termination
        raise RuntimeError("Application cannot start without database connection.") from e
    except Exception as e:
        logger.critical(f"An unexpected error occurred during database initialization: {e}", exc_info=True)
        raise RuntimeError("Application cannot start due to database initialization error.") from e

def initialize_managers(app: FastAPI):
    """Initializes and stores manager instances in app.state."""
    logger.info("Initializing manager singletons...")
    settings = get_settings()
    session_factory = get_session_factory() # Assumes DB is initialized
    db_session = None

    # Initialize Workspace Client first
    ws_client = None
    try:
        ws_client = get_workspace_client(settings=settings)
        if ws_client:
            logger.info("WorkspaceClient initialized successfully for managers.")
        else:
            logger.warning("WorkspaceClient could not be initialized for managers (likely missing config). Dependent features may fail.")
    except Exception as e:
        logger.error(f"Error initializing WorkspaceClient for managers: {e}", exc_info=True)

    try:
        db_session = session_factory()
        app.state.manager_instances = {}
        app.state.auth_manager = None
        app.state.settings_manager = None
        app.state.users_manager = None

        # Instantiate managers requiring dependencies
        # Core managers first
        settings_manager_instance = SettingsManager(db=db_session, workspace_client=ws_client)
        app.state.settings_manager = settings_manager_instance
        logger.info("SettingsManager singleton stored in app.state.")

        users_manager_instance = UsersManager(ws_client=ws_client)
        app.state.users_manager = users_manager_instance
        logger.info("UsersManager singleton stored in app.state.")

        auth_manager_instance = AuthorizationManager(settings_manager=settings_manager_instance)
        app.state.auth_manager = auth_manager_instance
        logger.info("AuthorizationManager singleton stored in app.state.")

        # Feature-specific managers
        dp_manager = DataProductsManager(db=db_session, ws_client=ws_client)
        app.state.manager_instances['data_products'] = dp_manager
        logger.info("DataProductsManager singleton stored in app.state.")

        # Example: Assuming DATA_DIR is needed and defined appropriately
        data_dir = Path(__file__).parent.parent / "data"
        dc_manager = DataContractsManager(data_dir=data_dir)
        app.state.manager_instances['data_contracts'] = dc_manager
        logger.info("DataContractsManager singleton stored in app.state.")

        bg_manager = BusinessGlossariesManager(data_dir=data_dir)
        app.state.manager_instances['business_glossaries'] = bg_manager
        logger.info("BusinessGlossariesManager singleton stored in app.state.")

        # Initialize NotificationsManager (takes no arguments)
        notifications_manager_instance = NotificationsManager(settings_manager=settings_manager_instance)
        app.state.manager_instances['notifications'] = notifications_manager_instance
        logger.info("NotificationsManager singleton stored in app.state.")

        # Initialize DataAssetReviewManager with all dependencies
        dar_manager = DataAssetReviewManager(
            db=db_session, 
            ws_client=ws_client, 
            notifications_manager=notifications_manager_instance
        )
        app.state.manager_instances['data_asset_reviews'] = dar_manager
        logger.info("DataAssetReviewManager singleton stored in app.state.")

        # --- Initialize Search Manager --- #
        # Filter managers based on the registry
        registered_searchable_managers = [
             manager for manager in app.state.manager_instances.values()
             if manager.__class__ in SEARCHABLE_ASSET_MANAGERS
        ]
        logger.info(f"Found {len(registered_searchable_managers)} managers registered via @searchable_asset for SearchManager.")

        search_manager_instance = SearchManager(
            searchable_managers=registered_searchable_managers
        )
        app.state.search_manager = search_manager_instance
        logger.info("SearchManager singleton stored in app.state.")

        # Commit session used for manager init (e.g., if default roles were created)
        db_session.commit()
        logger.info("Manager singletons created and stored successfully.")

    except Exception as e:
        logger.critical(f"Failed to create manager singletons during startup: {e}", exc_info=True)
        if db_session: db_session.rollback()
        # Depending on severity, you might want to raise an error here
        # raise RuntimeError("Failed to initialize application managers.") from e
    finally:
        if db_session:
            db_session.close()
            logger.info("DB session for manager instantiation closed.")

def load_initial_data(
    settings: Settings, # Keep settings for APP_DEMO_MODE check
    settings_manager: SettingsManager # Add settings_manager parameter
):
    """Loads demo data if configured."""
    # No longer need to get settings here if passed from startup
    # if settings is None:
    #     settings = get_settings()

    if not settings.APP_DEMO_MODE:
        logger.info("Demo mode is disabled. Skipping demo data loading.")
        return

    logger.info("Attempting demo data load...")
    session_factory = get_session_factory()
    db_session = None
    try:
        db_session = session_factory()
        # --- Remove lines getting settings_manager from app.state ---
        # from fastapi import FastAPI # Assuming 'app' instance is the global one
        # settings_manager_instance = app.state.settings_manager if hasattr(app.state, 'settings_manager') else None
        # if not settings_manager_instance:
        #      logger.error("Cannot load demo data: SettingsManager not found in app.state.")
        #      return # Or raise an error

        # Call load_demo_data with the passed-in manager
        load_demo_data(
            db_session=db_session,
            settings=settings,
            settings_manager=settings_manager # Use the passed-in manager
        )
        logger.info("Completed call to load_demo_data.")
        db_session.commit()
    except RuntimeError as e:
        logger.error(f"Cannot load demo data: {e}")
    except Exception as e:
        logger.error(f"Error during demo data loading execution: {e}", exc_info=True)
        if db_session: db_session.rollback()
    finally:
        if db_session:
            db_session.close()
            logger.info("Demo data DB session closed.") 