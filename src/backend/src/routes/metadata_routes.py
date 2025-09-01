from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body, Request
from fastapi.responses import StreamingResponse
from fastapi import Response
from sqlalchemy.orm import Session

from src.common.dependencies import DBSessionDep, CurrentUserDep
from src.common.features import FeatureAccessLevel
from src.common.authorization import PermissionChecker
from src.common.logging import get_logger
from src.controller.metadata_manager import MetadataManager
from src.common.manager_dependencies import get_metadata_manager
from src.models.metadata import (
    RichText, RichTextCreate, RichTextUpdate,
    Link, LinkCreate, LinkUpdate,
    Document, DocumentCreate,
)
from src.common.config import get_settings, Settings
from src.common.workspace_client import get_workspace_client
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import VolumeType

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["Metadata"])

FEATURE_ID = "data-domains"  # Use domain feature for now; can widen later


def _ensure_volume_and_path(ws: WorkspaceClient, settings: Settings, base_dir: str) -> str:
    # Unity Catalog volume name (catalog.schema.volume)
    volume_name = f"{settings.DATABRICKS_CATALOG}.{settings.DATABRICKS_SCHEMA}.{settings.DATABRICKS_VOLUME}"
    # Filesystem mount path for the volume
    volume_fs_base = f"/Volumes/{settings.DATABRICKS_CATALOG}/{settings.DATABRICKS_SCHEMA}/{settings.DATABRICKS_VOLUME}"
    try:
        try:
            # Ensure volume exists
            ws.volumes.read(volume_name)
        except Exception:
            ws.volumes.create(
                catalog_name=settings.DATABRICKS_CATALOG,
                schema_name=settings.DATABRICKS_SCHEMA,
                name=settings.DATABRICKS_VOLUME,
                volume_type=VolumeType.MANAGED,
            )
    except Exception as e:
        logger.error(f"Failed ensuring volume/path: {e!s}")
        raise
    # Return FS base path; caller appends base_dir/filename
    return volume_fs_base


# --- Rich Text ---
@router.post("/entities/{entity_type}/{entity_id}/rich-texts", response_model=RichText, status_code=status.HTTP_201_CREATED)
async def create_rich_text(
    entity_type: str,
    entity_id: str,
    payload: RichTextCreate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager: MetadataManager = Depends(get_metadata_manager),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_WRITE)),
):
    try:
        if payload.entity_type != entity_type or payload.entity_id != entity_id:
            raise HTTPException(status_code=400, detail="Entity path does not match body")
        return manager.create_rich_text(db, data=payload, user_email=current_user.email)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed creating rich text")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{entity_type}/{entity_id}/rich-texts", response_model=List[RichText])
async def list_rich_texts(
    entity_type: str,
    entity_id: str,
    db: DBSessionDep,
    manager: MetadataManager = Depends(get_metadata_manager),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_ONLY)),
):
    return manager.list_rich_texts(db, entity_type=entity_type, entity_id=entity_id)


@router.put("/rich-texts/{id}", response_model=RichText)
async def update_rich_text(
    id: str,
    payload: RichTextUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager: MetadataManager = Depends(get_metadata_manager),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_WRITE)),
):
    updated = manager.update_rich_text(db, id=id, data=payload, user_email=current_user.email)
    if not updated:
        raise HTTPException(status_code=404, detail="Rich text not found")
    return updated


@router.delete("/rich-texts/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rich_text(
    id: str,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager: MetadataManager = Depends(get_metadata_manager),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_WRITE)),
):
    ok = manager.delete_rich_text(db, id=id, user_email=current_user.email)
    if not ok:
        raise HTTPException(status_code=404, detail="Rich text not found")
    return


# --- Links ---
@router.post("/entities/{entity_type}/{entity_id}/links", response_model=Link, status_code=status.HTTP_201_CREATED)
async def create_link(
    entity_type: str,
    entity_id: str,
    payload: LinkCreate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager: MetadataManager = Depends(get_metadata_manager),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_WRITE)),
):
    try:
        if payload.entity_type != entity_type or payload.entity_id != entity_id:
            raise HTTPException(status_code=400, detail="Entity path does not match body")
        return manager.create_link(db, data=payload, user_email=current_user.email)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed creating link")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{entity_type}/{entity_id}/links", response_model=List[Link])
async def list_links(
    entity_type: str,
    entity_id: str,
    db: DBSessionDep,
    manager: MetadataManager = Depends(get_metadata_manager),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_ONLY)),
):
    return manager.list_links(db, entity_type=entity_type, entity_id=entity_id)


@router.put("/links/{id}", response_model=Link)
async def update_link(
    id: str,
    payload: LinkUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager: MetadataManager = Depends(get_metadata_manager),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_WRITE)),
):
    updated = manager.update_link(db, id=id, data=payload, user_email=current_user.email)
    if not updated:
        raise HTTPException(status_code=404, detail="Link not found")
    return updated


