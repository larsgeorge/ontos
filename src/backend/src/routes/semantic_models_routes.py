import os
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Request, Query

from src.controller.semantic_models_manager import SemanticModelsManager
from src.models.ontology import (
    OntologyConcept,
    ConceptHierarchy,
    TaxonomyStats,
    ConceptSearchResult
)

# Configure logging
from src.common.logging import get_logger
logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["semantic-models"])

def get_semantic_models_manager(request: Request) -> SemanticModelsManager:
    """Retrieves the SemanticModelsManager singleton from app.state."""
    manager = getattr(request.app.state, 'semantic_models_manager', None)
    if manager is None:
        logger.critical("SemanticModelsManager instance not found in app.state!")
        raise HTTPException(status_code=500, detail="Semantic Models service is not available.")
    if not isinstance(manager, SemanticModelsManager):
        logger.critical(f"Object found at app.state.semantic_models_manager is not a SemanticModelsManager instance (Type: {type(manager)})!")
        raise HTTPException(status_code=500, detail="Semantic Models service configuration error.")
    return manager

# --- Semantic Models endpoints ---

@router.get('/semantic-models')
async def get_semantic_models(manager: SemanticModelsManager = Depends(get_semantic_models_manager)) -> dict:
    """Get all available semantic models (formerly taxonomies)"""
    try:
        logger.info("Retrieving all semantic models from semantic knowledge graph")
        models = manager.get_taxonomies()
        # New key name for the list endpoint
        return {'semantic_models': [m.model_dump() for m in models]}
    except Exception as e:
        logger.error(f"Error retrieving semantic models: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/semantic-models/concepts')
async def list_simple_concepts(
    q: Optional[str] = Query(None, description="Simple text filter for concepts"),
    limit: int = Query(50, description="Maximum number of results"),
    manager: SemanticModelsManager = Depends(get_semantic_models_manager)
) -> List[dict]:
    """Return a simple flat list of concepts for selection dialogs.

    Shape: [{ value, label, type }]
    """
    try:
        results = manager.search_concepts(q or "", limit=limit)
        return results
    except Exception as e:
        logger.error(f"Error retrieving simple concepts: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/semantic-models/concepts/suggestions')
async def list_concept_suggestions(
    q: Optional[str] = Query(None, description="Simple text filter for concepts"),
    parent_iris: Optional[str] = Query(None, description="Comma-separated parent concept IRIs"),
    limit: int = Query(50, description="Maximum number of results"),
    manager: SemanticModelsManager = Depends(get_semantic_models_manager)
) -> dict:
    """Return suggested child concepts (if parent_iris provided) and other matches.

    Shape: { suggested: ConceptItem[], other: ConceptItem[] }
    """
    try:
        parents_list = [p for p in (parent_iris.split(',') if parent_iris else []) if p]
        data = manager.search_concepts_with_suggestions(text_filter=(q or ""), parent_iris=parents_list, limit=limit)
        return data
    except Exception as e:
        logger.error(f"Error retrieving concept suggestions: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/semantic-models/properties')
async def list_simple_properties(
    q: Optional[str] = Query(None, description="Simple text filter for properties"),
    limit: int = Query(50, description="Maximum number of results"),
    manager: SemanticModelsManager = Depends(get_semantic_models_manager)
) -> List[dict]:
    """Return a simple flat list of properties for selection dialogs.

    Shape: [{ value, label, type: 'property' }]
    """
    try:
        results = manager.search_properties(q or "", limit=limit)
        return results
    except Exception as e:
        logger.error(f"Error retrieving simple properties: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/semantic-models/properties/suggestions')
async def list_property_suggestions(
    q: Optional[str] = Query(None, description="Simple text filter for properties"),
    parent_iris: Optional[str] = Query(None, description="Comma-separated parent concept IRIs (unused for properties)"),
    limit: int = Query(50, description="Maximum number of results"),
    manager: SemanticModelsManager = Depends(get_semantic_models_manager)
) -> dict:
    """Return suggested properties (typically empty) and other matches.

    Shape: { suggested: ConceptItem[], other: ConceptItem[] }
    """
    try:
        parents_list = [p for p in (parent_iris.split(',') if parent_iris else []) if p]
        data = manager.search_properties_with_suggestions(text_filter=(q or ""), parent_iris=parents_list, limit=limit)
        return data
    except Exception as e:
        logger.error(f"Error retrieving property suggestions: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/semantic-models/concepts-grouped')
async def get_concepts_grouped(
    manager: SemanticModelsManager = Depends(get_semantic_models_manager)
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

@router.get('/semantic-models/concepts/{concept_iri:path}/hierarchy')
async def get_concept_hierarchy(
    concept_iri: str,
    manager: SemanticModelsManager = Depends(get_semantic_models_manager)
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

@router.get('/semantic-models/concepts/{concept_iri:path}')
async def get_concept_details(
    concept_iri: str,
    manager: SemanticModelsManager = Depends(get_semantic_models_manager)
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

@router.get('/semantic-models/stats')
async def get_taxonomy_stats(
    manager: SemanticModelsManager = Depends(get_semantic_models_manager)
) -> dict:
    """Get statistics about loaded taxonomies"""
    try:
        logger.info("Retrieving taxonomy statistics")
        stats = manager.get_taxonomy_stats()
        return {'stats': stats.model_dump()}
    except Exception as e:
        logger.error(f"Error retrieving taxonomy stats: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/semantic-models/search')
async def search_concepts(
    q: str = Query(..., description="Search query"),
    taxonomy: Optional[str] = Query(None, description="Filter by taxonomy name"),
    limit: int = Query(50, description="Maximum number of results"),
    manager: SemanticModelsManager = Depends(get_semantic_models_manager)
) -> dict:
    """Search for concepts by text query"""
    try:
        logger.info(f"Searching concepts with query: '{q}' in taxonomy: {taxonomy}")
        # Use the ontology-aware search that returns ConceptSearchResult items
        results = manager.search_ontology_concepts(q, taxonomy, limit)
        
        return {
            'results': [result.model_dump() for result in results]
        }
    except Exception as e:
        logger.error(f"Error searching concepts: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))

"""Legacy Business Glossary endpoints removed during rename to Semantic Models."""

def register_routes(app):
    """Register routes with the app"""
    app.include_router(router)
    logger.info("Semantic models routes registered")