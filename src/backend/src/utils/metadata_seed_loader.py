import os
import mimetypes
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from sqlalchemy.orm import Session

from src.common.logging import get_logger
from src.common.config import Settings
from src.common.workspace_client import get_workspace_client
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import VolumeType

from src.controller.metadata_manager import MetadataManager
from src.models.metadata import RichTextCreate, LinkCreate, DocumentCreate
from src.common.file_security import sanitize_filename

logger = get_logger(__name__)


def _ensure_volume_and_path(ws: WorkspaceClient, settings: Settings, base_dir: str) -> str:
    """Ensure the configured UC Volume exists and return its filesystem base path."""
    volume_name = f"{settings.DATABRICKS_CATALOG}.{settings.DATABRICKS_SCHEMA}.{settings.DATABRICKS_VOLUME}"
    volume_fs_base = f"/Volumes/{settings.DATABRICKS_CATALOG}/{settings.DATABRICKS_SCHEMA}/{settings.DATABRICKS_VOLUME}"
    try:
        try:
            ws.volumes.read(volume_name)
        except Exception:
            ws.volumes.create(
                catalog_name=settings.DATABRICKS_CATALOG,
                schema_name=settings.DATABRICKS_SCHEMA,
                name=settings.DATABRICKS_VOLUME,
                volume_type=VolumeType.MANAGED,
            )
    except Exception as e:
        logger.error(f"Failed ensuring UC Volume: {e!s}")
        raise
    return volume_fs_base


def _resolve_entity_id(db: Session, entity_type: str, entity_name: str) -> Optional[str]:
    """Resolve an entity UUID by human-readable name/title based on type."""
    try:
        if entity_type == "data_domain":
            from src.db_models.data_domains import DataDomain
            obj = db.query(DataDomain).filter(DataDomain.name == entity_name).first()
            return str(obj.id) if obj else None
        if entity_type == "data_product":
            from src.db_models.data_products import DataProductDb
            # ODPS v1.0.0: Query data products by name field (not info.title)
            product = db.query(DataProductDb).filter(DataProductDb.name == entity_name).first()
            return str(product.id) if product else None
        if entity_type == "data_contract":
            from src.db_models.data_contracts import DataContractDb
            obj = db.query(DataContractDb).filter(DataContractDb.name == entity_name).first()
            return str(obj.id) if obj else None
    except Exception as e:
        logger.warning(f"Failed resolving entity id for {entity_type}:{entity_name}: {e!s}")
        return None
    return None


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _list_existing(metadata_manager: MetadataManager, db: Session, entity_type: str, entity_id: str):
    notes = metadata_manager.list_rich_texts(db, entity_type=entity_type, entity_id=entity_id)
    links = metadata_manager.list_links(db, entity_type=entity_type, entity_id=entity_id)
    docs = metadata_manager.list_documents(db, entity_type=entity_type, entity_id=entity_id)
    return notes, links, docs


def _upload_document(
    db: Session,
    ws: WorkspaceClient,
    settings: Settings,
    metadata_manager: MetadataManager,
    *,
    entity_type: str,
    entity_id: str,
    title: str,
    short_description: Optional[str],
    source_path: Path,
    original_filename: str,
    user_email: str,
) -> bool:
    try:
        if not source_path.exists():
            logger.warning(f"Document source not found, skipping: {source_path}")
            return False

        # SECURITY: Sanitize filename to prevent path traversal
        safe_filename = sanitize_filename(original_filename, default="document.bin")

        base_dir = f"uploads/{entity_type}/{entity_id}"
        volume_fs_base = _ensure_volume_and_path(ws, settings, base_dir)

        with source_path.open("rb") as f:
            content = f.read()

        dest_dir = f"{volume_fs_base}/{base_dir}"
        dest_path = f"{dest_dir}/{safe_filename}"

        try:
            ws.files.create_directory(dest_dir)
        except Exception:
            pass

        ws.files.upload(dest_path, BytesIO(content))

        # Infer content type from sanitized filename
        guessed_type, _ = mimetypes.guess_type(safe_filename)

        payload = DocumentCreate(
            entity_type=entity_type,
            entity_id=entity_id,
            title=title,
            short_description=short_description,
        )
        metadata_manager.create_document_record(
            db,
            data=payload,
            filename=safe_filename,
            content_type=guessed_type or ("image/svg+xml" if safe_filename.lower().endswith(".svg") else None),
            size_bytes=len(content) if content else 0,
            storage_path=dest_path,
            user_email=user_email,
        )
        return True
    except Exception as e:
        logger.error(f"Failed uploading document {safe_filename} for {entity_type}:{entity_id}: {e!s}")
        return False


