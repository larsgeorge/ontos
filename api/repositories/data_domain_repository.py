from api.common.repository import CRUDBase
from api.db_models.data_domains import DataDomain
from api.models.data_domains import DataDomainCreate, DataDomainUpdate
from api.common.logging import get_logger
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional
from uuid import UUID

logger = get_logger(__name__)

class DataDomainRepository(CRUDBase[DataDomain, DataDomainCreate, DataDomainUpdate]):
    def __init__(self):
        super().__init__(DataDomain)
        logger.info("DataDomainRepository initialized.")

    def get_with_details(self, db: Session, id: UUID) -> Optional[DataDomain]:
        """Gets a single domain by ID, eager loading parent and children for count/details."""
        logger.debug(f"Fetching {self.model.__name__} with details for id: {id}")
        try:
            return (
                db.query(self.model)
                .options(
                    joinedload(self.model.parent),
                    selectinload(self.model.children)
                )
                .filter(self.model.id == str(id))
                .first()
            )
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching {self.model.__name__} with details by id {id}: {e}", exc_info=True)
            db.rollback()
            raise

    def get_multi_with_details(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[DataDomain]:
        """Gets multiple domains, eager loading parent and children for count/details."""
        logger.debug(f"Fetching multiple {self.model.__name__} with details, skip={skip}, limit={limit}")
        try:
            return (
                db.query(self.model)
                .options(
                    joinedload(self.model.parent),
                    selectinload(self.model.children)
                )
                .order_by(self.model.name)
                .offset(skip)
                .limit(limit)
                .all()
            )
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching multiple {self.model.__name__} with details: {e}", exc_info=True)
            db.rollback()
            raise

    # Add domain-specific methods here if needed later
    # For example:
    # def get_by_name(self, db: Session, *, name: str) -> Optional[DataDomain]:
    #     logger.debug(f"Fetching {self.model.__name__} with name: {name}")
    #     try:
    #         return db.query(self.model).filter(self.model.name == name).first()
    #     except SQLAlchemyError as e:
    #         logger.error(f"Database error fetching {self.model.__name__} by name {name}: {e}", exc_info=True)
    #         db.rollback()
    #         raise

# Singleton instance (optional, depending on how it's used/injected)
# data_domain_repository = DataDomainRepository() 