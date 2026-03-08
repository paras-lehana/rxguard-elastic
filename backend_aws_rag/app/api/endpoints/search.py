"""
POST /api/search — RAG Search with custom CDSCO compliance prompt.

This is the MOST CRITICAL endpoint. The flow:
  1. Receive query + optional sessionId
  2. Load the custom system prompt (cached)
  3. Call Bedrock retrieve_and_generate with KB + prompt
  4. Transform the LLM output to exact frontend JSON format
  5. Return SearchResponse
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.core.bedrock_service import BedrockServiceError, get_bedrock_service
from app.core.response_transformer import ResponseTransformer
from app.models.schemas import SearchRequest, SearchResponse
from app.utils.custom_prompt import get_prompt_loader

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/api/search",
    response_model=SearchResponse,
    summary="Search the pharmaceutical regulatory knowledge base",
    description=(
        "Performs a RAG search against the Bedrock Knowledge Base using "
        "the custom CDSCO compliance prompt. Returns structured JSON with "
        "medicine ban status, gazette references, and regulatory details."
    ),
    tags=["Search"],
)
async def search(request: SearchRequest):
    """
    RAG search — the core endpoint.
    
    Uses the custom system prompt to instruct Claude to return
    structured pharmaceutical regulatory compliance data.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="query is required")

    try:
        # ── Load custom prompt ───────────────────────────────────
        prompt_loader = get_prompt_loader()
        system_prompt = prompt_loader.get_system_prompt()

        # ── Call Bedrock RAG ─────────────────────────────────────
        service = get_bedrock_service()
        bedrock_result = await service.rag_search(
            query=request.query,
            system_prompt=system_prompt,
            session_id=request.sessionId,
        )

        # ── Transform to frontend format ─────────────────────────
        response_data = ResponseTransformer.transform_search_response(
            bedrock_result=bedrock_result,
            query=request.query,
            session_id=request.sessionId,
        )

        logger.info(
            "Search completed: query='%s', status='%s', results=%s",
            request.query[:50],
            response_data.get("current_status", "unknown"),
            response_data.get("total_results", "0"),
        )

        return SearchResponse(**response_data)

    except BedrockServiceError as e:
        logger.error("Search error: %s (query='%s')", e.message, request.query[:50])
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except FileNotFoundError as e:
        logger.error("Prompt file missing: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail="System prompt configuration error. Contact administrator.",
        )

    except Exception as e:
        logger.exception("Unexpected error during search (query='%s')", request.query[:50])
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
