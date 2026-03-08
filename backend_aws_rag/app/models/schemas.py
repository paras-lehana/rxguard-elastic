"""
Pydantic schemas — request/response models for all 4 API endpoints.

These schemas enforce the EXACT JSON format that the frontend expects.
Changing field names or nesting will break the frontend.

v1.1: Added PaginationParams, is_active on DocumentItem, pagination fields on DocumentsResponse.
"""

import math
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ╔════════════════════════════════════════════════════════════════════╗
# ║  POST /api/index — Upload & Index Document                        ║
# ╚════════════════════════════════════════════════════════════════════╝

class IndexResult(BaseModel):
    """Result payload for a successful indexing operation."""
    done: bool = True
    documentName: str = Field(..., description="KB document identifier, e.g. KB-XXX/documents/YYY")


class IndexResponse(BaseModel):
    """Response from POST /api/index."""
    message: str = "Document indexed successfully"
    result: IndexResult


# ╔════════════════════════════════════════════════════════════════════╗
# ║  GET /api/documents — List Documents                               ║
# ╚════════════════════════════════════════════════════════════════════╝

class PaginationParams(BaseModel):
    """Reusable pagination parameters with validation.
    
    Use this schema to add pagination support to any listing endpoint.
    page is 1-based, size is capped at 100 to prevent excessive Kendra queries.
    """
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    size: int = Field(default=10, ge=1, le=100, description="Items per page (max 100)")


class DocumentMetadataItem(BaseModel):
    """A single metadata key-value pair on a document."""
    key: str
    value: str


class DocumentItem(BaseModel):
    """A single document in the Knowledge Base."""
    name: str = Field(..., description="Full document identifier")
    displayName: str = Field(..., description="Original filename")
    state: str = Field(default="ACTIVE", description="Document state: ACTIVE, INDEXING, etc.")
    is_active: bool = Field(default=True, description="Soft-delete flag: False means document is marked for deletion")
    metadata: List[DocumentMetadataItem] = Field(default_factory=list)


class DocumentsResponse(BaseModel):
    """Response from GET /api/documents.
    
    Includes pagination metadata so the frontend can render page controls.
    - page: current page number (1-based)
    - total_pages: total number of pages at the given page_size
    - page_size: number of items per page
    - total: total number of active documents
    """
    documents: List[DocumentItem]
    total: int
    page: int = Field(default=1, description="Current page number (1-based)")
    total_pages: int = Field(default=1, description="Total number of pages")
    page_size: int = Field(default=10, description="Items per page")


# ╔════════════════════════════════════════════════════════════════════╗
# ║  POST /api/documents/delete — Delete Document                     ║
# ╚════════════════════════════════════════════════════════════════════╝

class DeleteRequest(BaseModel):
    """Request body for document deletion."""
    documentId: str = Field(..., description="Full document ID to delete, e.g. KB-XXX/documents/YYY")


class DeleteResponse(BaseModel):
    """Response from POST /api/documents/delete."""
    message: str = "Document deleted successfully"


class DeleteAllResponse(BaseModel):
    """Response from POST /api/documents/delete_all.
    
    Returns the count of successfully deleted documents, any failures,
    and the IDs of documents that could not be deleted.
    """
    message: str = Field(default="All documents deleted successfully", description="Summary message")
    deleted_count: int = Field(default=0, description="Number of documents successfully deleted")
    failed_count: int = Field(default=0, description="Number of documents that failed to delete")
    failed_ids: List[str] = Field(default_factory=list, description="Document IDs that failed to delete")


# ╔════════════════════════════════════════════════════════════════════╗
# ║  POST /api/search — RAG Search (CRITICAL ENDPOINT)                ║
# ╚════════════════════════════════════════════════════════════════════╝

class SearchRequest(BaseModel):
    """Request body for RAG search."""
    query: str = Field(..., description="The pharmaceutical regulatory query")
    sessionId: Optional[str] = Field(default=None, description="Session ID for conversation continuity")


