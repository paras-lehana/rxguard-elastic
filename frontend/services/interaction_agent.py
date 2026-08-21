"""
Interaction Agent — drug interaction and banned-FDC detection.
==============================================================

The clinical core of PharmAI, and the part that answers the challenge topic.

Most interaction checkers answer one question: do these two molecules interact
pharmacologically? In India that misses the more urgent one. A fixed-dose
combination can be *legally banned* by CDSCO — Nimesulide + Paracetamol is the
canonical case — while each molecule alone is perfectly legal and the pair
raises no textbook interaction flag. A pharmacist stocking it is committing a
licensing offence, and no international interaction database will tell them so.

So every pair goes through both lenses:

  1. Normalise    brand and dosage noise stripped to a salt name
  2. Retrieve     Elasticsearch, three ways — curated pair knowledge base,
                  per-salt gazette evidence, and hybrid search for the pair as
                  a combination
  3. Reason       the LLM classifies severity and explains mechanism, given
                  ONLY the retrieved passages
  4. Audit        verdict, evidence ids and model provenance are hash-chained
                  before the answer is returned

Severity ladder, most severe first:
  banned_fdc        prohibited combination under Indian law — regulatory, not
                    merely clinical, and therefore ranked above everything else
  contraindicated   never co-administer
  major / moderate / minor
  none
  unknown           no evidence retrieved; say so rather than guess
"""

import logging
import re

from . import config
from . import audit_service
from . import elastic_service
from . import llm_provider

logger = logging.getLogger(__name__)

SEVERITY_ORDER = ['banned_fdc', 'contraindicated', 'major', 'moderate',
                  'minor', 'none', 'unknown']

# Dosage strengths, pack forms and the usual brand decorations. Stripping these
# is what lets "Nimulid 100mg tablet" match a gazette entry for "nimesulide".
_NOISE = re.compile(
    r'\b(\d+\s*(mg|mcg|ml|g|iu|%)|tablet|tablets|tab|capsule|caps|cap|syrup|'
    r'suspension|injection|inj|cream|ointment|gel|drops|spray|sr|xr|er|dt|'
    r'plus|forte|max)\b',
    re.IGNORECASE,
)

# Brand → salt aliases for the Indian market.
#
# This map is not cosmetic. Patients and pharmacists type brand names, but
# gazette notifications and the interaction knowledge base are keyed on salts.
# Without this step "Nimulid + Paracetamol" silently fails to match the banned
# fixed-dose combination that "Nimesulide + Paracetamol" matches instantly —
# the verdict degrades from banned_fdc to unknown for the exact input a real
# user is most likely to supply. Index-time synonyms fix the free-text legs but
# cannot fix an exact keyword lookup, so the mapping has to happen here.
BRAND_TO_SALT = {
    'nimulid': 'nimesulide',
    'nise': 'nimesulide',
    'crocin': 'paracetamol',
    'calpol': 'paracetamol',
    'dolo': 'paracetamol',
    'metacin': 'paracetamol',
    'combiflam': 'ibuprofen paracetamol',
    'brufen': 'ibuprofen',
    'voveran': 'diclofenac',
    'zerodol': 'aceclofenac',
    'augmentin': 'amoxicillin',
    'mox': 'amoxicillin',
    'azithral': 'azithromycin',
    'cifran': 'ciprofloxacin',
    'ciplox': 'ciprofloxacin',
    'norflox': 'norfloxacin',
    'zanocin': 'ofloxacin',
    'flagyl': 'metronidazole',
    'metrogyl': 'metronidazole',
    'pan': 'pantoprazole',
    'pantocid': 'pantoprazole',
    'omez': 'omeprazole',
    'rantac': 'ranitidine',
    'zinetac': 'ranitidine',
    'domstal': 'domperidone',
    'sinarest': 'paracetamol chlorpheniramine phenylephrine',
    'vicks': 'camphor menthol',
    'disprin': 'aspirin',
    'ecosprin': 'aspirin',
    'glycomet': 'metformin',
    'amaryl': 'glimepiride',
    'lipitor': 'atorvastatin',
    'atorva': 'atorvastatin',
    'sompraz': 'esomeprazole',
    'tizan': 'tizanidine',
    'sirdalud': 'tizanidine',
    'ultracet': 'tramadol paracetamol',
    'tramazac': 'tramadol',
    'lyrica': 'pregabalin',
    'neurontin': 'gabapentin',
    'warf': 'warfarin',
    'sofarin': 'warfarin',
}

