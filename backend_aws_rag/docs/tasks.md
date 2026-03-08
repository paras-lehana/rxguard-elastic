## Plan R1: Pagination & Soft Deletes (v1.1.0) — ✅ COMPLETED

### Section A: Schema Updates (schemas.py)

- [x] **A1. Add pagination fields to `DocumentsResponse` schema** ✅ DONE — Added `page` (default=1), `total_pages` (default=1), `page_size` (default=10) fields with Field descriptions. Existing `documents` and `total` fields kept intact. Backward compatible since all new fields have defaults.

- [x] **A2. Add `is_active` field to `DocumentItem` schema** ✅ DONE — Added `is_active: bool = Field(default=True, description="Soft-delete flag...")` to `DocumentItem`. Default True ensures backward compatibility.

- [x] **A3. Add `PaginationParams` schema for reuse** ✅ DONE — Created `PaginationParams(BaseModel)` with `page: int = Field(default=1, ge=1)` and `size: int = Field(default=10, ge=1, le=100)`. Added above DocumentMetadataItem for logical ordering.

### Section B: Service Layer — Pagination in `list_documents` (bedrock_service.py)

- [x] **B1. Add `page_number` and `page_size` parameters to `list_documents`** ✅ DONE — Changed signature to `async def list_documents(self, page_number: int = 1, page_size: int = 10)`. Defaults maintain backward compat.

- [x] **B2. Change the Kendra query text from `"list all documents"` to `"*.pdf"`** ✅ DONE — Replaced semantic query `"list all documents"` with pattern `"*.pdf"` in the Kendra query call.

- [x] **B3. Replace hardcoded `PageSize=100` with pagination parameters** ✅ DONE — Now using `PageSize=page_size` and `PageNumber=page_number` from method args.

- [x] **B4. Compute and return `total_pages` along with documents** ✅ DONE — Return type changed to `Tuple[List, int, int, int]`. Uses `math.ceil(total / page_size)`.

- [x] **B5. Add `is_active` metadata to each listed document** ✅ DONE — Reads `_is_active` from Kendra `DocumentAttributes` array. Defaults to `True`.

- [x] **B6. Filter out soft-deleted documents from listing** ✅ DONE — Added `if not is_active: continue`.

### Section C: API Route — Pagination in `documents.py`

- [x] **C1. Add `page` and `size` query parameters to `GET /api/documents`** ✅ DONE — Added `page: int = Query(default=1, ge=1)` and `size: int = Query(default=10, ge=1, le=100)`.

- [x] **C2. Pass pagination params to `service.list_documents()`** ✅ DONE

- [x] **C3. Update response construction with pagination fields** ✅ DONE

- [x] **C4. Add `is_active` field mapping in document item construction** ✅ DONE

### Section D: Service Layer — Soft Delete in `delete_document` (bedrock_service.py)

- [x] **D1. Add soft-delete step BEFORE the hard delete call** ✅ DONE — Calls `batch_put_document` to set `_is_active=false` before `batch_delete_document`.

- [x] **D2. Build the `batch_put_document` payload for soft-delete** ✅ DONE

- [x] **D3. Handle soft-delete failure gracefully** ✅ DONE — Logs WARNING, continues to hard-delete.

- [x] **D4. Keep existing `batch_delete_document` call after soft-delete** ✅ DONE

### Section E: Service Layer — Search Filtering in `rag_search` (bedrock_service.py)

- [x] **E1. Add `is_active` filter to `_try_rag_search_extended`** ✅ DONE — `notEquals` filter, conditional on `ENABLE_SOFT_DELETE` + `use_filter` param.

- [x] **E2. Basic fallback has NO filter** ✅ DONE (REVERTED) — Initially added, then removed. Basic fallback must be pure safe path.

- [x] **E3. Backward compat for docs without `is_active` attribute** ✅ DONE — `notEquals` treats missing attributes as not matching.

- [x] **E4. (POST-DEPLOY FIX) 3-level graceful degradation** ✅ DONE — extended+filter → extended-no-filter → basic fallback.

### Section F: Kendra Configuration

- [x] **F1. Document Kendra Console configuration** ✅ DONE
- [x] **F2. Utility function to register attribute** ✅ DONE — `register_is_active_attribute()` method.
- [x] **F3. `ENABLE_SOFT_DELETE` environment variable** ✅ DONE

