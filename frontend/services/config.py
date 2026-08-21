"""
RxGuard configuration — single source of truth for every service module.
=======================================================================

Reads from the environment so that flipping the LLM provider from the demo
fallback to real AWS Bedrock is a config change, not a code change.
"""

import os

# ─── Elasticsearch (retrieval core) ──────────────────────────────────────────
ES_URL = os.getenv('ES_URL', 'http://rxguard-es:9200')
ES_USER = os.getenv('ES_USER', 'elastic')
ES_PASSWORD = os.getenv('ELASTIC_PASSWORD', '')

IDX_GAZETTES = 'rxguard-gazettes'
IDX_INTERACTIONS = 'rxguard-interactions'
IDX_FHIR = 'rxguard-fhir'
IDX_AUDIT = 'rxguard-audit'

# Dimensionality of the dense_vector fields. Fixed at index-creation time, so
# every embedder must project into this space — see embeddings.EMBED_DIM.
EMBED_DIM = int(os.getenv('EMBED_DIM', '384'))

# Hybrid retrieval weights. BM25 is the dependable half (exact salt names,
# gazette numbers); kNN catches paraphrase and misspelling. Fused in-process
# with reciprocal rank fusion so we stay inside the free basic licence.
HYBRID_BM25_WEIGHT = float(os.getenv('HYBRID_BM25_WEIGHT', '0.5'))
HYBRID_KNN_WEIGHT = float(os.getenv('HYBRID_KNN_WEIGHT', '0.5'))
RRF_K = int(os.getenv('RRF_K', '60'))

# ─── AWS Bedrock (generation + embeddings, production path) ──────────────────
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

# Nova Lite: cheapest Bedrock model that reliably honours a forced-JSON schema.
BEDROCK_MODEL_ID = os.getenv('BEDROCK_MODEL_ID', 'amazon.nova-lite-v1:0')
BEDROCK_EMBED_MODEL_ID = os.getenv('BEDROCK_EMBED_MODEL_ID', 'amazon.titan-embed-text-v2:0')

# Optional: the pre-existing Bedrock Knowledge Base / Kendra RAG backend.
# When set, gazette grounding can be delegated to it instead of local Elastic.
BEDROCK_KB_ID = os.getenv('BEDROCK_KB_ID', '')


_aws_usable_cache = None


def aws_credentials_present():
    """True when credentials are set. Says nothing about whether they work."""
    return bool(AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY)


def aws_configured(force_recheck=False):
    """
    True when a real Bedrock call could actually succeed.

    Presence of keys is not proof they are valid — stale or rotated credentials
    are the common case, and trusting them means every request pays a doomed
    Bedrock round-trip before falling back. So the first call validates once via
    STS and the answer is cached for the process lifetime.
    """
    global _aws_usable_cache
    if not aws_credentials_present():
        return False
    if _aws_usable_cache is not None and not force_recheck:
        return _aws_usable_cache

    try:
        import boto3
        from botocore.config import Config as BotoConfig
        sts = boto3.client(
            'sts', region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            config=BotoConfig(retries={'max_attempts': 1},
                              connect_timeout=5, read_timeout=5),
        )
        sts.get_caller_identity()
        _aws_usable_cache = True
    except Exception:
        _aws_usable_cache = False
    return _aws_usable_cache


# ─── Demo-time LLM fallback ──────────────────────────────────────────────────
# The platform's own LLM proxy. Used ONLY so the public demo answers while no
# AWS credential is present. Never presented as an AWS capability: responses
# carry provider metadata all the way to the UI and the audit trail.
PLATFORM_LLM_URL = os.getenv('PLATFORM_LLM_URL',
                             'https://llm.lehana.in/smk/pharmai')
PLATFORM_LLM_KEY = os.getenv('PLATFORM_LLM_KEY', '')

# 'auto'    → Bedrock when credentials exist, else the demo fallback
# 'bedrock' → Bedrock only; fail loudly if unavailable (use for judging runs)
# 'platform'→ demo fallback only
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'auto').lower()

# ─── Sarvam AI (retained: Indic voice, no AWS equivalent) ────────────────────
# The challenge permits external tools "where necessary" provided they do not
# replace Elastic or AWS. Sarvam is confined to speech and OCR — AWS Transcribe
# and Polly have no Hindi/regional parity for medical vocabulary. All reasoning
# and all retrieval moved off Sarvam.
SARVAM_API_KEY = os.getenv('SARVAM_API_KEY', '')
SARVAM_BASE = 'https://api.sarvam.ai'

# ─── Corpus ──────────────────────────────────────────────────────────────────
GAZETTE_CORPUS_DIR = os.getenv(
    'GAZETTE_CORPUS_DIR', '/root/ideas/pharmai/rag-api/data'
)

REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '45'))
