"""
Centralized LLM Provider Architecture for AI Court of India.
Supports:
1. Ollama — Primary Local Brain (default: http://localhost:11434, model: llama3:latest)
2. NVIDIA API — Cloud Model Provider (integrate.api.nvidia.com, model: meta/llama-3.1-70b-instruct)
3. OpenRouter — Cloud Multi-Model Gateway (openrouter.ai/api/v1, model: google/gemini-2.5-flash)
4. Gemini — Google Gemini API (google-genai SDK, model: gemini-2.5-flash)
5. Mock Provider — Deterministic zero-network fallback for hermetic unit testing

All agents and the Judicial Bench obtain their LLM through get_llm() or LLMProvider.get().
Strictly guarantees API keys and credentials are never leaked in logs or public responses.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar
from dotenv import load_dotenv
import httpx
from pydantic import BaseModel

# Load .env defaults without clobbering explicit process/test environment overrides
_env_file = Path(__file__).resolve().parents[3] / ".env"
if _env_file.exists():
    load_dotenv(dotenv_path=_env_file, override=False)
else:
    load_dotenv(override=False)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMConfig:
    """Centralized configuration resolved from environment variables."""

    @classmethod
    def provider(cls) -> str:
        return os.getenv("LLM_PROVIDER", "nvidia").strip().lower()

    @classmethod
    def enable_failover(cls) -> bool:
        return os.getenv("LLM_ENABLE_FAILOVER", "true").strip().lower() in {"1", "true", "yes"}

    @classmethod
    def request_timeout(cls) -> float:
        return float(os.getenv("LLM_REQUEST_TIMEOUT", "60.0"))

    @classmethod
    def max_retries(cls) -> int:
        return int(os.getenv("LLM_MAX_RETRIES", "2"))

    @classmethod
    def retry_backoff(cls) -> float:
        return float(os.getenv("LLM_RETRY_BACKOFF", "1.0"))

    @classmethod
    def health_check_interval(cls) -> float:
        return float(os.getenv("LLM_HEALTH_CHECK_INTERVAL", "60.0"))

    @classmethod
    def ollama_base_url(cls) -> str:
        return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")

    @classmethod
    def ollama_model(cls) -> str:
        return os.getenv("OLLAMA_MODEL", "qwen3:4b").strip()

    @classmethod
    def ollama_backup_model(cls) -> str:
        return os.getenv("OLLAMA_BACKUP_MODEL", "qwen3:4b").strip()

    @classmethod
    def nvidia_api_key(cls) -> Optional[str]:
        return os.getenv("NVIDIA_API_KEY")

    @classmethod
    def nvidia_base_url(cls) -> str:
        return os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")

    @classmethod
    def nvidia_model(cls) -> str:
        return os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b").strip()

    @classmethod
    def gemini_api_key(cls) -> Optional[str]:
        return os.getenv("GEMINI_API_KEY")

    @classmethod
    def gemini_model(cls) -> str:
        return os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

    @classmethod
    def openrouter_api_key(cls) -> Optional[str]:
        key = os.getenv("OPENROUTER_API_KEY")
        if not key:
            gkey = os.getenv("GEMINI_API_KEY", "")
            if gkey and gkey.strip().startswith("sk-or-"):
                return gkey.strip()
        return key.strip() if key else None

    @classmethod
    def openrouter_base_url(cls) -> str:
        return os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")

    @classmethod
    def openrouter_model(cls) -> str:
        return os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat").strip()


class BaseLLMClient:
    """Interface implemented by concrete LLM providers."""

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_prompt: str = "",
        fallback_data: Optional[dict[str, Any]] = None,
    ) -> T:
        raise NotImplementedError

    def health_check(self) -> dict[str, Any]:
        raise NotImplementedError


def _strip_thinking(content: str) -> str:
    """Remove <think>...</think> reasoning blocks emitted by reasoning models (e.g. Nemotron, Qwen3)."""
    if not content:
        return ""
    cleaned = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL | re.IGNORECASE)
    return cleaned.strip()


def _unwrap_properties_if_data(obj: Any) -> Any:
    """Unwrap an accidental {'properties': {...}} wrapper when its entries are data values rather than JSON Schema defs."""
    if isinstance(obj, dict) and "properties" in obj and isinstance(obj["properties"], dict):
        props = obj["properties"]
        if "$defs" not in props and props:
            looks_like_schema = all(
                isinstance(v, dict) and ("type" in v or "$ref" in v or "anyOf" in v or "description" in v and "properties" in v)
                for v in props.values()
            )
            if not looks_like_schema:
                return props
    return obj


def _extract_json_payload(content: str) -> dict[str, Any]:
    """Extract and parse a JSON object from model output, handling think tags and markdown fences."""
    cleaned = _strip_thinking(content)
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    try:
        parsed = json.loads(cleaned)
        return _unwrap_properties_if_data(parsed)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            return _unwrap_properties_if_data(parsed)
        raise


def _compact_schema_for_llm(response_schema: Type[BaseModel]) -> str:
    """Serialize response_schema, stripping post-computed Judgment fields to avoid token overflow."""
    schema_dict = response_schema.model_json_schema()
    if response_schema.__name__ == "Judgment":
        props = schema_dict.get("properties")
        if isinstance(props, dict):
            props.pop("ingredient_checklists", None)
            props.pop("scrutiny_report", None)
        defs = schema_dict.get("$defs")
        if isinstance(defs, dict):
            for k in ("IngredientChecklist", "IngredientItem", "DevilsAdvocateReport", "ScrutinyChallenge"):
                defs.pop(k, None)
    return json.dumps(schema_dict, indent=2)


class OllamaLLMClient(BaseLLMClient):
    """
    Ollama Local LLM Provider.
    Primary brain for AI Court of India.
    Connects to local Ollama daemon via native HTTP REST API.
    """

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or LLMConfig.ollama_base_url()).rstrip("/")
        self.model = model or LLMConfig.ollama_model()
        logger.info("Initialized OllamaLLMClient at '%s' with model '%s'", self.base_url, self.model)

    def health_check(self) -> dict[str, Any]:
        """Check Ollama daemon connectivity and model availability."""
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.base_url}/api/tags")
                if res.status_code != 200:
                    return {
                        "provider": "ollama",
                        "model": self.model,
                        "available": False,
                        "error": f"Ollama daemon responded with HTTP {res.status_code}",
                    }
                models_data = res.json().get("models", [])
                available_models = [m.get("name") for m in models_data]
                model_exists = any(
                    self.model == m or self.model in m or m.startswith(self.model)
                    for m in available_models
                )
                return {
                    "provider": "ollama",
                    "model": self.model,
                    "available": True,
                    "model_found": model_exists,
                    "available_models": available_models[:5],
                    "details": f"Connected to local Ollama daemon at {self.base_url}",
                }
        except Exception as e:
            return {
                "provider": "ollama",
                "model": self.model,
                "available": False,
                "error": f"Could not connect to Ollama at {self.base_url}: {e}",
            }

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        with httpx.Client(timeout=LLMConfig.request_timeout()) as client:
            res = client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                },
            )
            res.raise_for_status()
            data = res.json()
            return _strip_thinking(data.get("message", {}).get("content", ""))

    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_prompt: str = "",
        fallback_data: Optional[dict[str, Any]] = None,
    ) -> T:
        schema_json = _compact_schema_for_llm(response_schema)
        instruction = (
            f"{prompt}\n\n"
            f"CRITICAL: You must return ONLY a JSON object that strictly adheres to this JSON schema:\n"
            f"{schema_json}\n"
            f"Do not include any markdown formatting, preamble, or commentary. Output raw JSON only."
        )
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": instruction})

        with httpx.Client(timeout=max(LLMConfig.request_timeout(), 90.0)) as client:
            res = client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "format": "json",
                    "stream": False,
                },
            )
            res.raise_for_status()
            content = res.json().get("message", {}).get("content", "")
            parsed = _extract_json_payload(content)
            return response_schema.model_validate(parsed)


class NvidiaLLMClient(BaseLLMClient):
    """
    NVIDIA API (NIM) Cloud LLM Provider.
    Uses OpenAI-compatible chat completions interface.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key if api_key is not None else LLMConfig.nvidia_api_key()
        self.base_url = (base_url or LLMConfig.nvidia_base_url()).rstrip("/")
        self.model = model or LLMConfig.nvidia_model()
        logger.info("Initialized NvidiaLLMClient at '%s' with model '%s'", self.base_url, self.model)

    def health_check(self) -> dict[str, Any]:
        """Check NVIDIA NIM API reachability and authentication."""
        if not self.api_key:
            return {
                "provider": "nvidia",
                "model": self.model,
                "available": False,
                "error": "NVIDIA_API_KEY is not configured in environment.",
            }

        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            with httpx.Client(timeout=5.0) as client:
                res = client.get(f"{self.base_url}/models", headers=headers)
                if res.status_code == 200:
                    return {
                        "provider": "nvidia",
                        "model": self.model,
                        "available": True,
                        "details": "Authenticated successfully with NVIDIA NIM API.",
                    }
                elif res.status_code in (401, 403):
                    return {
                        "provider": "nvidia",
                        "model": self.model,
                        "available": False,
                        "error": "Authentication failed. Invalid or expired NVIDIA_API_KEY.",
                    }
                else:
                    return {
                        "provider": "nvidia",
                        "model": self.model,
                        "available": False,
                        "error": f"NVIDIA NIM responded with HTTP {res.status_code}",
                    }
        except Exception as e:
            return {
                "provider": "nvidia",
                "model": self.model,
                "available": False,
                "error": f"Could not reach NVIDIA API at {self.base_url}: {e}",
            }

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY is required for NVIDIA provider.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 2048,
        }
        if "nemotron" in self.model.lower() and os.getenv("NVIDIA_ENABLE_THINKING", "false").lower() not in {"1", "true", "yes"}:
            payload["chat_template_kwargs"] = {"enable_thinking": False}

        with httpx.Client(timeout=LLMConfig.request_timeout()) as client:
            res = client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            res.raise_for_status()
            data = res.json()
            content = data["choices"][0]["message"].get("content") or ""
            return _strip_thinking(content)

    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_prompt: str = "",
        fallback_data: Optional[dict[str, Any]] = None,
    ) -> T:
        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY is required for NVIDIA provider.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        schema_json = _compact_schema_for_llm(response_schema)
        instruction = (
            f"{prompt}\n\n"
            f"CRITICAL: Return ONLY a valid JSON DATA INSTANCE populated with the extracted values.\n"
            f"Do NOT return the JSON Schema definition ($defs, properties, required) itself.\n"
            f"Schema to populate:\n{schema_json}\n"
            f"Output raw JSON only, no markdown fences."
        )
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": instruction})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 8192,
            "response_format": {"type": "json_object"},
        }
        if "nemotron" in self.model.lower() and os.getenv("NVIDIA_ENABLE_THINKING", "false").lower() not in {"1", "true", "yes"}:
            payload["chat_template_kwargs"] = {"enable_thinking": False}

        with httpx.Client(timeout=max(LLMConfig.request_timeout(), 90.0)) as client:
            res = client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            res.raise_for_status()
            content = res.json()["choices"][0]["message"].get("content") or ""
            if not content.strip():
                raise ValueError("NVIDIA NIM returned empty content (reasoning budget exhausted).")
            parsed = _extract_json_payload(content)
            return response_schema.model_validate(parsed)


