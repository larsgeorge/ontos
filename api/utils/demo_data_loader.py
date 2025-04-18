import logging
from pathlib import Path

from sqlalchemy.orm import Session as SQLAlchemySession # Use Session from sqlalchemy.orm directly
from api.common.config import Settings
from api.common.logging import get_logger
from api.controller.data_products_manager import DataProductsManager
from api.controller.data_asset_reviews_manager import DataAssetReviewManager
from api.common.workspace_client import get_workspace_client # Keep this for now, might be needed for other managers
from api.controller.notifications_manager import NotificationsManager # Keep this for now

logger = get_logger(__name__)

def load_demo_data(db_session: SQLAlchemySession, settings: Settings):
    """Loads demo data if demo mode is enabled and tables are empty."""
    logger.info(f"Inside load_demo_data. Checking APP_DEMO_MODE: {settings.APP_DEMO_MODE}")
    if not settings.APP_DEMO_MODE:
        logger.info("Demo mode is disabled. Skipping demo data loading.")
        return

    logger.info("Demo mode is enabled. Checking if demo data needs to be loaded...")
    
    # --- Data Products --- 
    try:
        logger.debug("Checking Data Products for demo data loading...")
        dp_manager = DataProductsManager(db=db_session)
        if dp_manager._repo.is_empty(db=db_session): 
            YAML_PATH = Path('api/data/data_products.yaml')
            if YAML_PATH.exists():
                logger.info(f"Data Products table is empty. Loading demo data from {YAML_PATH}...")
                success = dp_manager.load_from_yaml(str(YAML_PATH))
                if success:
                    logger.info("Successfully loaded demo data for Data Products.")
                else:
                    logger.error("Failed to load demo data for Data Products.")
            else:
                logger.warning(f"Demo mode enabled but {YAML_PATH} not found.")
        else:
            logger.info("Data Products table is not empty. Skipping demo data loading.")
    except Exception as e:
         logger.error(f"Error during Data Products demo data check/load: {e}", exc_info=True)

    # --- Data Asset Reviews --- #
    try:
        logger.debug("Checking Data Asset Reviews for demo data loading...")
        # Ensure dependencies for the manager are available
        # Note: Getting ws_client might be complex outside request context.
        # Consider alternative ways to provide it during startup if needed,
        # or make ws_client optional in the manager for loading.
        # Assuming get_workspace_client() works here for simplicity.
        # Assuming a simple NotificationsManager instantiation works.
        # FIXME: Instantiate dependencies properly or refactor manager initialization
        #        for startup context. This might fail as is.
        try:
            ws_client = get_workspace_client() 
            notifications_mgr = NotificationsManager() # This likely needs context/dependencies too
            dar_manager = DataAssetReviewManager(db=db_session, ws_client=ws_client, notifications_manager=notifications_mgr)
            YAML_PATH = Path('api/data/data_asset_reviews.yaml')
            if YAML_PATH.exists():
                # load_from_yaml now includes the check for empty table
                logger.info(f"Attempting demo data load for Data Asset Reviews from {YAML_PATH}...")
                success = dar_manager.load_from_yaml(str(YAML_PATH))
                if success:
                    logger.info("Successfully loaded demo data for Data Asset Reviews.")
                # else: # load_from_yaml logs errors/warnings internally
                #    logger.error("Failed to load demo data for Data Asset Reviews.")
            else:
                logger.warning(f"Demo mode enabled but {YAML_PATH} not found.")
        except Exception as dep_e:
             logger.error(f"Error initializing dependencies for Data Asset Reviews Manager: {dep_e}", exc_info=True)

    except Exception as e:
         logger.error(f"Error during Data Asset Reviews demo data check/load: {e}", exc_info=True)

    # --- Add similar blocks for other services here --- 
    # Example: Business Glossary
    # try:
    #     logger.debug("Checking Business Glossary for demo data loading...")
    #     bg_manager = BusinessGlossaryManager(db=db_session) # Assuming it only needs db_session
    #     YAML_PATH = Path('api/data/business_glossaries.yaml')
    #     if YAML_PATH.exists():
    #         logger.info(f"Attempting demo data load for Business Glossary from {YAML_PATH}...")
    #         # Assuming load_from_yaml exists and handles empty check
    #         success = bg_manager.load_from_yaml(str(YAML_PATH))
    #         if success:
    #             logger.info("Successfully loaded demo data for Business Glossary.")
    #     else:
    #         logger.warning(f"Demo mode enabled but {YAML_PATH} not found.")
    # except Exception as e:
    #      logger.error(f"Error during Business Glossary demo data check/load: {e}", exc_info=True) 