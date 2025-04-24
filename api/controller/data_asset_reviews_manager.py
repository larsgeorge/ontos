import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from pydantic import ValidationError, parse_obj_as
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

# Import Databricks SDK components
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import TableInfo, FunctionInfo, SchemaInfo, CatalogInfo, TableType
from databricks.sdk.errors import NotFound, PermissionDenied, DatabricksError
import yaml # Import yaml
from pathlib import Path # Import Path

# Import API models
from api.models.data_asset_reviews import (
    DataAssetReviewRequest as DataAssetReviewRequestApi,
    DataAssetReviewRequestCreate,
    DataAssetReviewRequestUpdateStatus,
    ReviewedAsset as ReviewedAssetApi,
    ReviewedAssetUpdate,
    ReviewRequestStatus, ReviewedAssetStatus, AssetType
)
# Import Repository
from api.repositories.data_asset_reviews_repository import data_asset_review_repo

# Import Notification Manager (Assuming NotificationsManager is in this path)
from api.controller.notifications_manager import NotificationsManager
# Import correct enum from notifications model
from api.models.notifications import Notification, NotificationType

# Import Search Interfaces
from api.common.search_interfaces import SearchableAsset, SearchIndexItem
# Import the registry decorator
from api.common.search_registry import searchable_asset

from api.common.logging import setup_logging, get_logger
setup_logging(level=logging.INFO)
logger = get_logger(__name__)

