"""Application settings using Pydantic Settings."""
from pydantic_settings import BaseSettings
from typing import Optional


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
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
