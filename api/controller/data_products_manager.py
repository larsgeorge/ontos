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
    GenieSpaceRequest
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

from api.common.logging import get_logger

logger = get_logger(__name__)

# Import necessary components for creating a session
from api.common.database import get_session_factory

# Import config to get data path - Removed get_settings as it's not needed for path
# from api.common.config import get_settings 
from pathlib import Path

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

    def update_product(self, product_id: str, product_data_dict: Dict[str, Any]) -> Optional[DataProductApi]:
        """Update an existing data product. Expects a dictionary for product_data_dict."""
        logger.debug(f"Manager attempting to update product ID {product_id} with dict data.")
        try:
            db_obj = self._repo.get(db=self._db, id=product_id)
            if not db_obj:
                logger.warning(f"Attempted to update non-existent product: {product_id}")
                return None

            # Prepare the dictionary for Pydantic validation
            update_payload = product_data_dict.copy()
            update_payload['id'] = product_id  # Ensure ID from path is used
            update_payload['updated_at'] = datetime.utcnow() # Set update timestamp
            
            # Preserve created_at from the existing DB object if it exists in the dict or db_obj
            if 'created_at' not in update_payload and hasattr(db_obj, 'created_at'):
                update_payload['created_at'] = db_obj.created_at
            elif 'created_at' not in update_payload:
                # Fallback if created_at is somehow missing everywhere, though unlikely for an update
                update_payload['created_at'] = db_obj.updated_at # Or some other sensible default

            # Validate the dictionary into the Pydantic model (DataProductUpdate or DataProductApi)
            try:
                # Assuming DataProductUpdate is an alias or same as DataProductApi for now
                # If DataProductUpdate is different, ensure it's imported and used here.
                product_update_model = DataProductApi(**update_payload) 
            except ValidationError as e:
                logger.error(f"Validation error for update data (ID: {product_id}): {e.errors()}")
                raise ValueError(f"Invalid data for product update: {e.errors()}") from e

            # Pass the validated Pydantic model to the repository's update method
            updated_db_obj = self._repo.update(db=self._db, db_obj=db_obj, obj_in=product_update_model)
            
            return DataProductApi.from_orm(updated_db_obj)
            
        except SQLAlchemyError as e:
            logger.error(f"Database error updating data product {product_id}: {e}")
            raise
        except ValueError as e: # Catch validation errors from above
            logger.error(f"Value error during product update for ID {product_id}: {e}")
            raise
        except ValidationError as e: # Catch from_orm errors
            logger.error(f"Validation error mapping DB object to API model post-update for ID {product_id}: {e}")
            raise ValueError(f"Internal data mapping error post-update for ID {product_id}: {e}")
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

    def load_initial_data(self, db: Session) -> bool:
        """Load data products from the default YAML file into the database if empty."""
        # Check if products already exist
        try:
            existing_products = self._repo.get_multi(db=db, limit=1)
            if existing_products:
                 logger.info("DataProductsManager: Data products table is not empty. Skipping initial data loading.")
                 return False # Indicate that loading was skipped
        except SQLAlchemyError as e:
             logger.error(f"DataProductsManager: Error checking for existing data products: {e}", exc_info=True)
             raise # Propagate error, startup might need to handle this

        # Construct the default YAML path relative to the project structure
        # settings = get_settings() # No longer needed for path
        # yaml_path = Path(settings.APP_DATA_DIR) / "data_products.yaml" # Incorrect
        
        # Corrected path construction relative to this file's location
        base_dir = Path(__file__).parent.parent # Navigate up from controller/ to api/
        yaml_path = base_dir / "data" / "data_products.yaml"
        
        logger.info(f"DataProductsManager: Attempting to load initial data from {yaml_path}...")

        try:
            if not yaml_path.is_file():
                 logger.warning(f"DataProductsManager: Data product YAML file not found at {yaml_path}. No products loaded.")
                 return False

            with yaml_path.open() as file:
                data = yaml.safe_load(file)
            
            if not isinstance(data, list):
                 logger.error(f"DataProductsManager: YAML file {yaml_path} should contain a list of products.")
                 return False

            loaded_count = 0
            errors = 0
            for product_dict in data:
                if not isinstance(product_dict, dict):
                    logger.warning("DataProductsManager: Skipping non-dictionary item in YAML data.")
                    continue
                try:
                    # Generate ID if missing
                    if not product_dict.get('id'):
                         product_dict['id'] = str(uuid.uuid4())
                         
                    # Set timestamps if missing
                    now = datetime.utcnow()
                    product_dict.setdefault('created_at', now)
                    product_dict.setdefault('updated_at', now)

                    # Validate data using the API model
                    product_api = DataProductApi(**product_dict)
                    
                    # Check if product exists using the current session 'db'
                    # We need a get method that uses the repo and the passed db session
                    # Let's assume get_product should accept the session
                    # NOTE: We need to modify get_product/update_product/create_product or the repo methods 
                    # to accept the 'db' session parameter. 
                    # For now, we will directly use the repo with the passed db session.
                    
                    existing_db = self._repo.get(db=db, id=product_api.id) # Use passed db session

                    if existing_db:
                        logger.warning(f"DataProductsManager: Product ID {product_api.id} exists, attempting update from YAML using current session.")
                        # We need an update method that uses the repo and the passed db session.
                        # Pass the validated API model 'product_api' to the repo's update.
                        self._repo.update(db=db, db_obj=existing_db, obj_in=product_api) # Use passed db session
                    else:
                        logger.info(f"DataProductsManager: Creating product ID {product_api.id} from YAML using current session.")
                        # Pass the validated API model 'product_api' to the repo's create.
                        self._repo.create(db=db, obj_in=product_api) # Use passed db session
                        
                    loaded_count += 1
                except (ValidationError, ValueError, SQLAlchemyError) as e: 
                    logger.error(f"DataProductsManager: Error processing product from YAML (ID: {product_dict.get('id', 'N/A')}): {e}")
                    db.rollback() # Rollback this specific product's transaction part
                    errors += 1
                except Exception as inner_e: # Catch unexpected errors per product
                     logger.error(f"DataProductsManager: Unexpected error processing product from YAML (ID: {product_dict.get('id', 'N/A')}): {inner_e}", exc_info=True)
                     db.rollback() # Rollback this specific product's transaction part
                     errors += 1


            if errors == 0 and loaded_count > 0:
                 db.commit() # Commit only if all products loaded successfully
                 logger.info(f"DataProductsManager: Successfully loaded and committed {loaded_count} data products from {yaml_path}.")
            elif loaded_count > 0 and errors > 0:
                 logger.warning(f"DataProductsManager: Processed {loaded_count + errors} products from {yaml_path}, but encountered {errors} errors. Changes for successful products were rolled back.")
                 # Rollback is handled per error, no final commit needed
            elif errors > 0:
                 logger.error(f"DataProductsManager: Encountered {errors} errors processing products from {yaml_path}. No products loaded.")
                 # Rollback is handled per error, no final commit needed
            else:
                 logger.info(f"DataProductsManager: No new data products found to load from {yaml_path}.")
                 # No commit needed if nothing was loaded

            return loaded_count > 0 and errors == 0 # Return True only if some were loaded without errors

        except FileNotFoundError: # Catching outside the loop
            logger.warning(f"DataProductsManager: Data product YAML file not found at {yaml_path}. No products loaded.")
            return False
        except yaml.YAMLError as e:
            logger.error(f"DataProductsManager: Error parsing data product YAML file {yaml_path}: {e}")
            db.rollback() # Rollback if YAML parsing failed
            return False
        except SQLAlchemyError as e: # Catch DB errors outside the loop (e.g., during initial check)
             logger.error(f"DataProductsManager: Database error during initial data load from {yaml_path}: {e}", exc_info=True)
             db.rollback()
             return False
        except Exception as e: # Catch any other unexpected error during file handling/setup
            error_msg = str(e)
            logger.error(f"DataProductsManager: Unexpected error during YAML load setup ({yaml_path}): {error_msg}", exc_info=True)
            db.rollback()
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
                        product_type=product.productType if product.productType else None, 
                        type="data-product", # Keep type for frontend icon/rendering
                        feature_id="data-products", # <-- Add this
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
