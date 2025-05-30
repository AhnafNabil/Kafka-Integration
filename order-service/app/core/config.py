import os
from typing import Optional, Dict, Any, List

from pydantic import BaseSettings, AnyHttpUrl, validator


class Settings(BaseSettings):
    # API settings
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    PROJECT_NAME: str = "Order Service"
    PORT: int = 8001

    # Add these settings
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"
    ORDER_CREATED_QUEUE: str = "order_created"
    INVENTORY_RESERVED_QUEUE: str = "inventory_reserved"
    INVENTORY_FAILED_QUEUE: str = "inventory_failed"
    ORDER_PROCESSED_QUEUE: str = "order_processed"
    
    # MongoDB settings
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "order_db"
    
    # Service URLs
    USER_SERVICE_URL: AnyHttpUrl
    PRODUCT_SERVICE_URL: AnyHttpUrl
    INVENTORY_SERVICE_URL: AnyHttpUrl
    
    # Retry Configuration
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 1  # seconds
    
    # JWT Auth settings (for testing/development)
    SECRET_KEY: str = "development-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Order status codes
    ORDER_STATUS: Dict[str, str] = {
        "PENDING": "pending",
        "PAID": "paid",
        "PROCESSING": "processing",
        "SHIPPED": "shipped",
        "DELIVERED": "delivered",
        "CANCELLED": "cancelled",
        "REFUNDED": "refunded"
    }
    
    # Status transitions that are allowed
    ALLOWED_STATUS_TRANSITIONS: Dict[str, List[str]] = {
        "pending": ["paid", "cancelled"],
        "paid": ["processing", "cancelled", "refunded"],
        "processing": ["shipped", "cancelled", "refunded"],
        "shipped": ["delivered", "refunded"],
        "delivered": ["refunded"],
        "cancelled": [],
        "refunded": []
    }
    
    # Validate URLs are properly formatted
    @validator("USER_SERVICE_URL", "PRODUCT_SERVICE_URL", "INVENTORY_SERVICE_URL", pre=True)
    def validate_service_urls(cls, v):
        if isinstance(v, str) and not v.startswith(("http://", "https://")):
            return f"http://{v}"
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings object
settings = Settings()