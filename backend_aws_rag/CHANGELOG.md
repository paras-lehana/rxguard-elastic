# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - 2026-03-08

### Added
- **Bulk delete endpoint** `POST /api/documents/delete_all`
  - Paginates through all documents in Kendra index to collect IDs
  - Soft-deletes each document (sets `_is_active=false`) before hard-delete
  - Hard-deletes in batches of 10 (Kendra API limit)
  - Returns summary: `deleted_count`, `failed_count`, `failed_ids`
  - Graceful error handling: partial failures don't abort the operation
- **`DeleteAllResponse` schema** with `message`, `deleted_count`, `failed_count`, `failed_ids`

### Changed
- **Version** bumped from 1.1.0 to 1.2.0

## [1.1.0] - 2026-03-07

### Added
- **Pagination support** for `GET /api/documents` endpoint
  - New query parameters: `page` (default 1, min 1) and `size` (default 10, min 1, max 100)
  - Response now includes `page`, `total_pages`, and `page_size` fields
  - `PaginationParams` reusable Pydantic schema for future endpoints
- **Soft-delete mechanism** for document deletion
  - `delete_document` now sets `_is_active=false` via `batch_put_document` before hard-deleting
  - Provides instant hiding from search/listing while Kendra processes actual deletion
  - Graceful degradation: soft-delete failure doesn't block hard-delete
- **Search filtering** by `is_active` status
  - RAG search (`_try_rag_search_extended` and `_try_rag_search_basic`) now filters out soft-deleted documents
  - Uses `notEquals` filter for backward compatibility with pre-existing documents
- **`ENABLE_SOFT_DELETE` config option** in `.env`
  - Controls whether soft-delete step runs before hard-delete
  - Default: `true`. Set to `false` if Kendra `_is_active` attribute not registered
- **`register_is_active_attribute()` utility** in `BedrockKBService`
  - Programmatically registers `_is_active` custom attribute in Kendra index
  - Idempotent — safe to call multiple times
- **`is_active` field** on `DocumentItem` schema
  - Frontend can now see whether a document is soft-deleted

### Changed
- **Kendra query text** for listing documents changed from `"list all documents"` (semantic) to `"*.pdf"` (pattern match) for more reliable PDF discovery
- **`list_documents` return type** changed from `Tuple[List, int]` to `Tuple[List, int, int, int]` (docs, total, page_number, total_pages)
- **Version** bumped from 1.0.0 to 1.1.0

### Technical
- All modified files pass `python3 -m py_compile` validation
- Backward compatible: default parameters preserve existing behavior
- Plan documented in `docs/plan_R1/tasks.md`

## [1.0.0] - Initial Release

### Added
- FastAPI application with 4 REST endpoints (index, documents, delete, search)
- Kendra GenAI Index integration for document operations
- Bedrock retrieve_and_generate for RAG search
- 29-field structured response format for CDSCO compliance
- Custom system prompt for pharmaceutical regulatory analysis
- Docker support with docker-compose
- Health check endpoint
