"""
NVIDIA NIM Primary + Ollama Backup Provider Migration & Failover Test Suite.
Covers Part G Sections 9-12:
1. NVIDIA primary succeeds — Ollama is not called.
2. NVIDIA times out — retries then fails over to Ollama.
3. NVIDIA returns HTTP 429 — retries then fails over to Ollama.
4. NVIDIA returns retryable 5xx — fails over after bounded retries.
5. NVIDIA connection fails — fails over to Ollama.
6. Ollama unavailable or model missing — clear error is returned.
7. NVIDIA recovers after cooldown — subsequent requests return to NVIDIA.
8. Both providers fail — controlled error handling.
9. Non-retryable client errors (400/401/403) do NOT trigger failover.
10. Provider switching is logged and API keys never appear in logs.
11. OpenRouter remains selectable and JudgeAgent uses central LLMService.
"""

from __future__ import annotations

import logging
from pathlib import Path
import sys
import time
from unittest.mock import MagicMock

import httpx
from pydantic import BaseModel
import pytest

_ROOT = Path(__file__).resolve().parents[1]
_BACKEND = _ROOT / "backend"
for p in (str(_BACKEND), str(_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.agents.judge_agent import JudgeAgent
from app.core.llm_provider import (
    FailoverLLMManager,
    LLMConfig,
    LLMProvider,
    NvidiaLLMClient,
    OllamaLLMClient,
    OpenRouterLLMClient,
)
from app.graph.workflow import create_court_graph


class _MiniSchema(BaseModel):
    section: str
    act: str


def _http_status_error(code: int) -> httpx.HTTPStatusError:
    req = httpx.Request("POST", "https://integrate.api.nvidia.com/v1/chat/completions")
    resp = httpx.Response(code, request=req)
    return httpx.HTTPStatusError(f"HTTP {code}", request=req, response=resp)


def test_1_nvidia_succeeds_ollama_not_called():
    primary = MagicMock(model="nvidia/nemotron-3.5-lightning-30b-a3b")
    primary.generate_text.return_value = "NVIDIA OK"
    backup = MagicMock(model="qwen3:4b")

    mgr = FailoverLLMManager(primary=primary, backup=backup, max_retries=2, backoff_seconds=0.0)
    out = mgr.generate_text("Hello", agent_name="prosecutor")

    assert out == "NVIDIA OK"
    assert primary.generate_text.call_count == 1
    assert backup.generate_text.call_count == 0
    assert mgr.last_active_provider == "nvidia"
    assert mgr.usage_stats["primary_success"] == 1
    assert mgr.usage_stats["failovers"] == 0


def test_2_nvidia_timeout_fails_over_to_ollama():
    primary = MagicMock(model="nvidia/nemotron-3.5-lightning-30b-a3b")
    primary.generate_text.side_effect = httpx.ReadTimeout("Timed out")
    backup = MagicMock(model="qwen3:4b")
    backup.health_check.return_value = {"available": True, "model_found": True}
    backup.generate_text.return_value = "OLLAMA OK"

    mgr = FailoverLLMManager(primary=primary, backup=backup, max_retries=1, backoff_seconds=0.0)
    out = mgr.generate_text("Test timeout", agent_name="defense")

    assert out == "OLLAMA OK"
    assert primary.generate_text.call_count == 2  # 1 initial + 1 retry
    assert backup.generate_text.call_count == 1
    assert mgr.last_active_provider == "ollama"
    assert mgr.usage_stats["retries"] == 1
    assert mgr.usage_stats["failovers"] == 1


def test_3_nvidia_429_retries_then_fails_over():
    primary = MagicMock(model="nvidia/nemotron-3.5-lightning-30b-a3b")
    primary.generate_structured.side_effect = _http_status_error(429)
    backup = MagicMock(model="qwen3:4b")
    backup.health_check.return_value = {"available": True, "model_found": True}
    backup.generate_structured.return_value = _MiniSchema(section="411", act="IPC")

    mgr = FailoverLLMManager(primary=primary, backup=backup, max_retries=2, backoff_seconds=0.0)
    res = mgr.generate_structured("Schema test", _MiniSchema, agent_name="case_understanding")

    assert res.section == "411"
    assert primary.generate_structured.call_count == 3
    assert mgr.usage_stats["retries"] == 2
    assert mgr.usage_stats["failovers"] == 1


def test_4_nvidia_5xx_fails_over_after_bounded_retries():
    primary = MagicMock(model="nvidia/nemotron-3.5-lightning-30b-a3b")
    primary.generate_text.side_effect = _http_status_error(503)
    backup = MagicMock(model="qwen3:4b")
    backup.health_check.return_value = {"available": True, "model_found": True}
    backup.generate_text.return_value = "OLLAMA 503 FALLBACK"

    mgr = FailoverLLMManager(primary=primary, backup=backup, max_retries=1, backoff_seconds=0.0)
    out = mgr.generate_text("Test 503")
    assert out == "OLLAMA 503 FALLBACK"
    assert mgr.usage_stats["failovers"] == 1


def test_5_nvidia_connection_failure_uses_ollama():
    primary = MagicMock(model="nvidia/nemotron-3.5-lightning-30b-a3b")
    primary.generate_text.side_effect = httpx.ConnectError("DNS/network failure")
    backup = MagicMock(model="qwen3:4b")
    backup.health_check.return_value = {"available": True, "model_found": True}
    backup.generate_text.return_value = "OLLAMA CONN FALLBACK"

    mgr = FailoverLLMManager(primary=primary, backup=backup, max_retries=0, backoff_seconds=0.0)
    assert mgr.generate_text("Test conn") == "OLLAMA CONN FALLBACK"


def test_6_ollama_unavailable_or_missing_model_returns_clear_error():
    primary = MagicMock(model="nvidia/nemotron-3.5-lightning-30b-a3b")
    primary.generate_text.side_effect = httpx.ConnectError("Down")

    backup_down = MagicMock(model="qwen3:4b")
    backup_down.health_check.return_value = {"available": False, "error": "Connection refused"}
    mgr1 = FailoverLLMManager(primary=primary, backup=backup_down, max_retries=0, backoff_seconds=0.0)
    with pytest.raises(RuntimeError, match="Ollama backup.*unavailable"):
        mgr1.generate_text("Test")

    backup_nomodel = MagicMock(model="qwen3:4b")
    backup_nomodel.health_check.return_value = {"available": True, "model_found": False}
    mgr2 = FailoverLLMManager(primary=primary, backup=backup_nomodel, max_retries=0, backoff_seconds=0.0)
    with pytest.raises(RuntimeError, match="ollama pull qwen3:4b"):
        mgr2.generate_text("Test")


def test_7_nvidia_recovery_after_cooldown():
    primary = MagicMock(model="nvidia/nemotron-3.5-lightning-30b-a3b")
    primary.generate_text.side_effect = [httpx.ReadTimeout("Blip"), "NVIDIA RECOVERED"]
    backup = MagicMock(model="qwen3:4b")
    backup.health_check.return_value = {"available": True, "model_found": True}
    backup.generate_text.return_value = "OLLAMA DURING OUTAGE"

    mgr = FailoverLLMManager(
        primary=primary, backup=backup, max_retries=0, backoff_seconds=0.0, health_check_interval=0.05
    )
    assert mgr.generate_text("Req 1") == "OLLAMA DURING OUTAGE"
    assert mgr.last_active_provider == "ollama"

    time.sleep(0.06)
    assert mgr.generate_text("Req 2") == "NVIDIA RECOVERED"
    assert mgr.last_active_provider == "nvidia"
    assert mgr.usage_stats["recoveries"] == 1


def test_8_both_providers_fail_controlled_error():
    primary = MagicMock(model="nvidia/nemotron-3.5-lightning-30b-a3b")
    primary.generate_text.side_effect = httpx.ReadTimeout("Timeout")
    backup = MagicMock(model="qwen3:4b")
    backup.health_check.return_value = {"available": True, "model_found": True}
    backup.generate_text.side_effect = RuntimeError("Ollama crashed")

    mgr = FailoverLLMManager(primary=primary, backup=backup, max_retries=0, backoff_seconds=0.0)
    with pytest.raises(RuntimeError, match="Both NVIDIA primary.*and Ollama backup.*failed"):
        mgr.generate_text("Test both fail")


def test_9_non_retryable_client_errors_do_not_fail_over():
    primary = MagicMock(model="nvidia/nemotron-3.5-lightning-30b-a3b")
    primary.generate_text.side_effect = _http_status_error(400)
    backup = MagicMock(model="qwen3:4b")

    mgr = FailoverLLMManager(primary=primary, backup=backup, max_retries=2, backoff_seconds=0.0)
    with pytest.raises(httpx.HTTPStatusError):
        mgr.generate_text("Malformed")

    assert primary.generate_text.call_count == 1
    assert backup.generate_text.call_count == 0
    assert mgr.usage_stats["failovers"] == 0


def test_10_logging_and_no_api_key_leakage(caplog):
    secret = "nvapi-SUPER-SECRET-TEST-KEY-99999"
    primary = NvidiaLLMClient(api_key=secret, model="nvidia/nemotron-3.5-lightning-30b-a3b")
    primary.generate_text = MagicMock(side_effect=httpx.ConnectError("Network down"))
    backup = MagicMock(model="qwen3:4b")
    backup.health_check.return_value = {"available": True, "model_found": True}
    backup.generate_text.return_value = "BACKUP"

    mgr = FailoverLLMManager(primary=primary, backup=backup, max_retries=0, backoff_seconds=0.0)
    with caplog.at_level(logging.INFO):
        out = mgr.generate_text("Log check", agent_name="judge")

    assert out == "BACKUP"
    joined_logs = "\n".join(rec.getMessage() for rec in caplog.records)
    assert "LLM_EVENT=FAILOVER" in joined_logs
    assert "LLM_EVENT=BACKUP_SUCCESS" in joined_logs
    assert secret not in joined_logs


def test_11_openrouter_preserved_and_judge_uses_central_provider():
    # OpenRouter client remains directly selectable
    or_client = LLMProvider.get("openrouter")
    assert isinstance(or_client, OpenRouterLLMClient)

    # JudgeAgent no longer hardcodes provider="openrouter"
    judge = JudgeAgent()
    assert judge.llm_service.provider == LLMConfig.provider()

    # LangGraph still compiles cleanly
    compiled = create_court_graph().compile()
    assert "judge" in compiled.nodes
