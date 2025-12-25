import boto3
import logging
from core.config import settings

logger = logging.getLogger(__name__)

try:
    logger.info("Initializing AWS S3 client...")
    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SECRET_KEY,
        region_name=settings.AWS_REGION,
    )
    logger.info("AWS S3 client initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize AWS S3 client: {e}")
    s3 = None

