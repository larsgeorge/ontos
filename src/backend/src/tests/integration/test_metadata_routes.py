"""
Integration tests for metadata API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestMetadataRoutes:
    """Integration tests for metadata API endpoints."""

    @pytest.fixture
    def sample_rich_text_data(self):
        """Sample rich text metadata for testing."""
        return {
            "entity_id": "test-entity-123",
            "entity_type": "data_product",
            "title": "Test Documentation",
            "short_description": "Short description",
            "content_markdown": "# Test Content\nThis is test markdown content.",
        }

    @pytest.fixture
    def sample_link_data(self):
        """Sample link metadata for testing."""
        return {
            "entity_id": "test-entity-456",
            "entity_type": "data_contract",
            "title": "Related Link",
            "short_description": "Link description",
            "url": "https://example.com/related",
        }

    def test_get_metadata_for_entity(self, client: TestClient, db_session: Session):
        """Test getting all metadata for an entity."""
        response = client.get("/api/metadata/data_product/test-id")
        assert response.status_code == 200
        data = response.json()
        # Should return metadata structure
        assert isinstance(data, dict)

    def test_create_rich_text(self, client: TestClient, db_session: Session, sample_rich_text_data):
        """Test creating rich text metadata."""
        response = client.post("/api/metadata/rich-text", json=sample_rich_text_data)
        assert response.status_code in [200, 201]
        data = response.json()
        assert "id" in data
        assert data["title"] == "Test Documentation"

    def test_create_link(self, client: TestClient, db_session: Session, sample_link_data):
        """Test creating link metadata."""
        response = client.post("/api/metadata/link", json=sample_link_data)
        assert response.status_code in [200, 201]
        data = response.json()
        assert "id" in data
        assert data["url"] == "https://example.com/related"

    def test_update_rich_text(self, client: TestClient, db_session: Session, sample_rich_text_data):
        """Test updating rich text metadata."""
        # Create first
        create_response = client.post("/api/metadata/rich-text", json=sample_rich_text_data)
        if create_response.status_code in [200, 201]:
            metadata_id = create_response.json()["id"]
            
            # Update
            update_data = {
                "title": "Updated Title",
                "content_markdown": "# Updated Content",
            }
            response = client.put(f"/api/metadata/rich-text/{metadata_id}", json=update_data)
            assert response.status_code in [200, 404]

    def test_delete_metadata(self, client: TestClient, db_session: Session, sample_rich_text_data):
        """Test deleting metadata."""
        # Create first
        create_response = client.post("/api/metadata/rich-text", json=sample_rich_text_data)
        if create_response.status_code in [200, 201]:
            metadata_id = create_response.json()["id"]
            
            # Delete
            response = client.delete(f"/api/metadata/rich-text/{metadata_id}")
            assert response.status_code in [200, 204]

    def test_create_rich_text_validation_error(self, client: TestClient):
        """Test rich text creation with invalid data."""
        invalid_data = {
            "title": "Missing required fields"
        }
        response = client.post("/api/metadata/rich-text", json=invalid_data)
        assert response.status_code == 422

