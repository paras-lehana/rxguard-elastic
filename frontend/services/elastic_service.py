"""
Elasticsearch — the retrieval core of PharmAI.
=============================================

Every question the platform answers is grounded in an Elasticsearch hit. There
is no path where the LLM answers from parametric memory: retrieval happens
first, the retrieved documents are the only context supplied, and their ids
travel with the response into the audit trail.

Retrieval is hybrid. BM25 carries exact pharmaceutical tokens — salt names,
gazette numbers, "fixed dose combination" — where lexical precision is the
whole game. kNN over `dense_vector` carries paraphrase, transliteration and
misspelling, which is what real users type. The two rankings are fused with
reciprocal rank fusion in-process, deliberately rather than via the `rrf`
retriever, so the whole system runs on the free basic licence with no trial
clock that could expire mid-judging.

Index layout
    rxguard-gazettes      CDSCO gazette chunks, ban status per salt
    rxguard-interactions  curated drug-pair interaction knowledge base
    rxguard-fhir          ingested FHIR Patient / MedicationRequest resources
    rxguard-audit         append-only hash-chained decision log
"""

import logging
from datetime import datetime, timezone

from . import config

logger = logging.getLogger(__name__)

_client = None


# ─── Client ──────────────────────────────────────────────────────────────────

def es_client():
    """Lazily build the singleton Elasticsearch client, or None if unavailable."""
    global _client
    if _client is not None:
        return _client
    try:
        from elasticsearch import Elasticsearch
    except ImportError:
        logger.warning("elasticsearch client not installed — retrieval disabled")
        return None
    try:
        _client = Elasticsearch(
            config.ES_URL,
            basic_auth=(config.ES_USER, config.ES_PASSWORD),
            request_timeout=30,
            retry_on_timeout=True,
            max_retries=3,
        )
        return _client
    except Exception as exc:
        logger.error("Elasticsearch client init failed: %s", exc)
        return None


def es_available():
    """True when the cluster answers a ping."""
    client = es_client()
    if client is None:
        return False
    try:
        return bool(client.ping())
    except Exception:
        return False


def cluster_info():
    """Health summary for the /health endpoint and the pitch's live-proof panel."""
    client = es_client()
    if client is None:
        return {'available': False, 'reason': 'client not installed'}
    try:
        health = client.cluster.health()
        counts = {}
        for idx in (config.IDX_GAZETTES, config.IDX_INTERACTIONS,
                    config.IDX_FHIR, config.IDX_AUDIT):
            try:
                counts[idx] = client.count(index=idx)['count']
            except Exception:
                counts[idx] = None
        return {
            'available': True,
            'cluster_name': health.get('cluster_name'),
            'status': health.get('status'),
            'nodes': health.get('number_of_nodes'),
            'version': client.info()['version']['number'],
            'doc_counts': counts,
        }
    except Exception as exc:
        return {'available': False, 'reason': str(exc)}


# ─── Index definitions ───────────────────────────────────────────────────────

def _dense_vector():
    """kNN-searchable vector field. Cosine matches normalised embeddings."""
    return {
        'type': 'dense_vector',
        'dims': config.EMBED_DIM,
        'index': True,
        'similarity': 'cosine',
    }


# A custom analyzer matters more than it looks: pharmaceutical text is full of
# hyphenated salts and dosage tokens that the standard analyzer fragments badly.
_ANALYSIS = {
    'analyzer': {
        'pharma_text': {
            'type': 'custom',
            'tokenizer': 'standard',
            'filter': ['lowercase', 'asciifolding', 'pharma_synonyms', 'english_stop'],
        }
    },
    'filter': {
        'english_stop': {'type': 'stop', 'stopwords': '_english_'},
        # Judges see immediately that domain knowledge is encoded in the index,
        # not bolted on in prompts.
        'pharma_synonyms': {
            'type': 'synonym',
            'lenient': True,
            'synonyms': [
                'fdc, fixed dose combination, fixed-dose combination',
                'banned, prohibited, withdrawn',
                'cdsco, central drugs standard control organisation',
                'paracetamol, acetaminophen',
                'nimesulide, nimulid',
                'contraindicated, contra-indicated',
            ],
        },
    },
}

