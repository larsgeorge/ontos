"""
Demo Data Loader

Centralized module for loading all demo/example data when APP_DEMO_MODE is enabled.
This module consolidates demo data loading logic that was previously scattered across
individual manager classes and startup_tasks.py.

The loading order respects entity dependencies:
1. Data Domains (no dependencies)
2. Teams (depends on domains)
3. Projects (depends on teams)
4. Data Contracts, Data Products (depend on domains/teams)
5. Data Asset Reviews (depends on products/contracts)
6. Semantic Models, Notifications
7. Semantic Links (depends on all entities)
8. Compliance, Timeline, Metadata, Costs (cross-cutting)
"""

import json
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.common.logging import get_logger
from src.common.config import get_settings

logger = get_logger(__name__)


# =============================================================================
# Helper Functions
# =============================================================================

def _get_data_dir() -> Path:
    """Get the data directory path."""
    return Path(__file__).parent.parent / "data"


def _load_yaml(yaml_path: Path) -> Dict[str, Any]:
    """Load and parse a YAML file."""
    if not yaml_path.exists():
        logger.warning(f"YAML file not found: {yaml_path}")
        return {}

    try:
        with yaml_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Failed to load YAML from {yaml_path}: {e}")
        return {}


def _check_table_empty(db: Session, model_class) -> bool:
    """Check if a database table is empty."""
    try:
        count = db.query(model_class).count()
        return count == 0
    except Exception as e:
        logger.error(f"Error checking if table {model_class.__name__} is empty: {e}")
        return False


# =============================================================================
# Entity-Specific Loaders
# =============================================================================

def _load_domains(db: Session) -> None:
    """Load data domains from YAML file."""
    from src.db_models.data_domains import DataDomain

    if not _check_table_empty(db, DataDomain):
        logger.debug("Data domains table not empty. Skipping.")
        return

    yaml_path = _get_data_dir() / "data_domains.yaml"
    logger.info(f"Loading data domains from {yaml_path}...")

    config = _load_yaml(yaml_path)
    if not config:
        return

    # Get manager from app.state (will be passed in main function)
    # For now, we'll instantiate managers directly
    from src.repositories.data_domain_repository import DataDomainRepository
    from src.controller.data_domains_manager import DataDomainManager
    from src.models.data_domains import DataDomainCreate

    manager = DataDomainManager(repository=DataDomainRepository())
    domains_data = config.get("domains", [])

    # Create domains in order (parents before children)
    created_domains = {}
    for domain_data in domains_data:
        try:
            domain_name = domain_data.get("name")
            parent_name = domain_data.get("parent_name")
            parent_id = None

            if parent_name and parent_name in created_domains:
                parent_id = created_domains[parent_name]

            domain_create = DataDomainCreate(
                name=domain_name,
                description=domain_data.get("description"),
                tags=domain_data.get("tags", []),
                parent_id=parent_id
            )

            created = manager.create_domain(db, domain_create, current_user_id="system@startup.ucapp")
            created_domains[domain_name] = created.id
            logger.debug(f"Created domain: {domain_name}")

        except Exception as e:
            logger.error(f"Failed creating domain {domain_data.get('name')}: {e}")

    db.commit()
    logger.info(f"Loaded {len(created_domains)} data domains.")


def _load_teams(db: Session) -> None:
    """Load teams from YAML file."""
    from src.db_models.teams import TeamDb

    # Check if non-admin teams exist
    try:
        existing_teams = db.query(TeamDb).limit(10).all()
        non_admin_teams = [t for t in existing_teams if t.name != 'Admin Team']
        if non_admin_teams:
            logger.debug(f"Found {len(non_admin_teams)} non-admin teams. Skipping.")
            return
    except Exception as e:
        logger.error(f"Error checking existing teams: {e}")
        return

    yaml_path = _get_data_dir() / "teams.yaml"
    logger.info(f"Loading teams from {yaml_path}...")

    # Use teams manager to load data
    try:
        from src.controller.teams_manager import TeamsManager
        manager = TeamsManager()
        success = manager.load_initial_data(db)
        if success:
            logger.info("Teams loaded successfully.")
    except Exception as e:
        logger.error(f"Failed loading teams: {e}", exc_info=True)


