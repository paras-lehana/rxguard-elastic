#!/usr/bin/env python3
"""
Mine banned fixed-dose combinations out of the indexed gazette corpus.
=====================================================================

    .venv/bin/python scripts/mine_banned_fdcs.py            # dry run, prints findings
    .venv/bin/python scripts/mine_banned_fdcs.py --commit   # writes to rxguard-interactions

Why this exists rather than a hand-written list: the CDSCO prohibition
notifications are tables of the form

    S. No. | Drugs Name                          | Notification No. | & Date
    1.     | Nimesulide+ Paracetamol dispersible | S.O. 2394 (E)    | 02.06.2023

Every row is a banned combination with its own statutory citation. Hand-copying
them would be slow, error-prone and unverifiable. Reading them back out of
Elasticsearch means every seeded interaction record carries the real gazette ID
and the chunk it came from, so a verdict built on it cites primary evidence
rather than someone's typing.

Only two-component combinations are emitted. Three- and four-component
prohibitions stay searchable in the gazette index, but the interaction index is
keyed on unordered pairs, and decomposing a quadruple into six pairs would
assert bans the notification does not actually make.
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'frontend'))

from services import config, elastic_service  # noqa: E402
from services.embeddings import embed_text  # noqa: E402
from services.gazette_ingest import KNOWN_SALTS  # noqa: E402

SALT_SET = {s.lower() for s in KNOWN_SALTS}

# "Nimesulide+ Paracetamol", "Naproxen IP 375mg + Esomeprazole Magnesium".
# Dosage and pharmacopoeial noise between the salts is tolerated.
_PAIR_RE = re.compile(
    r'\b([A-Za-z][a-zA-Z\-]{3,})\b[^+\n]{0,60}?\+\s*\b([A-Za-z][a-zA-Z\-]{3,})\b')

_SO_RE = re.compile(
    r'(?:S\.?\s*O\.?|G\.?\s*S\.?\s*R\.?)\s*\.?\s*(?:NO\.?\s*)?(\d+)\s*\(?\s*E\s*\)?',
    re.IGNORECASE)
_DATE_RE = re.compile(r'(\d{2})\.(\d{2})\.(\d{4})')


def _canonical_salt(token):
    """Map a table token to a known salt name, or None if it is not one."""
    lowered = re.sub(r'[^a-z\-]', '', token.lower())
    if lowered in SALT_SET:
        return lowered
    # Tolerate simple plural / adjectival endings seen in the tables.
    for salt in SALT_SET:
        if lowered.startswith(salt) and len(lowered) - len(salt) <= 2:
            return salt
    return None


def _split_rows(text):
    """
    Split a table chunk into rows.

    Extraction collapses a table into lines; a serial number like "12." reliably
    starts a new row, which is what separates one prohibition from the next.
    """
    return re.split(r'(?:(?<=\s)|^)\d{1,3}\.\s+', text)


def mine_pairs():
    """Scan every prohibition-status gazette chunk for two-component FDCs."""
    client = elastic_service.es_client()
    if client is None or not elastic_service.es_available():
        raise RuntimeError(f'Elasticsearch unreachable at {config.ES_URL}')

    res = client.search(
        index=config.IDX_GAZETTES, size=1000,
        query={'terms': {'ban_status': ['banned', 'restricted']}},
    )

    found = {}
    for hit in res['hits']['hits']:
        src = hit['_source']
        text = src.get('text') or ''

        for row in _split_rows(text):
            so = _SO_RE.search(row)

            # GUARD 1: the row must carry its own notification number.
            #
            # A genuine prohibition table row always cites the S.O./G.S.R. that
            # banned it. Rows without one are prose from explanatory passages —
            # and prose produces false bans. The row
            #     "FDC of Ibuprofen + Paracetamol is not indicated in cold"
            # says the combination is not indicated for colds, not that it is
            # prohibited; Ibuprofen + Paracetamol (Combiflam) is licensed and
            # widely sold. Emitting it as banned_fdc would tell a pharmacist to
            # refuse a legal medicine, which is a worse failure than missing a
            # real ban.
            if not so:
                continue

            # GUARD 2: exactly two components in the drug-name portion.
            #
            # Component count must be measured across the WHOLE name, not just
            # after the matched pair. The row
            #     "Dextromethorphan + Phenylephrine + Cetirizine + Paracetamol
            #      + Caffeine   S.O. 929 (E)"
            # is a five-component prohibition; matching its last two salts would
            # assert that Paracetamol + Caffeine is banned, which it is not.
            drug_portion = row[:so.start()]
            if drug_portion.count('+') != 1:
                continue

            match = _PAIR_RE.search(drug_portion)
            if not match:
                continue

            salt_a = _canonical_salt(match.group(1))
            salt_b = _canonical_salt(match.group(2))
            if not salt_a or not salt_b or salt_a == salt_b:
                continue

            date = _DATE_RE.search(row)
            pair_key = '|'.join(sorted([salt_a, salt_b]))

            record = {
                'pair_key': pair_key,
                'drug_a': salt_a, 'drug_b': salt_b,
                # Prefer the row's own citation over the document's.
                'gazette_id': (f'S.O.{so.group(1)}(E)' if so
                               else src.get('gazette_id')),
                'notification_date': (
                    f'{date.group(3)}-{date.group(2)}-{date.group(1)}'
                    if date else src.get('notification_date')),
                'chunk_id': src.get('chunk_id'),
                'source_file': src.get('source_file'),
                'row': re.sub(r'\s+', ' ', row).strip()[:220],
            }
            # First sighting wins; every surviving row carries its own citation.
            found.setdefault(pair_key, record)

    return found


def to_interaction_docs(found):
    """Turn mined rows into interaction-index records."""
    docs = []
    for pair_key, rec in sorted(found.items()):
        citation = rec['gazette_id'] or 'CDSCO prohibition notification'
        mechanism = (
            f'Prohibited fixed-dose combination. Listed in a CDSCO prohibition '
            f'notification ({citation}) issued under section 26A of the Drugs '
            f'and Cosmetics Act 1940. Source row: "{rec["row"]}".'
        )
        recommendation = (
            'Do not dispense or stock this combination. Manufacture, sale and '
            'distribution are prohibited in India. Substitute single-agent '
            'therapy or an approved alternative.'
        )
        text = (f'{rec["drug_a"]} {rec["drug_b"]} banned fixed dose combination '
                f'{citation} {mechanism}')
        docs.append({
            'pair_key': pair_key,
            'drug_a': rec['drug_a'], 'drug_b': rec['drug_b'],
            'drug_a_text': rec['drug_a'], 'drug_b_text': rec['drug_b'],
            'severity': 'banned_fdc',
            'mechanism': mechanism,
            'recommendation': recommendation,
            'evidence_level': 'regulatory',
            # The chunk id keeps this record traceable to primary evidence.
            'sources': [s for s in (citation, rec.get('source_file'),
                                    rec.get('chunk_id')) if s],
            'embedding': embed_text(text),
        })
    return docs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', action='store_true',
                        help='write the mined pairs into rxguard-interactions')
    args = parser.parse_args()

    found = mine_pairs()
    print(f'Mined {len(found)} two-component banned FDCs from the corpus\n')
    for pair_key, rec in sorted(found.items()):
        print(f'  {pair_key:44s} {str(rec["gazette_id"]):16s} {rec["source_file"]}')

    if not args.commit:
        print('\nDry run. Re-run with --commit to write these to Elasticsearch.')
        return 0

    docs = to_interaction_docs(found)

    # Curated records share the pair_key space and carry richer pharmacology, so
    # a table row must never silently replace one. Skip pairs already present.
    client = elastic_service.es_client()
    existing = set()
    try:
        res = client.search(index=config.IDX_INTERACTIONS, size=1000,
                            query={'match_all': {}})
        existing = {h['_source']['pair_key'] for h in res['hits']['hits']}
    except Exception:
        pass

    fresh = [d for d in docs if d['pair_key'] not in existing]
    skipped = len(docs) - len(fresh)
    if not fresh:
        print(f'\nNothing new to write ({skipped} already present).')
        return 0

    success, errors = elastic_service.index_documents(
        config.IDX_INTERACTIONS, fresh, id_field='pair_key')
    print(f'\nIndexed {success} new banned-FDC pairs '
          f'({skipped} skipped — already curated), '
          f'{len(errors) if errors else 0} errors')
    counts = elastic_service.cluster_info()['doc_counts']
    print(f'rxguard-interactions now holds {counts.get(config.IDX_INTERACTIONS)} pairs')
    return 0


if __name__ == '__main__':
    sys.exit(main())