SYSTEM_PROMPT = """You are PharmAI, a pharmacovigilance analyst for the Indian market.

You are given retrieved evidence: CDSCO gazette passages and curated interaction
records. Classify the interaction between the two drugs using ONLY that evidence.

Rules you must not break:
- Ground every claim in the supplied evidence. Cite the evidence ids you used.
- If the evidence shows this pair is a banned or prohibited fixed-dose
  combination in India, severity is "banned_fdc" and is_banned_fdc is true.
  This holds even if only SOME dosage forms are named in the notification: a
  pharmacist needs to know the combination is restricted, and the dosage-form
  detail belongs in regulatory_note, not in a downgraded severity.
- Reserve "unknown" for genuinely empty evidence. If you can state a mechanism,
  a regulatory status or a clinical effect, you have enough to grade severity —
  choose the grade the evidence supports rather than defaulting to "unknown".
- If the evidence is insufficient, set severity "unknown" and say what is
  missing. Never fill a gap from memory.
- Never invent a gazette number, date or citation.

Return a single JSON object:
{
  "severity": "banned_fdc|contraindicated|major|moderate|minor|none|unknown",
  "is_banned_fdc": true|false,
  "mechanism": "how the interaction works, or why none exists",
  "clinical_effect": "what happens to the patient",
  "recommendation": "concrete action for a pharmacist or prescriber",
  "regulatory_note": "Indian regulatory status, or empty string",
  "evidence_ids": ["ids of the evidence you actually used"],
  "confidence": "high|medium|low"
}"""


