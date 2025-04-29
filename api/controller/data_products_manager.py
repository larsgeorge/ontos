import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

import yaml
from pydantic import ValidationError, parse_obj_as, BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

# Import Databricks SDK components
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound, PermissionDenied

from api.models.data_products import (
    DataOutput,
    DataProduct as DataProductApi,
    DataProductStatus,
    DataProductType,
    DataSource,
    SchemaField,
    GenieSpaceRequest,
)
from api.models.users import UserInfo

# Import the specific repository
from api.repositories.data_products_repository import data_product_repo

# Import Search Interfaces
from api.common.search_interfaces import SearchableAsset, SearchIndexItem
# Import the registry decorator
from api.common.search_registry import searchable_asset

# Import NotificationsManager (adjust path if necessary)
from api.controller.notifications_manager import NotificationsManager

from api.common.logging import setup_logging, get_logger
setup_logging(level=logging.INFO)
logger = get_logger(__name__)

# Import necessary components for creating a session
from api.common.database import get_session_factory

# Inherit from SearchableAsset
@searchable_asset
class DataProductsManager(SearchableAsset):
    def __init__(self, db: Session, ws_client: Optional[WorkspaceClient] = None, notifications_manager: Optional[NotificationsManager] = None):
        """
        Initializes the DataProductsManager.

        Args:
            db: SQLAlchemy Session for database operations.
            ws_client: Optional Databricks WorkspaceClient for SDK operations.
            notifications_manager: Optional NotificationsManager instance.
        """
        self._db = db
        self._ws_client = ws_client
        self._repo = data_product_repo
        self._notifications_manager = notifications_manager
        if not self._ws_client:
             logger.warning("WorkspaceClient was not provided to DataProductsManager. SDK operations might fail.")
        if not self._notifications_manager:
             logger.warning("NotificationsManager was not provided to DataProductsManager. Notifications will not be sent.")

    def get_types(self) -> List[str]:
        """Get all available data product types"""
        return [t.value for t in DataProductType]

    def get_statuses(self) -> List[str]:
        """Get all available data product statuses"""
        return [s.value for s in DataProductStatus]

    def create_product(self, product_data: Dict[str, Any]) -> DataProductApi:
        """Validates input data and creates a new data product via the repository."""
        logger.debug(f"Manager attempting to create product from data: {product_data}")
        try:
            # Validate the input dict into a Pydantic model first
            try:
                # Ensure ID exists before validation if needed
                if not product_data.get('id'):
                     product_data['id'] = str(uuid.uuid4())
                     logger.info(f"Generated ID {product_data['id']} during create_product validation.")
                
                # Ensure timestamps are set if missing from input data
                now = datetime.utcnow()
                product_data.setdefault('created_at', now)
                product_data.setdefault('updated_at', now)
                
                # Validate
                product_api_model = DataProductApi(**product_data)
                
            except ValidationError as e:
                 logger.error(f"Validation failed converting dict to DataProductApi model: {e}")
                 # Raise a specific error or handle as needed
                 raise ValueError(f"Invalid data provided for product creation: {e}") from e

            # Now pass the validated Pydantic model to the repository
            # The repository's create method expects the Pydantic model (DataProductCreate alias)
            created_db_obj = self._repo.create(db=self._db, obj_in=product_api_model)

            # Return the validated API model from the ORM object
            return DataProductApi.from_orm(created_db_obj)

        except SQLAlchemyError as e:
            logger.error(f"Database error creating data product: {e}")
            raise
        except ValueError as e: # Catch validation errors from above or repo mapping
            logger.error(f"Value error during product creation: {e}")
            raise # Re-raise ValueError
        except ValidationError as e:
            logger.error(f"Validation error mapping DB object to API model: {e}")
            raise ValueError(f"Internal data mapping error: {e}")

    def get_product(self, product_id: str) -> Optional[DataProductApi]:
        """Get a data product by ID using the repository."""
        try:
            product_db = self._repo.get(db=self._db, id=product_id)
            if product_db:
                # --- DEBUGGING START ---
                logger.info(f"--- DEBUG [DataProductsManager get_product] ---")
                logger.info(f"DB Object Type: {type(product_db)}")
                logger.info(f"DB Object ID: {product_db.id}")
                db_has_tags = hasattr(product_db, '_tags')
                logger.info(f"DB Object has '_tags' attribute: {db_has_tags}")
                if db_has_tags:
                     logger.info(f"DB Object '_tags' value: {product_db._tags}")
                     logger.info(f"DB Object '_tags' type: {type(product_db._tags)}")
                else:
                     logger.info(f"DB Object '_tags' attribute NOT FOUND.")
                # --- DEBUGGING END ---
                
                # Convert DB model to API model
                product_api = DataProductApi.from_orm(product_db)
                
                # --- DEBUGGING START ---
                logger.info(f"--- DEBUG [DataProductsManager get_product after from_orm] ---")
                logger.info(f"API Object Type: {type(product_api)}")
                logger.info(f"API Object ID: {product_api.id}")
                api_has_tags = hasattr(product_api, 'tags')
                logger.info(f"API Object has 'tags' attribute: {api_has_tags}")
                api_tags_value = "<Error accessing tags>" # Default for logging
                if api_has_tags:
                    try:
                         api_tags_value = product_api.tags # Access the computed field
                         logger.info(f"API Object 'tags' computed value: {api_tags_value}")
                         logger.info(f"API Object 'tags' type: {type(api_tags_value)}")
                    except Exception as e_compute:
                         logger.error(f"ERROR accessing computed 'tags' field: {e_compute}")
                else:
                     logger.info(f"API Object 'tags' attribute NOT FOUND.")
                # Log the dictionary representation
                try:
                    excluded_dump = product_api.model_dump(exclude={'tags'})
                    logger.info(f"API Object model_dump (excluding tags): {excluded_dump}")
                except Exception as e_dump_excl:
                    logger.error(f"ERROR dumping API model (excluding tags): {e_dump_excl}")
                try:
                    included_dump = product_api.model_dump()
                    logger.info(f"API Object model_dump (including tags?): {included_dump}")
                except Exception as e_dump_incl:
                    logger.error(f"ERROR dumping API model (including tags?): {e_dump_incl}")
                # --- DEBUGGING END ---
                
                return product_api
            return None
        except SQLAlchemyError as e:
            logger.error(f"Database error getting product {product_id}: {e}")
            raise
        except ValidationError as e:
            logger.error(f"Validation error mapping DB object to API model for ID {product_id}: {e}")
            raise ValueError(f"Internal data mapping error for ID {product_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting product {product_id}: {e}")
            raise

    def list_products(self, skip: int = 0, limit: int = 100) -> List[DataProductApi]:
        """List data products using the repository."""
        try:
            products_db = self._repo.get_multi(db=self._db, skip=skip, limit=limit)
            return parse_obj_as(List[DataProductApi], products_db)
        except SQLAlchemyError as e:
            logger.error(f"Database error listing products: {e}")
            raise
        except ValidationError as e:
             logger.error(f"Validation error mapping list of DB objects to API models: {e}")
             raise ValueError(f"Internal data mapping error during list: {e}")
        except Exception as e:
            logger.error(f"Unexpected error listing products: {e}")
            raise

    def update_product(self, product_id: str, product_data: DataProductApi) -> Optional[DataProductApi]:
        """Update an existing data product using the repository."""
        try:
            db_obj = self._repo.get(db=self._db, id=product_id)
            if not db_obj:
                logger.warning(f"Attempted to update non-existent product: {product_id}")
                return None

            product_data.id = product_id 
            product_data.updated_at = datetime.utcnow() 
            product_data.created_at = db_obj.created_at 

            updated_db_obj = self._repo.update(db=self._db, db_obj=db_obj, obj_in=product_data)
            
            return DataProductApi.from_orm(updated_db_obj)
            
        except SQLAlchemyError as e:
            logger.error(f"Database error updating data product {product_id}: {e}")
            raise
        except ValidationError as e:
            logger.error(f"Validation error during update/mapping for product {product_id}: {e}")
            raise ValueError(f"Invalid data or mapping error for update {product_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error updating data product {product_id}: {e}")
            raise

    def delete_product(self, product_id: str) -> bool:
        """Delete a data product using the repository."""
        try:
            deleted_obj = self._repo.remove(db=self._db, id=product_id)
            return deleted_obj is not None
        except SQLAlchemyError as e:
            logger.error(f"Database error deleting product {product_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting product {product_id}: {e}")
            raise

    def create_new_version(self, original_product_id: str, new_version: str) -> DataProductApi:
        """Creates a new version of a data product based on an existing one."""
        logger.info(f"Creating new version '{new_version}' based on product ID: {original_product_id}")
        original_product = self.get_product(original_product_id) # Fetches the API model
        if not original_product:
            raise ValueError(f"Original data product with ID {original_product_id} not found.")

        # Create a new dictionary from the original product
        # Use exclude to avoid copying fields that should be new/reset
        new_product_data = original_product.model_dump(
            exclude={'id', 'created_at', 'updated_at', 'version'}
        )

        # Generate a new ID and set the new version
        new_product_data['id'] = str(uuid.uuid4())
        new_product_data['version'] = new_version
        
        # Optionally reset status to DRAFT
        if 'info' in new_product_data and isinstance(new_product_data['info'], dict):
            new_product_data['info']['status'] = DataProductStatus.DRAFT.value
            logger.info(f"Resetting status to DRAFT for new version {new_product_data['id']}")
        else:
             logger.warning(f"Could not reset status for new version of {original_product_id} - info block missing or not a dict.")

        try:
            # Validate the dictionary as a DataProduct API model before creation
            new_product_api_model = DataProductApi(**new_product_data)
            
            # Create the new product in the database
            created_db_obj = self._repo.create(db=self._db, obj_in=new_product_api_model)
            
            logger.info(f"Successfully created new version {new_version} (ID: {created_db_obj.id}) from {original_product_id}")
            return DataProductApi.from_orm(created_db_obj)
        
        except ValidationError as e:
            logger.error(f"Validation error creating new version data: {e}")
            raise ValueError(f"Validation error creating new version: {e}")
        except SQLAlchemyError as e:
            logger.error(f"Database error creating new version: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating new version: {e}")
            raise

    async def initiate_genie_space_creation(self, request: GenieSpaceRequest, user_info: UserInfo, db: Session):
        """
        Simulates the initiation of a Genie Space creation process.

        Args:
            request: The request containing product IDs.
            user_info: The UserInfo object for the initiating user.
            db: The database session from the current request context.
        """
        if not self._notifications_manager:
            logger.error("Cannot initiate Genie Space creation: NotificationsManager is not configured.")
            raise RuntimeError("Notification system is not available.")

        user_email = user_info.email # Use email for recipient
        product_ids_str = ", ".join(request.product_ids)
        logger.info(f"Initiating Genie Space creation for products: {product_ids_str} by user: {user_email}")

        # 1. Send initial notification (pass the db session and use email)
        try:
            await self._notifications_manager.create_notification(
                db=db, # Pass the database session
                user_id=user_email, # Use email as recipient
                title="Genie Space Creation Started",
                description=f"Genie Space creation for Data Product(s) {product_ids_str} initiated. You will be notified when it's ready.",
                status="info"
            )
        except Exception as e:
            logger.error(f"Failed to send initial Genie Space creation notification: {e}", exc_info=True)
            # Proceed with simulation even if notification fails, but log it.

        # 2. Schedule background task, passing user email
        asyncio.create_task(self._simulate_genie_space_completion(request.product_ids, user_email))

        logger.info(f"Genie Space creation background simulation scheduled for products: {product_ids_str}")

    async def _simulate_genie_space_completion(self, product_ids: List[str], user_email: str):
        """Simulates the completion of Genie Space creation and sends notification."""
        # Import necessary components for creating a session
        from api.common.database import get_session_factory
        
        logger.info(f"Starting background simulation for Genie Space completion (products: {product_ids}). Waiting...")
        await asyncio.sleep(15) # Simulate a 15-second delay
        logger.info(f"Background simulation wait complete for products: {product_ids}.")

        product_ids_str = ", ".join(product_ids)
        mock_genie_space_url = f"https://<databricks-host>/genie-space/{uuid.uuid4()}"
        logger.info(f"Simulated Genie Space creation completed for products: {product_ids_str}. Mock URL: {mock_genie_space_url}")

        if not self._notifications_manager:
            logger.error("Cannot send Genie Space completion notification: NotificationsManager is not configured.")
            return

        session_factory = get_session_factory()
        if not session_factory:
            logger.error("Cannot send Genie Space completion notification: Database session factory not available.")
            return

        db_session = None
        try:
            # Create a new session specifically for this background task
            with session_factory() as db_session:
                logger.info(f"Creating completion notification for user {user_email}...")
                await self._notifications_manager.create_notification(
                    db=db_session, # Pass the new database session
                    user_id=user_email, # Use email as recipient
                    title="Genie Space Ready",
                    description=f"Your Genie Space for Data Product(s) {product_ids_str} is ready.",
                    link=mock_genie_space_url,
                    status="success"
                )
                logger.info(f"Completion notification created for user {user_email}.")
                # The context manager handles commit/rollback/close for db_session
        except Exception as e:
            logger.error(f"Failed to send Genie Space completion notification: {e}", exc_info=True)
            # No explicit rollback needed due to context manager

    def load_from_yaml(self, yaml_path: str) -> bool:
        """Load data products from YAML into the database via the repository."""
        try:
            with open(yaml_path) as file:
                data = yaml.safe_load(file)
            
            if not isinstance(data, list):
                 logger.error(f"YAML file {yaml_path} should contain a list of products.")
                 return False

            loaded_count = 0
            errors = 0
            for product_dict in data:
                if not isinstance(product_dict, dict):
                    logger.warning("Skipping non-dictionary item in YAML data.")
                    continue
                try:
                    product_api = DataProductApi(**product_dict)
                    existing = self.get_product(product_api.id)
                    if existing:
                        logger.warning(f"Product ID {product_api.id} exists, updating from YAML.")
                        self.update_product(product_api.id, product_api)
                    else:
                        # Correctly pass the dictionary to create_product
                        self.create_product(product_dict)
                    loaded_count += 1
                except (ValidationError, ValueError, SQLAlchemyError) as e: # Catch errors during processing/db ops
                    # This correctly uses product_dict.get() because product_dict IS a dict
                    logger.error(f"Error processing product from YAML (ID: {product_dict.get('id', 'N/A')}): {e}")
                    errors += 1

            logger.info(f"Processed {loaded_count} data products from {yaml_path}. Encountered {errors} processing errors.")
            return loaded_count > 0

        except FileNotFoundError:
            logger.warning(f"Data product YAML file not found at {yaml_path}. No products loaded.")
            return False
        except yaml.YAMLError as e:
            logger.error(f"Error parsing data product YAML file {yaml_path}: {e}")
            return False
        except Exception as e: # Catch any other unexpected error
            # Explicitly convert exception to string for logging
            error_msg = str(e)
            logger.error(f"Unexpected error during YAML load ({yaml_path}): {error_msg}", exc_info=True)
            return False

    def save_to_yaml(self, yaml_path: str) -> bool:
        """Save current data products from DB to a YAML file."""
        try:
            all_products_api = self.list_products(limit=10000)
            
            products_list = [p.dict(by_alias=True) for p in all_products_api]
            
            with open(yaml_path, 'w') as file:
                yaml.dump(products_list, file, default_flow_style=False, sort_keys=False)
            logger.info(f"Saved {len(products_list)} data products to {yaml_path}")
            return True
        except (SQLAlchemyError, ValidationError, ValueError) as e:
            logger.error(f"Error retrieving or processing data for saving to YAML: {e}")
            return False
        except Exception as e:
            logger.error(f"Error saving data products to YAML {yaml_path}: {e}")
            return False

    # --- Reinstate Helper methods for distinct values --- 
    # These now delegate to the repository which handles DB interaction.

    def get_distinct_owners(self) -> List[str]:
        """Get all distinct data product owners."""
        try:
            return self._repo.get_distinct_owners(db=self._db)
        except Exception as e:
            logger.error(f"Error getting distinct owners from repository: {e}", exc_info=True)
            # Depending on desired behavior, re-raise or return empty list
            # raise # Option 1: Let the route handler catch it
            return [] # Option 2: Return empty on error

    def get_distinct_domains(self) -> List[str]:
        """Get distinct 'domain' values from the 'info' JSON column."""
        # TODO: Add get_distinct_domains to repository if needed
        logger.warning("get_distinct_domains called - not implemented in repository yet.")
        return [] # Placeholder until implemented in repo

    def get_distinct_statuses(self) -> List[str]:
        """Get all distinct data product statuses from info and output ports."""
        try:
            return self._repo.get_distinct_statuses(db=self._db)
        except Exception as e:
            logger.error(f"Error getting distinct statuses from repository: {e}", exc_info=True)
            return []

    def get_distinct_product_types(self) -> List[str]:
        """Get all distinct data product types."""
        try:
            # Call the new repository method
            return self._repo.get_distinct_product_types(db=self._db)
        except Exception as e:
            logger.error(f"Error getting distinct product types from repository: {e}", exc_info=True)
            return []

    # --- Implementation of SearchableAsset --- 
    def get_search_index_items(self) -> List[SearchIndexItem]:
        """Fetches data products and maps them to SearchIndexItem format."""
        logger.info("Fetching data products for search indexing...")
        items = []
        try:
            # Fetch all products (adjust limit if needed, but potentially large)
            # Consider fetching only necessary fields if performance becomes an issue
            products_api = self.list_products(limit=10000) # Fetch Pydantic models
            
            for product in products_api:
                if not product.id or not product.info or not product.info.title:
                     logger.warning(f"Skipping product due to missing id or info.title: {product}")
                     continue
                     
                items.append(
                    SearchIndexItem(
                        id=f"product::{product.id}",
                        version=product.version, # Add version
                        product_type=product.productType.value if product.productType else None, # Add type
                        type="data-product",
                        title=product.info.title,
                        description=product.info.description or "",
                        link=f"/data-products/{product.id}",
                        tags=product.tags or []
                        # Add other fields like owner, status, domain if desired
                        # owner=product.info.owner,
                        # status=product.info.status,
                        # domain=product.info.domain
                    )
                )
            logger.info(f"Prepared {len(items)} data products for search index.")
            return items
        except Exception as e:
            logger.error(f"Error fetching or mapping data products for search: {e}", exc_info=True)
            return [] # Return empty list on error
