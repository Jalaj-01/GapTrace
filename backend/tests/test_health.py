"""Tests for the health check and root endpoints."""

def test_root_endpoint(client):
    """Verify root / endpoint returns project metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "Scientific Paper Gap Finder"
    assert data["version"] == "0.1.0"
    assert "health_check" in data


def test_health_endpoint(client):
    """Verify /api/v1/health returns diagnostics structure."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "database" in data
    assert "services" in data
    assert data["services"]["api"] == "operational"
