import logging
from typing import Optional
from app.core.config import settings
from events.kafka_client import KafkaClient, KafkaTopics
from events.schemas import ProductCreatedEvent, ProductCreatedEventData, ProductUpdatedEvent, ProductUpdatedEventData

logger = logging.getLogger(__name__)


class ProductEventProducer:
    """Producer for publishing product events to Kafka"""
    
    def __init__(self):
        self.kafka_client = KafkaClient(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            client_id=settings.KAFKA_CLIENT_ID
        )
    
    async def start(self):
        """Initialize the Kafka producer"""
        await self.kafka_client.start_producer()
        logger.info("Product event producer started")
    
    async def stop(self):
        """Stop the Kafka producer"""
        await self.kafka_client.stop_producer()
        logger.info("Product event producer stopped")
    
    async def publish_product_created(
        self,
        product_id: str,
        name: str,
        description: str,
        category: str,
        price: float,
        initial_quantity: int,
        reorder_threshold: Optional[int] = None
    ) -> bool:
        """
        Publish a product created event
        
        Args:
            product_id: MongoDB ObjectId as string
            name: Product name
            description: Product description
            category: Product category
            price: Product price
            initial_quantity: Initial quantity for inventory
            reorder_threshold: Low stock threshold
            
        Returns:
            bool: True if event was published successfully
        """
        try:
            # Calculate reorder threshold if not provided
            if reorder_threshold is None:
                reorder_threshold = max(5, int(initial_quantity * 0.1))
            
            logger.info(f"Publishing product.created event for {product_id} ({name})")
            
            # Create the event
            event_data = ProductCreatedEventData(
                product_id=product_id,
                name=name,
                description=description,
                category=category,
                price=price,
                initial_quantity=initial_quantity,
                reorder_threshold=reorder_threshold
            )
            
            event = ProductCreatedEvent(data=event_data)
            
            # Use product_id as the message key for partitioning
            success = await self.kafka_client.publish_event(
                topic=KafkaTopics.PRODUCT_EVENTS,
                event=event,
                key=product_id
            )
            
            if success:
                logger.info(f"✅ Published product.created event for product {product_id}")
            else:
                logger.error(f"❌ Failed to publish product.created event for product {product_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error publishing product.created event for product {product_id}: {str(e)}")
            return False
    
    async def publish_product_updated(
        self,
        product_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        price: Optional[float] = None,
        quantity: Optional[int] = None
    ) -> bool:
        """
        Publish a product updated event
        
        Args:
            product_id: MongoDB ObjectId as string
            name: Updated product name
            description: Updated product description
            category: Updated product category
            price: Updated product price
            quantity: Updated product quantity
            
        Returns:
            bool: True if event was published successfully
        """
        try:
            logger.info(f"Publishing product.updated event for {product_id}")
            
            # Create the event
            event_data = ProductUpdatedEventData(
                product_id=product_id,
                name=name,
                description=description,
                category=category,
                price=price,
                quantity=quantity
            )
            
            event = ProductUpdatedEvent(data=event_data)
            
            # Use product_id as the message key for partitioning
            success = await self.kafka_client.publish_event(
                topic=KafkaTopics.PRODUCT_EVENTS,
                event=event,
                key=product_id
            )
            
            if success:
                logger.info(f"✅ Published product.updated event for product {product_id}")
            else:
                logger.error(f"❌ Failed to publish product.updated event for product {product_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error publishing product.updated event for product {product_id}: {str(e)}")
            return False


# Create a singleton instance
product_event_producer = ProductEventProducer()