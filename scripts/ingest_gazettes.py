#!/usr/bin/env python3
"""
Bulk-ingest CDSCO gazette PDFs into the rxguard-gazettes index.
==============================================================

    .venv/bin/python scripts/ingest_gazettes.py
    .venv/bin/python scripts/ingest_gazettes.py --dir /path/to/pdfs --limit 3

Extraction and enrichment live in `services/gazette_ingest.py`, shared with the
portal's live upload endpoint so both paths produce identical evidence.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'frontend'))

from services import config, elastic_service  # noqa: E402
from services.embeddings import active_backend  # noqa: E402
from services.gazette_ingest import ingest_pdf, index_chunks  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dir', default=config.GAZETTE_CORPUS_DIR,
                        help='directory of gazette PDFs')
    parser.add_argument('--limit', type=int, help='only ingest N files')
    parser.add_argument('--no-embed', action='store_true',
                        help='skip vectors (BM25-only index, much faster)')
    args = parser.parse_args()

    if not elastic_service.es_available():
        print(f'FAIL: Elasticsearch unreachable at {config.ES_URL}')
        return 1
    if not os.path.isdir(args.dir):
        print(f'FAIL: corpus directory not found: {args.dir}')
        return 1

    pdfs = sorted(f for f in os.listdir(args.dir) if f.lower().endswith('.pdf'))
    # The combined files are concatenations of the individual notifications;
    # ingesting both would double-count every prohibition in the corpus.
    pdfs = [f for f in pdfs if 'combined' not in f.lower()]
    if args.limit:
        pdfs = pdfs[:args.limit]
    if not pdfs:
        print(f'No PDFs to ingest in {args.dir}')
        return 1

    print(f'Ingesting {len(pdfs)} gazette PDFs from {args.dir}')
    print(f'Embeddings: {"disabled" if args.no_embed else "enabled"}\n')

    total = 0
    for filename in pdfs:
        docs = ingest_pdf(os.path.join(args.dir, filename),
                          embed=not args.no_embed)
        if not docs:
            continue
        success, errors = index_chunks(docs)
        flagged = sum(1 for d in docs if d['ban_status'] != 'unknown')
        with_drugs = sum(1 for d in docs if d['drugs'])
        print(f'  {filename:38s} {success:4d} chunks  '
              f'{flagged:3d} regulatory  {with_drugs:3d} with salts'
              + (f'  {len(errors)} ERRORS' if errors else ''))
        total += success

    print(f'\nTotal chunks indexed: {total}')
    print(f'Embedding backend used: {active_backend()}')
    counts = elastic_service.cluster_info()['doc_counts']
    print(f"rxguard-gazettes now holds {counts.get(config.IDX_GAZETTES)} documents")
    return 0


if __name__ == '__main__':
    sys.exit(main())
