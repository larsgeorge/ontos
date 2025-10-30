from fastapi import APIRouter, HTTPException

from src.controller.entitlements_manager import EntitlementsManager

# Configure logging
from src.common.logging import get_logger
logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["entitlements"])

# Create a single instance of the manager (YAML loaded automatically in __init__)
entitlements_manager = EntitlementsManager()

@router.get('/entitlements/personas')
async def get_personas():
    """Get all personas"""
    try:
        formatted_personas = entitlements_manager.get_personas_formatted()
        logger.info(f"Retrieved {len(formatted_personas)} personas")
        return formatted_personas
    except Exception as e:
        error_msg = f"Error retrieving personas: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get('/entitlements/personas/{persona_id}')
async def get_persona(persona_id: str):
    """Get a specific persona"""
    try:
        formatted_persona = entitlements_manager.get_persona_formatted(persona_id)
        if not formatted_persona:
            logger.warning(f"Persona not found with ID: {persona_id}")
            raise HTTPException(status_code=404, detail="Persona not found")

        logger.info(f"Retrieved persona with ID: {persona_id}")
        return formatted_persona
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error retrieving persona {persona_id}: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.post('/entitlements/personas')
async def create_persona(persona_data: dict):
    """Create a new persona"""
    try:
        logger.info(f"Creating new persona: {persona_data.get('name', '')}")

        # Create persona (auto-persists to YAML)
        persona = entitlements_manager.create_persona(
            name=persona_data.get('name', ''),
            description=persona_data.get('description', ''),
            privileges=persona_data.get('privileges', [])
        )

        # Format and return
        response = entitlements_manager._format_persona(persona)
        logger.info(f"Successfully created persona with ID: {persona.id}")
        return response
    except Exception as e:
        error_msg = f"Error creating persona: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.put('/entitlements/personas/{persona_id}')
async def update_persona(persona_id: str, persona_data: dict):
    """Update a persona"""
    try:
        # Update persona (auto-persists to YAML)
        updated_persona = entitlements_manager.update_persona(
            persona_id=persona_id,
            name=persona_data.get('name'),
            description=persona_data.get('description'),
            privileges=persona_data.get('privileges')
        )

        if not updated_persona:
            logger.warning(f"Persona not found with ID: {persona_id}")
            raise HTTPException(status_code=404, detail="Persona not found")

        logger.info(f"Successfully updated persona with ID: {persona_id}")
        return entitlements_manager._format_persona(updated_persona)
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error updating persona {persona_id}: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.delete('/entitlements/personas/{persona_id}')
async def delete_persona(persona_id: str):
    """Delete a persona"""
    try:
        if not entitlements_manager.get_persona(persona_id):
            logger.warning(f"Persona not found for deletion with ID: {persona_id}")
            raise HTTPException(status_code=404, detail="Persona not found")

        logger.info(f"Deleting persona with ID: {persona_id}")
        entitlements_manager.delete_persona(persona_id)  # Auto-persists to YAML

        logger.info(f"Successfully deleted persona with ID: {persona_id}")
        return None
    except Exception as e:
        error_msg = f"Error deleting persona {persona_id}: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.post('/entitlements/personas/{persona_id}/privileges')
async def add_privilege(persona_id: str, privilege_data: dict):
    """Add a privilege to a persona"""
    try:
        # Add privilege (auto-persists to YAML)
        updated_persona = entitlements_manager.add_privilege(
            persona_id=persona_id,
            securable_id=privilege_data.get('securable_id', ''),
            securable_type=privilege_data.get('securable_type', ''),
            permission=privilege_data.get('permission', 'READ')
        )

        if not updated_persona:
            logger.warning(f"Persona not found with ID: {persona_id}")
            raise HTTPException(status_code=404, detail="Persona not found")

        logger.info(f"Successfully added privilege to persona with ID: {persona_id}")
        return entitlements_manager._format_persona(updated_persona)
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error adding privilege to persona {persona_id}: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.delete('/entitlements/personas/{persona_id}/privileges/{securable_id:path}')
async def remove_privilege(persona_id: str, securable_id: str):
    """Remove a privilege from a persona"""
    try:
        logger.info(f"Removing privilege {securable_id} from persona with ID: {persona_id}")

        # Remove privilege (auto-persists to YAML)
        updated_persona = entitlements_manager.remove_privilege(
            persona_id=persona_id,
            securable_id=securable_id
        )

        if not updated_persona:
            logger.warning(f"Persona not found with ID: {persona_id}")
            raise HTTPException(status_code=404, detail="Persona not found")

        logger.info(f"Successfully removed privilege from persona with ID: {persona_id}")
        return entitlements_manager._format_persona(updated_persona)
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error removing privilege from persona {persona_id}: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.put('/entitlements/personas/{persona_id}/groups')
async def update_persona_groups(persona_id: str, groups_data: dict):
    """Update groups for a persona"""
    try:
        if not isinstance(groups_data.get('groups'), list):
            raise HTTPException(status_code=400, detail="Invalid groups data")

        # Update groups (auto-persists to YAML)
        updated_persona = entitlements_manager.update_persona_groups(
            persona_id=persona_id,
            groups=groups_data['groups']
        )

        logger.info(f"Successfully updated groups for persona with ID: {persona_id}")
        return entitlements_manager._format_persona(updated_persona)
    except ValueError as e:
        # Persona not found
        logger.warning(f"Persona not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error updating groups for persona {persona_id}: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

def register_routes(app):
    """Register routes with the app"""
    app.include_router(router)
    logger.info("Entitlements routes registered")
