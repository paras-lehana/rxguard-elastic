"""
FHIR ingestion — turn a clinical record into a screened medication list.
=======================================================================

The challenge asks for structured FHIR data driving the workflow, and there is
a real reason it matters here rather than being a box to tick. A patient rarely
knows their own full medication list; their EHR does. Reading a FHIR Bundle
straight from the record and screening every pair in it is the difference
between "check these two drugs I remembered" and "here is what your actual
prescription history contains".

Supported input: a FHIR R4 Bundle containing any mix of
  Patient
  MedicationRequest    (prescribed)
  MedicationStatement  (reported as taken)
  Medication           (referenced detail)

Medication naming in the wild is inconsistent, so names are resolved in
descending order of reliability: RxNorm coding display → any coding display →
free-text. Whatever is found is recorded with the code system it came from, so
a downstream reviewer can see whether a match rested on a coded concept or on
someone's typing.

Ingested resources land in `rxguard-fhir`; the pairwise screen then runs through
the same Elasticsearch-grounded Interaction Agent as the manual checker, so a
FHIR-sourced verdict is auditable identically to a typed one.
"""

import logging
from datetime import datetime, timezone

from . import config
from . import audit_service
from . import elastic_service
from . import interaction_agent

logger = logging.getLogger(__name__)

RXNORM_SYSTEM = 'http://www.nlm.nih.gov/research/umls/rxnorm'

MEDICATION_RESOURCES = ('MedicationRequest', 'MedicationStatement')


def _codeable_name(concept):
    """
    Best available name from a FHIR CodeableConcept, plus its provenance.

    Returns (name, system, code). RxNorm wins because it is a normalised drug
    vocabulary; a bare `text` field is accepted last because it is often a brand
    name with dosage baked in.
    """
    if not isinstance(concept, dict):
        return None, None, None

    codings = concept.get('coding') or []

    for coding in codings:
        if coding.get('system') == RXNORM_SYSTEM and coding.get('display'):
            return coding['display'], 'rxnorm', coding.get('code')

    for coding in codings:
        if coding.get('display'):
            return coding['display'], coding.get('system', 'unknown'), coding.get('code')

    if concept.get('text'):
        return concept['text'], 'text', None

    return None, None, None


def _extract_medication(resource, contained_meds):
    """
    Pull the medication name out of one MedicationRequest / MedicationStatement.

    FHIR allows the drug inline (`medicationCodeableConcept`) or by reference
    (`medicationReference`), and R5 renames both to `medication`. All three
    shapes appear in real exports, so all three are handled.
    """
    concept = resource.get('medicationCodeableConcept')
    if concept:
        return _codeable_name(concept)

    # R5 style: medication.concept / medication.reference
    med = resource.get('medication')
    if isinstance(med, dict):
        if med.get('concept'):
            return _codeable_name(med['concept'])
        ref = (med.get('reference') or {}).get('reference')
        if ref and ref in contained_meds:
            return _codeable_name(contained_meds[ref])

    ref = (resource.get('medicationReference') or {}).get('reference')
    if ref and ref in contained_meds:
        return _codeable_name(contained_meds[ref])

    return None, None, None


def parse_bundle(bundle):
    """
    Extract patient identity and medications from a FHIR Bundle.

    Returns a dict with `patient`, `medications` (one entry per resource) and
    `warnings` naming anything that could not be resolved — silently dropping an
    unparseable medication would be the most dangerous possible failure mode.
    """
    if not isinstance(bundle, dict):
        return {'error': 'FHIR payload must be a JSON object'}
    if bundle.get('resourceType') != 'Bundle':
        return {'error': f"expected resourceType 'Bundle', got "
                         f"{bundle.get('resourceType')!r}"}

    entries = bundle.get('entry') or []
    resources = [e.get('resource') for e in entries if isinstance(e, dict)
                 and isinstance(e.get('resource'), dict)]

    # Index standalone Medication resources so references can be resolved.
    contained_meds = {}
    for resource in resources:
        if resource.get('resourceType') == 'Medication':
            rid = resource.get('id')
            if rid:
                concept = resource.get('code') or {}
                contained_meds[f'Medication/{rid}'] = concept
                contained_meds[f'#{rid}'] = concept

    patient, medications, warnings = None, [], []

    for resource in resources:
        rtype = resource.get('resourceType')

        if rtype == 'Patient' and patient is None:
            name = (resource.get('name') or [{}])[0]
            given = ' '.join(name.get('given') or [])
            patient = {
                'id': resource.get('id'),
                'reference': f"Patient/{resource.get('id')}",
                'name': (f"{given} {name.get('family', '')}".strip()
                         or name.get('text') or 'Unknown'),
                'gender': resource.get('gender'),
                'birth_date': resource.get('birthDate'),
            }

        elif rtype in MEDICATION_RESOURCES:
            name, system, code = _extract_medication(resource, contained_meds)
            if not name:
                warnings.append(
                    f"{rtype}/{resource.get('id', '?')}: medication name could "
                    f"not be resolved — excluded from screening"
                )
                continue
            medications.append({
                'resource_type': rtype,
                'resource_id': resource.get('id'),
                'display': name,
                'normalized': interaction_agent.normalize_drug(name),
                'code_system': system,
                'code': code,
                'status': resource.get('status'),
                'authored_on': resource.get('authoredOn')
                               or resource.get('effectiveDateTime'),
                'patient_ref': (resource.get('subject') or {}).get('reference'),
            })

    return {
        'patient': patient,
        'medications': medications,
        'warnings': warnings,
        'resource_count': len(resources),
    }


