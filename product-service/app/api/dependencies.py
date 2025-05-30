from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.db.mongodb import get_database

# OAuth2 configuration - in a microservice architecture, 
# actual token validation would typically happen at the gateway level
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    This is a stub dependency for authentication.
    
    In a real microservice architecture, the API gateway would validate
    the token and pass user details in request headers. This stub is included
    to maintain the API contract while allowing tests without actual auth.
    """
    if token is None:
        # This allows endpoints to be called without auth during development/testing
        # In production, the gateway should block unauthenticated requests
        return {"sub": "test-user", "is_admin": True}
    
    # In production, this function would verify the token signature
    # and decode the payload to get user information
    return {"sub": "authenticated-user", "is_admin": True}


async def get_db():
    """Dependency for database access."""
    return get_database()