from pathlib import Path
from typing import Optional, Dict, List
import json # Import json for parsing
import yaml

from fastapi import FastAPI
from sqlalchemy.orm import Session

from src.common.config import get_settings, Settings
from src.common.logging import get_logger
from src.common.database import init_db, get_session_factory, Base, engine, cleanup_db
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
# Business glossaries manager has been removed in favor of SemanticModelsManager
from src.controller.search_manager import SearchManager
from src.controller.users_manager import UsersManager
from src.controller.authorization_manager import AuthorizationManager
from src.controller.notifications_manager import NotificationsManager
from src.controller.audit_manager import AuditManager
from src.controller.data_domains_manager import DataDomainManager # Import new manager
from src.controller.tags_manager import TagsManager # Import TagsManager
from src.controller.semantic_models_manager import SemanticModelsManager
from src.controller.semantic_links_manager import SemanticLinksManager
from src.models.semantic_links import EntitySemanticLinkCreate
from src.controller.compliance_manager import ComplianceManager
from src.controller.teams_manager import TeamsManager
from src.controller.projects_manager import ProjectsManager

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
from src.db_models.data_products import DataProductDb, InputPortDb, OutputPortDb
from src.db_models.compliance import CompliancePolicyDb

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
from src.utils.metadata_seed_loader import seed_metadata_from_yaml
from src.utils.costs_seed_loader import seed_costs_from_yaml

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
        app.state.data_domain_manager = DataDomainManager(repository=data_domain_repo)
        # data_contracts_manager moved below after tags_manager initialization
        app.state.semantic_models_manager = SemanticModelsManager(db=db_session, data_dir=Path(__file__).parent.parent / "data")
        # Also register in global app_state fallback
        try:
            from src.common.app_state import set_app_state_manager
            set_app_state_manager('semantic_models_manager', app.state.semantic_models_manager)
        except Exception:
            pass
        # Remove BusinessGlossariesManager; rely solely on SemanticModelsManager
        # app.state.business_glossaries_manager = BusinessGlossariesManager(data_dir=data_dir, semantic_models_manager=app.state.semantic_models_manager)

        # Teams and Projects Managers
        app.state.teams_manager = TeamsManager()
        app.state.projects_manager = ProjectsManager()

        notifications_manager = getattr(app.state, 'notifications_manager', None)
        # Add other managers: Compliance, Estate, MDM, Security, Entitlements, Catalog Commander...

        # (moved) SearchManager initialization now happens AFTER all feature managers are constructed

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

            # Now instantiate DataProductsManager with TagsManager dependency
            app.state.data_products_manager = DataProductsManager(
                db=db_session,
                ws_client=ws_client,
                notifications_manager=app.state.notifications_manager,
                tags_manager=tags_manager
            )
            logger.info("DataProductsManager initialized with TagsManager integration.")
            
            # Now instantiate DataContractsManager with TagsManager dependency
            app.state.data_contracts_manager = DataContractsManager(data_dir=data_dir, tags_manager=tags_manager)
            logger.info("DataContractsManager initialized with TagsManager integration.")

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

        # Defer SearchManager initialization until after initial data loading completes
        logger.info("Deferring SearchManager initialization until after initial data load.")
        
        # --- Ensure default roles exist using the manager method --- 
        app.state.settings_manager.ensure_default_roles_exist()
        
        # --- Ensure default team and project exist for admins ---
        app.state.settings_manager.ensure_default_team_and_project()

        # --- Preload Compliance demo data so home dashboard has data on first load ---
        try:
            yaml_path = Path(__file__).parent.parent / "data" / "compliance.yaml"
            if yaml_path.exists():
                # Seed only if there are no policies yet
                existing_count = db_session.query(CompliancePolicyDb).count()
                if existing_count == 0:
                    ComplianceManager().load_from_yaml(db_session, str(yaml_path))
                    logger.info("Seeded compliance policies and sample runs from YAML during startup.")
                else:
                    logger.debug("Compliance policies already present; skipping YAML seeding.")
            else:
                logger.debug(f"Compliance YAML not found at {yaml_path}; skipping preload.")
        except Exception as e:
            logger.error(f"Failed preloading compliance data at startup: {e}", exc_info=True)

        # --- Commit session potentially used for default role creation ---
        # This commit is crucial AFTER all managers are initialized AND
        # default roles are potentially created by the SettingsManager
        db_session.commit()
        logger.info("Manager initialization and default role creation transaction committed.")

        # --- Start background job polling ---
        try:
            if app.state.jobs_manager:
                # Use configured polling interval (default: 5 minutes)
                app.state.jobs_manager.start_background_polling(interval_seconds=settings.JOB_POLLING_INTERVAL_SECONDS)
                logger.info(f"Started background job polling (interval: {settings.JOB_POLLING_INTERVAL_SECONDS}s)")
        except Exception as e:
            logger.error(f"Failed to start background job polling: {e}", exc_info=True)
            # Don't fail startup if polling fails to start

    except Exception as e:
        logger.critical(f"Failed during application startup (manager init or default roles): {e}", exc_info=True)
        if db_session: db_session.rollback() # Rollback if any part fails
        raise RuntimeError("Failed to initialize application managers or default roles.") from e
    finally:
        # Keep the DB session open for manager singletons that rely on it.
        # It will be managed at application shutdown.
        pass

