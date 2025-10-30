from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from databricks.sdk.errors import PermissionDenied, DatabricksError

from src.common.dependencies import WorkspaceManagerDep
from src.controller.workspace_manager import WorkspaceManager
from src.models.workspace import WorkspaceAsset
from src.common.authorization import PermissionChecker
from src.common.features import FeatureAccessLevel

from src.common.logging import get_logger
logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["workspace"])

@router.get("/workspace/assets/search", response_model=List[WorkspaceAsset])
async def search_workspace_assets(
    asset_type: str = Query(..., description="Type of asset to search (e.g., 'table', 'notebook', 'job')"),
    search_term: Optional[str] = Query(None, description="Search term to filter asset names/identifiers"),
    limit: int = Query(25, description="Maximum number of results to return", ge=1, le=100),
    manager: WorkspaceManager = Depends(WorkspaceManagerDep),
    _: bool = Depends(PermissionChecker('catalog-commander', FeatureAccessLevel.READ_ONLY))
):
    """
    Search for Databricks workspace assets based on type and search term.
    
    Supports searching for:
    - tables: Unity Catalog tables across available catalogs/schemas
    - notebooks: Notebooks in /Users, /Repos, and /Shared paths
    - jobs: Databricks jobs
    - views, functions, models: Placeholder (not yet implemented)
    """
    logger.info(f"Searching for workspace assets: type={asset_type}, term={search_term}, limit={limit}")

    try:
        # Delegate to manager
        results = manager.search_workspace_assets(
            asset_type=asset_type,
            search_term=search_term,
            limit=limit
        )
        return results
        
    except ValueError as e:
        # Invalid input (e.g., unsupported asset type, workspace not configured)
        logger.warning(f"Invalid request for workspace asset search: {e}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except PermissionDenied as e:
        # Databricks permissions issue
        logger.error(f"Permission denied during workspace asset search: {e}")
        raise HTTPException(
            status_code=403,
            detail="Permission denied to access requested Databricks resources."
        )
        
    except DatabricksError as e:
        # Other Databricks SDK errors
        logger.error(f"Databricks error during workspace asset search: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error communicating with Databricks workspace."
        )
        
    except Exception as e:
        # Unexpected errors
        logger.exception(f"Unexpected error searching workspace assets: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while searching workspace assets."
        )

def register_routes(app):
    """Register routes with the FastAPI app."""
    app.include_router(router)
    logger.info("Workspace routes registered") 