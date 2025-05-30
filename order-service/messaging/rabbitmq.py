# messaging/rabbitmq.py (to be added to each service)

import json
import logging
import asyncio
import aio_pika
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

class RabbitMQClient:
    """Client for interacting with RabbitMQ."""
    
    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        self.connection = None
        self.channel = None
    
    async def connect(self):
        """Establish connection to RabbitMQ."""
        if self.connection is None or self.connection.is_closed:
            try:
                self.connection = await aio_pika.connect_robust(self.connection_url)
                self.channel = await self.connection.channel()
                logger.info("Connected to RabbitMQ")
            except Exception as e:
                logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
                raise
    
    async def close(self):
        """Close the RabbitMQ connection."""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("Closed RabbitMQ connection")
    
    async def declare_queue(self, queue_name: str, durable: bool = True):
        """Declare a queue."""
        await self.connect()
        return await self.channel.declare_queue(
            queue_name,
            durable=durable
        )
    
    async def publish(self, queue_name: str, message: Dict[str, Any], correlation_id: Optional[str] = None):
        """Publish a message to a queue."""
        await self.connect()
        
        # Convert dict to JSON string
        message_body = json.dumps(message).encode()
        
        # Create message properties
        properties = {}
        if correlation_id:
            properties["correlation_id"] = correlation_id
        
        # Declare queue and publish message
        queue = await self.declare_queue(queue_name)
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=message_body,
                content_type="application/json",
                **properties
            ),
            routing_key=queue_name
        )
        logger.info(f"Published message to {queue_name}: {message}")
    
    async def consume(self, queue_name: str, callback: Callable, prefetch_count: int = 10):
        """Consume messages from a queue with the specified callback."""
        await self.connect()
        
        # Set QoS (prefetch_count)
        await self.channel.set_qos(prefetch_count=prefetch_count)
        
        # Declare queue
        queue = await self.declare_queue(queue_name)
        
        # Start consuming
        await queue.consume(callback)
        logger.info(f"Started consuming from {queue_name}")