"""
Response transformer — converts Bedrock retrieve_and_generate output
into the EXACT JSON format the frontend expects.

The frontend at medical.lehana.in/ncert parses very specific field names.
This module ensures backward compatibility.
"""

import json
import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ResponseTransformer:
    """
    Transform raw Bedrock output into frontend-compatible JSON.
    
    Bedrock's retrieve_and_generate returns free-form text from Claude.
    Our custom prompt instructs Claude to return JSON, but we must:
      1. Extract the JSON from the text (may have markdown fences)
      2. Map fields to the exact frontend format
      3. Handle malformed output gracefully
    """

    # Default result when parsing fails — all 29 fields from the new prompt
    EMPTY_RESULT = {
        "gazette_id": "N/A",
        "pdf_name": "source not identified",
        "medicine_name": "N/A",
        "date_of_ban": "N/A",
        "date_of_uplift": "N/A",
        "summary": "",
        "reasons_for_ban": "N/A",
        "reasons_for_uplift": "N/A",
        "drug_category": "N/A",
        "population_restriction": "none",
        "schedule_classification": "N/A",
        "controlled_status": "N/A",
        "source_authority": "N/A",
        "act_reference": "N/A",
        "alternative_medicines": "Not specified in documents",
        "compliance_note": "",
        "name_image_match": "N/A",
        "source_banned": "",
        "source_internet": "",
        "source_approved": "never banned",
        "source_approved_internet": "",
        "approved_gazette": "",
        "source_scheduled": "",
        "source_scheduled_file": "",
        "source_scheduled_internet": "",
        "source_controlled": "",
        "keyword": "",
        "misc": "",
        "reasoning": "",
        "itemid": "N/A",
    }

    @staticmethod
    def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON object from LLM output text.
        
        Handles:
          - Clean JSON
          - JSON wrapped in ```json ... ``` markdown fences
          - JSON with leading/trailing text
        """
        if not text or not text.strip():
            return None

        # Attempt 1: Direct parse
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # Attempt 2: Extract from markdown code fences
        fence_pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
        matches = re.findall(fence_pattern, text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue

        # Attempt 3: Find first { ... } block (greedy)
        brace_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
        matches = re.findall(brace_pattern, text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        # Attempt 4: Find the outermost { to last }
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            try:
                return json.loads(text[first_brace:last_brace + 1])
            except json.JSONDecodeError:
                pass

        logger.warning("Could not extract JSON from LLM output (length=%d)", len(text))
        return None

    @classmethod
    def transform_search_response(
        cls,
        bedrock_result: Dict[str, Any],
        query: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Transform Bedrock RAG output → exact frontend SearchResponse format.
        
        Frontend expects:
        {
            "query": "...",
            "medicine_searched": "...",
            "total_results": "1",
            "current_status": "banned",
            "results": { ...single object with 29 fields... },
            "text": "...",
            "sessionId": "..."
        }
        """
        output_text = bedrock_result.get("output_text", "")
        response_session_id = bedrock_result.get("session_id", session_id)

        # Try to parse the LLM's structured JSON
        parsed = cls.extract_json_from_text(output_text)

        if parsed:
            logger.info("Successfully parsed LLM JSON output")
            return cls._build_from_parsed(parsed, query, response_session_id, output_text)
        else:
            logger.warning("Using fallback — LLM did not return parseable JSON")
            return cls._build_fallback(query, response_session_id, output_text)

    @classmethod
    def _build_from_parsed(
        cls,
        parsed: Dict[str, Any],
        query: str,
        session_id: Optional[str],
        raw_text: str,
    ) -> Dict[str, Any]:
        """Build response from successfully parsed LLM JSON."""
        
        # Extract the results — could be array or single object
        raw_results = parsed.get("results", {})
        
        if isinstance(raw_results, list) and len(raw_results) > 0:
            # LLM returned an array — take the first result for frontend compatibility
            result_obj = cls._normalize_result(raw_results[0])
        elif isinstance(raw_results, dict):
            result_obj = cls._normalize_result(raw_results)
        else:
            result_obj = dict(cls.EMPTY_RESULT)

        # Build the summary text — prefer the summary from results
        summary_text = result_obj.get("summary", "")
        if not summary_text:
            summary_text = parsed.get("summary", parsed.get("text", ""))

        return {
            "query": parsed.get("query", query),
            "medicine_searched": parsed.get("medicine_searched", ""),
            "total_results": str(parsed.get("total_results", "1")),
            "current_status": parsed.get("current_status", "unknown"),
            "results": result_obj,
            "text": summary_text or raw_text[:500],
            "sessionId": session_id,
        }

    @classmethod
    def _build_fallback(
        cls,
        query: str,
        session_id: Optional[str],
        raw_text: str,
    ) -> Dict[str, Any]:
        """Fallback when LLM output is not JSON — return the raw text."""
        result = dict(cls.EMPTY_RESULT)
        result["summary"] = raw_text[:500] if raw_text else "No response generated"
        result["reasoning"] = raw_text
        result["keyword"] = query.lower().strip()

        return {
            "query": query,
            "medicine_searched": query.lower().strip(),
            "total_results": "0",
            "current_status": "unknown",
            "results": result,
            "text": raw_text or "Unable to parse structured response from knowledge base.",
            "sessionId": session_id,
        }

    @classmethod
    def _normalize_result(cls, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure a result dict has all 29 required fields with correct defaults.

        Pass through ALL fields from the LLM output, falling back to
        EMPTY_RESULT defaults for any missing fields.
        """
        normalized = dict(cls.EMPTY_RESULT)

        # Copy all known fields from LLM result
        for key in cls.EMPTY_RESULT:
            if key in result and result[key] is not None:
                normalized[key] = str(result[key])

        # Also copy any extra fields the LLM may return (forward-compatible)
        for key, value in result.items():
            if key not in normalized and value is not None:
                normalized[key] = str(value)

        return normalized

    @classmethod
    def transform_document_list(
        cls,
        documents: list,
        total: int,
    ) -> Dict[str, Any]:
        """Transform document list to frontend format."""
        return {
            "documents": documents,
            "total": total,
        }
