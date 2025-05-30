# order-service/app/services/order_processor.py
import json
import logging
from datetime import datetime
from bson import ObjectId

from app.messaging.rabbitmq import RabbitMQClient
from app.core.config import settings
from app.db.mongodb import get_database

logger = logging.getLogger(__name__)

# Create RabbitMQ client
rabbitmq_client = RabbitMQClient(settings.RABBITMQ_URL)

async def start_order_processor():
    """Start consumer for order processed events."""
    await rabbitmq_client.connect()
    
    async def on_order_processed(message):
        async with message.process():
            try:
                data = json.loads(message.body.decode())
                order_id = data.get("order_id")
                status = data.get("status")
                
                # Update the order status to reflect processing completion
                db = get_database()
                
                if status == "processing":
                    # Order is now in processing state (inventory reserved)
                    # Here you'd typically set up payment processing or other workflows
                    
                    # For simplicity, we'll update the order to "paid" status
                    # In a real system, this would be triggered by payment confirmation
                    await db["orders"].update_one(
                        {"_id": ObjectId(order_id)},
                        {
                            "$set": {
                                "status": settings.ORDER_STATUS["PAID"],
                                "updated_at": datetime.utcnow()
                            }
                        }
                    )
                    logger.info(f"Order {order_id} marked as paid (simulated payment)")
                
            except Exception as e:
                logger.error(f"Error processing order processed message: {str(e)}")
    
    # Start consuming from the order processed queue
    await rabbitmq_client.consume(settings.ORDER_PROCESSED_QUEUE, on_order_processed)