def index_bundle(parsed):
    """
    Persist the parsed resources into `rxguard-fhir`.

    Indexing is best-effort: a failure here must not stop the clinical screen,
    but it is reported so the caller knows the record was not retained.
    """
    if not elastic_service.es_available():
        return {'indexed': 0, 'error': 'Elasticsearch unavailable'}

    now = datetime.now(timezone.utc).isoformat()
    patient_ref = (parsed.get('patient') or {}).get('reference')

    docs = []
    if parsed.get('patient'):
        docs.append({
            'resource_type': 'Patient',
            'resource_id': parsed['patient'].get('id'),
            'patient_ref': patient_ref,
            'display': parsed['patient'].get('name'),
            'medications': [],
            'raw': parsed['patient'],
            'ingested_at': now,
        })

    for med in parsed.get('medications', []):
        docs.append({
            'resource_type': med['resource_type'],
            'resource_id': med.get('resource_id'),
            'patient_ref': med.get('patient_ref') or patient_ref,
            'display': med['display'],
            'medications': [med['normalized']],
            'rxnorm_codes': [med['code']] if med.get('code_system') == 'rxnorm'
                            and med.get('code') else [],
            'raw': med,
            'ingested_at': now,
        })

    if not docs:
        return {'indexed': 0}

    try:
        success, errors = elastic_service.index_documents(config.IDX_FHIR, docs)
        return {'indexed': success, 'errors': len(errors) if errors else 0}
    except Exception as exc:
        logger.error("FHIR indexing failed: %s", exc)
        return {'indexed': 0, 'error': str(exc)}


def analyze_bundle(bundle, actor='fhir-client'):
    """
    End-to-end: parse a Bundle, index it, screen every medication pair.

    This is the workflow the challenge describes — structured clinical data in,
    explainable and audited findings out.
    """
    parsed = parse_bundle(bundle)
    if 'error' in parsed:
        return parsed

    indexing = index_bundle(parsed)

    names = [m['normalized'] for m in parsed['medications'] if m['normalized']]
    screen = interaction_agent.analyze_medication_list(names, actor=actor)

    entry = audit_service.append(
        event_type='fhir_bundle_analysis',
        subject=(parsed.get('patient') or {}).get('reference', 'unknown-patient'),
        request_payload={'medications': names,
                         'resource_count': parsed['resource_count']},
        verdict=screen['highest_severity'],
        actor=actor,
        payload={'pairs_checked': screen['pairs_checked'],
                 'banned_fdc_count': screen['banned_fdc_count']},
    )

    return {
        'patient': parsed['patient'],
        'medications': parsed['medications'],
        'warnings': parsed['warnings'],
        'fhir_indexing': indexing,
        'screen': screen,
        'audit': interaction_agent._audit_summary(entry),
    }


def sample_bundle():
    """
    A minimal FHIR R4 Bundle for demos and tests.

    Deliberately contains Nimesulide + Paracetamol: two individually legal
    molecules whose combination is a banned FDC in India. It is the case that
    demonstrates why regulatory screening has to sit alongside pharmacological
    screening.
    """
    return {
        'resourceType': 'Bundle',
        'type': 'collection',
        'entry': [
            {'resource': {
                'resourceType': 'Patient',
                'id': 'demo-patient-001',
                'name': [{'given': ['Asha'], 'family': 'Verma'}],
                'gender': 'female',
                'birthDate': '1979-04-12',
            }},
            {'resource': {
                'resourceType': 'MedicationRequest',
                'id': 'mr-001',
                'status': 'active',
                'authoredOn': '2026-08-01',
                'subject': {'reference': 'Patient/demo-patient-001'},
                'medicationCodeableConcept': {
                    'coding': [{'system': RXNORM_SYSTEM, 'code': '7238',
                                'display': 'Nimesulide'}],
                    'text': 'Nimesulide 100mg tablet',
                },
            }},
            {'resource': {
                'resourceType': 'MedicationRequest',
                'id': 'mr-002',
                'status': 'active',
                'authoredOn': '2026-08-01',
                'subject': {'reference': 'Patient/demo-patient-001'},
                'medicationCodeableConcept': {
                    'coding': [{'system': RXNORM_SYSTEM, 'code': '161',
                                'display': 'Paracetamol'}],
                    'text': 'Paracetamol 500mg tablet',
                },
            }},
            {'resource': {
                'resourceType': 'MedicationStatement',
                'id': 'ms-001',
                'status': 'active',
                'subject': {'reference': 'Patient/demo-patient-001'},
                'medicationCodeableConcept': {'text': 'Warfarin 5mg'},
            }},
        ],
    }
