"""Integration Tests for Phase 9: Evidence-Grounded RAG and LLM Synthesis API.

Tests end-to-end integration:
- POST /api/v1/gaps/{gap_id}/synthesize
- GET /api/v1/gaps/{gap_id}/synthesis
- POST /api/v1/gaps/validate-citations
- 404 on unknown gap candidates
- Error status code handling for timeout / rate limit
- Provider abstraction integration with MockLLMProvider.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.paper import CitationSource
from backend.app.services.llm.factory import set_global_mock_provider
from backend.app.services.llm.mock_provider import MockLLMProvider


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_mock_llm():
    """Ensure global mock provider is configured for integration tests."""
    mock_p = MockLLMProvider(mode="grounded")
    set_global_mock_provider(mock_p)
    yield mock_p
    set_global_mock_provider(None)


class TestPhase9SynthesisIntegration:
    """Integration test suite for Phase 9 synthesis endpoints."""

    def test_post_gap_synthesize_endpoint(self, client: TestClient):
        """POST /api/v1/gaps/{gap_id}/synthesize returns grounded synthesis with citations."""
        cand_resp = client.get("/api/v1/gaps/candidates?limit=1")
        assert cand_resp.status_code == 200
        candidates = cand_resp.json().get("candidates", [])

        if not candidates:
            pytest.skip("No candidate gaps available in database fixture.")

        gap_id = candidates[0]["gap_id"]

        req_payload = {
            "provider": "mock",
            "temperature": 0.2,
            "validate_citations": True,
        }
        response = client.post(f"/api/v1/gaps/{gap_id}/synthesize", json=req_payload)
        assert response.status_code == 200

        data = response.json()
        assert data["gap_id"] == gap_id
        assert data["provider"] == "mock"
        assert "gap_explanation" in data
        assert "why_it_matters" in data
        assert "supporting_evidence_summary" in data
        assert "counter_evidence_summary" in data
        assert "current_status" in data
        assert isinstance(data["potential_research_questions"], list)
        assert isinstance(data["potential_future_directions"], list)
        assert "evidence_limitations" in data
        assert "citations" in data
        assert "validation_report" in data
        assert data["validation_report"]["is_valid"] is True
        assert data["validation_report"]["evidence_support_rate"] > 0.50

    def test_get_gap_synthesis_endpoint(self, client: TestClient):
        """GET /api/v1/gaps/{gap_id}/synthesis returns cached or on-demand synthesis."""
        cand_resp = client.get("/api/v1/gaps/candidates?limit=1")
        assert cand_resp.status_code == 200
        candidates = cand_resp.json().get("candidates", [])

        if not candidates:
            pytest.skip("No candidate gaps available in database fixture.")

        gap_id = candidates[0]["gap_id"]

        response = client.get(f"/api/v1/gaps/{gap_id}/synthesis")
        assert response.status_code == 200

        data = response.json()
        assert data["gap_id"] == gap_id
        assert "gap_explanation" in data
        assert "citations" in data

    def test_post_validate_citations_standalone(self, client: TestClient):
        """POST /api/v1/gaps/validate-citations checks factual claims and citation validity."""
        payload = {
            "text": "Self-attention computational complexity remains quadratic across transformers [E1]. Imaginary solvers resolve all constraints [E99].",
            "citations": {
                "E1": {
                    "citation_id": "E1",
                    "sentence_text": "We confirm attention memory overhead remains quadratic across transformer models.",
                    "paper_title": "Limits of Attention",
                    "page": 3,
                    "section": "Analysis",
                }
            },
            "min_support_score": 0.50,
        }

        response = client.post("/api/v1/gaps/validate-citations", json=payload)
        assert response.status_code == 200

        report = response.json()
        assert report["total_claims"] == 2
        assert report["claims_with_citations"] == 2
        assert report["supported_claims"] == 1
        assert report["hallucinated_citations"] == 1
        assert report["is_valid"] is False
        assert any("E99" in r for r in report["rejection_reasons"])

    def test_synthesize_unknown_gap_returns_404(self, client: TestClient):
        """POST /api/v1/gaps/{unknown_id}/synthesize returns 404."""
        response = client.post("/api/v1/gaps/non-existent-gap-999/synthesize", json={})
        assert response.status_code == 404
        assert "not found" in response.json()["error"]["message"].lower()

    def test_synthesize_provider_timeout_error(self, client: TestClient, setup_mock_llm: MockLLMProvider):
        """POST /api/v1/gaps/{gap_id}/synthesize propagates timeout as 504 Gateway Timeout."""
        cand_resp = client.get("/api/v1/gaps/candidates?limit=1")
        if not cand_resp.json().get("candidates"):
            pytest.skip("No candidate gaps.")

        gap_id = cand_resp.json()["candidates"][0]["gap_id"]
        setup_mock_llm.set_mode("timeout")

        response = client.post(f"/api/v1/gaps/{gap_id}/synthesize", json={"provider": "mock"})
        assert response.status_code == 504
        assert "timeout" in response.json()["error"]["message"].lower()

    def test_synthesize_provider_rate_limit_error(self, client: TestClient, setup_mock_llm: MockLLMProvider):
        """POST /api/v1/gaps/{gap_id}/synthesize propagates rate limit as 429 Too Many Requests."""
        cand_resp = client.get("/api/v1/gaps/candidates?limit=1")
        if not cand_resp.json().get("candidates"):
            pytest.skip("No candidate gaps.")

        gap_id = cand_resp.json()["candidates"][0]["gap_id"]
        setup_mock_llm.set_mode("rate_limit")

        response = client.post(f"/api/v1/gaps/{gap_id}/synthesize", json={"provider": "mock"})
        assert response.status_code == 429
        assert "rate limit" in response.json()["error"]["message"].lower()
