import os
from typing import Optional, Dict, Any

from pydantic import BaseSettings, AnyHttpUrl, validator, PostgresDsn, RedisDsn


class Settings(BaseSettings):
    # API settings
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    PROJECT_NAME: str = "Inventory Service"
    PORT: int = 8002

    # RabbitMQ settings
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"
    ORDER_CREATED_QUEUE: str = "order_created"
    INVENTORY_RESERVED_QUEUE: str = "inventory_reserved"
    INVENTORY_FAILED_QUEUE: str = "inventory_failed"
    
    # Kafka settings - FIXED: Use Docker-friendly default
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:29092"  # Changed from localhost:9092
    KAFKA_CLIENT_ID: str = "inventory-service"
    KAFKA_CONSUMER_GROUP: str = "inventory-consumer-group"
    
    # Database settings
    DATABASE_URL: PostgresDsn
    
    # Service URLs
    PRODUCT_SERVICE_URL: AnyHttpUrl
    
    # Retry Configuration
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 1  # seconds
    
    # JWT Auth settings (for testing/development)
    SECRET_KEY: str = "development-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Inventory settings
    LOW_STOCK_THRESHOLD: int = 5
    ENABLE_NOTIFICATIONS: bool = True
    
    # Redis settings for notifications
    REDIS_URL: RedisDsn = "redis://redis:6379/0"
    NOTIFICATION_CHANNEL: str = "inventory:low-stock"
    
    # Validate URLs are properly formatted
    @validator("PRODUCT_SERVICE_URL", pre=True)
    def validate_service_urls(cls, v):
        if isinstance(v, str) and not v.startswith(("http://", "https://")):
            return f"http://{v}"
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings object
settings = Settings()