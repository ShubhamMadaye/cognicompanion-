"""
CogniCompanion — PME Response Generator
=======================================
Dual-mode generation engine:
  - Generates compassionate AI responses with Gemini when configured
  - Strictly preserves deterministic medical facts & disclaimers for medication queries
  - Gracefully falls back to deterministic grounded synthesis when offline / timeout / no API key
"""

import logging
from typing import Any

from app.ai.memory_engine.intent_detector import PMEIntent
from app.ai.memory_engine.prompts import USER_QUERY_TEMPLATE
from app.ai.providers.llm import get_llm_provider
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ResponseGenerator:
    @staticmethod
    async def generate_response(
        query: str,
        intent: PMEIntent,
        context: dict[str, Any],
        confidence_level: str,
        image_base64: str | None = None,
    ) -> tuple[str, str | None]:
        """
        Generates the final response text with multimodal vision support.
        Returns (reply_text, model_name_or_none).
        """
        deterministic_reply = context["deterministic_reply"]

        # SAFETY-CRITICAL: Medication adherence without image is NEVER delegated to LLM generation
        if intent == PMEIntent.MEDICATION_ADHERENCE and not image_base64:
            return deterministic_reply, "deterministic-safety-engine"

        # Check if Gemini API key is configured
        if (
            not settings.GOOGLE_API_KEY
            or settings.GOOGLE_API_KEY.startswith("your-")
            or len(settings.GOOGLE_API_KEY.strip()) < 10
        ):
            return deterministic_reply, "deterministic-fallback"

        try:
            llm = get_llm_provider()
            prompt = USER_QUERY_TEMPLATE.format(query=query)
            system_instruction = context.get("system_instruction")

            response = await llm.generate(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=0.15,
                image_base64=image_base64,
            )
            if response and response.strip():
                return response.strip(), llm.model_name()
        except Exception as e:
            logger.warning("Gemini generation failed (%s) — falling back to deterministic response", e)

        return deterministic_reply, "deterministic-fallback"
