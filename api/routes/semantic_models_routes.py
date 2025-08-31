import json
from typing import List, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body, status, Request
from sqlalchemy.orm import Session

from api.common.dependencies import (
    DBSessionDep,
    AuditCurrentUserDep,
)
from api.common.manager_dependencies import get_semantic_models_manager
from api.controller.semantic_models_manager import SemanticModelsManager
from api.models.semantic_models import SemanticModel, SemanticModelUpdate, SemanticModelPreview
from api.common.logging import get_logger


logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["semantic-models"])

SEMANTIC_MODELS_FEATURE_ID = "settings"


def _detect_format(filename: str, content_type: str | None) -> str:
    # Basic detection for RDFS (rdf/xml) and SKOS (turtle, rdf/xml)
    lower = (filename or "").lower()
    if lower.endswith(".ttl") or (content_type and "turtle" in content_type):
        return "skos"
    # Default assume rdfs for rdf+xml or xml
    return "rdfs"


@router.get("/semantic-models", response_model=List[SemanticModel])
async def list_models(
    manager: SemanticModelsManager = Depends(get_semantic_models_manager),
):
    try:
        return manager.list()
    except Exception as e:
        logger.error(f"Failed listing semantic models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/semantic-models/prefix", response_model=List[dict])
async def prefix_search(
    q: str,
    limit: int = 20,
    manager: SemanticModelsManager = Depends(get_semantic_models_manager),
):
    if not q:
        return []
    try:
        return manager.prefix_search(q, limit=limit)
    except Exception as e:
        logger.error(f"Prefix search failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/semantic-models/neighbors", response_model=List[dict])
async def get_neighbors(
    iri: str,
    limit: int = 200,
    manager: SemanticModelsManager = Depends(get_semantic_models_manager),
):
    if not iri:
        raise HTTPException(status_code=400, detail="Missing 'iri' query param")
    try:
        return manager.neighbors(iri, limit=limit)
    except Exception as e:
        logger.error(f"Neighbors fetch failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/semantic-models/{model_id}", response_model=SemanticModel)
async def get_model(
    model_id: str,
    manager: SemanticModelsManager = Depends(get_semantic_models_manager),
):
    m = manager.get(model_id)
    if not m:
        raise HTTPException(status_code=404, detail="Semantic model not found")
    return m


@router.post("/semantic-models/upload", response_model=SemanticModel, status_code=status.HTTP_201_CREATED)
async def upload_model(
    request: Request,
    db: DBSessionDep,
    current_user: AuditCurrentUserDep,
    file: UploadFile = File(...),
    manager: SemanticModelsManager = Depends(get_semantic_models_manager),
):
    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        filename = file.filename or "uploaded.rdf"
        content_type = file.content_type
        fmt = _detect_format(filename, content_type)

        create_data = {
            "name": filename,
            "format": fmt,
            "content_text": contents.decode("utf-8", errors="ignore"),
            "original_filename": filename,
            "content_type": content_type,
            "size_bytes": len(contents),
            "enabled": True,
        }

        from api.models.semantic_models import SemanticModelCreate

        created = manager.create(SemanticModelCreate(**create_data), created_by=current_user.username if current_user else None)
        db.commit()
        manager.on_models_changed()
        return created
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error uploading semantic model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/semantic-models/{model_id}", response_model=SemanticModel)
async def update_model(
    model_id: str,
    db: DBSessionDep,
    current_user: AuditCurrentUserDep,
    payload: SemanticModelUpdate = Body(...),
    manager: SemanticModelsManager = Depends(get_semantic_models_manager),
):
    updated = manager.update(model_id, payload, updated_by=current_user.username if current_user else None)
    if not updated:
        raise HTTPException(status_code=404, detail="Semantic model not found")
    db.commit()
    manager.on_models_changed()
    return updated


@router.post("/semantic-models/{model_id}/upload", response_model=SemanticModel)
async def replace_model_content(
    model_id: str,
    db: DBSessionDep,
    current_user: AuditCurrentUserDep,
    file: UploadFile = File(...),
    manager: SemanticModelsManager = Depends(get_semantic_models_manager),
):
    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        updated = manager.replace_content(
            model_id=model_id,
            content_text=contents.decode("utf-8", errors="ignore"),
            original_filename=file.filename,
            content_type=file.content_type,
            size_bytes=len(contents),
            updated_by=current_user.username if current_user else None,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Semantic model not found")
        db.commit()
        manager.on_models_changed()
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error replacing semantic model content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/semantic-models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    model_id: str,
    db: DBSessionDep,
    manager: SemanticModelsManager = Depends(get_semantic_models_manager),
):
    deleted = manager.delete(model_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Semantic model not found")
    db.commit()
    manager.on_models_changed()
    return None


@router.get("/semantic-models/{model_id}/preview", response_model=SemanticModelPreview)
async def preview_model(
    model_id: str,
    manager: SemanticModelsManager = Depends(get_semantic_models_manager),
):
    p = manager.preview(model_id)
    if not p:
        raise HTTPException(status_code=404, detail="Semantic model not found")
    return p


@router.post("/semantic-models/query", response_model=List[dict])
async def query_graph(
    body: dict = Body(...),
    manager: SemanticModelsManager = Depends(get_semantic_models_manager),
):
    sparql = body.get("sparql")
    if not sparql or not isinstance(sparql, str):
        raise HTTPException(status_code=400, detail="Missing 'sparql' string in body")
    try:
        return manager.query(sparql)
    except Exception as e:
        logger.error(f"SPARQL query failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))




def register_routes(app):
    app.include_router(router)
    logger.info("Semantic models routes registered")
    # After routes are registered, rebuild graph once
    try:
        # Access manager via app.state
        manager = getattr(app.state, 'semantic_models_manager', None)
        if manager:
            manager.on_models_changed()
    except Exception:
        pass


