# notification-service/app/api/routes/notifications.py
import logging
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.models.notification import Notification, NotificationResponse
from app.db.postgresql import get_db
from app.api.dependencies import get_current_user

# Configure logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    skip: int = Query(0, ge=0, description="Number of notifications to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max number of notifications to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
    type: Optional[str] = Query(None, description="Filter by notification type"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get all notifications with optional filtering.
    """
    # Build query
    query = select(Notification)
    
    if status:
        query = query.where(Notification.status == status)
    
    if type:
        query = query.where(Notification.type == type)
    
    # Add ordering and pagination
    query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    notifications = result.scalars().all()
    
    return notifications


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: int = Path(..., description="The notification ID"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get a specific notification by ID.
    """
    result = await db.execute(select(Notification).where(Notification.id == notification_id))
    notification = result.scalars().first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification with ID {notification_id} not found"
        )
    
    return notification


@router.post("/test", response_model=Dict[str, Any])
async def send_test_notification(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Send a test notification to the admin email.
    """
    from app.services.email_provider import email_provider
    from app.core.config import settings
    
    if not settings.ADMIN_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin email not configured"
        )
    
    # Create a test notification with the required fields
    test_notification = Notification(
        type="test",
        channel="email",  # Add this required field
        recipient_id="admin",  # Add this field
        subject="Test Notification",
        content="This is a test notification to verify email delivery.",
        status="pending",
        data={"test": True}
    )
    
    db.add(test_notification)
    await db.commit()
    await db.refresh(test_notification)
    
    # Send test email
    success = await email_provider.send_email(
        to_email=settings.ADMIN_EMAIL,
        subject="Test Notification",
        html_content="<h1>Test Notification</h1><p>This is a test notification to verify email delivery.</p>"
    )
    
    if success:
        test_notification.status = "sent"
        test_notification.sent_at = datetime.utcnow()
    else:
        test_notification.status = "failed"
        test_notification.error_message = "Failed to send email"
    
    test_notification.updated_at = datetime.utcnow()
    await db.commit()
    
    return {
        "message": "Test notification created", 
        "notification_id": test_notification.id,
        "email_sent": success,
        "admin_email": settings.ADMIN_EMAIL
    }