def normalize_drug(name):
    """
    Reduce a user-typed medicine string to a comparable salt token.

    Strips dosage and pack-form noise, then resolves brand names to their salt
    via BRAND_TO_SALT so that keyword lookups against the gazette and
    interaction indices hit. "Nimulid 100mg tablet" → "nimesulide".
    """
    if not name:
        return ''
    cleaned = _NOISE.sub(' ', name.lower())
    cleaned = re.sub(r'[^a-z0-9\s\-]', ' ', cleaned)
    # Drop bare strengths ("Crocin 650"). _NOISE only catches digits glued to a
    # unit, and a stray number left in the token breaks the exact pair lookup.
    cleaned = re.sub(r'\b\d+\b', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    if not cleaned:
        return ''

    # Whole-string brand match first — the common, unambiguous case.
    if cleaned in BRAND_TO_SALT:
        return BRAND_TO_SALT[cleaned]

    # Otherwise map any token that is a known brand, leaving salts untouched.
    # A multi-word alias (combination brands) expands in place.
    tokens = [BRAND_TO_SALT.get(token, token) for token in cleaned.split()]
    return ' '.join(dict.fromkeys(' '.join(tokens).split()))


def _gather_evidence(drug_a, drug_b):
    """
    Retrieve from Elasticsearch, three complementary ways.

    Returns (evidence list, doc ids). Each item carries the id the LLM is asked
    to cite, so a citation can be resolved back to a real document.
    """
    evidence = []

    pair = elastic_service.find_interaction_pair(drug_a, drug_b)
    if pair:
        evidence.append({
            'id': f"interaction:{pair['_id']}",
            'kind': 'curated_interaction',
            'severity': pair.get('severity'),
            'mechanism': pair.get('mechanism'),
            'recommendation': pair.get('recommendation'),
            'evidence_level': pair.get('evidence_level'),
            'sources': pair.get('sources', []),
        })

    # Per-salt regulatory status: is either molecule itself restricted?
    for drug in (drug_a, drug_b):
        for hit in elastic_service.ban_status_for(drug, size=3):
            evidence.append({
                'id': f"gazette:{hit['_id']}",
                'kind': 'gazette_single_drug',
                'drug': drug,
                'gazette_id': hit.get('gazette_id'),
                'ban_status': hit.get('ban_status'),
                'notification_date': hit.get('notification_date'),
                'source_file': hit.get('source_file'),
                'page': hit.get('page'),
                'text': (hit.get('text') or '')[:1200],
                'score': round(hit.get('_score', 0), 5),
            })

    # The combination itself — this is the leg that catches banned FDCs, which
    # per-drug lookups structurally cannot find.
    for hit in elastic_service.hybrid_search(
        config.IDX_GAZETTES,
        query=f'{drug_a} {drug_b} fixed dose combination prohibited',
        size=4,
    ):
        evidence.append({
            'id': f"gazette:{hit['_id']}",
            'kind': 'gazette_combination',
            'gazette_id': hit.get('gazette_id'),
            'ban_status': hit.get('ban_status'),
            'notification_date': hit.get('notification_date'),
            'source_file': hit.get('source_file'),
            'page': hit.get('page'),
            'text': (hit.get('text') or '')[:1200],
            'score': round(hit.get('_score', 0), 5),
        })

    # De-duplicate: a document can legitimately surface in more than one leg.
    seen, unique = set(), []
    for item in evidence:
        if item['id'] not in seen:
            seen.add(item['id'])
            unique.append(item)
    return unique, [item['id'] for item in unique]


def _render_evidence(evidence):
    """Format retrieved documents as the LLM's only source of truth."""
    if not evidence:
        return 'NO EVIDENCE RETRIEVED.'
    lines = []
    for item in evidence:
        head = f"[{item['id']}] ({item['kind']})"
        body = ' | '.join(
            f'{k}={v}' for k, v in item.items()
            if k not in ('id', 'kind', 'text') and v not in (None, '', [])
        )
        lines.append(f'{head} {body}')
        if item.get('text'):
            lines.append(f"    excerpt: {item['text']}")
    return '\n'.join(lines)


def detect_interaction(drug_a_raw, drug_b_raw, actor='anonymous'):
    """
    Full detection pipeline for one drug pair.

    Always returns a verdict dict. When retrieval or generation fails the
    severity is "unknown" with the reason stated — a pharmacovigilance tool that
    guesses under failure is worse than one that admits ignorance.
    """
    drug_a = normalize_drug(drug_a_raw)
    drug_b = normalize_drug(drug_b_raw)

    result = {
        'drug_a': drug_a_raw, 'drug_b': drug_b_raw,
        'normalized': {'drug_a': drug_a, 'drug_b': drug_b},
        'severity': 'unknown',
        'is_banned_fdc': False,
        'evidence': [],
        'retrieval': {},
        'llm': {},
        'audit': {},
    }

    if not drug_a or not drug_b:
        result['error'] = 'Both drug names are required.'
        return result

    if not elastic_service.es_available():
        result['error'] = ('Elasticsearch is unavailable — PharmAI will not '
                           'issue a verdict without retrieved evidence.')
        return result

    evidence, doc_ids = _gather_evidence(drug_a, drug_b)
    result['evidence'] = evidence
    result['retrieval'] = {
        'engine': 'elasticsearch',
        'strategy': 'hybrid BM25 + kNN, reciprocal rank fusion',
        'indices': [config.IDX_INTERACTIONS, config.IDX_GAZETTES],
        'evidence_count': len(evidence),
    }

    if not evidence:
        result['mechanism'] = ''
        result['recommendation'] = (
            'No regulatory or interaction evidence found for this pair in the '
            'indexed corpus. Absence of evidence is not evidence of safety — '
            'consult a pharmacist.'
        )
        result['confidence'] = 'low'
        entry = audit_service.append(
            event_type='interaction_check', subject=f'{drug_a}+{drug_b}',
            request_payload={'drug_a': drug_a, 'drug_b': drug_b},
            verdict='unknown', retrieved_doc_ids=[], actor=actor,
        )
        result['audit'] = _audit_summary(entry)
        return result

    user_prompt = (
        f'Drug A: {drug_a_raw}  (normalised: {drug_a})\n'
        f'Drug B: {drug_b_raw}  (normalised: {drug_b})\n\n'
        f'RETRIEVED EVIDENCE:\n{_render_evidence(evidence)}'
    )

    try:
        generation = llm_provider.generate(
            SYSTEM_PROMPT, user_prompt, json_mode=True, max_tokens=1400,
            temperature=0.1,
        )
        parsed = generation.json() or {}
        result['llm'] = generation.as_dict()
    except Exception as exc:
        logger.error("interaction generation failed: %s", exc)
        result['error'] = f'Reasoning layer unavailable: {exc}'
        parsed = {}

    severity = str(parsed.get('severity', 'unknown')).lower()
    result['severity'] = severity if severity in SEVERITY_ORDER else 'unknown'
    result['is_banned_fdc'] = bool(parsed.get('is_banned_fdc'))
    # A banned FDC outranks any clinical grading the model chose.
    if result['is_banned_fdc']:
        result['severity'] = 'banned_fdc'

    result['mechanism'] = parsed.get('mechanism', '')
    result['clinical_effect'] = parsed.get('clinical_effect', '')
    result['recommendation'] = parsed.get('recommendation', '')
    result['regulatory_note'] = parsed.get('regulatory_note', '')
    result['confidence'] = parsed.get('confidence', 'low')
    # Only citations that resolve to a document we actually retrieved.
    result['cited_evidence_ids'] = [
        eid for eid in parsed.get('evidence_ids', []) if eid in doc_ids
    ]

    entry = audit_service.append(
        event_type='interaction_check',
        subject=f'{drug_a}+{drug_b}',
        request_payload={'drug_a': drug_a, 'drug_b': drug_b},
        verdict=result['severity'],
        llm_meta=result['llm'],
        retrieved_doc_ids=doc_ids,
        actor=actor,
        payload={'recommendation': result['recommendation']},
    )
    result['audit'] = _audit_summary(entry)
    return result


def analyze_medication_list(medications, actor='anonymous'):
    """
    Full N×N pairwise screen of a medication list.

    This is what a real prescription review needs and what a two-box interaction
    checker cannot do: the danger in polypharmacy is usually a pair the patient
    never thought to ask about.
    """
    meds = [m for m in dict.fromkeys(
        normalize_drug(m) for m in medications if m and m.strip()) if m]

    findings, worst = [], 'none'
    for i in range(len(meds)):
        for j in range(i + 1, len(meds)):
            verdict = detect_interaction(meds[i], meds[j], actor=actor)
            findings.append(verdict)
            if SEVERITY_ORDER.index(verdict['severity']) < SEVERITY_ORDER.index(worst):
                worst = verdict['severity']

    banned = [f for f in findings if f['is_banned_fdc']]
    entry = audit_service.append(
        event_type='medication_list_screen',
        subject=','.join(meds),
        request_payload={'medications': meds},
        verdict=worst,
        retrieved_doc_ids=sorted({
            e['id'] for f in findings for e in f.get('evidence', [])
        }),
        actor=actor,
        payload={'pairs_checked': len(findings)},
    )

    return {
        'medications': meds,
        'pairs_checked': len(findings),
        'highest_severity': worst,
        'banned_fdc_count': len(banned),
        'findings': sorted(
            findings, key=lambda f: SEVERITY_ORDER.index(f['severity'])),
        'audit': _audit_summary(entry),
    }


def _audit_summary(entry):
    """The audit fields the UI shows so a user can see the trail exists."""
    if not entry:
        return {'recorded': False,
                'reason': 'audit index unavailable — verdict not logged'}
    return {
        'recorded': True,
        'seq': entry['seq'],
        'entry_hash': entry['entry_hash'],
        'prev_hash': entry['prev_hash'],
        'timestamp': entry['timestamp'],
    }


# ─── Bedrock tool specifications ─────────────────────────────────────────────
# Exposed to the Converse tool-use loop so that, on the AWS path, the model
# chooses its own retrieval strategy instead of following the fixed sequence
# above. Same Elasticsearch functions underneath either way.

TOOL_SPECS = [
    {'toolSpec': {
        'name': 'search_gazettes',
        'description': ('Hybrid search over indexed CDSCO gazette notifications. '
                        'Use for regulatory ban status and FDC prohibitions.'),
        'inputSchema': {'json': {
            'type': 'object',
            'properties': {
                'query': {'type': 'string', 'description': 'search text'},
                'size': {'type': 'integer', 'description': 'max hits, default 5'},
            },
            'required': ['query'],
        }},
    }},
    {'toolSpec': {
        'name': 'lookup_interaction_pair',
        'description': 'Exact lookup in the curated drug-pair interaction knowledge base.',
        'inputSchema': {'json': {
            'type': 'object',
            'properties': {
                'drug_a': {'type': 'string'},
                'drug_b': {'type': 'string'},
            },
            'required': ['drug_a', 'drug_b'],
        }},
    }},
]


def tool_implementations():
    """Callables backing TOOL_SPECS, all reading from Elasticsearch."""
    def search_gazettes(query, size=5):
        hits = elastic_service.hybrid_search(config.IDX_GAZETTES, query,
                                             size=size)
        return {'hits': [{
            '_id': h['_id'], 'gazette_id': h.get('gazette_id'),
            'ban_status': h.get('ban_status'), 'page': h.get('page'),
            'text': (h.get('text') or '')[:800],
        } for h in hits]}

    def lookup_interaction_pair(drug_a, drug_b):
        pair = elastic_service.find_interaction_pair(
            normalize_drug(drug_a), normalize_drug(drug_b))
        return pair or {'found': False}

    return {'search_gazettes': search_gazettes,
            'lookup_interaction_pair': lookup_interaction_pair}
