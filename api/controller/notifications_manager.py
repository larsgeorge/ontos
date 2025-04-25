import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
import json

import yaml
from sqlalchemy.orm import Session # Import Session for type hinting
from pydantic import ValidationError # Import for error handling

from api.models.notifications import Notification, NotificationType # Import the enum too
# Import SettingsManager for role lookups
from api.controller.settings_manager import SettingsManager
# Import UserInfo type hint
from api.models.users import UserInfo
# Import the repository
from api.repositories.notification_repository import notification_repo, NotificationRepository

# Set up logging
from api.common.logging import setup_logging, get_logger
setup_logging(level=logging.INFO)
logger = get_logger(__name__)

class NotificationNotFoundError(Exception):
    """Raised when a notification is not found."""

class NotificationsManager:
    def __init__(self, settings_manager: SettingsManager):
        """Initialize the notification manager.

        Args:
            settings_manager: The SettingsManager instance to look up role details.
        """
        # self.notifications: List[Notification] = [] # REMOVE In-memory list
        self._repo = notification_repo # Use the repository instance
        self._settings_manager = settings_manager # Store the manager

    def load_from_yaml(self, yaml_path: str, db: Session) -> bool:
        """Load example notifications from YAML file into the database."""
        # Note: The check for empty DB should be done *before* calling this method
        # (e.g., in the demo_data_loader)
        try:
            file_path = Path(yaml_path)
            if not file_path.is_file():
                logger.error(f"Notifications YAML file not found at {yaml_path}")
                return False

            with open(file_path) as file:
                data = yaml.safe_load(file)
            
            if not isinstance(data, dict) or 'notifications' not in data or not isinstance(data['notifications'], list):
                logger.error(f"Invalid format in {yaml_path}. Expected a dict with a 'notifications' list.")
                return False

            loaded_count = 0
            errors = 0
            for notification_data in data.get('notifications', []):
                 try:
                    # Ensure ID exists or generate one
                    if 'id' not in notification_data or not notification_data['id']:
                        notification_data['id'] = str(uuid.uuid4())
                        
                    # Parse created_at string
                    if isinstance(notification_data.get('created_at'), str):
                         notification_data['created_at'] = datetime.fromisoformat(notification_data['created_at'].replace('Z', '+00:00')) # Handle Z timezone
                    else:
                         notification_data['created_at'] = datetime.utcnow() # Fallback
                         
                    # Validate with Pydantic model
                    notification_model = Notification(**notification_data)
                    
                    # Create in DB via repository
                    self._repo.create(db=db, obj_in=notification_model)
                    loaded_count += 1
                 except (ValidationError, ValueError) as e:
                     logger.error(f"Error validating/processing notification data from YAML: {e}. Data: {notification_data}", exc_info=True)
                     errors += 1
                 except Exception as e:
                     logger.error(f"Database or unexpected error loading notification from YAML: {e}. Data: {notification_data}", exc_info=True)
                     errors += 1
                     # Consider rolling back the session here or letting the caller handle it
                     # db.rollback() # Potential rollback

            logger.info(f"Processed {loaded_count} notifications from {yaml_path}. Encountered {errors} errors.")
            # Commit should happen outside this function (e.g., in load_initial_data)
            return errors == 0 # Return True only if no errors occurred

        except yaml.YAMLError as e:
            logger.error(f"Error parsing notifications YAML file {yaml_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error loading notifications from YAML {yaml_path}: {e}", exc_info=True)
            return False

    def get_notifications(self, db: Session, user_info: Optional[UserInfo] = None) -> List[Notification]:
        """Get notifications from the database, filtered for the user."""
        
        # Fetch all notifications from the repository
        all_notifications_db = self._repo.get_multi(db=db, limit=1000) # Adjust limit if needed
        
        # Convert DB models to Pydantic models (handling potential errors)
        all_notifications_api: List[Notification] = [] 
        for db_obj in all_notifications_db:
             try:
                 all_notifications_api.append(Notification.from_orm(db_obj))
             except ValidationError as e:
                 logger.error(f"Error validating Notification DB object (ID: {db_obj.id}): {e}")
                 continue # Skip this notification

        # --- Filtering logic (similar to before, but uses API models and SettingsManager) ---
        if not user_info:
            # Return only broadcast notifications if no user info
            return [n for n in all_notifications_api if not n.recipient]

        user_groups = set(user_info.groups or [])
        user_email = user_info.email

        # Pre-fetch all role definitions for efficient lookup
        try:
            all_roles = self._settings_manager.list_app_roles() # Assuming this uses DB and returns List[AppRole]
            role_map: Dict[str, 'AppRole'] = {role.name: role for role in all_roles} # Use AppRole type
        except Exception as e:
            logger.error(f"Failed to retrieve roles for notification filtering: {e}")
            role_map = {} # Continue with empty map if roles fail

        filtered_notifications = []
        for n in all_notifications_api:
            is_recipient = False
            recipient = n.recipient

            if not recipient: # Broadcast
                is_recipient = True
            elif user_email and recipient == user_email: # Direct email match
                is_recipient = True
            elif recipient in role_map: # Check if recipient matches a defined role name
                 target_role = role_map[recipient]
                 if any(group in user_groups for group in target_role.assigned_groups):
                      is_recipient = True

            if is_recipient:
                filtered_notifications.append(n)

        # Sort by created_at descending (using datetime objects)
        filtered_notifications.sort(key=lambda x: x.created_at, reverse=True)

        return filtered_notifications

    def create_notification(self, db: Session, notification: Notification) -> Notification:
        """Create a new notification using the repository."""
        try:
            # Ensure ID is set if not provided (repo might handle this too)
            if not notification.id:
                notification.id = str(uuid.uuid4())
            # Ensure created_at is set
            if not notification.created_at:
                notification.created_at = datetime.utcnow()
                
            created_db_obj = self._repo.create(db=db, obj_in=notification)
            return Notification.from_orm(created_db_obj)
        except Exception as e:
             logger.error(f"Error creating notification in DB: {e}", exc_info=True)
             raise # Re-raise to be handled by the caller/route

    def delete_notification(self, db: Session, notification_id: str) -> bool:
        """Delete a notification by ID using the repository."""
        try:
             deleted_obj = self._repo.remove(db=db, id=notification_id)
             return deleted_obj is not None
        except Exception as e:
             logger.error(f"Error deleting notification {notification_id}: {e}", exc_info=True)
             raise

    def mark_notification_read(self, db: Session, notification_id: str) -> Optional[Notification]:
        """Mark a notification as read using the repository."""
        try:
            db_obj = self._repo.get(db=db, id=notification_id)
            if not db_obj:
                return None
            
            if db_obj.read: # Already read
                return Notification.from_orm(db_obj)
                
            # Update using the repository's update method
            updated_db_obj = self._repo.update(db=db, db_obj=db_obj, obj_in={"read": True})
            return Notification.from_orm(updated_db_obj)
        except Exception as e:
            logger.error(f"Error marking notification {notification_id} as read: {e}", exc_info=True)
            raise

    def handle_actionable_notification(self, db: Session, action_type: str, action_payload: Dict) -> bool:
        """Finds notifications by action type/payload and marks them as read using the repository."""
        logger.debug(f"Attempting to handle notification: type={action_type}, payload={action_payload}")
        try:
            # Assuming repo has a method to find by action (might need creating)
            # Alternatively, get all matching type and filter here
            # Example: Fetch notifications matching action_type (needs repo method)
            # matching_notifications = self._repo.get_by_action_type(db, action_type=action_type)
            
            # Simplified: Get all and filter (less efficient for many notifications)
            all_notifications = self._repo.get_multi(db, limit=5000) 
            
            found_and_handled = False
            for notification_db in all_notifications:
                 # Convert payload string from DB back to dict for comparison
                 payload_db = {}
                 if notification_db.action_payload:
                     try:
                         payload_db = json.loads(notification_db.action_payload)
                     except json.JSONDecodeError:
                         logger.warning(f"Could not parse action_payload for notification {notification_db.id}")
                         continue

                 # Check for match
                 if (notification_db.action_type == action_type and
                     payload_db is not None and
                     # Check if provided payload is subset of DB payload
                     all(item in payload_db.items() for item in action_payload.items())):
                    
                    if not notification_db.read:
                        # Mark as read using the update method
                        self._repo.update(db=db, db_obj=notification_db, obj_in={"read": True})
                        logger.info(f"Marked actionable notification as read: ID={notification_db.id}, Type={action_type}")
                        found_and_handled = True
                        # Optional: break if only one notification should match
                        # break 
                    else:
                        logger.info(f"Actionable notification already read: ID={notification_db.id}, Type={action_type}")
                        # Still count as found
                        found_and_handled = True 
                        # break 
            
            if not found_and_handled:
                logger.warning(f"Could not find actionable notification to handle: type={action_type}, payload={action_payload}")
            
            db.commit() # Commit the changes made (marking as read)
            return found_and_handled
            
        except Exception as e:
             logger.error(f"Error handling actionable notification: {e}", exc_info=True)
             db.rollback() # Rollback on error
             return False
