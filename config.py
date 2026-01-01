"""
Configuration for The Orbital Jurist System
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # Model Configuration
    PHYSICS_MODEL: str = "llama-3.3-70b-versatile"
    SCHOLAR_MODEL: str = "llama-3.3-70b-versatile"
    JUDGE_MODEL: str = "llama-3.3-70b-versatile"
    
    # Model Parameters
    TEMPERATURE: float = 0.1
    MAX_TOKENS: int = 4096
    
    # MCP Configuration
    MCP_ORBITAL_PORT: int = 5001
    MCP_LEGAL_PORT: int = 5002
    
    # Data Paths
    BASE_DIR: Path = Path(__file__).parent
    DATA_DIR: Path = BASE_DIR / "data"
    LEGAL_DB_PATH: Path = DATA_DIR / "legal_db"
    
    # CelesTrak Configuration
    CELESTRAK_BASE_URL: str = "https://celestrak.org/NORAD/elements/gp.php"
    CELESTRAK_TLE_FORMAT: str = "TLE"  # Use TLE format instead of JSON
    
    # Analysis Parameters
    COLLISION_THRESHOLD_KM: float = 1.0
    MANEUVER_DETECTION_WINDOW_HOURS: int = 48
    VELOCITY_CHANGE_THRESHOLD_MS: float = 0.5  # m/s
    
    # FastAPI Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_TITLE: str = "Orbital Jurist API"
    API_VERSION: str = "1.0.0"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()