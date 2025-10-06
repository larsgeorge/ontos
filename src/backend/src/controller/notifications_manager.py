import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
import json

import yaml
from sqlalchemy.orm import Session # Import Session for type hinting
from pydantic import ValidationError # Import for error handling

from src.models.notifications import Notification, NotificationType # Import the enum too
# Import SettingsManager for role lookups
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.controller.settings_manager import SettingsManager
# Import UserInfo type hint
from src.models.users import UserInfo
# Import the repository
from src.repositories.notification_repository import notification_repo, NotificationRepository

# Set up logging
from src.common.logging import get_logger
logger = get_logger(__name__)

class NotificationNotFoundError(Exception):
    """Raised when a notification is not found."""

class NotificationsManager:
    def __init__(self, settings_manager: 'SettingsManager'):
        """Initialize the notification manager.

        Args:
            settings_manager: The SettingsManager instance to look up role details.
        """
        # self.notifications: List[Notification] = [] # REMOVE In-memory list
        self._repo = notification_repo # Use the repository instance
        self._settings_manager = settings_manager # Store the manager

    def load_initial_data(self, db: Session) -> bool:
        """Load example notifications from YAML file into the database if empty."""
        # Check if the table is empty first using the passed session
        try:
            # Assuming repository has is_empty method
            if not self._repo.is_empty(db=db):
                logger.info("Notifications table is not empty. Skipping initial data loading.")
                return False
        except AttributeError:
            logger.error("NotificationsManager repository does not have 'is_empty', cannot check if empty. Skipping load.")
            return False # Cannot proceed safely without the check
        except Exception as e:
            logger.error(f"Error checking if notifications table is empty: {e}", exc_info=True)
            return False # Error during check, skip loading
            
        # Construct the default YAML path relative to the project structure
        base_dir = Path(__file__).parent.parent # Navigate up from controller/ to api/
        yaml_path = base_dir / "data" / "notifications.yaml" # Standard location
        
        logger.info(f"Notifications table is empty. Attempting to load initial data from {yaml_path}...")
        try:
            if not yaml_path.is_file():
                logger.error(f"Notifications YAML file not found at {yaml_path}")
                return False

            with open(yaml_path) as file:
                data = yaml.safe_load(file)
            
            # YAML structure expected: a list of notification objects
            if not isinstance(data, list):
                logger.error(f"Invalid format in {yaml_path}. Expected a list of notifications.")
                return False

            loaded_count = 0
            errors = 0
            for notification_data in data:
                if not isinstance(notification_data, dict):
                    logger.warning("Skipping non-dictionary item in YAML notifications data.")
                    continue
                try:
                    # Ensure ID exists or generate one
                    if 'id' not in notification_data or not notification_data['id']:
                        notification_data['id'] = str(uuid.uuid4())
                        
                    # Parse created_at string
                    if isinstance(notification_data.get('created_at'), str):
                        # Handle ISO format with potential Z for UTC
                        dt_str = notification_data['created_at'].replace('Z', '+00:00')
                        try:
                            notification_data['created_at'] = datetime.fromisoformat(dt_str)
                        except ValueError:
                            logger.warning(f"Could not parse created_at string '{notification_data['created_at']}', using current time.")
                            notification_data['created_at'] = datetime.utcnow()
                    elif not isinstance(notification_data.get('created_at'), datetime):
                        notification_data['created_at'] = datetime.utcnow() # Fallback if missing or wrong type
                        
                    # Validate with Pydantic model
                    notification_model = Notification(**notification_data)
                    
                    # Create in DB via repository using the passed db session
                    self._repo.create(db=db, obj_in=notification_model)
                    loaded_count += 1
                except (ValidationError, ValueError) as e:
                    logger.error(f"Error validating/processing notification data from YAML (ID: {notification_data.get('id', 'N/A')}): {e}.")
                    db.rollback() # Rollback this item
                    errors += 1
                except Exception as e:
                    logger.error(f"Database or unexpected error loading notification from YAML (ID: {notification_data.get('id', 'N/A')}): {e}.", exc_info=True)
                    db.rollback() # Rollback this item
                    errors += 1

            if errors == 0 and loaded_count > 0:
                db.commit() # Commit only if all loaded successfully
                logger.info(f"Successfully loaded and committed {loaded_count} notifications from {yaml_path}.")
            elif loaded_count > 0 and errors > 0:
                logger.warning(f"Processed {loaded_count + errors} notifications from {yaml_path}, but encountered {errors} errors. Changes for successful notifications were rolled back.")
            elif errors > 0:
                logger.error(f"Encountered {errors} errors processing notifications from {yaml_path}. No notifications loaded.")
            else:
                logger.info(f"No new notifications found to load from {yaml_path}.")

            return loaded_count > 0 and errors == 0 # Return True only if loaded without errors

        except FileNotFoundError: # Catch outside loop
            logger.error(f"Notifications YAML file not found at {yaml_path}")
            return False
        except yaml.YAMLError as e:
            logger.error(f"Error parsing notifications YAML file {yaml_path}: {e}")
            db.rollback() # Rollback if YAML parsing failed
            return False
        except Exception as e:
            logger.error(f"Unexpected error loading notifications from YAML {yaml_path}: {e}", exc_info=True)
            db.rollback() # Rollback on other errors
            return False

    def get_notifications(self, db: Session, user_info: Optional[UserInfo] = None) -> List[Notification]:
        """Get notifications from the database, filtered for the user."""
        
        # Fetch all notifications from the repository
        all_notifications_db = self._repo.get_multi(db=db, limit=1000) # Adjust limit if needed
        
        # Convert DB models to Pydantic models (handling potential errors)
        all_notifications_api: List[Notification] = []
        for db_obj in all_notifications_db:
             try:
                 all_notifications_api.append(Notification.model_validate(db_obj))
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

    async def create_notification(
        self,
        db: Session,
        user_id: Optional[str] = None, # Add user_id (recipient or broadcast)
        title: str = "Notification",
        subtitle: Optional[str] = None,
        description: Optional[str] = None,
        link: Optional[str] = None,
        type: NotificationType = NotificationType.INFO,
        action_type: Optional[str] = None,
        action_payload: Optional[Dict] = None,
        can_delete: bool = True
    ) -> Notification:
        """Creates and saves a new notification using keyword arguments."""
        try:
            now = datetime.utcnow()
            notification_id = str(uuid.uuid4())
            
            # Construct the Notification Pydantic model internally
            notification_data = Notification(
                id=notification_id,
                recipient=user_id, # Use user_id as recipient (None for broadcast)
                title=title,
                subtitle=subtitle,
                description=description,
                link=link,
                type=type,
                action_type=action_type,
                action_payload=action_payload,
                can_delete=can_delete,
                created_at=now,
                read=False
            )

            logger.debug(f"Creating notification: {notification_data.dict()}")
            created_db_obj = self._repo.create(db=db, obj_in=notification_data)
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
            db.commit() # Commit the change to the database
            db.refresh(updated_db_obj) # Refresh to get the committed state
            return Notification.from_orm(updated_db_obj)
        except Exception as e:
            logger.error(f"Error marking notification {notification_id} as read: {e}", exc_info=True)
            db.rollback()
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

    def update_notification(self, db: Session, notification_id: str, *,
                            title: Optional[str] = None,
                            subtitle: Optional[str] = None,
                            description: Optional[str] = None,
                            link: Optional[str] = None,
                            type: Optional[NotificationType] = None,
                            action_type: Optional[str] = None,
                            action_payload: Optional[Dict] = None,
                            read: Optional[bool] = None,
                            can_delete: Optional[bool] = None) -> Optional[Notification]:
        """Update fields on an existing notification and return the updated API model."""
        try:
            db_obj = self._repo.get(db=db, id=notification_id)
            if not db_obj:
                return None

            update_data: Dict = {}
            if title is not None:
                update_data['title'] = title
            if subtitle is not None:
                update_data['subtitle'] = subtitle
            if description is not None:
                update_data['description'] = description
            if link is not None:
                update_data['link'] = link
            if type is not None:
                update_data['type'] = type
            if action_type is not None:
                update_data['action_type'] = action_type
            if action_payload is not None:
                update_data['action_payload'] = action_payload
            if read is not None:
                update_data['read'] = read
            if can_delete is not None:
                update_data['can_delete'] = can_delete

            updated = self._repo.update(db=db, db_obj=db_obj, obj_in=update_data)
            return Notification.from_orm(updated)
        except Exception as e:
            logger.error(f"Error updating notification {notification_id}: {e}", exc_info=True)
            db.rollback()
            return None

    def create_notification(self, notification: Notification, db: Session) -> Notification:
        """Create a notification from a Notification object."""
        try:
            logger.debug(f"Creating notification: {notification.model_dump()}")
            created_db_obj = self._repo.create(db=db, obj_in=notification)
            return Notification.model_validate(created_db_obj)
        except Exception as e:
            logger.error(f"Error creating notification in DB: {e}", exc_info=True)
            db.rollback()
            raise

    def update_notification(self, notification_id: str, update: 'NotificationUpdate', db: Session) -> Optional[Notification]:
        """Update a notification using a NotificationUpdate object."""
        try:
            from src.models.notifications import NotificationUpdate
            
            db_obj = self._repo.get(db=db, id=notification_id)
            if not db_obj:
                return None

            # Convert update model to dictionary, excluding None values
            update_data = {k: v for k, v in update.model_dump(exclude_none=True).items()}
            
            if update_data:
                updated = self._repo.update(db=db, db_obj=db_obj, obj_in=update_data)
                return Notification.model_validate(updated)
            
            return Notification.model_validate(db_obj)
            
        except Exception as e:
            logger.error(f"Error updating notification {notification_id}: {e}", exc_info=True)
            db.rollback()
            return None