def seed_metadata_from_yaml(db: Session, settings: Settings, yaml_path: Path, *, user_email: str = "system@startup.ucapp") -> None:
    """Seed metadata (notes, links, documents) from a YAML file.

    The YAML structure is expected as:
    metadata:
      - entity_type: data_domain|data_product|data_contract
        entity_name: <string>
        notes: [ { title, short_description?, content_markdown } ]
        links: [ { title, url, short_description? } ]
        documents: [ { title, original_filename, path, short_description? } ]
        output_port_notes: [ { port_name, title, short_description?, content_markdown } ]  # Only for data_product
    """
    if not yaml_path.exists():
        logger.info(f"Metadata seed YAML not found: {yaml_path}")
        return

    config = _load_yaml(yaml_path)
    items: List[Dict[str, Any]] = config.get("metadata", []) or []
    if not items:
        logger.info("No 'metadata' entries found in YAML; skipping.")
        return

    # Workspace client for document upload
    ws = get_workspace_client(settings=settings)
    manager = MetadataManager()

    for item in items:
        try:
            entity_type = item.get("entity_type")
            entity_name = item.get("entity_name")
            if not entity_type or not entity_name:
                logger.warning(f"Skipping invalid metadata block without entity_type/name: {item}")
                continue

            entity_id = _resolve_entity_id(db, entity_type, entity_name)
            if not entity_id:
                logger.warning(f"Target entity not found for {entity_type}:{entity_name}; skipping block")
                continue

            existing_notes, existing_links, existing_docs = _list_existing(manager, db, entity_type, entity_id)
            notes_by_title = {n.title: n for n in existing_notes}
            existing_note_titles = set(notes_by_title.keys())
            existing_link_keys = {(l.title, l.url) for l in existing_links}
            existing_doc_filenames = {d.original_filename for d in existing_docs}

            # Notes
            for note in item.get("notes", []) or []:
                title = note.get("title")
                if not title:
                    continue
                short_desc = note.get("short_description")
                content_md = note.get("content_markdown", "")
                if title in notes_by_title:
                    # Update if changed
                    existing = notes_by_title[title]
                    if (existing.short_description or "") != (short_desc or "") or (existing.content_markdown or "") != (content_md or ""):
                        manager.update_rich_text(
                            db,
                            id=str(existing.id),
                            data={"short_description": short_desc, "content_markdown": content_md},
                            user_email=user_email,
                        )
                else:
                    data = RichTextCreate(
                        entity_type=entity_type,
                        entity_id=entity_id,
                        title=title,
                        short_description=short_desc,
                        content_markdown=content_md,
                    )
                    manager.create_rich_text(db, data=data, user_email=user_email)

            # Output port notes (attach as product notes with clear headings)
            if entity_type == "data_product":
                for pnote in item.get("output_port_notes", []) or []:
                    title = pnote.get("title") or f"Output: {pnote.get('port_name','')}".strip()
                    if not title:
                        continue
                    short_desc = pnote.get("short_description")
                    content_md = pnote.get("content_markdown", "")
                    if title in notes_by_title:
                        existing = notes_by_title[title]
                        if (existing.short_description or "") != (short_desc or "") or (existing.content_markdown or "") != (content_md or ""):
                            manager.update_rich_text(
                                db,
                                id=str(existing.id),
                                data={"short_description": short_desc, "content_markdown": content_md},
                                user_email=user_email,
                            )
                    else:
                        data = RichTextCreate(
                            entity_type=entity_type,
                            entity_id=entity_id,
                            title=title,
                            short_description=short_desc,
                            content_markdown=content_md,
                        )
                        manager.create_rich_text(db, data=data, user_email=user_email)

            # Links
            for link in item.get("links", []) or []:
                title = link.get("title")
                url = link.get("url")
                if not title or not url or (title, url) in existing_link_keys:
                    continue
                data = LinkCreate(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    title=title,
                    url=url,
                    short_description=link.get("short_description"),
                )
                manager.create_link(db, data=data, user_email=user_email)

            # Documents
            for doc in item.get("documents", []) or []:
                original_filename = doc.get("original_filename")
                title = doc.get("title") or original_filename
                if not original_filename or not title or original_filename in existing_doc_filenames:
                    continue
                src_rel = doc.get("path")
                if not src_rel:
                    logger.warning(f"Missing 'path' for document {original_filename}; skipping")
                    continue
                source_path = (yaml_path.parent / src_rel).resolve()
                _upload_document(
                    db,
                    ws,
                    settings,
                    manager,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    title=title,
                    short_description=doc.get("short_description"),
                    source_path=source_path,
                    original_filename=original_filename,
                    user_email=user_email,
                )

            logger.info(f"Seeded metadata for {entity_type}:{entity_name}")
        except Exception as e:
            logger.error(f"Error seeding metadata block {item}: {e!s}")


