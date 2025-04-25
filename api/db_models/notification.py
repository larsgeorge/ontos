import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Boolean, Text, Enum as SQLAlchemyEnum, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID # Or keep generic UUID

from api.common.database import Base
from api.models.notifications import NotificationType # Import the Pydantic enum

class NotificationDb(Base):
    __tablename__ = 'notifications'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String(50), nullable=False, index=True)
    title = Column(String, nullable=False)
    subtitle = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    read = Column(Boolean, default=False, nullable=False)
    can_delete = Column(Boolean, default=True, nullable=False)
    recipient = Column(String, nullable=True, index=True) # Email or Role name
    action_type = Column(String, nullable=True) # For linking to actions
    action_payload = Column(String, nullable=True) # JSON string for action context

    def __repr__(self):
        return f"<NotificationDb(id='{self.id}', title='{self.title}', recipient='{self.recipient}')>" 