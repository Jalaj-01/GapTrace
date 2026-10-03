"""Integration Tests for Phase 7: Gap Genealogy and Gap Lifecycle API.

Tests end-to-end integration:
- Database & Research Knowledge Graph
- Candidate Generation Engine
- GET /api/v1/gaps/lifecycle/overview
- GET /api/v1/gaps/{gap_id}/timeline
- GET /api/v1/gaps/{gap_id}/genealogy
- GET /api/v1/gaps/{gap_id}/lifecycle
- Endpoint aliases and 404 error handling.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.paper import GapLifecycleStatus


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestPhase7LifecycleIntegration:
    """Integration test suite for Phase 7 lifecycle and genealogy endpoints."""

    def test_lifecycle_overview_endpoint(self, client: TestClient):
        """GET /api/v1/gaps/lifecycle/overview returns aggregate status counts."""
        response = client.get("/api/v1/gaps/lifecycle/overview")
        assert response.status_code == 200

        data = response.json()
        assert "total_gaps" in data
        assert "status_counts" in data
        assert "gaps" in data

        # Check all 6 lifecycle statuses are represented in dictionary keys
        for st in GapLifecycleStatus:
            assert st.value in data["status_counts"]

    def test_gap_timeline_endpoint(self, client: TestClient):
        """GET /api/v1/gaps/{gap_id}/timeline returns chronologically ordered events."""
        cand_resp = client.get("/api/v1/gaps/candidates?limit=1")
        assert cand_resp.status_code == 200
        candidates = cand_resp.json().get("candidates", [])

        if not candidates:
            pytest.skip("No candidate gaps available in current database fixture.")

        target_gap = candidates[0]
        gap_id = target_gap["gap_id"]

        response = client.get(f"/api/v1/gaps/{gap_id}/timeline")
        assert response.status_code == 200

        data = response.json()
        assert data["gap_id"] == gap_id
        assert "current_status" in data
        assert "events" in data
        assert data["total_events"] == len(data["events"])

        # Check chronological ordering
        years = [ev["year"] for ev in data["events"] if ev.get("year") is not None]
        assert years == sorted(years)

        # Check event structure
        for ev in data["events"]:
            assert "event_id" in ev
            assert "event_type" in ev
            assert "source_sentence" in ev
            assert "confidence" in ev

    def test_gap_genealogy_endpoint(self, client: TestClient):
        """GET /api/v1/gaps/{gap_id}/genealogy returns evolutionary chain transitions."""
        cand_resp = client.get("/api/v1/gaps/candidates?limit=1")
        assert cand_resp.status_code == 200
        candidates = cand_resp.json().get("candidates", [])

        if not candidates:
            pytest.skip("No candidate gaps available in current database fixture.")

        target_gap = candidates[0]
        gap_id = target_gap["gap_id"]

        response = client.get(f"/api/v1/gaps/{gap_id}/genealogy")
        assert response.status_code == 200

        data = response.json()
        assert data["gap_id"] == gap_id
        assert "root_limitation" in data
        assert "evolutionary_chain" in data
        assert "transitions" in data
        assert len(data["transitions"]) == data["total_transitions"]

        # Validate sequential step numbering
        for idx, trans in enumerate(data["transitions"], 1):
            assert trans["step_number"] == idx
            assert trans["stage_name"] != ""
            assert trans["source_sentence"] != ""
            assert "confidence" in trans

    def test_gap_lifecycle_detail_endpoint(self, client: TestClient):
        """GET /api/v1/gaps/{gap_id}/lifecycle returns lifecycle status and temporal reasoning."""
        cand_resp = client.get("/api/v1/gaps/candidates?limit=1")
        assert cand_resp.status_code == 200
        candidates = cand_resp.json().get("candidates", [])

        if not candidates:
            pytest.skip("No candidate gaps available in current database fixture.")

        target_gap = candidates[0]
        gap_id = target_gap["gap_id"]

        response = client.get(f"/api/v1/gaps/{gap_id}/lifecycle")
        assert response.status_code == 200

        data = response.json()
        assert data["gap_id"] == gap_id
        assert data["status"] in [st.value for st in GapLifecycleStatus]
        assert "status_reasoning" in data
        assert len(data["status_reasoning"]) > 10
        assert "evidence_paper_count" in data
        assert "year_span" in data

    def test_candidate_path_aliases(self, client: TestClient):
        """Verify both /{gap_id}/... and /candidates/{gap_id}/... path aliases work identically."""
        cand_resp = client.get("/api/v1/gaps/candidates?limit=1")
        assert cand_resp.status_code == 200
        candidates = cand_resp.json().get("candidates", [])

        if not candidates:
            pytest.skip("No candidate gaps available in current database fixture.")

        gap_id = candidates[0]["gap_id"]

        res_timeline = client.get(f"/api/v1/gaps/candidates/{gap_id}/timeline")
        assert res_timeline.status_code == 200

        res_genealogy = client.get(f"/api/v1/gaps/candidates/{gap_id}/genealogy")
        assert res_genealogy.status_code == 200

        res_lifecycle = client.get(f"/api/v1/gaps/candidates/{gap_id}/lifecycle")
        assert res_lifecycle.status_code == 200

    def test_nonexistent_gap_returns_404(self, client: TestClient):
        """Accessing lifecycle endpoints with unknown gap_id returns 404."""
        nonexistent_id = "nonexistent-gap-999"

        assert client.get(f"/api/v1/gaps/{nonexistent_id}/timeline").status_code == 404
        assert client.get(f"/api/v1/gaps/{nonexistent_id}/genealogy").status_code == 404
        assert client.get(f"/api/v1/gaps/{nonexistent_id}/lifecycle").status_code == 404
