import logging
import os
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from src.common.workspace_client import get_workspace_client_dependency
from src.controller.entitlements_sync_manager import EntitlementsSyncManager
from src.models.entitlements_sync import EntitlementSyncConfig

# Configure logging
from src.common.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["entitlements-sync"])

# Create a function to get the manager with dependency injection
def get_entitlements_sync_manager(workspace_client = Depends(get_workspace_client_dependency(timeout=30))):
    manager = EntitlementsSyncManager()
    manager.workspace_client = workspace_client

    # Check for YAML file in data directory
    yaml_path = Path(__file__).parent.parent / 'data' / 'entitlements_sync.yaml'
    if os.path.exists(yaml_path):
        try:
            manager.load_from_yaml(str(yaml_path))
            logging.info(f"Successfully loaded entitlements sync configurations from {yaml_path}")
        except Exception as e:
            logging.exception(f"Error loading entitlements sync configurations from YAML: {e!s}")

    return manager

@router.get("/entitlements-sync/configs", response_model=List[EntitlementSyncConfig])
async def get_configs(manager: EntitlementsSyncManager = Depends(get_entitlements_sync_manager)):
    """Get all entitlements sync configurations"""
    return manager.get_configs()

@router.get("/entitlements-sync/configs/{config_id}", response_model=EntitlementSyncConfig)
async def get_config(config_id: str, manager: EntitlementsSyncManager = Depends(get_entitlements_sync_manager)):
    """Get a specific sync configuration by ID"""
    config = manager.get_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config

@router.post("/entitlements-sync/configs", response_model=EntitlementSyncConfig)
async def create_config(config: EntitlementSyncConfig, manager: EntitlementsSyncManager = Depends(get_entitlements_sync_manager)):
    """Create a new sync configuration"""
    return manager.create_config(config)

@router.put("/entitlements-sync/configs/{config_id}", response_model=EntitlementSyncConfig)
async def update_config(config_id: str, config: EntitlementSyncConfig, manager: EntitlementsSyncManager = Depends(get_entitlements_sync_manager)):
    """Update an existing sync configuration"""
    updated_config = manager.update_config(config_id, config)
    if not updated_config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return updated_config

@router.delete("/entitlements-sync/configs/{config_id}")
async def delete_config(config_id: str, manager: EntitlementsSyncManager = Depends(get_entitlements_sync_manager)):
    """Delete a sync configuration"""
    if not manager.delete_config(config_id):
        raise HTTPException(status_code=404, detail="Configuration not found")
    return {"message": "Configuration deleted successfully"}

@router.get("/entitlements-sync/connections")
async def get_connections(manager: EntitlementsSyncManager = Depends(get_entitlements_sync_manager)):
    """Get available Unity Catalog connections"""
    return manager.get_connections()

@router.get("/entitlements-sync/catalogs")
async def get_catalogs(manager: EntitlementsSyncManager = Depends(get_entitlements_sync_manager)):
    """Get available Unity Catalog catalogs"""
    return manager.get_catalogs()

def register_routes(app):
    """Register routes with the app"""
    app.include_router(router)
    logger.info("Entitlements Sync routes registered")
