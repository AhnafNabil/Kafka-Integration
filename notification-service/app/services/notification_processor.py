# notification-service/app/services/notification_processor.py
import json
import logging
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.postgresql import AsyncSessionLocal
from app.models.notification import Notification
from app.services.redis_client import redis_client
from app.services.email_provider import email_provider

logger = logging.getLogger(__name__)

class NotificationProcessor:
    """Simplified processor for handling admin notifications."""
    
    def __init__(self):
        self.running = False
    
    async def start(self):
        """Start the notification processor."""
        self.running = True
        
        # Start the Redis subscription for real-time notifications
        asyncio.create_task(self.listen_for_notifications())
        
        logger.info("Notification processor started")
    
    async def stop(self):
        """Stop the notification processor."""
        self.running = False
        await redis_client.stop()
        logger.info("Notification processor stopped")
    
    async def listen_for_notifications(self):
        """Listen for notifications from Redis pub/sub."""
        channel = settings.NOTIFICATION_CHANNEL
        await redis_client.subscribe(channel, self.handle_notification)
    
    async def handle_notification(self, data: dict):
        """Handle a notification received from Redis."""
        logger.info(f"Received notification: {data}")
        
        try:
            notification_type = data.get("type")
            
            if notification_type == "low_stock":
                await self.handle_low_stock_notification(data)
            else:
                logger.warning(f"Unknown notification type: {notification_type}")
        
        except Exception as e:
            logger.error(f"Error handling notification: {str(e)}")
    
    async def handle_low_stock_notification(self, data: dict):
        """Handle a low stock notification and send to admin email."""
        product_id = data.get("product_id")
        product_name = data.get("product_name", product_id)
        current_quantity = data.get("current_quantity")
        threshold = data.get("threshold")
        
        if not product_id or current_quantity is None or threshold is None:
            logger.error(f"Invalid low stock notification data: {data}")
            return
        
        # Store notification in database for record keeping
        async with AsyncSessionLocal() as db:
            db_notification = Notification(
                type="low_stock",
                channel="email",  # Add required field
                recipient_id="admin",  # Add required field
                subject=f"Low Stock Alert: {product_name}",
                content=f"Product '{product_name}' is running low on stock. Current quantity: {current_quantity}, Threshold: {threshold}",
                data=data,
                status="pending"
            )
            db.add(db_notification)
            await db.commit()
            await db.refresh(db_notification)
            
            notification_id = db_notification.id
        
        # Send email to admin
        if settings.ADMIN_EMAIL:
            # Prepare email content
            html_content = f"""
            <h2>🚨 Low Stock Alert</h2>
            <p>Product <strong>{product_name}</strong> is running low on stock and needs immediate attention.</p>
            
            <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #dc3545; margin: 15px 0;">
                <h3>Stock Details:</h3>
                <ul style="margin: 0; padding-left: 20px;">
                    <li><strong>Product ID:</strong> {product_id}</li>
                    <li><strong>Product Name:</strong> {product_name}</li>
                    <li><strong>Current Quantity:</strong> <span style="color: #dc3545; font-weight: bold;">{current_quantity}</span></li>
                    <li><strong>Reorder Threshold:</strong> {threshold}</li>
                    <li><strong>Stock Status:</strong> <span style="color: #dc3545;">Below Threshold</span></li>
                </ul>
            </div>

            <p><strong>Action Required:</strong> Please replenish the inventory as soon as possible to avoid stockouts.</p>
            """
            
            # Send email
            success = await email_provider.send_email(
                to_email=settings.ADMIN_EMAIL,
                subject=f"🚨 Low Stock Alert: {product_name}",
                html_content=html_content
            )
            
            # Update notification status
            async with AsyncSessionLocal() as db:
                notification = await db.get(Notification, notification_id)
                if success:
                    notification.status = "sent"
                    notification.sent_at = datetime.utcnow()
                    logger.info(f"Sent low stock email notification to admin for product {product_id}")
                else:
                    notification.status = "failed"
                    notification.error_message = "Failed to send email"
                    logger.error(f"Failed to send low stock email notification to admin for product {product_id}")
                
                notification.updated_at = datetime.utcnow()
                await db.commit()
        else:
            logger.warning("Admin email not configured. Cannot send low stock notification email.")
        
        logger.info(f"Processed low stock notification for product {product_id}")

# Create a singleton instance
notification_processor = NotificationProcessor()