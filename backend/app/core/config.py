"""
CogniCompanion — Application Settings
======================================
Centralised configuration using Pydantic BaseSettings.
All values are read from environment variables (or .env file).
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────────
    APP_NAME: str = "CogniCompanion"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # ── Database ──────────────────────────────────────────────────────────────────
    DATABASE_URL: str  # postgresql+asyncpg://...
    SYNC_DATABASE_URL: str  # postgresql+psycopg2://... (Alembic)

    # ── JWT ───────────────────────────────────────────────────────────────────────
    JWT_SECRET: str
    JWT_REFRESH_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Google AI ─────────────────────────────────────────────────────────────────
    # Optional at startup — AI endpoints will raise a clear error if not set.
    # Get your key at: https://aistudio.google.com/app/apikey
    GOOGLE_API_KEY: str = ""
    LLM_MODEL: str = "gemini-flash-latest"
    EMBEDDING_MODEL: str = "models/gemini-embedding-001"
    SEMANTIC_SIMILARITY_THRESHOLD: float = 0.65
    SEMANTIC_HIGH_THRESHOLD: float = 0.75
    SEMANTIC_MEDIUM_THRESHOLD: float = 0.60
    SEMANTIC_LOW_THRESHOLD: float = 0.45
    SEMANTIC_SIGNIFICANCE_BOOST: float = 0.05
    CONFIDENCE_HIGH_THRESHOLD: float = 0.75
    CONFIDENCE_MEDIUM_THRESHOLD: float = 0.50
    CONFIDENCE_LOW_THRESHOLD: float = 0.30
    TTS_LANGUAGE_CODE: str = "en-IN"
    STT_LANGUAGE_CODE: str = "en-IN"

    # ── TTS System Configuration ───────────────────────────────────────────────────
    TTS_ENABLED: bool = True
    TTS_DEFAULT_LANGUAGE: str = "en-IN"
    INDIC_PARLER_MODEL: str = "ai4bharat/indic-parler-tts"
    RYNSAN_MODEL: str = "parler-tts/parler-tts-mini-v1"
    HF_TOKEN: str = ""
    TTS_DEVICE: str = "cpu"
    TTS_OUTPUT_FORMAT: str = "mp3"
    TTS_CACHE_DIR: str = "./cache/tts"

    # ── Storage ───────────────────────────────────────────────────────────────────
    STORAGE_PROVIDER: str = "local"
    LOCAL_STORAGE_PATH: str = "./uploads"

    # ── CORS ──────────────────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # ── API ────────────────────────────────────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"

    # ── Demo Patient (SIH Demo) ──────────────────────────────────────────────────
    # Credentials for the seeded demo patient account.
    # Used by seed_demo_patient.py and the Flutter auto-login.
    DEMO_PATIENT_EMAIL: str = "patient@cognicompanion.demo"
    DEMO_PATIENT_PASSWORD: str = "CogniDemo2024!"


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings singleton — safe for dependency injection."""
    return Settings()
