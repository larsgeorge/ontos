import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from src.common.database import Base

class AuditLogDb(Base):
    __tablename__ = 'audit_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    username = Column(String, nullable=False, index=True)
    ip_address = Column(String)
    feature = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False, index=True)
    success = Column(Boolean, nullable=False, default=True)
    details = Column(JSON) # Store arbitrary action-specific details

    def __repr__(self):
        return f"<AuditLog(id={self.id}, timestamp={self.timestamp}, user='{self.username}', feature='{self.feature}', action='{self.action}')>" 