from typing import Any, Dict, Optional, List, Union

from sqlalchemy.orm import Session, selectinload

from api.common.repository import CRUDBase
from api.db_models.data_contracts import (
    DataContractDb,
    DataContractTagDb,
    DataContractServerDb,
    DataContractServerPropertyDb,
    DataContractRoleDb,
    DataContractRolePropertyDb,
    DataContractTeamDb,
    DataContractSupportDb,
    DataContractPricingDb,
    DataContractAuthorityDb,
    DataContractCustomPropertyDb,
    DataContractSlaPropertyDb,
    SchemaObjectDb,
    SchemaPropertyDb,
    DataQualityCheckDb,
    DataContractCommentDb,
)
from api.common.logging import get_logger

logger = get_logger(__name__)


class DataContractRepository(CRUDBase[DataContractDb, Dict[str, Any], Union[Dict[str, Any], DataContractDb]]):
    def __init__(self):
        super().__init__(DataContractDb)

    def get_with_all(self, db: Session, *, id: str) -> Optional[DataContractDb]:
        try:
            return (
                db.query(self.model)
                .options(
                    selectinload(self.model.tags),
                    selectinload(self.model.servers).selectinload(DataContractServerDb.properties),
                    selectinload(self.model.roles).selectinload(DataContractRoleDb.custom_properties),
                    selectinload(self.model.team),
                    selectinload(self.model.support),
                    selectinload(self.model.pricing),
                    selectinload(self.model.authoritative_defs),
                    selectinload(self.model.custom_properties),
                    selectinload(self.model.sla_properties),
                    selectinload(self.model.schema_objects)
                        .selectinload(SchemaObjectDb.properties),
                    selectinload(self.model.schema_objects)
                        .selectinload(SchemaObjectDb.quality_checks),
                    selectinload(self.model.comments),
                )
                .filter(self.model.id == id)
                .first()
            )
        except Exception as e:
            logger.error(f"Error fetching DataContractDb with all relations for id {id}: {e}", exc_info=True)
            db.rollback()
            raise

    # Override create to accept either a dict payload or a pre-built SA model
    def create(self, db: Session, *, obj_in: Union[Dict[str, Any], DataContractDb]) -> DataContractDb:
        try:
            if isinstance(obj_in, DataContractDb):
                db.add(obj_in)
                db.flush()
                db.refresh(obj_in)
                return obj_in
            payload: Dict[str, Any] = dict(obj_in)
            db_obj = self.model(**payload)
            db.add(db_obj)
            db.flush()
            db.refresh(db_obj)
            return db_obj
        except Exception as e:
            logger.error(f"Error creating DataContractDb: {e}", exc_info=True)
            db.rollback()
            raise


# Singleton-like access if desired
data_contract_repo = DataContractRepository()


