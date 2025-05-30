from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import users, auth
from app.core.config import settings
from app.db.postgresql import initialize_db, close_db_connection

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="User Service API",
    version="1.0.0",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up API routes
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(users.router, prefix=settings.API_PREFIX)

# Register startup and shutdown events
app.add_event_handler("startup", initialize_db)
app.add_event_handler("shutdown", close_db_connection)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "user-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)