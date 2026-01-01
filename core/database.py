from pymongo import MongoClient
import certifi
import logging
from core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    logger.info("Connecting to MongoDB...")
    client = MongoClient(settings.MONGO_URI, tlsCAFile=certifi.where())
    db = client[settings.MONGO_DB_NAME]
    assets_collection = db["assets"]
    users_collection = db["users"]
    logger.info("Successfully connected to MongoDB.")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    # Initialize as None to prevent import errors
    client = None
    db = None
    assets_collection = None
    users_collection = None

def check_db_connection():
    from fastapi import HTTPException
    if db is None:
        raise HTTPException(status_code=503, detail="Database Unavailable")

