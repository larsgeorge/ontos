from typing import List, Optional

from sqlalchemy.orm import Session
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import VolumeType

from src.common.logging import get_logger
from src.common.config import Settings
from src.models.metadata import (
    RichText, RichTextCreate, RichTextUpdate,
    Link, LinkCreate, LinkUpdate,
    Document, DocumentCreate,
)
from src.repositories.metadata_repository import (
    rich_text_repo, link_repo, document_repo,
    RichTextRepository, LinkRepository, DocumentRepository,
)
from src.repositories.change_log_repository import change_log_repo
from src.db_models.change_log import ChangeLogDb

logger = get_logger(__name__)


class MetadataManager:
    def __init__(
        self,
        rich_text_repository: RichTextRepository = rich_text_repo,
        link_repository: LinkRepository = link_repo,
        document_repository: DocumentRepository = document_repo,
    ):
        self._rich_text_repo = rich_text_repository
        self._link_repo = link_repository
        self._document_repo = document_repository

    def _log_change(self, db: Session, *, entity_type: str, entity_id: str, action: str, username: Optional[str], details_json: Optional[str] = None) -> None:
        entry = ChangeLogDb(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            username=username,
            details_json=details_json,
        )
        db.add(entry)
        db.commit()

    # --- Volume Management ---
    
    def ensure_volume_path(self, ws: WorkspaceClient, settings: Settings, base_dir: str) -> str:
        """Ensure Unity Catalog volume exists and return filesystem path.
        
        Args:
            ws: WorkspaceClient for SDK calls
            settings: Application settings with catalog/schema/volume config
            base_dir: Base directory name within volume (not used in path construction)
            
        Returns:
            Filesystem mount path for the volume (e.g., /Volumes/catalog/schema/volume)
            
        Raises:
            Exception: If volume creation or access fails
        """
        # Unity Catalog volume name (catalog.schema.volume)
        volume_name = f"{settings.DATABRICKS_CATALOG}.{settings.DATABRICKS_SCHEMA}.{settings.DATABRICKS_VOLUME}"
        # Filesystem mount path for the volume
        volume_fs_base = f"/Volumes/{settings.DATABRICKS_CATALOG}/{settings.DATABRICKS_SCHEMA}/{settings.DATABRICKS_VOLUME}"
        
        try:
            try:
                # Ensure volume exists
                ws.volumes.read(volume_name)
                logger.debug(f"Volume {volume_name} already exists")
            except Exception as e:
                logger.info(f"Creating volume {volume_name}")
                ws.volumes.create(
                    catalog_name=settings.DATABRICKS_CATALOG,
                    schema_name=settings.DATABRICKS_SCHEMA,
                    name=settings.DATABRICKS_VOLUME,
                    volume_type=VolumeType.MANAGED,
                )
                logger.info(f"Successfully created volume {volume_name}")
        except Exception as e:
            logger.error(f"Failed ensuring volume/path {volume_name}: {e!s}")
            raise
        
        # Return FS base path; caller appends base_dir/filename
        return volume_fs_base

    # --- Rich Text ---
    def create_rich_text(self, db: Session, *, data: RichTextCreate, user_email: Optional[str]) -> RichText:
        db_obj = self._rich_text_repo.create(db, obj_in=data)
        db.commit()
        db.refresh(db_obj)
        self._log_change(db, entity_type=f"{data.entity_type}:rich_text", entity_id=data.entity_id, action="CREATE", username=user_email)
        return RichText.from_orm(db_obj)

    def list_rich_texts(self, db: Session, *, entity_type: str, entity_id: str) -> List[RichText]:
        rows = self._rich_text_repo.list_for_entity(db, entity_type=entity_type, entity_id=entity_id)
        return [RichText.from_orm(r) for r in rows]

    def update_rich_text(self, db: Session, *, id: str, data: RichTextUpdate, user_email: Optional[str]) -> Optional[RichText]:
        db_obj = self._rich_text_repo.get(db, id=id)
        if not db_obj:
            return None
        updated = self._rich_text_repo.update(db, db_obj=db_obj, obj_in=data)
        db.commit()
        db.refresh(updated)
        self._log_change(db, entity_type=f"{updated.entity_type}:rich_text", entity_id=updated.entity_id, action="UPDATE", username=user_email)
        return RichText.from_orm(updated)

    def delete_rich_text(self, db: Session, *, id: str, user_email: Optional[str]) -> bool:
        db_obj = self._rich_text_repo.get(db, id=id)
        if not db_obj:
            return False
        entity_type, entity_id = db_obj.entity_type, db_obj.entity_id
        removed = self._rich_text_repo.remove(db, id=id)
        if removed:
            db.commit()
            self._log_change(db, entity_type=f"{entity_type}:rich_text", entity_id=entity_id, action="DELETE", username=user_email)
            return True
        return False

    # --- Link ---
    def create_link(self, db: Session, *, data: LinkCreate, user_email: Optional[str]) -> Link:
        db_obj = self._link_repo.create(db, obj_in=data)
        db.commit()
        db.refresh(db_obj)
        self._log_change(db, entity_type=f"{data.entity_type}:link", entity_id=data.entity_id, action="CREATE", username=user_email)
        return Link.from_orm(db_obj)

    def list_links(self, db: Session, *, entity_type: str, entity_id: str) -> List[Link]:
        rows = self._link_repo.list_for_entity(db, entity_type=entity_type, entity_id=entity_id)
        return [Link.from_orm(r) for r in rows]

    def update_link(self, db: Session, *, id: str, data: LinkUpdate, user_email: Optional[str]) -> Optional[Link]:
        db_obj = self._link_repo.get(db, id=id)
        if not db_obj:
            return None
        updated = self._link_repo.update(db, db_obj=db_obj, obj_in=data)
        db.commit()
        db.refresh(updated)
        self._log_change(db, entity_type=f"{updated.entity_type}:link", entity_id=updated.entity_id, action="UPDATE", username=user_email)
        return Link.from_orm(updated)

    def delete_link(self, db: Session, *, id: str, user_email: Optional[str]) -> bool:
        db_obj = self._link_repo.get(db, id=id)
        if not db_obj:
            return False
        entity_type, entity_id = db_obj.entity_type, db_obj.entity_id
        removed = self._link_repo.remove(db, id=id)
        if removed:
            db.commit()
            self._log_change(db, entity_type=f"{entity_type}:link", entity_id=entity_id, action="DELETE", username=user_email)
            return True
        return False

    # --- Document ---
    def create_document_record(self, db: Session, *, data: DocumentCreate, filename: str, content_type: Optional[str], size_bytes: Optional[int], storage_path: str, user_email: Optional[str]) -> Document:
        # DocumentCreate has base fields; other metadata supplied by upload logic
        from src.db_models.metadata import DocumentMetadataDb
        db_obj = DocumentMetadataDb(
            entity_id=data.entity_id,
            entity_type=data.entity_type,
            title=data.title,
            short_description=data.short_description,
            original_filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_path=storage_path,
            created_by=user_email,
            updated_by=user_email,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        self._log_change(db, entity_type=f"{data.entity_type}:document", entity_id=data.entity_id, action="CREATE", username=user_email)
        return Document.from_orm(db_obj)

    def list_documents(self, db: Session, *, entity_type: str, entity_id: str) -> List[Document]:
        rows = self._document_repo.list_for_entity(db, entity_type=entity_type, entity_id=entity_id)
        return [Document.from_orm(r) for r in rows]

    def delete_document(self, db: Session, *, id: str, user_email: Optional[str]) -> bool:
        db_obj = self._document_repo.get(db, id=id)
        if not db_obj:
            return False
        entity_type, entity_id = db_obj.entity_type, db_obj.entity_id
        removed = self._document_repo.remove(db, id=id)
        if removed:
            db.commit()
            self._log_change(db, entity_type=f"{entity_type}:document", entity_id=entity_id, action="DELETE", username=user_email)
            return True
        return False

    def get_document(self, db: Session, *, id: str) -> Optional[Document]:
        db_obj = self._document_repo.get(db, id=id)
        if not db_obj:
            return None
        return Document.from_orm(db_obj)