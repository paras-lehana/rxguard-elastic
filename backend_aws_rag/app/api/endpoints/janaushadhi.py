"""
POST /api/janaushadhi/search — Generic RAG search for Jan Aushadhi queries.

Unlike /api/search which uses the hardcoded CDSCO compliance prompt (designed
for drug ban/gazette analysis), this endpoint provides a CLEAN RAG pipeline:
  1. Receive query + optional custom system_prompt
  2. If no system_prompt provided, use a minimal generic one
  3. Call Bedrock retrieve_and_generate with KB + prompt
  4. Return raw text response (not the structured CDSCO JSON)

Use cases:
  - "Find Jan Aushadhi generics for Paracetamol" → returns raw text about medicines
  - "List Kendras in Delhi" → returns raw text about locations
  - Any KB query needing free-form text output

The pharmai_portal frontend orchestrates multi-step flows (LLM → KB → LLM)
and uses this endpoint for the KB retrieval step.
"""

import logging

from fastapi import APIRouter, HTTPException

from app.core.bedrock_service import BedrockServiceError, get_bedrock_service
from app.models.schemas import JanAushadhiSearchRequest, JanAushadhiSearchResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/janaushadhi", tags=["Jan Aushadhi"])

# Minimal generic prompt — no CDSCO constraints, just factual RAG
_DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful pharmaceutical knowledge assistant. "
    "Answer the user's question based ONLY on the provided search results. "
    "Be factual, precise, and include all relevant details found in the documents. "
    "If the documents do not contain relevant information, clearly state that. "
    "Here are the search results:\n$search_results$"
)


@router.post(
    "/search",
    response_model=JanAushadhiSearchResponse,
    summary="Generic RAG search for Jan Aushadhi medicine and Kendra queries",
    description=(
        "Performs a RAG search against the Bedrock Knowledge Base using "
        "a generic prompt (or caller-provided custom prompt). Returns "
        "raw text — not the structured CDSCO JSON format. "
        "Designed for Jan Aushadhi medicine alternatives and Kendra locator queries."
    ),
)
async def janaushadhi_search(request: JanAushadhiSearchRequest):
    """
    Generic RAG search — no CDSCO prompt overlay.

    Uses the caller's system_prompt if provided, otherwise falls back
    to a minimal generic prompt that instructs Claude to answer
    based on the retrieved KB documents.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="query is required")

    try:
        # Determine which system prompt to use
        system_prompt = request.system_prompt or _DEFAULT_SYSTEM_PROMPT

        # Ensure the prompt has the $search_results$ placeholder
        # (Bedrock requires this to inject retrieved document chunks)
        if "$search_results$" not in system_prompt:
            system_prompt += "\n\nHere are the search results:\n$search_results$"

        # Call Bedrock RAG service
        service = get_bedrock_service()
        bedrock_result = await service.rag_search(
            query=request.query,
            system_prompt=system_prompt,
            session_id=None,  # Fresh session each time
        )

        # Extract fields from the raw Bedrock response
        output_text = bedrock_result.get("output_text", "")
        session_id = bedrock_result.get("session_id", "")
        citations = bedrock_result.get("citations", [])

        # Simplify citations to just source references
        simplified_citations = []
        for citation in citations:
            refs = citation.get("retrievedReferences", [])
            for ref in refs:
                location = ref.get("location", {})
                content = ref.get("content", {}).get("text", "")[:200]
                simplified_citations.append({
                    "source": location,
                    "excerpt": content,
                })

        logger.info(
            "Jan Aushadhi search completed: query='%s', response_length=%d, citations=%d",
            request.query[:80], len(output_text), len(simplified_citations),
        )

        return JanAushadhiSearchResponse(
            query=request.query,
            text=output_text,
            citations=simplified_citations,
            session_id=session_id or None,
        )

    except BedrockServiceError as e:
        logger.error(
            "Jan Aushadhi search error: %s (query='%s')",
            e.message, request.query[:50],
        )
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except Exception as e:
        logger.exception(
            "Unexpected error during Jan Aushadhi search (query='%s')",
            request.query[:50],
        )
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
