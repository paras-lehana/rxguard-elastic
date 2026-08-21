"""
Immutable audit trail — append-only, hash-chained, stored in Elasticsearch.
==========================================================================

Every clinical verdict the platform issues is recorded here before it reaches
the user. Healthcare and insurance decisions need to be reconstructable months
later: which documents grounded this answer, which model produced it, has
anything been altered since.

"Immutable" is engineered, not asserted:

  Append-only    Writes use `op_type=create` with the sequence number as the
                 document id, so an existing entry can never be overwritten by
                 a later write — a duplicate id is a hard failure, not an
                 update.
  Hash-chained   Each entry stores the SHA-256 of its own canonical content
                 plus the hash of its predecessor. Editing any historical entry
                 breaks every hash after it.
  Verifiable     `verify_chain()` recomputes the whole chain and names the exact
                 sequence number where it first diverges. Tamper-evident is the
                 honest claim: Elasticsearch cannot forbid a privileged
                 operator from editing a document, but it cannot hide it either.

What is recorded is deliberately provenance, not prose: the digest of the input,
the ids of the retrieved documents, the model and provider that generated the
verdict, and the SHA-256 of the exact prompt.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone

from . import config
from .elastic_service import es_client, es_available

logger = logging.getLogger(__name__)

GENESIS_HASH = '0' * 64
MAX_SEQ_RETRIES = 5


def _canonical(payload):
    """Byte-stable serialization — the hash must not depend on key order."""
    return json.dumps(payload, sort_keys=True, separators=(',', ':'),
                      default=str)


def _entry_hash(entry):
    """
    SHA-256 over the chained fields only.

    `payload` is excluded on purpose: it is a non-indexed convenience copy of
    the response, and including free-form model prose would make the chain
    fragile to harmless formatting differences. Everything the chain commits to
    — the input digest, the retrieved ids, the model, the prompt hash, the
    verdict — is here.
    """
    return hashlib.sha256(_canonical({
        'seq': entry['seq'],
        'prev_hash': entry['prev_hash'],
        'event_type': entry['event_type'],
        'actor': entry['actor'],
        'timestamp': entry['timestamp'],
        'subject': entry['subject'],
        'request_digest': entry['request_digest'],
        'llm_provider': entry['llm_provider'],
        'llm_model': entry['llm_model'],
        'prompt_sha256': entry['prompt_sha256'],
        'retrieved_doc_ids': entry['retrieved_doc_ids'],
        'verdict': entry['verdict'],
    }).encode()).hexdigest()


def _head():
    """Current chain head as (seq, entry_hash). (-1, GENESIS) when empty."""
    client = es_client()
    try:
        res = client.search(
            index=config.IDX_AUDIT, size=1,
            query={'match_all': {}},
            sort=[{'seq': {'order': 'desc'}}],
        )
        hits = res['hits']['hits']
        if not hits:
            return -1, GENESIS_HASH
        return hits[0]['_source']['seq'], hits[0]['_source']['entry_hash']
    except Exception:
        return -1, GENESIS_HASH


def append(event_type, subject, request_payload, verdict=None, llm_meta=None,
           retrieved_doc_ids=None, actor='anonymous', payload=None):
    """
    Append one entry. Returns the written entry, or None if Elastic is down.

    A failed audit write never blocks the clinical answer — losing the answer
    is worse than losing the log line — but it is logged loudly so the gap is
    visible rather than silent.
    """
    if not es_available():
        logger.warning("audit append skipped: Elasticsearch unavailable")
        return None

    client = es_client()
    llm_meta = llm_meta or {}

    for attempt in range(MAX_SEQ_RETRIES):
        prev_seq, prev_hash = _head()
        entry = {
            'seq': prev_seq + 1,
            'prev_hash': prev_hash,
            'event_type': event_type,
            'actor': actor,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'subject': subject,
            'request_digest': hashlib.sha256(
                _canonical(request_payload).encode()).hexdigest(),
            'llm_provider': llm_meta.get('provider', 'none'),
            'llm_model': llm_meta.get('model', 'none'),
            'prompt_sha256': llm_meta.get('prompt_sha256', ''),
            'retrieved_doc_ids': sorted(retrieved_doc_ids or []),
            'verdict': verdict or 'none',
            'payload': payload or {},
        }
        entry['entry_hash'] = _entry_hash(entry)

        try:
            # op_type=create is what makes this append-only: if another request
            # already claimed this seq, the write is rejected rather than
            # clobbering it, and we retry against the new head.
            client.create(index=config.IDX_AUDIT,
                          id=f"{entry['seq']:012d}", document=entry,
                          refresh='wait_for')
            return entry
        except Exception as exc:
            if attempt == MAX_SEQ_RETRIES - 1:
                logger.error("audit append failed after %s attempts: %s",
                             MAX_SEQ_RETRIES, exc)
                return None
            logger.debug("audit seq %s contended, retrying", entry['seq'])
    return None


def verify_chain(limit=10000):
    """
    Recompute the entire chain.

    Returns a report naming the first divergent sequence number, if any. This is
    the endpoint an auditor actually runs.
    """
    if not es_available():
        return {'verified': False, 'reason': 'Elasticsearch unavailable'}

    client = es_client()
    try:
        res = client.search(
            index=config.IDX_AUDIT, size=limit,
            query={'match_all': {}},
            sort=[{'seq': {'order': 'asc'}}],
        )
    except Exception as exc:
        return {'verified': False, 'reason': str(exc)}

    entries = [h['_source'] for h in res['hits']['hits']]
    if not entries:
        return {'verified': True, 'entries': 0,
                'note': 'empty chain is trivially valid'}

    expected_prev = GENESIS_HASH
    for position, entry in enumerate(entries):
        if entry['seq'] != position:
            return {'verified': False, 'entries': len(entries),
                    'broken_at_seq': entry['seq'],
                    'reason': f"sequence gap: expected {position}, found {entry['seq']}"}
        if entry['prev_hash'] != expected_prev:
            return {'verified': False, 'entries': len(entries),
                    'broken_at_seq': entry['seq'],
                    'reason': 'prev_hash does not match predecessor'}
        if _entry_hash(entry) != entry['entry_hash']:
            return {'verified': False, 'entries': len(entries),
                    'broken_at_seq': entry['seq'],
                    'reason': 'entry content does not match its stored hash'}
        expected_prev = entry['entry_hash']

    return {
        'verified': True,
        'entries': len(entries),
        'head_seq': entries[-1]['seq'],
        'head_hash': entries[-1]['entry_hash'],
        'algorithm': 'SHA-256 linked chain, append-only via ES op_type=create',
    }


def recent(size=20):
    """Most recent entries, newest first — powers the UI audit panel."""
    if not es_available():
        return []
    client = es_client()
    try:
        res = client.search(
            index=config.IDX_AUDIT, size=size,
            query={'match_all': {}},
            sort=[{'seq': {'order': 'desc'}}],
        )
        return [h['_source'] for h in res['hits']['hits']]
    except Exception as exc:
        logger.warning("audit fetch failed: %s", exc)
        return []