def load_demo_semantic_links(db: Session) -> None:
    """Load demo semantic links between app entities and business concepts."""
    logger.info("Loading demo semantic links...")

    try:
        semantic_links_manager = SemanticLinksManager(db)

        # Load semantic links configuration
        semantic_links_file = Path(__file__).parent.parent / "data" / "semantic_links_demo.yaml"
        if not semantic_links_file.exists():
            logger.warning(f"Semantic links demo file not found: {semantic_links_file}")
            return

        with open(semantic_links_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        if not config or 'semantic_links' not in config:
            logger.warning("No semantic_links section found in config")
            return

        # Load entity semantic links
        links_created = 0
        for link_config in config['semantic_links']:
            try:
                entity_type = link_config['entity_type']
                entity_name = link_config['entity_name']
                iri = link_config['iri']
                label = link_config.get('label', '')

                # Find entity ID by name and type
                entity_id = None
                if entity_type == 'data_domain':
                    # Query data domains to find by name
                    from src.db_models.data_domains import DataDomain
                    domain = db.query(DataDomain).filter(DataDomain.name == entity_name).first()
                    if domain:
                        entity_id = str(domain.id)
                elif entity_type == 'data_product':
                    # Query data products to find by name (ODPS v1.0.0)
                    product = db.query(DataProductDb).filter(DataProductDb.name == entity_name).first()
                    if product:
                        entity_id = str(product.id)
                elif entity_type == 'data_contract':
                    # Query data contracts to find by name
                    from src.db_models.data_contracts import DataContractDb
                    contract = db.query(DataContractDb).filter(DataContractDb.name == entity_name).first()
                    if contract:
                        entity_id = str(contract.id)

                if entity_id:
                    # Create semantic link
                    link_data = EntitySemanticLinkCreate(
                        entity_id=entity_id,
                        entity_type=entity_type,
                        iri=iri,
                        label=label
                    )
                    semantic_links_manager.add(link_data, created_by="system")
                    links_created += 1
                    logger.debug(f"Created semantic link: {entity_type}:{entity_name} -> {iri}")
                else:
                    logger.warning(f"Entity not found: {entity_type} '{entity_name}'")

            except Exception as e:
                logger.warning(f"Failed to create semantic link for {link_config}: {e}")

        db.commit()
        logger.info(f"Successfully created {links_created} semantic links")

    except Exception as e:
        logger.exception(f"Error loading demo semantic links: {e}")
        db.rollback()

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
        business_glossaries_manager = None
        notifications_manager = getattr(app.state, 'notifications_manager', None) # Add this line
        teams_manager = getattr(app.state, 'teams_manager', None)
        projects_manager = getattr(app.state, 'projects_manager', None)
        # Add other managers as needed

        # Call load_initial_data for each manager that has it
        if settings_manager and hasattr(settings_manager, 'load_initial_data'):
            settings_manager.load_initial_data(db)
        if auth_manager and hasattr(auth_manager, 'load_initial_data'):
            auth_manager.load_initial_data(db)

        # Load Data Domains FIRST (teams reference domains via domain_id)
        if data_domain_manager and hasattr(data_domain_manager, 'load_initial_data'):
            data_domain_manager.load_initial_data(db)

        # Load Teams AFTER domains (teams belong to domains)
        if teams_manager and hasattr(teams_manager, 'load_initial_data'):
            teams_manager.load_initial_data(db)

        # Load Projects after Teams (projects reference teams via owner_team_id and team assignments)
        if projects_manager and hasattr(projects_manager, 'load_initial_data'):
            projects_manager.load_initial_data(db)

        # Now load other feature data that may depend on domains and teams
        if data_contracts_manager and hasattr(data_contracts_manager, 'load_initial_data'):
            data_contracts_manager.load_initial_data(db)
        if data_product_manager and hasattr(data_product_manager, 'load_initial_data'):
            data_product_manager.load_initial_data(db)
        if data_asset_review_manager and hasattr(data_asset_review_manager, 'load_initial_data'):
            data_asset_review_manager.load_initial_data(db)
        # Glossaries initial data loading removed
        semantic_models_manager = getattr(app.state, 'semantic_models_manager', None)
        if semantic_models_manager and hasattr(semantic_models_manager, 'load_initial_data'):
            semantic_models_manager.load_initial_data(db)
            # After loading semantic models, make sure business glossaries manager is connected
            pass
        if notifications_manager and hasattr(notifications_manager, 'load_initial_data'):
            notifications_manager.load_initial_data(db)
        
        # Load demo timeline entries after all entities are created
        if data_domain_manager and hasattr(data_domain_manager, 'load_demo_timeline_entries'):
            data_domain_manager.load_demo_timeline_entries(db)

        # Load demo semantic links after all entities are created
        load_demo_semantic_links(db)
        # After loading demo links, ensure KG contains entities and links
        try:
            sm = getattr(app.state, 'semantic_models_manager', None)
            if sm:
                sm.on_models_changed()
        except Exception:
            pass

        # Seed example metadata (rich text, links, documents) for products and domains
        try:
            yaml_path = Path(__file__).parent.parent / "data" / "metadata" / "product_metadata.yaml"
            if yaml_path.exists():
                seed_metadata_from_yaml(db, settings, yaml_path)
                logger.info("Seeded example metadata from YAML during startup.")
            else:
                logger.debug(f"Metadata YAML not found at {yaml_path}; skipping metadata seeding.")
        except Exception as e:
            logger.error(f"Failed seeding example metadata at startup: {e}", exc_info=True)

        # Seed example costs
        try:
            costs_yaml = Path(__file__).parent.parent / "data" / "costs.yaml"
            if costs_yaml.exists():
                seed_costs_from_yaml(db, costs_yaml)
                logger.info("Seeded example cost items from YAML during startup.")
            else:
                logger.debug(f"Costs YAML not found at {costs_yaml}; skipping cost seeding.")
        except Exception as e:
            logger.error(f"Failed seeding example costs at startup: {e}", exc_info=True)

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

        # Step 4: Build the SearchManager AFTER data has been loaded
        try:
            logger.info("Initializing SearchManager after managers and initial data are ready...")
            searchable_managers_instances = []
            for attr_name, manager_instance in list(getattr(app.state, '_state', {}).items()):
                try:
                    if isinstance(manager_instance, SearchableAsset) and hasattr(manager_instance, 'get_search_index_items'):
                        searchable_managers_instances.append(manager_instance)
                        logger.debug(f"Added searchable manager instance from app.state: {attr_name}")
                except Exception:
                    continue

            app.state.search_manager = SearchManager(searchable_managers=searchable_managers_instances)
            app.state.search_manager.build_index()
            logger.info("Search index initialized and built from DB-backed managers.")
        except Exception as e:
            logger.error(f"Failed initializing or building search index after data load: {e}", exc_info=True)

        logger.info("Application startup event handler finished successfully.")
    except Exception as e:
        logger.critical(f"CRITICAL ERROR during application startup: {e}", exc_info=True)
        # Depending on the severity, you might want to prevent the app from starting
        # or raise the exception to let FastAPI handle it (which might stop the server).
        # For now, just logging critically.

async def shutdown_event_handler(app: FastAPI):
    # Implement shutdown logic here
    logger.info("Executing application shutdown event handler...")
    
    # Cleanup database resources (including OAuth token refresh thread)
    try:
        cleanup_db()
        logger.info("Database cleanup completed successfully")
    except Exception as e:
        logger.error(f"Error during database cleanup: {e}", exc_info=True)
    
    # Add any other necessary cleanup or resource release logic here
    logger.info("Application shutdown event handler finished successfully.") 
