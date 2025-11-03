"""S3 file operations."""
import base64

import aioboto3

from finsense.settings import settings
from utils.logging import logger

EXPIRATION_TIME = 600
REGION = settings.AWS_S3_REGION_NAME
DEFAULT_BUCKET = settings.AWS_STORAGE_BUCKET_NAME

# Create session if AWS credentials are configured
session = None
if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
    session = aioboto3.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=REGION,
    )


async def generate_upload_url(
    file_id: str,
    s3_key: str,
    content_type: str,
    expires_in: int = EXPIRATION_TIME,
    bucket: str | None = None,
) -> str:
    """
    Generate a presigned S3 URL for uploading a file directly to S3.
    
    Returns a local file path if S3 is not configured.
    """
    if not bucket:
        bucket = DEFAULT_BUCKET
    
    if not bucket or not session:
        # Fallback to local file path
        logger.warning("S3 not configured, using local file path fallback")
        return f"local://files/{file_id}/{s3_key}"
    
    async with session.client("s3") as s3_client:
        try:
            presigned_url = await s3_client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": bucket,
                    "Key": s3_key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )
            return presigned_url
        except Exception as e:
            logger.error(f"Storage error generating upload URL for file {file_id}: {e}")
            raise RuntimeError(f"Storage error generating upload URL: {e}") from e


async def generate_download_url(
    file_id: str,
    file_key: str,
    bucket: str | None = None,
    expires_in: int = EXPIRATION_TIME,
) -> str:
    """
    Generate a presigned S3 URL for downloading a file.
    
    Returns a local file path if S3 is not configured.
    """
    if not bucket:
        bucket = DEFAULT_BUCKET
    
    if not bucket or not session:
        # Fallback to local file path
        logger.warning("S3 not configured, using local file path fallback")
        return f"local://files/{file_id}/{file_key}"
    
    async with session.client("s3") as s3_client:
        try:
            response = await s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": file_key},
                ExpiresIn=expires_in,
            )
            return response
        except Exception as e:
            logger.error(f"Storage error generating download URL for file {file_id}: {e}")
            raise RuntimeError(f"Storage error generating download URL: {e}") from e


async def delete_file(file_id: str, s3_key: str) -> None:
    """Delete a file from S3."""
    if not DEFAULT_BUCKET or not session:
        logger.warning(f"S3 not configured, skipping delete for file {file_id}")
        return
    
    async with session.client("s3") as s3_client:
        try:
            await s3_client.delete_object(Bucket=DEFAULT_BUCKET, Key=s3_key)
        except Exception as e:
            logger.error(f"Error deleting S3 file {file_id}: {e}")
            raise RuntimeError(f"Error deleting S3 file: {e}") from e

