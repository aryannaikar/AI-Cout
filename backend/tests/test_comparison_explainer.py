"""Tests for the read-only 'Understand the Difference' explainer."""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import comparison_routes
from app.comparison import explainer
from app.comparison.explainer import (
    DifferenceExplanation,
    KeyDifference,
    explain_differences,
)
from app.comparison.service import ComparisonService

REAL_JUDGMENT = """
IN THE SUPREME COURT OF INDIA
CRIMINAL APPEAL NO. 452/2023
State v. Ramesh Kumar
JUDGMENT
1. The accused was charged under Section 379 of the Indian Penal Code, 1860.
2. The key issue is whether the prosecution proved possession of stolen property beyond reasonable doubt.
3. PW1 and PW2 gave contradictory statements regarding the recovery of the money.
4. Independent witnesses were not joined during the seizure and the seizure memo was not proved.
5. In view of material inconsistencies, the benefit of doubt is extended to the accused.
VERDICT: ACQUITTAL.
The accused is hereby acquitted of all framed charges.
"""

AI_JUDGMENT = {
    "case_title": "State v. Ramesh Kumar",
    "verdict": "CONVICTION",
    "summary": "The Court finds the accused guilty of theft under Section 379 IPC based on the recovery from his house.",
    "operative_order": "CONVICTION under Section 379 IPC.",
}


@pytest.fixture()
def comparison():
    service = ComparisonService()
    report = service.compare_manual(
        ai_judgment_source=json.dumps(AI_JUDGMENT).encode(),
        real_judgment_source=REAL_JUDGMENT.encode(),
        case_id="EXPLAIN-1",
    )
    return report, service.last_context


def test_fallback_explanation_is_grounded_and_labelled(monkeypatch, comparison):
    report, ctx = comparison
    monkeypatch.setattr(explainer, "_llm_explanation", lambda *_a, **_k: None)
    before = report.model_dump_json()

    out = explain_differences(report, ctx["ai"], ctx["real"], ctx["packet_text"])

    assert out.generated_by == "deterministic_fallback"
    assert out.key_differences, "expected at least one difference item"
    assert out.why_judgments_differ
    assert {d.basis for d in out.key_differences} <= {"from_judgments", "ai_analysis", "information_unavailable"}
    # Investigation problems come only from the real judgment text.
    inv = [d for d in out.key_differences if d.category == "investigation"]
    assert inv and "seizure" in inv[0].real_court_view.lower()
    # Read-only guarantee.
    assert report.model_dump_json() == before


def test_unavailable_information_is_reported_not_guessed(monkeypatch, comparison):
    report, _ = comparison
    monkeypatch.setattr(explainer, "_llm_explanation", lambda *_a, **_k: None)
    out = explain_differences(report, None, None, None)
    assert out.unavailable_information
    assert any("case packet" in item.lower() for item in out.unavailable_information)


def test_llm_output_is_used_but_verdict_anchors_stay_deterministic(monkeypatch, comparison):
    report, ctx = comparison
    fake = DifferenceExplanation(
        verdicts_differ=False,  # LLM tries to claim verdicts match
        why_judgments_differ="The AI trusted the recovery; the real judge doubted it.",
        key_differences=[KeyDifference(category="evidence", title="Recovery", ai_view="a", real_court_view="b",
                                       why_different="c", basis="from_judgments")],
    )
    monkeypatch.setattr(explainer, "_llm_explanation", lambda *_a, **_k: fake)
    out = explain_differences(report, ctx["ai"], ctx["real"], ctx["packet_text"])
    assert out.generated_by == "llm"
    assert out.verdicts_differ == (report.verdict_comparison.alignment != "aligned")
    assert out.why_judgments_differ.startswith("The AI trusted")
    assert out.real_court_concluded  # filled from deterministic data when LLM omitted it


def test_endpoint_returns_explanation_and_404_without_report(monkeypatch, comparison):
    report, ctx = comparison
    monkeypatch.setattr(explainer, "_llm_explanation", lambda *_a, **_k: None)
    app = FastAPI()
    app.include_router(comparison_routes.router, prefix="/api")
    client = TestClient(app)

    assert client.post("/api/cases/NOPE/comparison/explain").status_code == 404

    comparison_routes._reports_by_case_id["EXPLAIN-1"] = report
    comparison_routes._context_by_case_id["EXPLAIN-1"] = ctx
    resp = client.post("/api/cases/EXPLAIN-1/comparison/explain")
    assert resp.status_code == 200
    body = resp.json()
    assert body["key_differences"] and body["disclaimer"]

    # Works from a client-supplied report after a server restart.
    comparison_routes._reports_by_case_id.clear()
    comparison_routes._context_by_case_id.clear()
    resp = client.post("/api/cases/EXPLAIN-1/comparison/explain", json={"report": json.loads(report.model_dump_json())})
    assert resp.status_code == 200


def test_jargon_heavy_reasons_are_rewritten_in_plain_words(monkeypatch, comparison):
    report, ctx = comparison
    heavy = DifferenceExplanation(
        simple_summary="The AI assessed whether the presumption under Section 114 of the Indian Evidence Act could apply.",
        main_reasons=["The AI Court assessed whether the presumption under Section 114 of the Indian Evidence Act could apply, "
                      "noting the prosecution failed to prove the stolen amount with circumstantial proof."],
        key_differences=[KeyDifference(category="evidence", title="t", ai_view="a", real_court_view="b", why_different="c")],
    )
    monkeypatch.setattr(explainer, "_llm_explanation", lambda *_a, **_k: heavy)
    monkeypatch.setattr(
        explainer, "_simplify_with_llm",
        lambda *_a, **_k: explainer._SimpleText(
            simple_summary="Nobody proved the cash was stolen.",
            main_reasons=["Nobody proved the cash was really stolen, so keeping it was not a crime."],
        ),
    )
    out = explain_differences(report, ctx["ai"], ctx["real"], ctx["packet_text"])
    assert out.main_reasons == ["Nobody proved the cash was really stolen, so keeping it was not a crime."]
    assert "Section" not in out.simple_summary


def test_if_simplifier_fails_plain_fallback_reasons_replace_jargon(monkeypatch, comparison):
    report, ctx = comparison
    heavy = DifferenceExplanation(
        simple_summary="Short and plain.",
        main_reasons=["Under Section 114 the presumption of burden was circumstantial."],
        key_differences=[KeyDifference(category="evidence", title="t", ai_view="a", real_court_view="b", why_different="c")],
    )
    monkeypatch.setattr(explainer, "_llm_explanation", lambda *_a, **_k: heavy)
    monkeypatch.setattr(explainer, "_simplify_with_llm", lambda *_a, **_k: None)
    out = explain_differences(report, ctx["ai"], ctx["real"], ctx["packet_text"])
    assert not any("presumption" in r.lower() for r in out.main_reasons)
