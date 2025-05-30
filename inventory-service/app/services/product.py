import httpx
import logging
from typing import Dict, Optional
from tenacity import retry, stop_after_attempt, wait_fixed

from app.core.config import settings

logger = logging.getLogger(__name__)


class ProductServiceClient:
    """Client for interacting with the Product Service."""

    def __init__(self):
        self.base_url = str(settings.PRODUCT_SERVICE_URL)
        self.timeout = 5.0  # seconds
        self.max_retries = settings.MAX_RETRIES
        self.retry_delay = settings.RETRY_DELAY

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def get_product(self, product_id: str) -> Optional[Dict]:
        """
        Get product details by ID for notification enrichment.
        
        This method is used primarily for enriching low-stock notifications
        with product names. It's acceptable to use HTTP here since:
        1. It's for display purposes only (not core business logic)
        2. It has proper fallback handling
        3. Notifications can degrade gracefully if this fails
        
        Args:
            product_id: The ID of the product
            
        Returns:
            dict: Product details or None if not found
        """
        logger.info(f"Getting product details for notification: {product_id}")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/products/{product_id}")
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    logger.warning(f"Product not found for notification: {product_id}")
                    return None
                else:
                    logger.error(f"Error getting product for notification: {response.text}")
                    return None
        except httpx.RequestError as e:
            logger.error(f"Request error getting product for notification: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting product for notification: {str(e)}")
            return None

    async def get_product_name(self, product_id: str) -> str:
        """
        Get product name by ID, with fallback to product_id.
        
        This is a convenience method specifically for notifications
        that always returns a usable string.
        
        Args:
            product_id: The ID of the product
            
        Returns:
            str: Product name or product_id as fallback
        """
        try:
            product = await self.get_product(product_id)
            if product and 'name' in product:
                return product['name']
            else:
                logger.info(f"Using product_id as fallback name for: {product_id}")
                return product_id
        except Exception as e:
            logger.warning(f"Failed to get product name, using product_id: {str(e)}")
            return product_id


# Create a singleton instance
product_service = ProductServiceClient()