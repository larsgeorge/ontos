import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .config import get_config_manager
from .logging import get_logger

logger = get_logger(__name__)

class NotificationType(Enum):
    """Types of notifications."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    PROGRESS = "progress"

class Notification:
    """Represents a user notification."""
    def __init__(
        self,
        id: str,
        type: NotificationType,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None
    ) -> None:
        """Initialize a notification.
        
        Args:
            id: Unique notification ID
            type: Type of notification
            message: Notification message
            details: Optional additional details
            created_at: Optional creation timestamp
        """
        self.id = id
        self.type = type
        self.message = message
        self.details = details or {}
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "type": self.type.value,
            "message": self.message,
            "details": self.details,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Notification':
        """Create notification from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            Notification instance
        """
        return cls(
            id=data["id"],
            type=NotificationType(data["type"]),
            message=data["message"],
            details=data.get("details"),
            created_at=datetime.fromisoformat(data["created_at"])
        )

class NotificationService:
    """Service for managing user notifications."""

    def __init__(self) -> None:
        """Initialize the notification service."""
        config = get_config_manager()
        self.notifications_dir = config.data_dir / 'notifications'
        self.notifications_dir.mkdir(parents=True, exist_ok=True)
        self.notifications: Dict[str, List[Notification]] = {}

    def create_notification(
        self,
        user_id: str,
        type: NotificationType,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """Create a new notification.
        
        Args:
            user_id: ID of the user to notify
            type: Type of notification
            message: Notification message
            details: Optional additional details
            
        Returns:
            Created notification
        """
        notification = Notification(
            id=f"{user_id}_{datetime.utcnow().timestamp()}",
            type=type,
            message=message,
            details=details
        )

        if user_id not in self.notifications:
            self.notifications[user_id] = []

        self.notifications[user_id].append(notification)
        self._save_notifications(user_id)

        logger.info(f"Created notification {notification.id} for user {user_id}")
        return notification

    def get_notifications(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Notification]:
        """Get notifications for a user.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of notifications
            offset: Number of notifications to skip
            
        Returns:
            List of notifications
        """
        if user_id not in self.notifications:
            self._load_notifications(user_id)

        notifications = self.notifications.get(user_id, [])
        notifications.sort(key=lambda x: x.created_at, reverse=True)
        return notifications[offset:offset + limit]

    def update_progress(
        self,
        user_id: str,
        notification_id: str,
        progress: float,
        message: Optional[str] = None
    ) -> Optional[Notification]:
        """Update progress of a progress notification.
        
        Args:
            user_id: ID of the user
            notification_id: ID of the notification
            progress: Progress value between 0 and 1
            message: Optional updated message
            
        Returns:
            Updated notification if found, None otherwise
        """
        if user_id not in self.notifications:
            return None

        for notification in self.notifications[user_id]:
            if notification.id == notification_id and notification.type == NotificationType.PROGRESS:
                notification.details["progress"] = progress
                if message:
                    notification.message = message
                self._save_notifications(user_id)
                return notification

        return None

    def delete_notification(self, user_id: str, notification_id: str) -> bool:
        """Delete a notification.
        
        Args:
            user_id: ID of the user
            notification_id: ID of the notification
            
        Returns:
            True if notification was deleted, False otherwise
        """
        if user_id not in self.notifications:
            return False

        for i, notification in enumerate(self.notifications[user_id]):
            if notification.id == notification_id:
                del self.notifications[user_id][i]
                self._save_notifications(user_id)
                return True

        return False

    def _load_notifications(self, user_id: str) -> None:
        """Load notifications for a user.
        
        Args:
            user_id: ID of the user
        """
        file_path = self.notifications_dir / f"{user_id}.json"
        if not file_path.exists():
            self.notifications[user_id] = []
            return

        try:
            with open(file_path) as f:
                data = json.load(f)
                self.notifications[user_id] = [
                    Notification.from_dict(item)
                    for item in data
                ]
        except Exception as e:
            logger.error(f"Error loading notifications for user {user_id}: {e!s}")
            self.notifications[user_id] = []

    def _save_notifications(self, user_id: str) -> None:
        """Save notifications for a user.
        
        Args:
            user_id: ID of the user
        """
        file_path = self.notifications_dir / f"{user_id}.json"
        try:
            with open(file_path, 'w') as f:
                json.dump(
                    [n.to_dict() for n in self.notifications[user_id]],
                    f,
                    indent=2
                )
        except Exception as e:
            logger.error(f"Error saving notifications for user {user_id}: {e!s}")
            raise

# Global notification service instance
notification_service: Optional[NotificationService] = None

def init_notification_service() -> None:
    """Initialize the global notification service instance."""
    global notification_service
    notification_service = NotificationService()

def get_notification_service() -> NotificationService:
    """Get the global notification service instance.
    
    Returns:
        Notification service
        
    Raises:
        RuntimeError: If notification service is not initialized
    """
    if not notification_service:
        raise RuntimeError("Notification service not initialized")
    return notification_service