INDEX_DEFS = {
    config.IDX_GAZETTES: {
        'settings': {'number_of_shards': 1, 'number_of_replicas': 0,
                     'analysis': _ANALYSIS},
        'mappings': {'properties': {
            'gazette_id': {'type': 'keyword'},
            'title': {'type': 'text', 'analyzer': 'pharma_text'},
            'source_file': {'type': 'keyword'},
            'page': {'type': 'integer'},
            'chunk_id': {'type': 'keyword'},
            'text': {'type': 'text', 'analyzer': 'pharma_text'},
            # Salts extracted at ingest time, so a ban lookup is a keyword
            # filter rather than a full-text guess.
            'drugs': {'type': 'keyword'},
            'ban_status': {'type': 'keyword'},
            # Whether ban_status came from this chunk's own wording or was
            # inherited from the document being a prohibition list. Surfaced in
            # explanations so a verdict never overstates its own evidence.
            'ban_status_source': {'type': 'keyword'},
            'notification_date': {'type': 'date',
                                  'format': 'yyyy-MM-dd||yyyy||epoch_millis'},
            'embedding': _dense_vector(),
            'ingested_at': {'type': 'date'},
        }},
    },

    config.IDX_INTERACTIONS: {
        'settings': {'number_of_shards': 1, 'number_of_replicas': 0,
                     'analysis': _ANALYSIS},
        'mappings': {'properties': {
            # Sorted "drug_a|drug_b" so a pair has exactly one canonical key.
            'pair_key': {'type': 'keyword'},
            'drug_a': {'type': 'keyword'},
            'drug_b': {'type': 'keyword'},
            'drug_a_text': {'type': 'text', 'analyzer': 'pharma_text'},
            'drug_b_text': {'type': 'text', 'analyzer': 'pharma_text'},
            'severity': {'type': 'keyword'},
            'mechanism': {'type': 'text', 'analyzer': 'pharma_text'},
            'recommendation': {'type': 'text', 'analyzer': 'pharma_text'},
            'evidence_level': {'type': 'keyword'},
            'sources': {'type': 'keyword'},
            'embedding': _dense_vector(),
            'ingested_at': {'type': 'date'},
        }},
    },

    config.IDX_FHIR: {
        'settings': {'number_of_shards': 1, 'number_of_replicas': 0},
        'mappings': {'properties': {
            'resource_type': {'type': 'keyword'},
            'resource_id': {'type': 'keyword'},
            'patient_ref': {'type': 'keyword'},
            'medications': {'type': 'keyword'},
            'display': {'type': 'text'},
            'rxnorm_codes': {'type': 'keyword'},
            # Kept verbatim for provenance but not indexed — FHIR bundles are
            # deep and mapping them wholesale would explode the field count.
            'raw': {'type': 'object', 'enabled': False},
            'ingested_at': {'type': 'date'},
        }},
    },

    config.IDX_AUDIT: {
        'settings': {'number_of_shards': 1, 'number_of_replicas': 0},
        'mappings': {'properties': {
            'seq': {'type': 'long'},
            'entry_hash': {'type': 'keyword'},
            'prev_hash': {'type': 'keyword'},
            'event_type': {'type': 'keyword'},
            'actor': {'type': 'keyword'},
            'timestamp': {'type': 'date'},
            'request_digest': {'type': 'keyword'},
            'llm_provider': {'type': 'keyword'},
            'llm_model': {'type': 'keyword'},
            'prompt_sha256': {'type': 'keyword'},
            'retrieved_doc_ids': {'type': 'keyword'},
            'verdict': {'type': 'keyword'},
            'subject': {'type': 'keyword'},
            'payload': {'type': 'object', 'enabled': False},
        }},
    },
}


def bootstrap_indices(recreate=False):
    """Create every index if absent. Returns {index: action} for reporting."""
    client = es_client()
    if client is None:
        raise RuntimeError('Elasticsearch client unavailable')

    results = {}
    for name, body in INDEX_DEFS.items():
        exists = client.indices.exists(index=name)
        if exists and recreate:
            client.indices.delete(index=name)
            exists = False
            results[name] = 'recreated'
        if not exists:
            client.indices.create(index=name, **body)
            results.setdefault(name, 'created')
        else:
            results[name] = 'exists'
    return results


# ─── Retrieval ───────────────────────────────────────────────────────────────

def _rrf_fuse(rankings, k=None):
    """
    Reciprocal rank fusion.

    Each ranking is an ordered list of (doc_id, source_dict). A document's score
    is the weighted sum of 1/(k + rank) across the rankings it appears in, which
    rewards documents both retrievers agree on without needing the two score
    scales to be comparable.
    """
    k = k or config.RRF_K
    scored = {}
    for weight, ranking in rankings:
        for rank, (doc_id, source) in enumerate(ranking, start=1):
            entry = scored.setdefault(doc_id, {'score': 0.0, 'source': source,
                                               'ranks': {}})
            entry['score'] += weight * (1.0 / (k + rank))
            entry['ranks'][len(entry['ranks'])] = rank
    fused = [
        {'_id': doc_id, '_score': data['score'], **data['source']}
        for doc_id, data in scored.items()
    ]
    fused.sort(key=lambda d: d['_score'], reverse=True)
    return fused


