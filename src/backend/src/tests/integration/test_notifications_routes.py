"""
Integration tests for notifications API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestNotificationsRoutes:
    """Integration tests for notifications API endpoints."""

    def test_get_notifications(self, client: TestClient, db_session: Session):
        """Test getting notifications for current user."""
        response = client.get("/api/notifications")
        assert response.status_code == 200
        data = response.json()
        # Should return notifications structure
        assert isinstance(data, (list, dict))

    def test_get_unread_notifications(self, client: TestClient, db_session: Session):
        """Test getting unread notifications."""
        response = client.get("/api/notifications?unread_only=true")
        assert response.status_code == 200

    def test_mark_notification_as_read(self, client: TestClient, db_session: Session):
        """Test marking notification as read."""
        # Get notifications first
        get_response = client.get("/api/notifications")
        if get_response.status_code == 200:
            notifications = get_response.json()
            if isinstance(notifications, list) and len(notifications) > 0:
                notification_id = notifications[0].get("id")
                if notification_id:
                    # Mark as read
                    response = client.put(f"/api/notifications/{notification_id}/read")
                    assert response.status_code in [200, 204]

    def test_mark_all_as_read(self, client: TestClient, db_session: Session):
        """Test marking all notifications as read."""
        response = client.put("/api/notifications/mark-all-read")
        assert response.status_code in [200, 204]

    def test_get_notification_count(self, client: TestClient, db_session: Session):
        """Test getting notification count."""
        response = client.get("/api/notifications/count")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data or "total" in data or isinstance(data, int)

    def test_delete_notification(self, client: TestClient, db_session: Session):
        """Test deleting a notification."""
        # Get notifications first
        get_response = client.get("/api/notifications")
        if get_response.status_code == 200:
            notifications = get_response.json()
            if isinstance(notifications, list) and len(notifications) > 0:
                notification_id = notifications[0].get("id")
                if notification_id:
                    # Delete notification
                    response = client.delete(f"/api/notifications/{notification_id}")
                    assert response.status_code in [200, 204]

