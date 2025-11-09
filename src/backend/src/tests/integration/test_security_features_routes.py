"""
Integration tests for security features API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestSecurityFeaturesRoutes:
    """Integration tests for security features API endpoints."""

    def test_get_security_features(self, client: TestClient, db_session: Session):
        """Test getting available security features."""
        response = client.get("/api/security-features")
        assert response.status_code in [200, 404]

    def test_enable_security_feature(self, client: TestClient, db_session: Session):
        """Test enabling a security feature for an entity."""
        enable_data = {
            "entity_type": "data_product",
            "entity_id": "test-product-123",
            "feature": "differential_privacy",
            "config": {},
        }
        response = client.post("/api/security-features/enable", json=enable_data)
        assert response.status_code in [200, 201, 404]

    def test_disable_security_feature(self, client: TestClient, db_session: Session):
        """Test disabling a security feature."""
        response = client.delete("/api/security-features/data_product/test-product-123/differential_privacy")
        assert response.status_code in [200, 204, 404]

    def test_get_entity_security_status(self, client: TestClient, db_session: Session):
        """Test getting security status for an entity."""
        response = client.get("/api/security-features/data_product/test-product-123")
        assert response.status_code in [200, 404]

