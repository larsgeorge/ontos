from typing import Any, Dict, Optional, List, Union

from sqlalchemy.orm import Session, selectinload

from src.common.repository import CRUDBase
from src.db_models.data_contracts import (
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
from src.common.logging import get_logger

logger = get_logger(__name__)


class DataContractRepository(CRUDBase[DataContractDb, Dict[str, Any], Union[Dict[str, Any], DataContractDb]]):
    def __init__(self):
        super().__init__(DataContractDb)

    def get_by_name(self, db: Session, *, name: str) -> Optional[DataContractDb]:
        """Get data contract by name."""
        try:
            return db.query(self.model).filter(self.model.name == name).first()
        except Exception as e:
            logger.error(f"Error fetching DataContractDb by name {name}: {e}", exc_info=True)
            db.rollback()
            raise

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

    # --- Project Filtering Methods ---
    def get_by_project(self, db: Session, project_id: str, skip: int = 0, limit: int = 100) -> List[DataContractDb]:
        """Get data contracts filtered by project_id."""
        logger.debug(f"Fetching DataContracts for project {project_id} with skip: {skip}, limit: {limit}")
        try:
            return (
                db.query(self.model)
                .filter(self.model.project_id == project_id)
                .offset(skip)
                .limit(limit)
                .all()
            )
        except Exception as e:
            logger.error(f"Database error fetching DataContracts by project {project_id}: {e}", exc_info=True)
            db.rollback()
            raise

    def get_without_project(self, db: Session, skip: int = 0, limit: int = 100) -> List[DataContractDb]:
        """Get data contracts that are not assigned to any project."""
        logger.debug(f"Fetching DataContracts without project assignment with skip: {skip}, limit: {limit}")
        try:
            return (
                db.query(self.model)
                .filter(self.model.project_id.is_(None))
                .offset(skip)
                .limit(limit)
                .all()
            )
        except Exception as e:
            logger.error(f"Database error fetching DataContracts without project: {e}", exc_info=True)
            db.rollback()
            raise

    def count_by_project(self, db: Session, project_id: str) -> int:
        """Count data contracts for a specific project."""
        logger.debug(f"Counting DataContracts for project {project_id}")
        try:
            return db.query(self.model).filter(self.model.project_id == project_id).count()
        except Exception as e:
            logger.error(f"Database error counting DataContracts by project {project_id}: {e}", exc_info=True)
            db.rollback()
            raise


# Singleton-like access if desired
data_contract_repo = DataContractRepository()


# ===== Tag Repository Methods =====
class ContractTagRepository(CRUDBase[DataContractTagDb, Dict[str, Any], DataContractTagDb]):
    def __init__(self):
        super().__init__(DataContractTagDb)

    def get_by_contract(self, db: Session, *, contract_id: str) -> List[DataContractTagDb]:
        """Get all tags for a specific contract."""
        try:
            return db.query(self.model).filter(self.model.contract_id == contract_id).all()
        except Exception as e:
            logger.error(f"Error fetching tags for contract {contract_id}: {e}", exc_info=True)
            db.rollback()
            raise

    def get_by_name(self, db: Session, *, contract_id: str, name: str) -> Optional[DataContractTagDb]:
        """Get a tag by contract_id and name (to prevent duplicates)."""
        try:
            return db.query(self.model).filter(
                self.model.contract_id == contract_id,
                self.model.name == name
            ).first()
        except Exception as e:
            logger.error(f"Error fetching tag {name} for contract {contract_id}: {e}", exc_info=True)
            db.rollback()
            raise

    def create_tag(self, db: Session, *, contract_id: str, name: str) -> DataContractTagDb:
        """Create a new tag for a contract."""
        try:
            # Check for duplicate
            existing = self.get_by_name(db=db, contract_id=contract_id, name=name)
            if existing:
                raise ValueError(f"Tag '{name}' already exists for this contract")

            tag = DataContractTagDb(contract_id=contract_id, name=name)
            db.add(tag)
            db.flush()
            db.refresh(tag)
            return tag
        except Exception as e:
            logger.error(f"Error creating tag for contract {contract_id}: {e}", exc_info=True)
            db.rollback()
            raise

    def update_tag(self, db: Session, *, tag_id: str, name: str) -> Optional[DataContractTagDb]:
        """Update a tag's name."""
        try:
            tag = db.query(self.model).filter(self.model.id == tag_id).first()
            if not tag:
                return None

            # Check for duplicate name in same contract
            existing = self.get_by_name(db=db, contract_id=tag.contract_id, name=name)
            if existing and existing.id != tag_id:
                raise ValueError(f"Tag '{name}' already exists for this contract")

            tag.name = name
            db.flush()
            db.refresh(tag)
            return tag
        except Exception as e:
            logger.error(f"Error updating tag {tag_id}: {e}", exc_info=True)
            db.rollback()
            raise

    def delete_tag(self, db: Session, *, tag_id: str) -> bool:
        """Delete a tag."""
        try:
            tag = db.query(self.model).filter(self.model.id == tag_id).first()
            if not tag:
                return False
            db.delete(tag)
            db.flush()
            return True
        except Exception as e:
            logger.error(f"Error deleting tag {tag_id}: {e}", exc_info=True)
            db.rollback()
            raise


# Singleton instance
contract_tag_repo = ContractTagRepository()


