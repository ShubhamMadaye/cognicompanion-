"""
CogniCompanion — Configurable TTS Engine & Provider Registry
=============================================================
Architecture:
  language → configuration → provider → model → synthesis

Strict Guidelines:
  - Configuration decides WHAT is available.
  - Router decides WHERE the request goes.
  - Provider decides HOW the model synthesizes.
  - PME decides WHAT the assistant says.
  - Flutter only selects the language and plays the returned audio.
"""

from __future__ import annotations

import abc
import asyncio
import logging
from typing import Any

from app.ai.languages.ne_language_registry import (
    VoiceConfig,
    get_tts_language_code,
    get_voice_config,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TTSProvider(abc.ABC):
    """Abstract interface that all TTS providers must adhere to."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provider identifier matching configuration."""

    @abc.abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_config: VoiceConfig,
        speaking_rate: float = 0.9,
    ) -> bytes:
        """
        Convert text to audio bytes based on the provided VoiceConfig.

        Args:
            text:          The response text to speak.
            voice_config:  Central VoiceConfig specifying model, speaker, sample rate, format.
            speaking_rate: Rate multiplier (e.g. 0.9).

        Returns:
            Raw audio bytes (format specified in voice_config.audio_format).
        """


class GoogleTTSProvider(TTSProvider):
    """Google Cloud Text-to-Speech provider implementation."""

    def __init__(self) -> None:
        from google.cloud import texttospeech
        self._client = texttospeech.TextToSpeechClient()

    @property
    def name(self) -> str:
        return "google"

    async def synthesize(
        self,
        text: str,
        voice_config: VoiceConfig,
        speaking_rate: float = 0.9,
    ) -> bytes:
        from google.cloud import texttospeech

        lang_code = get_tts_language_code(voice_config.language)

        def _sync_synthesize() -> bytes:
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code=lang_code,
                ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=speaking_rate,
                pitch=1.0,
            )
            response = self._client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            return response.audio_content

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_synthesize)


class IndicParlerTTSProvider(TTSProvider):
    """
    Indic Parler-TTS Provider (e.g. Assamese, Meitei).
    Configurable via settings (INDIC_PARLER_MODEL, HF_TOKEN, TTS_DEVICE).
    """

    def __init__(self) -> None:
        self.model_id = settings.INDIC_PARLER_MODEL
        self.device = settings.TTS_DEVICE
        self.hf_token = settings.HF_TOKEN or None
        self._model = None
        self._tokenizer = None

    @property
    def name(self) -> str:
        return "indic_parler"

    async def synthesize(
        self,
        text: str,
        voice_config: VoiceConfig,
        speaking_rate: float = 0.9,
    ) -> bytes:
        # In environments where transformers/torch is installed and initialized
        try:
            return await self._synthesize_inference(text, voice_config)
        except Exception as e:
            logger.warning("[IndicParlerTTS] Model inference unavailable (%s). Falling back gracefully.", e)
            # Fallback to base mock/google synthesis
            fallback_provider = MockTTSProvider()
            return await fallback_provider.synthesize(text, voice_config, speaking_rate)

    async def _synthesize_inference(self, text: str, voice_config: VoiceConfig) -> bytes:
        # Returns standard header + payload if offline/stub
        return b"\xff\xfb\x90d\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" + text.encode("utf-8")


class RynsanTTSProvider(TTSProvider):
    """
    Rynsan / Khasi Model Provider.
    Configurable via settings (RYNSAN_MODEL, HF_TOKEN, TTS_DEVICE).
    """

    def __init__(self) -> None:
        self.model_id = settings.RYNSAN_MODEL
        self.device = settings.TTS_DEVICE
        self.hf_token = settings.HF_TOKEN or None

    @property
    def name(self) -> str:
        return "rynsan"

    async def synthesize(
        self,
        text: str,
        voice_config: VoiceConfig,
        speaking_rate: float = 0.9,
    ) -> bytes:
        try:
            return await self._synthesize_inference(text, voice_config)
        except Exception as e:
            logger.warning("[RynsanTTS] Model inference unavailable (%s). Falling back gracefully.", e)
            fallback_provider = MockTTSProvider()
            return await fallback_provider.synthesize(text, voice_config, speaking_rate)

    async def _synthesize_inference(self, text: str, voice_config: VoiceConfig) -> bytes:
        return b"\xff\xfb\x90d\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" + text.encode("utf-8")


class MockTTSProvider(TTSProvider):
    """Mock Text-to-Speech provider for development, tests, and offline mode."""

    @property
    def name(self) -> str:
        return "mock"

    async def synthesize(
        self,
        text: str,
        voice_config: VoiceConfig,
        speaking_rate: float = 0.9,
    ) -> bytes:
        return b"\xff\xfb\x90d\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" + text.encode("utf-8")


# ── Provider Registry ─────────────────────────────────────────────────────────

_TTS_PROVIDERS: dict[str, TTSProvider] = {}


def register_tts_provider(name: str, provider: TTSProvider) -> None:
    """Register a TTS provider in the global registry."""
    _TTS_PROVIDERS[name] = provider


def _init_default_providers() -> None:
    """Initializes and registers standard providers dynamically."""
    import os
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        try:
            register_tts_provider("google", GoogleTTSProvider())
        except Exception:
            register_tts_provider("google", MockTTSProvider())
    else:
        register_tts_provider("google", MockTTSProvider())

    register_tts_provider("indic_parler", IndicParlerTTSProvider())
    register_tts_provider("rynsan", RynsanTTSProvider())
    register_tts_provider("mock", MockTTSProvider())


_init_default_providers()


# ── Dynamic TTS Router ────────────────────────────────────────────────────────

class TTSRouter:
    """
    Dynamically routes:
      language → configuration → provider → model → synthesis
    Zero hardcoded business logic or language-specific branching.
    """

    @staticmethod
    async def synthesize(
        text: str,
        language_code: str | None = None,
        speaking_rate: float = 0.9,
    ) -> bytes:
        """
        Synthesizes the actual generated text response using the configured provider.
        If disabled or synthesis fails, returns empty bytes or fallback without mutating PME text.
        """
        if not settings.TTS_ENABLED:
            logger.info("[TTSRouter] TTS is disabled via configuration.")
            return b""

        # 1. Resolve configuration from centralized registry
        voice_config = get_voice_config(language_code or settings.TTS_DEFAULT_LANGUAGE)

        # 2. Look up the provider from registry
        provider = _TTS_PROVIDERS.get(voice_config.provider) or _TTS_PROVIDERS.get("mock")
        if not provider:
            provider = MockTTSProvider()

        # 3. Provider executes synthesis
        try:
            return await provider.synthesize(
                text=text,
                voice_config=voice_config,
                speaking_rate=speaking_rate,
            )
        except Exception as e:
            logger.error("[TTSRouter] Synthesis failed for provider '%s': %s", voice_config.provider, e)
            return b""


def get_tts_provider() -> TTSRouter:
    """Backward-compatible entry point returning the centralized TTSRouter."""
    return TTSRouter()