class OpenRouterLLMClient(BaseLLMClient):
    """
    OpenRouter API Cloud LLM Provider.
    Uses OpenAI-compatible chat completions interface via OpenRouter.
    Default model: google/gemini-2.5-flash (or OPENROUTER_MODEL env var).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        raw_key = api_key if api_key is not None else LLMConfig.openrouter_api_key()
        self.api_key = raw_key.strip() if raw_key else None
        self.base_url = (base_url or LLMConfig.openrouter_base_url()).rstrip("/")
        self.model = model or LLMConfig.openrouter_model()
        self.request_count: int = 0
        self.agent_request_counts: dict[str, int] = {}
        self.total_tokens_used: int = 0
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self._lock = threading.Lock()
        logger.info("Initialized OpenRouterLLMClient at '%s' with model '%s'", self.base_url, self.model)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/AI-Court-of-India",
            "X-Title": "AI Court of India",
            "Content-Type": "application/json",
        }

    def get_usage_summary(self) -> dict[str, Any]:
        """Return audit metrics on requests and token consumption."""
        with self._lock:
            return {
                "provider": "openrouter",
                "model": self.model,
                "total_requests": self.request_count,
                "agent_requests": dict(self.agent_request_counts),
                "total_prompt_tokens": self.total_prompt_tokens,
                "total_completion_tokens": self.total_completion_tokens,
                "total_tokens_used": self.total_tokens_used,
            }

    def _infer_agent_name(self, system_prompt: str, prompt: str) -> str:
        combined = f"{system_prompt} {prompt}".lower()
        if "liveprosecutor" in combined or "public prosecutor" in combined:
            return "live_prosecutor"
        if "livedefense" in combined or "defence counsel" in combined:
            return "live_defense"
        if "independent judicial bench" in combined or "you are the judge" in combined or "judgeagent" in combined:
            return "judge"
        if "prosecut" in combined:
            return "prosecutor"
        if "defen" in combined:
            return "defense"
        if "judge" in combined:
            return "judge"
        if "evidence" in combined:
            return "evidence"
        if "conflict" in combined:
            return "conflict"
        if "case packet" in combined or "structuredcase" in combined:
            return "case_understanding"
        return "courtroom_agent"

    def _track_request(self, agent_name: str, usage: Optional[dict] = None) -> int:
        with self._lock:
            self.request_count += 1
            current_num = self.request_count
            self.agent_request_counts[agent_name] = self.agent_request_counts.get(agent_name, 0) + 1
            if usage:
                pt = usage.get("prompt_tokens", 0)
                ct = usage.get("completion_tokens", 0)
                tt = usage.get("total_tokens", pt + ct)
                self.total_prompt_tokens += pt
                self.total_completion_tokens += ct
                self.total_tokens_used += tt
            return current_num

    def health_check(self) -> dict[str, Any]:
        """Check OpenRouter API reachability and authentication."""
        if not self.api_key:
            return {
                "provider": "openrouter",
                "model": self.model,
                "available": False,
                "error": "OPENROUTER_API_KEY is not configured in environment.",
            }

        try:
            with httpx.Client(timeout=8.0) as client:
                res = client.get(f"{self.base_url}/auth/key", headers=self._headers())
                if res.status_code == 200:
                    return {
                        "provider": "openrouter",
                        "model": self.model,
                        "available": True,
                        "details": "Authenticated successfully with OpenRouter API.",
                    }
                elif res.status_code in (401, 403):
                    return {
                        "provider": "openrouter",
                        "model": self.model,
                        "available": False,
                        "error": "Authentication failed. Invalid or expired OPENROUTER_API_KEY.",
                    }
                else:
                    return {
                        "provider": "openrouter",
                        "model": self.model,
                        "available": False,
                        "error": f"OpenRouter responded with HTTP {res.status_code}",
                    }
        except Exception as e:
            return {
                "provider": "openrouter",
                "model": self.model,
                "available": False,
                "error": f"Could not reach OpenRouter API at {self.base_url}: {e}",
            }

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required for OpenRouter provider.")

        agent_name = self._infer_agent_name(system_prompt, prompt)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        import time
        max_retries = 3
        last_exc = None
        t_start = time.perf_counter()

        for attempt in range(1, max_retries + 1):
            try:
                with httpx.Client(timeout=60.0) as client:
                    res = client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self._headers(),
                        json={
                            "model": self.model,
                            "messages": messages,
                            "temperature": 0.2,
                            "max_tokens": 2048,
                        },
                    )
                    # Quota / Payment handling
                    if res.status_code == 402:
                        logger.error("OpenRouter out of credits (HTTP 402): %s", res.text[:200])
                        raise RuntimeError("OpenRouter quota error (HTTP 402): Account has insufficient credits.")

                    # Auth failure
                    if res.status_code in (401, 403):
                        logger.error("OpenRouter auth failure (HTTP %d): %s", res.status_code, res.text[:200])
                        raise RuntimeError(f"OpenRouter authentication failure (HTTP {res.status_code}). Check OPENROUTER_API_KEY.")

                    # Rate limit or temporary outage
                    if res.status_code in (429, 503) and attempt < max_retries:
                        backoff = 3.0 * attempt
                        logger.warning("OpenRouter busy (%d/%d): %s — backing off %.1fs", attempt, max_retries, res.text[:80], backoff)
                        time.sleep(backoff)
                        continue

                    res.raise_for_status()
                    data = res.json()
                    content = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                    req_num = self._track_request(agent_name, usage)
                    elapsed = time.perf_counter() - t_start

                    logger.info(
                        "[OpenRouter #%d] Agent: '%s' | Model: '%s' | %d chars in %.2fs | Tokens: %s",
                        req_num, agent_name, self.model, len(content), elapsed, usage.get("total_tokens", "N/A"),
                    )
                    return content
            except Exception as e:
                last_exc = e
                if isinstance(e, RuntimeError):
                    raise
                if attempt < max_retries and ("429" in str(e) or "503" in str(e) or "timeout" in str(e).lower()):
                    time.sleep(3.0 * attempt)
                    continue
                break
        raise RuntimeError(f"OpenRouter generate_text failed for agent '{agent_name}': {last_exc}") from last_exc

    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_prompt: str = "",
        fallback_data: Optional[dict[str, Any]] = None,
    ) -> T:
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required for OpenRouter provider.")

        agent_name = self._infer_agent_name(system_prompt, prompt)
        schema_json = _compact_schema_for_llm(response_schema)
        instruction = (
            f"{prompt}\n\n"
            f"CRITICAL INSTRUCTION: You must return ONLY a JSON object that adheres strictly to this schema:\n"
            f"{schema_json}\n"
            f"No codeblocks, no markdown, only raw JSON."
        )
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": instruction})

        import time
        max_retries = 3
        last_exc = None
        t_start = time.perf_counter()
        raw_content = None

        for attempt in range(1, max_retries + 1):
            try:
                with httpx.Client(timeout=90.0) as client:
                    payload = {
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.1,
                        "max_tokens": 8192,
                        "response_format": {"type": "json_object"},
                    }
                    res = client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self._headers(),
                        json=payload,
                    )
                    # Quota / Payment handling
                    if res.status_code == 402:
                        logger.error("OpenRouter out of credits (HTTP 402): %s", res.text[:200])
                        raise RuntimeError("OpenRouter quota error (HTTP 402): Account has insufficient credits.")

                    # Auth failure
                    if res.status_code in (401, 403):
                        logger.error("OpenRouter auth failure (HTTP %d): %s", res.status_code, res.text[:200])
                        raise RuntimeError(f"OpenRouter authentication failure (HTTP {res.status_code}). Check OPENROUTER_API_KEY.")

                    # Rate limit or temporary outage
                    if res.status_code in (429, 503) and attempt < max_retries:
                        backoff = 3.0 * attempt
                        logger.warning("OpenRouter structured busy (%d/%d): %s — backing off %.1fs", attempt, max_retries, res.text[:80], backoff)
                        time.sleep(backoff)
                        continue

                    res.raise_for_status()
                    data = res.json()
                    content = data["choices"][0]["message"]["content"]
                    raw_content = content
                    usage = data.get("usage", {})
                    req_num = self._track_request(agent_name, usage)
                    elapsed = time.perf_counter() - t_start

                    clean_content = content.strip()
                    if clean_content.startswith("```json"):
                        clean_content = clean_content[7:]
                    if clean_content.startswith("```"):
                        clean_content = clean_content[3:]
                    if clean_content.endswith("```"):
                        clean_content = clean_content[:-3]
                    clean_content = clean_content.strip()

                    parsed = json.loads(clean_content)
                    validated = response_schema.model_validate(parsed)
                    logger.info(
                        "[OpenRouter #%d] Agent: '%s' | Schema: '%s' OK (%d chars in %.2fs) | Tokens: %s",
                        req_num, agent_name, response_schema.__name__, len(content), elapsed, usage.get("total_tokens", "N/A"),
                    )
                    return validated
            except Exception as e:
                last_exc = e
                if isinstance(e, RuntimeError):
                    raise
                if attempt < max_retries and ("429" in str(e) or "503" in str(e) or "timeout" in str(e).lower()):
                    time.sleep(3.0 * attempt)
                    continue
                break

        # If we reached here: check why it failed
        logger.error(
            "OpenRouter generate_structured FAILED for agent '%s' (schema '%s'): %s",
            agent_name, response_schema.__name__, last_exc,
        )

        # STRICT CONSTRAINTS: Never silently substitute fabricated output on API/HTTP/Network failures!
        # Only parse errors where OpenRouter responded with HTTP 200 may utilize caller-supplied fallback data
        if raw_content is not None and fallback_data is not None and isinstance(last_exc, (json.JSONDecodeError, Exception)):
            logger.warning(
                "OpenRouter returned response but JSON validation failed. Using caller fallback for '%s'.",
                response_schema.__name__,
            )
            return response_schema.model_validate(fallback_data)

        raise RuntimeError(
            f"OpenRouter structured generation failed for agent '{agent_name}' ({response_schema.__name__}): {last_exc}"
        ) from last_exc


class GeminiLLMClient(BaseLLMClient):
    """
    Google Gemini API LLM Provider.
    Uses the official google-genai SDK (google.genai.Client).
    Model: gemini-2.5-flash (or GEMINI_MODEL env var).
    Never silently falls back — raises LLMGenerationError on failure.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        from google import genai as _genai  # local import to keep optional dependency
        self.api_key = api_key if api_key is not None else LLMConfig.gemini_api_key()
        self.model = model or LLMConfig.gemini_model()
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Add it to your .env file."
            )
        self._client = _genai.Client(api_key=self.api_key)
        logger.info("Initialized GeminiLLMClient (google-genai SDK) with model '%s'", self.model)

    def _build_contents(self, prompt: str, system_prompt: str) -> list:
        """Build contents list; prepend system_prompt as a user/model exchange."""
        from google.genai import types as _types
        parts = []
        if system_prompt:
            # Gemini native API uses system_instruction separately; we embed it in the first turn
            parts.append(
                _types.Content(
                    role="user",
                    parts=[_types.Part(text=f"[SYSTEM INSTRUCTION]\n{system_prompt}\n\n[USER REQUEST]\n{prompt}")],
                )
            )
        else:
            parts.append(
                _types.Content(
                    role="user",
                    parts=[_types.Part(text=prompt)],
                )
            )
        return parts

    def health_check(self) -> dict[str, Any]:
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents="Respond with the single word: OK",
            )
            text = response.text or ""
            if text.strip():
                return {
                    "provider": "gemini",
                    "model": self.model,
                    "available": True,
                    "details": f"Gemini responded: '{text.strip()[:30]}'",
                }
            return {
                "provider": "gemini",
                "model": self.model,
                "available": False,
                "error": "Gemini returned empty response.",
            }
        except Exception as e:
            return {
                "provider": "gemini",
                "model": self.model,
                "available": False,
                "error": f"Gemini health check failed: {e}",
            }

    def _call_with_retry(self, contents: list, max_retries: int = 3, delay: float = 4.0) -> str:
        """Call Gemini with automatic retry on 503/429 (rate limit / server busy)."""
        import time
        last_exc = None
        for attempt in range(1, max_retries + 1):
            try:
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=contents,
                )
                text = response.text
                if not text:
                    raise RuntimeError("Gemini returned an empty response.")
                return text
            except Exception as e:
                last_exc = e
                err_str = str(e)
                # Retry on transient server-side errors
                if attempt < max_retries and ("503" in err_str or "429" in err_str or "UNAVAILABLE" in err_str or "RESOURCE_EXHAUSTED" in err_str):
                    wait = delay * attempt
                    logger.warning("Gemini transient error (attempt %d/%d): %s — retrying in %.1fs", attempt, max_retries, err_str[:80], wait)
                    time.sleep(wait)
                else:
                    break
        raise last_exc  # type: ignore[misc]

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        contents = self._build_contents(prompt, system_prompt)
        try:
            text = self._call_with_retry(contents)
            logger.info("Gemini generate_text: received %d chars", len(text))
            return text
        except Exception as e:
            logger.error("Gemini generate_text FAILED: %s", e)
            raise RuntimeError(f"Gemini LLM generation failed: {e}") from e

    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_prompt: str = "",
        fallback_data: Optional[dict[str, Any]] = None,
    ) -> T:
        schema_json = _compact_schema_for_llm(response_schema)
        full_prompt = (
            f"{prompt}\n\n"
            f"CRITICAL INSTRUCTION: Return ONLY a valid JSON object matching this exact schema. "
            f"No markdown, no code fences, no commentary — raw JSON only.\n\n"
            f"JSON Schema:\n{schema_json}"
        )
        contents = self._build_contents(full_prompt, system_prompt)

        try:
            raw = self._call_with_retry(contents)
            if not raw:
                raise RuntimeError("Gemini returned empty response for structured generation.")

            # Strip markdown fences if model wrapped output
            clean = raw.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            elif clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            clean = clean.strip()

            parsed = json.loads(clean)
            validated = response_schema.model_validate(parsed)
            logger.info(
                "Gemini generate_structured: OK — %s parsed successfully (%d chars)",
                response_schema.__name__, len(raw),
            )
            return validated

        except Exception as e:
            logger.error(
                "Gemini generate_structured FAILED for schema '%s': %s",
                response_schema.__name__, e,
            )
            # Only use fallback_data if explicitly provided by the caller AND the error is a parse/validation error
            if fallback_data is not None and not isinstance(e, RuntimeError):
                logger.warning(
                    "Using caller-supplied fallback_data for '%s' after parse error.",
                    response_schema.__name__,
                )
                return response_schema.model_validate(fallback_data)
            # Surface the failure — do NOT silently generate mock data
            raise RuntimeError(
                f"Gemini structured generation failed for '{response_schema.__name__}': {e}"
            ) from e


