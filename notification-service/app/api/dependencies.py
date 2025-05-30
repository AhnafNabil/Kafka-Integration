from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# Simple authentication stub for API endpoints
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Simplified authentication stub that always returns an admin user.
    In a real production environment, this would validate the token properly.
    """
    # For simplified admin-only system, we just return an admin user
    return {"is_admin": True}