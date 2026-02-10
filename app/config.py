from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/ai_community_club"

    # Security
    SECRET_KEY: str = "change-me-to-a-real-secret-key-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 72

    # App
    APP_NAME: str = "AI Community Club"
    APP_URL: str = "http://localhost:8000"
    DEBUG: bool = False

    # Robokassa (stub)
    ROBOKASSA_MERCHANT_LOGIN: Optional[str] = None
    ROBOKASSA_PASSWORD_1: Optional[str] = None
    ROBOKASSA_PASSWORD_2: Optional[str] = None
    ROBOKASSA_TEST_MODE: bool = True

    # Email (stub)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
