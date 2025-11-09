"""
Integration tests for tags API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestTagsRoutes:
    """Integration tests for tags API endpoints."""

    @pytest.fixture
    def sample_namespace_data(self):
        """Sample namespace data for testing."""
        return {
            "name": "test-namespace",
            "description": "Test namespace for integration testing",
        }

    @pytest.fixture
    def sample_tag_data(self):
        """Sample tag data for testing."""
        return {
            "namespace_id": "test-namespace",
            "tag_name": "test-tag",
            "description": "Test tag",
        }

    def test_get_namespaces(self, client: TestClient, db_session: Session):
        """Test getting tag namespaces."""
        response = client.get("/api/tags/namespaces")
        assert response.status_code == 200
        # Should return list of namespaces
        assert isinstance(response.json(), list)

    def test_create_namespace(self, client: TestClient, db_session: Session, sample_namespace_data):
        """Test creating a tag namespace."""
        response = client.post("/api/tags/namespaces", json=sample_namespace_data)
        assert response.status_code in [200, 201]
        data = response.json()
        assert "name" in data or "id" in data

    def test_get_tags_for_namespace(self, client: TestClient, db_session: Session):
        """Test getting tags for a namespace."""
        response = client.get("/api/tags/namespace/test-namespace")
        assert response.status_code in [200, 404]

    def test_create_tag(self, client: TestClient, db_session: Session, sample_tag_data):
        """Test creating a tag."""
        response = client.post("/api/tags", json=sample_tag_data)
        assert response.status_code in [200, 201, 404]

    def test_assign_tag_to_entity(self, client: TestClient, db_session: Session):
        """Test assigning a tag to an entity."""
        assign_data = {
            "namespace_id": "test-namespace",
            "tag_name": "test-tag",
            "entity_type": "data_product",
            "entity_id": "test-product-123",
        }
        response = client.post("/api/tags/assign", json=assign_data)
        assert response.status_code in [200, 201, 404]

    def test_get_tags_for_entity(self, client: TestClient, db_session: Session):
        """Test getting tags for an entity."""
        response = client.get("/api/tags/entity/data_product/test-product-123")
        assert response.status_code == 200
        # Should return list of tags
        assert isinstance(response.json(), list)

    def test_remove_tag_from_entity(self, client: TestClient, db_session: Session):
        """Test removing a tag from an entity."""
        response = client.delete("/api/tags/entity/data_product/test-product-123/namespace/test/tag/test-tag")
        assert response.status_code in [200, 204, 404]

    def test_create_namespace_validation_error(self, client: TestClient):
        """Test namespace creation with invalid data."""
        invalid_data = {}
        response = client.post("/api/tags/namespaces", json=invalid_data)
        assert response.status_code == 422

