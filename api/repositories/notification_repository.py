from sqlalchemy.orm import Session
from typing import Any, Dict, Union, Optional, List
import json # For handling JSON strings
from sqlalchemy import func

from api.common.repository import CRUDBase
from api.db_models.notifications import NotificationDb # SQLAlchemy model
from api.models.notifications import Notification as NotificationApi # API model
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
        obj_in_data = obj_in.model_dump(exclude_unset=True) 

        # Convert action_payload dict to JSON string if present
        if 'action_payload' in obj_in_data and isinstance(obj_in_data['action_payload'], dict):
            obj_in_data['action_payload'] = json.dumps(obj_in_data['action_payload'])
            
        # Explicitly convert Enum to its string value
        if 'type' in obj_in_data and isinstance(obj_in_data['type'], NotificationType):
            obj_in_data['type'] = obj_in_data['type'].value
            
        # Ensure 'read' field has a boolean value
        if 'read' not in obj_in_data:
            obj_in_data['read'] = False 
        elif obj_in_data['read'] is None: 
            obj_in_data['read'] = False
            
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        # --- Flush and Refresh --- 
        db.flush()  # Send pending changes to DB (assigns defaults like 'read')
        db.refresh(db_obj) # Update the db_obj instance with DB state
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
            
        # Explicitly convert Enum to its string value
        if 'type' in update_data and isinstance(update_data['type'], NotificationType):
            update_data['type'] = update_data['type'].value
            
        # --- Ensure 'read' field is boolean if provided in update --- 
        if 'read' in update_data and update_data['read'] is None:
             # If an update explicitly tries to set read to None, either raise error or force False
             logger.warning(f"Attempted to set 'read' to None during update for Notification {db_obj.id}. Setting to False instead.")
             update_data['read'] = False 
             # Alternatively: raise ValueError("'read' field cannot be set to None")

        return super().update(db, db_obj=db_obj, obj_in=update_data)
    
    def is_empty(self, db: Session) -> bool:
        """Checks if the notifications table is empty."""
        return db.query(self.model).first() is None

# Create a singleton instance for the manager to use
notification_repo = NotificationRepository(NotificationDb) 