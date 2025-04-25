import logging
from pathlib import Path

from sqlalchemy.orm import Session as SQLAlchemySession # Use Session from sqlalchemy.orm directly
from api.common.config import Settings
from api.common.logging import get_logger
from api.controller.data_products_manager import DataProductsManager
from api.controller.data_asset_reviews_manager import DataAssetReviewManager
from api.common.workspace_client import get_workspace_client # Keep this for now, might be needed for other managers
from api.controller.notifications_manager import NotificationsManager # Keep this for now
from api.controller.settings_manager import SettingsManager # Import SettingsManager

logger = get_logger(__name__)

def load_demo_data(
    db_session: SQLAlchemySession, 
    settings: Settings, 
    settings_manager: SettingsManager # Add settings_manager parameter
):
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
        # Use the passed-in settings_manager
        notifications_mgr = NotificationsManager(settings_manager=settings_manager)
        try:
            # Get workspace client (consider if needed here or within DAR manager)
            ws_client = get_workspace_client(settings=settings) 
            dar_manager = DataAssetReviewManager(db=db_session, ws_client=ws_client, notifications_manager=notifications_mgr)
            YAML_PATH = Path('api/data/data_asset_reviews.yaml')
            if YAML_PATH.exists():
                logger.info(f"Attempting demo data load for Data Asset Reviews from {YAML_PATH}...")
                success = dar_manager.load_from_yaml(str(YAML_PATH))
                if success:
                    logger.info("Successfully loaded demo data for Data Asset Reviews.")
            else:
                logger.warning(f"Demo mode enabled but {YAML_PATH} not found.")
        except Exception as dep_e:
             logger.error(f"Error initializing ws_client or DAR manager: {dep_e}", exc_info=True)

    except Exception as e:
         logger.error(f"Error during Data Asset Reviews demo data check/load: {e}", exc_info=True)

    # --- Notifications --- 
    try:
        logger.debug("Checking Notifications for demo data loading...")
        # Instantiate NotificationsManager correctly using the passed-in settings_manager
        notifications_mgr = NotificationsManager(settings_manager=settings_manager)
        
        # Check if the notification table is empty (assuming repo has is_empty)
        if notifications_mgr._repo.is_empty(db=db_session):
            YAML_PATH = Path('api/data/notifications.yaml')
            if YAML_PATH.exists():
                logger.info(f"Notifications table is empty. Loading demo data from {YAML_PATH}...")
                # Assume load_from_yaml method exists/will be created in NotificationsManager
                success = notifications_mgr.load_from_yaml(yaml_path=str(YAML_PATH), db=db_session)
                if success:
                    logger.info("Successfully loaded demo data for Notifications.")
                else:
                    logger.error("Failed to load demo data for Notifications.")
            else:
                logger.warning(f"Demo mode enabled but Notifications YAML {YAML_PATH} not found.")
        else:
             logger.info("Notifications table is not empty. Skipping demo data loading.")
    except AttributeError:
        logger.error("NotificationsManager or its repository does not have an 'is_empty' method. Skipping demo data load check.")
        # Decide if you still want to try loading or skip completely
    except Exception as e:
         logger.error(f"Error during Notifications demo data check/load: {e}", exc_info=True)

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