def _load_projects(db: Session) -> None:
    """Load projects from YAML file."""
    from src.db_models.projects import ProjectDb

    # Check if non-admin projects exist
    try:
        existing_projects = db.query(ProjectDb).limit(10).all()
        non_admin_projects = [p for p in existing_projects if p.name != 'Admin Project']
        if non_admin_projects:
            logger.debug(f"Found {len(non_admin_projects)} non-admin projects. Skipping.")
            return
    except Exception as e:
        logger.error(f"Error checking existing projects: {e}")
        return

    yaml_path = _get_data_dir() / "projects.yaml"
    logger.info(f"Loading projects from {yaml_path}...")

    # Use projects manager to load data
    try:
        from src.controller.projects_manager import ProjectsManager
        manager = ProjectsManager()
        success = manager.load_initial_data(db)
        if success:
            logger.info("Projects loaded successfully.")
    except Exception as e:
        logger.error(f"Failed loading projects: {e}", exc_info=True)


def _load_data_contracts(db: Session) -> None:
    """Load data contracts from YAML file."""
    yaml_path = _get_data_dir() / "data_contracts.yaml"
    logger.info(f"Loading data contracts from {yaml_path}...")

    try:
        from src.controller.data_contracts_manager import DataContractsManager
        # DataContractsManager needs data_dir and tags_manager
        manager = DataContractsManager(data_dir=_get_data_dir(), tags_manager=None)
        success = manager.load_initial_data(db)
        if success:
            logger.info("Data contracts loaded successfully.")
    except Exception as e:
        logger.error(f"Failed loading data contracts: {e}", exc_info=True)


def _load_data_products(db: Session, ws_client=None, notifications_manager=None, tags_manager=None) -> None:
    """Load data products from YAML file."""
    from src.db_models.data_products import DataProductDb

    # Check if products exist
    try:
        existing = db.query(DataProductDb).limit(1).all()
        if existing:
            logger.debug("Data products table not empty. Skipping.")
            return
    except Exception as e:
        logger.error(f"Error checking existing products: {e}")
        return

    yaml_path = _get_data_dir() / "data_products.yaml"
    logger.info(f"Loading data products from {yaml_path}...")

    try:
        from src.controller.data_products_manager import DataProductsManager
        manager = DataProductsManager(
            db=db,
            ws_client=ws_client,
            notifications_manager=notifications_manager,
            tags_manager=tags_manager
        )
        success = manager.load_initial_data(db)
        if success:
            logger.info("Data products loaded successfully.")
    except Exception as e:
        logger.error(f"Failed loading data products: {e}", exc_info=True)


def _load_data_asset_reviews(db: Session, ws_client=None, notifications_manager=None) -> None:
    """Load data asset reviews from YAML file."""
    yaml_path = _get_data_dir() / "data_asset_reviews.yaml"
    logger.info(f"Loading data asset reviews from {yaml_path}...")

    try:
        from src.controller.data_asset_reviews_manager import DataAssetReviewManager
        manager = DataAssetReviewManager(
            db=db,
            ws_client=ws_client,
            notifications_manager=notifications_manager
        )
        success = manager.load_initial_data(db)
        if success:
            logger.info("Data asset reviews loaded successfully.")
    except Exception as e:
        logger.error(f"Failed loading data asset reviews: {e}", exc_info=True)


def _load_semantic_models(db: Session) -> None:
    """Load semantic models from data directory."""
    logger.info("Loading semantic models...")

    try:
        from src.controller.semantic_models_manager import SemanticModelsManager
        manager = SemanticModelsManager(db=db, data_dir=_get_data_dir())
        manager.load_initial_data(db)
        logger.info("Semantic models loaded successfully.")
    except Exception as e:
        logger.error(f"Failed loading semantic models: {e}", exc_info=True)


def _load_notifications(db: Session) -> None:
    """Load example notifications from YAML file."""
    yaml_path = _get_data_dir() / "notifications.yaml"
    logger.info(f"Loading notifications from {yaml_path}...")

    try:
        from src.controller.notifications_manager import NotificationsManager
        from src.controller.settings_manager import SettingsManager

        # NotificationsManager needs settings_manager
        # We'll need to get it from app.state (will be passed in main function)
        # For now, create a minimal instance
        settings_manager = None  # TODO: Get from app.state
        manager = NotificationsManager(settings_manager=settings_manager)
        success = manager.load_initial_data(db)
        if success:
            logger.info("Notifications loaded successfully.")
    except Exception as e:
        logger.error(f"Failed loading notifications: {e}", exc_info=True)


