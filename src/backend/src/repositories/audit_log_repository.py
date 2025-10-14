from datetime import datetime
from typing import List, Optional, Sequence

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from src.common.repository import CRUDBase
from src.models.audit_log import AuditLogCreate  # Pydantic model for creation
from src.db_models.audit_log import AuditLogDb # Corrected import

class AuditLogRepository(CRUDBase[AuditLogDb, AuditLogCreate, AuditLogCreate]):
    
    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        username: Optional[str] = None,
        feature: Optional[str] = None,
        action: Optional[str] = None,
        success: Optional[bool] = None,
    ) -> Sequence[AuditLogDb]:
        """Retrieve multiple audit logs with filtering and pagination."""
        statement = select(self.model).order_by(self.model.timestamp.desc())

        if start_time:
            statement = statement.where(self.model.timestamp >= start_time)
        if end_time:
            statement = statement.where(self.model.timestamp <= end_time)
        if username:
            statement = statement.where(self.model.username == username)
        if feature:
            statement = statement.where(self.model.feature == feature)
        if action:
            statement = statement.where(self.model.action == action)
        if success is not None:
            statement = statement.where(self.model.success == success)

        statement = statement.offset(skip).limit(limit)

        result = db.execute(statement)
        return result.scalars().all()

    def get_multi_count(
        self,
        db: Session,
        *,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        username: Optional[str] = None,
        feature: Optional[str] = None,
        action: Optional[str] = None,
        success: Optional[bool] = None,
    ) -> int:
        """Count audit logs with filtering."""
        statement = select(func.count()).select_from(self.model)

        if start_time:
            statement = statement.where(self.model.timestamp >= start_time)
        if end_time:
            statement = statement.where(self.model.timestamp <= end_time)
        if username:
            statement = statement.where(self.model.username == username)
        if feature:
            statement = statement.where(self.model.feature == feature)
        if action:
            statement = statement.where(self.model.action == action)
        if success is not None:
            statement = statement.where(self.model.success == success)

        result = db.execute(statement)
        return result.scalar_one()


audit_log_repository = AuditLogRepository(AuditLogDb) 