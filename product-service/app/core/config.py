import os
from typing import Optional
from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    # API settings
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    PROJECT_NAME: str = "Product Service"
    
    # MongoDB settings
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "product_db"
    
    # Kafka settings - FIXED: Use Docker-friendly default
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:29092"  # Changed from localhost:9092
    KAFKA_CLIENT_ID: str = "product-service"
    
    # JWT Auth settings (for testing/development)
    SECRET_KEY: str = "development-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create global settings object
settings = Settings()