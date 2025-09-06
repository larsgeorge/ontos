from typing import List
from sqlalchemy.orm import Session

from src.common.repository import CRUDBase
from src.db_models.semantic_links import EntitySemanticLinkDb
from src.models.semantic_links import EntitySemanticLinkCreate


class EntitySemanticLinksRepository(CRUDBase[EntitySemanticLinkDb, EntitySemanticLinkCreate, dict]):
    def list_for_entity(self, db: Session, entity_id: str, entity_type: str) -> List[EntitySemanticLinkDb]:
        return db.query(self.model).filter(
            self.model.entity_id == entity_id,
            self.model.entity_type == entity_type
        ).all()

    def list_for_iri(self, db: Session, iri: str) -> List[EntitySemanticLinkDb]:
        return db.query(self.model).filter(self.model.iri == iri).all()

    def get_by_entity_and_iri(self, db: Session, entity_id: str, entity_type: str, iri: str) -> EntitySemanticLinkDb | None:
        return db.query(self.model).filter(
            self.model.entity_id == entity_id,
            self.model.entity_type == entity_type,
            self.model.iri == iri
        ).first()

    def list_all(self, db: Session) -> List[EntitySemanticLinkDb]:
        return db.query(self.model).all()


entity_semantic_links_repo = EntitySemanticLinksRepository(EntitySemanticLinkDb)


