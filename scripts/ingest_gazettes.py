#!/usr/bin/env python3
"""
Ingest CDSCO gazette PDFs into the rxguard-gazettes index.
=========================================================

    .venv/bin/python scripts/ingest_gazettes.py
    .venv/bin/python scripts/ingest_gazettes.py --dir /path/to/pdfs --limit 3

What makes this more than a PDF dump: salt names and ban status are extracted
at ingest time and stored as keyword fields. That converts "is this drug
banned?" from a semantic similarity guess into an exact filtered lookup, which
is the difference between an answer a pharmacist can act on and one they cannot.

Chunking is per page with a sentence-boundary split for long pages. Gazette
notifications are already structured by page, and a banned-combination entry is
almost never split across a page break, so page-aligned chunks keep each
prohibition intact with its notification context.
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'frontend'))

from services import config, elastic_service  # noqa: E402
from services.embeddings import embed_text, active_backend  # noqa: E402

MAX_CHUNK_CHARS = 2200

# Salts that appear across the CDSCO prohibition lists. Kept explicit rather
# than NER-extracted: a curated list is auditable and produces no false drug
# names, which matters more than recall when the output is a legal claim.
KNOWN_SALTS = [
    'nimesulide', 'paracetamol', 'acetaminophen', 'phenylpropanolamine',
    'analgin', 'metamizole', 'pioglitazone', 'rosiglitazone', 'cisapride',
    'sibutramine', 'rimonabant', 'phenylbutazone', 'oxyphenbutazone',
    'chloramphenicol', 'furazolidone', 'nitrofurazone', 'nialamide',
    'dextropropoxyphene', 'ranitidine', 'domperidone', 'diclofenac',
    'ibuprofen', 'aceclofenac', 'serratiopeptidase', 'chlorzoxazone',
    'tramadol', 'codeine', 'chlorpheniramine', 'dextromethorphan',
    'ciprofloxacin', 'norfloxacin', 'ofloxacin', 'levofloxacin',
    'azithromycin', 'amoxicillin', 'ampicillin', 'cefixime', 'ceftriaxone',
    'metronidazole', 'tinidazole', 'ornidazole', 'albendazole',
    'pheniramine', 'cetirizine', 'levocetirizine', 'montelukast',
    'ambroxol', 'guaifenesin', 'bromhexine', 'terbutaline', 'salbutamol',
    'warfarin', 'aspirin', 'clopidogrel', 'atorvastatin', 'metformin',
    'glimepiride', 'omeprazole', 'pantoprazole', 'rabeprazole',
    'tizanidine', 'thiocolchicoside', 'drotaverine', 'dicyclomine',
    'caffeine', 'ergotamine', 'sumatriptan', 'tapentadol', 'gabapentin',
    'pregabalin', 'amitriptyline', 'fluoxetine', 'sertraline',
]

BAN_MARKERS = [
    (r'\b(prohibit|prohibited|prohibition)\b', 'banned'),
    (r'\bban(ned)?\b', 'banned'),
    (r'\bwithdraw(n|al)?\b', 'banned'),
    (r'\bsuspend(ed|sion)?\b', 'restricted'),
    (r'\brestrict(ed|ion)?\b', 'restricted'),
    (r'\bschedule\s+h1?\b', 'restricted'),
]

GAZETTE_ID_RE = re.compile(
    r'(?:G\.?S\.?R\.?|S\.?O\.?)\s*[\.\s]*(\d+\s*\(?[EeAa]?\)?)', re.IGNORECASE)
DATE_RE = re.compile(
    r'\b(\d{1,2})(?:st|nd|rd|th)?\s+'
    r'(January|February|March|April|May|June|July|August|September|October|'
    r'November|December),?\s+(\d{4})\b', re.IGNORECASE)

MONTHS = {m.lower(): i for i, m in enumerate(
    ['January', 'February', 'March', 'April', 'May', 'June', 'July',
     'August', 'September', 'October', 'November', 'December'], start=1)}


def extract_drugs(text):
    """Salts mentioned in this chunk, as lowercase keywords."""
    lowered = text.lower()
    return sorted({salt for salt in KNOWN_SALTS if salt in lowered})


def classify_ban_status(text):
    """
    Coarse regulatory status for the chunk.

    'unknown' is a real and common answer — most gazette pages are preamble or
    schedules. Labelling those as bans would poison every downstream verdict.
    """
    lowered = text.lower()
    for pattern, status in BAN_MARKERS:
        if re.search(pattern, lowered):
            return status
    return 'unknown'


def extract_gazette_id(text):
    match = GAZETTE_ID_RE.search(text)
    return re.sub(r'\s+', '', match.group(0)).upper() if match else None


def extract_date(text):
    match = DATE_RE.search(text)
    if not match:
        return None
    day, month, year = match.groups()
    month_num = MONTHS.get(month.lower())
    if not month_num:
        return None
    return f'{year}-{month_num:02d}-{int(day):02d}'


def split_page(text):
    """Split an over-long page on sentence boundaries, never mid-sentence."""
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]
    parts, current = [], ''
    for sentence in re.split(r'(?<=[.;])\s+', text):
        if len(current) + len(sentence) + 1 > MAX_CHUNK_CHARS and current:
            parts.append(current.strip())
            current = sentence
        else:
            current = f'{current} {sentence}'.strip()
    if current.strip():
        parts.append(current.strip())
    return parts


def ingest_pdf(path, embed=True):
    """Extract, chunk and enrich one PDF. Returns a list of index-ready docs."""
    import pymupdf

    filename = os.path.basename(path)
    docs = []
    try:
        pdf = pymupdf.open(path)
    except Exception as exc:
        print(f'  SKIP {filename}: {exc}')
        return []

    # Front-matter usually carries the notification number and date for the
    # whole document; individual pages often omit them.
    header = ''
    for page_num in range(min(2, pdf.page_count)):
        header += pdf[page_num].get_text() or ''
    doc_gazette_id = extract_gazette_id(header)
    doc_date = extract_date(header)

    for page_index in range(pdf.page_count):
        raw = pdf[page_index].get_text() or ''
        text = re.sub(r'[ \t]+', ' ', raw).strip()
        if len(text) < 60:
            continue  # scanned or blank page — nothing to retrieve

        for chunk_index, chunk in enumerate(split_page(text)):
            drugs = extract_drugs(chunk)
            docs.append({
                'chunk_id': f'{filename}:p{page_index + 1}:c{chunk_index}',
                'source_file': filename,
                'page': page_index + 1,
                'title': f'{filename} page {page_index + 1}',
                'text': chunk,
                'drugs': drugs,
                'ban_status': classify_ban_status(chunk),
                'gazette_id': extract_gazette_id(chunk) or doc_gazette_id,
                'notification_date': extract_date(chunk) or doc_date,
                'embedding': embed_text(chunk) if embed else None,
            })
    pdf.close()
    return docs


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

    total_chunks = 0
    for filename in pdfs:
        docs = ingest_pdf(os.path.join(args.dir, filename),
                          embed=not args.no_embed)
        if not docs:
            continue
        # Drop the embedding key entirely when null; ES rejects a null vector.
        for doc in docs:
            if doc.get('embedding') is None:
                doc.pop('embedding', None)
        success, errors = elastic_service.index_documents(
            config.IDX_GAZETTES, docs, id_field='chunk_id')
        flagged = sum(1 for d in docs if d['ban_status'] != 'unknown')
        with_drugs = sum(1 for d in docs if d['drugs'])
        print(f'  {filename:38s} {success:4d} chunks  '
              f'{flagged:3d} regulatory  {with_drugs:3d} with salts'
              + (f'  {len(errors)} ERRORS' if errors else ''))
        total_chunks += success

    print(f'\nTotal chunks indexed: {total_chunks}')
    print(f'Embedding backend used: {active_backend()}')
    counts = elastic_service.cluster_info()['doc_counts']
    print(f"rxguard-gazettes now holds {counts.get(config.IDX_GAZETTES)} documents")
    return 0


if __name__ == '__main__':
    sys.exit(main())
