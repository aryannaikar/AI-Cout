"""
FastAPI router for AI Court of India.
Provides endpoints for Case Packet upload, Server-Sent Events (SSE) streaming
of live courtroom proceedings, non-streaming runs, and artifact downloads.
Strictly isolates Ground Truth from entering the courtroom pipeline.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
import threading
from typing import Any, AsyncGenerator, Optional
from uuid import uuid4

import pymupdf
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.graph.validation import (
    BlindEvaluationViolation,
    validate_case_packet_path,
    validate_no_ground_truth_text,
)
from app.graph.workflow import CourtWorkflow, run_court

logger = logging.getLogger(__name__)

router = APIRouter()

# Directory to store validated uploaded case packets
def _get_upload_dir() -> Path:
    backend_dir = Path(__file__).resolve().parents[2]
    canonical = backend_dir / "data" / "cases" / "uploads"
    if canonical.exists():
        return canonical
    for cand in [Path("data/cases/uploads"), Path("backend/data/cases/uploads")]:
        if cand.exists():
            return cand.resolve()
    canonical.mkdir(parents=True, exist_ok=True)
    return canonical

UPLOAD_DIR = _get_upload_dir()


class UploadResponse(BaseModel):
    upload_id: str = Field(description="Unique upload identifier")
    filename: str = Field(description="Original filename of uploaded Case Packet")
    file_size: int = Field(description="Size in bytes")
    page_count: int = Field(description="Number of pages in the PDF")
    valid: bool = Field(default=True, description="Whether the Case Packet passed security validation")
    message: str = Field(description="Status description")


class StreamCourtRequest(BaseModel):
    upload_id: Optional[str] = Field(default=None, description="Identifier of uploaded Case Packet PDF")
    case_text: Optional[str] = Field(default=None, description="Raw structured case text (alternative to upload_id)")


@router.post("/upload", response_model=UploadResponse)
async def upload_case_packet(file: UploadFile = File(...)) -> UploadResponse:
    """
    Upload and validate a Case Packet PDF for courtroom simulation.
    Strictly validates that the file is not a Ground Truth / Verdict file.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty.",
        )

    # Validate file extension
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF Case Packets are supported (.pdf).",
        )

    # 1. Validate filename security (reject Ground Truth, Real Verdict files)
    try:
        validate_case_packet_path(file.filename)
    except BlindEvaluationViolation as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Security Violation: {e}",
        )

    # Read bytes
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # Verify PDF magic header (%PDF-)
    if not contents.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not appear to be a valid PDF.",
        )

    # 2. Inspect document text for hidden ground truth signatures
    try:
        doc = pymupdf.open(stream=contents, filetype="pdf")
        page_count = len(doc)
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        doc.close()

        validate_no_ground_truth_text(full_text)
    except BlindEvaluationViolation as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Security Violation: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to inspect PDF: {e}",
        )

    # Store file safely
    upload_id = f"up_{uuid4().hex[:12]}"
    dest_path = UPLOAD_DIR / f"{upload_id}_Case_Packet.pdf"
    dest_path.write_bytes(contents)

    logger.info("Case packet uploaded: '%s' (%d bytes, %d pages)", file.filename, len(contents), page_count)

    return UploadResponse(
        upload_id=upload_id,
        filename=file.filename,
        file_size=len(contents),
        page_count=page_count,
        valid=True,
        message="Case Packet successfully validated and staged for AI Court.",
    )


@router.post("/stream")
async def stream_court_proceedings(request: StreamCourtRequest):
    """
    Stream live courtroom debate and reasoning via Server-Sent Events (SSE).
    Clients receive progressive updates as each of the 10 agents executes.
    """
    target_case: Optional[str | Path] = None

    if request.upload_id:
        target_file = UPLOAD_DIR / f"{request.upload_id}_Case_Packet.pdf"
        if not target_file.exists():
            for cand_dir in [Path("data/cases/uploads"), Path("backend/data/cases/uploads")]:
                alt_file = cand_dir.resolve() / f"{request.upload_id}_Case_Packet.pdf"
                if alt_file.exists():
                    target_file = alt_file
                    break
        if not target_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Uploaded Case Packet with id '{request.upload_id}' not found.",
            )
        target_case = target_file
    elif request.case_text:
        target_case = request.case_text
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either upload_id or case_text.",
        )

    async def event_generator() -> AsyncGenerator[str, None]:
        queue: asyncio.Queue[Optional[dict[str, Any]]] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def run_trial_thread():
            try:
                workflow = CourtWorkflow()
                for event in workflow.stream_trial(target_case):
                    loop.call_soon_threadsafe(queue.put_nowait, event)
            except BlindEvaluationViolation as e:
                loop.call_soon_threadsafe(queue.put_nowait, {"type": "court_error", "message": f"Security Violation: {e}"})
            except Exception as e:
                logger.exception("Error during courtroom stream execution: %s", e)
                loop.call_soon_threadsafe(queue.put_nowait, {"type": "court_error", "message": f"Courtroom Execution Error: {e}"})
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        worker_thread = threading.Thread(target=run_trial_thread, daemon=True)
        worker_thread.start()

        while True:
            event = await queue.get()
            if event is None:
                break
            event_type = event.get("type", "message")
            data = json.dumps(event, default=str)
            yield f"event: {event_type}\ndata: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/run")
async def run_court_synchronous(request: StreamCourtRequest):
    """
    Non-streaming courtroom execution returning complete trial state and judgment.
    """
    target_case: Optional[str | Path] = None

    if request.upload_id:
        target_file = UPLOAD_DIR / f"{request.upload_id}_Case_Packet.pdf"
        if not target_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Uploaded Case Packet with id '{request.upload_id}' not found.",
            )
        target_case = target_file
    elif request.case_text:
        target_case = request.case_text
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either upload_id or case_text.",
        )

    try:
        final_state = run_court(target_case)
        return {
            "status": final_state.status,
            "case_id": final_state.case_id,
            "ai_judgment": final_state.judgment.model_dump() if final_state.judgment else None,
            "execution_report": final_state.execution_report.model_dump() if final_state.execution_report else None,
        }
    except BlindEvaluationViolation as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

@router.get("/cases/{case_id}/download/{format_type}")
async def download_judgment_artifact(case_id: str, format_type: str):
    """
    Download persisted AI Courtroom judgment artifacts (PDF, JSON, TXT) or execution report.
    """
    safe_id = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in case_id)
    backend_dir = Path(__file__).resolve().parents[2]
    out_dir = backend_dir / "data" / "cases" / safe_id / "output"

    format_map = {
        "pdf": ("ai_judgment.pdf", "application/pdf"),
        "json": ("ai_judgment.json", "application/json"),
        "txt": ("ai_judgment.txt", "text/plain"),
        "report": ("execution_report.json", "application/json"),
    }

    target_info = format_map.get(format_type.lower())
    if not target_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format '{format_type}'. Supported: pdf, json, txt, report",
        )

    filename, media_type = target_info
    target_path = out_dir / filename

    if not target_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact '{filename}' not found for case '{case_id}'.",
        )

    return FileResponse(path=str(target_path), media_type=media_type, filename=filename)


@router.get("/cases/{case_id}/judgment")
async def get_persisted_judgment(case_id: str):
    """Return the actual persisted AI judgment for a completed case."""
    safe_id = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in case_id)
    backend_dir = Path(__file__).resolve().parents[2]
    target_path = backend_dir / "data" / "cases" / safe_id / "output" / "ai_judgment.json"
    if not target_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No persisted AI judgment found for case '{case_id}'.")
    return JSONResponse(content=json.loads(target_path.read_text(encoding="utf-8")))