class MockLLMClient(BaseLLMClient):
    """Deterministic, zero-network mock client for unit and integration testing."""

    def __init__(self):
        logger.info("Initialized MockLLMClient for offline testing.")

    def health_check(self) -> dict[str, Any]:
        return {
            "provider": "mock",
            "model": "mock-deterministic",
            "available": True,
            "details": "Deterministic offline mock engine.",
        }

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        return f"[MOCK LLM] Response for prompt: {prompt[:80]}"

    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_prompt: str = "",
        fallback_data: Optional[dict[str, Any]] = None,
    ) -> T:
        if fallback_data is not None:
            return response_schema.model_validate(fallback_data)
        return self._generate_mock_instance(response_schema)

    @staticmethod
    def _generate_mock_instance(schema: Type[T]) -> T:
        sample_dict: dict[str, Any] = {}
        for field_name, field_info in schema.model_fields.items():
            ann = field_info.annotation
            if ann == str or getattr(ann, "__name__", "") == "str":
                sample_dict[field_name] = f"Sample {field_name.replace('_', ' ').title()}"
            elif ann == int or getattr(ann, "__name__", "") == "int":
                sample_dict[field_name] = 1
            elif ann == float or getattr(ann, "__name__", "") == "float":
                sample_dict[field_name] = 0.95
            elif ann == bool or getattr(ann, "__name__", "") == "bool":
                sample_dict[field_name] = True
            elif getattr(ann, "__origin__", None) == list:
                sample_dict[field_name] = []
            elif getattr(ann, "__origin__", None) == dict:
                sample_dict[field_name] = {}
            else:
                sample_dict[field_name] = None
        return schema.model_validate(sample_dict)


