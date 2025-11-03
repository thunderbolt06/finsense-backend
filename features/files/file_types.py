"""File upload request types."""
import uuid

from pydantic import BaseModel


class PresignedFileUploadRequest(BaseModel):
    """Request model for presigned file upload."""
    id: uuid.UUID
    filename: str
    content_type: str
    size: int
    width: int | None = None
    height: int | None = None
    entity: str | None = None
    entity_id: str | None = None

