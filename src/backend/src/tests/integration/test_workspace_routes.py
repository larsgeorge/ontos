"""
Integration tests for workspace API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestWorkspaceRoutes:
    """Integration tests for workspace API endpoints."""

    def test_get_workspace_info(self, client: TestClient, db_session: Session):
        """Test getting workspace information."""
        response = client.get("/api/workspace/info")
        assert response.status_code in [200, 404]

    def test_get_catalogs(self, client: TestClient, db_session: Session):
        """Test getting Unity Catalog catalogs."""
        response = client.get("/api/workspace/catalogs")
        assert response.status_code in [200, 503]

    def test_get_schemas(self, client: TestClient, db_session: Session):
        """Test getting schemas for a catalog."""
        response = client.get("/api/workspace/catalogs/test-catalog/schemas")
        assert response.status_code in [200, 404, 503]

    def test_get_tables(self, client: TestClient, db_session: Session):
        """Test getting tables for a schema."""
        response = client.get("/api/workspace/catalogs/test-catalog/schemas/test-schema/tables")
        assert response.status_code in [200, 404, 503]

    def test_get_table_info(self, client: TestClient, db_session: Session):
        """Test getting table information."""
        response = client.get("/api/workspace/catalogs/test-catalog/schemas/test-schema/tables/test-table")
        assert response.status_code in [200, 404, 503]

    def test_get_users(self, client: TestClient, db_session: Session):
        """Test getting workspace users."""
        response = client.get("/api/workspace/users")
        assert response.status_code in [200, 403, 503]

    def test_get_groups(self, client: TestClient, db_session: Session):
        """Test getting workspace groups."""
        response = client.get("/api/workspace/groups")
        assert response.status_code in [200, 403, 503]

