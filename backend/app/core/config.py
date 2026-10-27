import os
from typing import List
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "SentinelFlow AI — The Self-Directed Fraud Investigation Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() in ("true", "1")
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    
    # Database URL: default SQLite with path resolution, or Supabase PostgreSQL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./sentinelflow.db")
    
    # Supabase Integration (Database, Auth, Storage, Email)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")
    SUPABASE_STORAGE_BUCKET: str = os.getenv("SUPABASE_STORAGE_BUCKET", "evidence-files")
    
    # Security & Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "sentinelflow_super_secret_demo_key_9874123")
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
