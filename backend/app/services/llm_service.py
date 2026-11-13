"""
Configurable LLM Service for AI Court of India.
Delegates to the centralized LLMProvider (supporting Ollama, NVIDIA, OpenRouter, Gemini, and Mock).
Active provider is controlled by LLM_PROVIDER in .env (e.g. openrouter).
Includes zero-network deterministic mock engine for hermetic testing.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional, Type, TypeVar
from pydantic import BaseModel

from app.core.llm_provider import LLMConfig, LLMProvider, MockLLMClient, get_llm

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMService:
    """
    Unified LLM Service wrapper utilized by courtroom agents and Judicial Bench.
    Obtains the active model from the centralized LLMProvider architecture.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.provider = (provider or LLMConfig.provider()).lower()
        self.model_name = model_name
        self.api_key = api_key
        logger.info("Initialized LLMService wrapping centralized provider: '%s'", self.provider)

    def get_client(self):
        """Obtain underlying client from LLMProvider."""
        return LLMProvider.get(self.provider)

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        """Generate unstructured text completion via configured LLM provider."""
        client = self.get_client()
        return client.generate_text(prompt=prompt, system_prompt=system_prompt)

    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_prompt: str = "",
        fallback_data: Optional[dict[str, Any]] = None,
    ) -> T:
        """
        Generate structured output adhering to a Pydantic schema via configured LLM provider.
        """
        client = self.get_client()
        return client.generate_structured(
            prompt=prompt,
            response_schema=response_schema,
            system_prompt=system_prompt,
            fallback_data=fallback_data,
        )

    @staticmethod
    def _generate_mock_instance(schema: Type[T]) -> T:
        return MockLLMClient._generate_mock_instance(schema)
