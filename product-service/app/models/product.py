from typing import List, Optional
from bson import ObjectId
from pydantic import BaseModel, Field, validator


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic models."""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class ProductBase(BaseModel):
    """Base Product model with common fields."""
    name: str
    description: str
    category: str
    price: float
    quantity: int
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Smartphone X",
                "description": "Latest model with high-end camera",
                "category": "Electronics",
                "price": 699.99,
                "quantity": 50
            }
        }


class ProductCreate(ProductBase):
    """Model for creating a new product."""
    pass


class ProductResponse(ProductBase):
    """Model for product response including ID."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ProductUpdate(BaseModel):
    """Model for partial updates to a product."""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Smartphone X Pro",
                "price": 799.99,
            }
        }