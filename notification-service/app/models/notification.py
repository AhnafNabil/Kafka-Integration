# notification-service/app/models/notification.py
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text
from sqlalchemy.sql import func
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from app.db.postgresql import Base


# SQLAlchemy Models
class Notification(Base):
    """Database model for notifications."""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)  # "low_stock", etc.
    channel = Column(String, nullable=False, default="email")  # Add this field
    
    # Recipients
    recipient_id = Column(String, nullable=True)  # Add this field
    
    # Content
    subject = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    
    # Delivery status
    status = Column(String, nullable=False, default="pending")  # "pending", "sent", "failed"
    error_message = Column(String, nullable=True)
    
    # Data used to generate the notification
    data = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)


# Pydantic Models for API
class NotificationBase(BaseModel):
    """Base model for notifications."""
    type: str
    channel: str = "email"  # Add this field
    recipient_id: Optional[str] = None  # Add this field
    subject: Optional[str] = None
    content: str
    data: Optional[Dict[str, Any]] = None


class NotificationCreate(NotificationBase):
    """Model for creating a notification."""
    pass


class NotificationResponse(NotificationBase):
    """Model for notification response."""
    id: int
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    sent_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True