@searchable_asset # Register this manager with the search system
class DataAssetReviewManager(SearchableAsset): # Inherit from SearchableAsset
    def __init__(self, db: Session, ws_client: WorkspaceClient, notifications_manager: NotificationsManager):
        """
        Initializes the DataAssetReviewManager.

        Args:
            db: SQLAlchemy Session for database operations.
            ws_client: Databricks WorkspaceClient for SDK operations.
            notifications_manager: Manager for creating notifications.
        """
        self._db = db
        self._ws_client = ws_client
        self._repo = data_asset_review_repo
        self._notifications_manager = notifications_manager
        if not self._ws_client:
             logger.warning("WorkspaceClient was not provided to DataAssetReviewManager. SDK operations will fail.")

    def _determine_asset_type(self, fqn: str) -> AssetType:
        """Tries to determine the asset type using the Databricks SDK."""
        if not self._ws_client:
            logger.warning(f"Cannot determine asset type for {fqn}: WorkspaceClient not available.")
            # Default or raise error? For now, default to TABLE as a fallback.
            return AssetType.TABLE

        parts = fqn.split('.')
        if len(parts) != 3:
            logger.warning(f"Invalid FQN format for asset type determination: {fqn}. Defaulting to TABLE.")
            return AssetType.TABLE
        
        catalog_name, schema_name, object_name = parts

        try:
            # Try fetching as Table first (most common)
            try:
                table_info = self._ws_client.tables.get(full_name_arg=fqn)
                if table_info.table_type == TableType.VIEW or table_info.table_type == TableType.MATERIALIZED_VIEW:
                    return AssetType.VIEW
                else:
                    return AssetType.TABLE
            except DatabricksError as e:
                # If not found or permission denied as table, try function
                if "NOT_FOUND" not in str(e) and "PERMISSION_DENIED" not in str(e):
                    raise # Re-raise unexpected errors
            
            # Try fetching as Function
            try:
                self._ws_client.functions.get(name=fqn)
                return AssetType.FUNCTION
            except DatabricksError as e:
                if "NOT_FOUND" not in str(e) and "PERMISSION_DENIED" not in str(e):
                     raise

            # Try fetching as Model (assuming registered models have FQN like catalog.schema.model_name)
            try:
                # Note: This might need adjustment based on how models are registered and accessed.
                # The Python SDK might have a dedicated function for models.
                # For now, assuming a hypothetical `get_model` exists or it falls under tables/functions.
                # If a dedicated model client exists, use that.
                # Example: self._ws_client.models.get(name=fqn)
                # If it doesn't exist, we might need more info or skip model detection.
                pass # Placeholder for model check
            except DatabricksError as e:
                 if "NOT_FOUND" not in str(e) and "PERMISSION_DENIED" not in str(e):
                    raise
            
            logger.warning(f"Could not determine asset type for FQN: {fqn} using SDK checks. Defaulting to TABLE.")
            return AssetType.TABLE # Default if not found as table or function

        except PermissionDenied:
             logger.warning(f"Permission denied while trying to determine asset type for {fqn}. Defaulting to TABLE.")
             return AssetType.TABLE
        except Exception as e:
            logger.error(f"Unexpected SDK error determining asset type for {fqn}: {e}. Defaulting to TABLE.", exc_info=True)
            return AssetType.TABLE

    def create_review_request(self, request_data: DataAssetReviewRequestCreate) -> DataAssetReviewRequestApi:
        """Creates a new data asset review request."""
        try:
            request_id = str(uuid.uuid4())
            assets_to_review: List[ReviewedAssetApi] = []
            processed_fqns = set() # Track processed FQNs to avoid duplicates

            for fqn in request_data.asset_fqns:
                if fqn in processed_fqns:
                    logger.warning(f"Duplicate FQN '{fqn}' in request, skipping.")
                    continue
                
                asset_type = self._determine_asset_type(fqn)
                assets_to_review.append(
                    ReviewedAssetApi(
                        id=str(uuid.uuid4()),
                        asset_fqn=fqn,
                        asset_type=asset_type,
                        status=ReviewedAssetStatus.PENDING, # Start as pending
                        updated_at=datetime.utcnow()
                    )
                )
                processed_fqns.add(fqn)
            
            if not assets_to_review:
                 raise ValueError("No valid or unique assets provided for review.")
                 
            # Prepare the full API model for the repository
            full_request = DataAssetReviewRequestApi(
                id=request_id,
                requester_email=request_data.requester_email,
                reviewer_email=request_data.reviewer_email,
                status=ReviewRequestStatus.QUEUED,
                notes=request_data.notes,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                assets=assets_to_review
            )

            # Use the repository to create the request and its assets in DB
            created_db_obj = self._repo.create_with_assets(db=self._db, obj_in=full_request)

            # Convert DB object back to API model for response
            created_api_obj = DataAssetReviewRequestApi.from_orm(created_db_obj)

            # --- Create Notification --- #
            try:
                 notification = Notification(
                     id=str(uuid.uuid4()),
                     user_email=created_api_obj.reviewer_email, # Notify the reviewer
                     # Using Notification model fields (assuming 'title' or 'message')
                     title="New Data Asset Review Request", # Use title
                     description=f"Review request ({created_api_obj.id}) assigned to you by {created_api_obj.requester_email}.", # Use description for details
                     type=NotificationType.INFO, # Use NotificationType enum
                     link=f"/data-asset-reviews/{created_api_obj.id}" # Link to the review details page
                 )
                 self._notifications_manager.create_notification(notification)
                 logger.info(f"Notification created for reviewer {created_api_obj.reviewer_email} for request {created_api_obj.id}")
            except Exception as notify_err:
                 # Log error but don't fail the request creation
                 logger.error(f"Failed to create notification for review request {created_api_obj.id}: {notify_err}", exc_info=True)

            return created_api_obj

        except SQLAlchemyError as e:
            logger.error(f"Database error creating review request: {e}")
            raise
        except ValidationError as e:
            logger.error(f"Validation error creating review request: {e}")
            raise ValueError(f"Invalid data for review request: {e}")
        except ValueError as e:
            logger.error(f"Value error creating review request: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating review request: {e}")
            raise

    def get_review_request(self, request_id: str) -> Optional[DataAssetReviewRequestApi]:
        """Gets a review request by its ID."""
        try:
            request_db = self._repo.get(db=self._db, id=request_id)
            if request_db:
                return DataAssetReviewRequestApi.from_orm(request_db)
            return None
        except SQLAlchemyError as e:
            logger.error(f"Database error getting review request {request_id}: {e}")
            raise
        except ValidationError as e:
            logger.error(f"Validation error mapping DB object for request {request_id}: {e}")
            raise ValueError(f"Internal data mapping error for request {request_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting review request {request_id}: {e}")
            raise

    def list_review_requests(self, skip: int = 0, limit: int = 100) -> List[DataAssetReviewRequestApi]:
        """Lists all review requests."""
        try:
            requests_db = self._repo.get_multi(db=self._db, skip=skip, limit=limit)
            # Use parse_obj_as for lists
            return parse_obj_as(List[DataAssetReviewRequestApi], requests_db)
        except SQLAlchemyError as e:
            logger.error(f"Database error listing review requests: {e}")
            raise
        except ValidationError as e:
            logger.error(f"Validation error mapping list of DB objects for review requests: {e}")
            raise ValueError(f"Internal data mapping error during list: {e}")
        except Exception as e:
            logger.error(f"Unexpected error listing review requests: {e}")
            raise

    def update_review_request_status(self, request_id: str, update_data: DataAssetReviewRequestUpdateStatus) -> Optional[DataAssetReviewRequestApi]:
        """Updates the overall status of a review request."""
        try:
            db_obj = self._repo.get(db=self._db, id=request_id)
            if not db_obj:
                logger.warning(f"Attempted to update status for non-existent review request: {request_id}")
                return None
            
            updated_db_obj = self._repo.update_request_status(db=self._db, db_obj=db_obj, status=update_data.status, notes=update_data.notes)
            
            # --- Add Notification for Requester on final status --- #
            final_statuses = [ReviewRequestStatus.APPROVED, ReviewRequestStatus.NEEDS_REVIEW, ReviewRequestStatus.DENIED]
            if updated_db_obj.status in final_statuses:
                try:
                     notification_message = f"Data asset review request ({updated_db_obj.id}) status updated to {updated_db_obj.status} by {updated_db_obj.reviewer_email}."
                     # Map review status to notification type
                     notification_type = NotificationType.INFO if updated_db_obj.status == ReviewRequestStatus.APPROVED else NotificationType.WARNING

                     notification = Notification(
                         id=str(uuid.uuid4()),
                         user_email=updated_db_obj.requester_email, # Notify the requester
                         title=f"Review Request {updated_db_obj.status.value.capitalize()}",
                         description=notification_message,
                         type=notification_type, # Use NotificationType enum
                         link=f"/data-asset-reviews/{updated_db_obj.id}"
                     )
                     self._notifications_manager.create_notification(notification)
                     logger.info(f"Notification created for requester {updated_db_obj.requester_email} for request {updated_db_obj.id} status update.")
                except Exception as notify_err:
                    logger.error(f"Failed to create status update notification for request {updated_db_obj.id}: {notify_err}", exc_info=True)
            # --- End Notification --- #
            
            return DataAssetReviewRequestApi.from_orm(updated_db_obj)
        except SQLAlchemyError as e:
             logger.error(f"Database error updating status for request {request_id}: {e}")
             raise
        except ValidationError as e:
             logger.error(f"Validation error mapping updated DB object for request {request_id}: {e}")
             raise ValueError(f"Internal mapping error after update {request_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error updating status for request {request_id}: {e}")
            raise

    def update_reviewed_asset_status(self, request_id: str, asset_id: str, update_data: ReviewedAssetUpdate) -> Optional[ReviewedAssetApi]:
        """Updates the status and comments of a specific asset within a review."""
        try:
            db_asset_obj = self._repo.get_asset(db=self._db, request_id=request_id, asset_id=asset_id)
            if not db_asset_obj:
                logger.warning(f"Attempted to update non-existent asset {asset_id} in request {request_id}")
                return None
            
            updated_db_asset_obj = self._repo.update_asset_status(db=self._db, db_asset_obj=db_asset_obj, status=update_data.status, comments=update_data.comments)
            
            # TODO: Check if all assets are reviewed and potentially update overall request status?
            
            return ReviewedAssetApi.from_orm(updated_db_asset_obj)
        except SQLAlchemyError as e:
             logger.error(f"Database error updating asset {asset_id} status in request {request_id}: {e}")
             raise
        except ValidationError as e:
             logger.error(f"Validation error mapping updated DB asset {asset_id}: {e}")
             raise ValueError(f"Internal mapping error after asset update {asset_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error updating asset {asset_id} status: {e}")
            raise

    def delete_review_request(self, request_id: str) -> bool:
        """Deletes a review request and its associated assets."""
        try:
            deleted_obj = self._repo.remove(db=self._db, id=request_id)
            return deleted_obj is not None
        except SQLAlchemyError as e:
            logger.error(f"Database error deleting review request {request_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting review request {request_id}: {e}")
            raise
    
    # Add methods for getting asset content (text/data preview) using ws_client
    def get_asset_definition(self, asset_fqn: str, asset_type: AssetType) -> Optional[str]:
        """Fetches the definition (e.g., SQL) for a view or function."""
        if not self._ws_client:
            logger.warning(f"Cannot fetch definition for {asset_fqn}: WorkspaceClient not available.")
            return None
        if asset_type not in [AssetType.VIEW, AssetType.FUNCTION]:
            logger.info(f"Definition fetch only supported for VIEW/FUNCTION, not {asset_type} ({asset_fqn})")
            return None
            
        try:
            if asset_type == AssetType.VIEW:
                 # Assuming view definition is part of TableInfo for views
                 table_info = self._ws_client.tables.get(full_name_arg=asset_fqn)
                 return table_info.view_definition
            elif asset_type == AssetType.FUNCTION:
                 func_info = self._ws_client.functions.get(name=asset_fqn)
                 return func_info.definition
        except NotFound:
            logger.warning(f"Asset {asset_fqn} not found when fetching definition.")
            return None
        except PermissionDenied:
            logger.warning(f"Permission denied when fetching definition for {asset_fqn}.")
            return None
        except Exception as e:
            logger.error(f"Error fetching definition for {asset_fqn}: {e}", exc_info=True)
            return None
        return None
        
    def get_table_preview(self, table_fqn: str, limit: int = 25) -> Optional[Dict[str, Any]]:
        """Fetches a preview of data from a table."""
        if not self._ws_client:
            logger.warning(f"Cannot fetch preview for {table_fqn}: WorkspaceClient not available.")
            return None
            
        try:
             # Use ws_client.tables.read - Note: This might require specific permissions
             # and connection setup if running outside Databricks runtime.
             # The exact method might vary based on SDK version and context.
             # This is a conceptual example.
             # Example using a hypothetical direct read or via execute_statement
             # data = self._ws_client.tables.read(name=table_fqn, max_rows=limit)
             # return data.to_dict() # Or format as needed
             
             # --- Attempting preview via sql.execute --- #
            try:
                table_info = self._ws_client.tables.get(full_name_arg=table_fqn)
                schema = table_info.columns
                formatted_schema = [{"name": col.name, "type": col.type_text, "nullable": col.nullable} for col in schema]
                
                # Try executing a SELECT query
                # Note: This requires ws_client to be configured with appropriate
                # credentials and potentially a host/warehouse for SQL execution.
                # It might fail if only configured for workspace APIs.
                result = self._ws_client.sql.execute(
                    statement=f"SELECT * FROM {table_fqn} LIMIT {limit}",
                    # warehouse_id="YOUR_WAREHOUSE_ID" # Usually required
                )
                
                # Assuming result.rows gives a list of rows (actual structure might vary)
                data = result.rows if result and hasattr(result, 'rows') else []
                
                # Get total rows (may not be accurate from LIMIT query)
                total_rows = table_info.properties.get("numRows", 0) if table_info.properties else 0
                
                logger.info(f"Successfully fetched preview for {table_fqn} via sql.execute.")
                return {"schema": formatted_schema, "data": data, "total_rows": total_rows}

            except DatabricksError as sql_error:
                 # Specific handling if sql.execute fails (e.g., permissions, config)
                 logger.warning(f"sql.execute failed for {table_fqn}: {sql_error}. Falling back to schema-only.")
                 # Fallback: Return schema only if data fetch fails
                 if 'table_info' in locals(): # Ensure table_info was fetched before error
                      schema = table_info.columns
                      formatted_schema = [{"name": col.name, "type": col.type_text, "nullable": col.nullable} for col in schema]
                      total_rows = table_info.properties.get("numRows", 0) if table_info.properties else 0
                      return {"schema": formatted_schema, "data": [], "total_rows": total_rows}
                 else:
                     raise sql_error # Re-raise if we couldn't even get schema
            except Exception as exec_err:
                 # Catch other potential errors during execution or data processing
                 logger.error(f"Unexpected error during sql.execute or processing for {table_fqn}: {exec_err}", exc_info=True)
                 # Fallback as above
                 if 'table_info' in locals():
                      schema = table_info.columns
                      formatted_schema = [{"name": col.name, "type": col.type_text, "nullable": col.nullable} for col in schema]
                      total_rows = table_info.properties.get("numRows", 0) if table_info.properties else 0
                      return {"schema": formatted_schema, "data": [], "total_rows": total_rows}
                 else:
                    logger.error(f"Could not get schema info for {table_fqn} before execution error.")
                    return None # Return None if schema couldn't be fetched either
            # --- End of sql.execute attempt --- #

        except NotFound:
            logger.warning(f"Table {table_fqn} not found when fetching preview.")
            return None
        except PermissionDenied:
            logger.warning(f"Permission denied when fetching preview for {table_fqn}.")
            return None
        except Exception as e:
            logger.error(f"Error fetching preview for {table_fqn}: {e}", exc_info=True)
            return None
        
    # TODO: Add methods for running automated checks (similar to Compliance)
    # This would involve defining check types, potentially creating/running Databricks jobs
    # and updating the asset status based on results. 

    def load_from_yaml(self, yaml_path: str) -> bool:
        """Loads data asset reviews from a YAML file if the table is empty."""
        # Check if the table is empty first
        if not self._repo.is_empty(db=self._db):
            logger.info("Data Asset Reviews table is not empty. Skipping demo data loading.")
            return False

        logger.info(f"Data Asset Reviews table is empty. Attempting to load from {yaml_path}...")
        try:
            yaml_file = Path(yaml_path)
            if not yaml_file.exists():
                 logger.warning(f"Data asset review YAML file not found at {yaml_path}. No reviews loaded.")
                 return False
                 
            with open(yaml_file, 'r') as file:
                data = yaml.safe_load(file)

            if not isinstance(data, list):
                logger.error(f"YAML file {yaml_path} should contain a list of review requests.")
                return False

            loaded_count = 0
            errors = 0
            for request_dict in data:
                if not isinstance(request_dict, dict):
                    logger.warning("Skipping non-dictionary item in YAML data.")
                    continue
                try:
                    # Parse using the API model for validation
                    request_api = DataAssetReviewRequestApi(**request_dict)
                    # Use the repository's create_with_assets method
                    self._repo.create_with_assets(db=self._db, obj_in=request_api)
                    loaded_count += 1
                except (ValidationError, ValueError, SQLAlchemyError) as e:
                    logger.error(f"Error processing review request from YAML (ID: {request_dict.get('id', 'N/A')}): {e}")
                    errors += 1
                except Exception as e:
                     logger.error(f"Unexpected error processing review request from YAML (ID: {request_dict.get('id', 'N/A')}): {e}", exc_info=True)
                     errors += 1

            logger.info(f"Processed {loaded_count} data asset reviews from {yaml_path}. Encountered {errors} processing errors.")
            return loaded_count > 0

        except yaml.YAMLError as e:
            logger.error(f"Error parsing data asset review YAML file {yaml_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error loading data asset reviews from YAML {yaml_path}: {e}", exc_info=True)
            return False

    # --- Implementation of SearchableAsset ---
    def get_search_index_items(self) -> List[SearchIndexItem]:
        """Fetches data asset review requests and maps them to SearchIndexItem format."""
        logger.info("Fetching data asset review requests for search indexing...")
        items = []
        try:
            # Fetch all review requests (adjust limit if needed)
            reviews_api = self.list_review_requests(limit=10000) # Fetch Pydantic models

            for review in reviews_api:
                if not review.id:
                    logger.warning(f"Skipping review due to missing id: {review}")
                    continue

                # Create a descriptive title and potentially tags
                title = f"Review Request by {review.requester_email} for {review.reviewer_email}"
                if review.assets:
                    title += f" ({len(review.assets)} assets)"

                tags = [review.status.value] # Start with the overall status
                tags.append(f"reviewer:{review.reviewer_email}")
                tags.append(f"requester:{review.requester_email}")
                if review.assets:
                    tags.extend([asset.status.value for asset in review.assets]) # Add individual asset statuses
                    tags.extend([asset.asset_fqn for asset in review.assets]) # Add asset FQNs as tags
                    tags.extend([asset.asset_type.value for asset in review.assets]) # Add asset types

                items.append(
                    SearchIndexItem(
                        id=f"review::{review.id}",
                        type="data-asset-review",
                        title=title,
                        description=review.notes or f"Review request {review.id}",
                        link=f"/data-asset-reviews/{review.id}",
                        tags=list(set(tags)) # Remove duplicate tags
                    )
                )
            logger.info(f"Prepared {len(items)} data asset reviews for search index.")
            return items
        except Exception as e:
            logger.error(f"Error fetching or mapping data asset reviews for search: {e}", exc_info=True)
            return [] # Return empty list on error 