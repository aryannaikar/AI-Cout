"""
FastAPI Router for Phase 5 — AI Court Judgment Comparison Engine.
Provides endpoints for Post-Trial Comparison and Manual Standalone Comparison.
All results are computed in-memory and returned directly — no disk reads/writes.
Guarantees strict isolation of Ground Truth from courtroom simulation endpoints.
"""

from __future__ import annotations

import logging
import json
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.comparison.errors import (
    AIJudgmentNotFoundError,
    CaseIdentityMismatchError,
    ComparisonError,
    InvalidJudgmentFormatError,
    RealJudgmentNotFoundError,
)
from app.comparison.explainer import DifferenceExplanationResponse, explain_differences
from app.comparison.schemas import ComparisonReport
from app.comparison.report_generator import ComparisonReportGenerator
from app.comparison.service import ComparisonService

logger = logging.getLogger(__name__)

router = APIRouter()
# Reports are deliberately session-local: download routes expose the generated
# comparison, never the uploaded ground-truth document, and write no case data.
_reports_by_case_id: dict[str, ComparisonReport] = {}
# Normalised judgments kept only to feed the read-only difference explainer.
_context_by_case_id: dict[str, dict] = {}


class ExplainDifferenceRequest(BaseModel):
    """Optional body: lets the client resend its report if the server session was restarted."""
    report: Optional[ComparisonReport] = None


@router.post("/cases/{case_id}/compare", response_model=ComparisonReport)
async def post_trial_compare(
    case_id: str,
    ai_judgment_file: UploadFile = File(..., description="AI Judgment file (JSON or TXT) produced by the courtroom run"),
    real_judgment_file: UploadFile = File(..., description="Authoritative Real Court Judgment PDF/TXT/JSON"),
    case_packet_file: Optional[UploadFile] = File(default=None, description="Optional supporting Case Packet PDF/TXT"),
) -> ComparisonReport:
    """
    Post-Trial Comparison.
    Both AI Judgment and Real Court Judgment must be supplied by the caller directly.
    No files are read from or written to disk.
    """
    ai_bytes = await ai_judgment_file.read()
    real_bytes = await real_judgment_file.read()
    packet_bytes = await case_packet_file.read() if case_packet_file else None

    if not ai_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="AI Judgment file is empty.")
    if not real_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Real Court Judgment file is empty.")

    service = ComparisonService()
    try:
        report = service.compare_post_trial(
            case_id=case_id,
            ai_judgment_source=ai_bytes,
            real_judgment_source=real_bytes,
            case_packet_source=packet_bytes,
        )
        _reports_by_case_id[case_id] = report
        _context_by_case_id[case_id] = dict(getattr(service, "last_context", {}) or {})
        return report
    except AIJudgmentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RealJudgmentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except InvalidJudgmentFormatError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except CaseIdentityMismatchError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except ComparisonError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during post-trial comparison: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/comparison/manual", response_model=ComparisonReport)
async def manual_standalone_compare(
    ai_judgment: UploadFile = File(..., description="AI Judgment file (JSON, TXT, or PDF)"),
    real_judgment: UploadFile = File(..., description="Real Court Judgment file (PDF, TXT, or JSON)"),
    case_packet: Optional[UploadFile] = File(default=None, description="Optional supporting Case Packet PDF/TXT"),
) -> ComparisonReport:
    """
    Manual Standalone Comparison between user-supplied AI Judgment and Real Court Judgment.
    Optional Case Packet is supporting context only.
    Does NOT execute the courtroom pipeline. Results returned in-memory only.
    """
    ai_bytes = await ai_judgment.read()
    real_bytes = await real_judgment.read()
    packet_bytes = await case_packet.read() if case_packet else None

    if not ai_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="AI Judgment file is empty.")
    if not real_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Real Court Judgment file is empty.")

    service = ComparisonService()
    try:
        report = service.compare_manual(
            ai_judgment_source=ai_bytes,
            real_judgment_source=real_bytes,
            case_packet_source=packet_bytes,
        )
        _reports_by_case_id[report.case_id] = report
        _context_by_case_id[report.case_id] = dict(getattr(service, "last_context", {}) or {})
        return report
    except InvalidJudgmentFormatError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except CaseIdentityMismatchError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during manual comparison: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/cases/{case_id}/comparison/explain", response_model=DifferenceExplanationResponse)
def explain_comparison_difference(
    case_id: str,
    body: Optional[ExplainDifferenceRequest] = None,
) -> DifferenceExplanationResponse:
    """
    "Understand the Difference": plain-language explanation of why the AI Court and the real
    court differ. Read-only — it never regenerates or alters either judgment or the report.
    """
    report = _reports_by_case_id.get(case_id) or (body.report if body else None)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No comparison report is available for this case. Run the comparison first.",
        )
    ctx = _context_by_case_id.get(case_id) or {}
    try:
        return explain_differences(
            report=report,
            ai_judgment=ctx.get("ai"),
            real_judgment=ctx.get("real"),
            packet_text=ctx.get("packet_text"),
        )
    except Exception as e:
        logger.exception("Difference explanation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate the explanation right now. Please try again.",
        )


def _report_for_download(case_id: str) -> ComparisonReport:
    report = _reports_by_case_id.get(case_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No comparison report is available for this case in the current server session. Run comparison again.",
        )
    return report


@router.get("/cases/{case_id}/comparison/download/txt")
async def download_comparison_txt(case_id: str) -> Response:
    report = _report_for_download(case_id)
    content = ComparisonReportGenerator.format_report_text(report)
    return Response(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="comparison-{case_id}.txt"'},
    )


@router.get("/cases/{case_id}/comparison/download/json")
async def download_comparison_json(case_id: str) -> Response:
    report = _report_for_download(case_id)
    return Response(
        content=json.dumps(report.model_dump(mode="json"), indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="comparison-{case_id}.json"'},
    )


@router.get("/cases/{case_id}/comparison/download/pdf")
async def download_comparison_pdf(case_id: str) -> Response:
    report = _report_for_download(case_id)
    report_text = ComparisonReportGenerator.format_report_text(report)
    temp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        ComparisonReportGenerator.write_report_pdf(report_text, temp_path)
        content = temp_path.read_bytes()
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="comparison-{case_id}.pdf"'},
    )
