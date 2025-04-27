import logging
from typing import List, Optional, Dict, Any, Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

# Import API models
from api.models.data_asset_reviews import (
    DataAssetReviewRequest as DataAssetReviewRequestApi,
    DataAssetReviewRequestCreate,
    DataAssetReviewRequestUpdateStatus,
    ReviewedAsset as ReviewedAssetApi,
    ReviewedAssetUpdate,
    AssetType
)

# Import Manager and other dependencies
from api.controller.data_asset_reviews_manager import DataAssetReviewManager
from api.controller.notifications_manager import NotificationsManager # Assuming manager is here
from api.common.database import get_db
from api.common.workspace_client import get_workspace_client_dependency
from databricks.sdk import WorkspaceClient

from api.common.logging import setup_logging, get_logger
from api.common.dependencies import (
    DBSessionDep, 
    # Define annotated types for WorkspaceClient and NotificationsManager if not already done
    # For now, assume they exist or need to be added to dependencies.py
    # Let's use placeholder names WorkspaceClientDep, NotificationsManagerDep
    # We need to define these properly in dependencies.py
    # ---> Import DataAssetReviewManagerDep <--- (Assuming it's added to dependencies.py)
    DataAssetReviewManagerDep,
    # Import the newly defined types
    NotificationsManagerDep,
    WorkspaceClientDep 
)
# Remove the old getter import
# from api.common.dependencies import get_notifications_manager 

# --- REMOVE Need to define these in dependencies.py --- #
# # Example placeholder definition (replace with actual implementation in dependencies.py)
# from api.common.manager_dependencies import get_notifications_manager
# from api.common.workspace_client import get_workspace_client
# from typing import Annotated
# NotificationsManagerDep = Annotated[NotificationsManager, Depends(get_notifications_manager)]
# WorkspaceClientDep = Annotated[WorkspaceClient, Depends(get_workspace_client)] # Assuming get_workspace_client exists
# --- End placeholder definitions --- #

# --- REMOVED Define DataAssetReviewManagerDep --- #

setup_logging(level=logging.INFO)
logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["data-asset-reviews"])

# --- Routes (using Annotated Types directly) --- #

@router.post("/data-asset-reviews", response_model=DataAssetReviewRequestApi, status_code=status.HTTP_201_CREATED)
def create_review_request(
    request_in: DataAssetReviewRequestCreate,
    # Inject manager directly using its Annotated type
    manager: DataAssetReviewManagerDep,
    db: DBSessionDep # Keep DB session if manager methods require it explicitly
):
    """Create a new data asset review request."""
    logger.info(f"Received request to create data asset review from {request_in.requester_email} for {request_in.reviewer_email}")
    try:
        # Pass db session if needed by the manager method
        created_request = manager.create_review_request(db=db, request_in=request_in)
        return created_request
    except ValueError as e:
        logger.warning(f"Value error creating review request: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error creating review request: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error creating review request.")

@router.get("/data-asset-reviews")
def list_review_requests(
    db: DBSessionDep,
    manager: DataAssetReviewManagerDep,
    skip: int = 0,
    limit: int = 100,
):
    """Retrieve a list of data asset review requests."""
    logger.info(f"Listing data asset review requests (skip={skip}, limit={limit})")
    try:
        requests = manager.list_review_requests(db=db, skip=skip, limit=limit)
        if not requests:
            return JSONResponse(content={"items": []})
        else:
            return requests
            
    except HTTPException as http_exc:
        logger.warning(f"HTTPException caught in list_review_requests: {http_exc.status_code} - {http_exc.detail}")
        raise http_exc
    except Exception as e:
        # Catch any other exception, log it clearly, and raise a standard 500
        logger.exception(f"Unexpected error in list_review_requests: {e}") # Use logger.exception to include traceback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Internal server error processing request: {e}"
        )

@router.get("/data-asset-reviews/{request_id}", response_model=DataAssetReviewRequestApi)
def get_review_request(
    request_id: str,
    manager: DataAssetReviewManagerDep,
    db: DBSessionDep
):
    """Get a specific data asset review request by its ID."""
    logger.info(f"Fetching data asset review request ID: {request_id}")
    try:
        request = manager.get_review_request(db=db, request_id=request_id)
        if request is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review request not found")
        return request
    except ValueError as e: # Catch mapping errors
         logger.error(f"Mapping error retrieving request {request_id}: {e}")
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal data error: {e}")
    except Exception as e:
        logger.exception(f"Error getting review request {request_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error getting review request.")

