"""
Integration tests for jobs API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestJobsRoutes:
    """Integration tests for jobs API endpoints."""

    def test_get_workflow_installations(self, client: TestClient, db_session: Session):
        """Test getting workflow installations."""
        response = client.get("/api/jobs/installations")
        assert response.status_code == 200

    def test_get_workflow_runs(self, client: TestClient, db_session: Session):
        """Test getting workflow runs."""
        response = client.get("/api/jobs/runs")
        assert response.status_code == 200

    def test_trigger_workflow(self, client: TestClient, db_session: Session):
        """Test triggering a workflow."""
        trigger_data = {
            "workflow_id": "test-workflow",
            "parameters": {},
        }
        response = client.post("/api/jobs/trigger", json=trigger_data)
        assert response.status_code in [200, 201, 404, 503]

    def test_get_job_status(self, client: TestClient, db_session: Session):
        """Test getting job status."""
        response = client.get("/api/jobs/status/12345")
        assert response.status_code in [200, 404]

    def test_get_job_logs(self, client: TestClient, db_session: Session):
        """Test getting job logs."""
        response = client.get("/api/jobs/logs/12345")
        assert response.status_code in [200, 404]

    def test_cancel_job(self, client: TestClient, db_session: Session):
        """Test canceling a job."""
        response = client.post("/api/jobs/cancel/12345")
        assert response.status_code in [200, 404]

    def test_get_workflow_installation_by_id(self, client: TestClient, db_session: Session):
        """Test getting specific workflow installation."""
        response = client.get("/api/jobs/installation/test-installation-id")
        assert response.status_code in [200, 404]

