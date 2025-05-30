import httpx
import logging
from typing import Dict, Optional, Any
from tenacity import retry, stop_after_attempt, wait_fixed

from app.core.config import settings

logger = logging.getLogger(__name__)

class UserServiceClient:
    """Client for interacting with the User Service."""

    def __init__(self):
        self.base_url = str(settings.USER_SERVICE_URL) if settings.USER_SERVICE_URL else None
        self.timeout = 5.0  # seconds
        self.max_retries = 3
        self.retry_delay = 1  # seconds

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user details by ID.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            dict: User details or None if not found
        """
        if not self.base_url:
            logger.warning("User service URL not configured")
            return None
            
        logger.info(f"Getting user details for ID: {user_id}")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/users/{user_id}")
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    logger.warning(f"User not found: {user_id}")
                    return None
                else:
                    logger.error(f"Error getting user: {response.text}")
                    return None
        except httpx.RequestError as e:
            logger.error(f"Request error getting user: {str(e)}")
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def verify_user(self, user_id: str) -> bool:
        """
        Verify that a user exists and is active.
        
        Args:
            user_id: The ID of the user to check
            
        Returns:
            bool: True if user exists and is active, False otherwise
        """
        if not self.base_url:
            logger.warning("User service URL not configured")
            return False
            
        logger.info(f"Verifying user: {user_id}")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/users/{user_id}/verify")
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("valid", False)
                else:
                    logger.error(f"User verification failed: {response.text}")
                    return False
        except httpx.RequestError as e:
            logger.error(f"Error verifying user: {str(e)}")
            return False


# Create a singleton instance
user_service = UserServiceClient()