@router.put("/data-asset-reviews/{request_id}/status", response_model=DataAssetReviewRequestApi)
def update_review_request_status(
    request_id: str,
    status_update: DataAssetReviewRequestUpdateStatus,
    manager: DataAssetReviewManagerDep,
    db: DBSessionDep
):
    """Update the overall status of a data asset review request."""
    logger.info(f"Updating status for review request ID: {request_id} to {status_update.status}")
    try:
        updated_request = manager.update_review_request_status(db=db, request_id=request_id, status_update=status_update)
        if updated_request is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review request not found")
        return updated_request
    except ValueError as e:
        logger.warning(f"Value error updating status for request {request_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Error updating status for request {request_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error updating request status.")

@router.put("/data-asset-reviews/{request_id}/assets/{asset_id}/status", response_model=ReviewedAssetApi)
def update_reviewed_asset_status(
    request_id: str,
    asset_id: str,
    asset_update: ReviewedAssetUpdate,
    manager: DataAssetReviewManagerDep,
    db: DBSessionDep
):
    """Update the status and comments of a specific asset within a review request."""
    logger.info(f"Updating status for asset ID: {asset_id} in request {request_id} to {asset_update.status}")
    try:
        updated_asset = manager.update_reviewed_asset_status(db=db, request_id=request_id, asset_id=asset_id, asset_update=asset_update)
        if updated_asset is None:
            # Distinguish between request not found and asset not found in request
            # Manager method should handle fetching request if needed
            request_exists = manager.get_review_request(db=db, request_id=request_id)
            if not request_exists:
                 raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review request not found")
            else:
                 raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found within the specified review request")
                 
        return updated_asset
    except ValueError as e:
        logger.warning(f"Value error updating status for asset {asset_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Error updating status for asset {asset_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error updating asset status.")

@router.delete("/data-asset-reviews/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review_request(
    request_id: str,
    manager: DataAssetReviewManagerDep,
    db: DBSessionDep
):
    """Delete a data asset review request."""
    logger.info(f"Deleting review request ID: {request_id}")
    try:
        deleted = manager.delete_review_request(db=db, request_id=request_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review request not found")
        # Return No Content on success
        return
    except Exception as e:
        logger.exception(f"Error deleting review request {request_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error deleting review request.")

# --- Routes for Asset Content/Preview --- #

@router.get("/data-asset-reviews/{request_id}/assets/{asset_id}/definition")
async def get_asset_definition(
    request_id: str,
    asset_id: str,
    manager: DataAssetReviewManagerDep,
    db: DBSessionDep # Pass DB if needed to get asset info first
):
    """Get the definition (e.g., SQL) for a view or function asset."""
    logger.info(f"Getting definition for asset {asset_id} in request {request_id}")
    try:
        # Let the manager handle getting the asset info and definition
        definition = await manager.get_asset_definition(
            db=db, 
            request_id=request_id, 
            asset_id=asset_id
        )

        if definition is None:
             # Manager should raise appropriate exception or return None if handled here
             # This logic might be better inside the manager
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset definition not found, invalid type, or access denied.")
                 
        # Return as plain text
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(content=definition)
        
    except HTTPException as e:
        raise e # Re-raise specific HTTP exceptions
    except Exception as e:
        logger.exception(f"Error getting definition for asset {asset_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error getting asset definition.")

@router.get("/data-asset-reviews/{request_id}/assets/{asset_id}/preview")
async def get_table_preview(
    request_id: str,
    asset_id: str,
    db: DBSessionDep, 
    manager: DataAssetReviewManagerDep,
    limit: int = Query(25, ge=1, le=100, description="Number of rows to preview"),
):
    """Get a preview of data for a table asset."""
    logger.info(f"Getting preview for asset {asset_id} (table) in request {request_id} (limit={limit})")
    try:
        # Let manager handle fetching asset info and preview
        preview_data = await manager.get_table_preview(
            db=db, 
            request_id=request_id, 
            asset_id=asset_id, 
            limit=limit
        )

        if preview_data is None:
             # Manager should raise appropriate exception or return None if handled here
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table preview not available, invalid type, or access denied.")
             
        return preview_data # Returns dict {schema: [], data: []}
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Error getting preview for asset {asset_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error getting table preview.")

# --- Register Routes (if using a central registration pattern) --- #
def register_routes(app):
    """Register Data Asset Review routes with the FastAPI app."""
    app.include_router(router)
    logger.info("Data Asset Review routes registered") 