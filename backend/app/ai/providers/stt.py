"""
CogniCompanion — STT Provider (Speech-to-Text)
================================================
Abstract interface + Google Cloud Speech-to-Text implementation.

The patient speaks; audio bytes come in; transcribed text goes to the PME.
"""

import abc

from app.core.config import get_settings

settings = get_settings()


class STTProvider(abc.ABC):
    @abc.abstractmethod
    async def transcribe(
        self,
        audio_bytes: bytes,
        language_code: str | None = None,
        audio_encoding: str = "WEBM_OPUS",
        sample_rate_hz: int = 16000,
    ) -> str:
        """
        Transcribe audio bytes to text.

        Args:
            audio_bytes:   Raw audio data from microphone.
            language_code: BCP-47 code e.g. "en-IN", "hi-IN", "as-IN".
            audio_encoding: "WEBM_OPUS" | "LINEAR16" | "FLAC"
            sample_rate_hz: Sample rate of the audio.

        Returns:
            Transcribed text string.
        """


class GoogleSTTProvider(STTProvider):
    """Google Cloud Speech-to-Text V1 provider."""

    def __init__(self) -> None:
        from google.cloud import speech
        self._client = speech.SpeechClient()

    async def transcribe(
        self,
        audio_bytes: bytes,
        language_code: str | None = None,
        audio_encoding: str = "WEBM_OPUS",
        sample_rate_hz: int = 16000,
    ) -> str:
        import asyncio
        from google.cloud import speech

        from app.ai.languages.ne_language_registry import get_stt_language_code

        requested_lang = language_code or settings.STT_LANGUAGE_CODE
        lang = get_stt_language_code(requested_lang)

        resolved_encoding = audio_encoding
        if audio_bytes.startswith(b"RIFF"):
            resolved_encoding = "LINEAR16"
        elif audio_bytes.startswith(b"\x1a\x45\xdf\xa3"):
            resolved_encoding = "WEBM_OPUS"

        encoding_map = {
            "WEBM_OPUS": speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            "LINEAR16": speech.RecognitionConfig.AudioEncoding.LINEAR16,
            "FLAC": speech.RecognitionConfig.AudioEncoding.FLAC,
        }

        def _sync_transcribe() -> str:
            audio = speech.RecognitionAudio(content=audio_bytes)
            config = speech.RecognitionConfig(
                encoding=encoding_map.get(resolved_encoding, speech.RecognitionConfig.AudioEncoding.WEBM_OPUS),
                sample_rate_hertz=sample_rate_hz,
                language_code=lang,
                enable_automatic_punctuation=True,
            )
            response = self._client.recognize(config=config, audio=audio)
            if not response.results:
                return ""
            return response.results[0].alternatives[0].transcript

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_transcribe)


class MockSTTProvider(STTProvider):
    """Mock Speech-to-Text provider for offline / test environments."""

    def __init__(self, fixed_text: str = "Who is Rahul?") -> None:
        self.fixed_text = fixed_text

    async def transcribe(
        self,
        audio_bytes: bytes,
        language_code: str | None = None,
        audio_encoding: str = "WEBM_OPUS",
        sample_rate_hz: int = 16000,
    ) -> str:
        if not audio_bytes:
            return ""
        # If audio starts with text bytes for testing, decode if valid UTF-8
        try:
            decoded = audio_bytes.decode("utf-8").strip()
            if decoded and len(decoded) < 500 and not any(ord(c) == 0 for c in decoded):
                return decoded
        except Exception:
            pass
        return self.fixed_text


def get_stt_provider() -> STTProvider:
    import os
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        try:
            return GoogleSTTProvider()
        except Exception:
            return MockSTTProvider()
    return MockSTTProvider()
