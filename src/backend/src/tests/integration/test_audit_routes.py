"""
Integration tests for audit API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestAuditRoutes:
    """Integration tests for audit API endpoints."""

    def test_get_audit_logs(self, client: TestClient, db_session: Session):
        """Test getting audit logs."""
        response = client.get("/api/audit/logs")
        assert response.status_code == 200
        data = response.json()
        # Should return logs array and total count
        assert "logs" in data or isinstance(data, list)

    def test_get_audit_logs_pagination(self, client: TestClient, db_session: Session):
        """Test audit logs with pagination."""
        response = client.get("/api/audit/logs?skip=0&limit=10")
        assert response.status_code == 200

    def test_get_audit_logs_by_feature(self, client: TestClient, db_session: Session):
        """Test filtering audit logs by feature."""
        response = client.get("/api/audit/logs?feature=data_products")
        assert response.status_code == 200

    def test_get_audit_logs_by_username(self, client: TestClient, db_session: Session):
        """Test filtering audit logs by username."""
        response = client.get("/api/audit/logs?username=test@example.com")
        assert response.status_code == 200

    def test_get_audit_logs_by_action(self, client: TestClient, db_session: Session):
        """Test filtering audit logs by action."""
        response = client.get("/api/audit/logs?action=CREATE")
        assert response.status_code == 200

    def test_get_change_logs(self, client: TestClient, db_session: Session):
        """Test getting change logs."""
        response = client.get("/api/audit/changes")
        assert response.status_code == 200

    def test_get_change_logs_by_entity(self, client: TestClient, db_session: Session):
        """Test getting change logs for specific entity."""
        response = client.get("/api/audit/changes/data_product/test-id")
        assert response.status_code == 200 or response.status_code == 404

    def test_get_audit_stats(self, client: TestClient, db_session: Session):
        """Test getting audit statistics."""
        response = client.get("/api/audit/stats")
        assert response.status_code == 200
        # Should return statistics object
        assert isinstance(response.json(), dict)

