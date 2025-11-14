import os
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Request, Query, UploadFile, File

from src.controller.semantic_models_manager import SemanticModelsManager
from src.models.ontology import (
    OntologyConcept,
    ConceptHierarchy,
    TaxonomyStats,
    ConceptSearchResult
)
from src.models.semantic_models import SemanticModelCreate, SemanticModelUpdate
from src.common.dependencies import CurrentUserDep, AuditManagerDep, DBSessionDep, AuditCurrentUserDep
from src.common.authorization import PermissionChecker
from src.common.features import FeatureAccessLevel
from src.common.file_security import sanitize_filename
from rdflib import ConjunctiveGraph, RDF

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
    """Get all available semantic models (database + file-based + built-in schemas)"""
    try:
        logger.info("Retrieving all semantic models from database and graph")
        
        # Get database models (with IDs, upload info, enabled status)
        db_models = manager.list()
        
        # Get graph-based taxonomies (file-based and built-in schemas)
        graph_taxonomies = manager.get_taxonomies()
        
        # Convert graph taxonomies to API format (they don't have DB IDs)
        # Skip any that match database model names to avoid duplicates
        db_model_names = {m.name for m in db_models}
        
        combined = []
        
        # Add database models first
        for m in db_models:
            combined.append(m.model_dump())
        
        # Add graph-based taxonomies that aren't in the database
        for tax in graph_taxonomies:
            if tax.name not in db_model_names:
                # Create a pseudo-model for file-based/schema taxonomies
                combined.append({
                    'id': f'file-{tax.name}',  # Pseudo-ID for file-based
                    'name': tax.name,
                    'format': tax.format or 'skos',
                    'original_filename': tax.name,
                    'content_type': 'text/turtle' if tax.format == 'ttl' else 'application/rdf+xml',
                    'size_bytes': None,
                    'enabled': True,  # File-based are always enabled
                    'created_by': 'system@file' if tax.source_type == 'file' else f'system@{tax.source_type}',
                    'updated_by': None,
                    'created_at': None,
                    'updated_at': None,
                })
        
        return {'semantic_models': combined}
    except Exception as e:
        logger.error("Error retrieving semantic models", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve semantic models")

@router.post('/semantic-models/upload')
async def upload_semantic_model(
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    file: UploadFile = File(...),
    manager: SemanticModelsManager = Depends(get_semantic_models_manager),
    _: bool = Depends(PermissionChecker("semantic-models", FeatureAccessLevel.READ_WRITE))
) -> dict:
    """Upload a new semantic model file (RDFS/SKOS/OWL/etc.)"""
    
    # SECURITY: Sanitize filename
    raw_filename = file.filename or "ontology.ttl"
    safe_filename = sanitize_filename(raw_filename, default="ontology.ttl")
    
    # Validate file extension
    allowed_extensions = {'.ttl', '.rdf', '.xml', '.skos', '.rdfs', '.owl', '.nt', '.n3', '.trig', '.trix', '.jsonld', '.json'}
    lower_filename = safe_filename.lower()
    if not any(lower_filename.endswith(ext) for ext in allowed_extensions):
        audit_manager.log_action(
            db=db,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            feature="semantic-models",
            action="UPLOAD",
            success=False,
            details={"filename": safe_filename, "error": "Invalid file type"}
        )
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(sorted(allowed_extensions))}"
        )
    
    success = False
    created_model_id = None
    
    try:
        # Read file content
        content_bytes = await file.read()
        content_text = content_bytes.decode('utf-8')
        size_bytes = len(content_bytes)
        
        # Detect format from extension
        def detect_format(filename: str) -> str:
            lower = filename.lower()
            if lower.endswith('.ttl') or lower.endswith('.n3'):
                return "skos"
            return "rdfs"
        
        format_type = detect_format(safe_filename)
        
        # Parse and count concepts/properties to validate file
        try:
            temp_graph = ConjunctiveGraph()
            if format_type == "skos":
                temp_graph.parse(data=content_text, format="turtle")
            else:
                temp_graph.parse(data=content_text, format="xml")
            
            # Count concepts using SPARQL query
            concepts_query = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT (COUNT(DISTINCT ?concept) AS ?count) WHERE {
                {
                    ?concept a rdfs:Class .
                } UNION {
                    ?concept a skos:Concept .
                } UNION {
                    ?concept a skos:ConceptScheme .
                }
                FILTER(!STRSTARTS(STR(?concept), "http://www.w3.org/1999/02/22-rdf-syntax-ns#"))
                FILTER(!STRSTARTS(STR(?concept), "http://www.w3.org/2000/01/rdf-schema#"))
                FILTER(!STRSTARTS(STR(?concept), "http://www.w3.org/2004/02/skos/core#"))
            }
            """
            count_results = list(temp_graph.query(concepts_query))
            concepts_count = int(count_results[0][0]) if count_results and count_results[0][0] is not None else 0
            
            properties_count = len(list(temp_graph.subjects(RDF.type, RDF.Property)))
            
            logger.info(f"Parsed file '{safe_filename}': {concepts_count} concepts, {properties_count} properties")
            
        except Exception as parse_error:
            logger.error(f"Failed to parse uploaded file '{safe_filename}': {parse_error}", exc_info=True)
            audit_manager.log_action(
                db=db,
                username=current_user.username,
                ip_address=request.client.host if request.client else None,
                feature="semantic-models",
                action="UPLOAD",
                success=False,
                details={
                    "filename": safe_filename,
                    "error": "File parsing failed",
                    "parse_error": str(parse_error)
                }
            )
            raise HTTPException(
                status_code=400,
                detail=f"Failed to parse ontology file. Please check the file format and syntax. Error: {str(parse_error)}"
            )
        
        # Create semantic model in database
        create_data = SemanticModelCreate(
            name=safe_filename,
            format=format_type,
            content_text=content_text,
            original_filename=safe_filename,
            content_type=file.content_type,
            size_bytes=size_bytes,
            enabled=True
        )
        
        created_model = manager.create(create_data, created_by=current_user.username)
        created_model_id = created_model.id
        
        # Rebuild graph to include the new model
        manager.rebuild_graph_from_enabled()
        
        success = True
        
        # Audit log success
        audit_manager.log_action(
            db=db,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            feature="semantic-models",
            action="UPLOAD",
            success=True,
            details={
                "filename": safe_filename,
                "model_id": created_model_id,
                "concepts_count": concepts_count,
                "properties_count": properties_count,
                "size_bytes": size_bytes
            }
        )
        
        logger.info(f"Successfully uploaded semantic model '{safe_filename}' (ID: {created_model_id})")
        
        return {"model": created_model.model_dump(), "message": "Semantic model uploaded successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error uploading semantic model: {e}", exc_info=True)
        audit_manager.log_action(
            db=db,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            feature="semantic-models",
            action="UPLOAD",
            success=False,
            details={"filename": safe_filename, "error": str(e)}
        )
        raise HTTPException(status_code=500, detail=f"Failed to upload semantic model: {str(e)}")

@router.patch('/semantic-models/{model_id}')
async def update_semantic_model(
    model_id: str,
    update_data: SemanticModelUpdate,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    manager: SemanticModelsManager = Depends(get_semantic_models_manager),
    _: bool = Depends(PermissionChecker("semantic-models", FeatureAccessLevel.READ_WRITE))
) -> dict:
    """Update a semantic model (e.g., toggle enabled status)"""
    
    try:
        # Update the model
        updated_model = manager.update(model_id, update_data, updated_by=current_user.username)
        
        if not updated_model:
            audit_manager.log_action(
                db=db,
                username=current_user.username,
                ip_address=request.client.host if request.client else None,
                feature="semantic-models",
                action="UPDATE",
                success=False,
                details={"model_id": model_id, "error": "Model not found"}
            )
            raise HTTPException(status_code=404, detail="Semantic model not found")
        
        # Rebuild graph to reflect enabled/disabled status
        manager.rebuild_graph_from_enabled()
        
        # Audit log success
        audit_manager.log_action(
            db=db,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            feature="semantic-models",
            action="UPDATE",
            success=True,
            details={
                "model_id": model_id,
                "updates": update_data.model_dump(exclude_unset=True)
            }
        )
        
        logger.info(f"Successfully updated semantic model {model_id}")
        
        return {"model": updated_model.model_dump(), "message": "Semantic model updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating semantic model {model_id}: {e}", exc_info=True)
        audit_manager.log_action(
            db=db,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            feature="semantic-models",
            action="UPDATE",
            success=False,
            details={"model_id": model_id, "error": str(e)}
        )
        raise HTTPException(status_code=500, detail=f"Failed to update semantic model: {str(e)}")

@router.delete('/semantic-models/{model_id}', status_code=204)
async def delete_semantic_model(
    model_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    manager: SemanticModelsManager = Depends(get_semantic_models_manager),
    _: bool = Depends(PermissionChecker("semantic-models", FeatureAccessLevel.READ_WRITE))
):
    """Delete a semantic model"""
    
    try:
        # Get model details for audit log before deletion
        model = manager.get(model_id)
        if not model:
            audit_manager.log_action(
                db=db,
                username=current_user.username,
                ip_address=request.client.host if request.client else None,
                feature="semantic-models",
                action="DELETE",
                success=False,
                details={"model_id": model_id, "error": "Model not found"}
            )
            raise HTTPException(status_code=404, detail="Semantic model not found")
        
        # Delete the model
        success = manager.delete(model_id)
        
        if not success:
            audit_manager.log_action(
                db=db,
                username=current_user.username,
                ip_address=request.client.host if request.client else None,
                feature="semantic-models",
                action="DELETE",
                success=False,
                details={"model_id": model_id, "error": "Failed to delete"}
            )
            raise HTTPException(status_code=500, detail="Failed to delete semantic model")
        
        # Rebuild graph to remove deleted model
        manager.rebuild_graph_from_enabled()
        
        # Audit log success
        audit_manager.log_action(
            db=db,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            feature="semantic-models",
            action="DELETE",
            success=True,
            details={
                "model_id": model_id,
                "model_name": model.name
            }
        )
        
        logger.info(f"Successfully deleted semantic model {model_id} ('{model.name}')")
        
        # Return 204 No Content
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting semantic model {model_id}: {e}", exc_info=True)
        audit_manager.log_action(
            db=db,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            feature="semantic-models",
            action="DELETE",
            success=False,
            details={"model_id": model_id, "error": str(e)}
        )
        raise HTTPException(status_code=500, detail=f"Failed to delete semantic model: {str(e)}")

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
        logger.error("Error retrieving simple concepts", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve concepts")

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
        logger.error("Error retrieving concept suggestions", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve concept suggestions")

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
        logger.error("Error retrieving simple properties", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve properties")

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
        logger.error("Error retrieving property suggestions", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve property suggestions")

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
        logger.error("Error retrieving grouped concepts", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve grouped concepts")

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
        logger.error("Error retrieving concept hierarchy for %s", concept_iri, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve concept hierarchy")

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
        logger.error("Error retrieving concept details for %s", concept_iri, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve concept details")

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
        logger.error("Error retrieving taxonomy stats", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve taxonomy stats")

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
        logger.error("Error searching concepts", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to search concepts")

@router.get('/semantic-models/neighbors')
async def get_neighbors(
    iri: str = Query(..., description="Resource IRI to get neighbors for"),
    limit: int = Query(200, description="Maximum number of neighbors to return"),
    manager: SemanticModelsManager = Depends(get_semantic_models_manager)
) -> List[dict]:
    """Get all neighboring triples for a resource (for graph navigation).

    Returns a list of neighbors with direction (incoming/outgoing/predicate),
    predicate IRI, display value, display type, and step information.
    """
    try:
        logger.info(f"Retrieving neighbors for IRI: {iri} (limit: {limit})")
        neighbors = manager.neighbors(iri, limit)
        return neighbors
    except Exception as e:
        logger.error("Error retrieving neighbors for %s", iri, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve neighbors")

@router.get('/semantic-models/prefix')
async def prefix_search(
    q: str = Query(..., description="IRI prefix substring to search for"),
    limit: int = Query(25, description="Maximum number of results"),
    manager: SemanticModelsManager = Depends(get_semantic_models_manager)
) -> List[dict]:
    """Search for resources and properties by IRI prefix/substring.

    Returns a list of items with value (IRI) and type (resource/property).
    """
    try:
        logger.info(f"Searching by prefix: '{q}' (limit: {limit})")
        results = manager.prefix_search(q, limit)
        return results
    except Exception as e:
        logger.error("Error in prefix search for '%s'", q, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to perform prefix search")

@router.post('/semantic-models/query')
async def sparql_query(
    http_request: Request,
    request: dict,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    audit_manager: AuditManagerDep,
    _: bool = Depends(PermissionChecker("semantic-models", FeatureAccessLevel.READ_WRITE)),
    manager: SemanticModelsManager = Depends(get_semantic_models_manager)
) -> List[dict]:
    """Execute a SPARQL query against the loaded semantic graph.

    Request body should contain a 'sparql' field with the SPARQL query string.
    Returns a list of result bindings as dictionaries.
    
    Security: Requires authentication and READ_WRITE permission.
    Only read-only SPARQL queries (SELECT, ASK, DESCRIBE, CONSTRUCT) are allowed.
    Queries are validated for safety and subject to resource limits.
    """
    try:
        sparql = request.get('sparql', '')
        if not sparql:
            raise HTTPException(status_code=400, detail="Missing 'sparql' field in request body")

        # Log security event - query attempt
        logger.warning(
            f"SPARQL query execution attempt by user '{current_user.email}': "
            f"query_length={len(sparql)}"
        )
        
        # Execute query with validation and safety limits
        # The manager will validate and enforce timeout/result limits
        try:
            results = manager.query(sparql, max_results=1000, timeout_seconds=30)
        except ValueError as ve:
            # Validation or execution error
            logger.error(f"SPARQL query validation/execution failed for user '{current_user.email}': {ve}")
            audit_manager.log_action(
                db=db,
                username=current_user.email,
                ip_address=http_request.client.host if http_request.client else None,
                feature="semantic-models",
                action="SPARQL_QUERY_FAILED",
                success=False,
                details={"error": str(ve), "query_length": len(sparql)}
            )
            raise HTTPException(status_code=400, detail=str(ve))
        
        # Audit log successful execution
        audit_manager.log_action(
            db=db,
            username=current_user.email,
            ip_address=http_request.client.host if http_request.client else None,
            feature="semantic-models",
            action="SPARQL_QUERY",
            success=True,
            details={
                "query_length": len(sparql),
                "result_count": len(results),
                "status": "success"
            }
        )
        
        logger.info(
            f"SPARQL query executed successfully by '{current_user.email}': "
            f"{len(results)} results returned"
        )
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error executing SPARQL query: {e!s}", exc_info=True)
        # Audit log the failure
        audit_manager.log_action(
            db=db,
            username=current_user.email,
            ip_address=http_request.client.host if http_request.client else None,
            feature="semantic-models",
            action="SPARQL_QUERY_ERROR",
            success=False,
            details={"error": str(e), "query_length": len(sparql) if sparql else 0}
        )
        raise HTTPException(status_code=500, detail="Internal server error executing query")

"""Legacy Business Glossary endpoints removed during rename to Semantic Models."""

def register_routes(app):
    """Register routes with the app"""
    app.include_router(router)
    logger.info("Semantic models routes registered")