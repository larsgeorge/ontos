import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Boolean, Text, Enum as SQLAlchemyEnum, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID # Or keep generic UUID

from src.common.database import Base
from src.models.notifications import NotificationType # Import the Pydantic enum

class NotificationDb(Base):
    __tablename__ = 'notifications'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String(50), nullable=False, index=True)
    title = Column(String, nullable=False)
    subtitle = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    message = Column(Text, nullable=True)  # Alternative to description for job progress
    link = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)  # For tracking updates
    read = Column(Boolean, default=False, nullable=False)
    can_delete = Column(Boolean, default=True, nullable=False)
    recipient = Column(String, nullable=True, index=True) # Email or Role name
    target_roles = Column(String, nullable=True)  # JSON array of role names
    action_type = Column(String, nullable=True) # For linking to actions
    action_payload = Column(String, nullable=True) # JSON string for action context
    data = Column(String, nullable=True)  # JSON string for additional data (job progress etc.)

    def __repr__(self):
        return f"<NotificationDb(id='{self.id}', title='{self.title}', recipient='{self.recipient}')>" 