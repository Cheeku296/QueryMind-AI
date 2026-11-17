import os
from typing import List, Optional
from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "QueryMind AI"
    APP_ENV: str = "development"
    PORT: int = 8000
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = "qm_jwt_secret_dev_3e8b7d6a5c4b3a2f1e0d9c8b7a6f5e4d"
    ENCRYPTION_KEY: str = "Wk5qT3F5SnptZld6cVR5TXVpT2FDSndzck12TFFzRGs="
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Application Databases
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgrespassword@localhost:5432/querymind"
    ASYNC_DATABASE_URL: str = "postgresql+asyncpg://postgres:postgrespassword@localhost:5432/querymind"

    # Demo Target Database
    DEMO_DATABASE_URL: str = "postgresql+psycopg://postgres:postgrespassword@localhost:5432/querymind_demo"
    ASYNC_DEMO_DATABASE_URL: str = "postgresql+asyncpg://postgres:postgrespassword@localhost:5432/querymind_demo"

    # Cache & Queue
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Qdrant Vector Store
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION: str = "querymind_schemas"

    # AI Configuration
    LLM_PROVIDER: str = "gemini"  # Default: Google Gemini
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google AI Studio Gemini API Key")
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"

    # Optional local Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1"

    # LangSmith Observability
    LANGSMITH_API_KEY: Optional[str] = None
    LANGSMITH_TRACING: bool = False
    LANGCHAIN_PROJECT: str = "querymind-ai"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://localhost:80",
    ]

    # Execution Governance
    SQL_QUERY_TIMEOUT_SECONDS: int = 15
    SQL_MAX_ROWS_RETURNED: int = 500
    SQL_MAX_CORRECTION_ATTEMPTS: int = 2

    @field_validator("GEMINI_API_KEY")
    @classmethod
    def validate_gemini_key(cls, v: Optional[str]) -> Optional[str]:
        if not v or v.strip() in ("", "PASTE_YOUR_NEW_GEMINI_API_KEY_HERE", "YOUR_GEMINI_API_KEY"):
            return None
        return v.strip()


settings = Settings()
