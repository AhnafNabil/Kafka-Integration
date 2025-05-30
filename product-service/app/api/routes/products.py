from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument
from typing import List, Optional, Dict, Any
import logging

from app.models.product import ProductCreate, ProductResponse, ProductUpdate, PyObjectId
from app.api.dependencies import get_current_user, get_db
from app.services.kafka_producer import product_event_producer

# Configure logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/products", tags=["products"])


@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(
    product: ProductCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new product and publish event to Kafka for inventory creation.
    """
    product_dict = product.dict()
    
    # Create product in MongoDB
    result = await db["products"].insert_one(product_dict)
    created_product = await db["products"].find_one({"_id": result.inserted_id})
    
    product_id = str(result.inserted_id)
    logger.info(f"Created product: {product_id}")
    
    # Publish product created event to Kafka (async, non-blocking)
    try:
        event_published = await product_event_producer.publish_product_created(
            product_id=product_id,
            name=product.name,
            description=product.description,
            category=product.category,
            price=product.price,
            initial_quantity=product.quantity,
            reorder_threshold=max(5, int(product.quantity * 0.1))
        )
        
        if event_published:
            logger.info(f"Product created event published successfully for product {product_id}")
        else:
            logger.warning(f"Failed to publish product created event for product {product_id}")
            # Note: We don't fail the request even if event publishing fails
            # This ensures the product creation is not blocked by messaging issues
    
    except Exception as e:
        logger.error(f"Error publishing product created event for product {product_id}: {str(e)}")
        # Continue with successful response even if event publishing fails
    
    return created_product


@router.get("/", response_model=List[ProductResponse])
async def get_products(
    skip: int = Query(0, ge=0, description="Number of products to skip"),
    limit: int = Query(100, ge=1, le=100, description="Max number of products to return"),
    category: Optional[str] = Query(None, description="Filter by category"),
    name: Optional[str] = Query(None, description="Search by name (case insensitive)"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price filter"),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get all products with optional filtering.
    """
    query = {}
    if category:
        query["category"] = category
    if name:
        query["name"] = {"$regex": name, "$options": "i"}  # Case insensitive search
    if min_price is not None or max_price is not None:
        query["price"] = {}
        if min_price is not None:
            query["price"]["$gte"] = min_price
        if max_price is not None:
            query["price"]["$lte"] = max_price
    
    cursor = db["products"].find(query).skip(skip).limit(limit)
    products = await cursor.to_list(length=limit)
    
    return products


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str = Path(..., description="The ID of the product to retrieve"),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get a single product by ID.
    """
    try:
        product_obj_id = PyObjectId(product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product ID format")
    
    product = await db["products"].find_one({"_id": product_obj_id})
    if product:
        return product
    
    raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product: ProductUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update a product by ID and publish update event to Kafka.
    """
    try:
        product_obj_id = PyObjectId(product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product ID format")
    
    update_data = {k: v for k, v in product.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updated_product = await db["products"].find_one_and_update(
        {"_id": product_obj_id},
        {"$set": update_data},
        return_document=ReturnDocument.AFTER
    )
    
    if updated_product:
        logger.info(f"Updated product: {product_id}")
        
        # Publish product updated event to Kafka (async, non-blocking)
        try:
            event_published = await product_event_producer.publish_product_updated(
                product_id=product_id,
                name=product.name,
                description=product.description,
                category=product.category,
                price=product.price,
                quantity=product.quantity
            )
            
            if event_published:
                logger.info(f"Product updated event published successfully for product {product_id}")
            else:
                logger.warning(f"Failed to publish product updated event for product {product_id}")
        
        except Exception as e:
            logger.error(f"Error publishing product updated event for product {product_id}: {str(e)}")
        
        return updated_product
    
    raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a product by ID.
    """
    try:
        product_obj_id = PyObjectId(product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product ID format")
    
    result = await db["products"].delete_one({"_id": product_obj_id})
    if result.deleted_count:
        logger.info(f"Deleted product: {product_id}")
        return None
    
    raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")


@router.get("/category/list", response_model=List[str])
async def get_categories(db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Get all unique product categories.
    """
    categories = await db["products"].distinct("category")
    return categories