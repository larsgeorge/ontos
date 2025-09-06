from typing import List
from sqlalchemy.orm import Session

from src.db_models.semantic_links import EntitySemanticLinkDb
from src.models.semantic_links import EntitySemanticLink, EntitySemanticLinkCreate
from src.repositories.semantic_links_repository import entity_semantic_links_repo
from src.common.logging import get_logger

logger = get_logger(__name__)

class SemanticLinksManager:
    def __init__(self, db: Session):
        self._db = db

    def _to_api(self, db_obj: EntitySemanticLinkDb) -> EntitySemanticLink:
        return EntitySemanticLink(
            id=str(db_obj.id),
            entity_id=db_obj.entity_id,
            entity_type=db_obj.entity_type,  # type: ignore
            iri=db_obj.iri,
            label=db_obj.label,
        )

    def list_for_entity(self, entity_id: str, entity_type: str) -> List[EntitySemanticLink]:
        items = entity_semantic_links_repo.list_for_entity(self._db, entity_id, entity_type)
        return [self._to_api(it) for it in items]

    def list_for_iri(self, iri: str) -> List[EntitySemanticLink]:
        items = entity_semantic_links_repo.list_for_iri(self._db, iri)
        return [self._to_api(it) for it in items]

    def _link_exists(self, entity_id: str, entity_type: str, iri: str) -> bool:
        """Check if a semantic link already exists for this entity/IRI combination"""
        existing = entity_semantic_links_repo.get_by_entity_and_iri(self._db, entity_id, entity_type, iri)
        return existing is not None

    def add(self, payload: EntitySemanticLinkCreate, created_by: str | None) -> EntitySemanticLink:
        # Check if link already exists
        if self._link_exists(payload.entity_id, payload.entity_type, payload.iri):
            # Return existing link instead of creating a duplicate
            existing = entity_semantic_links_repo.get_by_entity_and_iri(
                self._db, payload.entity_id, payload.entity_type, payload.iri
            )
            logger.info(f"Semantic link already exists for {payload.entity_type}:{payload.entity_id} -> {payload.iri}")
            return self._to_api(existing)
        
        # Create new link
        db_obj = entity_semantic_links_repo.create(self._db, obj_in=payload)
        if created_by:
            db_obj.created_by = created_by
            self._db.add(db_obj)
        self._db.flush()
        self._db.refresh(db_obj)
        
        # Trigger KG refresh
        try:
            from src.controller.semantic_models_manager import SemanticModelsManager
            # Reuse same DB session to get manager from app.state is not available here; instantiate lightweight
            sm = SemanticModelsManager(db=self._db)
            sm.on_models_changed()
        except Exception as e:
            logger.warning(f"Failed to trigger KG refresh after link add: {e}")
        return self._to_api(db_obj)

    def remove(self, link_id: str) -> bool:
        removed = entity_semantic_links_repo.remove(self._db, id=link_id)
        try:
            from src.controller.semantic_models_manager import SemanticModelsManager
            sm = SemanticModelsManager(db=self._db)
            sm.on_models_changed()
        except Exception as e:
            logger.warning(f"Failed to trigger KG refresh after link removal: {e}")
        return removed is not None


