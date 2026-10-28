"""
CogniCompanion — Northeast Indian Language Identifier
=====================================================
Detects language from text input using:
  1. Unicode block detection for distinctive scripts:
     - Assamese / Bengali (U+0980–U+09FF) with Ra (ৰ) and Va (ৱ) discrimination
     - Meitei Mayek (U+ABC0–U+ABFF)
     - Indic scripts: Devanagari, Tamil, Telugu, Kannada, Malayalam
  2. Lexical / keyword markers for Latin-script Northeast languages:
     - Mizo (lus), Khasi (kha), Garo (grt), Nagamese (nag), Kokborok (trp)
  3. Trust-the-selection principle: If the patient or caregiver manually selected
     a Latin-script NE language, preserve it rather than defaulting back to English.
"""

from __future__ import annotations

import re
from app.ai.languages.ne_language_registry import resolve_ne_language


# ── Lexical Markers for Latin-Script Northeast Languages ───────────────────────

_MIZO_KEYWORDS = {
    "chibai", "khawiah", "engtikah", "enge", "tu nge", "kan", "kha", "chu",
    "ṭha", "dam", "khua", "tih", "leh", "chuan", "tur", "ani",
}

_KHASI_KEYWORDS = {
    "khublei", "kumno", "shano", "mynno", "aei", "phi", "nga", "bad",
    "jong", "ha", "ba", "la", "kine", "kitai", "hynrei",
}

_GARO_KEYWORDS = {
    "namgipa", "bano", "basako", "mai", "sawa", "angni", "na·a", "donga",
    "chingni", "song", "re·ba", "cha·a",
}

_NAGAMESE_KEYWORDS = {
    "kene", "kot", "ki", "kun", "tai", "amibilak", "bhal", "ase",
    "ekhon", "kotha", "jaise", "kise",
}

_KOKBOROK_KEYWORDS = {
    "kaham", "boba", "tamoni", "baha", "chwng", "nwng", "ang", "kwrwi",
    "tong", "man", "phai",
}


def detect_language_from_text(text: str, current_language: str = "en-IN") -> str:
    """
    Infers the language code from user text, honoring script blocks and NE vocabulary.
    Falls back to current_language if text is English or neutral Latin text.
    """
    if not text or not text.strip():
        return current_language

    # 1. Unicode Script Analysis
    # Meitei Mayek script (U+ABC0 - U+ABFF)
    if any("\uABC0" <= c <= "\uABFF" for c in text):
        return "mni-IN"

    # Assamese / Bengali script (U+0980 - U+09FF)
    # Check for unique Assamese characters: ৰ (U+09F0), ৱ (U+09F1)
    if any(c in {"\u09F0", "\u09F1"} for c in text):
        return "as-IN"
    # General Bengali/Assamese block
    if any("\u0980" <= c <= "\u09FF" for c in text):
        # Default to Assamese in CogniCompanion NE context if current is as-IN or unassigned
        if current_language.startswith("as"):
            return "as-IN"
        return "as-IN"

    # Devanagari (Hindi)
    if any("\u0900" <= c <= "\u097F" for c in text):
        return "hi-IN"

    # Dravidian scripts
    if any("\u0B80" <= c <= "\u0BFF" for c in text):
        return "ta-IN"
    if any("\u0C00" <= c <= "\u0C7F" for c in text):
        return "te-IN"
    if any("\u0C80" <= c <= "\u0CFF" for c in text):
        return "kn-IN"
    if any("\u0D00" <= c <= "\u0D7F" for c in text):
        return "ml-IN"

    # 2. Latin Script Keyword Matching
    words = set(re.findall(r"\b[a-zA-Zṭ·]+\b", text.lower()))
    if words:
        if words & _MIZO_KEYWORDS:
            return "lus-IN"
        if words & _KHASI_KEYWORDS:
            return "kha-IN"
        if words & _GARO_KEYWORDS:
            return "grt-IN"
        if words & _NAGAMESE_KEYWORDS:
            return "nag-IN"
        if words & _KOKBOROK_KEYWORDS:
            return "trp-IN"

    # 3. Trust-the-selection rule
    # If the user already selected a Northeast language, preserve their selection
    ne_cfg = resolve_ne_language(current_language)
    if ne_cfg:
        return ne_cfg.bcp47

    return current_language
