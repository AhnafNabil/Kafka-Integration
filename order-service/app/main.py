from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import orders
from app.core.config import settings
from app.db.mongodb import close_mongo_connection, connect_to_mongo
from app.services import rabbitmq_service
from app.services import order_processor

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Order Service API",
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
app.include_router(orders.router, prefix=settings.API_PREFIX)

# Register startup and shutdown events
app.add_event_handler("startup", connect_to_mongo)
app.add_event_handler("shutdown", close_mongo_connection)

# Add this to the startup event handlers
@app.on_event("startup")
async def start_rabbitmq_consumers():
    """Start RabbitMQ consumers."""
    await rabbitmq_service.start_inventory_consumers()

# Add this to the shutdown event handlers
@app.on_event("shutdown")
async def close_rabbitmq_connection():
    """Close RabbitMQ connection."""
    await rabbitmq_service.rabbitmq_client.close()

# Add this to the startup event handlers
@app.on_event("startup")
async def start_order_processor():
    """Start order processor consumer."""
    await order_processor.start_order_processor()

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "order-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)