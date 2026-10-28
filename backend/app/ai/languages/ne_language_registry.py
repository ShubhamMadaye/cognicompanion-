"""
CogniCompanion — Northeast Indian Language Registry
===================================================
Defines metadata, capabilities, and tier assignments for the 9 supported
Northeast Indian languages:
  - Assamese  (as / as-IN)  — Tier 1: Full Voice (Native STT + TTS)
  - Meitei    (mni / mni-IN)— Tier 2: Partial Voice (Gemini LLM + fallback)
  - Mizo      (lus / lus-IN)— Tier 2: Partial Voice (Gemini LLM + fallback)
  - Khasi     (kha / kha-IN)— Tier 2: Partial Voice (Gemini LLM + fallback)
  - Garo      (grt / grt-IN)— Tier 3: Text Response (Gemini LLM)
  - Kokborok  (trp / trp-IN)— Tier 3: Text Response (Gemini LLM)
  - Naga      (nag / nag-IN)— Tier 3: Text Response (Gemini LLM)
  - Nyishi    (njz / njz-IN)— Tier 4: Investigational (Gemini LLM)
  - Pnar      (pbv / pbv-IN)— Tier 3: Text Response (Gemini LLM)
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Literal


class NELanguageTier(int, enum.Enum):
    TIER_1_FULL_VOICE = 1      # End-to-end native STT + LLM + native TTS
    TIER_2_PARTIAL_VOICE = 2   # Native text LLM, fallback STT/TTS
    TIER_3_TEXT_RESPONSE = 3   # Native text LLM + on-screen subtitles, fallback TTS
    TIER_4_INVESTIGATIONAL = 4 # Experimental LLM coverage


@dataclass(frozen=True)
class VoiceConfig:
    language: str
    provider: str
    speaker: str | None = None
    model_id: str | None = None
    sample_rate: int = 24000
    audio_format: str = "mp3"


@dataclass(frozen=True)
class LanguageConfig:
    code: str                     # Short code e.g. "as", "lus", "kha"
    bcp47: str                    # Full BCP-47 tag e.g. "as-IN", "lus-IN"
    name: str                     # English name
    native_name: str              # Native script / name
    tier: NELanguageTier          # Tier 1-4
    script_type: Literal["bengali", "latin", "meitei"]
    stt_supported: bool           # Direct native STT supported by Google Speech
    tts_supported: bool           # Direct native TTS supported by Google TTS
    google_stt_code: str | None   # Google Speech recognition code
    google_tts_code: str | None   # Google TTS voice code
    fallback_stt_code: str        # Fallback STT language code (e.g. "en-IN")
    fallback_tts_code: str        # Fallback TTS language code (e.g. "en-IN" or "as-IN")
    voice_disclaimer: str | None  # Displayed when voice playback uses fallback
    tts_provider: str = "google"  # Configured TTS provider e.g. "indic_parler", "rynsan", "google"


# ── Provider Voice Configurations ─────────────────────────────────────────────
# Centralized registry: language -> configuration -> provider -> model -> synthesis
VOICE_CONFIGS: dict[str, VoiceConfig] = {
    "as": VoiceConfig(
        language="as",
        provider="indic_parler",
        speaker="Amit",
        sample_rate=24000,
        audio_format="mp3",
    ),
    "mni": VoiceConfig(
        language="mni",
        provider="indic_parler",
        speaker="Ranjit",
        sample_rate=24000,
        audio_format="mp3",
    ),
    "kha": VoiceConfig(
        language="kha",
        provider="rynsan",
        speaker=None,
        sample_rate=24000,
        audio_format="mp3",
    ),
    "en": VoiceConfig(
        language="en",
        provider="google",
        speaker=None,
        sample_rate=24000,
        audio_format="mp3",
    ),
}


# ── Registry of Supported Northeast Indian Languages ─────────────────────────

NE_LANGUAGES: dict[str, LanguageConfig] = {
    # ── Tier 1: Full Voice ───────────────────────────────────────────────────
    "as": LanguageConfig(
        code="as",
        bcp47="as-IN",
        name="Assamese",
        native_name="অসমীয়া",
        tier=NELanguageTier.TIER_1_FULL_VOICE,
        script_type="bengali",
        stt_supported=True,
        tts_supported=True,
        google_stt_code="as-IN",
        google_tts_code="as-IN",
        fallback_stt_code="as-IN",
        fallback_tts_code="as-IN",
        voice_disclaimer=None,
    ),

    # ── Tier 2: Partial Voice ─────────────────────────────────────────────────
    "mni": LanguageConfig(
        code="mni",
        bcp47="mni-IN",
        name="Meitei",
        native_name="ꯃꯩꯇꯩꯂꯣꯟ",
        tier=NELanguageTier.TIER_2_PARTIAL_VOICE,
        script_type="meitei",
        stt_supported=False,
        tts_supported=False,
        google_stt_code=None,
        google_tts_code=None,
        fallback_stt_code="en-IN",
        fallback_tts_code="en-IN",
        voice_disclaimer="Spoken response in English audio with Meitei text on screen.",
    ),
    "lus": LanguageConfig(
        code="lus",
        bcp47="lus-IN",
        name="Mizo",
        native_name="Mizo ṭawng",
        tier=NELanguageTier.TIER_2_PARTIAL_VOICE,
        script_type="latin",
        stt_supported=False,
        tts_supported=False,
        google_stt_code=None,
        google_tts_code=None,
        fallback_stt_code="en-IN",
        fallback_tts_code="en-IN",
        voice_disclaimer="Spoken response in English audio with Mizo text on screen.",
    ),
    "kha": LanguageConfig(
        code="kha",
        bcp47="kha-IN",
        name="Khasi",
        native_name="Ka Ktien Khasi",
        tier=NELanguageTier.TIER_2_PARTIAL_VOICE,
        script_type="latin",
        stt_supported=False,
        tts_supported=False,
        google_stt_code=None,
        google_tts_code=None,
        fallback_stt_code="en-IN",
        fallback_tts_code="en-IN",
        voice_disclaimer="Spoken response in English audio with Khasi text on screen.",
    ),

    # ── Tier 3: Text Response ─────────────────────────────────────────────────
    "grt": LanguageConfig(
        code="grt",
        bcp47="grt-IN",
        name="Garo",
        native_name="A·chik",
        tier=NELanguageTier.TIER_3_TEXT_RESPONSE,
        script_type="latin",
        stt_supported=False,
        tts_supported=False,
        google_stt_code=None,
        google_tts_code=None,
        fallback_stt_code="en-IN",
        fallback_tts_code="en-IN",
        voice_disclaimer="Garo text displayed on screen.",
    ),
    "trp": LanguageConfig(
        code="trp",
        bcp47="trp-IN",
        name="Kokborok",
        native_name="Kokborok",
        tier=NELanguageTier.TIER_3_TEXT_RESPONSE,
        script_type="latin",
        stt_supported=False,
        tts_supported=False,
        google_stt_code=None,
        google_tts_code=None,
        fallback_stt_code="en-IN",
        fallback_tts_code="en-IN",
        voice_disclaimer="Kokborok text displayed on screen.",
    ),
    "nag": LanguageConfig(
        code="nag",
        bcp47="nag-IN",
        name="Naga (Nagamese)",
        native_name="Nagamese",
        tier=NELanguageTier.TIER_3_TEXT_RESPONSE,
        script_type="latin",
        stt_supported=False,
        tts_supported=False,
        google_stt_code=None,
        google_tts_code=None,
        fallback_stt_code="en-IN",
        fallback_tts_code="en-IN",
        voice_disclaimer="Nagamese text displayed on screen.",
    ),
    "pbv": LanguageConfig(
        code="pbv",
        bcp47="pbv-IN",
        name="Pnar",
        native_name="Pnar",
        tier=NELanguageTier.TIER_3_TEXT_RESPONSE,
        script_type="latin",
        stt_supported=False,
        tts_supported=False,
        google_stt_code=None,
        google_tts_code=None,
        fallback_stt_code="en-IN",
        fallback_tts_code="en-IN",
        voice_disclaimer="Pnar text displayed on screen.",
    ),

    # ── Tier 4: Investigational ───────────────────────────────────────────────
    "njz": LanguageConfig(
        code="njz",
        bcp47="njz-IN",
        name="Nyishi",
        native_name="Nyishi",
        tier=NELanguageTier.TIER_4_INVESTIGATIONAL,
        script_type="latin",
        stt_supported=False,
        tts_supported=False,
        google_stt_code=None,
        google_tts_code=None,
        fallback_stt_code="en-IN",
        fallback_tts_code="en-IN",
        voice_disclaimer="Nyishi text assistance (experimental).",
    ),
}

# Aliases to map various language code formats (e.g. "as-IN", "as", "grt-IN", "gar")
_LANGUAGE_ALIASES: dict[str, str] = {
    # Assamese
    "as": "as", "as-in": "as", "asm": "as", "assamese": "as",
    # Meitei
    "mni": "mni", "mni-in": "mni", "manipuri": "mni", "meitei": "mni",
    # Mizo
    "lus": "lus", "lus-in": "lus", "mizo": "lus", "lushai": "lus",
    # Khasi
    "kha": "kha", "kha-in": "kha", "khasi": "kha",
    # Garo
    "grt": "grt", "grt-in": "grt", "garo": "grt", "gar": "grt",
    # Kokborok
    "trp": "trp", "trp-in": "trp", "kokborok": "trp", "kok": "trp", "tripuri": "trp",
    # Naga
    "nag": "nag", "nag-in": "nag", "naga": "nag", "nagamese": "nag",
    # Nyishi
    "njz": "njz", "njz-in": "njz", "nyishi": "njz", "aph": "njz", "dafla": "njz",
    # Pnar
    "pbv": "pbv", "pbv-in": "pbv", "pnar": "pbv", "jaintia": "pbv",
}


def resolve_ne_language(code_or_name: str | None) -> LanguageConfig | None:
    """
    Resolves a language code, BCP-47 tag, or language name to its LanguageConfig.
    Returns None if the language is not one of the 9 Northeast Indian languages.
    """
    if not code_or_name:
        return None
    normalized = code_or_name.strip().lower()
    canonical_key = _LANGUAGE_ALIASES.get(normalized)
    if canonical_key:
        return NE_LANGUAGES.get(canonical_key)
    return None


def is_ne_language(code_or_name: str | None) -> bool:
    """Returns True if the given code/name is a supported Northeast Indian language."""
    return resolve_ne_language(code_or_name) is not None


def get_stt_language_code(language_code: str) -> str:
    """
    Returns the appropriate STT language code.
    If the language has native STT support (e.g. Assamese as-IN), returns as-IN.
    Otherwise returns the designated fallback STT code.
    """
    config = resolve_ne_language(language_code)
    if config:
        return config.google_stt_code if config.stt_supported and config.google_stt_code else config.fallback_stt_code
    return language_code


def get_tts_language_code(language_code: str) -> str:
    """
    Returns the appropriate TTS language code.
    If native TTS is supported (e.g. as-IN), returns as-IN.
    Otherwise returns fallback TTS code.
    """
    config = resolve_ne_language(language_code)
    if config:
        return config.google_tts_code if config.tts_supported and config.google_tts_code else config.fallback_tts_code
    return language_code


# ── Centralized Supported Languages Metadata ──────────────────────────────────
SUPPORTED_LANGUAGES: dict[str, dict[str, str]] = {
    "as": {
        "name": "Assamese",
        "native_name": "অসমীয়া",
        "tts_provider": "indic_parler",
    },
    "mni": {
        "name": "Meitei",
        "native_name": "ꯃꯩꯇꯩꯂꯣꯟ",
        "tts_provider": "indic_parler",
    },
    "kha": {
        "name": "Khasi",
        "native_name": "Ka Ktien Khasi",
        "tts_provider": "rynsan",
    },
    "lus": {
        "name": "Mizo",
        "native_name": "Mizo ṭawng",
        "tts_provider": "google",
    },
    "grt": {
        "name": "Garo",
        "native_name": "A·chik",
        "tts_provider": "google",
    },
    "trp": {
        "name": "Kokborok",
        "native_name": "Kokborok",
        "tts_provider": "google",
    },
    "nag": {
        "name": "Naga (Nagamese)",
        "native_name": "Nagamese",
        "tts_provider": "google",
    },
    "pbv": {
        "name": "Pnar",
        "native_name": "Pnar",
        "tts_provider": "google",
    },
    "njz": {
        "name": "Nyishi",
        "native_name": "Nyishi",
        "tts_provider": "google",
    },
    "en": {
        "name": "English",
        "native_name": "English",
        "tts_provider": "google",
    },
}


def get_voice_config(language_code: str | None) -> VoiceConfig:
    """
    Resolves the VoiceConfig for a given language code.
    Falls back to 'en' configuration if not directly registered.
    """
    if not language_code:
        return VOICE_CONFIGS["en"]
    cleaned = language_code.strip().lower().split("-")[0]
    return VOICE_CONFIGS.get(cleaned, VOICE_CONFIGS["en"])
