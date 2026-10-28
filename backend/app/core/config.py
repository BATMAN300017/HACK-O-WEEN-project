import os
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

DEVELOPMENT_SECRET_KEY = "sentinelflow_super_secret_demo_key_9874123"


def validate_production_secret_key(environment: str, secret_key: str) -> None:
    if environment.lower() in ("development", "test"):
        return

    normalized_key = secret_key.strip()
    if (
        len(normalized_key) < 32
        or normalized_key == DEVELOPMENT_SECRET_KEY
        or normalized_key.startswith("replace-this")
    ):
        raise RuntimeError(
            "Set a unique SECRET_KEY of at least 32 characters before running outside development or test."
        )


class Settings(BaseModel):
    PROJECT_NAME: str = "SentinelFlow AI — The Self-Directed Fraud Investigation Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() in ("true", "1")
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    
    # SQLite is the only database backend currently implemented.
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./sentinelflow.db")
    
    # Security & Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", DEVELOPMENT_SECRET_KEY)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
    ALGORITHM: str = "HS256"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]
    
    # Risk Ensemble Weights (configurable, defaults from spec)
    RULE_ENGINE_WEIGHT: float = float(os.getenv("RULE_ENGINE_WEIGHT", "0.30"))
    BEHAVIORAL_ANOMALY_WEIGHT: float = float(os.getenv("BEHAVIORAL_ANOMALY_WEIGHT", "0.25"))
    SUPERVISED_MODEL_WEIGHT: float = float(os.getenv("SUPERVISED_MODEL_WEIGHT", "0.25"))
    GRAPH_INTELLIGENCE_WEIGHT: float = float(os.getenv("GRAPH_INTELLIGENCE_WEIGHT", "0.20"))
    
    # Triage Bands
    TRIAGE_ROUTINE_MAX: int = 24
    TRIAGE_LOW_MAX: int = 49
    TRIAGE_ELEVATED_MAX: int = 74
    TRIAGE_HIGH_MIN: int = 75
    
    # Investigation Agent Boundaries
    MAX_GRAPH_DEPTH: int = int(os.getenv("MAX_GRAPH_DEPTH", "3"))
    MAX_ENTITIES_PER_INVESTIGATION: int = int(os.getenv("MAX_ENTITIES_PER_INVESTIGATION", "50"))
    MAX_TRANSACTIONS_EXAMINED: int = int(os.getenv("MAX_TRANSACTIONS_EXAMINED", "200"))
    MAX_EXECUTION_TIME_SECONDS: int = int(os.getenv("MAX_EXECUTION_TIME_SECONDS", "30"))
    
    # Optional LLM
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "mock")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

settings = Settings()
