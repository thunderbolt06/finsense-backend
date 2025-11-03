"""Database operations for files."""
import asyncio

from django.utils import timezone

from db.models import File
from finsense.settings import settings
from utils.logging import logger


async def find_file_by_id(file_id: str) -> File:
    """Find a file by ID."""
    try:
        file_obj = await File.objects.aget(id=file_id)
        return file_obj
    except File.DoesNotExist:
        logger.error(f"File not found: {file_id}")
        raise ValueError("File not found")


async def create_file(
    filename: str,
    content_type: str,
    size: int,
    file_key: str,
    file_id: str | None = None,
    width: int | None = None,
    height: int | None = None,
    entity: str | None = None,
    entity_id: str | None = None,
) -> File:
    """Create a new file record."""
    try:
        file_obj = await File.objects.acreate(
            id=file_id,
            filename=filename,
            content_type=content_type,
            size=size,
            file_key=file_key,
            width=width,
            height=height,
            entity=entity,
            entity_id=entity_id,
            status=File.FileStatus.PENDING,
        )
        return file_obj
    except Exception as e:
        logger.error(f"Error creating file record: {e}")
        raise


async def update_file_last_accessed_at(file_id: str) -> None:
    """Update the last accessed timestamp for a file."""
    await File.objects.filter(id=file_id).aupdate(last_accessed_at=timezone.now())


async def update_file_status(file_id: str, status: str) -> File:
    """Update file status."""
    await File.objects.filter(id=file_id).aupdate(status=status)
    return await File.objects.aget(id=file_id)


async def delete_file(file_id: str) -> None:
    """Soft delete a file."""
    try:
        file_obj = await File.objects.aget(id=file_id)
        
        # Delete from S3 if configured
        from features.files.s3 import delete_file as s3_delete_file
        try:
            await s3_delete_file(file_id, file_obj.file_key)
        except Exception as e:
            logger.warning(f"Failed to delete file from S3: {e}")
        
        # Soft delete in database
        await File.objects.filter(id=file_id).aupdate(
            deleted_at=timezone.now(),
            status=File.FileStatus.PENDING,
        )
        logger.info(f"File {file_id} deleted")
    except File.DoesNotExist:
        logger.error(f"File not found: {file_id}")
        raise ValueError("File not found")
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {e}")
        raise

