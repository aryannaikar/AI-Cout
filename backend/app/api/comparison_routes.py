"""
FastAPI Router for Phase 5 — AI Court Judgment Comparison Engine.
Provides endpoints for Post-Trial Comparison and Manual Standalone Comparison.
All results are computed in-memory and returned directly — no disk reads/writes.
Guarantees strict isolation of Ground Truth from courtroom simulation endpoints.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.comparison.errors import (
    AIJudgmentNotFoundError,
    ComparisonError,
    InvalidJudgmentFormatError,
    RealJudgmentNotFoundError,
)
from app.comparison.schemas import ComparisonReport
from app.comparison.service import ComparisonService

logger = logging.getLogger(__name__)

router = APIRouter()


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
        return report
    except AIJudgmentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RealJudgmentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except InvalidJudgmentFormatError as e:
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
        return report
    except InvalidJudgmentFormatError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during manual comparison: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