@router.delete("/links/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(
    id: str,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager: MetadataManager = Depends(get_metadata_manager),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_WRITE)),
):
    ok = manager.delete_link(db, id=id, user_email=current_user.email)
    if not ok:
        raise HTTPException(status_code=404, detail="Link not found")
    return


# --- Documents ---
@router.post("/entities/{entity_type}/{entity_id}/documents", response_model=Document, status_code=status.HTTP_201_CREATED)
async def upload_document(
    entity_type: str,
    entity_id: str,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    title: str = Body(...),
    short_description: Optional[str] = Body(None),
    file: UploadFile = File(...),
    request: Request = None,
    manager: MetadataManager = Depends(get_metadata_manager),
    settings: Settings = Depends(get_settings),
    ws: WorkspaceClient = Depends(get_workspace_client),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_WRITE)),
):
    try:
        # Ensure volume/path
        base_dir = f"uploads/{entity_type}/{entity_id}"
        volume_fs_base = _ensure_volume_and_path(ws, settings, base_dir)

        # Read file content
        content = await file.read()
        filename = file.filename or "document.bin"
        content_type = file.content_type
        size_bytes = len(content) if content else 0

        # Destination path
        dest_path = f"{volume_fs_base}/{base_dir}/{filename}"

        # Ensure directory exists in UC Volumes filesystem
        try:
            ws.files.create_directory(f"{volume_fs_base}/{base_dir}")
        except Exception:
            pass

        # Upload file bytes to the UC Volume path (path, file_bytes, overwrite)
        ws.files.upload(dest_path, content)

        payload = DocumentCreate(
            entity_type=entity_type,
            entity_id=entity_id,
            title=title,
            short_description=short_description,
        )
        return manager.create_document_record(
            db,
            data=payload,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_path=dest_path,
            user_email=current_user.email,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed uploading document")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{entity_type}/{entity_id}/documents", response_model=List[Document])
async def list_documents(
    entity_type: str,
    entity_id: str,
    db: DBSessionDep,
    manager: MetadataManager = Depends(get_metadata_manager),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_ONLY)),
):
    return manager.list_documents(db, entity_type=entity_type, entity_id=entity_id)


@router.get("/documents/{id}", response_model=Document)
async def get_document(
    id: str,
    db: DBSessionDep,
    manager: MetadataManager = Depends(get_metadata_manager),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_ONLY)),
):
    doc = manager.get_document(db, id=id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/documents/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    id: str,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager: MetadataManager = Depends(get_metadata_manager),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_WRITE)),
):
    ok = manager.delete_document(db, id=id, user_email=current_user.email)
    if not ok:
        raise HTTPException(status_code=404, detail="Document not found")
    return


def register_routes(app):
    app.include_router(router)
    logger.info("Metadata routes registered with prefix /api")


@router.get("/documents/{id}/content")
async def get_document_content(
    id: str,
    db: DBSessionDep,
    manager: MetadataManager = Depends(get_metadata_manager),
    ws: WorkspaceClient = Depends(get_workspace_client),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_ONLY)),
):
    doc = manager.get_document(db, id=id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        # Download file from UC Volumes. SDK returns a DownloadResponse with a generator method `.contents()`.
        downloaded = ws.files.download(doc.storage_path)

        # Log shape once to aid debugging if needed
        try:
            logger.debug(f"DownloadResponse type={type(downloaded)} attrs={dir(downloaded)}")
        except Exception:
            pass

        media_type = doc.content_type or "application/octet-stream"
        headers = {"Content-Disposition": f"inline; filename=\"{doc.original_filename}\""}

        # Preferred path: DownloadResponse.contents is a BinaryIO stream we can read in chunks
        try:
            stream = getattr(downloaded, "contents", None)
            if stream is not None and hasattr(stream, "read"):
                def chunk_iter():
                    while True:
                        chunk = stream.read(1024 * 1024)
                        if not chunk:
                            break
                        yield chunk
                media_type = doc.content_type or getattr(downloaded, "content_type", None) or "application/octet-stream"
                headers = {"Content-Disposition": f"inline; filename=\"{doc.original_filename}\""}
                return StreamingResponse(chunk_iter(), media_type=media_type, headers=headers)
        except Exception:
            pass

        # Fallbacks
        media_type = doc.content_type or getattr(downloaded, "content_type", None) or "application/octet-stream"
        headers = {"Content-Disposition": f"inline; filename=\"{doc.original_filename}\""}

        if hasattr(downloaded, "read"):
            try:
                data = downloaded.read()
                return Response(content=data, media_type=media_type, headers=headers)
            except Exception:
                pass

        if isinstance(downloaded, (bytes, bytearray)):
            return Response(content=bytes(downloaded), media_type=media_type, headers=headers)

        # If all else fails, error with clear message
        raise HTTPException(status_code=500, detail="Unsupported Databricks download response; missing BinaryIO 'contents'")
    except Exception as e:
        logger.exception("Failed streaming document content")
        raise HTTPException(status_code=500, detail=str(e))