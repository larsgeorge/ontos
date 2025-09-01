import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Request

from src.controller.business_glossaries_manager import BusinessGlossariesManager

# Configure logging
from src.common.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["business-glossaries"])

def get_business_glossaries_manager(request: Request) -> BusinessGlossariesManager:
    """Retrieves the BusinessGlossariesManager singleton from app.state."""
    manager = getattr(request.app.state, 'business_glossaries_manager', None)
    if manager is None:
        logger.critical("BusinessGlossariesManager instance not found in app.state!")
        raise HTTPException(status_code=500, detail="Business Glossary service is not available.")
    if not isinstance(manager, BusinessGlossariesManager):
        logger.critical(f"Object found at app.state.business_glossaries_manager is not a BusinessGlossariesManager instance (Type: {type(manager)})!")
        raise HTTPException(status_code=500, detail="Business Glossary service configuration error.")
    return manager

@router.get('/business-glossaries')
async def get_glossaries(manager: BusinessGlossariesManager = Depends(get_business_glossaries_manager)):
    """Get all glossaries"""
    try:
        logger.info("Retrieving all glossaries")
        glossaries = manager.list_glossaries()
        return {'glossaries': glossaries}
    except Exception as e:
        logger.error(f"Error retrieving glossaries: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/business-glossaries')
async def create_glossary(glossary_data: dict, manager: BusinessGlossariesManager = Depends(get_business_glossaries_manager)):
    """Create a new business glossary"""
    try:
        glossary = manager.create_glossary(
            name=glossary_data['name'],
            description=glossary_data['description'],
            scope=glossary_data['scope'],
            org_unit=glossary_data['org_unit'],
            domain=glossary_data['domain'],
            parent_glossary_ids=glossary_data.get('parent_glossary_ids', []),
            tags=glossary_data.get('tags', [])
        )
        return glossary.to_dict()
    except Exception as e:
        logger.error(f"Error creating glossary: {e!s}")
        raise HTTPException(status_code=400, detail=str(e))

@router.put('/business-glossaries/{glossary_id}')
async def update_glossary(glossary_id: str, glossary_data: dict, manager: BusinessGlossariesManager = Depends(get_business_glossaries_manager)):
    """Update a glossary"""
    try:
        updated_glossary = manager.update_glossary(glossary_id, glossary_data)
        if not updated_glossary:
            raise HTTPException(status_code=404, detail="Glossary not found")
        return updated_glossary
    except Exception as e:
        logger.error(f"Error updating glossary {glossary_id}: {e!s}")
        raise HTTPException(status_code=400, detail=str(e))

@router.delete('/business-glossaries/{glossary_id}')
async def delete_glossary(glossary_id: str, manager: BusinessGlossariesManager = Depends(get_business_glossaries_manager)):
    """Delete a glossary"""
    try:
        manager.delete_glossary(glossary_id)
        return None
    except Exception as e:
        logger.error(f"Error deleting glossary {glossary_id}: {e!s}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get('/business-glossaries/{glossary_id}/terms')
async def get_terms(glossary_id: str, manager: BusinessGlossariesManager = Depends(get_business_glossaries_manager)):
    """Get terms for a glossary"""
    try:
        glossary = manager.get_glossary(glossary_id)
        if not glossary:
            raise HTTPException(status_code=404, detail="Glossary not found")
        return [term.to_dict() for term in glossary.terms.values()]
    except Exception as e:
        logger.error(f"Error getting terms for glossary {glossary_id}: {e!s}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post('/business-glossaries/{glossary_id}/terms')
async def create_term(glossary_id: str, term_data: dict, manager: BusinessGlossariesManager = Depends(get_business_glossaries_manager)):
    """Create a new term in a glossary"""
    try:
        glossary = manager.get_glossary(glossary_id)
        if not glossary:
            raise HTTPException(status_code=404, detail="Glossary not found")

        term = manager.create_term(**term_data)
        manager.add_term_to_glossary(glossary, term)
        return term.to_dict()
    except Exception as e:
        logger.error(f"Error creating term: {e!s}")
        raise HTTPException(status_code=400, detail=str(e))

@router.delete('/business-glossaries/{glossary_id}/terms/{term_id}')
async def delete_term(glossary_id: str, term_id: str, manager: BusinessGlossariesManager = Depends(get_business_glossaries_manager)):
    """Delete a term from a glossary"""
    try:
        glossary = manager.get_glossary(glossary_id)
        if not glossary:
            raise HTTPException(status_code=404, detail="Glossary not found")

        if manager.delete_term_from_glossary(glossary, term_id):
            return None
        raise HTTPException(status_code=404, detail="Term not found")
    except Exception as e:
        logger.error(f"Error deleting term {term_id}: {e!s}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get('/business-glossaries/counts')
async def get_glossary_counts(manager: BusinessGlossariesManager = Depends(get_business_glossaries_manager)):
    """Get counts of glossaries and terms"""
    try:
        counts = manager.get_counts()
        return counts
    except Exception as e:
        logger.error(f"Error getting glossary counts: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

def register_routes(app):
    """Register routes with the app"""
    app.include_router(router)
    logger.info("Business glossary routes registered")