class FailoverLLMManager(BaseLLMClient):
    """
    Centralized LLM Failover Manager: NVIDIA NIM primary + Ollama (qwen3:4b) local backup.
    Implements bounded retries, exponential backoff, circuit-breaker cooldown,
    automatic recovery to NVIDIA, and structured observability without logging secrets.
    """

    def __init__(
        self,
        primary: Optional[BaseLLMClient] = None,
        backup: Optional[BaseLLMClient] = None,
        max_retries: Optional[int] = None,
        backoff_seconds: Optional[float] = None,
        health_check_interval: Optional[float] = None,
    ):
        self.primary = primary or NvidiaLLMClient()
        self.backup = backup or OllamaLLMClient(model=LLMConfig.ollama_backup_model())
        self.max_retries = LLMConfig.max_retries() if max_retries is None else max_retries
        self.backoff_seconds = LLMConfig.retry_backoff() if backoff_seconds is None else backoff_seconds
        self.health_check_interval = (
            LLMConfig.health_check_interval() if health_check_interval is None else health_check_interval
        )
        self._lock = threading.Lock()
        self._circuit_open_until: float = 0.0
        self._was_failed_over: bool = False
        self.last_active_provider: str = "nvidia"
        self.last_active_model: str = getattr(self.primary, "model", LLMConfig.nvidia_model())
        self.usage_stats: dict[str, int] = {
            "primary_success": 0,
            "primary_failures": 0,
            "backup_success": 0,
            "backup_failures": 0,
            "failovers": 0,
            "recoveries": 0,
            "retries": 0,
        }

    @staticmethod
    def _classify_error(exc: Exception) -> tuple[bool, str]:
        """Return (is_retryable_for_failover, error_category)."""
        if isinstance(exc, httpx.TimeoutException):
            return True, "timeout"
        if isinstance(exc, httpx.RequestError):
            return True, "connection_error"
        if isinstance(exc, httpx.HTTPStatusError):
            code = exc.response.status_code
            if code == 429:
                return True, "rate_limit_429"
            if 500 <= code < 600:
                return True, f"server_error_{code}"
            return False, f"client_error_{code}"
        if isinstance(exc, ValueError):
            return False, "invalid_request_or_schema"
        return False, type(exc).__name__

    def _execute_with_failover(self, operation_name: str, call_fn, agent_name: str = "unknown") -> Any:
        now = time.monotonic()
        with self._lock:
            circuit_open = now < self._circuit_open_until
            was_failed_over = self._was_failed_over

        primary_model = getattr(self.primary, "model", LLMConfig.nvidia_model())
        backup_model = getattr(self.backup, "model", LLMConfig.ollama_backup_model())
        primary_err: Optional[Exception] = None
        err_category = "none"

        if not circuit_open:
            for attempt in range(self.max_retries + 1):
                t0 = time.perf_counter()
                try:
                    result = call_fn(self.primary)
                    dur_ms = (time.perf_counter() - t0) * 1000.0
                    with self._lock:
                        self.usage_stats["primary_success"] += 1
                        self.last_active_provider = "nvidia"
                        self.last_active_model = primary_model
                        if was_failed_over:
                            self._was_failed_over = False
                            self._circuit_open_until = 0.0
                            self.usage_stats["recoveries"] += 1
                            logger.info(
                                "LLM_EVENT=RECOVERY provider=nvidia model=%s agent=%s duration_ms=%.1f retries=%d",
                                primary_model, agent_name, dur_ms, attempt,
                            )
                        else:
                            logger.info(
                                "LLM_EVENT=SUCCESS provider=nvidia model=%s agent=%s op=%s duration_ms=%.1f retries=%d",
                                primary_model, agent_name, operation_name, dur_ms, attempt,
                            )
                    return result
                except Exception as exc:
                    dur_ms = (time.perf_counter() - t0) * 1000.0
                    retryable, err_category = self._classify_error(exc)
                    primary_err = exc
                    logger.warning(
                        "LLM_EVENT=PRIMARY_ERROR provider=nvidia model=%s agent=%s attempt=%d/%d category=%s retryable=%s duration_ms=%.1f",
                        primary_model, agent_name, attempt + 1, self.max_retries + 1, err_category, retryable, dur_ms,
                    )
                    if not retryable:
                        raise
                    if attempt < self.max_retries:
                        with self._lock:
                            self.usage_stats["retries"] += 1
                        if self.backoff_seconds > 0:
                            time.sleep(self.backoff_seconds * (2 ** attempt))

            # Exhausted primary retries -> open circuit and fail over
            with self._lock:
                self.usage_stats["primary_failures"] += 1
                self.usage_stats["failovers"] += 1
                self._was_failed_over = True
                self._circuit_open_until = time.monotonic() + self.health_check_interval
            logger.warning(
                "LLM_EVENT=FAILOVER from=nvidia to=ollama backup_model=%s agent=%s reason=%s cooldown_s=%.1f",
                backup_model, agent_name, err_category, self.health_check_interval,
            )
        else:
            logger.info(
                "LLM_EVENT=CIRCUIT_OPEN provider=nvidia routing=ollama backup_model=%s agent=%s",
                backup_model, agent_name,
            )

        # Backup: Ollama
        health = self.backup.health_check()
        if not health.get("available"):
            with self._lock:
                self.usage_stats["backup_failures"] += 1
            raise RuntimeError(
                f"NVIDIA primary failed ({err_category}) and Ollama backup at {LLMConfig.ollama_base_url()} is unavailable: "
                f"{health.get('error', 'unreachable')}"
            ) from primary_err
        if health.get("model_found") is False:
            with self._lock:
                self.usage_stats["backup_failures"] += 1
            raise RuntimeError(
                f"NVIDIA primary failed ({err_category}) and Ollama backup model '{backup_model}' is not installed. "
                f"Run: ollama pull {backup_model}"
            ) from primary_err

        t0 = time.perf_counter()
        try:
            result = call_fn(self.backup)
            dur_ms = (time.perf_counter() - t0) * 1000.0
            with self._lock:
                self.usage_stats["backup_success"] += 1
                self.last_active_provider = "ollama"
                self.last_active_model = backup_model
            logger.info(
                "LLM_EVENT=BACKUP_SUCCESS provider=ollama model=%s agent=%s op=%s duration_ms=%.1f",
                backup_model, agent_name, operation_name, dur_ms,
            )
            return result
        except Exception as backup_exc:
            dur_ms = (time.perf_counter() - t0) * 1000.0
            with self._lock:
                self.usage_stats["backup_failures"] += 1
            logger.error(
                "LLM_EVENT=BACKUP_FAILED provider=ollama model=%s agent=%s duration_ms=%.1f err=%s",
                backup_model, agent_name, dur_ms, backup_exc,
            )
            raise RuntimeError(
                f"Both NVIDIA primary ({err_category}) and Ollama backup ({backup_model}) failed: {backup_exc}"
            ) from backup_exc

    def generate_text(self, prompt: str, system_prompt: str = "", agent_name: str = "unknown") -> str:
        return self._execute_with_failover(
            "generate_text",
            lambda client: client.generate_text(prompt=prompt, system_prompt=system_prompt),
            agent_name=agent_name,
        )

    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_prompt: str = "",
        fallback_data: Optional[dict[str, Any]] = None,
        agent_name: str = "unknown",
    ) -> T:
        return self._execute_with_failover(
            "generate_structured",
            lambda client: client.generate_structured(
                prompt=prompt,
                response_schema=response_schema,
                system_prompt=system_prompt,
                fallback_data=fallback_data,
            ),
            agent_name=agent_name,
        )

    def health_check(self) -> dict[str, Any]:
        primary_health = self.primary.health_check()
        backup_health = self.backup.health_check()
        circuit_open = time.monotonic() < self._circuit_open_until
        active = "ollama" if (circuit_open or not primary_health.get("available")) and backup_health.get("available") else (
            "nvidia" if primary_health.get("available") else "unavailable"
        )
        return {
            "provider": active,
            "primary": primary_health,
            "backup": backup_health,
            "available": bool(primary_health.get("available") or backup_health.get("available")),
            "circuit_open": circuit_open,
            "last_active_provider": self.last_active_provider,
            "last_active_model": self.last_active_model,
            "usage_stats": dict(self.usage_stats),
        }


