# order-service/app/services/rabbitmq_service.py
from app.messaging.rabbitmq import RabbitMQClient
from app.core.config import settings

# Create RabbitMQ client
rabbitmq_client = RabbitMQClient(settings.RABBITMQ_URL)

async def publish_order_created(order_id: str, order_data: dict):
    """Publish an order created event to RabbitMQ."""
    await rabbitmq_client.publish(
        queue_name=settings.ORDER_CREATED_QUEUE,
        message={
            "order_id": order_id,
            "order_data": order_data
        },
        correlation_id=order_id
    )

async def start_inventory_consumers():
    """Start consumers for inventory-related queues."""
    await rabbitmq_client.connect()
    
    # Handler for inventory reserved events
    async def on_inventory_reserved(message):
        async with message.process():
            try:
                data = json.loads(message.body.decode())
                order_id = data.get("order_id")
                
                # Update the order status to reflect inventory reservation
                db = get_database()
                await db["orders"].update_one(
                    {"_id": ObjectId(order_id)},
                    {
                        "$set": {
                            "status": settings.ORDER_STATUS["PROCESSING"],
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
                
                logger.info(f"Order {order_id} updated: inventory reserved")
                
                # Publish to order processed queue (simplified flow)
                await rabbitmq_client.publish(
                    settings.ORDER_PROCESSED_QUEUE,
                    {
                        "order_id": order_id,
                        "status": "processing",
                        "message": "Inventory reserved successfully"
                    },
                    correlation_id=order_id
                )
            except Exception as e:
                logger.error(f"Error processing inventory reserved message: {str(e)}")
    
    # Handler for inventory failed events
    async def on_inventory_failed(message):
        async with message.process():
            try:
                data = json.loads(message.body.decode())
                order_id = data.get("order_id")
                reason = data.get("reason", "Unknown reason")
                
                # Update the order status to reflect inventory failure
                db = get_database()
                await db["orders"].update_one(
                    {"_id": ObjectId(order_id)},
                    {
                        "$set": {
                            "status": settings.ORDER_STATUS["CANCELLED"],
                            "cancellation_reason": f"Inventory not available: {reason}",
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
                
                logger.info(f"Order {order_id} cancelled: inventory not available")
            except Exception as e:
                logger.error(f"Error processing inventory failed message: {str(e)}")
    
    # Start consuming from inventory queues
    await rabbitmq_client.consume(settings.INVENTORY_RESERVED_QUEUE, on_inventory_reserved)
    await rabbitmq_client.consume(settings.INVENTORY_FAILED_QUEUE, on_inventory_failed)