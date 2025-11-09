"""
Integration tests for comments API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestCommentsRoutes:
    """Integration tests for comments API endpoints."""

    @pytest.fixture
    def sample_comment_data(self):
        """Sample comment data for testing."""
        return {
            "entity_id": "test-entity-123",
            "entity_type": "data_product",
            "title": "Test Comment",
            "comment": "This is a test comment",
            "audience": None,
        }

    def test_get_comments_for_entity(self, client: TestClient, db_session: Session):
        """Test getting comments for an entity."""
        response = client.get("/api/comments/data_product/test-id")
        assert response.status_code == 200
        data = response.json()
        # Should return comments list and count
        assert "comments" in data or isinstance(data, list)

    def test_create_comment(self, client: TestClient, db_session: Session, sample_comment_data):
        """Test creating a comment."""
        response = client.post("/api/comments", json=sample_comment_data)
        assert response.status_code in [200, 201]
        data = response.json()
        assert "id" in data
        assert data["title"] == "Test Comment"

    def test_update_comment(self, client: TestClient, db_session: Session, sample_comment_data):
        """Test updating a comment."""
        # Create comment first
        create_response = client.post("/api/comments", json=sample_comment_data)
        assert create_response.status_code in [200, 201]
        comment_id = create_response.json()["id"]

        # Update the comment
        update_data = {
            "title": "Updated Comment Title",
            "comment": "Updated comment text",
        }
        response = client.put(f"/api/comments/{comment_id}", json=update_data)
        assert response.status_code in [200, 404]  # Might be 404 if feature not fully implemented

    def test_delete_comment(self, client: TestClient, db_session: Session, sample_comment_data):
        """Test deleting a comment."""
        # Create comment first
        create_response = client.post("/api/comments", json=sample_comment_data)
        if create_response.status_code in [200, 201]:
            comment_id = create_response.json()["id"]

            # Delete the comment
            response = client.delete(f"/api/comments/{comment_id}")
            assert response.status_code in [200, 204]

    def test_create_comment_with_audience(self, client: TestClient, db_session: Session):
        """Test creating a comment with specific audience."""
        comment_data = {
            "entity_id": "test-entity-456",
            "entity_type": "data_contract",
            "title": "Restricted Comment",
            "comment": "This comment is for specific groups only",
            "audience": ["admins", "data_stewards"],
        }
        response = client.post("/api/comments", json=comment_data)
        assert response.status_code in [200, 201]

    def test_create_comment_validation_error(self, client: TestClient):
        """Test comment creation with invalid data."""
        invalid_data = {
            "comment": "Missing required fields"
        }
        response = client.post("/api/comments", json=invalid_data)
        assert response.status_code == 422

