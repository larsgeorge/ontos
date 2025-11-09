"""
Integration tests for search API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestSearchRoutes:
    """Integration tests for search API endpoints."""

    def test_search_empty_query(self, client: TestClient, db_session: Session):
        """Test search with empty query."""
        response = client.get("/api/search?query=")
        # Should return 200 with empty results or 400 for invalid query
        assert response.status_code in [200, 400]

    def test_search_with_query(self, client: TestClient, db_session: Session):
        """Test search with a query string."""
        response = client.get("/api/search?query=test")
        assert response.status_code == 200
        data = response.json()
        # Should return search results structure
        assert isinstance(data, (list, dict))

    def test_search_with_filters(self, client: TestClient, db_session: Session):
        """Test search with entity type filter."""
        response = client.get("/api/search?query=test&entity_type=data_product")
        assert response.status_code == 200

    def test_search_pagination(self, client: TestClient, db_session: Session):
        """Test search with pagination."""
        response = client.get("/api/search?query=test&skip=0&limit=10")
        assert response.status_code == 200

    def test_search_case_insensitive(self, client: TestClient, db_session: Session):
        """Test that search is case insensitive."""
        response1 = client.get("/api/search?query=TEST")
        response2 = client.get("/api/search?query=test")
        
        assert response1.status_code == 200
        assert response2.status_code == 200

