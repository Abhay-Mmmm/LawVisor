"""
LawVisor Upload API
===================
Handles document upload, validation, and storage.
"""

import hashlib
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

import aiofiles
from fastapi import APIRouter, File, HTTPException, UploadFile, status

from core.config import get_settings
from schemas import AnalysisStatusEnum, ErrorResponse, UploadResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/upload", tags=["Upload"])
settings = get_settings()

# In-memory document store (replace with database in production)
# Stores document metadata and processing status
DOCUMENT_STORE: dict[str, dict] = {}


def generate_document_id() -> str:
    """Generate a unique document ID."""
    unique_id = uuid.uuid4().hex[:12]
    return f"doc-{unique_id}"


def validate_file(file: UploadFile) -> None:
    """
    Validate uploaded file.
    
    Checks:
    - File type is PDF
    - File size is within limits
    
    Raises:
        HTTPException: If validation fails
    """
    # Check content type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "error": "UnsupportedMediaType",
                "message": "Only PDF files are accepted.",
                "details": {
                    "received_type": file.content_type,
                    "accepted_types": ["application/pdf"]
                }
            }
        )
    
    # Check filename
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "InvalidFilename",
                "message": "File must have a .pdf extension.",
                "details": {"filename": file.filename}
            }
        )


async def save_file(file: UploadFile, document_id: str) -> tuple[Path, int]:
    """
    Save uploaded file to disk.
    
    Args:
        file: Uploaded file
        document_id: Unique document identifier
        
    Returns:
        Tuple of (file_path, file_size_bytes)
    """
    # Ensure upload directory exists
    upload_dir = settings.upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Create unique filename
    safe_filename = f"{document_id}.pdf"
    file_path = upload_dir / safe_filename
    
    # Stream file to disk
    file_size = 0
    async with aiofiles.open(file_path, 'wb') as out_file:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            file_size += len(chunk)
            
            # Check file size limit
            if file_size > settings.max_file_size_bytes:
                # Clean up partial file
                file_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail={
                        "error": "FileTooLarge",
                        "message": f"File exceeds maximum size of {settings.max_file_size_mb}MB.",
                        "details": {
                            "max_size_mb": settings.max_file_size_mb,
                            "received_bytes": file_size
                        }
                    }
                )
            
            await out_file.write(chunk)
    
    return file_path, file_size


@router.post(
    "",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        413: {"model": ErrorResponse, "description": "File too large"},
        415: {"model": ErrorResponse, "description": "Unsupported file type"},
        400: {"model": ErrorResponse, "description": "Invalid request"}
    },
    summary="Upload a legal document",
    description="""
    Upload a PDF legal document for analysis.
    
    The document will be validated and stored. Once uploaded, use the 
    returned `document_id` to initiate analysis via the `/analyze/{document_id}` endpoint.
    
    **Accepted file types:** PDF only
    **Maximum file size:** 50MB
    """
)
async def upload_document(
    file: Annotated[UploadFile, File(description="PDF document to upload")]
) -> UploadResponse:
    """
    Upload a PDF legal document for analysis.
    
    Returns a document_id that can be used for subsequent analysis.
    """
    logger.info(f"Received upload request: {file.filename}")
    
    # Validate file
    validate_file(file)
    
    # Generate document ID
    document_id = generate_document_id()
    
    # Save file
    file_path, file_size = await save_file(file, document_id)
    
    # Store document metadata
    upload_timestamp = datetime.utcnow()
    DOCUMENT_STORE[document_id] = {
        "document_id": document_id,
        "filename": file.filename,
        "file_path": str(file_path),
        "file_size_bytes": file_size,
        "upload_timestamp": upload_timestamp,
        "status": AnalysisStatusEnum.PENDING,
        "analysis_started_at": None,
        "analysis_completed_at": None,
        "risk_report": None,
        "error_message": None
    }
    
    logger.info(f"Document uploaded: {document_id} ({file_size} bytes)")
    
    return UploadResponse(
        document_id=document_id,
        filename=file.filename or "unknown.pdf",
        file_size_bytes=file_size,
        upload_timestamp=upload_timestamp,
        status=AnalysisStatusEnum.PENDING,
        message="Document uploaded successfully. Ready for analysis."
    )


@router.get(
    "/{document_id}",
    summary="Get upload status",
    description="Check the status of an uploaded document."
)
async def get_upload_status(document_id: str):
    """Get the status of an uploaded document."""
    if document_id not in DOCUMENT_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "DocumentNotFound",
                "message": f"Document with ID '{document_id}' not found.",
                "details": {"document_id": document_id}
            }
        )
    
    doc = DOCUMENT_STORE[document_id]
    return {
        "document_id": doc["document_id"],
        "filename": doc["filename"],
        "status": doc["status"],
        "upload_timestamp": doc["upload_timestamp"],
        "file_size_bytes": doc["file_size_bytes"]
    }


def get_document_store() -> dict:
    """Get the document store (for use by other modules)."""
    return DOCUMENT_STORE
