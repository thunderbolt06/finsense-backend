"""File upload and management router."""
import uuid

from fastapi import APIRouter, Body, HTTPException

from db.models import File
from features.files.db_files import (
    create_file,
    delete_file,
    find_file_by_id,
    update_file_last_accessed_at,
    update_file_status,
)
from features.files.file_types import PresignedFileUploadRequest
from features.files.files_validation import validate_filename, validate_presigned_file_request
from features.files.s3 import generate_download_url, generate_upload_url
from utils.logging import logger

router = APIRouter(prefix="/api")


@router.post("/get_upload_url")
async def get_upload_url(
    file_metadata: PresignedFileUploadRequest = Body(..., embed=True),
):
    """
    Generate a presigned S3 URL for direct upload from the client.
    Accepts a JSON body: {"id": ..., "filename": ..., "content_type": ..., "size": ...}
    """
    filename = file_metadata.filename
    content_type = file_metadata.content_type

    validate_presigned_file_request(file_metadata)
    file_key = f"files/{file_metadata.id}/{filename}"
    
    try:
        upload_url = await generate_upload_url(
            file_id=str(file_metadata.id), s3_key=file_key, content_type=content_type
        )
        
        file_obj = await create_file(
            file_id=str(file_metadata.id),
            filename=filename,
            content_type=content_type,
            size=file_metadata.size,
            file_key=file_key,
            width=file_metadata.width,
            height=file_metadata.height,
            entity=file_metadata.entity,
            entity_id=file_metadata.entity_id,
        )
        
        return {
            "id": str(file_obj.id),
            "status": "success",
            "url": upload_url,
            "content_type": file_obj.content_type,
            "filename": file_obj.filename,
            "fileKey": file_obj.file_key,
            "entity": file_obj.entity,
            "entityId": file_obj.entity_id,
            "width": file_obj.width,
            "height": file_obj.height,
        }
    except Exception as e:
        logger.error(
            f"Error generating presigned S3 URL for {filename} file type {content_type} size {file_metadata.size}: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Failed to generate presigned URL: {e}",
                "filename": filename,
                "content_type": content_type,
            },
        )


@router.get("/files/{file_id}")
async def get_download_url(file_id: str):
    """
    Get download URL for a file by ID.
    Returns JSON with URL and file metadata.
    """
    try:
        file_obj = await find_file_by_id(file_id)
        await update_file_last_accessed_at(file_id)
    except ValueError as e:
        logger.error(f"Error fetching file with id {file_id}: {e}")
        raise HTTPException(status_code=404, detail={"message": f"File not found: {file_id}"})
    
    try:
        s3_url = await generate_download_url(file_id=file_id, file_key=file_obj.file_key)
        return {
            "url": s3_url,
            "content_type": file_obj.content_type,
            "filename": file_obj.filename,
            "id": str(file_obj.id),
            "size": file_obj.size,
            "width": file_obj.width,
            "height": file_obj.height,
            "entity": file_obj.entity,
            "entityId": file_obj.entity_id,
        }
    except Exception as e:
        logger.error(
            f"Error generating download URL for {file_obj.filename} file type {file_obj.content_type} size {file_obj.size}: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Failed to generate download URL: {e}",
                "filename": file_obj.filename,
                "content_type": file_obj.content_type,
            },
        )


@router.post("/finalize_upload/{file_id}")
async def finalize_upload(file_id: str):
    """Mark a file upload as complete."""
    try:
        file_obj = await update_file_status(file_id, File.FileStatus.SUCCESS)
        return {
            "status": "success",
            "id": str(file_obj.id),
            "filename": file_obj.filename,
            "content_type": file_obj.content_type,
            "size": file_obj.size,
            "width": file_obj.width,
            "height": file_obj.height,
            "entity": file_obj.entity,
            "entityId": file_obj.entity_id,
        }
    except ValueError as e:
        logger.error(f"Error finalizing file upload for {file_id}: {e}")
        raise HTTPException(status_code=404, detail={"message": f"File not found or could not be updated: {file_id}"})


@router.delete("/files/{file_id}")
async def delete_file_route(file_id: str):
    """Delete a file."""
    try:
        await delete_file(file_id)
        logger.info(f"File {file_id} deleted")
        return {"detail": "File deleted"}
    except ValueError as e:
        logger.error(f"File {file_id} not found")
        raise HTTPException(status_code=404, detail={"user_error_message": str(e)})
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {e}")
        raise HTTPException(status_code=500, detail={"user_error_message": "Failed to delete file"})

