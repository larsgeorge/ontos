from sqlalchemy.orm import Session
from typing import Any, Dict, Union, Optional, List
import json # For handling JSON strings

from api.common.repository import CRUDBase
from api.models.notifications import Notification as NotificationApi, NotificationType # Pydantic model and Enum
from api.db_models.notification import NotificationDb # SQLAlchemy model
from api.common.logging import get_logger

logger = get_logger(__name__)

# Use NotificationApi for create/update types for simplicity
NotificationCreate = NotificationApi
NotificationUpdate = Union[NotificationApi, Dict[str, Any]]

class NotificationRepository(CRUDBase[NotificationDb, NotificationCreate, NotificationUpdate]):
    """Repository for Notification CRUD operations."""

    # Override create and update to handle potential JSON string conversion for payload
    # and explicit Enum -> String conversion for the 'type' field.
    def create(self, db: Session, *, obj_in: NotificationCreate) -> NotificationDb:
        logger.debug(f"Creating Notification (DB layer)")
        # Prepare data
        obj_in_data = obj_in.model_dump(exclude_unset=True) 

        # Convert action_payload dict to JSON string if present
        if 'action_payload' in obj_in_data and isinstance(obj_in_data['action_payload'], dict):
            obj_in_data['action_payload'] = json.dumps(obj_in_data['action_payload'])
            
        # --- Explicitly convert Enum to its string value --- 
        if 'type' in obj_in_data and isinstance(obj_in_data['type'], NotificationType):
            obj_in_data['type'] = obj_in_data['type'].value
            
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        # No commit/refresh here, handled by caller (like manager or demo loader)
        # db.flush()
        # db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: NotificationDb, obj_in: NotificationUpdate) -> NotificationDb:
        logger.debug(f"Updating Notification (DB layer) with id: {db_obj.id}")
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True) 

        # Convert action_payload dict to JSON string if present in update data
        if 'action_payload' in update_data and isinstance(update_data['action_payload'], dict):
            update_data['action_payload'] = json.dumps(update_data['action_payload'])
            
        # --- Explicitly convert Enum to its string value --- 
        if 'type' in update_data and isinstance(update_data['type'], NotificationType):
            update_data['type'] = update_data['type'].value

        return super().update(db, db_obj=db_obj, obj_in=update_data)
    
    def is_empty(self, db: Session) -> bool:
        """Checks if the notifications table is empty."""
        return db.query(self.model).first() is None

# Create a singleton instance for the manager to use
notification_repo = NotificationRepository(NotificationDb) 