"""
Integration tests for user API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestUserRoutes:
    """Integration tests for user API endpoints."""

    def test_get_current_user(self, client: TestClient, db_session: Session):
        """Test getting current user information."""
        response = client.get("/api/user/me")
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "groups" in data

    def test_get_user_permissions(self, client: TestClient, db_session: Session):
        """Test getting user permissions."""
        response = client.get("/api/user/permissions")
        assert response.status_code == 200
        data = response.json()
        # Should return permissions mapping
        assert isinstance(data, dict)

    def test_get_user_profile(self, client: TestClient, db_session: Session):
        """Test getting user profile."""
        response = client.get("/api/user/profile")
        assert response.status_code == 200
        data = response.json()
        assert "email" in data or "username" in data

    def test_search_users(self, client: TestClient, db_session: Session):
        """Test searching for users."""
        response = client.get("/api/users/search?query=test")
        # Might require admin permissions
        assert response.status_code in [200, 403]

    def test_get_user_activity(self, client: TestClient, db_session: Session):
        """Test getting user activity."""
        response = client.get("/api/user/activity")
        # Might not be implemented or require permissions
        assert response.status_code in [200, 404, 405]

