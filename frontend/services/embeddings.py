"""
Vector generation for the kNN half of hybrid retrieval.
======================================================

Three embedders, tried in order, each reporting which one actually ran so the
provenance reaches the audit trail:

  1. Bedrock Titan Embed Text v2   production path; needs AWS credentials
  2. fastembed / BAAI-bge-small    local ONNX, free, offline, no torch
  3. hashed character n-grams      dependency-free floor, never fails

Changing embedder changes the vector space, so it also requires a reindex —
`EMBED_DIM` must match the `dims` the indices were created with. Titan v2
supports 256/512/1024; the local model emits 384. Default is therefore 384
(local), and the documented AWS switch is EMBED_DIM=512 plus a re-ingest.
"""

import hashlib
import json
import logging
import math
import re

from . import config

logger = logging.getLogger(__name__)

_local_model = None
_active_backend = None

TITAN_ALLOWED_DIMS = (256, 512, 1024)


def active_backend():
    """Name of the embedder that served the most recent call."""
    return _active_backend or 'none'


# ─── 1. AWS Bedrock Titan (production) ───────────────────────────────────────

def _embed_bedrock(text):
    if not config.aws_configured():
        return None
    if config.EMBED_DIM not in TITAN_ALLOWED_DIMS:
        logger.warning(
            "EMBED_DIM=%s unsupported by Titan v2 %s — skipping Bedrock embedder",
            config.EMBED_DIM, TITAN_ALLOWED_DIMS,
        )
        return None
    try:
        import boto3
        client = boto3.client(
            'bedrock-runtime',
            region_name=config.AWS_REGION,
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        )
        res = client.invoke_model(
            modelId=config.BEDROCK_EMBED_MODEL_ID,
            body=json.dumps({
                'inputText': text[:8000],
                'dimensions': config.EMBED_DIM,
                'normalize': True,
            }),
        )
        return json.loads(res['body'].read())['embedding']
    except Exception as exc:
        logger.warning("Bedrock embedding failed: %s", exc)
        return None


# ─── 2. Local ONNX model (free, offline) ─────────────────────────────────────

def _embed_local(text):
    global _local_model
    try:
        if _local_model is None:
            from fastembed import TextEmbedding
            # bge-small-en-v1.5 → 384 dims, ~130MB ONNX, no torch dependency.
            _local_model = TextEmbedding(model_name='BAAI/bge-small-en-v1.5')
        vec = list(next(iter(_local_model.embed([text[:8000]]))))
        return [float(v) for v in vec]
    except Exception as exc:
        logger.debug("local embedder unavailable: %s", exc)
        return None


# ─── 3. Hashed character n-grams (dependency-free floor) ─────────────────────

_TOKEN_RE = re.compile(r'[a-z0-9]+')


def _embed_hashed(text):
    """
    Deterministic hashing-trick vector.

    Not semantic — it captures lexical overlap only. Its job is to keep the kNN
    leg structurally alive so the pipeline never has a dead branch; BM25 is
    doing the real lexical work in that situation anyway.
    """
    dim = config.EMBED_DIM
    vec = [0.0] * dim
    tokens = _TOKEN_RE.findall(text.lower())
    for token in tokens:
        grams = [token] + [token[i:i + 3] for i in range(max(len(token) - 2, 0))]
        for gram in grams:
            h = int(hashlib.md5(gram.encode()).hexdigest()[:8], 16)
            vec[h % dim] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    return [v / norm for v in vec] if norm else vec


# ─── Public API ──────────────────────────────────────────────────────────────

def embed_text(text):
    """
    Embed one string, preferring the most capable backend available.

    Returns a list[float] of length EMBED_DIM, or None for empty input.
    """
    global _active_backend
    if not text or not text.strip():
        return None

    for name, fn in (('bedrock-titan', _embed_bedrock),
                     ('local-bge-small', _embed_local),
                     ('hashed-ngrams', _embed_hashed)):
        vec = fn(text)
        if vec and len(vec) == config.EMBED_DIM:
            _active_backend = name
            return vec
        if vec:
            logger.warning(
                "%s returned dim %s, expected %s — index was built for the "
                "latter, so this vector is unusable",
                name, len(vec), config.EMBED_DIM,
            )
    return None


def embed_batch(texts):
    """Embed a list of strings. Kept simple: ingestion is not latency-bound."""
    return [embed_text(t) for t in texts]


def backend_report():
    """Which embedders could run right now — surfaced on /health."""
    return {
        'expected_dim': config.EMBED_DIM,
        'bedrock_titan': 'available' if config.aws_configured() else 'no credentials',
        'local_onnx': 'available' if _probe_local() else 'not installed',
        'hashed_fallback': 'always available',
        'last_used': active_backend(),
    }


def _probe_local():
    try:
        import fastembed  # noqa: F401
        return True
    except ImportError:
        return False
