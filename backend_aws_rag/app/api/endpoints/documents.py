"""
GET  /api/documents             — List all documents in the Knowledge Base (paginated)
POST /api/documents/delete      — Delete a document by ID (with soft-delete)
POST /api/documents/delete_all  — Delete ALL documents from the Knowledge Base

All operations call BedrockKBService and return frontend-compatible JSON.

v1.1: Added pagination query params (page, size) and is_active field mapping.
v1.2: Added bulk delete_all endpoint.
"""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.core.bedrock_service import BedrockServiceError, get_bedrock_service
from app.models.schemas import (
    DeleteAllResponse,
    DeleteRequest,
    DeleteResponse,
    DocumentItem,
    DocumentMetadataItem,
    DocumentsResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/api/documents",
    response_model=DocumentsResponse,
    summary="List all indexed documents (paginated)",
    description=(
        "Returns documents currently indexed in the Bedrock Knowledge Base (Kendra). "
        "Supports pagination via `page` and `size` query parameters. "
        "Soft-deleted documents (is_active=false) are excluded."
    ),
    tags=["Documents"],
)
async def list_documents(
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    size: int = Query(default=10, ge=1, le=100, description="Items per page (max 100)"),
):
    """
    List all documents in the Knowledge Base with pagination.
    
    Verification scenario (from plan_R1):
      1. Upload 12 PDFs
      2. GET /api/documents?page=1&size=10 → expect 10 items
      3. GET /api/documents?page=2&size=10 → expect 2 items
      4. Delete one PDF → search should return zero results for it
    """
    try:
        service = get_bedrock_service()
        docs, total, page_num, total_pages = await service.list_documents(
            page_number=page,
            page_size=size,
        )

        # Transform into Pydantic models
        document_items = []
        for doc in docs:
            metadata_items = [
                DocumentMetadataItem(key=m["key"], value=m["value"])
                for m in doc.get("metadata", [])
            ]
            document_items.append(
                DocumentItem(
                    name=doc["name"],
                    displayName=doc["displayName"],
                    state=doc.get("state", "ACTIVE"),
                    is_active=doc.get("is_active", True),
                    metadata=metadata_items,
                )
            )

        return DocumentsResponse(
            documents=document_items,
            total=total,
            page=page_num,
            total_pages=total_pages,
            page_size=size,
        )

    except BedrockServiceError as e:
        logger.error("List documents error: %s", e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except Exception as e:
        logger.exception("Unexpected error listing documents")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post(
    "/api/documents/delete",
    response_model=DeleteResponse,
    summary="Delete a document from the Knowledge Base",
    description="Delete a specific document by its identifier.",
    tags=["Documents"],
)
async def delete_document(request: DeleteRequest):
    """Delete a document from the Knowledge Base by ID."""
    if not request.documentId or not request.documentId.strip():
        raise HTTPException(status_code=400, detail="documentId is required")

    try:
        service = get_bedrock_service()
        await service.delete_document(request.documentId)

        logger.info("Document deleted: %s", request.documentId)
        return DeleteResponse(message="Document deleted successfully")

    except BedrockServiceError as e:
        logger.error("Delete document error: %s", e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except Exception as e:
        logger.exception("Unexpected error deleting document")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post(
    "/api/documents/delete_all",
    response_model=DeleteAllResponse,
    summary="Delete ALL documents from the Knowledge Base",
    description=(
        "Bulk-deletes every document in the Kendra index. "
        "Internally paginates to collect all document IDs, soft-deletes each "
        "(if ENABLE_SOFT_DELETE is true), then hard-deletes in batches of 10. "
        "Returns a summary with deleted_count and any failed IDs."
    ),
    tags=["Documents"],
)
async def delete_all_documents():
    """
    Delete all documents from the Knowledge Base.
    
    No request body needed. Returns a summary of the bulk deletion
    including counts and any failed document IDs.
    
    WARNING: This is a destructive operation. All documents will be
    permanently removed from the Knowledge Base.
    """
    try:
        service = get_bedrock_service()
        result = await service.delete_all_documents()

        deleted = result.get("deleted_count", 0)
        failed = result.get("failed_count", 0)
        failed_ids = result.get("failed_ids", [])

        if failed > 0:
            msg = f"Deleted {deleted} documents. {failed} failed."
        else:
            msg = f"All {deleted} documents deleted successfully."

        logger.info("Bulk delete complete: %d deleted, %d failed", deleted, failed)

        return DeleteAllResponse(
            message=msg,
            deleted_count=deleted,
            failed_count=failed,
            failed_ids=failed_ids,
        )

    except BedrockServiceError as e:
        logger.error("Bulk delete error: %s", e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except Exception as e:
        logger.exception("Unexpected error during bulk delete")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
