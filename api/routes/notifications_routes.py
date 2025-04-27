import logging
import os
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from api.models.users import UserInfo
from api.controller.notifications_manager import NotificationNotFoundError, NotificationsManager
from api.models.notifications import Notification
from api.common.dependencies import NotificationsManagerDep, DBSessionDep, CurrentUserDep

# Configure logging
from api.common.logging import setup_logging, get_logger
setup_logging(level=logging.INFO)
logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["notifications"])

@router.get('/notifications', response_model=List[Notification])
async def get_notifications(
    db: DBSessionDep,
    user_info: CurrentUserDep,
    manager: NotificationsManagerDep
):
    """Get notifications filtered for the current user."""
    try:
        logger.info(f"Retrieving notifications for user: {user_info.email} with groups: {user_info.groups}")
        notifications = manager.get_notifications(db=db, user_info=user_info)
        logger.info(f"Number of notifications retrieved: {len(notifications)}")
        return notifications
    except Exception as e:
        logger.error(f"Error retrieving notifications: {e!s}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error retrieving notifications.")

@router.post('/notifications', response_model=Notification)
async def create_notification(
    notification: Notification,
    db: DBSessionDep,
    manager: NotificationsManagerDep
):
    """Create a new notification."""
    try:
        created_notification = manager.create_notification(db=db, notification=notification)
        return created_notification
    except Exception as e:
        logger.error(f"Error creating notification: {e!s}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error creating notification.")

@router.delete('/notifications/{notification_id}', status_code=204)
async def delete_notification(
    notification_id: str,
    db: DBSessionDep,
    manager: NotificationsManagerDep
):
    """Delete a notification by ID."""
    try:
        deleted = manager.delete_notification(db=db, notification_id=notification_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Notification not found")
        return None
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error deleting notification {notification_id}: {e!s}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error deleting notification.")

@router.put('/notifications/{notification_id}/read', response_model=Notification)
async def mark_notification_read(
    notification_id: str,
    db: DBSessionDep,
    manager: NotificationsManagerDep
):
    """Mark a notification as read."""
    try:
        updated_notification = manager.mark_notification_read(db=db, notification_id=notification_id)
        if updated_notification is None:
            raise HTTPException(status_code=404, detail="Notification not found")
        return updated_notification
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error marking notification {notification_id} as read: {e!s}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error marking notification as read.")

def register_routes(app):
    """Register notification routes with the FastAPI app."""
    app.include_router(router)
    logger.info("Notifications routes registered")

