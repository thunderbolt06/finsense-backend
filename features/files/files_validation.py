"""File validation utilities."""
from pathlib import Path

from fastapi import HTTPException

from features.files.file_types import PresignedFileUploadRequest

# Common file types supported
ALLOWED_FILE_EXTENSIONS = {
    # Documents
    ".pdf", ".txt", ".docx", ".doc", ".rtf", ".odt",
    # Spreadsheets
    ".csv", ".xlsx", ".xls", ".ods",
    # Presentations
    ".pptx", ".ppt", ".odp",
    # Code/Data
    ".py", ".js", ".java", ".cpp", ".json", ".yaml", ".yml", ".sql",
    ".html", ".md", ".xml", ".jsx", ".tsx", ".vue", ".css", ".scss",
    # Images
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico",
    ".heic", ".heif",
    # Archives
    ".zip", ".tar", ".gz", ".7z",
    # Other
    ".ipynb", ".sh", ".env",
}

SORTED_EXTENSIONS = ", ".join(sorted(ALLOWED_FILE_EXTENSIONS))

# File size limits
MAX_FILE_SIZE_MB: int = 30
MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024


def validate_filename(filename: str) -> None:
    """Validate filename to prevent path traversal attacks."""
    if not filename or ".." in filename or "/" in filename or "\\" in filename or filename.startswith("."):
        raise HTTPException(status_code=400, detail={"message": "Invalid filename"})


def validate_presigned_file_request(file: PresignedFileUploadRequest) -> None:
    """
    Validate file extension and size for presigned URL requests.
    Raises HTTPException if invalid.
    """
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail={"user_error_message": f"File extension '{ext}' not allowed. Supported types: {SORTED_EXTENSIONS}"},
        )
    if file.size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail={"user_error_message": f"File '{file.filename}' exceeds maximum size limit of {MAX_FILE_SIZE_MB}MB"},
        )
    if file.size == 0:
        raise HTTPException(
            status_code=400,
            detail={"user_error_message": f"File '{file.filename}' has no content or is corrupted"},
        )

