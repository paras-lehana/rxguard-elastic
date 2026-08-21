#!/usr/bin/env python3
"""
Create the RxGuard Elasticsearch indices and seed the interaction knowledge base.
===============================================================================

Idempotent: existing indices are left alone unless --recreate is passed.

    .venv/bin/python scripts/bootstrap_elastic.py
    .venv/bin/python scripts/bootstrap_elastic.py --recreate   # drops data

The seed interaction set is small and deliberately so. It is curated, cited,
and covers the pairs the demo walks through — including the banned-FDC cases
that make the Indian regulatory angle concrete. It is a starting corpus, not a
claim to be a complete interaction database, and the code says as much rather
than implying coverage it does not have.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'frontend'))

from services import config, elastic_service  # noqa: E402
from services.embeddings import embed_text  # noqa: E402


# Severity vocabulary matches interaction_agent.SEVERITY_ORDER.
SEED_INTERACTIONS = [
    {
        'drug_a': 'nimesulide', 'drug_b': 'paracetamol',
        'severity': 'banned_fdc',
        'mechanism': (
            'Both agents are hepatotoxic through distinct pathways; nimesulide '
            'causes idiosyncratic hepatocellular injury while paracetamol '
            'produces dose-dependent centrilobular necrosis via NAPQI. The '
            'fixed-dose combination compounds hepatic risk with no established '
            'therapeutic advantage over either agent alone.'
        ),
        'recommendation': (
            'Do not dispense. This fixed-dose combination is prohibited for '
            'manufacture, sale and distribution in India. Substitute a single '
            'analgesic agent.'
        ),
        'evidence_level': 'regulatory',
        'sources': ['CDSCO FDC prohibition list', 'Drugs and Cosmetics Act s.26A'],
    },
    {
        'drug_a': 'warfarin', 'drug_b': 'nimesulide',
        'severity': 'major',
        'mechanism': (
            'NSAIDs displace warfarin from plasma protein binding sites and '
            'inhibit platelet aggregation, while COX inhibition compromises '
            'gastric mucosal protection. The combined effect raises bleeding '
            'risk substantially above either agent alone.'
        ),
        'recommendation': (
            'Avoid. If an analgesic is unavoidable, prefer paracetamol at the '
            'lowest effective dose with INR monitoring.'
        ),
        'evidence_level': 'established',
        'sources': ['pharmacology: protein binding displacement, COX inhibition'],
    },
    {
        'drug_a': 'paracetamol', 'drug_b': 'warfarin',
        'severity': 'moderate',
        'mechanism': (
            'Sustained paracetamol use potentiates warfarin anticoagulation, '
            'likely through interference with vitamin K dependent clotting '
            'factor synthesis. Occasional single doses are not implicated.'
        ),
        'recommendation': (
            'Acceptable for short-term use. Monitor INR if paracetamol is taken '
            'regularly at doses above 2g daily.'
        ),
        'evidence_level': 'established',
        'sources': ['clinical pharmacology: vitamin K pathway interference'],
    },
    {
        'drug_a': 'ciprofloxacin', 'drug_b': 'tizanidine',
        'severity': 'contraindicated',
        'mechanism': (
            'Ciprofloxacin is a potent CYP1A2 inhibitor and tizanidine is '
            'cleared almost entirely by CYP1A2. Co-administration raises '
            'tizanidine exposure roughly tenfold, producing profound hypotension '
            'and sedation.'
        ),
        'recommendation': 'Never co-administer. Choose a non-quinolone antibiotic.',
        'evidence_level': 'established',
        'sources': ['CYP1A2 inhibition, documented tenfold AUC increase'],
    },
    {
        'drug_a': 'ciprofloxacin', 'drug_b': 'warfarin',
        'severity': 'major',
        'mechanism': (
            'Ciprofloxacin inhibits CYP1A2 and CYP3A4 and displaces warfarin '
            'from albumin, reducing warfarin clearance. Concurrent suppression '
            'of vitamin K producing gut flora compounds the effect.'
        ),
        'recommendation': (
            'Avoid where an alternative antibiotic exists. If unavoidable, '
            'monitor INR every 2-3 days during therapy and for a week after, '
            'and anticipate a warfarin dose reduction.'
        ),
        'evidence_level': 'established',
        'sources': ['CYP1A2/3A4 inhibition', 'protein binding displacement',
                    'gut flora vitamin K suppression'],
    },
    {
        'drug_a': 'aspirin', 'drug_b': 'warfarin',
        'severity': 'major',
        'mechanism': (
            'Additive haemostatic impairment: warfarin suppresses vitamin K '
            'dependent clotting factor synthesis while aspirin irreversibly '
            'inhibits platelet COX-1. Aspirin also causes direct gastric '
            'mucosal injury, creating a bleeding site.'
        ),
        'recommendation': (
            'Combine only on a specific cardiological indication with gastro-'
            'protection and close INR monitoring. Never add over the counter.'
        ),
        'evidence_level': 'established',
        'sources': ['additive anticoagulant and antiplatelet effect'],
    },
    {
        'drug_a': 'tramadol', 'drug_b': 'sertraline',
        'severity': 'major',
        'mechanism': (
            'Both agents raise synaptic serotonin — tramadol through reuptake '
            'inhibition alongside its opioid action, sertraline as an SSRI. '
            'Co-administration risks serotonin syndrome, and tramadol '
            'independently lowers the seizure threshold.'
        ),
        'recommendation': (
            'Avoid. If co-prescribed, counsel the patient on serotonin syndrome '
            'signs (agitation, hyperthermia, clonus, tremor) and review urgently.'
        ),
        'evidence_level': 'established',
        'sources': ['serotonergic additive effect', 'seizure threshold reduction'],
    },
    {
        'drug_a': 'amoxicillin', 'drug_b': 'paracetamol',
        'severity': 'none',
        'mechanism': (
            'No clinically significant pharmacokinetic or pharmacodynamic '
            'interaction. Distinct metabolic and elimination pathways.'
        ),
        'recommendation': 'Safe to co-administer at standard doses.',
        'evidence_level': 'established',
        'sources': ['no shared metabolic pathway'],
    },
]


def seed_interactions(recreate=False):
    """Index the curated interaction pairs with their embeddings."""
    docs = []
    for item in SEED_INTERACTIONS:
        drug_a = item['drug_a'].lower().strip()
        drug_b = item['drug_b'].lower().strip()
        # Canonical key: one document per unordered pair.
        pair_key = '|'.join(sorted([drug_a, drug_b]))
        text = (f"{drug_a} {drug_b} {item['severity']} "
                f"{item['mechanism']} {item['recommendation']}")
        docs.append({
            'pair_key': pair_key,
            'drug_a': drug_a, 'drug_b': drug_b,
            'drug_a_text': drug_a, 'drug_b_text': drug_b,
            'severity': item['severity'],
            'mechanism': item['mechanism'],
            'recommendation': item['recommendation'],
            'evidence_level': item['evidence_level'],
            'sources': item['sources'],
            'embedding': embed_text(text),
        })
    success, errors = elastic_service.index_documents(
        config.IDX_INTERACTIONS, docs, id_field='pair_key')
    return success, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recreate', action='store_true',
                        help='drop and recreate indices (DESTROYS DATA)')
    parser.add_argument('--skip-seed', action='store_true',
                        help='create indices only, do not seed interactions')
    args = parser.parse_args()

    if not elastic_service.es_available():
        print(f'FAIL: Elasticsearch unreachable at {config.ES_URL}')
        return 1

    info = elastic_service.cluster_info()
    print(f"Cluster {info['cluster_name']} v{info['version']} "
          f"status={info['status']}")

    if args.recreate:
        print('WARNING: --recreate will delete all indexed data.')

    print('\nIndices:')
    for name, action in elastic_service.bootstrap_indices(
            recreate=args.recreate).items():
        print(f'  {name:24s} {action}')

    if not args.skip_seed:
        print('\nSeeding interaction knowledge base...')
        success, errors = seed_interactions()
        print(f'  indexed {success} pairs, {len(errors) if errors else 0} errors')
        for err in (errors or [])[:3]:
            print(f'    {err}')

    print('\nDone. Document counts:')
    for idx, count in elastic_service.cluster_info()['doc_counts'].items():
        print(f'  {idx:24s} {count}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
