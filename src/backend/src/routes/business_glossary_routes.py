import os
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Request, Query

from src.controller.business_glossaries_manager import BusinessGlossariesManager
from src.models.ontology import (
    OntologyTaxonomy,
    OntologyConcept,
    ConceptHierarchy,
    TaxonomyStats,
    ConceptSearchResult
)

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

# --- New Ontology-based endpoints ---

@router.get('/business-glossaries')
async def get_taxonomies(manager: BusinessGlossariesManager = Depends(get_business_glossaries_manager)) -> dict:
    """Get all available taxonomies"""
    try:
        logger.info("Retrieving all taxonomies from semantic knowledge graph")
        taxonomies = manager.get_taxonomies()
        return {'taxonomies': [taxonomy.model_dump() for taxonomy in taxonomies]}
    except Exception as e:
        logger.error(f"Error retrieving taxonomies: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/business-glossaries/concepts')
async def get_concepts(
    taxonomy_name: Optional[str] = Query(None, description="Filter by taxonomy name"),
    search: Optional[str] = Query(None, description="Search query"),
    limit: int = Query(100, description="Maximum number of results"),
    manager: BusinessGlossariesManager = Depends(get_business_glossaries_manager)
) -> dict:
    """Get concepts, optionally filtered by taxonomy or search query"""
    try:
        if search:
            logger.info(f"Searching concepts with query: '{search}' in taxonomy: {taxonomy_name}")
            results = manager.search_concepts(search, taxonomy_name, limit)
            concepts = [result.concept for result in results]
        else:
            logger.info(f"Retrieving concepts from taxonomy: {taxonomy_name or 'all'}")
            concepts = manager.get_concepts_by_taxonomy(taxonomy_name)
        
        return {
            'concepts': [concept.model_dump() for concept in concepts[:limit]]
        }
    except Exception as e:
        logger.error(f"Error retrieving concepts: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/business-glossaries/concepts-grouped')
async def get_concepts_grouped(
    manager: BusinessGlossariesManager = Depends(get_business_glossaries_manager)
) -> dict:
    """Get all concepts grouped by taxonomy source"""
    try:
        logger.info("Retrieving concepts grouped by taxonomy")
        grouped = manager.get_grouped_concepts()
        
        # Convert to serializable format
        result = {}
        for source, concepts in grouped.items():
            result[source] = [concept.model_dump() for concept in concepts]
        
        return {'grouped_concepts': result}
    except Exception as e:
        logger.error(f"Error retrieving grouped concepts: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/business-glossaries/concepts/{concept_iri:path}/hierarchy')
async def get_concept_hierarchy(
    concept_iri: str,
    manager: BusinessGlossariesManager = Depends(get_business_glossaries_manager)
) -> dict:
    """Get hierarchical relationships for a concept"""
    try:
        logger.info(f"Retrieving hierarchy for concept: {concept_iri}")
        hierarchy = manager.get_concept_hierarchy(concept_iri)
        
        if not hierarchy:
            raise HTTPException(status_code=404, detail="Concept not found")
        
        return {'hierarchy': hierarchy.model_dump()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving concept hierarchy for {concept_iri}: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/business-glossaries/concepts/{concept_iri:path}')
async def get_concept_details(
    concept_iri: str,
    manager: BusinessGlossariesManager = Depends(get_business_glossaries_manager)
) -> dict:
    """Get detailed information about a specific concept"""
    try:
        logger.info(f"Retrieving details for concept: {concept_iri}")
        concept = manager.get_concept_details(concept_iri)
        
        if not concept:
            raise HTTPException(status_code=404, detail="Concept not found")
        
        return {'concept': concept.model_dump()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving concept details for {concept_iri}: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/business-glossaries/stats')
async def get_taxonomy_stats(
    manager: BusinessGlossariesManager = Depends(get_business_glossaries_manager)
) -> dict:
    """Get statistics about loaded taxonomies"""
    try:
        logger.info("Retrieving taxonomy statistics")
        stats = manager.get_taxonomy_stats()
        return {'stats': stats.model_dump()}
    except Exception as e:
        logger.error(f"Error retrieving taxonomy stats: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/business-glossaries/search')
async def search_concepts(
    q: str = Query(..., description="Search query"),
    taxonomy: Optional[str] = Query(None, description="Filter by taxonomy name"),
    limit: int = Query(50, description="Maximum number of results"),
    manager: BusinessGlossariesManager = Depends(get_business_glossaries_manager)
) -> dict:
    """Search for concepts by text query"""
    try:
        logger.info(f"Searching concepts with query: '{q}' in taxonomy: {taxonomy}")
        results = manager.search_concepts(q, taxonomy, limit)
        
        return {
            'results': [result.model_dump() for result in results]
        }
    except Exception as e:
        logger.error(f"Error searching concepts: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Legacy endpoints for backwards compatibility ---

@router.post('/business-glossaries')
async def create_glossary(glossary_data: dict, manager: BusinessGlossariesManager = Depends(get_business_glossaries_manager)):
    """Create a new business glossary (legacy)"""
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
    """Update a glossary (legacy)"""
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
    """Delete a glossary (legacy)"""
    try:
        manager.delete_glossary(glossary_id)
        return None
    except Exception as e:
        logger.error(f"Error deleting glossary {glossary_id}: {e!s}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get('/business-glossaries/{glossary_id}/terms')
async def get_terms(glossary_id: str, manager: BusinessGlossariesManager = Depends(get_business_glossaries_manager)):
    """Get terms for a glossary (legacy)"""
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
    """Create a new term in a glossary (legacy)"""
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
    """Delete a term from a glossary (legacy)"""
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
    """Get counts of glossaries and terms (legacy)"""
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