"""
POST /api/index — Upload document and ingest directly into Kendra GenAI Index.

Flow:
  1. Receive multipart form: file (PDF/TXT/HTML/CSV/MD) + optional metadata (JSON string)
  2. Read file content as bytes
  3. Call BedrockKBService.ingest_document() → inline upload to KB
  4. Return IndexResponse with document name

No temp file or S3 needed — documents are sent inline via
ingest_knowledge_base_documents API.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.bedrock_service import BedrockServiceError, get_bedrock_service
from app.models.schemas import IndexResponse, IndexResult

logger = logging.getLogger(__name__)
router = APIRouter()

# Supported file types for Kendra GenAI Index
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".html", ".csv", ".md"}


@router.post(
    "/api/index",
    response_model=IndexResponse,
    summary="Upload and index a document",
    description="Upload a document to the Bedrock Knowledge Base. Supported: PDF, TXT, HTML, CSV, MD.",
    tags=["Documents"],
)
async def index_document(
    file: UploadFile = File(..., description="Document file to upload and index"),
    metadata: Optional[str] = Form(default=None, description="Optional JSON metadata string"),
):
    """Upload a document and ingest directly into the Knowledge Base."""

    # ── Validate file ────────────────────────────────────────────
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    # ── Parse metadata ───────────────────────────────────────────
    meta_dict = {}
    if metadata:
        try:
            meta_dict = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid metadata JSON string",
            )

    # ── Read content and ingest ──────────────────────────────────
    try:
        content = await file.read()

        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        logger.info(
            "Uploading document: %s (%d bytes, metadata=%s)",
            file.filename, len(content), meta_dict,
        )

        # Ingest directly via Bedrock KB (inline upload, no S3)
        service = get_bedrock_service()
        result = await service.ingest_document(
            file_content=content,
            file_name=file.filename,
            metadata=meta_dict if meta_dict else None,
        )

        return IndexResponse(
            message="Document indexed successfully",
            result=IndexResult(
                done=result.get("done", True),
                documentName=result.get("documentName", ""),
            ),
        )

    except BedrockServiceError as e:
        logger.error("Ingestion error: %s", e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is

    except Exception as e:
        logger.exception("Unexpected error during document indexing")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
