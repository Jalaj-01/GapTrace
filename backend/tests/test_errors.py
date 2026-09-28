"""Tests for centralized error handling and custom exceptions."""

from backend.app.core.errors import NotFoundError, AppException


def test_not_found_error_structure(client):
    """Verify requesting a non-existent paper returns formatted JSON error envelope."""
    response = client.get("/api/v1/papers/999999")
    assert response.status_code == 404
    payload = response.json()
    assert payload["success"] is False
    assert "error" in payload
    assert payload["error"]["code"] == "NOT_FOUND"
    assert "Paper with ID 999999 not found" in payload["error"]["message"]


def test_validation_error_structure(client):
    """Verify invalid payloads trigger 422 with structured validation error envelope."""
    response = client.post("/api/v1/papers", json={"invalid_field": 123})
    assert response.status_code == 422
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "VALIDATION_ERROR"