class SearchResultItem(BaseModel):
    """
    A single search result matching the EXACT frontend format.
    
    CRITICAL: Do NOT rename or remove any of these fields.
    The frontend parses this exact structure.
    All 29 fields match the OUTPUT_FORMAT in the new CDSCO prompt.
    """
    # ── Core identification ──────────────────────────────────────
    gazette_id: str = Field(default="N/A", description="GSR number exactly as found in documents")
    pdf_name: str = Field(default="source not identified", description="Exact source document name from metadata")
    medicine_name: str = Field(default="N/A", description="Full medicine name or FDC exactly as in document")

    # ── Ban/uplift dates ─────────────────────────────────────────
    date_of_ban: str = Field(default="N/A", description="DD MMM YYYY exactly as found in documents")
    date_of_uplift: str = Field(default="N/A", description="DD MMM YYYY if ban was lifted")

    # ── Summary & reasoning ──────────────────────────────────────
    summary: str = Field(default="", description="1-2 lines summary with CDSCO/Gazette/Act references")
    reasons_for_ban: str = Field(default="N/A", description="Reasons exactly as stated in documents")
    reasons_for_uplift: str = Field(default="N/A", description="Reasons for ban withdrawal")

    # ── Classification ───────────────────────────────────────────
    drug_category: str = Field(default="N/A", description="single_drug | fdc | import_banned")
    population_restriction: str = Field(default="none", description="all | children | women | animals | none")
    schedule_classification: str = Field(default="N/A", description="Schedule H | Schedule H1 | Schedule X | Not Scheduled | N/A")
    controlled_status: str = Field(default="N/A", description="NDPS controlled | Not controlled | N/A")

    # ── Authority & legal ────────────────────────────────────────
    source_authority: str = Field(default="N/A", description="Issuing authority as stated in document")
    act_reference: str = Field(default="N/A", description="Legal act/section cited, e.g. Drugs and Cosmetics Act 1940 Section 26A")
    alternative_medicines: str = Field(default="Not specified in documents", description="Alternatives from documents")
    compliance_note: str = Field(default="", description="Penalties, transition periods from documents")

    # ── Image matching ───────────────────────────────────────────
    name_image_match: str = Field(default="N/A", description="Yes or No — does image match drug name")

    # ── Source tracking (banned) ─────────────────────────────────
    source_banned: str = Field(default="", description="file | news | gazette | internet | blank")
    source_internet: str = Field(default="", description="Few words description of internet source")

    # ── Source tracking (approved/uplift) ────────────────────────
    source_approved: str = Field(default="never banned", description="news | gazette | internet | never banned")
    source_approved_internet: str = Field(default="", description="Few words description of approval source")
    approved_gazette: str = Field(default="", description="Gazette reference for approval, e.g. GSR 91 E")

    # ── Source tracking (scheduled) ──────────────────────────────
    source_scheduled: str = Field(default="", description="file | news | gazette | internet | blank")
    source_scheduled_file: str = Field(default="", description="Exact schedule source file name")
    source_scheduled_internet: str = Field(default="", description="Few words description of schedule source")

    # ── Source tracking (controlled) ─────────────────────────────
    source_controlled: str = Field(default="", description="file | news | gazette | internet | blank")

    # ── Drug identification ──────────────────────────────────────
    keyword: str = Field(default="", description="Few word main drug name for matching")
    misc: str = Field(default="", description="NSQ, substandard quality, import banned, etc.")
    reasoning: str = Field(default="", description="Full reasoning for the classification")
    itemid: str = Field(default="N/A", description="Item ID from input file (primary key)")

    class Config:
        extra = "allow"  # Allow extra fields from Bedrock without breaking


class SearchResponse(BaseModel):
    """
    Response from POST /api/search.
    
    EXACT format that the frontend parses.
    `results` is a single object (not an array) per promp.txt spec.
    """
    query: str
    medicine_searched: str = ""
    total_results: str = "0"
    current_status: str = "unknown"
    results: Dict[str, Any] = Field(default_factory=dict, description="Single result object matching frontend format")
    text: str = Field(default="", description="Human-readable summary text")
    sessionId: Optional[str] = None


# ╔════════════════════════════════════════════════════════════════════╗
# ║  GET /health — Health Check                                        ║
# ╚════════════════════════════════════════════════════════════════════╝

# ╔════════════════════════════════════════════════════════════════════╗
# ║  POST /api/janaushadhi/search — Generic RAG (No CDSCO Prompt)      ║
# ╚════════════════════════════════════════════════════════════════════╝

class JanAushadhiSearchRequest(BaseModel):
    """
    Request body for Jan Aushadhi generic RAG search.
    
    Unlike /api/search which uses the hardcoded CDSCO compliance prompt,
    this endpoint allows the caller to optionally inject a custom system
    prompt or uses a minimal generic one.
    
    Use cases:
      - Search Jan Aushadhi medicine lists for generic alternatives
      - Search Jan Aushadhi Kendra location directories
      - Any KB query that needs raw text output (not the CDSCO JSON format)
    """
    query: str = Field(..., description="The search query for the Knowledge Base")
    system_prompt: Optional[str] = Field(
        default=None,
        description="Optional custom system prompt. If not provided, a minimal generic prompt is used."
    )
    max_results: int = Field(default=10, ge=1, le=50, description="Max retrieval results from KB (1-50)")


class JanAushadhiSearchResponse(BaseModel):
    """
    Response from POST /api/janaushadhi/search.
    
    Returns raw text from the LLM (not the structured CDSCO JSON).
    The caller is responsible for further processing the text.
    """
    query: str = Field(..., description="Original query")
    text: str = Field(default="", description="Raw text response from LLM after RAG retrieval")
    citations: list = Field(default_factory=list, description="Source citations from KB documents")
    session_id: Optional[str] = Field(default=None, description="Bedrock session ID for continuity")


class HealthResponse(BaseModel):
    """Response from GET /health."""
    status: str = "healthy"
    service: str = "knowledge-base-aws"
    version: str = "1.2.0"
    bedrock_kb_id: Optional[str] = None
