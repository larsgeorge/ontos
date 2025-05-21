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
    AssetType,
    AssetAnalysisRequest,
    AssetAnalysisResponse
)

# Import Manager and other dependencies
from api.controller.data_asset_reviews_manager import DataAssetReviewManager
from api.controller.notifications_manager import NotificationsManager # Assuming manager is here
from api.common.database import get_db
from api.common.workspace_client import get_workspace_client_dependency
from databricks.sdk import WorkspaceClient

from api.common.logging import get_logger
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

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["data-asset-reviews"])

# --- Routes (using Annotated Types directly) --- #

@router.post("/data-asset-reviews", response_model=DataAssetReviewRequestApi, status_code=status.HTTP_201_CREATED)
def create_review_request(
    request_data: DataAssetReviewRequestCreate,
    # Inject manager directly using its Annotated type
    manager: DataAssetReviewManagerDep,
):
    """Create a new data asset review request."""
    logger.info(f"Received request to create data asset review from {request_data.requester_email} for {request_data.reviewer_email}")
    try:
        # Pass db session if needed by the manager method
        created_request = manager.create_review_request(request_data=request_data)
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
        requests = manager.list_review_requests(skip=skip, limit=limit)
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
        request = manager.get_review_request(request_id=request_id)
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
):
    """Update the overall status of a data asset review request."""
    logger.info(f"Updating status for review request ID: {request_id} to {status_update.status}")
    try:
        updated_request = manager.update_review_request_status(request_id=request_id, status_update=status_update)
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
):
    """Update the status and comments of a specific asset within a review request."""
    logger.info(f"Updating status for asset ID: {asset_id} in request {request_id} to {asset_update.status}")
    try:
        updated_asset = manager.update_reviewed_asset_status(request_id=request_id, asset_id=asset_id, asset_update=asset_update)
        if updated_asset is None:
            # Distinguish between request not found and asset not found in request
            # Manager method should handle fetching request if needed
            request_exists = manager.get_review_request(request_id=request_id)
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
):
    """Delete a data asset review request."""
    logger.info(f"Deleting review request ID: {request_id}")
    try:
        deleted = manager.delete_review_request(request_id=request_id)
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
    # db: DBSessionDep # No longer needed here
):
    """Get the definition (e.g., SQL) for a view or function asset."""
    logger.info(f"Getting definition for asset {asset_id} in request {request_id}")
    try:
        reviewed_asset = manager.get_reviewed_asset(request_id=request_id, asset_id=asset_id)
        if not reviewed_asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reviewed asset not found")

        if reviewed_asset.asset_type not in [AssetType.VIEW, AssetType.FUNCTION, AssetType.NOTEBOOK]:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Asset definition can only be fetched for VIEW, FUNCTION, or NOTEBOOK types, not {reviewed_asset.asset_type.value}")

        definition = await manager.get_asset_definition(
            asset_fqn=reviewed_asset.asset_fqn,
            asset_type=reviewed_asset.asset_type
        )

        if definition is None:
             # This might indicate asset not found by ws_client or permission issue, handled by manager logging
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset definition not found by the workspace client, or access denied.")
                 
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
    # db: DBSessionDep, # No longer needed here
    manager: DataAssetReviewManagerDep,
    limit: int = Query(25, ge=1, le=100, description="Number of rows to preview"),
):
    """Get a preview of data for a table asset."""
    logger.info(f"Getting preview for asset {asset_id} (table) in request {request_id} (limit={limit})")
    try:
        reviewed_asset = manager.get_reviewed_asset(request_id=request_id, asset_id=asset_id)
        if not reviewed_asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reviewed asset not found")

        if reviewed_asset.asset_type != AssetType.TABLE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Table preview can only be fetched for TABLE types, not {reviewed_asset.asset_type.value}")

        preview_data = await manager.get_table_preview(
            table_fqn=reviewed_asset.asset_fqn, 
            limit=limit
        )

        if preview_data is None:
             # This might indicate asset not found by ws_client or permission issue, handled by manager logging
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table preview not available, or access denied by the workspace client.")
             
        return preview_data
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Error getting preview for asset {asset_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error getting table preview.")

@router.post("/data-asset-reviews/{request_id}/assets/{asset_id}/analyze", response_model=AssetAnalysisResponse)
async def analyze_asset_with_llm(
    request_id: str,
    asset_id: str,
    manager: DataAssetReviewManagerDep,
):
    """Triggers LLM analysis for a specific asset's content."""
    logger.info(f"Received request to analyze asset {asset_id} in request {request_id} with LLM.")

    try:
        # 1. Fetch the reviewed asset to get its FQN and type
        # get_reviewed_asset is synchronous, so it can be called directly.
        reviewed_asset_api = manager.get_reviewed_asset(request_id=request_id, asset_id=asset_id)
        if not reviewed_asset_api:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reviewed asset not found")

        # 2. Fetch the asset's definition (content) - this is an async call
        asset_content = await manager.get_asset_definition(
            asset_fqn=reviewed_asset_api.asset_fqn,
            asset_type=reviewed_asset_api.asset_type
        )

        if asset_content is None:
            # Consider if asset_type is TABLE or MODEL, for which definition might be None
            # but we might want to send schema or other metadata. For now, only code.
            if reviewed_asset_api.asset_type not in [AssetType.VIEW, AssetType.FUNCTION, AssetType.NOTEBOOK]:
                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"LLM content analysis currently only supports VIEW, FUNCTION, or NOTEBOOK types, not {reviewed_asset_api.asset_type.value}. Content could not be retrieved.") 
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset content not found or not available for analysis.")

        # 3. Call the manager's analysis method (which is synchronous)
        # To call a synchronous method from an async route, FastAPI handles it by running it in a thread pool.
        analysis_result = manager.analyze_asset_content(
            request_id=request_id,
            asset_id=asset_id,
            asset_content=asset_content,
            asset_type=reviewed_asset_api.asset_type
        )

        if not analysis_result:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="LLM analysis failed or returned no result. Check server logs.")

        return analysis_result

    except HTTPException as http_exc:
        logger.error(f"HTTPException during LLM analysis for asset {asset_id}: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error during LLM analysis for asset {asset_id} in request {request_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")

# --- Register Routes (if using a central registration pattern) --- #
def register_routes(app):
    """Register Data Asset Review routes with the FastAPI app."""
    app.include_router(router)
    logger.info("Data Asset Review routes registered") 