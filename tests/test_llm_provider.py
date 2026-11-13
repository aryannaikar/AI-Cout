"""
Tests for Centralized LLM Provider Architecture (Ollama & NVIDIA).
Verifies:
1. Ollama provider initializes and configures.
2. NVIDIA provider initializes and configures.
3. Provider selection works ('ollama', 'nvidia', 'mock').
4. Unreachable Ollama produces structured error.
5. Missing NVIDIA API key produces structured error.
6. Courtroom agents obtain LLM from centralized provider.
7. Judge Agent obtains LLM from centralized provider.
8. API keys NEVER appear in logs.
9. API keys NEVER appear in API health check response.
10. Mock client operates hermetically without network calls.
"""

import os
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.core.llm_provider import (
    LLMConfig,
    LLMProvider,
    MockLLMClient,
    NvidiaLLMClient,
    OllamaLLMClient,
    get_llm,
)
from app.agents.case_agent import CaseUnderstandingAgent
from app.agents.judge_agent import JudgeAgent
from app.agents.prosecutor_agent import ProsecutorAgent
from app.agents.defense_agent import DefenseAgent
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_1_ollama_provider_initialization():
    """Verify Ollama provider client initialization."""
    client = OllamaLLMClient(base_url="http://localhost:11434", model="llama3:latest")
    assert client.base_url == "http://localhost:11434"
    assert client.model == "llama3:latest"


def test_2_nvidia_provider_initialization():
    """Verify NVIDIA provider client initialization."""
    client = NvidiaLLMClient(api_key="mock-nvapi-key", model="meta/llama-3.1-70b-instruct")
    assert client.api_key == "mock-nvapi-key"
    assert client.model == "meta/llama-3.1-70b-instruct"
    assert "integrate.api.nvidia.com" in client.base_url


def test_3_provider_selection():
    """Verify selecting providers via LLMProvider.get()."""
    mock_client = LLMProvider.get("mock")
    assert isinstance(mock_client, MockLLMClient)

    ollama_client = LLMProvider.get("ollama")
    assert isinstance(ollama_client, OllamaLLMClient)

    nvidia_client = LLMProvider.get("nvidia")
    assert isinstance(nvidia_client, NvidiaLLMClient)


def test_4_unreachable_ollama_produces_useful_error():
    """Verify unreachable Ollama daemon reports error gracefully in health check."""
    client = OllamaLLMClient(base_url="http://localhost:9999", model="llama3:latest")
    health = client.health_check()
    assert health["available"] is False
    assert "error" in health
    assert "Could not connect" in health["error"]


def test_5_missing_nvidia_key_produces_useful_error():
    """Verify missing NVIDIA API key produces a clear configuration error."""
    client = NvidiaLLMClient(api_key="")
    health = client.health_check()
    assert health["available"] is False
    assert "NVIDIA_API_KEY is not configured" in health["error"]

    with pytest.raises(ValueError, match="NVIDIA_API_KEY is required"):
        client.generate_text("Prompt without key")


def test_6_agents_obtain_centralized_llm():
    """Verify Courtroom agents obtain their LLM through centralized provider."""
    case_agent = CaseUnderstandingAgent()
    assert case_agent.llm_service is not None
    assert case_agent.llm_service.get_client() is not None

    prosecutor = ProsecutorAgent()
    assert prosecutor.llm_service is not None

    defense = DefenseAgent()
    assert defense.llm_service is not None


def test_7_judge_obtains_centralized_llm():
    """Verify Judge Agent obtains its LLM through centralized provider."""
    judge = JudgeAgent()
    assert judge.llm_service is not None
    assert judge.llm_service.get_client() is not None


def test_8_api_keys_never_appear_in_logs(caplog):
    """Verify NVIDIA_API_KEY never leaks into application logs."""
    import logging
    secret = "nvapi-SUPER-CONFIDENTIAL-KEY-999"
    with patch.dict(os.environ, {"NVIDIA_API_KEY": secret, "LLM_PROVIDER": "nvidia"}):
        with caplog.at_level(logging.DEBUG):
            client = NvidiaLLMClient(api_key=secret)
            client.health_check()
    
    assert secret not in caplog.text
    assert "SUPER-CONFIDENTIAL" not in caplog.text


def test_9_api_keys_never_appear_in_health_response(client: TestClient):
    """Verify /api/health/llm never leaks NVIDIA_API_KEY or secrets."""
    secret = "nvapi-SUPER-SECRET-KEY-12345"
    with patch.dict(os.environ, {"NVIDIA_API_KEY": secret, "LLM_PROVIDER": "nvidia"}):
        res = client.get("/api/health/llm")
        assert res.status_code == 200
        raw_text = res.text
        assert secret not in raw_text
        assert "nvapi" not in raw_text
        assert "api_key" not in raw_text


def test_10_mock_client_hermetic_operation():
    """Verify MockLLMClient operates offline with valid text and schema output."""
    from app.models.judgment_models import Judgment
    mock = MockLLMClient()
    text = mock.generate_text("Explain burden of proof")
    assert "[MOCK LLM]" in text

    structured = mock.generate_structured("Produce sample verdict", Judgment)
    assert isinstance(structured, Judgment)
    assert structured.final_decision is not None
