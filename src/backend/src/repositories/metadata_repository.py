from typing import List, Optional, Union, Dict, Any, Type

from sqlalchemy.orm import Session

from src.common.repository import CRUDBase
from src.db_models.metadata import RichTextMetadataDb, LinkMetadataDb, DocumentMetadataDb
from src.models.metadata import (
    RichTextCreate, RichTextUpdate,
    LinkCreate, LinkUpdate,
    DocumentCreate,
)


class RichTextRepository(CRUDBase[RichTextMetadataDb, RichTextCreate, RichTextUpdate]):
    def list_for_entity(self, db: Session, *, entity_type: str, entity_id: str) -> List[RichTextMetadataDb]:
        return (
            db.query(RichTextMetadataDb)
            .filter(RichTextMetadataDb.entity_type == entity_type, RichTextMetadataDb.entity_id == entity_id)
            .order_by(RichTextMetadataDb.created_at.desc())
            .all()
        )


class LinkRepository(CRUDBase[LinkMetadataDb, LinkCreate, LinkUpdate]):
    def list_for_entity(self, db: Session, *, entity_type: str, entity_id: str) -> List[LinkMetadataDb]:
        return (
            db.query(LinkMetadataDb)
            .filter(LinkMetadataDb.entity_type == entity_type, LinkMetadataDb.entity_id == entity_id)
            .order_by(LinkMetadataDb.created_at.desc())
            .all()
        )


class DocumentRepository(CRUDBase[DocumentMetadataDb, DocumentCreate, DocumentCreate]):
    def list_for_entity(self, db: Session, *, entity_type: str, entity_id: str) -> List[DocumentMetadataDb]:
        return (
            db.query(DocumentMetadataDb)
            .filter(DocumentMetadataDb.entity_type == entity_type, DocumentMetadataDb.entity_id == entity_id)
            .order_by(DocumentMetadataDb.created_at.desc())
            .all()
        )


# Instantiate repositories
rich_text_repo = RichTextRepository(RichTextMetadataDb)
link_repo = LinkRepository(LinkMetadataDb)
document_repo = DocumentRepository(DocumentMetadataDb)


