import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import inventory
from app.core.config import settings
from app.db.postgresql import initialize_db, close_db_connection
from app.services import rabbitmq_service
from app.services.redis_client import redis_client
from app.services.kafka_consumer import inventory_event_consumer

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Inventory Service API",
    version="1.0.0",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up API routes
app.include_router(inventory.router, prefix=settings.API_PREFIX)

# Register startup and shutdown events
app.add_event_handler("startup", initialize_db)
app.add_event_handler("shutdown", close_db_connection)

# RabbitMQ event handlers
@app.on_event("startup")
async def start_rabbitmq_consumers():
    """Start RabbitMQ consumers."""
    await rabbitmq_service.start_consumers()

@app.on_event("shutdown")
async def close_rabbitmq_connection():
    """Close RabbitMQ connection."""
    await rabbitmq_service.rabbitmq_client.close()

# Redis connection handling
@app.on_event("startup")
async def connect_to_redis():
    """Connect to Redis."""
    await redis_client.connect()

@app.on_event("shutdown")
async def close_redis_connection():
    """Close Redis connection."""
    await redis_client.close()

# Kafka event handlers
@app.on_event("startup")
async def start_kafka_consumer():
    """Start Kafka consumer for product events."""
    # Start the consumer in a background task
    asyncio.create_task(inventory_event_consumer.start())

@app.on_event("shutdown")
async def stop_kafka_consumer():
    """Stop Kafka consumer."""
    await inventory_event_consumer.stop()

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "inventory-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)