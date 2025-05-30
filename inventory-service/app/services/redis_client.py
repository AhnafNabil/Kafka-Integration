import json
import logging
import redis.asyncio as redis
from typing import Any, Dict

from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisClient:
    """Client for interacting with Redis."""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client = None
    
    async def connect(self):
        """Establish connection to Redis."""
        if self.client is None:
            try:
                self.client = await redis.from_url(self.redis_url, decode_responses=True)
                logger.info("Connected to Redis")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {str(e)}")
                raise
    
    async def close(self):
        """Close the Redis connection."""
        if self.client:
            await self.client.close()
            logger.info("Closed Redis connection")
    
    async def publish(self, channel: str, message: Dict[str, Any]):
        """Publish a message to a Redis channel."""
        await self.connect()
        
        # Convert dict to JSON string
        message_json = json.dumps(message)
        
        # Publish message
        await self.client.publish(channel, message_json)
        logger.info(f"Published message to channel {channel}")
    
    async def add_to_stream(self, stream_name: str, fields: Dict[str, Any], max_len: int = 1000):
        """Add a message to a Redis Stream with automatic trimming."""
        await self.connect()
        
        # Add to stream and trim if needed
        await self.client.xadd(
            stream_name, 
            fields,
            maxlen=max_len,
            approximate=True
        )
        logger.info(f"Added message to stream {stream_name}")

# Create a singleton instance
redis_client = RedisClient(str(settings.REDIS_URL))