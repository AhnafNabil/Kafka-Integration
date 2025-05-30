import os
from typing import Optional

from pydantic import BaseSettings, PostgresDsn, RedisDsn, EmailStr, validator


class Settings(BaseSettings):
    # API settings
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    PROJECT_NAME: str = "Notification Service"
    PORT: int = 8004
    
    # Database settings
    DATABASE_URL: PostgresDsn
    
    # Redis settings for notifications
    REDIS_URL: RedisDsn = "redis://redis:6379/0"
    NOTIFICATION_CHANNEL: str = "inventory:low-stock"
    
    # Email settings
    SMTP_HOST: str = "sandbox.smtp.mailtrap.io"
    SMTP_PORT: int = 2525
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: Optional[EmailStr] = None
    EMAIL_FROM_NAME: str = "E-commerce Notifications"
    
    # Admin email for receiving low stock notifications
    ADMIN_EMAIL: Optional[EmailStr] = "admin@example.com"
    
    # Notification processing settings
    NOTIFICATION_PROCESSING_INTERVAL: int = 30  # seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings object
settings = Settings()