from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

from app.db.postgresql import Base
from app.core.config import settings


# SQLAlchemy Models
class InventoryItem(Base):
    """Database model for inventory items."""
    __tablename__ = "inventory_items"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String, unique=True, index=True, nullable=False)
    available_quantity = Column(Integer, nullable=False, default=0)
    reserved_quantity = Column(Integer, nullable=False, default=0)
    reorder_threshold = Column(Integer, nullable=False, default=settings.LOW_STOCK_THRESHOLD)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Ensure quantities are not negative
    __table_args__ = (
        CheckConstraint('available_quantity >= 0', name='check_available_quantity_positive'),
        CheckConstraint('reserved_quantity >= 0', name='check_reserved_quantity_positive'),
    )


class InventoryHistory(Base):
    """Database model for inventory history tracking."""
    __tablename__ = "inventory_history"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String, index=True, nullable=False)
    quantity_change = Column(Integer, nullable=False)
    previous_quantity = Column(Integer, nullable=False)
    new_quantity = Column(Integer, nullable=False)
    change_type = Column(String, nullable=False)  # "add", "remove", "reserve", "release"
    reference_id = Column(String, nullable=True)  # Order ID or other reference
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


# Pydantic Models for API
class InventoryItemBase(BaseModel):
    """Base model for inventory items."""
    product_id: str
    available_quantity: int = Field(..., ge=0)
    reserved_quantity: int = Field(..., ge=0)
    reorder_threshold: int = Field(..., ge=0)


class InventoryItemCreate(InventoryItemBase):
    """Model for creating a new inventory item."""
    pass


class InventoryItemUpdate(BaseModel):
    """Model for updating an inventory item."""
    available_quantity: Optional[int] = Field(None, ge=0)
    reserved_quantity: Optional[int] = Field(None, ge=0)
    reorder_threshold: Optional[int] = Field(None, ge=0)


class InventoryItemResponse(InventoryItemBase):
    """Model for inventory item response including ID."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


class InventoryCheck(BaseModel):
    """Model for checking inventory availability."""
    product_id: str
    quantity: int = Field(..., gt=0)


class InventoryReserve(BaseModel):
    """Model for reserving inventory."""
    product_id: str
    quantity: int = Field(..., gt=0)
    order_id: Optional[str] = None
    
    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError("Quantity must be greater than 0")
        return v


class InventoryRelease(BaseModel):
    """Model for releasing inventory."""
    product_id: str
    quantity: int = Field(..., gt=0)
    order_id: Optional[str] = None
    
    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError("Quantity must be greater than 0")
        return v


class InventoryAdjust(BaseModel):
    """Model for adjusting inventory levels."""
    product_id: str
    quantity_change: int  # Can be positive (add) or negative (remove)
    reason: str = Field(..., min_length=3, max_length=200)
    reference_id: Optional[str] = None