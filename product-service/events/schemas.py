# events/schemas.py
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid


class EventMetadata(BaseModel):
    """Common metadata for all events"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str
    version: str = "1.0"
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None


class ProductCreatedEventData(BaseModel):
    """Data payload for product created event"""
    product_id: str
    name: str
    description: str
    category: str
    price: float
    initial_quantity: int
    reorder_threshold: Optional[int] = None


class ProductCreatedEvent(BaseModel):
    """Product created event schema"""
    metadata: EventMetadata
    data: ProductCreatedEventData
    
    def __init__(self, **data):
        if 'metadata' not in data:
            data['metadata'] = EventMetadata(
                event_type="product.created",
                source="product-service"
            )
        super().__init__(**data)


class InventoryCreatedEventData(BaseModel):
    """Data payload for inventory created event"""
    product_id: str
    inventory_id: int
    available_quantity: int
    reserved_quantity: int = 0
    reorder_threshold: int
    status: str = "created"


class InventoryCreatedEvent(BaseModel):
    """Inventory created event schema"""
    metadata: EventMetadata
    data: InventoryCreatedEventData
    
    def __init__(self, **data):
        if 'metadata' not in data:
            data['metadata'] = EventMetadata(
                event_type="inventory.created",
                source="inventory-service"
            )
        super().__init__(**data)


class ProductUpdatedEventData(BaseModel):
    """Data payload for product updated event"""
    product_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None


class ProductUpdatedEvent(BaseModel):
    """Product updated event schema"""
    metadata: EventMetadata
    data: ProductUpdatedEventData
    
    def __init__(self, **data):
        if 'metadata' not in data:
            data['metadata'] = EventMetadata(
                event_type="product.updated",
                source="product-service"
            )
        super().__init__(**data)