import logging
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
# Remove Session and WorkspaceClient imports if no longer needed directly
# from sqlalchemy.sdk import Session 
# from databricks.sdk import WorkspaceClient 

from src.controller.search_manager import SearchManager
# Remove direct manager imports as they are no longer needed here
# from src.routes.data_product_routes import get_data_products_manager
# from src.routes.business_glossary_routes import glossary_manager as business_glossary_manager_instance 
# from src.routes.data_contract_routes import contract_manager as data_contract_manager_instance 
# from src.controller.data_products_manager import DataProductsManager
# from src.controller.business_glossaries_manager import BusinessGlossariesManager
# from src.controller.data_contracts_manager import DataContractsManager

# Import the search interfaces
from src.common.search_interfaces import SearchableAsset, SearchIndexItem
# Import dependencies for db and ws_client (Not needed directly here anymore)
# from src.common.database import get_db
# from src.common.workspace_client import get_workspace_client_dependency
# Import Permission Checker class (not the non-existent getter)
from src.common.authorization import PermissionChecker # Keep PermissionChecker class import if needed elsewhere, but remove getter
# Import correct dependencies using Annotated types from dependencies.py
from src.common.dependencies import (
    CurrentUserDep, 
    AuthorizationManagerDep,
    SettingsManagerDep
)

# Configure logging
from src.common.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["search"])

# --- Manager Dependency ---
# Remove unused global variable
# _search_manager_instance: Optional[SearchManager] = None

async def get_search_manager(
    request: Request # Inject Request object
) -> SearchManager:
    """Dependency to retrieve the SearchManager singleton instance from app.state."""
    search_manager = getattr(request.app.state, 'search_manager', None)
    if search_manager is None:
        # This should not happen if startup was successful
        logger.critical("SearchManager instance not found in app.state!")
        raise HTTPException(status_code=500, detail="Search service is not available.")
    return search_manager

# --- Routes ---
@router.get("/search", response_model=List[SearchIndexItem])
async def search_items(
    search_term: str,
    # Reorder parameters: non-defaults first
    auth_manager: AuthorizationManagerDep,
    current_user: CurrentUserDep,
    settings_manager: SettingsManagerDep,
    manager: SearchManager = Depends(get_search_manager) 
) -> List[SearchIndexItem]:
    """Search across indexed items, filtered by user permissions."""
    if not search_term:
        raise HTTPException(status_code=400, detail="Query parameter (search_term) is required")
    try:
        # Determine team role override (applied impersonation) if any
        try:
            applied_override_id = settings_manager.get_applied_role_override_for_user(current_user.email)
        except Exception:
            applied_override_id = None
        # Map override id to role NAME because AuthorizationManager expects role name for override
        override_role_name = None
        if applied_override_id:
            try:
                role = settings_manager.get_app_role(applied_override_id)
                override_role_name = role.name if role else None
            except Exception:
                override_role_name = None
        # Pass auth_manager, current_user and override role name to the search method
        results = manager.search(search_term, auth_manager, current_user, team_role_override=override_role_name)
        return results
    except Exception as e:
        logger.exception(f"Error during search for query '{search_term}': {e}")
        raise HTTPException(status_code=500, detail="Search failed")

@router.post("/search/rebuild-index", status_code=202)
async def rebuild_search_index(
    manager: SearchManager = Depends(get_search_manager)
):
    """Triggers a rebuild of the search index."""
    try:
        # In a real app, this might be a background task
        manager.build_index()
        return {"message": "Search index rebuild initiated."}
    except Exception as e:
        logger.exception(f"Error during index rebuild: {e}")
        raise HTTPException(status_code=500, detail="Index rebuild failed")

# --- Register Function ---
# Removed unused function argument `app` as it's not needed for `register_routes`
def register_routes(app):
    app.include_router(router)
    logger.info("Search routes registered")
