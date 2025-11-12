from uuid import uuid4
from core.aws_client import s3
from core.config import settings

def upload_to_s3(file, folder, content_type):
    """Uploads a file to S3 and returns its key and URL."""
    file_id = str(uuid4())
    file_key = f"{folder}/{file_id}_{file.filename}"

    s3.upload_fileobj(
        file.file,
        settings.S3_BUCKET,
        file_key,
        ExtraArgs={"ContentType": content_type},
    )

    file_url = f"https://{settings.S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{file_key}"
    return file_id, file_key, file_url


def delete_from_s3(file_key):
    """Deletes an object from S3."""
    s3.delete_object(Bucket=settings.S3_BUCKET, Key=file_key)
