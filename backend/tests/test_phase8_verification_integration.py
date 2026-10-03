"""Integration Tests for Phase 8: Counter-Evidence Search and Gap Verification API.

Tests end-to-end integration:
- Database & Research Knowledge Graph
- Candidate Generation Engine
- GET /api/v1/gaps/{gap_id}/verification
- GET /api/v1/gaps/{gap_id}/counter-evidence
- POST /api/v1/gaps/{gap_id}/verify
- Endpoint aliases and 404 error handling.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.paper import GapVerificationFinalStatus


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestPhase8VerificationIntegration:
    """Integration test suite for Phase 8 verification endpoints."""

    def test_get_gap_verification_endpoint(self, client: TestClient):
        """GET /api/v1/gaps/{gap_id}/verification returns multi-category verification result."""
        cand_resp = client.get("/api/v1/gaps/candidates?limit=1")
        assert cand_resp.status_code == 200
        candidates = cand_resp.json().get("candidates", [])

        if not candidates:
            pytest.skip("No candidate gaps available in current database fixture.")

        gap_id = candidates[0]["gap_id"]

        response = client.get(f"/api/v1/gaps/{gap_id}/verification")
        assert response.status_code == 200

        data = response.json()
        assert data["gap_id"] == gap_id
        assert "supporting_evidence" in data
        assert "counter_evidence" in data
        assert "addressed_by_evidence" in data
        assert "contradictory_evidence" in data
        assert "evidence_dates" in data
        assert "verification_confidence" in data
        assert data["final_status"] in [st.value for st in GapVerificationFinalStatus]
        assert "status_reasoning" in data

    def test_get_gap_counter_evidence_endpoint(self, client: TestClient):
        """GET /api/v1/gaps/{gap_id}/counter-evidence returns opposing and contradictory evidence."""
        cand_resp = client.get("/api/v1/gaps/candidates?limit=1")
        assert cand_resp.status_code == 200
        candidates = cand_resp.json().get("candidates", [])

        if not candidates:
            pytest.skip("No candidate gaps available in current database fixture.")

        gap_id = candidates[0]["gap_id"]

        response = client.get(f"/api/v1/gaps/{gap_id}/counter-evidence")
        assert response.status_code == 200

        data = response.json()
        assert data["gap_id"] == gap_id
        assert "counter_evidence" in data
        assert "addressed_by_evidence" in data
        assert "contradictory_evidence" in data
        assert "total_counter_items" in data
        assert data["total_counter_items"] == len(data["counter_evidence"]) + len(data["addressed_by_evidence"]) + len(data["contradictory_evidence"])

    def test_post_gap_verify_endpoint(self, client: TestClient):
        """POST /api/v1/gaps/{gap_id}/verify triggers active verification and returns updated result."""
        cand_resp = client.get("/api/v1/gaps/candidates?limit=1")
        assert cand_resp.status_code == 200
        candidates = cand_resp.json().get("candidates", [])

        if not candidates:
            pytest.skip("No candidate gaps available in current database fixture.")

        gap_id = candidates[0]["gap_id"]

        response = client.post(
            f"/api/v1/gaps/{gap_id}/verify",
            json={"min_confidence": 0.60, "include_nli": True},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["gap_id"] == gap_id
        assert "nli_distribution" in data
        assert "verified_at" in data

    def test_candidate_path_aliases(self, client: TestClient):
        """Verify both /{gap_id}/... and /candidates/{gap_id}/... path aliases work identically."""
        cand_resp = client.get("/api/v1/gaps/candidates?limit=1")
        assert cand_resp.status_code == 200
        candidates = cand_resp.json().get("candidates", [])

        if not candidates:
            pytest.skip("No candidate gaps available in current database fixture.")

        gap_id = candidates[0]["gap_id"]

        res_verif = client.get(f"/api/v1/gaps/candidates/{gap_id}/verification")
        assert res_verif.status_code == 200

        res_counter = client.get(f"/api/v1/gaps/candidates/{gap_id}/counter-evidence")
        assert res_counter.status_code == 200

        res_verify_post = client.post(
            f"/api/v1/gaps/candidates/{gap_id}/verify",
            json={"min_confidence": 0.60, "include_nli": True},
        )
        assert res_verify_post.status_code == 200

    def test_nonexistent_gap_returns_404(self, client: TestClient):
        """Accessing verification endpoints with unknown gap_id returns 404."""
        nonexistent_id = "nonexistent-gap-999"

        assert client.get(f"/api/v1/gaps/{nonexistent_id}/verification").status_code == 404
        assert client.get(f"/api/v1/gaps/{nonexistent_id}/counter-evidence").status_code == 404
        assert client.post(f"/api/v1/gaps/{nonexistent_id}/verify").status_code == 404
