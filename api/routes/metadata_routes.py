import logging
from typing import List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import PermissionDenied

from api.controller.metadata_manager import MetadataManager
from api.models.metadata import MetastoreTableInfo
from api.common.workspace_client import get_workspace_client_dependency

from api.common.logging import get_logger

logger = get_logger(__name__)

# Define router with /api/metadata prefix
router = APIRouter(prefix="/api", tags=["metadata"])

# --- Manager Dependency --- 
_metadata_manager_instance: Optional[MetadataManager] = None

async def get_metadata_manager(
    ws_client: WorkspaceClient = Depends(get_workspace_client_dependency(timeout=60))
) -> MetadataManager:
    """Dependency to get or create the MetadataManager instance with injected client."""
    global _metadata_manager_instance
    if _metadata_manager_instance is None:
        logger.info("Initializing MetadataManager instance.")
        _metadata_manager_instance = MetadataManager(ws_client=ws_client)
    # Check if the client needs to be updated (e.g., if timeout changed, though less likely here)
    # Use the correct attribute name 'ws_client' (no underscore)
    elif not _metadata_manager_instance.ws_client and ws_client:
         logger.warning("Updating ws_client on existing MetadataManager instance.")
         _metadata_manager_instance.ws_client = ws_client
        
    return _metadata_manager_instance

# --- Routes --- 

@router.get("/metadata/tables", response_model=List[MetastoreTableInfo])
async def list_metastore_tables_route(
    manager: MetadataManager = Depends(get_metadata_manager)
):
    """List tables from the Databricks metastore accessible by the workspace client."""
    try:
        logger.info("Request received for GET /api/metadata/tables")
        tables = manager.list_metastore_tables()
        logger.info(f"DEBUG: list_metastore_tables_route returning: {type(tables)}, {tables=}")
        logger.info(f"Returning {len(tables)} metastore tables.")
        return tables
    except PermissionDenied as e:
        logger.error(f"Permission denied while listing metastore tables: {e}")
        raise HTTPException(status_code=403, detail="Permission denied accessing Databricks Metastore.")
    except Exception as e:
        error_msg = f"Error listing metastore tables: {e!s}"
        logger.exception(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/metadata/tables/search", response_model=List[MetastoreTableInfo])
async def search_metastore_tables_route(
    query: str, # Query parameter from request URL
    limit: int = 50, # Optional limit, default 50
    manager: MetadataManager = Depends(get_metadata_manager)
):
    """Searches metastore tables by full name based on the query string."""
    try:
        logger.info(f"Request received for GET /api/metadata/tables/search with query='{query}', limit={limit}")
        tables = manager.search_metastore_tables(query=query, limit=limit)
        logger.info(f"Returning {len(tables)} tables matching search.")
        return tables
    except Exception as e:
        error_msg = f"Error searching metastore tables for query '{query}': {e!s}"
        logger.exception(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/metadata/tables/initial", response_model=List[MetastoreTableInfo])
async def get_initial_metastore_tables_route(
    limit: int = 20, # Optional limit, default 20
    manager: MetadataManager = Depends(get_metadata_manager)
):
    """Gets an initial list of metastore tables (first N)."""
    try:
        logger.info(f"Request received for GET /api/metadata/tables/initial with limit={limit}")
        tables = manager.get_initial_metastore_tables(limit=limit)
        logger.info(f"Returning {len(tables)} initial tables.")
        return tables
    except Exception as e:
        error_msg = f"Error getting initial metastore tables: {e!s}"
        logger.exception(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/metadata/schemas/{schema_name}") # Response model can be Dict[str, Any] or just Any
async def get_json_schema_route(
    schema_name: str,
    manager: MetadataManager = Depends(get_metadata_manager)
) -> Any:
    """Retrieves a specific JSON schema file from the /schemas directory."""
    try:
        logger.info(f"Request received for GET /api/metadata/schemas/{schema_name}")
        schema_data = manager.get_schema(schema_name)
        return schema_data
    except FileNotFoundError as e:
        logger.warning(f"Schema not found request: {schema_name}")
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.error(f"Invalid JSON in schema request: {schema_name}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        error_msg = f"Error retrieving schema '{schema_name}': {e!s}"
        logger.exception(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

# Add other metadata routes here later (e.g., /catalogs)

# --- Register Function --- 
def register_routes(app):
    """Register metadata routes with the FastAPI app."""
    app.include_router(router)
    logger.info("Metadata routes registered with prefix /api/metadata") 