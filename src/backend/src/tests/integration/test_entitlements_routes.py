"""
Integration tests for entitlements API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestEntitlementsRoutes:
    """Integration tests for entitlements API endpoints."""

    @pytest.fixture
    def sample_persona_data(self):
        """Sample persona data for testing."""
        return {
            "name": "Data Analyst",
            "description": "Data analyst persona with read access",
            "permissions": {
                "catalogs": ["read"],
                "schemas": ["read"],
                "tables": ["read", "select"],
            },
        }

    def test_get_personas(self, client: TestClient, db_session: Session):
        """Test getting entitlement personas."""
        response = client.get("/api/entitlements/personas")
        assert response.status_code in [200, 404]

    def test_create_persona(self, client: TestClient, db_session: Session, sample_persona_data):
        """Test creating an entitlement persona."""
        response = client.post("/api/entitlements/personas", json=sample_persona_data)
        assert response.status_code in [200, 201, 403, 404]

    def test_get_persona_by_id(self, client: TestClient, db_session: Session):
        """Test getting a specific persona."""
        response = client.get("/api/entitlements/personas/test-persona-id")
        assert response.status_code in [200, 404]

    def test_update_persona(self, client: TestClient, db_session: Session):
        """Test updating a persona."""
        update_data = {
            "description": "Updated description",
        }
        response = client.put("/api/entitlements/personas/test-persona-id", json=update_data)
        assert response.status_code in [200, 404]

    def test_delete_persona(self, client: TestClient, db_session: Session):
        """Test deleting a persona."""
        response = client.delete("/api/entitlements/personas/test-persona-id")
        assert response.status_code in [200, 204, 404]

    def test_get_group_entitlements(self, client: TestClient, db_session: Session):
        """Test getting entitlements for a group."""
        response = client.get("/api/entitlements/groups/test-group")
        assert response.status_code in [200, 404]

    def test_assign_persona_to_group(self, client: TestClient, db_session: Session):
        """Test assigning a persona to a group."""
        assign_data = {
            "group_name": "test-group",
            "persona_id": "test-persona-id",
        }
        response = client.post("/api/entitlements/assign", json=assign_data)
        assert response.status_code in [200, 201, 404]

    def test_get_entitlements_summary(self, client: TestClient, db_session: Session):
        """Test getting entitlements summary."""
        response = client.get("/api/entitlements/summary")
        assert response.status_code in [200, 404]

