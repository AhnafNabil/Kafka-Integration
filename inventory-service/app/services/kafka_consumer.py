import json
import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, text  # Added text import
from datetime import datetime

from app.core.config import settings
from app.db.postgresql import AsyncSessionLocal
from app.models.inventory import InventoryItem, InventoryHistory
from events.kafka_client import KafkaClient, KafkaTopics
from events.schemas import InventoryCreatedEvent, InventoryCreatedEventData, EventMetadata

logger = logging.getLogger(__name__)


class InventoryEventConsumer:
    """Consumer for processing product events from Kafka"""
    
    def __init__(self):
        self.kafka_client = KafkaClient(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            client_id=settings.KAFKA_CLIENT_ID
        )
        self.consumer = None
        self.running = False
    
    async def start(self):
        """Start the Kafka consumer"""
        try:
            logger.info("Starting inventory event consumer...")
            
            # Create consumer for product events
            self.consumer = await self.kafka_client.create_consumer(
                topics=[KafkaTopics.PRODUCT_EVENTS],
                group_id=settings.KAFKA_CONSUMER_GROUP,
                auto_offset_reset='earliest'
            )
            
            logger.info("Inventory event consumer created successfully")
            
            # Start consuming events
            await self.kafka_client.consume_events(
                consumer=self.consumer,
                message_handler=self.handle_product_event
            )
            
        except Exception as e:
            logger.error(f"Error starting inventory event consumer: {str(e)}")
            raise
    
    async def stop(self):
        """Stop the Kafka consumer"""
        await self.kafka_client.stop_consumers()
        logger.info("Inventory event consumer stopped")
    
    async def handle_product_event(self, message: Dict[str, Any]) -> bool:
        """
        Handle product events from Kafka
        
        Args:
            message: The Kafka message containing the event
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        try:
            # Extract event metadata
            metadata = message.get('metadata', {})
            event_type = metadata.get('event_type')
            event_id = metadata.get('event_id')
            
            logger.info(f"Processing event: {event_type} (ID: {event_id})")
            
            # Route to appropriate handler
            if event_type == "product.created":
                return await self.handle_product_created(message)
            elif event_type == "product.updated":
                return await self.handle_product_updated(message)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                return True  # Return True to avoid retries for unknown events
                
        except Exception as e:
            logger.error(f"Error handling product event: {str(e)}")
            return False
    
    async def handle_product_created(self, message: Dict[str, Any]) -> bool:
        """
        Handle product created events and create inventory
        
        Args:
            message: The Kafka message containing the product created event
            
        Returns:
            bool: True if inventory was created successfully
        """
        try:
            # Extract event data
            data = message.get('data', {})
            product_id = data.get('product_id')
            name = data.get('name')
            initial_quantity = data.get('initial_quantity', 0)
            reorder_threshold = data.get('reorder_threshold', 5)
            
            if not product_id:
                logger.error("Product ID missing in product.created event")
                return False
            
            logger.info(f"Creating inventory for product {product_id} ({name}) with quantity {initial_quantity}")
            
            # Create inventory item
            async with AsyncSessionLocal() as db:
                try:
                    # FIXED: Check if inventory already exists using proper SQLAlchemy syntax
                    result = await db.execute(
                        select(InventoryItem.id).where(InventoryItem.product_id == product_id)
                    )
                    if result.scalar():
                        logger.info(f"Inventory for product {product_id} already exists, skipping")
                        return True
                    
                    # Create new inventory item
                    inventory_item = InventoryItem(
                        product_id=product_id,
                        available_quantity=initial_quantity,
                        reserved_quantity=0,
                        reorder_threshold=reorder_threshold
                    )
                    
                    db.add(inventory_item)
                    await db.flush()  # Get the ID
                    
                    # Create history entry
                    history_entry = InventoryHistory(
                        product_id=product_id,
                        quantity_change=initial_quantity,
                        previous_quantity=0,
                        new_quantity=initial_quantity,
                        change_type="add",
                        reference_id=f"product_created_{product_id}"
                    )
                    db.add(history_entry)
                    
                    await db.commit()
                    await db.refresh(inventory_item)
                    
                    logger.info(
                        f"✅ Successfully created inventory for product {product_id}: "
                        f"quantity={initial_quantity}, threshold={reorder_threshold}"
                    )
                    
                    # Publish inventory created event (optional, for other services)
                    await self.publish_inventory_created_event(
                        inventory_item=inventory_item,
                        correlation_id=message.get('metadata', {}).get('event_id')
                    )
                    
                    return True
                    
                except IntegrityError as e:
                    await db.rollback()
                    logger.warning(f"Inventory for product {product_id} already exists (integrity error)")
                    return True  # This is expected if processed before
                    
                except Exception as e:
                    await db.rollback()
                    logger.error(f"Database error creating inventory for product {product_id}: {str(e)}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error handling product created event: {str(e)}")
            return False
    
    async def handle_product_updated(self, message: Dict[str, Any]) -> bool:
        """
        Handle product updated events
        
        Args:
            message: The Kafka message containing the product updated event
            
        Returns:
            bool: True if processing was successful
        """
        try:
            # Extract event data
            data = message.get('data', {})
            product_id = data.get('product_id')
            
            logger.info(f"Processing product updated event for product {product_id}")
            
            # For now, we'll just log the update
            # In the future, you might want to update inventory metadata
            # or trigger specific actions based on product changes
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling product updated event: {str(e)}")
            return False
    
    async def publish_inventory_created_event(
        self, 
        inventory_item: InventoryItem, 
        correlation_id: str = None
    ):
        """
        Publish an inventory created event (optional, for other services)
        
        Args:
            inventory_item: The created inventory item
            correlation_id: Original event ID for correlation
        """
        try:
            # Create inventory created event
            event_data = InventoryCreatedEventData(
                product_id=inventory_item.product_id,
                inventory_id=inventory_item.id,
                available_quantity=inventory_item.available_quantity,
                reserved_quantity=inventory_item.reserved_quantity,
                reorder_threshold=inventory_item.reorder_threshold,
                status="created"
            )
            
            metadata = EventMetadata(
                event_type="inventory.created",
                source="inventory-service",
                correlation_id=correlation_id
            )
            
            event = InventoryCreatedEvent(
                metadata=metadata,
                data=event_data
            )
            
            # Publish to inventory events topic
            success = await self.kafka_client.publish_event(
                topic=KafkaTopics.INVENTORY_EVENTS,
                event=event,
                key=inventory_item.product_id
            )
            
            if success:
                logger.info(f"Published inventory.created event for product {inventory_item.product_id}")
            else:
                logger.warning(f"Failed to publish inventory.created event for product {inventory_item.product_id}")
                
        except Exception as e:
            logger.error(f"Error publishing inventory created event: {str(e)}")


# Create a singleton instance
inventory_event_consumer = InventoryEventConsumer()