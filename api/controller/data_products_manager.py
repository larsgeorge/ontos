import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

import yaml
from pydantic import ValidationError, parse_obj_as
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
)

# Import the specific repository
from api.repositories.data_products_repository import data_product_repo

# Import Search Interfaces
from api.common.search_interfaces import SearchableAsset, SearchIndexItem
# Import the registry decorator
from api.common.search_registry import searchable_asset

from api.common.logging import setup_logging, get_logger
setup_logging(level=logging.INFO)
logger = get_logger(__name__)

# Inherit from SearchableAsset
@searchable_asset
class DataProductsManager(SearchableAsset):
    def __init__(self, db: Session, ws_client: Optional[WorkspaceClient] = None):
        """
        Initializes the DataProductsManager.

        Args:
            db: SQLAlchemy Session for database operations.
            ws_client: Optional Databricks WorkspaceClient for SDK operations.
        """
        self._db = db
        self._ws_client = ws_client
        self._repo = data_product_repo
        if not self._ws_client:
             logger.warning("WorkspaceClient was not provided to DataProductsManager. SDK operations might fail.")

    def get_types(self) -> List[str]:
        """Get all available data product types"""
        return [t.value for t in DataProductType]

    def get_statuses(self) -> List[str]:
        """Get all available data product statuses"""
        return [s.value for s in DataProductStatus]

    def create_product(self, product_data: DataProductApi) -> DataProductApi:
        """Create a new data product using the repository."""
        try:
            if not product_data.id:
                 product_data.id = str(uuid.uuid4())
                 
            now = datetime.utcnow()
            product_data.created_at = now
            product_data.updated_at = now

            created_db_obj = self._repo.create(db=self._db, obj_in=product_data)
            
            return DataProductApi.from_orm(created_db_obj)
            
        except SQLAlchemyError as e:
            logger.error(f"Database error creating data product: {e}")
            raise
        except ValidationError as e:
            logger.error(f"Validation error mapping DB object to API model: {e}")
            raise ValueError(f"Internal data mapping error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating data product: {e}")
            raise

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
                         self.create_product(product_api)
                    loaded_count += 1
                except (ValidationError, ValueError, SQLAlchemyError) as e:
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
        except Exception as e:
            logger.error(f"Unexpected error loading data products from YAML {yaml_path}: {e}")
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
        # Note: get_distinct_domains was missing in the original, but the logic
        # is the same as owners/archetypes. We need a repo method for it.
        # Assuming we add get_distinct_domains to the repo similar to others:
        # return self._repo.get_distinct_domains(db=self._db)
        # For now, let's implement it using the generic helper if needed, or
        # it needs to be added to the repo first.
        logger.warning("get_distinct_domains called, but repository method not implemented yet.")
        # Example using generic helper (if we were to expose it or call internal)
        # return self._repo.get_distinct_json_values(self._db, self._repo.model.info, ['domain'])
        return [] # Placeholder

    def get_distinct_archetypes(self) -> List[str]:
         """Get all distinct data product archetypes."""
         try:
             return self._repo.get_distinct_archetypes(db=self._db)
         except Exception as e:
             logger.error(f"Error getting distinct archetypes from repository: {e}", exc_info=True)
             return []

    def get_distinct_statuses(self) -> List[str]:
        """Get all distinct data product statuses from info and output ports."""
        try:
            return self._repo.get_distinct_statuses(db=self._db)
        except Exception as e:
            logger.error(f"Error getting distinct statuses from repository: {e}", exc_info=True)
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
