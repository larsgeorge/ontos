from fastapi.testclient import TestClient

# test_settings fixture is not directly used here, but the client fixture uses it.
# from src.common.config import Settings # Not strictly needed for this test


def test_get_settings(client: TestClient):
    """Test GET /api/settings endpoint."""
    response = client.get("/api/settings")
    print("/api/settings response text:", response.text)
    assert response.status_code == 200

    response_data = response.json()

    # Check for top-level keys
    assert "job_clusters" in response_data
    assert "current_settings" in response_data
    assert "available_jobs" in response_data

    # Check job_clusters (mocked to be empty)
    assert response_data["job_clusters"] == []

    # Check available_jobs (based on SettingsManager._available_jobs)
    # This list might change, so it's good to be aware if this test breaks due to it.
    expected_available_jobs = [
        'data_contracts',
        'business_glossaries',
        'entitlements',
        'mdm_jobs',
        'catalog_commander_jobs'
    ]
    assert response_data["available_jobs"] == expected_available_jobs

    # Check current_settings (based on test_settings fixture and Settings.to_dict())
    current_settings = response_data["current_settings"]
    assert current_settings["job_cluster_id"] is None
    assert current_settings["sync_enabled"] is False
    assert current_settings["sync_repository"] is None
    assert current_settings["enabled_jobs"] == []
    assert current_settings["updated_at"] is None 