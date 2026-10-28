"""
CogniCompanion — Northeast Indian Languages Support Package
"""

from app.ai.languages.ne_language_registry import (
    NE_LANGUAGES,
    NELanguageTier,
    LanguageConfig,
    resolve_ne_language,
    is_ne_language,
    get_stt_language_code,
    get_tts_language_code,
)
from app.ai.languages.language_identifier import detect_language_from_text

__all__ = [
    "NE_LANGUAGES",
    "NELanguageTier",
    "LanguageConfig",
    "resolve_ne_language",
    "is_ne_language",
    "get_stt_language_code",
    "get_tts_language_code",
    "detect_language_from_text",
]
