# inventory-service/app/services/rabbitmq_service.py
import json
import logging
from datetime import datetime
from sqlalchemy import select

from app.messaging.rabbitmq import RabbitMQClient
from app.core.config import settings
from app.db.postgresql import AsyncSessionLocal
from app.models.inventory import InventoryItem, InventoryHistory

# ADD THIS IMPORT - This is the key fix!
from app.api.routes.inventory import check_and_notify_low_stock

logger = logging.getLogger(__name__)

# Create RabbitMQ client
rabbitmq_client = RabbitMQClient(settings.RABBITMQ_URL)

async def start_order_consumer():
    """Start consumer for order created events."""
    await rabbitmq_client.connect()
    
    async def on_order_created(message):
        async with message.process():
            try:
                # Get the correlation ID for response publishing
                correlation_id = message.correlation_id
                
                # Parse the message body
                data = json.loads(message.body.decode())
                order_id = data.get("order_id")
                order_data = data.get("order_data", {})
                items = order_data.get("items", [])
                
                # For tracking which products need inventory reservation
                inventory_results = []
                
                # Create async session for database operations
                async with AsyncSessionLocal() as db:
                    for item in items:
                        product_id = item.get("product_id")
                        quantity = item.get("quantity", 0)
                        
                        # Query inventory
                        query = select(InventoryItem).where(InventoryItem.product_id == product_id)
                        result = await db.execute(query)
                        inventory_item = result.scalars().first()
                        
                        if not inventory_item:
                            # Inventory not found
                            inventory_results.append({
                                "product_id": product_id,
                                "success": False,
                                "reason": "Inventory not found"
                            })
                            continue
                        
                        if inventory_item.available_quantity < quantity:
                            # Insufficient inventory
                            inventory_results.append({
                                "product_id": product_id, 
                                "success": False,
                                "reason": f"Insufficient inventory. Available: {inventory_item.available_quantity}, Requested: {quantity}"
                            })
                            continue
                        
                        # Reserve inventory
                        new_available = inventory_item.available_quantity - quantity
                        new_reserved = inventory_item.reserved_quantity + quantity
                        
                        inventory_item.available_quantity = new_available
                        inventory_item.reserved_quantity = new_reserved
                        inventory_item.updated_at = datetime.utcnow()
                        
                        # Add history record
                        history = InventoryHistory(
                            product_id=product_id,
                            quantity_change=-quantity,
                            previous_quantity=inventory_item.available_quantity + quantity,
                            new_quantity=inventory_item.available_quantity,
                            change_type="reserve",
                            reference_id=order_id
                        )
                        db.add(history)
                        
                        inventory_results.append({
                            "product_id": product_id,
                            "success": True,
                            "available_quantity": new_available,
                            "reserved_quantity": new_reserved
                        })
                    
                    # Check if all products have been reserved successfully
                    all_success = all(result.get("success", False) for result in inventory_results)
                    
                    if all_success:
                        # All inventory reservations successful
                        await db.commit()
                        
                        # 🔧 FIX: Check for low stock notifications after successful reservation
                        for item in items:
                            product_id = item.get("product_id")
                            
                            # Get the updated inventory item
                            query = select(InventoryItem).where(InventoryItem.product_id == product_id)
                            result = await db.execute(query)
                            updated_inventory_item = result.scalars().first()
                            
                            if updated_inventory_item:
                                # Call the same notification function used by the API
                                await check_and_notify_low_stock(updated_inventory_item)
                                logger.info(f"Checked low stock notification for product {product_id} after order processing")
                        
                        # Publish success message
                        await rabbitmq_client.publish(
                            queue_name=settings.INVENTORY_RESERVED_QUEUE,
                            message={
                                "order_id": order_id,
                                "status": "reserved",
                                "results": inventory_results
                            },
                            correlation_id=correlation_id
                        )
                        logger.info(f"Successfully reserved inventory for order {order_id}")
                    else:
                        # Failed to reserve some inventory
                        await db.rollback()
                        
                        # Publish failure message
                        failed_items = [item for item in inventory_results if not item.get("success", False)]
                        await rabbitmq_client.publish(
                            queue_name=settings.INVENTORY_FAILED_QUEUE,
                            message={
                                "order_id": order_id,
                                "status": "failed",
                                "reason": "Failed to reserve inventory",
                                "details": failed_items
                            },
                            correlation_id=correlation_id
                        )
                        logger.warning(f"Failed to reserve inventory for order {order_id}")
            
            except Exception as e:
                logger.error(f"Error processing order created message: {str(e)}")
                
                # Try to publish failure message
                try:
                    await rabbitmq_client.publish(
                        queue_name=settings.INVENTORY_FAILED_QUEUE,
                        message={
                            "order_id": data.get("order_id") if 'data' in locals() else "unknown",
                            "status": "error",
                            "reason": f"Internal error: {str(e)}"
                        },
                        correlation_id=message.correlation_id if message.correlation_id else None
                    )
                except Exception as publish_error:
                    logger.error(f"Failed to publish error message: {str(publish_error)}")
    
    # Start consuming from the order created queue
    await rabbitmq_client.consume(settings.ORDER_CREATED_QUEUE, on_order_created)

async def start_inventory_release_consumer():
    """Start consumer for inventory release events."""
    await rabbitmq_client.connect()
    
    async def on_inventory_release(message):
        async with message.process():
            try:
                data = json.loads(message.body.decode())
                order_id = data.get("order_id")
                product_id = data.get("product_id")
                quantity = data.get("quantity", 0)
                
                async with AsyncSessionLocal() as db:
                    # Get inventory item
                    query = select(InventoryItem).where(InventoryItem.product_id == product_id)
                    result = await db.execute(query)
                    inventory_item = result.scalars().first()
                    
                    if not inventory_item:
                        logger.warning(f"Inventory not found for product {product_id} when releasing")
                        return
                    
                    # Release inventory
                    new_reserved = max(0, inventory_item.reserved_quantity - quantity)
                    released_quantity = inventory_item.reserved_quantity - new_reserved
                    new_available = inventory_item.available_quantity + released_quantity
                    
                    inventory_item.reserved_quantity = new_reserved
                    inventory_item.available_quantity = new_available
                    inventory_item.updated_at = datetime.utcnow()
                    
                    # Add history record
                    history = InventoryHistory(
                        product_id=product_id,
                        quantity_change=released_quantity,
                        previous_quantity=inventory_item.available_quantity - released_quantity,
                        new_quantity=inventory_item.available_quantity,
                        change_type="release",
                        reference_id=order_id
                    )
                    db.add(history)
                    
                    await db.commit()
                    
                    # 🔧 Note: We don't usually notify on inventory release (stock going up)
                    # But if you want to notify when stock is replenished, you could add it here
                    
                    logger.info(f"Released {released_quantity} units of {product_id} from order {order_id}")
            
            except Exception as e:
                logger.error(f"Error processing inventory release message: {str(e)}")
    
    # Start consuming from the inventory release queue
    await rabbitmq_client.consume("inventory_release", on_inventory_release)

# Update the start_order_consumer function to also start the release consumer
async def start_consumers():
    """Start all RabbitMQ consumers."""
    await start_order_consumer()
    await start_inventory_release_consumer()