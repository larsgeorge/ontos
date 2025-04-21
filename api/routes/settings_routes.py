import logging
from typing import List, Dict, Any, Optional

from databricks.sdk import WorkspaceClient
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session

from ..common.workspace_client import get_workspace_client
from ..controller.settings_manager import SettingsManager
from ..models.settings import AppRole, AppRoleCreate
from ..common.database import get_db
from ..common.dependencies import get_settings_manager

# Configure logging
from api.common.logging import setup_logging, get_logger
setup_logging(level=logging.INFO)
logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["settings"])

@router.get('/settings')
async def get_settings(manager: SettingsManager = Depends(get_settings_manager)):
    """Get all settings including available job clusters"""
    try:
        settings = manager.get_settings()
        return settings
    except Exception as e:
        logger.error(f"Error getting settings: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put('/settings')
async def update_settings(
    settings: dict,
    manager: SettingsManager = Depends(get_settings_manager)
):
    """Update settings"""
    try:
        updated = manager.update_settings(settings)
        return updated.to_dict()
    except Exception as e:
        logger.error(f"Error updating settings: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/settings/health')
async def health_check(manager: SettingsManager = Depends(get_settings_manager)):
    """Check if the settings API is healthy"""
    try:
        # Try to list workflows as a health check
        manager.list_available_workflows()
        logger.info("Workflows health check successful")
        return {"status": "healthy"}
    except Exception as e:
        error_msg = f"Workflows health check failed: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get('/settings/job-clusters')
async def list_job_clusters(manager: SettingsManager = Depends(get_settings_manager)):
    """List all available job clusters"""
    try:
        clusters = manager.get_job_clusters()
        return [{
            'id': cluster.id,
            'name': cluster.name,
            'node_type_id': cluster.node_type_id,
            'autoscale': cluster.autoscale,
            'min_workers': cluster.min_workers,
            'max_workers': cluster.max_workers
        } for cluster in clusters]
    except Exception as e:
        logger.error(f"Error fetching job clusters: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

# --- RBAC Routes ---

@router.get("/settings/features", response_model=Dict[str, Dict[str, Any]])
async def get_features_config(manager: SettingsManager = Depends(get_settings_manager)):
    """Get the application feature configuration including allowed access levels."""
    try:
        features = manager.get_features_with_access_levels()
        return features
    except Exception as e:
        logger.error(f"Error getting features configuration: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/settings/roles", response_model=List[AppRole])
async def list_roles(manager: SettingsManager = Depends(get_settings_manager)):
    """List all application roles."""
    try:
        roles = manager.list_app_roles()
        return roles
    except Exception as e:
        logger.error(f"Error listing roles: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/settings/roles", response_model=AppRole, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: AppRoleCreate = Body(..., embed=False),
    manager: SettingsManager = Depends(get_settings_manager)
):
    """Create a new application role."""
    try:
        # The SettingsManager handles the creation logic, including ID generation if needed
        # Pass the AppRoleCreate object directly
        created_role = manager.create_app_role(role_data)
        return created_role
    except ValueError as e:
        logger.warning(f"Validation error creating role '{role_data.name}': {e!s}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating role '{role_data.name}': {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/settings/roles/{role_id}", response_model=AppRole)
async def get_role(
    role_id: str,
    manager: SettingsManager = Depends(get_settings_manager)
):
    """Get a specific application role by ID."""
    try:
        role = manager.get_app_role(role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        return role
    except Exception as e:
        logger.error(f"Error getting role '{role_id}': {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/settings/roles/{role_id}", response_model=AppRole)
async def update_role(
    role_id: str,
    role_data: AppRole = Body(..., embed=False),
    manager: SettingsManager = Depends(get_settings_manager)
):
    """Update an existing application role."""
    try:
        updated_role = manager.update_app_role(role_id, role_data)
        if updated_role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        return updated_role
    except ValueError as e:
        logger.warning(f"Validation error updating role '{role_id}': {e!s}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating role '{role_id}': {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/settings/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: str,
    manager: SettingsManager = Depends(get_settings_manager)
):
    """Delete an application role."""
    try:
        deleted = manager.delete_app_role(role_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        return None # Return None for 204
    except ValueError as e: # Catch potential error like deleting admin role
        logger.warning(f"Error deleting role '{role_id}': {e!s}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting role '{role_id}': {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Registration --- 

def register_routes(app):
    """Register routes with the app"""
    app.include_router(router)
    logger.info("Settings routes registered")