### Section G: Testing & Verification

- [x] **G1. Inline verification comments** ✅ DONE
- [x] **G2. Document verification scenario** ✅ DONE
- [x] **G3. Edge case handling** ✅ DONE

### Section H: Documentation & Cleanup

- [x] **H1. Update README.md with pagination docs** ✅ DONE
- [x] **H2. Add soft-delete docs to README.md** ✅ DONE
- [x] **H3. Update `.env.example`** ✅ DONE
- [x] **H4. CHANGELOG entry for v1.1.0** ✅ DONE

---

## Plan R3: Bulk Delete All Documents (v1.2.0) — ✅ COMPLETED

### Section I: Schema Updates (schemas.py)

- [x] **I1. Add `DeleteAllResponse` schema** ✅ DONE — Schema already exists in schemas.py. Add new Pydantic model with fields: `message` (str), `deleted_count` (int), `failed_count` (int), `failed_ids` (List[str]). Place it after `DeleteResponse` in the delete section. All fields need defaults for backward compat.

### Section J: Service Layer — `delete_all_documents()` (bedrock_service.py)

- [x] **J1. Add `delete_all_documents()` method signature** ✅ DONE — New async method returning `Dict[str, Any]` with keys: deleted_count, failed_count, failed_ids. Add comprehensive docstring explaining the algorithm.

- [x] **J2. Collect all document IDs by paginating through Kendra** ✅ DONE — Use `describe_index` for total count, then query `"*.pdf"` with `PageSize=100` across all pages. Collect all `DocumentId` values from `ResultItems`. Handle edge case: zero documents → return immediately with `deleted_count=0`.

- [x] **J3. Soft-delete all collected documents** ✅ DONE — Loop through collected IDs and call `batch_put_document` for each, setting `_is_active=false`. Only if `ENABLE_SOFT_DELETE` is True. Catch failures per-document, don't abort the whole operation.

- [x] **J4. Hard-delete in batches of 10** ✅ DONE — Kendra's `batch_delete_document` accepts max 10 IDs per call. Chunk the collected IDs into batches of 10 and call sequentially. Track which deletions succeed/fail. Log each batch.

- [x] **J5. Return summary dict** ✅ DONE — Return `{"deleted_count": N, "failed_count": M, "failed_ids": [...]}`. On complete failure, raise `BedrockServiceError`.

### Section K: API Route — `POST /api/documents/delete_all` (documents.py)

- [x] **K1. Add new route `POST /api/documents/delete_all`** ✅ DONE — Added POST /api/documents/delete_all endpoint in documents.py with DeleteAllResponse, proper tags, summary, description, and error handling.

- [x] **K2. Add `DeleteAllResponse` import** ✅ DONE — Added DeleteAllResponse to the imports from app.models.schemas in documents.py.

### Section L: Documentation & Version Bump

- [x] **L1. Update README.md with delete_all endpoint docs** ✅ DONE — Added POST /api/documents/delete_all section with curl example, response format, and WARNING about destructive operation.

- [x] **L2. Add CHANGELOG entry for v1.2.0** ✅ DONE — Added [1.2.0] - 2026-03-08 entry with Added and Changed sections.

- [x] **L3. Bump version to 1.2.0** ✅ DONE — Updated version in main.py (app definition + health endpoint) and schemas.py (HealthResponse) from 1.1.0 to 1.2.0.

### Section M: Testing & Deployment

- [x] **M1. Compile check all modified files** ✅ DONE — All 4 files pass py_compile: schemas.py, documents.py, main.py, bedrock_service.py.

- [x] **M2. Rebuild and deploy Docker container** ✅ DONE — docker compose up --build -d succeeded. Health check returns v1.2.0.

- [x] **M3. Test `POST /api/documents/delete_all`** ✅ DONE — Response: {"message": "All 9 documents deleted successfully.", "deleted_count": 9, "failed_count": 0, "failed_ids": []}. All 4 keys present.

- [x] **M4. Verify existing APIs still work** ✅ DONE — Health (v1.2.0), List (returns documents/total/page/total_pages/page_size), Search (returns all 7 top-level keys + 30 result fields), Delete single, Index — all backward compatible.