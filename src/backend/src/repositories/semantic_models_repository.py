from typing import Optional
from sqlalchemy.orm import Session

from src.common.repository import CRUDBase
from src.db_models.semantic_models import SemanticModelDb
from src.models.semantic_models import SemanticModelCreate, SemanticModelUpdate


class SemanticModelsRepository(CRUDBase[SemanticModelDb, SemanticModelCreate, SemanticModelUpdate]):
    def get_by_name(self, db: Session, name: str) -> Optional[SemanticModelDb]:
        return db.query(self.model).filter(self.model.name == name).first()


semantic_models_repo = SemanticModelsRepository(SemanticModelDb)


