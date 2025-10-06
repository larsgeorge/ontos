from databricks.sdk import WorkspaceClient
from fastapi import APIRouter, Depends, HTTPException

from src.common.workspace_client import get_workspace_client
from src.controller.catalog_commander_manager import CatalogCommanderManager
# Import permission checker and feature level
from src.common.authorization import PermissionChecker
from src.common.features import FeatureAccessLevel

# Configure logging
from src.common.logging import get_logger
logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["catalog-commander"])

# Define the feature ID for permission checks
CATALOG_COMMANDER_FEATURE_ID = 'catalog-commander'

# Modify dependency injector to return manager (no auth check needed here)
def get_catalog_manager(client: WorkspaceClient = Depends(get_workspace_client)) -> CatalogCommanderManager:
    """Get a configured catalog commander manager instance.
    
    Args:
        client: Databricks workspace client (injected by FastAPI)
        
    Returns:
        Configured catalog commander manager instance
    """
    return CatalogCommanderManager(client)

# --- Read-Only Routes (Require READ_ONLY or higher) ---

@router.get('/catalogs', dependencies=[Depends(PermissionChecker(CATALOG_COMMANDER_FEATURE_ID, FeatureAccessLevel.READ_ONLY))])
async def list_catalogs(catalog_manager: CatalogCommanderManager = Depends(get_catalog_manager)):
    """List all catalogs in the Databricks workspace."""
    try:
        logger.info("Starting to fetch catalogs")
        catalogs = catalog_manager.list_catalogs()
        logger.info(f"Successfully fetched {len(catalogs)} catalogs")
        return catalogs
    except Exception as e:
        error_msg = f"Failed to fetch catalogs: {e!s}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get('/catalogs/{catalog_name}/schemas', dependencies=[Depends(PermissionChecker(CATALOG_COMMANDER_FEATURE_ID, FeatureAccessLevel.READ_ONLY))])
async def list_schemas(
    catalog_name: str,
    catalog_manager: CatalogCommanderManager = Depends(get_catalog_manager)
):
    """List all schemas in a catalog."""
    try:
        logger.info(f"Fetching schemas for catalog: {catalog_name}")
        schemas = catalog_manager.list_schemas(catalog_name)
        logger.info(f"Successfully fetched {len(schemas)} schemas for catalog {catalog_name}")
        return schemas
    except Exception as e:
        error_msg = f"Failed to fetch schemas for catalog {catalog_name}: {e!s}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get('/catalogs/{catalog_name}/schemas/{schema_name}/tables', dependencies=[Depends(PermissionChecker(CATALOG_COMMANDER_FEATURE_ID, FeatureAccessLevel.READ_ONLY))])
async def list_tables(
    catalog_name: str,
    schema_name: str,
    catalog_manager: CatalogCommanderManager = Depends(get_catalog_manager)
):
    """List all tables in a schema."""
    try:
        logger.info(f"Fetching tables for schema: {catalog_name}.{schema_name}")
        tables = catalog_manager.list_tables(catalog_name, schema_name)
        logger.info(f"Successfully fetched {len(tables)} tables for schema {catalog_name}.{schema_name}")
        return tables
    except Exception as e:
        error_msg = f"Failed to fetch tables for schema {catalog_name}.{schema_name}: {e!s}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get('/catalogs/{catalog_name}/schemas/{schema_name}/views', dependencies=[Depends(PermissionChecker(CATALOG_COMMANDER_FEATURE_ID, FeatureAccessLevel.READ_ONLY))])
async def list_views(
    catalog_name: str,
    schema_name: str,
    catalog_manager: CatalogCommanderManager = Depends(get_catalog_manager)
):
    """List all views in a schema."""
    try:
        logger.info(f"Fetching views for schema: {catalog_name}.{schema_name}")
        views = catalog_manager.list_views(catalog_name, schema_name)
        logger.info(f"Successfully fetched {len(views)} views for schema {catalog_name}.{schema_name}")
        return views
    except Exception as e:
        error_msg = f"Failed to fetch views for schema {catalog_name}.{schema_name}: {e!s}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get('/catalogs/{catalog_name}/schemas/{schema_name}/functions', dependencies=[Depends(PermissionChecker(CATALOG_COMMANDER_FEATURE_ID, FeatureAccessLevel.READ_ONLY))])
async def list_functions(
    catalog_name: str,
    schema_name: str,
    catalog_manager: CatalogCommanderManager = Depends(get_catalog_manager)
):
    """List all functions in a schema."""
    try:
        logger.info(f"Fetching functions for schema: {catalog_name}.{schema_name}")
        functions = catalog_manager.list_functions(catalog_name, schema_name)
        logger.info(f"Successfully fetched {len(functions)} functions for schema {catalog_name}.{schema_name}")
        return functions
    except Exception as e:
        error_msg = f"Failed to fetch functions for schema {catalog_name}.{schema_name}: {e!s}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get('/catalogs/dataset/{dataset_path:path}', dependencies=[Depends(PermissionChecker(CATALOG_COMMANDER_FEATURE_ID, FeatureAccessLevel.READ_ONLY))])
async def get_dataset(
    dataset_path: str,
    catalog_manager: CatalogCommanderManager = Depends(get_catalog_manager)
):
    """Get dataset content and schema."""
    try:
        logger.info(f"Fetching dataset: {dataset_path}")
        dataset = catalog_manager.get_dataset(dataset_path)
        logger.info(f"Successfully fetched dataset {dataset_path}")
        return dataset
    except Exception as e:
        error_msg = f"Failed to fetch dataset {dataset_path}: {e!s}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

# --- Health Check (Usually doesn't require auth, but let's add READ_ONLY for consistency) ---
@router.get('/catalogs/health', dependencies=[Depends(PermissionChecker(CATALOG_COMMANDER_FEATURE_ID, FeatureAccessLevel.READ_ONLY))])
async def health_check(catalog_manager: CatalogCommanderManager = Depends(get_catalog_manager)):
    """Check if the catalog API is healthy."""
    try:
        logger.info("Performing health check")
        status = catalog_manager.health_check()
        logger.info("Health check successful")
        return status
    except Exception as e:
        error_msg = f"Health check failed: {e!s}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

# --- TODO: Add Write Routes (Require FULL or higher) ---
# Placeholder for future routes like move, create, delete, rename
# Example:
# @router.post('/catalogs/move', dependencies=[Depends(PermissionChecker(CATALOG_COMMANDER_FEATURE_ID, FeatureAccessLevel.FULL))])
# async def move_asset(...):
#    ...

def register_routes(app):
    """Register routes with the app"""
    app.include_router(router)
    logger.info("Catalog commander routes registered")
