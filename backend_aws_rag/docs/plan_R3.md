# Plan R3: Bulk Delete All Documents Endpoint

## Problem

The PharmAI Portal frontend needs a "Delete All Documents" button that clears the entire
Knowledge Base. Currently, this is handled by a **fragile proxy loop** in
`pharmai_portal/frontend/app.py` (line 620) which:

1. Fetches `GET /api/documents` — but since plan_R1 introduced pagination (default size=10),
   this only returns the **first 10 documents**, NOT all.
2. Iterates per-document calling `POST /api/documents/delete` — N individual HTTP calls = slow.
3. Falls back to `DELETE /api/documents/all` — which **does not exist** in the backend (404).

## Solution

Add a native `POST /api/documents/delete_all` endpoint to `AWS_RAG_CURD` that:

1. Internally paginates through ALL documents in the Kendra index.
2. Soft-deletes each document (sets `_is_active=false`) for immediate search hiding.
3. Hard-deletes all documents via `batch_delete_document` (supports batches of up to 10 IDs).
4. Returns a summary: `{ "message": "...", "deleted_count": N, "failed_count": N, "failed_ids": [...] }`.

The PharmAI Portal can then simply call this single endpoint instead of looping.

## Design

### New Schema: `DeleteAllResponse` (schemas.py)
```python
class DeleteAllResponse(BaseModel):
    message: str = "All documents deleted successfully"
    deleted_count: int = 0
    failed_count: int = 0
    failed_ids: List[str] = Field(default_factory=list)

New Service Method: delete_all_documents() (bedrock_service.py)

async def delete_all_documents(self) -> Dict[str, Any]:
    """
    Delete ALL documents from the Kendra Index.
    
    Algorithm:
      1. Use describe_index to get total document count.
      2. Query Kendra with "*.pdf" page by page (page_size=100) to collect all doc IDs.
      3. Soft-delete each doc (set _is_active=false) — for immediate search hiding.
      4. Hard-delete in batches of 10 (Kendra batch_delete_document limit).
      5. Return summary with counts and any failed IDs.
    """

New API Endpoint: POST /api/documents/delete_all (documents.py)

1. No request body needed.
2. Returns DeleteAllResponse.
3. Logs each batch deletion for observability.

Backward Compatibility

1. This is a NEW endpoint — no existing endpoints are modified.
2. The existing POST /api/documents/delete (single doc) remains unchanged.
3 Frontend can call this endpoint directly; no output format changes on existing APIs.

Files to Modify
File	Changes
schemas.py	Add DeleteAllResponse schema
bedrock_service.py	Add delete_all_documents() method
documents.py	Add POST /api/documents/delete_all route
README.md	Document new endpoint
CHANGELOG.md	Add entry for v1.2.0

Verification

1. Upload 5+ documents via /api/index.
2. Verify GET /api/documents returns them.
3. Call POST /api/documents/delete_all.
4. Verify response: deleted_count matches uploaded count.
5. Verify GET /api/documents returns 0 documents.
6. Verify search returns no results for previously indexed content.