def _load_demo_semantic_links(db: Session) -> None:
    """Load demo semantic links between app entities and business concepts."""
    logger.info("Loading demo semantic links...")

    yaml_path = _get_data_dir() / "semantic_links_demo.yaml"
    if not yaml_path.exists():
        logger.warning(f"Semantic links demo file not found: {yaml_path}")
        return

    try:
        from src.controller.semantic_links_manager import SemanticLinksManager
        from src.models.semantic_links import EntitySemanticLinkCreate
        from src.db_models.data_products import DataProductDb
        from src.db_models.data_domains import DataDomain

        semantic_links_manager = SemanticLinksManager(db)
        config = _load_yaml(yaml_path)

        if not config or 'semantic_links' not in config:
            logger.warning("No semantic_links section found in config")
            return

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
                    domain = db.query(DataDomain).filter(DataDomain.name == entity_name).first()
                    if domain:
                        entity_id = str(domain.id)
                elif entity_type == 'data_product':
                    product = db.query(DataProductDb).filter(DataProductDb.name == entity_name).first()
                    if product:
                        entity_id = str(product.id)
                elif entity_type == 'data_contract':
                    from src.db_models.data_contracts import DataContractDb
                    contract = db.query(DataContractDb).filter(DataContractDb.name == entity_name).first()
                    if contract:
                        entity_id = str(contract.id)

                if entity_id:
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


def _load_compliance(db: Session) -> None:
    """Load compliance policies and sample runs from YAML file."""
    from src.db_models.compliance import CompliancePolicyDb

    # Check if policies exist
    try:
        existing_count = db.query(CompliancePolicyDb).count()
        if existing_count > 0:
            logger.debug("Compliance policies already present. Skipping.")
            return
    except Exception as e:
        logger.error(f"Error checking compliance policies: {e}")
        return

    yaml_path = _get_data_dir() / "compliance.yaml"
    if not yaml_path.exists():
        logger.debug(f"Compliance YAML not found at {yaml_path}. Skipping.")
        return

    logger.info(f"Loading compliance policies from {yaml_path}...")

    try:
        from src.controller.compliance_manager import ComplianceManager
        ComplianceManager().load_from_yaml(db, str(yaml_path))
        logger.info("Compliance policies loaded successfully.")
    except Exception as e:
        logger.error(f"Failed loading compliance data: {e}", exc_info=True)


def _load_demo_timeline(db: Session, data_domain_manager=None) -> None:
    """Load demo timeline entries for data domains."""
    logger.info("Loading demo timeline entries...")

    try:
        if data_domain_manager and hasattr(data_domain_manager, 'load_demo_timeline_entries'):
            data_domain_manager.load_demo_timeline_entries(db)
            logger.info("Demo timeline entries loaded successfully.")
        else:
            logger.warning("DataDomainManager not available or missing load_demo_timeline_entries method")
    except Exception as e:
        logger.error(f"Failed loading demo timeline entries: {e}", exc_info=True)


def _load_metadata(db: Session) -> None:
    """Load example metadata (rich text, links, documents) for products and domains."""
    from src.utils.metadata_seed_loader import seed_metadata_from_yaml

    yaml_path = _get_data_dir() / "metadata" / "product_metadata.yaml"
    if not yaml_path.exists():
        logger.debug(f"Metadata YAML not found at {yaml_path}. Skipping.")
        return

    logger.info(f"Loading metadata from {yaml_path}...")

    try:
        settings = get_settings()
        seed_metadata_from_yaml(db, settings, yaml_path)
        logger.info("Metadata loaded successfully.")
    except Exception as e:
        logger.error(f"Failed loading metadata: {e}", exc_info=True)


def _load_costs(db: Session) -> None:
    """Load example cost items from YAML file."""
    from src.utils.costs_seed_loader import seed_costs_from_yaml

    yaml_path = _get_data_dir() / "costs.yaml"
    if not yaml_path.exists():
        logger.debug(f"Costs YAML not found at {yaml_path}. Skipping.")
        return

    logger.info(f"Loading costs from {yaml_path}...")

    try:
        seed_costs_from_yaml(db, yaml_path)
        logger.info("Costs loaded successfully.")
    except Exception as e:
        logger.error(f"Failed loading costs: {e}", exc_info=True)


