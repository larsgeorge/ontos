from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound, PermissionDenied

from api.common.workspace_client import get_workspace_client_dependency # If available
from api.common.authorization import PermissionChecker
from api.common.features import FeatureAccessLevel
from api.common.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


class WorkspaceAsset(BaseModel):
    type: str = Field(..., description="Type of the asset (e.g., 'table', 'notebook', 'job')")
    identifier: str = Field(..., description="Unique identifier for the asset")
    name: str = Field(..., description="Display name of the asset")
    # Add other optional fields as needed, e.g., path, url
    path: Optional[str] = None
    url: Optional[str] = None

# Example simplified endpoint - needs refinement for actual SDK calls and error handling
@router.get("/assets/search", response_model=List[WorkspaceAsset])
async def search_workspace_assets(
    request: Request,
    asset_type: str = Query(..., description="Type of asset to search (e.g., 'table', 'notebook', 'job')"),
    search_term: Optional[str] = Query(None, description="Search term to filter asset names/identifiers"),
    limit: int = Query(25, description="Maximum number of results to return", ge=1, le=100),
    # Add dependencies for workspace client and permissions
    # ws_client: WorkspaceClient = Depends(get_workspace_client_dependency),
    # _: bool = Depends(PermissionChecker(feature_id='*', level=FeatureAccessLevel.READ_ONLY)) # Check appropriate feature/level
):
    """Search for Databricks workspace assets based on type and search term."""
    logger.info(f"Searching for workspace assets: type={asset_type}, term={search_term}, limit={limit}")

    # --- Get Workspace Client from App State --- 
    ws_client = getattr(request.app.state, 'workspace_client', None)
    if not ws_client or not isinstance(ws_client, WorkspaceClient):
        logger.error("WorkspaceClient not found or invalid in app state.")
        raise HTTPException(status_code=500, detail="Workspace connection not configured.")

    results: List[WorkspaceAsset] = []
    try:
        # --- Implement SDK calls based on asset_type --- 
        # This section requires detailed implementation for each type
        # Example for tables (needs refinement for catalog/schema, name pattern):
        if asset_type.lower() == 'table':
            # TODO: Determine how to get catalog/schema from user input or defaults
            # For now, just listing tables matching name pattern across known catalogs/schemas?
            # This part is complex and needs a proper strategy.
            logger.warning("Table search implementation is currently a placeholder.")
            # Example: Placeholder structure
            # tables = ws_client.tables.list(catalog_name='main', schema_name='default', name_pattern=f'%{search_term}%')
            # for table in tables:
            #     results.append(WorkspaceAsset(type='table', identifier=table.full_name, name=table.name))
            # Add dummy data for now
            if search_term and 'sales' in search_term.lower():
                 results.append(WorkspaceAsset(type='table', identifier='main.data.raw_sales', name='raw_sales'))
                 results.append(WorkspaceAsset(type='table', identifier='main.data.prepared_sales', name='prepared_sales'))
            elif search_term and 'customer' in search_term.lower():
                 results.append(WorkspaceAsset(type='table', identifier='main.gold.dim_customer', name='dim_customer'))

        elif asset_type.lower() == 'notebook':
            logger.warning("Notebook search implementation is currently a placeholder.")
            # Example: Requires listing workspace objects with path filtering
            # objects = ws_client.workspace.list(path='/Users/...') # Need path prefix?
            # for obj in objects:
            #    if obj.object_type == 'NOTEBOOK' and (not search_term or search_term.lower() in obj.path.lower()):
            #       results.append(WorkspaceAsset(type='notebook', identifier=obj.path, name=obj.path.split('/')[-1]))
            if search_term and 'etl' in search_term.lower():
                results.append(WorkspaceAsset(type='notebook', identifier='/Repos/user@org.com/project/notebooks/etl_pipeline', name='etl_pipeline.py'))

        elif asset_type.lower() == 'job':
            logger.warning("Job search implementation is currently a placeholder.")
            # jobs = ws_client.jobs.list(name_contains=search_term, limit=limit)
            # for job in jobs:
            #     results.append(WorkspaceAsset(type='job', identifier=str(job.job_id), name=job.settings.name))
            if search_term and 'daily' in search_term.lower():
                results.append(WorkspaceAsset(type='job', identifier='12345', name='daily_sales_job'))
                results.append(WorkspaceAsset(type='job', identifier='67890', name='daily_inventory_update'))

        # TODO: Implement other asset types (view, function, model, dashboard)
        else:
            logger.warning(f"Asset type '{asset_type}' search not implemented yet.")
            # Return empty list or raise error?
            # raise HTTPException(status_code=400, detail=f"Searching for asset type '{asset_type}' is not supported.")

        # Limit results (if SDK call didn't already)
        return results[:limit]

    except PermissionDenied:
        logger.error(f"Permission denied during workspace asset search (type: {asset_type}, term: {search_term}).")
        raise HTTPException(status_code=403, detail="Permission denied to access requested Databricks resources.")
    except Exception as e:
        logger.error(f"Error searching workspace assets (type: {asset_type}, term: {search_term}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred while searching workspace assets: {e!s}")

def register_routes(app):
    """Register routes with the FastAPI app."""
    app.include_router(router)
    logger.info("Workspace routes registered") 