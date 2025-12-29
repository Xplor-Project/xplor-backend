from uuid import uuid4
from fastapi import HTTPException
from core.aws_client import s3
from core.config import settings
import logging

logger = logging.getLogger(__name__)


def check_s3_connection():
    if s3 is None:
        logger.error("AWS S3 client is not available.")
        raise HTTPException(status_code=503, detail="Storage service unavailable")


def upload_to_s3(file, folder: str, content_type: str):
    """
    Uploads a file to S3 and returns:
    (file_id, file_key, file_url)
    """
    check_s3_connection()

    try:
        file.file.seek(0)  # Ensure reading from beginning
        file_id = str(uuid4())
        file_key = f"{folder}/{file_id}_{file.filename}"

        logger.info(
            f"Uploading {file.filename} to "
            f"{settings.S3_BUCKET}/{file_key}"
        )

        s3.upload_fileobj(
            file.file,
            settings.S3_BUCKET,
            file_key,
            ExtraArgs={"ContentType": content_type},
        )

        file_url = (
            f"https://{settings.S3_BUCKET}.s3."
            f"{settings.AWS_REGION}.amazonaws.com/{file_key}"
        )

        return file_id, file_key, file_url

    except Exception as e:
        logger.error(f"S3 Upload Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"S3 upload failed: {str(e)}"
        )


def delete_from_s3(file_key: str):
    """Deletes an object from S3."""
    check_s3_connection()

    try:
        s3.delete_object(
            Bucket=settings.S3_BUCKET,
            Key=file_key
        )
    except Exception as e:
        logger.error(f"S3 Delete Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"S3 delete failed: {str(e)}"
        )
