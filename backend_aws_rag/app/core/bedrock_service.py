"""
Bedrock Knowledge Base service — all AWS operations.

This is the central business logic layer. All boto3 calls go through here.
Endpoints never call boto3 directly.

Architecture for Kendra GenAI Index Knowledge Bases:
  • Document CRUD  → Kendra client (batch_put_document, list_documents, batch_delete_document)
  • RAG Search      → Bedrock Agent Runtime (retrieve_and_generate)
  • KB Metadata     → Bedrock Agent (get_knowledge_base, list_data_sources)

The Kendra Index ID is auto-detected from the KB if not configured.
"""

import base64
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from botocore.exceptions import ClientError, ParamValidationError

from app.config import get_settings
from app.core.bedrock_client import get_bedrock_clients

logger = logging.getLogger(__name__)


class BedrockServiceError(Exception):
    """Custom exception for Bedrock service failures."""

    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class BedrockKBService:
    """
    All AWS operations for Kendra GenAI Index Knowledge Base.
    
    Document operations go through the Kendra client.
    RAG search goes through the Bedrock Agent Runtime client.
    """

    def __init__(self):
        self._settings = get_settings()
        self._clients = get_bedrock_clients()
        self._cached_kendra_index_id: Optional[str] = None

    @property
    def kb_id(self) -> str:
        return self._settings.BEDROCK_KB_ID

    @property
    def model_arn(self) -> str:
        return self._settings.model_arn

    # ────────────────────────────────────────────────────────────────
    # Kendra Index ID Discovery
    # ────────────────────────────────────────────────────────────────

    def _get_kendra_index_id(self) -> str:
        """
        Get the Kendra Index ID for document operations.
        
        Priority:
          1. Cached value
          2. KENDRA_INDEX_ID from .env
          3. Auto-detect from the Bedrock Knowledge Base configuration
        """
        if self._cached_kendra_index_id:
            return self._cached_kendra_index_id

        # Check env var
        if self._settings.KENDRA_INDEX_ID:
            self._cached_kendra_index_id = self._settings.KENDRA_INDEX_ID
            logger.info("Using configured KENDRA_INDEX_ID: %s", self._cached_kendra_index_id)
            return self._cached_kendra_index_id

        # Auto-detect from KB
        try:
            kb_response = self._clients.agent.get_knowledge_base(
                knowledgeBaseId=self.kb_id,
            )
            kb_config = kb_response.get("knowledgeBase", {})
            storage_config = kb_config.get("storageConfiguration", {})

            # For Kendra GenAI Index, the index info is in the KB config
            kendra_config = storage_config.get("kendraKnowledgeBaseConfiguration", {})
            index_id = kendra_config.get("kendraIndexId", "")

            if not index_id:
                # Try extracting from ARN if available
                arn = self._settings.KENDRA_INDEX_ARN or ""
                if arn:
                    # ARN format: arn:aws:kendra:region:account:index/index-id
                    parts = arn.split("/")
                    index_id = parts[-1] if len(parts) > 1 else ""

            if not index_id:
                raise BedrockServiceError(
                    "Could not determine Kendra Index ID. "
                    "Please set KENDRA_INDEX_ID in your .env file.",
                    status_code=500,
                )

            self._cached_kendra_index_id = index_id
            logger.info("Auto-detected Kendra Index ID: %s", index_id)
            return index_id

        except ClientError as e:
            raise BedrockServiceError(
                f"Failed to get KB config: {e.response['Error']['Message']}. "
                f"Please set KENDRA_INDEX_ID in your .env file.",
                status_code=502,
            ) from e

    # ────────────────────────────────────────────────────────────────
    # POST /api/index — Ingest Document via Kendra BatchPutDocument
    # ────────────────────────────────────────────────────────────────

    async def ingest_document(
        self,
        file_content: bytes,
        file_name: str,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Upload a document directly into Kendra using BatchPutDocument.
        
        Sends the file content as a blob — NO S3 bucket needed.
        This is the correct approach for Kendra GenAI Index KBs.
        """
        index_id = self._get_kendra_index_id()

        # Generate a stable document ID from the filename
        doc_id = file_name.rsplit(".", 1)[0].replace(" ", "_").lower()

        # Determine content type
        content_type = "PDF"  # Default
        ext = file_name.lower().rsplit(".", 1)[-1] if "." in file_name else ""
        content_type_map = {
            "pdf": "PDF",
            "html": "HTML",
            "txt": "PLAIN_TEXT",
            "csv": "CSV",
            "md": "MD",
        }
        content_type = content_type_map.get(ext, "PDF")

        try:
            # Build the Kendra document object
            # NOTE: Kendra custom attributes must be pre-registered in the index.
            # We store the original filename in the Title field instead.
            document = {
                "Id": doc_id,
                "Title": file_name,
                "Blob": file_content,
                "ContentType": content_type,
            }

            logger.info(
                "Ingesting document via Kendra: file=%s, doc_id=%s, index=%s, size=%d bytes, type=%s",
                file_name, doc_id, index_id, len(file_content), content_type,
            )

            response = self._clients.kendra.batch_put_document(
                IndexId=index_id,
                Documents=[document],
            )

            # Check for errors in the response
            failed_docs = response.get("FailedDocuments", [])
            if failed_docs:
                error_msg = failed_docs[0].get("ErrorMessage", "Unknown error")
                error_code = failed_docs[0].get("ErrorCode", "UNKNOWN")
                logger.error(
                    "Kendra ingestion failed: doc_id=%s, code=%s, msg=%s",
                    doc_id, error_code, error_msg,
                )
                raise BedrockServiceError(
                    f"Document ingestion failed: {error_msg}",
                    status_code=502,
                    details={"error_code": error_code},
                )

            document_name = f"{self.kb_id}/documents/{doc_id}"

            logger.info(
                "Document ingested via Kendra: doc_id=%s, document_name=%s",
                doc_id, document_name,
            )

            return {
                "done": True,
                "documentName": document_name,
                "documentId": doc_id,
                "status": "INDEXED",
            }

        except ClientError as e:
            error_msg = e.response["Error"]["Message"]
            error_code = e.response["Error"]["Code"]
            logger.error("Kendra ingestion failed: %s — %s", error_code, error_msg)
            raise BedrockServiceError(
                f"Failed to ingest document: {error_msg}",
                status_code=502,
                details={"aws_error_code": error_code},
            ) from e

    # ────────────────────────────────────────────────────────────────
    # GET /api/documents — List Documents via Kendra (Paginated)
    # ────────────────────────────────────────────────────────────────

    async def list_documents(
        self,
        page_number: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Dict[str, Any]], int, int, int]:
        """
        List documents in the Kendra Index with server-side pagination.
        
        Uses Kendra query API with "*.pdf" to capture ALL PDFs.
        Applies pagination via Kendra's PageNumber/PageSize params.
        Filters out soft-deleted documents (is_active=false).
        
        Args:
            page_number: 1-based page number (default 1).
            page_size: Number of items per page (default 10, max 100).
        
        Returns:
            Tuple of (documents_list, total_count, page_number, total_pages).
            
        Pagination math:
            total_pages = ceil(total_count / page_size)
            If page_number > total_pages → returns empty list with correct metadata.
        """
        index_id = self._get_kendra_index_id()

        try:
            documents = []

            # Use Kendra's describe_index to get document count
            index_info = self._clients.kendra.describe_index(Id=index_id)
            index_stats = index_info.get("IndexStatistics", {})
            text_stats = index_stats.get("TextDocumentStatistics", {})
            total = text_stats.get("IndexedTextDocumentsCount", 0)

            # Calculate total_pages (ceil division, minimum 0 if no docs)
            import math
            total_pages = math.ceil(total / page_size) if total > 0 else 0

            # Edge case: page beyond total_pages → return empty with metadata
            if page_number > total_pages and total > 0:
                logger.info(
                    "Page %d exceeds total_pages %d — returning empty list",
                    page_number, total_pages,
                )
                return [], total, page_number, total_pages

            # Query Kendra with "*.pdf" to capture all PDF documents
            # Previously used "list all documents" which was a semantic query —
            # it only returned docs semantically related to that phrase.
            # "*.pdf" is a pattern match that reliably captures all PDFs.
            if total > 0:
                try:
                    query_kwargs = {
                        "IndexId": index_id,
                        "QueryText": "*.pdf",
                        "PageSize": page_size,
                        "PageNumber": page_number,
                    }

                    query_response = self._clients.kendra.query(**query_kwargs)

                    for item in query_response.get("ResultItems", []):
                        doc_id = item.get("DocumentId", "unknown")
                        doc_title = item.get("DocumentTitle", {})
                        title_text = doc_title.get("Text", doc_id) if isinstance(doc_title, dict) else str(doc_title)
                        doc_uri = item.get("DocumentURI", "")

                        # Check is_active attribute from Kendra document attributes
                        # Documents with is_active=false are soft-deleted and should be hidden
                        doc_attributes = item.get("DocumentAttributes", [])
                        is_active = True  # Default: active unless explicitly marked false
                        for attr in doc_attributes:
                            if attr.get("Key") == "_is_active":
                                attr_value = attr.get("Value", {}).get("StringValue", "true")
                                is_active = attr_value.lower() != "false"
                                break

                        # Skip soft-deleted documents
                        if not is_active:
                            continue

                        documents.append({
                            "name": f"{self.kb_id}/documents/{doc_id}",
                            "displayName": title_text or doc_id,
                            "state": "ACTIVE",
                            "is_active": is_active,
                            "metadata": [
                                {"key": "documentId", "value": doc_id},
                                {"key": "documentURI", "value": doc_uri} if doc_uri else None,
                            ],
                        })
                        # Clean up None entries in metadata
                        documents[-1]["metadata"] = [
                            m for m in documents[-1]["metadata"] if m is not None
                        ]

                except ClientError as qe:
                    logger.warning("Query for document list failed: %s", str(qe)[:100])
                    # Return empty list with known count
                    return [], total, page_number, total_pages

            logger.info(
                "Listed %d documents from Kendra index %s (page=%d/%d, total=%d)",
                len(documents), index_id, page_number, total_pages, total,
            )
            return documents, total if total else len(documents), page_number, total_pages

        except ClientError as e:
            error_msg = e.response["Error"]["Message"]
            logger.error("Failed to list documents: %s", error_msg)
            raise BedrockServiceError(
                f"Failed to list documents: {error_msg}",
                status_code=502,
            ) from e

    # ────────────────────────────────────────────────────────────────
    # POST /api/documents/delete — Soft-Delete + Hard-Delete via Kendra
    # ────────────────────────────────────────────────────────────────

    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from the Kendra Index using a two-step approach:
        
        Step 1 (Soft-delete): Set is_active=false via batch_put_document.
                This immediately hides the doc from search results and listings.
                Kendra's actual deletion can take minutes — the soft-delete
                provides instant visual feedback.
        
        Step 2 (Hard-delete): Call batch_delete_document to permanently remove
                the document from the index.
        
        If soft-delete fails (e.g., _is_active attribute not registered),
        we log a warning but proceed with hard-delete. This makes the feature
        gracefully degrade if Kendra hasn't been configured for soft-deletes yet.
        
        Accepts document_id in format: KB-XXX/documents/YYY
        """
        index_id = self._get_kendra_index_id()
        settings = self._settings

        # Parse the document identifier
        # Input: "KB-XXX/documents/YYY" → we need the "YYY" part
        parts = document_id.split("/documents/")
        doc_key = parts[-1] if len(parts) > 1 else document_id

        # ── Step 1: Soft-delete — set is_active=false ────────────
        # Only attempt if ENABLE_SOFT_DELETE is True (default)
        enable_soft_delete = getattr(settings, "ENABLE_SOFT_DELETE", True)
        if enable_soft_delete:
            try:
                soft_delete_doc = {
                    "Id": doc_key,
                    "Attributes": [
                        {
                            "Key": "_is_active",
                            "Value": {"StringValue": "false"},
                        }
                    ],
                }

                self._clients.kendra.batch_put_document(
                    IndexId=index_id,
                    Documents=[soft_delete_doc],
                )

                logger.info(
                    "Soft-deleted document: %s (set _is_active=false) in index %s",
                    doc_key, index_id,
                )

            except (ClientError, ParamValidationError) as soft_err:
                # Soft-delete failure is NOT fatal — log and continue to hard delete
                # Common cause: _is_active custom attribute not registered in Kendra
                logger.warning(
                    "Soft-delete attribute update failed for doc_id=%s: %s. "
                    "Proceeding with hard delete. "
                    "Hint: Register '_is_active' as a custom String attribute in Kendra console.",
                    doc_key, str(soft_err)[:200],
                )

        # ── Step 2: Hard-delete — permanently remove from index ──
        try:
            self._clients.kendra.batch_delete_document(
                IndexId=index_id,
                DocumentIdList=[doc_key],
            )

            logger.info("Hard-deleted document: %s from Kendra index %s", doc_key, index_id)
            return True

        except ClientError as e:
            error_msg = e.response["Error"]["Message"]
            logger.error("Failed to delete document %s: %s", document_id, error_msg)
            raise BedrockServiceError(
                f"Failed to delete document: {error_msg}",
                status_code=502,
            ) from e

    async def delete_all_documents(self) -> Dict[str, Any]:
        """
        Delete all documents from the Kendra Index.

        Algorithm:
        1. Collect all document IDs by querying Kendra iteratively.
        2. Soft-delete all collected documents by setting _is_active=false.
        3. Hard-delete all collected documents in batches of 10.
        4. Return summary with deleted_count, failed_count, failed_ids.
        """
        index_id = self._get_kendra_index_id()
        settings = self._settings

        # 1. Collect all document IDs
        all_doc_ids = []
        try:
            # First, check if there are any documents to avoid unnecessary queries
            logger.info("Collecting all documents from index %s for deletion...", index_id)
            page_number = 1
            while True:
                response = self._clients.kendra.query(
                    IndexId=index_id,
                    QueryText="*.pdf",
                    PageNumber=page_number,
                    PageSize=100
                )
                items = response.get("ResultItems", [])
                if not items:
                    break
                
                for item in items:
                    if "DocumentId" in item:
                        all_doc_ids.append(item["DocumentId"])
                
                if len(items) < 100:
                    break
                page_number += 1
        except ClientError as e:
            error_msg = e.response["Error"]["Message"]
            logger.error("Failed to query documents for bulk deletion: %s", error_msg)
            raise BedrockServiceError(
                f"Failed to query documents: {error_msg}", status_code=502
            ) from e

        total_docs = len(all_doc_ids)
        if total_docs == 0:
            logger.info("No documents found to delete.")
            return {"deleted_count": 0, "failed_count": 0, "failed_ids": []}

        logger.info("Found %d documents to delete.", total_docs)

        # 2. Soft-delete all collected documents
        enable_soft_delete = getattr(settings, "ENABLE_SOFT_DELETE", True)
        if enable_soft_delete:
            logger.info("Soft-deleting %d documents before hard delete...", total_docs)
            for doc_id in all_doc_ids:
                try:
                    soft_delete_doc = {
                        "Id": doc_id,
                        "Attributes": [{"Key": "_is_active", "Value": {"StringValue": "false"}}]
                    }
                    self._clients.kendra.batch_put_document(
                        IndexId=index_id,
                        Documents=[soft_delete_doc]
                    )
                except Exception as soft_err:
                    logger.warning("Soft-delete failed for doc_id=%s: %s", doc_id, str(soft_err)[:200])

        # 3. Hard-delete in batches of 10
        logger.info("Hard-deleting %d documents in batches of 10...", total_docs)
        deleted_count = 0
        failed_count = 0
        failed_ids = []
        
        batch_size = 10
        for i in range(0, total_docs, batch_size):
            batch = all_doc_ids[i:i + batch_size]
            try:
                response = self._clients.kendra.batch_delete_document(
                    IndexId=index_id,
                    DocumentIdList=batch
                )
                
                failed_docs = response.get("FailedDocuments", [])
                failed_in_batch = [fd["Id"] for fd in failed_docs]
                
                failed_ids.extend(failed_in_batch)
                failed_count += len(failed_in_batch)
                deleted_count += (len(batch) - len(failed_in_batch))
                
                logger.info("Batch processed: %d deleted, %d failed.", len(batch) - len(failed_in_batch), len(failed_in_batch))
            except ClientError as e:
                error_msg = e.response["Error"]["Message"]
                logger.error("Failed to delete batch starting at index %d: %s", i, error_msg)
                failed_ids.extend(batch)
                failed_count += len(batch)

        if failed_count == total_docs and total_docs > 0:
            logger.error("Complete failure when deleting documents.")
            raise BedrockServiceError("Failed to delete any documents.", status_code=502)

        return {
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "failed_ids": failed_ids
        }

    # ────────────────────────────────────────────────────────────────
    # POST /api/search — RAG Search via Bedrock (MOST CRITICAL)
    # ────────────────────────────────────────────────────────────────

    async def rag_search(
        self,
        query: str,
        system_prompt: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Perform RAG search using Bedrock retrieve_and_generate.
        
        Sends the query + custom CDSCO system prompt to Bedrock KB.
        The KB retrieves relevant chunks from Kendra, then Claude
        generates a structured JSON response.
        
        IMPORTANT:
          - Session IDs: Bedrock generates its own session IDs.
            User-provided session IDs are NOT valid. We only re-use
            session IDs that Bedrock previously returned.
          - Prompt: Sent via generationConfiguration.promptTemplate.
            Kendra has a 1000-char limit on query text, so the prompt
            CANNOT be injected into the query.
        
        Returns raw Bedrock response dict.
        """
        # Don't pass user-provided session IDs — Bedrock only accepts
        # session IDs it has generated from previous interactions.
        # We ignore the session_id parameter for now.
        effective_session_id = None

        try:
            response = self._try_rag_search_extended(query, system_prompt, effective_session_id)
        except Exception as extended_error:
            error_str = str(extended_error)[:200]
            logger.warning(
                "Extended retrieve_and_generate failed (%s), trying basic call",
                error_str,
            )

            # If the filter caused a ValidationException, retry extended WITHOUT filter
            # This happens when _is_active attribute isn't registered in Kendra yet
            if "filter" in error_str.lower() or "ValidationException" in error_str:
                logger.info("Filter-related error detected — retrying extended call WITHOUT soft-delete filter")
                try:
                    response = self._try_rag_search_extended(
                        query, system_prompt, effective_session_id, use_filter=False,
                    )
                except Exception:
                    logger.warning("Extended call without filter also failed, falling back to basic")
                    try:
                        response = self._try_rag_search_basic(query, effective_session_id)
                    except ClientError as e:
                        error_msg = e.response["Error"]["Message"]
                        error_code = e.response["Error"]["Code"]
                        logger.error("RAG search failed: %s — %s", error_code, error_msg)
                        raise BedrockServiceError(
                            f"RAG search failed: {error_msg}",
                            status_code=502,
                            details={"aws_error_code": error_code},
                        ) from e
            else:
                try:
                    response = self._try_rag_search_basic(query, effective_session_id)
                except ClientError as e:
                    error_msg = e.response["Error"]["Message"]
                    error_code = e.response["Error"]["Code"]
                    logger.error("RAG search failed: %s — %s", error_code, error_msg)
                    raise BedrockServiceError(
                        f"RAG search failed: {error_msg}",
                        status_code=502,
                        details={"aws_error_code": error_code},
                    ) from e

        output_text = response.get("output", {}).get("text", "")
        response_session_id = response.get("sessionId", "")
        citations = response.get("citations", [])

        logger.info(
            "RAG search completed: output_length=%d, citations=%d, session=%s",
            len(output_text), len(citations), response_session_id,
        )

        return {
            "output_text": output_text,
            "session_id": response_session_id,
            "citations": citations,
            "raw_response": response,
        }

    def _try_rag_search_extended(
        self, query: str, system_prompt: str, session_id: Optional[str],
        use_filter: bool = True,
    ) -> Dict[str, Any]:
        """
        Full API — includes generationConfiguration with custom prompt,
        retrievalConfiguration with numberOfResults, and optional is_active filter.
        
        The prompt template MUST include $search_results$ placeholder
        for Bedrock to inject the retrieved document chunks.
        
        The is_active filter ensures soft-deleted documents are excluded
        from retrieval. If use_filter=False, the filter is skipped (used
        for graceful retry when the Kendra attribute isn't registered yet).
        """
        # Ensure prompt has the $search_results$ placeholder
        prompt_with_placeholder = system_prompt
        if "$search_results$" not in prompt_with_placeholder:
            prompt_with_placeholder += "\n\nHere are the search results:\n$search_results$"

        # Build the vector search config
        vector_search_config: Dict[str, Any] = {
            "numberOfResults": 10,
        }

        # Add soft-delete filter ONLY if enabled AND use_filter is True
        # The filter requires _is_active attribute to be registered in Kendra.
        # If it's not registered, the API returns ValidationException and
        # rag_search() retries with use_filter=False.
        enable_soft_delete = getattr(self._settings, "ENABLE_SOFT_DELETE", True)
        filter_applied = enable_soft_delete and use_filter
        if filter_applied:
            vector_search_config["filter"] = {
                "notEquals": {
                    "key": "_is_active",
                    "value": {"stringValue": "false"},
                },
            }

        kwargs: Dict[str, Any] = {
            "input": {"text": query},
            "retrieveAndGenerateConfiguration": {
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": {
                    "knowledgeBaseId": self.kb_id,
                    "modelArn": self.model_arn,
                    "generationConfiguration": {
                        "promptTemplate": {
                            "textPromptTemplate": prompt_with_placeholder,
                        },
                    },
                    "retrievalConfiguration": {
                        "vectorSearchConfiguration": vector_search_config,
                    },
                },
            },
        }
        if session_id:
            kwargs["sessionId"] = session_id

        logger.info("RAG search (extended): query='%s', kb=%s, soft_delete_filter=%s", query[:80], self.kb_id, filter_applied)
        return self._clients.agent_runtime.retrieve_and_generate(**kwargs)

    def _try_rag_search_basic(
        self, query: str, session_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Basic API fallback — knowledgeBaseId + modelArn ONLY.
        
        Does NOT inject the system prompt into the query text because
        Kendra has a 1000-char limit on query text. Instead, sends
        just the user query and lets the KB use its default behavior.
        
        IMPORTANT: This is the last-resort fallback. It intentionally
        does NOT include any filters to maximize the chance of success.
        If the extended call with filter fails, we don't want this
        fallback to also fail for the same reason.
        """
        kwargs: Dict[str, Any] = {
            "input": {"text": query},
            "retrieveAndGenerateConfiguration": {
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": {
                    "knowledgeBaseId": self.kb_id,
                    "modelArn": self.model_arn,
                },
            },
        }
        if session_id:
            kwargs["sessionId"] = session_id

        logger.info("RAG search (basic fallback, no filter): query='%s', kb=%s", query[:80], self.kb_id)
        return self._clients.agent_runtime.retrieve_and_generate(**kwargs)

    # ────────────────────────────────────────────────────────────────
    # Utility: Register _is_active Custom Attribute in Kendra
    # ────────────────────────────────────────────────────────────────

    def register_is_active_attribute(self) -> bool:
        """
        Programmatically register the '_is_active' custom attribute in Kendra.
        
        This is a ONE-TIME setup step required before soft-delete works.
        Can also be done manually via:
          AWS Console → Amazon Kendra → Select Index → Facets/Custom Attributes
          → Add attribute: Name="_is_active", Type=STRING_VALUE,
            Searchable=No, Displayable=Yes, Facetable=Yes
        
        This function is idempotent — calling it when the attribute
        already exists will NOT cause an error (Kendra merges the config).
        
        Returns True if registration succeeded, False if it failed.
        """
        index_id = self._get_kendra_index_id()

        try:
            self._clients.kendra.update_index(
                Id=index_id,
                DocumentMetadataConfigurationUpdates=[
                    {
                        "Name": "_is_active",
                        "Type": "STRING_VALUE",
                        "Search": {
                            "Facetable": True,
                            "Searchable": False,
                            "Displayable": True,
                            "Sortable": False,
                        },
                    }
                ],
            )
            logger.info(
                "Registered '_is_active' custom attribute in Kendra index %s",
                index_id,
            )
            return True

        except ClientError as e:
            error_msg = e.response["Error"]["Message"]
            # Check if error indicates attribute already exists
            if "already exists" in error_msg.lower() or "ValidationException" in str(e):
                logger.info("'_is_active' attribute already registered in index %s", index_id)
                return True
            logger.error(
                "Failed to register '_is_active' attribute: %s", error_msg,
            )
            return False


# ── Module-level convenience function ────────────────────────────────

def get_bedrock_service() -> BedrockKBService:
    """Create a new service instance (lightweight, reads from cached singletons)."""
    return BedrockKBService()