# =============================================================================
# Main Orchestrator
# =============================================================================

def load_all_demo_data(app: FastAPI, db: Session) -> None:
    """
    Load all demo/example data when APP_DEMO_MODE is enabled.

    This function orchestrates loading data in the correct dependency order:
    1. Data Domains (no dependencies)
    2. Teams (depends on domains)
    3. Projects (depends on teams)
    4. Data Contracts, Data Products (depend on domains/teams)
    5. Data Asset Reviews (depends on products/contracts)
    6. Semantic Models, Notifications
    7. Semantic Links (depends on all entities)
    8. Compliance, Timeline, Metadata, Costs (cross-cutting)

    Args:
        app: FastAPI application instance (provides access to app.state managers)
        db: SQLAlchemy database session
    """
    logger.info("=" * 80)
    logger.info("Starting demo data loading process...")
    logger.info("=" * 80)

    try:
        # Get managers from app.state
        settings_manager = getattr(app.state, 'settings_manager', None)
        auth_manager = getattr(app.state, 'authorization_manager', None)
        data_asset_review_manager = getattr(app.state, 'data_asset_review_manager', None)
        data_product_manager = getattr(app.state, 'data_products_manager', None)
        data_domain_manager = getattr(app.state, 'data_domain_manager', None)
        data_contracts_manager = getattr(app.state, 'data_contracts_manager', None)
        notifications_manager = getattr(app.state, 'notifications_manager', None)
        teams_manager = getattr(app.state, 'teams_manager', None)
        projects_manager = getattr(app.state, 'projects_manager', None)
        semantic_models_manager = getattr(app.state, 'semantic_models_manager', None)
        ws_client = getattr(app.state, 'ws_client', None)
        tags_manager = getattr(app.state, 'tags_manager', None)

        # Phase 1: Core entities (in dependency order)
        logger.info("Phase 1: Loading core entities...")

        # Load settings and auth data
        if settings_manager and hasattr(settings_manager, 'load_initial_data'):
            settings_manager.load_initial_data(db)
        if auth_manager and hasattr(auth_manager, 'load_initial_data'):
            auth_manager.load_initial_data(db)

        # Load domains first (no dependencies)
        _load_domains(db)

        # Load teams (depends on domains)
        _load_teams(db)

        # Load projects (depends on teams)
        _load_projects(db)

        # Phase 2: Feature data
        logger.info("Phase 2: Loading feature data...")

        # Load data contracts and products (depend on domains/teams)
        if data_contracts_manager and hasattr(data_contracts_manager, 'load_initial_data'):
            data_contracts_manager.load_initial_data(db)

        if data_product_manager and hasattr(data_product_manager, 'load_initial_data'):
            data_product_manager.load_initial_data(db)

        if data_asset_review_manager and hasattr(data_asset_review_manager, 'load_initial_data'):
            data_asset_review_manager.load_initial_data(db)

        # Load semantic models
        if semantic_models_manager and hasattr(semantic_models_manager, 'load_initial_data'):
            semantic_models_manager.load_initial_data(db)

        # Load notifications
        if notifications_manager and hasattr(notifications_manager, 'load_initial_data'):
            notifications_manager.load_initial_data(db)

        # Phase 3: Cross-cutting data
        logger.info("Phase 3: Loading cross-cutting data...")

        # Load demo timeline entries
        _load_demo_timeline(db, data_domain_manager)

        # Load demo semantic links (depends on all entities)
        _load_demo_semantic_links(db)

        # Update knowledge graph after loading semantic links
        try:
            if semantic_models_manager:
                semantic_models_manager.on_models_changed()
        except Exception as e:
            logger.warning(f"Failed updating knowledge graph: {e}")

        # Load compliance data
        _load_compliance(db)

        # Load metadata (notes, links, documents)
        _load_metadata(db)

        # Load cost items
        _load_costs(db)

        logger.info("=" * 80)
        logger.info("Demo data loading completed successfully!")
        logger.info("=" * 80)

    except Exception as e:
        logger.exception(f"Error during demo data loading: {e}")
        db.rollback()
        raise
