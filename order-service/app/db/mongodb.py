import logging
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("order-service")


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
    await mongodb.db["orders"].create_index("user_id")
    await mongodb.db["orders"].create_index("status")
    await mongodb.db["orders"].create_index("created_at")
    
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