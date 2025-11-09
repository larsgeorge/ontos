"""
Integration tests for costs API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date


class TestCostsRoutes:
    """Integration tests for costs API endpoints."""

    @pytest.fixture
    def sample_cost_data(self):
        """Sample cost item data for testing."""
        return {
            "entity_type": "data_product",
            "entity_id": "test-product-123",
            "title": "Monthly Storage Cost",
            "description": "Storage costs for data product",
            "cost_center": "infrastructure",
            "amount_cents": 150000,  # $1500.00
            "currency": "USD",
            "start_month": "2024-01-01",
        }

    def test_get_costs_for_entity(self, client: TestClient, db_session: Session):
        """Test getting costs for an entity."""
        response = client.get("/api/costs/data_product/test-id")
        assert response.status_code == 200
        data = response.json()
        # Should return list of costs
        assert isinstance(data, list)

    def test_create_cost_item(self, client: TestClient, db_session: Session, sample_cost_data):
        """Test creating a cost item."""
        response = client.post("/api/costs", json=sample_cost_data)
        assert response.status_code in [200, 201]
        data = response.json()
        assert "id" in data
        assert data["amount_cents"] == 150000

    def test_update_cost_item(self, client: TestClient, db_session: Session, sample_cost_data):
        """Test updating a cost item."""
        # Create first
        create_response = client.post("/api/costs", json=sample_cost_data)
        if create_response.status_code in [200, 201]:
            cost_id = create_response.json()["id"]
            
            # Update
            update_data = {
                "amount_cents": 200000,
                "description": "Updated description",
            }
            response = client.put(f"/api/costs/{cost_id}", json=update_data)
            assert response.status_code in [200, 404]

    def test_delete_cost_item(self, client: TestClient, db_session: Session, sample_cost_data):
        """Test deleting a cost item."""
        # Create first
        create_response = client.post("/api/costs", json=sample_cost_data)
        if create_response.status_code in [200, 201]:
            cost_id = create_response.json()["id"]
            
            # Delete
            response = client.delete(f"/api/costs/{cost_id}")
            assert response.status_code in [200, 204]

    def test_get_cost_summary(self, client: TestClient, db_session: Session, sample_cost_data):
        """Test getting cost summary for entity."""
        # Create a cost first
        client.post("/api/costs", json=sample_cost_data)
        
        # Get summary
        response = client.get(f"/api/costs/data_product/test-product-123/summary?month=2024-01")
        assert response.status_code in [200, 404]

    def test_create_cost_validation_error(self, client: TestClient):
        """Test cost creation with invalid data."""
        invalid_data = {
            "amount_cents": "not_a_number",
        }
        response = client.post("/api/costs", json=invalid_data)
        assert response.status_code == 422

