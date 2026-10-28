"""
CogniCompanion — LLM Provider Abstraction
==========================================
Abstract interface + Google Gemini implementation.

Usage:
    from app.ai.providers.llm import get_llm_provider

    llm = get_llm_provider()
    response = await llm.generate("Tell me about Rahul's last visit.", context=context)
"""

import abc

import google.generativeai as genai

from app.core.config import get_settings

settings = get_settings()


class LLMProvider(abc.ABC):
    """Abstract interface for all LLM backends."""

    @abc.abstractmethod
    async def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.2,
        image_base64: str | None = None,
    ) -> str:
        """Generate a text response for the given prompt, optionally with image content."""

    @abc.abstractmethod
    def model_name(self) -> str:
        """Return the model identifier string."""


import logging

logger = logging.getLogger(__name__)

# Fallback sequence of supported Gemini models in order of speed and modern compatibility
SUPPORTED_MODELS = [
    "gemini-flash-latest",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-flash-lite-latest",
    "gemini-pro-latest",
]


class GeminiLLMProvider(LLMProvider):
    """
    Google Gemini LLM provider with multimodal vision and language support.

    Low temperature (0.2) by default — we want factual, grounded responses,
    not creative generation. The Confidence & Safety Layer further filters
    hallucinated personal information.
    Supports multimodal queries (text + image_base64).
    Automatically tries latest supported models (gemini-1.5-flash, gemini-2.0-flash)
    if the primary model encounters version or availability constraints.
    """

    def __init__(self) -> None:
        if settings.GOOGLE_API_KEY:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
        self._active_model_name = settings.LLM_MODEL or "gemini-1.5-flash"

    async def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.2,
        image_base64: str | None = None,
    ) -> str:
        # google-generativeai doesn't have native async; run in thread pool
        import asyncio
        import base64

        # Candidate models to try in order: preferred model first, then alternatives
        candidates = [self._active_model_name] + [
            m for m in SUPPORTED_MODELS if m != self._active_model_name
        ]

        def _sync_generate() -> str:
            last_err = None
            content_parts: list = []

            if image_base64:
                try:
                    b64_clean = image_base64.strip()
                    mime = "image/jpeg"
                    if "base64," in b64_clean:
                        header, b64_clean = b64_clean.split("base64,", 1)
                        if "image/png" in header:
                            mime = "image/png"
                        elif "image/webp" in header:
                            mime = "image/webp"
                        elif "image/gif" in header:
                            mime = "image/gif"
                    raw_bytes = base64.b64decode(b64_clean)
                    content_parts.append({
                        "mime_type": mime,
                        "data": raw_bytes,
                    })
                except Exception as ex:
                    logger.warning("Could not decode image_base64 for multimodal request: %s", ex)

            content_parts.append(prompt)

            for model_name in candidates:
                try:
                    kwargs: dict = {
                        "model_name": model_name,
                        "generation_config": genai.GenerationConfig(
                            temperature=temperature,
                            top_p=0.95,
                            max_output_tokens=1024,
                        ),
                    }
                    if system_instruction:
                        kwargs["system_instruction"] = system_instruction

                    model = genai.GenerativeModel(**kwargs)
                    response = model.generate_content(content_parts if len(content_parts) > 1 else prompt)
                    if response and response.text:
                        if model_name != self._active_model_name:
                            logger.info(f"Switched active Gemini model to supported: {model_name}")
                            self._active_model_name = model_name
                        return response.text
                except Exception as e:
                    last_err = e
                    logger.warning(f"Gemini generation with '{model_name}' failed: {e}. Trying next model...")

            if last_err:
                raise last_err
            raise RuntimeError("All Gemini model candidates failed to generate a response.")

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_generate)

    def model_name(self) -> str:
        return self._active_model_name


def get_llm_provider() -> LLMProvider:
    """Factory — returns the configured LLM provider."""
    return GeminiLLMProvider()
