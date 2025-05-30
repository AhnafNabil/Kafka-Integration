import logging
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings

logger = logging.getLogger(__name__)

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

mongodb = MongoDB()

async def connect_to_mongo():
    """Create database connection."""
    logger.info("Connecting to MongoDB...")
    mongodb.client = AsyncIOMotorClient(settings.MONGODB_URI)
    mongodb.db = mongodb.client[settings.MONGODB_DB]
    
    # Create indexes
    await mongodb.db["products"].create_index("name")
    await mongodb.db["products"].create_index("category")
    
    logger.info("Connected to MongoDB!")


async def close_mongo_connection():
    """Close database connection."""
    logger.info("Closing MongoDB connection...")
    if mongodb.client:
        mongodb.client.close()
    logger.info("MongoDB connection closed.")


def get_database():
    """Return database instance."""
    return mongodb.db