def _bm25_search(index, query, size, extra_filter=None, fields=None):
    client = es_client()
    fields = fields or ['text^2', 'title^3', 'drugs^4']
    must = [{'multi_match': {
        'query': query,
        'fields': fields,
        'type': 'best_fields',
        'fuzziness': 'AUTO',
    }}]
    body = {'query': {'bool': {'must': must}}}
    if extra_filter:
        body['query']['bool']['filter'] = extra_filter
    res = client.search(index=index, size=size, **body)
    return [(h['_id'], h['_source']) for h in res['hits']['hits']]


def _knn_search(index, vector, size, extra_filter=None):
    client = es_client()
    knn = {
        'field': 'embedding',
        'query_vector': vector,
        'k': size,
        # Oversample the candidate pool so kNN recall is not capped by k.
        'num_candidates': max(size * 10, 100),
    }
    if extra_filter:
        knn['filter'] = extra_filter
    res = client.search(index=index, size=size, knn=knn)
    return [(h['_id'], h['_source']) for h in res['hits']['hits']]


def hybrid_search(index, query, size=8, extra_filter=None, fields=None,
                  query_vector=None):
    """
    Hybrid BM25 + kNN retrieval with RRF fusion.

    Returns a ranked list of documents, each carrying `_id` and the fused
    `_score`. If embeddings are unavailable the call silently degrades to
    BM25-only, which is why the lexical half is never optional.
    """
    if not es_available():
        return []

    rankings = []
    try:
        bm25 = _bm25_search(index, query, size, extra_filter, fields)
        rankings.append((config.HYBRID_BM25_WEIGHT, bm25))
    except Exception as exc:
        logger.warning("BM25 leg failed on %s: %s", index, exc)

    if query_vector is None:
        from .embeddings import embed_text
        query_vector = embed_text(query)

    if query_vector:
        try:
            knn = _knn_search(index, query_vector, size, extra_filter)
            rankings.append((config.HYBRID_KNN_WEIGHT, knn))
        except Exception as exc:
            logger.warning("kNN leg failed on %s: %s", index, exc)

    if not rankings:
        return []
    return _rrf_fuse(rankings)[:size]


def find_interaction_pair(drug_a, drug_b):
    """
    Exact-pair lookup in the curated interaction knowledge base.

    Canonical key ordering means one lookup covers both argument orders.
    """
    if not es_available():
        return None
    client = es_client()
    pair_key = '|'.join(sorted([drug_a.lower().strip(), drug_b.lower().strip()]))
    try:
        res = client.search(
            index=config.IDX_INTERACTIONS, size=1,
            query={'term': {'pair_key': pair_key}},
        )
        hits = res['hits']['hits']
        return {'_id': hits[0]['_id'], **hits[0]['_source']} if hits else None
    except Exception as exc:
        logger.warning("interaction pair lookup failed: %s", exc)
        return None


def ban_status_for(drug, size=5):
    """
    Gazette evidence for a single salt.

    Filtered on the `drugs` keyword so this is a precise regulatory lookup, not
    a similarity guess — the distinction that makes the answer defensible.
    """
    if not es_available():
        return []
    return hybrid_search(
        config.IDX_GAZETTES,
        query=drug,
        size=size,
        extra_filter=[{'term': {'drugs': drug.lower().strip()}}],
    ) or hybrid_search(config.IDX_GAZETTES, query=drug, size=size)


def index_documents(index, docs, id_field=None):
    """Bulk-index documents. Returns (success_count, errors)."""
    client = es_client()
    if client is None:
        raise RuntimeError('Elasticsearch client unavailable')
    from elasticsearch.helpers import bulk

    now = datetime.now(timezone.utc).isoformat()
    actions = []
    for doc in docs:
        doc.setdefault('ingested_at', now)
        action = {'_index': index, '_source': doc}
        if id_field and doc.get(id_field):
            action['_id'] = doc[id_field]
        actions.append(action)

    success, errors = bulk(client, actions, raise_on_error=False,
                           stats_only=False)
    # Refresh so a caller that immediately counts or searches sees these docs.
    # Ingestion here is batch and low-frequency, so the cost is irrelevant and
    # the alternative is a confusing "indexed 5, count 0".
    try:
        client.indices.refresh(index=index)
    except Exception as exc:
        logger.debug("refresh after bulk failed on %s: %s", index, exc)
    return success, errors
