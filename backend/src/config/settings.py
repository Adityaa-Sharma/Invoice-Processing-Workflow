"""Application settings using Pydantic Settings."""
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration settings."""
    
    # Application
    APP_NAME: str = "Invoice Processing Workflow"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "sqlite:///./demo.db"
    
    # Workflow
    MATCH_THRESHOLD: float = 0.90
    TWO_WAY_TOLERANCE_PCT: float = 5.0
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # LLM - Gemini
    GEMINI_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gemini-2.0-flash"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_RETRIES: int = 2
    
    # MCP Servers
    COMMON_MCP_URL: str = "http://localhost:8001"
    ATLAS_MCP_URL: str = "http://localhost:8002"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
