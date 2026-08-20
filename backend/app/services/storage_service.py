"""Storage service — S3-compatible abstraction for MinIO (local) and R2 (production)."""

import logging
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import get_settings
from app.utils.exceptions import StorageError

logger = logging.getLogger(__name__)
settings = get_settings()


def get_boto3_client() -> Any:
    """Creates and returns an S3-compatible boto3 client."""
    # We use signature version s3v4 which is required by R2 and MinIO
    boto_config = Config(
        region_name=settings.storage_region,
        signature_version="s3v4",
        retries={"max_attempts": 3, "mode": "standard"},
    )
    
    return boto3.client(
        "s3",
        endpoint_url=settings.storage_endpoint,
        aws_access_key_id=settings.storage_access_key,
        aws_secret_access_key=settings.storage_secret_key,
        config=boto_config,
    )


def ensure_bucket_exists() -> None:
    """Creates the bucket if it does not already exist."""
    s3 = get_boto3_client()
    try:
        s3.head_bucket(Bucket=settings.storage_bucket)
        logger.info(f"Bucket '{settings.storage_bucket}' already exists.")
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "404":
            logger.info(f"Bucket '{settings.storage_bucket}' not found. Creating...")
            try:
                s3.create_bucket(Bucket=settings.storage_bucket)
                logger.info(f"Bucket '{settings.storage_bucket}' created successfully.")
            except ClientError as create_error:
                logger.error(f"Failed to create bucket: {create_error}")
                raise StorageError(f"Failed to create bucket: {create_error}")
        else:
            logger.error(f"Failed to check bucket: {e}")
            raise StorageError(f"Failed to check bucket: {e}")


def generate_presigned_upload_url(
    key: str, 
    content_type: str, 
    expires_in: int = settings.presign_expiry_seconds
) -> str:
    """Generate a presigned URL for direct browser uploads.
    
    Args:
        key: The object key (path) in the bucket.
        content_type: Expected MIME type of the upload.
        expires_in: Expiration time in seconds.
        
    Returns:
        The presigned URL string.
    """
    s3 = get_boto3_client()
    try:
        url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": settings.storage_bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in,
        )
        return url
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL for {key}: {e}")
        raise StorageError("Could not generate upload URL.")


def check_object_exists(key: str) -> bool:
    """Check if an object exists in storage."""
    s3 = get_boto3_client()
    try:
        s3.head_object(Bucket=settings.storage_bucket, Key=key)
        return True
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "404":
            return False
        logger.error(f"Failed to check object {key}: {e}")
        raise StorageError("Failed to verify object existence.")


def get_object_metadata(key: str) -> dict[str, Any] | None:
    """Get metadata for an object.
    
    Returns:
        Dict containing ContentLength, ContentType, etc.
        None if object does not exist.
    """
    s3 = get_boto3_client()
    try:
        response = s3.head_object(Bucket=settings.storage_bucket, Key=key)
        return response
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "404":
            return None
        logger.error(f"Failed to get metadata for {key}: {e}")
        raise StorageError("Failed to retrieve object metadata.")


def delete_object(key: str) -> None:
    """Delete a single object from storage."""
    s3 = get_boto3_client()
    try:
        s3.delete_object(Bucket=settings.storage_bucket, Key=key)
    except ClientError as e:
        logger.error(f"Failed to delete object {key}: {e}")
        raise StorageError("Failed to delete object.")


def delete_objects(keys: list[str]) -> None:
    """Batch delete multiple objects from storage.
    
    S3 delete_objects takes a max of 1000 keys per request.
    """
    if not keys:
        return
        
    s3 = get_boto3_client()
    
    # Chunk keys into batches of 1000
    chunk_size = 1000
    for i in range(0, len(keys), chunk_size):
        chunk = keys[i:i + chunk_size]
        objects = [{"Key": key} for key in chunk]
        
        try:
            s3.delete_objects(
                Bucket=settings.storage_bucket,
                Delete={"Objects": objects, "Quiet": True}
            )
        except ClientError as e:
            logger.error(f"Failed to batch delete objects: {e}")
            raise StorageError("Failed to batch delete objects.")