class LLMProvider:
    """
    Centralized factory and registry for AI Court of India LLMs.
    Ensures all 10 agents and the Judicial Bench share the identical configured model.
    """

    _active_provider: Optional[str] = None
    _instances: Dict[str, BaseLLMClient] = {}

    @classmethod
    def set_provider(cls, provider: str) -> None:
        """Explicitly override active provider ('ollama', 'nvidia', 'openrouter', 'gemini', 'mock')."""
        cls._active_provider = provider.lower().strip()
        logger.info("Active LLM provider set to: '%s'", cls._active_provider)

    @classmethod
    def get(cls, provider: Optional[str] = None) -> BaseLLMClient:
        """
        Get the configured LLM client.
        Defaults to LLM_PROVIDER from environment (defaults to 'ollama').
        """
        target = (provider or cls._active_provider or LLMConfig.provider()).lower()

        if target not in cls._instances:
            if target == "ollama":
                cls._instances[target] = OllamaLLMClient()
            elif target == "nvidia":
                if LLMConfig.enable_failover():
                    cls._instances[target] = FailoverLLMManager()
                else:
                    cls._instances[target] = NvidiaLLMClient()
            elif target == "nvidia_direct":
                cls._instances[target] = NvidiaLLMClient()
            elif target in ("openrouter", "open_router"):
                cls._instances[target] = OpenRouterLLMClient()
            elif target == "gemini":
                # If GEMINI_API_KEY is an OpenRouter key, seamlessly route to OpenRouterLLMClient
                if (LLMConfig.gemini_api_key() or "").startswith("sk-or-") or (LLMConfig.openrouter_api_key() or "").startswith("sk-or-"):
                    logger.info("Routing 'gemini' provider to OpenRouterLLMClient based on sk-or- key.")
                    cls._instances[target] = OpenRouterLLMClient()
                else:
                    cls._instances[target] = GeminiLLMClient()
            elif target == "mock":
                cls._instances[target] = MockLLMClient()
            else:
                raise ValueError(
                    f"Unsupported LLM provider '{target}'. "
                    f"Supported providers are: 'ollama', 'nvidia', 'openrouter', 'gemini', 'mock'."
                )

        return cls._instances[target]

    @classmethod
    def check_health(cls, provider: Optional[str] = None) -> dict[str, Any]:
        """
        Run health check on configured LLM provider.
        Strictly excludes any credentials or secret keys from the response.
        """
        client = cls.get(provider)
        return client.health_check()


def get_llm(provider: Optional[str] = None) -> BaseLLMClient:
    """Convenience accessor to obtain the centralized LLM client."""
    return LLMProvider.get(provider)
