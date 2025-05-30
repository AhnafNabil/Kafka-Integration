from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import notifications
from app.core.config import settings
from app.db.postgresql import initialize_db, close_db_connection
from app.services.redis_client import redis_client
from app.services.notification_processor import notification_processor

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Notification Service API",
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
app.include_router(notifications.router, prefix=settings.API_PREFIX)

# Register startup and shutdown events
app.add_event_handler("startup", initialize_db)
app.add_event_handler("shutdown", close_db_connection)

# Add Redis connection handling
@app.on_event("startup")
async def connect_to_redis():
    """Connect to Redis."""
    await redis_client.connect()

@app.on_event("shutdown")
async def close_redis_connection():
    """Close Redis connection."""
    await redis_client.close()

# Start notification processor
@app.on_event("startup")
async def start_notification_processor():
    """Start the notification processor."""
    await notification_processor.start()

@app.on_event("shutdown")
async def stop_notification_processor():
    """Stop the notification processor."""
    await notification_processor.stop()

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "notification-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)