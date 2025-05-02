from api.common.repository import CRUDBase
from api.db_models.data_domains import DataDomain
from api.models.data_domains import DataDomainCreate, DataDomainUpdate
from api.common.logging import get_logger

logger = get_logger(__name__)

class DataDomainRepository(CRUDBase[DataDomain, DataDomainCreate, DataDomainUpdate]):
    def __init__(self):
        super().__init__(DataDomain)
        logger.info("DataDomainRepository initialized.")

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