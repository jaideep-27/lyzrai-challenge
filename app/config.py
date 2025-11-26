"""
Configuration settings for PR Review Agent
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Google Gemini
    google_api_key: str = ""
    
    # GitHub
    github_token: str = ""
    
    # Database
    database_url: str = "sqlite:///./pr_reviews.db"
    
    # App Settings
    debug: bool = True
    log_level: str = "INFO"
    
    # LLM Settings
    llm_model: str = "gemini-2.0-flash"
    llm_temperature: float = 0.3
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
