"""
Production configuration for The Orbital Jurist System
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # ── API Keys ────────────────────────────────────────────────────────────
    GROQ_API_KEY: str = ""
    # Set to a non-empty value to require X-API-Key header on all endpoints
    INTERNAL_API_KEY: str = ""

    # ── Model Configuration ─────────────────────────────────────────────────
    PHYSICS_MODEL: str = "llama-3.3-70b-versatile"
    SCHOLAR_MODEL: str = "llama-3.3-70b-versatile"
    JUDGE_MODEL:   str = "llama-3.3-70b-versatile"
    PROMPT_VERSION: str = "v1"
    TEMPERATURE: float = 0.1
    MAX_TOKENS: int = 4096

    # ── CelesTrak ───────────────────────────────────────────────────────────
    CELESTRAK_BASE_URL: str = "https://celestrak.org/NORAD/elements/gp.php"
    CELESTRAK_TIMEOUT_S: float = 15.0
    CELESTRAK_CACHE_TTL_S: int = 3600

    # ── Circuit Breakers ─────────────────────────────────────────────────────
    CB_CELESTRAK_FAILURE_THRESHOLD: int = 5
    CB_CELESTRAK_RECOVERY_TIMEOUT_S: float = 120.0
    CB_GROQ_FAILURE_THRESHOLD: int = 3
    CB_GROQ_RECOVERY_TIMEOUT_S: float = 60.0

    # ── Analysis Parameters ──────────────────────────────────────────────────
    COLLISION_THRESHOLD_KM: float = 1.0
    # Real-world conjunction warning threshold (CDM issuance level in LEO).
    # Miss distances above this value are not conjunction events — the workflow
    # short-circuits and returns a no-liability verdict without LLM calls.
    CONJUNCTION_RISK_THRESHOLD_KM: float = 10.0
    MANEUVER_DETECTION_WINDOW_HOURS: int = 48
    VELOCITY_CHANGE_THRESHOLD_MS: float = 0.5

    # ── FastAPI ──────────────────────────────────────────────────────────────
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_TITLE: str = "Orbital Jurist API"
    API_VERSION: str = "1.0.0"

    # ── Rate Limiting ────────────────────────────────────────────────────────
    RATE_LIMIT_ANALYZE: str = "10/minute"
    RATE_LIMIT_DEFAULT: str = "60/minute"

    # ── Results Store ────────────────────────────────────────────────────────
    RESULTS_TTL_SECONDS: int = 3600

    # ── Observability ────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True

    # ── Paths ────────────────────────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).parent

    @property
    def DATA_DIR(self) -> Path:
        return self.BASE_DIR / "data"

    @property
    def LEGAL_DB_PATH(self) -> Path:
        return self.DATA_DIR / "legal_precedents.json"


settings = Settings()