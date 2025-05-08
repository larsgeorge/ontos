from fastapi import APIRouter, Depends, HTTPException
from api.common.config import Settings, get_settings
from api.common.workspace_client import get_workspace_client, WorkspaceClient
from api.models.estate import Estate, CloudType, SyncStatus
from api.controller.estate_manager import EstateManager
import logging
import os
from pathlib import Path
import yaml
from datetime import datetime

# Configure logging
from api.common.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["estates"])

def get_estate_manager(client: WorkspaceClient = Depends(get_workspace_client), settings: Settings = Depends(get_settings)) -> EstateManager:
    logger.info("Getting estate manager")
    manager = EstateManager(client, settings)

    # Check for YAML file in data directory
    yaml_path = Path(__file__).parent.parent / 'data' / 'estates.yaml'
    if os.path.exists(yaml_path):
        try:
            manager.load_from_yaml(yaml_path)
            logger.info(f"Successfully loaded estates from {yaml_path}")
        except Exception as e:
            logger.exception(f"Error loading estates from YAML: {e!s}")

    return manager

@router.get("/estates", response_model=list[Estate])
async def list_estates(estate_manager: EstateManager = Depends(get_estate_manager)):
    """List all configured estates"""
    logger.info("Listing estates")
    return await estate_manager.list_estates()

@router.get("/estates/{estate_id}", response_model=Estate)
async def get_estate(estate_id: str, estate_manager: EstateManager = Depends(get_estate_manager)):
    """Get a specific estate by ID"""
    estate = await estate_manager.get_estate(estate_id)
    if not estate:
        raise HTTPException(status_code=404, detail="Estate not found")
    return estate

@router.post("/estates", response_model=Estate)
async def create_estate(estate: Estate, estate_manager: EstateManager = Depends(get_estate_manager)):
    """Create a new estate"""
    return await estate_manager.create_estate(estate)

@router.put("/estates/{estate_id}", response_model=Estate)
async def update_estate(estate_id: str, estate: Estate, estate_manager: EstateManager = Depends(get_estate_manager)):
    """Update an existing estate"""
    updated_estate = await estate_manager.update_estate(estate_id, estate)
    if not updated_estate:
        raise HTTPException(status_code=404, detail="Estate not found")
    return updated_estate

@router.delete("/estates/{estate_id}")
async def delete_estate(estate_id: str, estate_manager: EstateManager = Depends(get_estate_manager)):
    """Delete an estate"""
    success = await estate_manager.delete_estate(estate_id)
    if not success:
        raise HTTPException(status_code=404, detail="Estate not found")
    return {"message": "Estate deleted successfully"}

@router.post("/estates/{estate_id}/sync")
async def sync_estate(estate_id: str, estate_manager: EstateManager = Depends(get_estate_manager)):
    """Trigger a sync for a specific estate"""
    success = await estate_manager.sync_estate(estate_id)
    if not success:
        raise HTTPException(status_code=404, detail="Estate not found or sync disabled")
    return {"message": "Estate sync triggered successfully"} 

def register_routes(app):
    """Register routes with the app"""
    app.include_router(router)
    logger.info("Estate manager routes registered")
