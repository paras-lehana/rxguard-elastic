"""
RxGuard service layer — Elastic-core, Bedrock-native drug interaction detection.
==============================================================================

Added for the Elastic + AWS hackathon. The pre-existing PharmAI portal
(Sarvam Indic voice, prescription OCR, Jan Aushadhi lookup) is untouched; this
package supplies the four capabilities the challenge topic asks for:

  elastic_service     Elasticsearch as the retrieval core (BM25 + kNN hybrid)
  embeddings          vector generation (Bedrock Titan → local → deterministic)
  llm_provider        AWS Bedrock generation, with a demo-time fallback
  interaction_agent   drug-pair interaction + CDSCO ban detection pipeline
  fhir_service        FHIR Bundle ingestion → N×N interaction matrix
  audit_service       append-only, hash-chained audit trail in Elasticsearch

Every module degrades gracefully: a missing optional dependency or an absent
AWS credential narrows what the system can do, never crashes the portal.
"""

__version__ = '3.0.0'
