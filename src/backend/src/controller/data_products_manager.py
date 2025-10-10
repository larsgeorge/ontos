import asyncio
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

from src.models.data_products import (
    DataOutput,
    DataProduct as DataProductApi,
    DataProductCreate,
    DataProductStatus,
    DataProductType,
    DataSource,
    SchemaField,
    GenieSpaceRequest
)
from src.models.users import UserInfo

# Import the specific repository
from src.repositories.data_products_repository import data_product_repo

# Import Search Interfaces
from src.common.search_interfaces import SearchableAsset, SearchIndexItem
# Import the registry decorator
from src.common.search_registry import searchable_asset

# Import NotificationsManager (adjust path if necessary)
from src.controller.notifications_manager import NotificationsManager

# Import TagsManager and entity tag repository for tag integration
from src.controller.tags_manager import TagsManager
from src.repositories.tags_repository import entity_tag_repo

from src.common.logging import get_logger
logger = get_logger(__name__)

# Import necessary components for creating a session
from src.common.database import get_session_factory

# Import config to get data path - Removed get_settings as it's not needed for path
# from src.common.config import get_settings 
from pathlib import Path

# Inherit from SearchableAsset
@searchable_asset
class DataProductsManager(SearchableAsset):
    def __init__(self, db: Session, ws_client: Optional[WorkspaceClient] = None, notifications_manager: Optional[NotificationsManager] = None, tags_manager: Optional[TagsManager] = None):
        """
        Initializes the DataProductsManager.

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
             logger.warning("WorkspaceClient was not provided to DataProductsManager. SDK operations might fail.")
        if not self._notifications_manager:
             logger.warning("NotificationsManager was not provided to DataProductsManager. Notifications will not be sent.")
        if not self._tags_manager:
             logger.warning("TagsManager was not provided to DataProductsManager. Tag operations will not be available.")

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

            # Extract tags before creating the product (tags are handled separately)
            tags_data = product_data.get('tags', [])

            # Now pass the validated Pydantic model to the repository
            # The repository's create method expects the Pydantic model (DataProductCreate alias)
            created_db_obj = self._repo.create(db=self._db, obj_in=product_api_model)

            # Handle tag assignments if tags are provided and tags_manager is available
            if tags_data and self._tags_manager:
                try:
                    self._assign_tags_to_product(created_db_obj.id, tags_data)
                except Exception as e:
                    logger.error(f"Failed to assign tags to product {created_db_obj.id}: {e}")
                    # Note: We don't rollback the product creation, just log the error

            # Load and return the product with its tags
            return self._load_product_with_tags(created_db_obj)

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
                return self._load_product_with_tags(product_db)
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
            # Load each product with its tags
            products_with_tags = []
            for product_db in products_db:
                product_with_tags = self._load_product_with_tags(product_db)
                products_with_tags.append(product_with_tags)
            return products_with_tags
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

            # Extract tags before updating the product (tags are handled separately)
            tags_data = product_data_dict.get('tags', [])

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

            # Handle tag updates if tags are provided and tags_manager is available
            if tags_data is not None and self._tags_manager:  # Check explicitly for None since empty list is valid
                try:
                    # First, remove all existing tags for this product
                    existing_tags = self._entity_tag_repo.get_assigned_tags_for_entity(
                        db=self._db,
                        entity_id=product_id,
                        entity_type="data_product"
                    )
                    for existing_tag in existing_tags:
                        self._entity_tag_repo.remove_tag_from_entity(
                            db=self._db,
                            tag_id=existing_tag.tag_id,
                            entity_id=product_id,
                            entity_type="data_product"
                        )

                    # Then assign the new tags
                    if tags_data:  # Only assign if there are tags to assign
                        self._assign_tags_to_product(product_id, tags_data)

                except Exception as e:
                    logger.error(f"Failed to update tags for product {product_id}: {e}")
                    # Note: We don't rollback the product update, just log the error

            # Load and return the product with its tags
            return self._load_product_with_tags(updated_db_obj)
            
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
        from src.common.database import get_session_factory
        
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

    def _resolve_team_name_to_id(self, db: Session, team_name: str) -> Optional[str]:
        """Helper method to resolve team name to team UUID."""
        if not team_name:
            return None

        try:
            from src.repositories.teams_repository import team_repo
            team = team_repo.get_by_name(db, name=team_name)
            if team:
                logger.info(f"Successfully resolved team '{team_name}' to ID: {team.id}")
                return str(team.id)
            else:
                logger.warning(f"Team '{team_name}' not found")
                return None
        except Exception as e:
            logger.warning(f"Failed to resolve team '{team_name}': {e}")
            return None

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

                    # Resolve owner_team to owner_team_id if present
                    if 'info' in product_dict and isinstance(product_dict['info'], dict):
                        info_dict = product_dict['info']
                        if 'owner_team' in info_dict:
                            owner_team = info_dict.pop('owner_team')  # Remove owner_team
                            owner_team_id = self._resolve_team_name_to_id(db, owner_team)
                            if owner_team_id:
                                info_dict['owner_team_id'] = owner_team_id
                            else:
                                logger.warning(f"Could not resolve owner_team '{owner_team}' for product ID {product_dict.get('id')}. Product will be created without team ownership.")

                    # Pre-process tags: Convert tag_fqn format to AssignedTagCreate format
                    self._preprocess_tags_for_yaml_loading(product_dict)

                    # Extract and store all tags before model creation
                    tags_data = []
                    port_tags_data = {}

                    # Extract product-level tags
                    if 'tags' in product_dict:
                        tags_data = product_dict.pop('tags', [])

                    # Extract port-level tags
                    if 'inputPorts' in product_dict:
                        for i, port in enumerate(product_dict['inputPorts']):
                            if 'tags' in port:
                                port_tags_data[f"input_{i}"] = port.pop('tags', [])

                    if 'outputPorts' in product_dict:
                        for i, port in enumerate(product_dict['outputPorts']):
                            if 'tags' in port:
                                port_tags_data[f"output_{i}"] = port.pop('tags', [])

                    # Now create the API model with cleaned data (no tags)
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
                        updated_product = self._repo.update(db=db, db_obj=existing_db, obj_in=product_api) # Use passed db session
                        # Assign tags after update
                        if tags_data and self._tags_manager:
                            self._assign_tags_to_product(product_api.id, tags_data)
                    else:
                        logger.info(f"DataProductsManager: Creating product ID {product_api.id} from YAML using current session.")
                        # Pass the validated API model 'product_api' to the repo's create.
                        created_product = self._repo.create(db=db, obj_in=product_api) # Use passed db session
                        # Assign tags after creation
                        if tags_data and self._tags_manager:
                            self._assign_tags_to_product(product_api.id, tags_data)

                    loaded_count += 1
                except (ValidationError, ValueError, SQLAlchemyError) as e:
                    if isinstance(e, ValidationError):
                        logger.error(f"DataProductsManager: Validation error processing product from YAML (ID: {product_dict.get('id', 'N/A')}): {len(e.errors())} validation errors")
                        for i, error in enumerate(e.errors()):
                            logger.error(f"  Validation Error {i+1}: {error}")
                    else:
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
                     
                # Normalize tags as strings for SearchIndexItem
                tag_strings: List[str] = []
                try:
                    for t in (product.tags or []):
                        if isinstance(t, dict):
                            fqn = t.get('tag_fqn')
                            if fqn:
                                tag_strings.append(str(fqn))
                            elif t.get('tag_id'):
                                tag_strings.append(str(t.get('tag_id')))
                            else:
                                tag_strings.append(str(t))
                        else:
                            tag_strings.append(str(t))
                except Exception:
                    tag_strings = []

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
                        tags=tag_strings
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

    # --- Tag Integration Methods ---

    def _assign_tags_to_product(self, product_id: str, tags_data: List[Dict[str, Any]]) -> None:
        """Helper method to assign tags to a data product."""
        if not self._tags_manager:
            logger.warning("TagsManager not available, cannot assign tags")
            return

        for tag_data in tags_data:
            try:
                # Handle both tag_id and tag_fqn formats
                if isinstance(tag_data, dict):
                    tag_id = tag_data.get('tag_id')
                    tag_fqn = tag_data.get('tag_fqn')
                    assigned_value = tag_data.get('assigned_value')
                else:
                    # Legacy format - assume it's a tag name/fqn string
                    tag_fqn = str(tag_data)
                    tag_id = None
                    assigned_value = None

                # Use the tags manager to assign the tag
                if tag_id:
                    self._entity_tag_repo.add_tag_to_entity(
                        db=self._db,
                        tag_id=tag_id,
                        entity_id=product_id,
                        entity_type="data_product",
                        assigned_value=assigned_value,
                        assigned_by="system"  # Could be passed from user context
                    )
                elif tag_fqn:
                    # Resolve FQN to tag_id first
                    tag = self._tags_manager.get_tag_by_fqn(self._db, fqn=tag_fqn)
                    if tag:
                        self._entity_tag_repo.add_tag_to_entity(
                            db=self._db,
                            tag_id=tag.id,
                            entity_id=product_id,
                            entity_type="data_product",
                            assigned_value=assigned_value,
                            assigned_by="system"
                        )
                    else:
                        logger.warning(f"Tag with FQN '{tag_fqn}' not found, cannot assign to product {product_id}")

            except Exception as e:
                logger.error(f"Failed to assign tag {tag_data} to product {product_id}: {e}")

    def _load_product_with_tags(self, db_obj) -> DataProductApi:
        """Helper method to load a data product with its associated tags."""
        try:
            # Convert DB object to API model
            product_api = DataProductApi.from_orm(db_obj)

            # Load associated tags if tags_manager is available
            if self._tags_manager:
                try:
                    assigned_tags = self._entity_tag_repo.get_assigned_tags_for_entity(
                        db=self._db,
                        entity_id=db_obj.id,
                        entity_type="data_product"
                    )
                    # Convert to the expected format
                    product_api.tags = assigned_tags
                except Exception as e:
                    logger.error(f"Failed to load tags for product {db_obj.id}: {e}")
                    # Set empty tags list on error
                    product_api.tags = []
            else:
                product_api.tags = []

            return product_api

        except Exception as e:
            logger.error(f"Failed to load product with tags: {e}")
            # Fallback to basic conversion
            return DataProductApi.from_orm(db_obj)

    def assign_tag_to_product(self, product_id: str, tag_id: str, assigned_value: Optional[str] = None, assigned_by: str = "system") -> bool:
        """Public method to assign a tag to a data product."""
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
            logger.error(f"Failed to assign tag {tag_id} to product {product_id}: {e}")
            return False

    def remove_tag_from_product(self, product_id: str, tag_id: str) -> bool:
        """Public method to remove a tag from a data product."""
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
            logger.error(f"Failed to remove tag {tag_id} from product {product_id}: {e}")
            return False

    def get_product_tags(self, product_id: str) -> List[Dict[str, Any]]:
        """Public method to get all tags assigned to a data product."""
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
            logger.error(f"Failed to get tags for product {product_id}: {e}")
            return []

    def _preprocess_tags_for_yaml_loading(self, product_dict: Dict[str, Any]) -> None:
        """
        Convert tag_fqn format in YAML to AssignedTagCreate format for DataProductCreate validation.

        Converts:
            tags:
              - tag_fqn: "default/source"
              - tag_fqn: "default/pos"

        To:
            tags:
              - tag_fqn: "default/source"
              - tag_fqn: "default/pos"

        This ensures the YAML structure is compatible with AssignedTagCreate models.
        """
        def process_tags_in_dict(obj: Dict[str, Any]):
            """Recursively process tags in nested dictionaries."""
            if 'tags' in obj and isinstance(obj['tags'], list):
                new_tags = []
                for tag_item in obj['tags']:
                    if isinstance(tag_item, dict) and 'tag_fqn' in tag_item:
                        # Ensure assigned_value is present for AssignedTagCreate
                        if 'assigned_value' not in tag_item:
                            tag_item['assigned_value'] = None
                        new_tags.append(tag_item)
                    elif isinstance(tag_item, str):
                        # Convert string to tag_fqn format with assigned_value
                        new_tags.append({"tag_fqn": tag_item, "assigned_value": None})
                    else:
                        # Assume it's already in correct format but ensure assigned_value
                        if isinstance(tag_item, dict) and 'assigned_value' not in tag_item:
                            tag_item['assigned_value'] = None
                        new_tags.append(tag_item)
                obj['tags'] = new_tags

            # Recursively process nested dictionaries
            for key, value in obj.items():
                if isinstance(value, dict):
                    process_tags_in_dict(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            process_tags_in_dict(item)

        # Process the main product dictionary
        process_tags_in_dict(product_dict)

