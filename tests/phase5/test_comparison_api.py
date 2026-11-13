"""
Phase 5 Tests: FastAPI Comparison Endpoints.
Verifies REST API routes for Post-Trial comparison, Manual comparison,
and artifact downloads.
"""

from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_api_manual_comparison_endpoint(
    client: TestClient, synthetic_ai_judgment_json: str, real_court_judgment_text: str
):
    """Verify POST /api/comparison/manual accepts uploaded files and returns ComparisonReport."""
    files = {
        "ai_judgment": ("ai_judgment.json", BytesIO(synthetic_ai_judgment_json.encode("utf-8")), "application/json"),
        "real_judgment": ("real_judgment.txt", BytesIO(real_court_judgment_text.encode("utf-8")), "text/plain"),
    }
    response = client.post("/api/comparison/manual", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "manual"
    assert "scores" in data
    assert "verdict_comparison" in data
    assert data["scores"]["verdict_alignment"] == 100.0


def test_api_manual_comparison_empty_file_rejected(client: TestClient):
    """Verify empty uploads in manual comparison return 400."""
    files = {
        "ai_judgment": ("ai_judgment.json", BytesIO(b""), "application/json"),
        "real_judgment": ("real_judgment.txt", BytesIO(b"content"), "text/plain"),
    }
    response = client.post("/api/comparison/manual", files=files)
    assert response.status_code == 400


def test_api_post_trial_compare_existing_case(
    client: TestClient, real_court_judgment_text: str
):
    """
    Verify POST /api/cases/{case_id}/compare for CASE-2024-001
    (which has ai_judgment.json already persisted from Phase 4).
    """
    case_id = "CASE-2024-001"
    case_out_dir = Path("backend/data/cases") / case_id / "output"

    if (case_out_dir / "ai_judgment.json").exists():
        files = {
            "real_judgment_file": ("real_verdict.txt", BytesIO(real_court_judgment_text.encode("utf-8")), "text/plain"),
        }
        response = client.post(f"/api/cases/{case_id}/compare", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["case_id"] == case_id
        assert data["mode"] == "post_trial"

        # Verify download endpoints
        res_json = client.get(f"/api/cases/{case_id}/comparison/download/json")
        assert res_json.status_code == 200
        assert res_json.headers["content-type"] == "application/json"

        res_txt = client.get(f"/api/cases/{case_id}/comparison/download/txt")
        assert res_txt.status_code == 200
        assert "text/plain" in res_txt.headers["content-type"]

        res_pdf = client.get(f"/api/cases/{case_id}/comparison/download/pdf")
        assert res_pdf.status_code == 200
        assert res_pdf.headers["content-type"] == "application/pdf"


def test_api_post_trial_compare_nonexistent_case(client: TestClient):
    """Verify comparing non-existent case returns 404."""
    files = {
        "real_judgment_file": ("real.txt", BytesIO(b"Text of judgment"), "text/plain"),
    }
    response = client.post("/api/cases/NON_EXISTENT_CASE_9999/compare", files=files)
    assert response.status_code == 404


def test_api_comparison_download_invalid_format(client: TestClient):
    """Verify requesting invalid format returns 400."""
    response = client.get("/api/cases/CASE-2024-001/comparison/download/docx")
    assert response.status_code == 400
