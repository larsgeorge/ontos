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
import os
from openai import OpenAI

# Import API models
from api.models.data_asset_reviews import (
    DataAssetReviewRequest as DataAssetReviewRequestApi,
    DataAssetReviewRequestCreate,
    DataAssetReviewRequestUpdateStatus,
    ReviewedAsset as ReviewedAssetApi,
    ReviewedAssetUpdate,
    ReviewRequestStatus, ReviewedAssetStatus, AssetType,
    AssetAnalysisRequest, AssetAnalysisResponse # Added LLM models
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

from api.common.logging import get_logger
from api.common.config import Settings, get_settings # Added Settings and get_settings

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
    
    def get_reviewed_asset(self, request_id: str, asset_id: str) -> Optional[ReviewedAssetApi]:
        """Gets a specific reviewed asset by its ID and its parent request ID."""
        try:
            asset_db = self._repo.get_asset(db=self._db, request_id=request_id, asset_id=asset_id)
            if asset_db:
                return ReviewedAssetApi.from_orm(asset_db)
            return None
        except SQLAlchemyError as e:
            logger.error(f"Database error getting reviewed asset {asset_id} for request {request_id}: {e}")
            raise
        except ValidationError as e:
            logger.error(f"Validation error mapping DB object for asset {asset_id}: {e}")
            raise ValueError(f"Internal data mapping error for asset {asset_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting reviewed asset {asset_id}: {e}")
            raise
    
    def analyze_asset_content(self, request_id: str, asset_id: str, asset_content: str, asset_type: AssetType) -> Optional[AssetAnalysisResponse]:
        """Analyzes asset content using an LLM via Databricks Serving Endpoint."""
        settings: Settings = get_settings()
        if not settings.SERVING_ENDPOINT:
            logger.warning("SERVING_ENDPOINT is not configured. Cannot perform LLM analysis.")
            return None
        
        databricks_host = settings.DATABRICKS_HOST
        # Ensure host does not have https:// prefix for OpenAI base_url constructor
        if databricks_host.startswith("https://"):
            # Slice off "https://"
            formatted_host = databricks_host[8:]
        else:
            formatted_host = databricks_host

        # DATABRICKS_TOKEN can be set in .env for local dev or injected in Databricks App environment
        databricks_token = os.environ.get('DATABRICKS_TOKEN')
        if not databricks_token:
            logger.warning("DATABRICKS_TOKEN environment variable not found. LLM analysis might fail if not authenticated.")
            # Attempt to use ws_client for token if available and if it makes sense for OpenAI client
            # This is a fallback, direct env var is preferred for OpenAI client.
            if self._ws_client and hasattr(self._ws_client.config, 'token') and self._ws_client.config.token:
                databricks_token = self._ws_client.config.token
                logger.info("Using token from WorkspaceClient configuration for LLM call.")
            else:
                 logger.warning("No fallback token available from WorkspaceClient configuration.")

        try:
            client = OpenAI(
                api_key=databricks_token, 
                base_url=f"https://{formatted_host}/serving-endpoints" 
            )

            system_prompt = "You are a Data Steward tasked with reviewing metadata, data, and SQL/Python code to check if any sensitive information is used. These include PII data, like names, addresses, age, social security numbers, credit card numbers etc. Look at the provided text and identify insecure coding or sensitive data and return a summary."
            
            logger.info(f"Sending content of asset {asset_id} (type: {asset_type.value}) to LLM endpoint: {settings.SERVING_ENDPOINT} at {formatted_host}")

            # Assuming openai.chat.completions.create is synchronous based on typical usage
            response = client.chat.completions.create(
                model=settings.SERVING_ENDPOINT, # Model name is the serving endpoint name
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": asset_content}
                ],
                # Add other parameters like temperature, max_tokens if needed
            )
            
            analysis_summary = response.choices[0].message.content
            if not analysis_summary:
                logger.warning(f"LLM analysis for asset {asset_id} returned empty summary.")
                return None

            logger.info(f"LLM analysis successful for asset {asset_id}.")
            return AssetAnalysisResponse(
                request_id=request_id,
                asset_id=asset_id,
                analysis_summary=analysis_summary.strip(),
                model_used=settings.SERVING_ENDPOINT,
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Error during LLM analysis for asset {asset_id} (request {request_id}): {e}", exc_info=True)
            return None

    # Add methods for getting asset content (text/data preview) using ws_client
    async def get_asset_definition(self, asset_fqn: str, asset_type: AssetType) -> Optional[str]:
        """Fetches the definition (e.g., SQL) for a view or function."""
        # Hardcoded data for demo purposes
        sample_view_sql = '''-- Sample View: main.marketing.campaign_view
SELECT
    c.campaign_id,
    c.campaign_name,
    SUM(s.amount) AS total_sales_amount,
    COUNT(DISTINCT s.customer_id) AS unique_customers
FROM
    main.sales.orders s
JOIN
    main.marketing.campaigns c ON s.campaign_id = c.campaign_id
WHERE
    s.order_date BETWEEN c.start_date AND c.end_date
GROUP BY
    c.campaign_id,
    c.campaign_name
ORDER BY
    total_sales_amount DESC;'''

        sample_function_python = '''# Sample Function: dev.staging.udf_process_customer
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType
import re

# Example of a potentially sensitive pattern (email)
EMAIL_PATTERN = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

def _contains_email(text_column):
    """
    Checks if the text column contains an email address.
    WARNING: This is a simplified example for demonstration.
    Real PII detection requires more robust methods.
    """
    if text_column and re.search(EMAIL_PATTERN, text_column):
        return "Contains Email"
    return "No Email Detected"

contains_email_udf = udf(_contains_email, StringType())

# Example usage (not part of the function definition itself, but for context):
# df = spark.createDataFrame([("test@example.com",1), ("no_email_here",2)], ["text_col", "id"])
# df_with_flag = df.withColumn("email_check", contains_email_udf(df["text_col"]))
# df_with_flag.show()'''

        if not self._ws_client:
            logger.warning(f"Cannot fetch definition for {asset_fqn}: WorkspaceClient not available.")
            if asset_type == AssetType.VIEW:
                logger.info(f"Returning hardcoded SQL for view {asset_fqn} as fallback.")
                return sample_view_sql
            elif asset_type == AssetType.FUNCTION:
                logger.info(f"Returning hardcoded Python for function {asset_fqn} as fallback.")
                return sample_function_python
            return None
            
        if asset_type not in [AssetType.VIEW, AssetType.FUNCTION]:
            logger.info(f"Definition fetch only supported for VIEW/FUNCTION, not {asset_type} ({asset_fqn})")
            return None
            
        try:
            if asset_type == AssetType.VIEW:
                 table_info = self._ws_client.tables.get(full_name_arg=asset_fqn)
                 return table_info.view_definition
            elif asset_type == AssetType.FUNCTION:
                 func_info = self._ws_client.functions.get(name=asset_fqn)
                 return func_info.definition
        except AttributeError as e:
            logger.error(f"AttributeError fetching definition for {asset_fqn} (type: {asset_type}): {e}. Likely SDK object mismatch (e.g., CachedTables).")
            if asset_type == AssetType.VIEW:
                logger.info(f"Returning hardcoded SQL for view {asset_fqn} due to AttributeError.")
                return sample_view_sql
            elif asset_type == AssetType.FUNCTION:
                logger.info(f"Returning hardcoded Python for function {asset_fqn} due to AttributeError.")
                return sample_function_python
        except NotFound:
            logger.warning(f"Asset {asset_fqn} not found when fetching definition.")
            # Fallback for demo even if asset not found by SDK
            if asset_type == AssetType.VIEW:
                return sample_view_sql
            elif asset_type == AssetType.FUNCTION:
                return sample_function_python
            return None
        except PermissionDenied:
            logger.warning(f"Permission denied when fetching definition for {asset_fqn}.")
            # Fallback for demo even if permission denied
            if asset_type == AssetType.VIEW:
                return sample_view_sql
            elif asset_type == AssetType.FUNCTION:
                return sample_function_python
            return None
        except Exception as e:
            logger.error(f"Error fetching definition for {asset_fqn}: {e}", exc_info=True)
            # General fallback
            if asset_type == AssetType.VIEW:
                return sample_view_sql
            elif asset_type == AssetType.FUNCTION:
                return sample_function_python
            return None
        return None # Should not be reached if logic is correct
        
    async def get_table_preview(self, table_fqn: str, limit: int = 25) -> Optional[Dict[str, Any]]:
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

    def load_initial_data(self, db: Session) -> bool:
        """Loads data asset reviews from a YAML file if the table is empty."""
        # Check if the table is empty first using the passed session
        try:
            if not self._repo.is_empty(db=db): # Use passed db session
                logger.info("Data Asset Reviews table is not empty. Skipping initial data loading.")
                return False
        except SQLAlchemyError as e:
             logger.error(f"DataAssetReviewManager: Error checking for existing reviews: {e}", exc_info=True)
             raise # Propagate error

        # Construct the default YAML path relative to the project structure
        base_dir = Path(__file__).parent.parent # Navigate up from controller/ to api/
        yaml_path = base_dir / "data" / "data_asset_reviews.yaml" # Standard location

        logger.info(f"Data Asset Reviews table is empty. Attempting to load from {yaml_path}...")
        try:
            if not yaml_path.is_file():
                 logger.warning(f"Data asset review YAML file not found at {yaml_path}. No reviews loaded.")
                 return False
                 
            with open(yaml_path, 'r') as file:
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
                    # Ensure timestamps are set if missing
                    now = datetime.utcnow()
                    request_dict.setdefault('created_at', now)
                    request_dict.setdefault('updated_at', now)
                    # Ensure assets have timestamps if missing
                    if 'assets' in request_dict and isinstance(request_dict['assets'], list):
                        for asset in request_dict['assets']:
                            if isinstance(asset, dict):
                                asset.setdefault('updated_at', now)

                    request_api = DataAssetReviewRequestApi(**request_dict)
                    # Use the repository's create_with_assets method with the passed db session
                    self._repo.create_with_assets(db=db, obj_in=request_api) # Use passed db session
                    loaded_count += 1
                except (ValidationError, ValueError, SQLAlchemyError) as e:
                    logger.error(f"Error processing review request from YAML (ID: {request_dict.get('id', 'N/A')}): {e}")
                    db.rollback() # Rollback this specific item
                    errors += 1
                except Exception as e:
                     logger.error(f"Unexpected error processing review request from YAML (ID: {request_dict.get('id', 'N/A')}): {e}", exc_info=True)
                     db.rollback() # Rollback this specific item
                     errors += 1

            if errors == 0 and loaded_count > 0:
                 db.commit() # Commit only if all loaded successfully
                 logger.info(f"Successfully loaded and committed {loaded_count} data asset reviews from {yaml_path}.")
            elif loaded_count > 0 and errors > 0:
                 logger.warning(f"Processed {loaded_count + errors} reviews from {yaml_path}, but encountered {errors} errors. Changes for successful reviews were rolled back.")
            elif errors > 0:
                 logger.error(f"Encountered {errors} errors processing reviews from {yaml_path}. No reviews loaded.")
            else:
                 logger.info(f"No new data asset reviews found to load from {yaml_path}.")

            return loaded_count > 0 and errors == 0 # Return True only if loaded without errors

        except FileNotFoundError:
            logger.warning(f"Data asset review YAML file not found at {yaml_path}. No reviews loaded.")
            return False
        except yaml.YAMLError as e:
            logger.error(f"Error parsing data asset review YAML file {yaml_path}: {e}")
            db.rollback() # Rollback if YAML parsing failed
            return False
        except SQLAlchemyError as e: # Catch DB errors outside the loop (e.g., during initial check)
             logger.error(f"Database error during initial review data load from {yaml_path}: {e}", exc_info=True)
             db.rollback()
             return False
        except Exception as e:
            logger.error(f"Unexpected error loading data asset reviews from YAML {yaml_path}: {e}", exc_info=True)
            db.rollback() # Rollback on other errors
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
                        feature_id="data-asset-reviews",
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