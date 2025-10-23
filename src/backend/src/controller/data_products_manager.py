"""
ODPS v1.0.0 Data Products Manager

This module implements the business logic layer for ODPS v1.0.0 Data Products.
Handles product creation, updates, versioning, contract integration, and search indexing.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

import yaml
from pydantic import ValidationError
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound, PermissionDenied

from src.models.data_products import (
    DataProduct as DataProductApi,
    DataProductCreate,
    DataProductUpdate,
    DataProductStatus,
    Description,
    AuthoritativeDefinition,
    CustomProperty,
    InputPort,
    OutputPort,
    ManagementPort,
    Support,
    Team,
    TeamMember,
    GenieSpaceRequest,
    NewVersionRequest
)
from src.models.users import UserInfo
from src.repositories.data_products_repository import data_product_repo
from src.common.search_interfaces import SearchableAsset, SearchIndexItem
from src.common.search_registry import searchable_asset
from src.controller.notifications_manager import NotificationsManager
from src.controller.tags_manager import TagsManager
from src.repositories.tags_repository import entity_tag_repo
from src.models.tags import AssignedTagCreate
from src.common.logging import get_logger
from src.common.database import get_session_factory

logger = get_logger(__name__)


@searchable_asset
class DataProductsManager(SearchableAsset):
    def __init__(
        self,
        db: Session,
        ws_client: Optional[WorkspaceClient] = None,
        notifications_manager: Optional[NotificationsManager] = None,
        tags_manager: Optional[TagsManager] = None
    ):
        """
        Initializes the DataProductsManager for ODPS v1.0.0.

        Args:
            db: SQLAlchemy Session for database operations.
            ws_client: Optional Databricks WorkspaceClient for SDK operations.
            notifications_manager: Optional NotificationsManager instance.
            tags_manager: Optional TagsManager for tag operations.
        """
        self._db = db
        self._ws_client = ws_client
        self._repo = data_product_repo
        self._notifications_manager = notifications_manager
        self._tags_manager = tags_manager
        self._entity_tag_repo = entity_tag_repo

        if not self._ws_client:
            logger.warning("WorkspaceClient not provided to DataProductsManager. SDK operations might fail.")
        if not self._notifications_manager:
            logger.warning("NotificationsManager not provided. Notifications will not be sent.")
        if not self._tags_manager:
            logger.warning("TagsManager not provided. Tag operations will not be available.")

    def get_statuses(self) -> List[str]:
        """Get all ODPS v1.0.0 status values."""
        return [s.value for s in DataProductStatus]

    def create_product(self, product_data: Dict[str, Any]) -> DataProductApi:
        """Creates a new ODPS v1.0.0 data product via the repository."""
        logger.debug(f"Manager creating ODPS product from data: {product_data}")
        try:
            # Generate ID if missing
            if not product_data.get('id'):
                product_data['id'] = str(uuid.uuid4())
                logger.info(f"Generated ID {product_data['id']} for new product.")

            # Ensure ODPS required fields have defaults
            product_data.setdefault('apiVersion', 'v1.0.0')
            product_data.setdefault('kind', 'DataProduct')
            product_data.setdefault('status', DataProductStatus.DRAFT.value)

            # Validate
            try:
                product_api_model = DataProductCreate(**product_data)
            except ValidationError as e:
                logger.error(f"Validation failed for ODPS product: {e}")
                raise ValueError(f"Invalid ODPS product data: {e}") from e

            # Extract tags (handled separately)
            tags_data = product_data.get('tags', [])

            # Create via repository
            created_db_obj = self._repo.create(db=self._db, obj_in=product_api_model)

            # Handle tag assignments
            if tags_data and self._tags_manager:
                try:
                    self._assign_tags_to_product(created_db_obj.id, tags_data)
                except Exception as e:
                    logger.error(f"Failed to assign tags to product {created_db_obj.id}: {e}")

            # Load and return with tags
            return self._load_product_with_tags(created_db_obj)

        except SQLAlchemyError as e:
            logger.error(f"Database error creating ODPS product: {e}")
            raise
        except ValueError as e:
            logger.error(f"Value error during ODPS product creation: {e}")
            raise

    def get_product(self, product_id: str) -> Optional[DataProductApi]:
        """Get an ODPS v1.0.0 data product by ID."""
        try:
            product_db = self._repo.get(db=self._db, id=product_id)
            if product_db:
                return self._load_product_with_tags(product_db)
            return None
        except SQLAlchemyError as e:
            logger.error(f"Database error getting product {product_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting product {product_id}: {e}")
            raise

    def list_products(self, skip: int = 0, limit: int = 100) -> List[DataProductApi]:
        """List ODPS v1.0.0 data products."""
        try:
            products_db = self._repo.get_multi(db=self._db, skip=skip, limit=limit)
            products_with_tags = []
            for product_db in products_db:
                product_with_tags = self._load_product_with_tags(product_db)
                products_with_tags.append(product_with_tags)
            return products_with_tags
        except SQLAlchemyError as e:
            logger.error(f"Database error listing products: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error listing products: {e}")
            raise

    def update_product(self, product_id: str, product_data_dict: Dict[str, Any]) -> Optional[DataProductApi]:
        """Update an existing ODPS v1.0.0 data product."""
        logger.debug(f"Manager updating ODPS product {product_id}")
        try:
            db_obj = self._repo.get(db=self._db, id=product_id)
            if not db_obj:
                logger.warning(f"Attempted to update non-existent product: {product_id}")
                return None

            # Extract tags (handled separately)
            tags_data = product_data_dict.get('tags', [])

            # Prepare update payload
            update_payload = product_data_dict.copy()
            update_payload['id'] = product_id

            # Validate
            try:
                product_update_model = DataProductUpdate(**update_payload)
            except ValidationError as e:
                logger.error(f"Validation error for ODPS update: {e}")
                raise ValueError(f"Invalid ODPS update data: {e}") from e

            # Update via repository
            updated_db_obj = self._repo.update(db=self._db, db_obj=db_obj, obj_in=product_update_model)

            # Handle tag updates
            if tags_data is not None and self._tags_manager:
                try:
                    self._assign_tags_to_product(product_id, tags_data)
                except Exception as e:
                    logger.error(f"Failed to update tags for product {product_id}: {e}")

            # Load and return with tags
            return self._load_product_with_tags(updated_db_obj)

        except SQLAlchemyError as e:
            logger.error(f"Database error updating ODPS product {product_id}: {e}")
            raise
        except ValueError as e:
            logger.error(f"Value error updating ODPS product {product_id}: {e}")
            raise

    def delete_product(self, product_id: str) -> bool:
        """Delete an ODPS v1.0.0 data product."""
        try:
            deleted_obj = self._repo.remove(db=self._db, id=product_id)
            return deleted_obj is not None
        except SQLAlchemyError as e:
            logger.error(f"Database error deleting product {product_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting product {product_id}: {e}")
            raise

    def create_new_version(self, original_product_id: str, request: NewVersionRequest) -> DataProductApi:
        """Creates a new version of an ODPS v1.0.0 data product."""
        logger.info(f"Creating new ODPS version '{request.new_version}' from product {original_product_id}")

        original_product = self.get_product(original_product_id)
        if not original_product:
            raise ValueError(f"Original data product with ID {original_product_id} not found.")

        # Create new product data (exclude id, created_at, updated_at)
        new_product_data = original_product.model_dump(
            exclude={'id', 'created_at', 'updated_at'}
        )

        # Generate new ID and set new version
        new_product_data['id'] = str(uuid.uuid4())
        new_product_data['version'] = request.new_version

        # Reset status to DRAFT
        new_product_data['status'] = DataProductStatus.DRAFT.value
        logger.info(f"Resetting status to DRAFT for new version {new_product_data['id']}")

        try:
            # Validate and create
            new_product_api_model = DataProductCreate(**new_product_data)
            created_db_obj = self._repo.create(db=self._db, obj_in=new_product_api_model)

            logger.info(f"Successfully created new version {request.new_version} (ID: {created_db_obj.id})")
            return DataProductApi.model_validate(created_db_obj)

        except ValidationError as e:
            logger.error(f"Validation error creating new ODPS version: {e}")
            raise ValueError(f"Validation error creating new version: {e}")
        except SQLAlchemyError as e:
            logger.error(f"Database error creating new version: {e}")
            raise

    async def initiate_genie_space_creation(self, request: GenieSpaceRequest, user_info: UserInfo, db: Session):
        """Initiates Genie Space creation for selected ODPS data products."""
        if not self._notifications_manager:
            logger.error("Cannot initiate Genie Space creation: NotificationsManager not configured.")
            raise RuntimeError("Notification system is not available.")

        user_email = user_info.email
        product_ids_str = ", ".join(request.product_ids)
        logger.info(f"Initiating Genie Space for products: {product_ids_str} by {user_email}")

        # Send initial notification
        try:
            await self._notifications_manager.create_notification(
                db=db,
                user_id=user_email,
                title="Genie Space Creation Started",
                description=f"Genie Space creation for Data Product(s) {product_ids_str} initiated. "
                           "You will be notified when it's ready.",
                status="info"
            )
        except Exception as e:
            logger.error(f"Failed to send initial Genie Space notification: {e}", exc_info=True)

        # Schedule background task
        asyncio.create_task(self._simulate_genie_space_completion(request.product_ids, user_email))
        logger.info(f"Genie Space background simulation scheduled for: {product_ids_str}")

    async def _simulate_genie_space_completion(self, product_ids: List[str], user_email: str):
        """Simulates Genie Space completion and sends notification."""
        logger.info(f"Starting Genie Space simulation for products: {product_ids}. Waiting...")
        await asyncio.sleep(15)
        logger.info(f"Simulation wait complete for products: {product_ids}.")

        product_ids_str = ", ".join(product_ids)
        mock_genie_space_url = f"https://<databricks-host>/genie-space/{uuid.uuid4()}"
        logger.info(f"Simulated Genie Space creation completed. Mock URL: {mock_genie_space_url}")

        if not self._notifications_manager:
            logger.error("Cannot send Genie Space completion notification: NotificationsManager not configured.")
            return

        session_factory = get_session_factory()
        if not session_factory:
            logger.error("Cannot send notification: Database session factory not available.")
            return

        try:
            with session_factory() as db_session:
                logger.info(f"Creating completion notification for {user_email}...")
                await self._notifications_manager.create_notification(
                    db=db_session,
                    user_id=user_email,
                    title="Genie Space Ready",
                    description=f"Your Genie Space for Data Product(s) {product_ids_str} is ready.",
                    link=mock_genie_space_url,
                    status="success"
                )
                logger.info(f"Completion notification created for {user_email}.")
        except Exception as e:
            logger.error(f"Failed to send Genie Space completion notification: {e}", exc_info=True)

    def load_initial_data(self, db: Session) -> bool:
        """Load ODPS v1.0.0 data products from YAML file into the database if empty."""
        # Check if products already exist
        try:
            existing_products = self._repo.get_multi(db=db, limit=1)
            if existing_products:
                logger.info("Data products table not empty. Skipping initial data loading.")
                return False
        except SQLAlchemyError as e:
            logger.error(f"Error checking for existing data products: {e}", exc_info=True)
            raise

        # Construct YAML path
        base_dir = Path(__file__).parent.parent
        yaml_path = base_dir / "data" / "data_products.yaml"
        logger.info(f"Attempting to load ODPS initial data from {yaml_path}...")

        try:
            if not yaml_path.is_file():
                logger.warning(f"ODPS data file not found at {yaml_path}. No products loaded.")
                return False

            with yaml_path.open() as file:
                data = yaml.safe_load(file)

            if not isinstance(data, list):
                logger.error(f"YAML file {yaml_path} should contain a list of ODPS products.")
                return False

            loaded_count = 0
            errors = 0

            for product_dict in data:
                if not isinstance(product_dict, dict):
                    logger.warning("Skipping non-dictionary item in YAML data.")
                    continue

                try:
                    # Generate ID if missing
                    if not product_dict.get('id'):
                        product_dict['id'] = str(uuid.uuid4())

                    # Ensure ODPS required fields
                    product_dict.setdefault('apiVersion', 'v1.0.0')
                    product_dict.setdefault('kind', 'DataProduct')
                    product_dict.setdefault('status', DataProductStatus.DRAFT.value)

                    # Extract top-level tags for internal tag assignment
                    # IMPORTANT: Do NOT preprocess nested tags (in ports) as ODPS expects simple strings
                    tags_data_raw = product_dict.pop('tags', [])
                    
                    # Convert top-level tags to internal format for tag assignment
                    tags_data = []
                    if tags_data_raw:
                        for tag_item in tags_data_raw:
                            if isinstance(tag_item, str):
                                tags_data.append({"tag_fqn": tag_item, "assigned_value": None})
                            elif isinstance(tag_item, dict):
                                if 'assigned_value' not in tag_item:
                                    tag_item['assigned_value'] = None
                                tags_data.append(tag_item)

                    # Create API model and save (nested tags remain as strings for ODPS compliance)
                    product_api = DataProductCreate(**product_dict)
                    existing_db = self._repo.get(db=db, id=product_api.id)

                    if existing_db:
                        logger.warning(f"Product ID {product_api.id} exists, updating from YAML.")
                        self._repo.update(db=db, db_obj=existing_db, obj_in=product_api)
                    else:
                        logger.info(f"Creating ODPS product ID {product_api.id} from YAML.")
                        self._repo.create(db=db, obj_in=product_api)

                    # Assign tags
                    if tags_data and self._tags_manager:
                        self._assign_tags_to_product(product_api.id, tags_data)

                    loaded_count += 1

                except (ValidationError, ValueError, SQLAlchemyError) as e:
                    if isinstance(e, ValidationError):
                        logger.error(f"Validation error for ODPS product (ID: {product_dict.get('id', 'N/A')}): "
                                   f"{len(e.errors())} errors")
                        for i, error in enumerate(e.errors()):
                            logger.error(f"  Error {i+1}: {error}")
                    else:
                        logger.error(f"Error processing ODPS product (ID: {product_dict.get('id', 'N/A')}): {e}")
                    db.rollback()
                    errors += 1
                except Exception as inner_e:
                    logger.error(f"Unexpected error processing ODPS product (ID: {product_dict.get('id', 'N/A')}): "
                               f"{inner_e}", exc_info=True)
                    db.rollback()
                    errors += 1

            if errors == 0 and loaded_count > 0:
                db.commit()
                logger.info(f"Successfully loaded {loaded_count} ODPS products from {yaml_path}.")
            elif loaded_count > 0 and errors > 0:
                logger.warning(f"Processed {loaded_count + errors} ODPS products, but encountered {errors} errors.")
            elif errors > 0:
                logger.error(f"Encountered {errors} errors processing ODPS products. No products loaded.")
            else:
                logger.info(f"No new ODPS products found to load from {yaml_path}.")

            return loaded_count > 0 and errors == 0

        except FileNotFoundError:
            logger.warning(f"ODPS data file not found at {yaml_path}. No products loaded.")
            return False
        except yaml.YAMLError as e:
            logger.error(f"Error parsing ODPS YAML file {yaml_path}: {e}")
            db.rollback()
            return False
        except SQLAlchemyError as e:
            logger.error(f"Database error during ODPS initial data load: {e}", exc_info=True)
            db.rollback()
            return False
        except Exception as e:
            logger.error(f"Unexpected error during ODPS YAML load: {e}", exc_info=True)
            db.rollback()
            return False

    def save_to_yaml(self, yaml_path: str) -> bool:
        """Save current ODPS v1.0.0 data products to a YAML file."""
        try:
            all_products_api = self.list_products(limit=10000)
            products_list = [p.model_dump(by_alias=True) for p in all_products_api]

            with open(yaml_path, 'w') as file:
                yaml.dump(products_list, file, default_flow_style=False, sort_keys=False)

            logger.info(f"Saved {len(products_list)} ODPS products to {yaml_path}")
            return True

        except Exception as e:
            logger.error(f"Error saving ODPS products to YAML {yaml_path}: {e}")
            return False

    # --- ODPS-specific query helpers ---

    def get_distinct_domains(self) -> List[str]:
        """Get distinct domain values from ODPS products."""
        try:
            return self._repo.get_distinct_domains(db=self._db)
        except Exception as e:
            logger.error(f"Error getting distinct domains: {e}", exc_info=True)
            return []

    def get_distinct_tenants(self) -> List[str]:
        """Get distinct tenant values from ODPS products."""
        try:
            return self._repo.get_distinct_tenants(db=self._db)
        except Exception as e:
            logger.error(f"Error getting distinct tenants: {e}", exc_info=True)
            return []

    def get_distinct_statuses(self) -> List[str]:
        """Get all distinct ODPS status values."""
        try:
            return self._repo.get_distinct_statuses(db=self._db)
        except Exception as e:
            logger.error(f"Error getting distinct statuses: {e}", exc_info=True)
            return []

    def get_distinct_product_types(self) -> List[str]:
        """Get distinct product types from output ports."""
        try:
            return self._repo.get_distinct_product_types(db=self._db)
        except Exception as e:
            logger.error(f"Error getting distinct product types: {e}", exc_info=True)
            return []

    def get_distinct_owners(self) -> List[str]:
        """Get distinct owner names from product teams."""
        try:
            return self._repo.get_distinct_owners(db=self._db)
        except Exception as e:
            logger.error(f"Error getting distinct owners: {e}", exc_info=True)
            return []

    # --- SearchableAsset implementation ---

    def get_search_index_items(self) -> List[SearchIndexItem]:
        """Fetches ODPS v1.0.0 data products and maps them to SearchIndexItem format."""
        logger.info("Fetching ODPS products for search indexing...")
        items = []

        try:
            products_api = self.list_products(limit=10000)

            for product in products_api:
                if not product.id or not product.name:
                    logger.warning(f"Skipping ODPS product due to missing id or name: {product}")
                    continue

                # Get description from ODPS structured description
                description = ""
                if product.description:
                    parts = []
                    if product.description.purpose:
                        parts.append(product.description.purpose)
                    if product.description.usage:
                        parts.append(product.description.usage)
                    description = " | ".join(parts)

                # Normalize tags
                tag_strings: List[str] = []
                try:
                    for t in (product.tags or []):
                        if isinstance(t, dict):
                            fqn = t.get('tag_fqn')
                            if fqn:
                                tag_strings.append(str(fqn))
                        else:
                            tag_strings.append(str(t))
                except Exception:
                    tag_strings = []

                items.append(
                    SearchIndexItem(
                        id=f"product::{product.id}",
                        version=product.version,
                        type="data-product",
                        feature_id="data-products",
                        title=product.name,
                        description=description,
                        link=f"/data-products/{product.id}",
                        tags=tag_strings
                    )
                )

            logger.info(f"Prepared {len(items)} ODPS products for search index.")
            return items

        except Exception as e:
            logger.error(f"Error fetching/mapping ODPS products for search: {e}", exc_info=True)
            return []

    # --- Tag integration helpers ---

    def _assign_tags_to_product(self, product_id: str, tags_data: List[Dict[str, Any]]) -> None:
        """Helper to assign tags to an ODPS data product."""
        if not self._tags_manager:
            logger.warning("TagsManager not available, cannot assign tags")
            return

        try:
            assigned_tags = []
            for tag_data in tags_data:
                if isinstance(tag_data, dict):
                    try:
                        assigned_tag = AssignedTagCreate(**tag_data)
                        assigned_tags.append(assigned_tag)
                    except Exception as e:
                        logger.warning(f"Failed to parse tag data {tag_data}: {e}")
                else:
                    try:
                        assigned_tag = AssignedTagCreate(tag_fqn=str(tag_data), assigned_value=None)
                        assigned_tags.append(assigned_tag)
                    except Exception as e:
                        logger.warning(f"Failed to create AssignedTagCreate from string {tag_data}: {e}")

            if not assigned_tags:
                logger.debug(f"No valid tags to assign to ODPS product {product_id}")
                return

            self._tags_manager.set_tags_for_entity(
                db=self._db,
                entity_id=product_id,
                entity_type="data_product",
                tags=assigned_tags,
                user_email="system"
            )
            logger.debug(f"Successfully assigned {len(assigned_tags)} tags to ODPS product {product_id}")

        except Exception as e:
            logger.error(f"Failed to assign tags to ODPS product {product_id}: {e}", exc_info=True)

    def _load_product_with_tags(self, db_obj) -> DataProductApi:
        """Helper to load an ODPS data product with its associated tags."""
        try:
            product_api = DataProductApi.model_validate(db_obj)

            if self._tags_manager:
                try:
                    assigned_tags = self._entity_tag_repo.get_assigned_tags_for_entity(
                        db=self._db,
                        entity_id=db_obj.id,
                        entity_type="data_product"
                    )
                    product_api.tags = assigned_tags
                except Exception as e:
                    logger.error(f"Failed to load tags for ODPS product {db_obj.id}: {e}")
                    product_api.tags = []
            else:
                product_api.tags = []

            return product_api

        except Exception as e:
            logger.error(f"Failed to load ODPS product with tags: {e}")
            return DataProductApi.model_validate(db_obj)

    def assign_tag_to_product(self, product_id: str, tag_id: str, assigned_value: Optional[str] = None,
                              assigned_by: str = "system") -> bool:
        """Public method to assign a tag to an ODPS data product."""
        if not self._tags_manager:
            logger.error("TagsManager not available, cannot assign tag")
            return False

        try:
            self._entity_tag_repo.add_tag_to_entity(
                db=self._db,
                tag_id=tag_id,
                entity_id=product_id,
                entity_type="data_product",
                assigned_value=assigned_value,
                assigned_by=assigned_by
            )
            return True
        except Exception as e:
            logger.error(f"Failed to assign tag {tag_id} to ODPS product {product_id}: {e}")
            return False

    def remove_tag_from_product(self, product_id: str, tag_id: str) -> bool:
        """Public method to remove a tag from an ODPS data product."""
        if not self._tags_manager:
            logger.error("TagsManager not available, cannot remove tag")
            return False

        try:
            return self._entity_tag_repo.remove_tag_from_entity(
                db=self._db,
                tag_id=tag_id,
                entity_id=product_id,
                entity_type="data_product"
            )
        except Exception as e:
            logger.error(f"Failed to remove tag {tag_id} from ODPS product {product_id}: {e}")
            return False

    def get_product_tags(self, product_id: str) -> List[Dict[str, Any]]:
        """Public method to get all tags assigned to an ODPS data product."""
        if not self._tags_manager:
            logger.warning("TagsManager not available, returning empty tags list")
            return []

        try:
            return self._entity_tag_repo.get_assigned_tags_for_entity(
                db=self._db,
                entity_id=product_id,
                entity_type="data_product"
            )
        except Exception as e:
            logger.error(f"Failed to get tags for ODPS product {product_id}: {e}")
            return []

    def _preprocess_tags_for_yaml_loading(self, product_dict: Dict[str, Any]) -> None:
        """Convert tag_fqn format in YAML to AssignedTagCreate format."""
        def process_tags_in_dict(obj: Dict[str, Any]):
            if 'tags' in obj and isinstance(obj['tags'], list):
                new_tags = []
                for tag_item in obj['tags']:
                    if isinstance(tag_item, dict) and 'tag_fqn' in tag_item:
                        if 'assigned_value' not in tag_item:
                            tag_item['assigned_value'] = None
                        new_tags.append(tag_item)
                    elif isinstance(tag_item, str):
                        new_tags.append({"tag_fqn": tag_item, "assigned_value": None})
                    else:
                        if isinstance(tag_item, dict) and 'assigned_value' not in tag_item:
                            tag_item['assigned_value'] = None
                        new_tags.append(tag_item)
                obj['tags'] = new_tags

            for key, value in obj.items():
                if isinstance(value, dict):
                    process_tags_in_dict(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            process_tags_in_dict(item)

        process_tags_in_dict(product_dict)

    # --- Contract-Product Integration (ODPS v1.0.0) ---

    def create_from_contract(
        self,
        contract_id: str,
        product_name: str,
        version: str,
        output_port_name: Optional[str] = None
    ) -> DataProductApi:
        """
        Creates a new ODPS v1.0.0 Data Product from an existing Data Contract.

        The contract governs one output port of the product. Inherits domain,
        owner team, and project from the contract.

        Args:
            contract_id: ID of the contract to create product from
            product_name: Name for the new data product
            version: Version string for the product
            output_port_name: Optional name for the output port

        Returns:
            Created DataProduct API model

        Raises:
            ValueError: If contract doesn't exist or is not in valid status
        """
        logger.info(f"Creating ODPS Data Product '{product_name}' from contract {contract_id}")

        from src.repositories.data_contracts_repository import data_contract_repo

        # Validate contract exists
        contract_db = data_contract_repo.get(db=self._db, id=contract_id)
        if not contract_db:
            raise ValueError(f"Data Contract with ID {contract_id} not found")

        # Validate contract status
        valid_statuses = ['active', 'approved', 'certified']
        if contract_db.status and contract_db.status.lower() not in valid_statuses:
            raise ValueError(
                f"Cannot create product from contract in status '{contract_db.status}'. "
                f"Contract must be in one of: {', '.join(valid_statuses)}"
            )

        # Create ODPS product data
        product_id = str(uuid.uuid4())
        product_data = {
            'id': product_id,
            'apiVersion': 'v1.0.0',
            'kind': 'DataProduct',
            'name': product_name,
            'version': version,
            'status': DataProductStatus.DRAFT.value,
            'domain': contract_db.domain_id,  # Inherit from contract
            'description': {
                'purpose': f"Data Product created from contract: {contract_db.name}",
                'limitations': None,
                'usage': None
            },
            'inputPorts': [],
            'outputPorts': [
                {
                    'name': output_port_name or contract_db.name,
                    'version': version,
                    'description': f"Output governed by contract: {contract_db.name}",
                    'contractId': contract_id  # Link to contract
                }
            ]
        }

        # TODO: Add team members from contract owner
        if contract_db.owner_team_id:
            product_data['team'] = {
                'name': f"Team from contract {contract_db.name}",
                'members': []  # Could populate from contract owner
            }

        # Create the product
        created_product = self.create_product(product_data)
        logger.info(f"Successfully created ODPS Data Product {product_id} from contract {contract_id}")
        return created_product

    def get_products_by_contract(self, contract_id: str) -> List[DataProductApi]:
        """
        Get all ODPS Data Products that use a specific Data Contract.

        Args:
            contract_id: ID of the contract to search for

        Returns:
            List of DataProduct API models with output ports linked to this contract
        """
        logger.debug(f"Fetching ODPS products linked to contract {contract_id}")

        try:
            all_products = self.list_products(limit=10000)
            linked_products = []

            for product in all_products:
                if product.outputPorts:
                    for port in product.outputPorts:
                        if port.contractId == contract_id:
                            linked_products.append(product)
                            break

            logger.info(f"Found {len(linked_products)} ODPS products linked to contract {contract_id}")
            return linked_products

        except Exception as e:
            logger.error(f"Error fetching ODPS products by contract {contract_id}: {e}")
            raise

    def get_contracts_for_product(self, product_id: str) -> List[str]:
        """
        Get all Data Contract IDs associated with an ODPS Data Product's output ports.

        Args:
            product_id: ID of the product

        Returns:
            List of contract IDs (may be empty)
        """
        logger.debug(f"Fetching contracts for ODPS product {product_id}")

        try:
            product = self.get_product(product_id)
            if not product:
                raise ValueError(f"Product with ID {product_id} not found")

            contract_ids = []
            if product.outputPorts:
                for port in product.outputPorts:
                    if port.contractId and port.contractId not in contract_ids:
                        contract_ids.append(port.contractId)

            logger.info(f"Found {len(contract_ids)} contracts for ODPS product {product_id}")
            return contract_ids

        except Exception as e:
            logger.error(f"Error fetching contracts for ODPS product {product_id}: {e}")
            raise
