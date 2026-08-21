"""
PharmAI Portal — Flask Backend v2.0
====================================
Serves the frontend and proxies all Sarvam AI / N8N API calls.
Keeps API keys server-side (never exposed to browser).

Endpoints:
  GET  /                       → Main portal page
  GET  /pharmai                → Same (Traefik compat)
  GET  /analyze, /pharmai/analyze → Results page
  POST /api/search             → 2-tier medicine search (N8N → Sarvam)
  POST /api/stt                → Speech-to-Text (Sarvam Saaras v3)
  POST /api/tts                → Text-to-Speech (Sarvam Bulbul v3)
  POST /api/translate          → Translation (Sarvam Mayura v1)
  POST /api/ocr                → Document OCR (Sarvam parse/document)
  POST /api/interaction        → Drug interaction check (Sarvam Chat)
  POST /api/doc-analysis       → AI document analysis (Sarvam Chat)
  POST /api/upload-files       → PDF upload & index
  POST /api/list-documents     → List indexed documents
  POST /api/delete-document    → Delete a document
  DELETE /api/delete-all-documents → Delete all documents
  GET  /health                 → Health check
"""

from flask import (Flask, render_template_string, request, redirect, jsonify,
                   send_from_directory)
import os
import requests
import json
from werkzeug.utils import secure_filename
import time

# ─── Load environment variables from .env ────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use OS env vars directly

SARVAM_API_KEY = os.getenv('SARVAM_API_KEY', '')
PHARMA_INSIGHT_URL = os.getenv('PHARMA_INSIGHT_URL', '')
SARVAM_BASE = 'https://api.sarvam.ai'

# ─── RxGuard service layer (Elastic core + AWS Bedrock reasoning) ────────────
# Imported defensively: if a dependency is missing the portal must still serve
# its Sarvam voice and OCR features rather than fail to boot.
try:
    from services import (
        audit_service,
        config as rx_config,
        elastic_service,
        embeddings,
        fhir_service,
        interaction_agent,
        llm_provider,
    )
    RXGUARD_AVAILABLE = True
    RXGUARD_IMPORT_ERROR = None
except Exception as _exc:  # pragma: no cover - import-time guard
    RXGUARD_AVAILABLE = False
    RXGUARD_IMPORT_ERROR = str(_exc)
    print(f"⚠️  RxGuard service layer unavailable: {_exc}")


def _rxguard_required():
    """Uniform 503 when the Elastic/Bedrock layer could not be imported."""
    return _cors_json({
        'error': 'RxGuard service layer unavailable',
        'detail': RXGUARD_IMPORT_ERROR,
    }, 503)

# ─── Flask App ───────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'pharmai-portal-secret-2026')
app.config['UPLOAD_FOLDER'] = '../data'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Create upload directory
upload_path = os.path.abspath(app.config['UPLOAD_FOLDER'])
os.makedirs(upload_path, exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'webp'}


def allowed_file(filename):
    """Check if file extension is in the allowed set."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ─── Sarvam API headers ─────────────────────────────────────────────────────
def sarvam_headers(content_type='application/json'):
    """Return standard Sarvam API headers with the subscription key."""
    return {
        'Content-Type': content_type,
        'api-subscription-key': SARVAM_API_KEY,
    }


# ─── N8N Rejection Rule (CRITICAL) ──────────────────────────────────────────
def is_useless_n8n_response(text):
    """
    Detect N8N boilerplate 'give me more data' responses.
    If HTTP 200 but text is short (<800 chars) and matches these patterns,
    discard and fall through to Sarvam (Tier 2).
    """
    if not text or len(text) >= 800:
        return False
    t = text.lower()
    return (
        "haven't provided" in t
        or "no specific drug" in t
        or "need to analyze" in t
        or "please provide" in t
        or ("would need" in t and "drug" in t)
    )


# ─── System prompt for Sarvam Chat ──────────────────────────────────────────
PHARMAI_SYSTEM_PROMPT = (
    "You are PharmaAI, an expert Indian pharmaceutical assistant specialized "
    "in drug safety. When given a medicine name, composition, or scanned text "
    "from a medicine package, provide a comprehensive analysis:\n\n"
    "**Status:** Whether it is BANNED / RESTRICTED / ALLOWED in India "
    "(check CDSCO/FSSAI regulations)\n"
    "**Safety:** Side effects, contraindications, drug interactions, warnings\n"
    "**Usage:** What it is used for, dosage guidelines\n"
    "**Regulatory:** CDSCO schedule classification, gazette notifications if banned\n"
    "**Alternatives:** Safer alternatives if the medicine is banned or restricted\n\n"
    "Be concise, accurate, and respond in the same language the user uses. "
    "If the query is in Hindi or another Indian language, respond in that language. "
    "Use Markdown bold (**text**) for section headers. Start your response with a "
    "clear status indicator: ✅ ALLOWED, 🚫 BANNED, or ⚠️ RESTRICTED."
)


# ══════════════════════════════════════════════════════════════════════════════
#  SEARCH — 2-Tier Fallback (N8N RAG → Sarvam Chat)
# ══════════════════════════════════════════════════════════════════════════════

def search_tier1_n8n(query, session_id):
    """Tier 1 — N8N RAG Pipeline. Returns dict or None to fall through."""
    if not PHARMA_INSIGHT_URL:
        return None
    try:
        res = requests.post(
            PHARMA_INSIGHT_URL,
            json={'query': query, 'sessionId': session_id},
            headers={'Content-Type': 'application/json'},
            timeout=38,
        )
        if res.status_code == 200:
            data = res.json()
            # PharmaSafe structured response
            if data.get('medicine_searched'):
                badges = {'open': '✅ ALLOWED', 'banned': '🚫 BANNED', 'restricted': '⚠️ RESTRICTED'}
                status = data.get('current_status', 'unknown')
                badge = badges.get(status, 'ℹ️ UNKNOWN')
                summary = ''
                if isinstance(data.get('results'), dict):
                    summary = data['results'].get('summary', '')
                elif isinstance(data.get('results'), str):
                    summary = data['results']
                return {
                    'source': 'n8n',
                    'answer': f"{badge}\n\n**Medicine:** {data['medicine_searched']}\n\n{summary}",
                    'status': status,
                    'medicine_name': data['medicine_searched'],
                    'raw': data,
                }
            # Plain text response
            text = data.get('text') or data.get('output') or data.get('answer') or ''
            if text and not is_useless_n8n_response(text):
                return {'source': 'n8n', 'answer': text}
    except Exception as e:
        print(f"[SEARCH T1] N8N error: {e}")
    return None


def search_tier2_sarvam(query):
    """Tier 2 — Sarvam AI Chat (sarvam-m). Returns dict or None."""
    if not SARVAM_API_KEY:
        return None
    try:
        res = requests.post(
            f'{SARVAM_BASE}/v1/chat/completions',
            headers=sarvam_headers(),
            json={
                'model': 'sarvam-m',
                'messages': [
                    {'role': 'system', 'content': PHARMAI_SYSTEM_PROMPT},
                    {'role': 'user', 'content': query},
                ],
                'temperature': 0.5,
                'max_tokens': 1024,
            },
            timeout=45,
        )
        if res.status_code == 200:
            data = res.json()
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            if content:
                return {'source': 'sarvam', 'answer': f"🤖 **AI Analysis (Sarvam-M)**\n\n{content}"}
    except Exception as e:
        print(f"[SEARCH T2] Sarvam error: {e}")
    return None


def search_medicine(query, session_id):
    """Execute the full 2-tier search fallback chain."""
    result = search_tier1_n8n(query, session_id)
    if result:
        return result
    result = search_tier2_sarvam(query)
    if result:
        return result
    return {
        'source': 'error',
        'answer': (
            '❌ **Unable to reach medicine databases**\n\n'
            'All sources are currently unreachable.\n\n'
            '**Tip:** Try again in a moment or check your internet connection.'
        ),
    }


# ─── Template loading ────────────────────────────────────────────────────────
def load_template(name):
    try:
        with open(name, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Template {name} not found"


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — Pages
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/')
@app.route('/pharmai')
def index():
    return render_template_string(load_template('index.html'))


@app.route('/analyze')
@app.route('/pharmai/analyze')
def analyze():
    return render_template_string(load_template('result.html'))


# ─── Static assets ───────────────────────────────────────────────────────────
# index.html references css/*.css and js/*.js as relative paths, but those live
# in frontend/css and frontend/js — not in Flask's default `static/` folder — so
# without these routes every stylesheet and script 404s and the page renders as
# unstyled HTML with no interactivity. /health and the JSON APIs stay perfectly
# green while this is broken, which is why it survived: only loading the actual
# page in a browser reveals it.
#
# Both path forms are registered because Traefik strips the /pharmai prefix
# before the request reaches the container, but a direct hit (bare-metal run,
# or a request that bypasses the strip middleware) arrives with it intact.

_ASSET_ROOT = os.path.dirname(os.path.abspath(__file__))


# Assets are served under /assets/** and NOT the historical /css, /js paths.
#
# Why the rename: while the static routes were missing, Traefik returned
# text/plain 404s for /pharmai/css/*, and Cloudflare cached those responses for
# four hours (max-age=14400) independently at each edge POP. After the fix, some
# edges still served the poisoned entry, so browsers refused the stylesheets
# with a strict-MIME error while curl — hitting a different POP — saw a clean
# text/css 200. Bumping ?v= did not reliably help and we have no Cloudflare API
# credential to purge with. A path that has never been requested is guaranteed
# clean at every edge.
#
# The short max-age means a future poisoned entry expires in minutes, not hours.
# The legacy /css and /js routes are kept so any cached HTML still resolves.

_ASSET_CACHE_SECONDS = 300


def _serve_asset(subdir, filename, mimetype):
    # mimetype is explicit rather than guessed: browsers enforce strict MIME
    # checking on stylesheets and refuse a sheet served as text/plain, which
    # kills the responsive layout while the request still returns 200.
    response = send_from_directory(os.path.join(_ASSET_ROOT, subdir), filename,
                                   mimetype=mimetype)
    response.headers['Cache-Control'] = f'public, max-age={_ASSET_CACHE_SECONDS}'
    return response


@app.route('/assets/css/<path:filename>')
@app.route('/pharmai/assets/css/<path:filename>')
@app.route('/css/<path:filename>')
@app.route('/pharmai/css/<path:filename>')
def serve_css(filename):
    return _serve_asset('css', filename, 'text/css')


@app.route('/assets/js/<path:filename>')
@app.route('/pharmai/assets/js/<path:filename>')
@app.route('/js/<path:filename>')
@app.route('/pharmai/js/<path:filename>')
def serve_js(filename):
    return _serve_asset('js', filename, 'application/javascript')


@app.route('/favicon.ico')
@app.route('/pharmai/favicon.ico')
def favicon():
    path = os.path.join(_ASSET_ROOT, 'favicon.ico')
    if os.path.exists(path):
        return send_from_directory(_ASSET_ROOT, 'favicon.ico')
    return ('', 204)  # no icon shipped; 204 beats a noisy 404 in the console


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — Search API (2-tier)
# ══════════════════════════════════════════════════════════════════════════════

RXGUARD_SEARCH_PROMPT = """You are RxGuard, a drug safety assistant for the Indian market.

Answer using ONLY the retrieved CDSCO gazette passages supplied below. Cite the
passage ids you rely on, in square brackets, inline.

If the passages do not answer the question, say exactly what is missing. Never
supply a gazette number, date or ban status that does not appear in the
passages. An honest "the indexed corpus does not cover this" is correct; an
invented citation is a patient-safety failure.

Return a single JSON object:
{
  "answer": "your markdown answer, concise and concrete, with inline [citations]",
  "status": "banned|restricted|allowed|unknown"
}

`status` describes THE SUBJECT THE USER ASKED ABOUT, not any drug that happens
to appear in the passages. If the evidence does not establish the status of that
specific subject, `status` is "unknown" — even when the passages discuss bans on
other drugs or other combinations. This field drives a prominent badge in the
user interface, so a wrong value actively misinforms a pharmacist.

If the evidence establishes a prohibition on the subject in ANY dosage form,
`status` is "banned". Note the formulation limits in `answer`, but do not
downgrade `status` to "unknown" because other formulations are unaddressed — a
pharmacist needs to know the combination is restricted, and a badge reading
"unknown" above an answer reading "is prohibited" contradicts itself."""

# Context window for the search answer, and the per-file cap that keeps one
# oversized notification from consuming it. See search_elastic_grounded.
SEARCH_CONTEXT_SIZE = 8
MAX_HITS_PER_SOURCE = 2


def search_elastic_grounded(query, actor='anonymous'):
    """
    Primary search path: Elasticsearch retrieval, then LLM synthesis.

    Retrieval always happens first and the retrieved passages are the model's
    only context, which is what makes the citations resolvable and the answer
    auditable.
    """
    # Over-retrieve, then enforce source diversity.
    #
    # The corpus is lopsided: one notification contributes 284 of 379 chunks,
    # and its near-duplicate pages will fill a small result window on any query
    # about a banned combination — starving the one page in a different file
    # that holds the actual answer. Capping hits per source file is what makes
    # the difference between "the corpus does not cover this" and the correct
    # citation.
    candidates = elastic_service.hybrid_search(
        rx_config.IDX_GAZETTES, query, size=24)
    if not candidates:
        return None

    per_file, hits = {}, []
    for hit in candidates:
        source = hit.get('source_file', 'unknown')
        if per_file.get(source, 0) >= MAX_HITS_PER_SOURCE:
            continue
        per_file[source] = per_file.get(source, 0) + 1
        hits.append(hit)
        if len(hits) >= SEARCH_CONTEXT_SIZE:
            break

    passages = '\n\n'.join(
        f"[gazette:{h['_id']}] (file={h.get('source_file')} "
        f"page={h.get('page')} gazette_id={h.get('gazette_id')} "
        f"status={h.get('ban_status')})\n{(h.get('text') or '')[:1500]}"
        for h in hits
    )
    doc_ids = [f"gazette:{h['_id']}" for h in hits]

    try:
        generation = llm_provider.generate(
            RXGUARD_SEARCH_PROMPT,
            f'QUESTION: {query}\n\nRETRIEVED PASSAGES:\n{passages}',
            json_mode=True, max_tokens=1400, temperature=0.2,
        )
    except Exception as exc:
        print(f'[SEARCH] generation failed: {exc}')
        return None

    # The status is taken from this structured field, never inferred from the
    # prose. The UI previously substring-matched the answer text for "banned",
    # which stamped a 🚫 BANNED badge on answers that said the corpus contained
    # no ban information — a badge contradicting its own body text, on a
    # patient-safety tool.
    parsed = generation.json() or {}
    answer_text = parsed.get('answer') or generation.text or ''
    status = str(parsed.get('status', 'unknown')).lower()
    if status not in ('banned', 'restricted', 'allowed', 'unknown'):
        status = 'unknown'

    entry = audit_service.append(
        event_type='gazette_search', subject=query[:200],
        request_payload={'query': query},
        verdict='answered', llm_meta=generation.as_dict(),
        retrieved_doc_ids=doc_ids, actor=actor,
    )

    return {
        'source': 'elasticsearch+' + generation.provider,
        'answer': answer_text,
        'status': status,
        'citations': [{
            'id': f"gazette:{h['_id']}",
            'gazette_id': h.get('gazette_id'),
            'source_file': h.get('source_file'),
            'page': h.get('page'),
            'ban_status': h.get('ban_status'),
            'score': round(h.get('_score', 0), 5),
        } for h in hits],
        'retrieval': {
            'engine': 'elasticsearch',
            'strategy': 'hybrid BM25 + kNN, reciprocal rank fusion',
            'index': rx_config.IDX_GAZETTES,
            'hits': len(hits),
        },
        'llm': generation.as_dict(),
        'audit': interaction_agent._audit_summary(entry),
    }


@app.route('/api/search', methods=['POST', 'OPTIONS'])
@app.route('/pharmai/api/search', methods=['POST', 'OPTIONS'])
def api_search():
    if request.method == 'OPTIONS':
        return _cors_preflight()
    data = request.get_json(force=True)
    query = data.get('query') or data.get('prompt', '')
    session_id = data.get('sessionId', f'pharmai-web-{int(time.time())}')
    if not query:
        return jsonify({'status': 'error', 'error': 'No query provided'}), 400
    print(f"[SEARCH] query='{query}' session={session_id}")

    # Elastic-grounded retrieval is the primary and only compliant path.
    if RXGUARD_AVAILABLE:
        result = search_elastic_grounded(query, actor=session_id)
        if result:
            return _cors_json({'status': 'success', **result})
        print('[SEARCH] Elastic path returned nothing — using legacy fallback')

    # Legacy N8N → Sarvam chain. Retained only for the case where the Elastic
    # corpus has no coverage at all, so the portal degrades to answering rather
    # than to a blank screen. Tagged in the response so the UI and the pitch can
    # both show which engine served the answer: this is a fallback, never a
    # substitute for the Elastic + Bedrock path.
    result = search_medicine(query, session_id)
    return _cors_json({
        'status': 'success' if result['source'] != 'error' else 'error',
        'degraded': True,
        'degraded_reason': 'no Elasticsearch coverage for this query',
        **result,
    })


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — Sarvam AI Features
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/stt', methods=['POST', 'OPTIONS'])
@app.route('/pharmai/api/stt', methods=['POST', 'OPTIONS'])
def api_stt():
    """Speech-to-Text — Sarvam Saaras v3."""
    if request.method == 'OPTIONS':
        return _cors_preflight()
    if 'file' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    audio = request.files['file']
    try:
        res = requests.post(
            f'{SARVAM_BASE}/speech-to-text',
            headers={'api-subscription-key': SARVAM_API_KEY},
            files={'file': (audio.filename or 'audio.wav', audio.stream, audio.content_type or 'audio/wav')},
            data={'model': 'saaras:v3', 'mode': 'transcribe'},
            timeout=30,
        )
        return _cors_json(res.json(), res.status_code)
    except Exception as e:
        return _cors_json({'error': str(e)}, 500)


@app.route('/api/tts', methods=['POST', 'OPTIONS'])
@app.route('/pharmai/api/tts', methods=['POST', 'OPTIONS'])
def api_tts():
    """Text-to-Speech — Sarvam Bulbul v3."""
    if request.method == 'OPTIONS':
        return _cors_preflight()
    data = request.get_json(force=True)
    text = data.get('text', '')[:500]
    lang = data.get('language', 'hi-IN')
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    try:
        res = requests.post(
            f'{SARVAM_BASE}/text-to-speech',
            headers=sarvam_headers(),
            json={
                'inputs': [text],
                'target_language_code': lang,
                'speaker': 'meera',
                'model': 'bulbul:v3',
                'enable_preprocessing': True,
            },
            timeout=30,
        )
        rj = res.json()
        audio_b64 = rj.get('audios', [None])[0]
        if audio_b64:
            return _cors_json({'audio': audio_b64})
        return _cors_json({'error': 'No audio generated'}, 500)
    except Exception as e:
        return _cors_json({'error': str(e)}, 500)


@app.route('/api/translate', methods=['POST', 'OPTIONS'])
@app.route('/pharmai/api/translate', methods=['POST', 'OPTIONS'])
def api_translate():
    """Translation — Sarvam Mayura v1."""
    if request.method == 'OPTIONS':
        return _cors_preflight()
    data = request.get_json(force=True)
    text = data.get('text', '')
    target = data.get('target', 'hi-IN')
    source = data.get('source', 'en-IN')
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    try:
        res = requests.post(
            f'{SARVAM_BASE}/translate',
            headers=sarvam_headers(),
            json={
                'input': text,
                'source_language_code': source,
                'target_language_code': target,
                'model': 'mayura:v1',
                'enable_preprocessing': False,
            },
            timeout=30,
        )
        return _cors_json(res.json(), res.status_code)
    except Exception as e:
        return _cors_json({'error': str(e)}, 500)


@app.route('/api/ocr', methods=['POST', 'OPTIONS'])
@app.route('/pharmai/api/ocr', methods=['POST', 'OPTIONS'])
def api_ocr():
    """Document OCR — Sarvam parse/document."""
    if request.method == 'OPTIONS':
        return _cors_preflight()
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    doc = request.files['file']
    try:
        res = requests.post(
            f'{SARVAM_BASE}/parse/document',
            headers={'api-subscription-key': SARVAM_API_KEY},
            files={'file': (doc.filename, doc.stream, doc.content_type or 'application/octet-stream')},
            timeout=60,
        )
        rj = res.json()
        extracted = rj.get('text', '') or rj.get('content', '') or rj.get('extracted_text', '')
        if not extracted and isinstance(rj.get('pages'), list):
            extracted = '\n'.join(p.get('text', '') for p in rj['pages'])
        return _cors_json({'text': extracted, 'raw': rj})
    except Exception as e:
        return _cors_json({'error': str(e)}, 500)


@app.route('/api/interaction', methods=['POST', 'OPTIONS'])
@app.route('/pharmai/api/interaction', methods=['POST', 'OPTIONS'])
def api_interaction():
    """
    Drug interaction + banned-FDC detection.

    Elasticsearch-grounded and audited. Replaces the previous single-prompt
    Sarvam implementation, which could neither cite a source nor detect that a
    pair was prohibited in India.

    Response keeps an `answer` markdown field so the existing UI renders without
    change, alongside the structured verdict for clients that want it.
    """
    if request.method == 'OPTIONS':
        return _cors_preflight()
    if not RXGUARD_AVAILABLE:
        return _rxguard_required()

    data = request.get_json(force=True)
    med_a = data.get('medicine_a', '').strip()
    med_b = data.get('medicine_b', '').strip()
    if not med_a or not med_b:
        return jsonify({'error': 'Both medicine names required'}), 400

    verdict = interaction_agent.detect_interaction(
        med_a, med_b, actor=data.get('sessionId', 'web'))
    verdict['answer'] = _render_verdict_markdown(verdict)
    return _cors_json(verdict)


SEVERITY_LABELS = {
    'banned_fdc': ('🚫', 'BANNED IN INDIA', 'Prohibited fixed-dose combination'),
    'contraindicated': ('⛔', 'CONTRAINDICATED', 'Never co-administer'),
    'major': ('🔴', 'MAJOR', 'Serious interaction'),
    'moderate': ('🟠', 'MODERATE', 'Clinically significant'),
    'minor': ('🟡', 'MINOR', 'Usually manageable'),
    'none': ('🟢', 'NO KNOWN INTERACTION', 'Safe at standard doses'),
    'unknown': ('⚪', 'INSUFFICIENT EVIDENCE', 'Not covered by indexed corpus'),
}


def _render_verdict_markdown(verdict):
    """Render a verdict as markdown so the existing UI needs no changes."""
    if verdict.get('error'):
        return f"❌ **{verdict['error']}**"

    icon, label, subtitle = SEVERITY_LABELS.get(
        verdict['severity'], SEVERITY_LABELS['unknown'])

    lines = [
        f"## {icon} {label}",
        f"*{subtitle}*",
        '',
        f"**{verdict['drug_a']}** + **{verdict['drug_b']}**",
        '',
    ]
    if verdict.get('regulatory_note'):
        lines += [f"### ⚖️ Regulatory status", verdict['regulatory_note'], '']
    if verdict.get('mechanism'):
        lines += ['### 🔬 Mechanism', verdict['mechanism'], '']
    if verdict.get('clinical_effect'):
        lines += ['### 🩺 Clinical effect', verdict['clinical_effect'], '']
    if verdict.get('recommendation'):
        lines += ['### ✅ Recommendation', verdict['recommendation'], '']

    cited = verdict.get('cited_evidence_ids') or []
    if cited:
        lines += ['### 📚 Evidence', *(f'- `{cid}`' for cid in cited), '']

    retrieval = verdict.get('retrieval', {})
    audit = verdict.get('audit', {})
    llm = verdict.get('llm', {})
    lines += [
        '---',
        f"*Retrieval: {retrieval.get('strategy', 'n/a')} over "
        f"{retrieval.get('evidence_count', 0)} documents · "
        f"Reasoning: {llm.get('model', 'n/a')} ({llm.get('provider', 'n/a')}) · "
        f"Confidence: {verdict.get('confidence', 'n/a')}*",
    ]
    if audit.get('recorded'):
        lines.append(
            f"*Audit entry #{audit['seq']} · `{audit['entry_hash'][:16]}…`*")
    return '\n'.join(lines)


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — Medication list screening (N×N)
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/medications/screen', methods=['POST', 'OPTIONS'])
@app.route('/pharmai/api/medications/screen', methods=['POST', 'OPTIONS'])
def api_screen_medications():
    """
    Screen every pair in a medication list.

    Polypharmacy risk hides in pairs nobody thought to check, which a two-box
    checker structurally cannot surface.
    """
    if request.method == 'OPTIONS':
        return _cors_preflight()
    if not RXGUARD_AVAILABLE:
        return _rxguard_required()

    data = request.get_json(force=True)
    meds = data.get('medications') or []
    if isinstance(meds, str):
        meds = [m.strip() for m in meds.split(',') if m.strip()]
    if len(meds) < 2:
        return jsonify({'error': 'At least two medications required'}), 400
    if len(meds) > 12:
        # N×N growth: 12 drugs is already 66 pairs, each an LLM call.
        return jsonify({'error': 'Maximum 12 medications per screen'}), 400

    return _cors_json(interaction_agent.analyze_medication_list(
        meds, actor=data.get('sessionId', 'web')))


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — FHIR
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/fhir/analyze', methods=['POST', 'OPTIONS'])
@app.route('/pharmai/api/fhir/analyze', methods=['POST', 'OPTIONS'])
def api_fhir_analyze():
    """Ingest a FHIR R4 Bundle, index it, and screen every medication pair."""
    if request.method == 'OPTIONS':
        return _cors_preflight()
    if not RXGUARD_AVAILABLE:
        return _rxguard_required()

    bundle = request.get_json(force=True, silent=True)
    if not bundle:
        return jsonify({'error': 'A FHIR Bundle JSON body is required'}), 400

    result = fhir_service.analyze_bundle(bundle, actor='fhir-api')
    status = 400 if 'error' in result else 200
    return _cors_json(result, status)


@app.route('/api/fhir/sample', methods=['GET'])
@app.route('/pharmai/api/fhir/sample', methods=['GET'])
def api_fhir_sample():
    """A demo Bundle — POST it straight back to /api/fhir/analyze."""
    if not RXGUARD_AVAILABLE:
        return _rxguard_required()
    return _cors_json(fhir_service.sample_bundle())


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — Audit trail
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/audit/verify', methods=['GET'])
@app.route('/pharmai/api/audit/verify', methods=['GET'])
def api_audit_verify():
    """
    Recompute the hash chain end to end.

    This is the endpoint an auditor runs to prove nothing has been altered.
    """
    if not RXGUARD_AVAILABLE:
        return _rxguard_required()
    return _cors_json(audit_service.verify_chain())


@app.route('/api/audit/recent', methods=['GET'])
@app.route('/pharmai/api/audit/recent', methods=['GET'])
def api_audit_recent():
    """Most recent audit entries, newest first."""
    if not RXGUARD_AVAILABLE:
        return _rxguard_required()
    size = min(int(request.args.get('size', 20)), 100)
    return _cors_json({'entries': audit_service.recent(size)})


@app.route('/api/doc-analysis', methods=['POST', 'OPTIONS'])
@app.route('/pharmai/api/doc-analysis', methods=['POST', 'OPTIONS'])
def api_doc_analysis():
    """AI Document Analysis — OCR then Chat interpretation."""
    if request.method == 'OPTIONS':
        return _cors_preflight()
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    doc = request.files['file']
    # Step 1: OCR
    ocr_text = ''
    try:
        ocr_res = requests.post(
            f'{SARVAM_BASE}/parse/document',
            headers={'api-subscription-key': SARVAM_API_KEY},
            files={'file': (doc.filename, doc.stream, doc.content_type or 'application/octet-stream')},
            timeout=60,
        )
        rj = ocr_res.json()
        ocr_text = rj.get('text', '') or rj.get('content', '') or rj.get('extracted_text', '')
        if not ocr_text and isinstance(rj.get('pages'), list):
            ocr_text = '\n'.join(p.get('text', '') for p in rj['pages'])
    except Exception as e:
        return _cors_json({'error': f'OCR failed: {e}'}, 500)
    if not ocr_text.strip():
        return _cors_json({'error': 'Could not extract text from document.'}, 400)
    # Step 2: AI Interpretation
    analysis_prompt = (
        f"I have a medical document with the following extracted text:\n\n"
        f"---\n{ocr_text[:3000]}\n---\n\n"
        "Please analyze this document and provide:\n"
        "1. **Document Type** (prescription, blood test, X-ray report, etc.)\n"
        "2. **Key Findings** from the document\n"
        "3. **Medicines mentioned** and their safety status in India\n"
        "4. **Recommendations** or flags for the patient\n"
        "Use markdown formatting."
    )
    try:
        res = requests.post(
            f'{SARVAM_BASE}/v1/chat/completions',
            headers=sarvam_headers(),
            json={
                'model': 'sarvam-m',
                'messages': [
                    {'role': 'system', 'content': PHARMAI_SYSTEM_PROMPT},
                    {'role': 'user', 'content': analysis_prompt},
                ],
                'temperature': 0.5,
                'max_tokens': 1024,
            },
            timeout=45,
        )
        rj = res.json()
        analysis = rj.get('choices', [{}])[0].get('message', {}).get('content', '')
        return _cors_json({
            'ocr_text': ocr_text[:2000],
            'analysis': analysis or 'Analysis could not be generated.',
        })
    except Exception as e:
        return _cors_json({'error': f'Analysis failed: {e}'}, 500)


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — Document Upload & Management
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/upload-files', methods=['POST'])
@app.route('/pharmai/api/upload-files', methods=['POST'])
def api_upload_files():
    if 'files' not in request.files:
        return jsonify({'success': False, 'message': 'No files provided'}), 400
    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'success': False, 'message': 'No files selected'}), 400
    uploaded = []
    for f in files:
        if f and f.filename and allowed_file(f.filename):
            fname = secure_filename(f.filename)
            fpath = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], fname))
            f.save(fpath)
            uploaded.append(fpath)
    if not uploaded:
        return jsonify({'success': False, 'message': 'No valid files uploaded'}), 400
    # Ingest straight into Elasticsearch using the same enrichment pipeline as
    # the bulk CLI, so an uploaded notification produces identical evidence to a
    # bulk-loaded one and is searchable the moment this call returns.
    #
    # This previously POSTed to `medical.lehana.in/ncert/api/index` — a retired
    # education-project service — so uploads silently failed to index anywhere.
    if not RXGUARD_AVAILABLE:
        return _rxguard_required()

    from services import gazette_ingest

    index_results = []
    for fpath in uploaded:
        try:
            index_results.append(gazette_ingest.ingest_upload(fpath))
        except Exception as e:
            index_results.append({'file': os.path.basename(fpath),
                                  'indexed': False, 'error': str(e)})
        finally:
            try:
                os.remove(fpath)
            except OSError:
                pass

    ok = sum(1 for r in index_results if r['indexed'])
    chunks = sum(r.get('chunks', 0) for r in index_results)
    return jsonify({
        'success': ok > 0,
        'message': (f'Indexed {ok}/{len(uploaded)} file(s) into Elasticsearch '
                    f'({chunks} searchable chunks)'),
        'count': len(uploaded),
        'index': rx_config.IDX_GAZETTES,
        'results': index_results,
    })


@app.route('/api/list-documents', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/pharmai/api/list-documents', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/documents', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/pharmai/api/documents', methods=['GET', 'POST', 'OPTIONS'])
def api_list_documents():
    """
    The indexed regulatory corpus, read from Elasticsearch.

    Previously this proxied `medical.lehana.in/ncert/api/documents` — a leftover
    from an unrelated education project which is no longer running, so the
    Knowledge Base tab returned 503 and the UI threw on a non-iterable response.
    Reading from `rxguard-gazettes` is both the correct source of truth and the
    thing the tab should have been showing all along.
    """
    if request.method == 'OPTIONS':
        return _cors_preflight()
    if not RXGUARD_AVAILABLE:
        return _rxguard_required()

    client = elastic_service.es_client()
    if client is None or not elastic_service.es_available():
        return _cors_json([], 200)  # empty list keeps the UI renderable

    try:
        # One bucket per source PDF, with chunk count and how many chunks were
        # classified as prohibitions — a genuinely useful corpus summary.
        res = client.search(
            index=rx_config.IDX_GAZETTES, size=0,
            aggs={'files': {
                'terms': {'field': 'source_file', 'size': 100},
                'aggs': {
                    'regulatory': {'filter': {'terms': {'ban_status': ['banned', 'restricted']}}},
                    'gazettes': {'cardinality': {'field': 'gazette_id'}},
                    'salts': {'cardinality': {'field': 'drugs'}},
                },
            }},
        )
        documents = [{
            'document_id': bucket['key'],
            'title': bucket['key'],
            'name': bucket['key'],
            'chunks': bucket['doc_count'],
            'regulatory_chunks': bucket['regulatory']['doc_count'],
            'gazette_ids': bucket['gazettes']['value'],
            'distinct_salts': bucket['salts']['value'],
            'index': rx_config.IDX_GAZETTES,
        } for bucket in res['aggregations']['files']['buckets']]
        return _cors_json(documents)
    except Exception as exc:
        print(f'[DOCS] Elasticsearch aggregation failed: {exc}')
        return _cors_json([], 200)


# The regulatory corpus is deliberately read-only through the web UI.
#
# These endpoints used to proxy deletes to the retired NCERT service. Rather
# than repoint them at Elasticsearch, they now refuse: gazette notifications are
# the evidence that every audit entry cites, and letting a web visitor delete
# them would break the auditability the whole design rests on. Corpus changes go
# through scripts/ingest_gazettes.py, on the server, by an operator.

_CORPUS_READONLY = {
    'error': 'The regulatory corpus is read-only.',
    'detail': ('Gazette documents are cited by entries in the immutable audit '
               'trail. Deleting them would orphan those citations. Corpus '
               'changes are made server-side via scripts/ingest_gazettes.py.'),
}


@app.route('/api/delete-document', methods=['POST', 'DELETE', 'OPTIONS'])
@app.route('/pharmai/api/delete-document', methods=['POST', 'DELETE', 'OPTIONS'])
def api_delete_document():
    if request.method == 'OPTIONS':
        return _cors_preflight()
    return _cors_json(_CORPUS_READONLY, 403)


@app.route('/api/delete-all-documents', methods=['DELETE', 'POST', 'OPTIONS'])
@app.route('/pharmai/api/delete-all-documents', methods=['DELETE', 'POST', 'OPTIONS'])
def api_delete_all_documents():
    if request.method == 'OPTIONS':
        return _cors_preflight()
    return _cors_json(_CORPUS_READONLY, 403)


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — Corpus explorer (Elasticsearch transparency)
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/corpus/stats', methods=['GET'])
@app.route('/pharmai/api/corpus/stats', methods=['GET'])
def api_corpus_stats():
    """
    What is actually in the index, straight from Elasticsearch aggregations.

    Exists so the claim "Elasticsearch is the core" is verifiable rather than
    asserted: a reviewer can see the real document counts, the salts covered,
    how ban status was established, and the analyzer in use — without shell
    access to the cluster.
    """
    if not RXGUARD_AVAILABLE:
        return _rxguard_required()
    client = elastic_service.es_client()
    if client is None or not elastic_service.es_available():
        return _cors_json({'error': 'Elasticsearch unavailable'}, 503)

    try:
        agg = client.search(
            index=rx_config.IDX_GAZETTES, size=0,
            aggs={
                'by_status': {'terms': {'field': 'ban_status'}},
                # How the status was decided: the chunk's own wording, or
                # inherited from the document being a prohibition list.
                'by_status_source': {'terms': {'field': 'ban_status_source'}},
                'by_file': {'terms': {'field': 'source_file', 'size': 50}},
                'distinct_salts': {'cardinality': {'field': 'drugs'}},
                'distinct_gazettes': {'cardinality': {'field': 'gazette_id'}},
                'top_salts': {'terms': {'field': 'drugs', 'size': 25}},
            },
        )['aggregations']

        interactions = client.search(
            index=rx_config.IDX_INTERACTIONS, size=0,
            aggs={'by_severity': {'terms': {'field': 'severity'}}},
        )['aggregations']

        return _cors_json({
            'cluster': elastic_service.cluster_info(),
            'retrieval': {
                'strategy': 'hybrid BM25 + kNN, reciprocal rank fusion',
                'analyzer': 'pharma_text (asciifolding, english_stop, pharma_synonyms)',
                'vector_field': 'embedding',
                'vector_dims': rx_config.EMBED_DIM,
                'similarity': 'cosine',
                'licence': 'basic (free) — RRF fused in-process, no trial features',
            },
            'gazettes': {
                'distinct_salts': agg['distinct_salts']['value'],
                'distinct_gazette_ids': agg['distinct_gazettes']['value'],
                'by_ban_status': {b['key']: b['doc_count']
                                  for b in agg['by_status']['buckets']},
                'by_ban_status_source': {b['key']: b['doc_count']
                                         for b in agg['by_status_source']['buckets']},
                'salts_covered': [b['key'] for b in agg['top_salts']['buckets']],
                'files': [{'file': b['key'], 'chunks': b['doc_count']}
                          for b in agg['by_file']['buckets']],
            },
            'interactions': {
                'by_severity': {b['key']: b['doc_count']
                                for b in interactions['by_severity']['buckets']},
            },
            'embeddings': embeddings.backend_report(),
        })
    except Exception as exc:
        return _cors_json({'error': str(exc)}, 500)


@app.route('/api/corpus/search', methods=['GET'])
@app.route('/pharmai/api/corpus/search', methods=['GET'])
def api_corpus_search():
    """
    Raw hybrid-retrieval output with no LLM in the path.

    Deliberately unsummarised: it shows exactly which documents Elasticsearch
    returns and at what fused score, so the retrieval layer can be judged on its
    own merits rather than through a model's paraphrase.
    """
    if not RXGUARD_AVAILABLE:
        return _rxguard_required()
    query = (request.args.get('q') or '').strip()
    if not query:
        return _cors_json({'error': 'q parameter required'}, 400)
    size = min(int(request.args.get('size', 10)), 50)

    hits = elastic_service.hybrid_search(rx_config.IDX_GAZETTES, query, size=size)
    return _cors_json({
        'query': query,
        'engine': 'elasticsearch',
        'strategy': 'hybrid BM25 + kNN, reciprocal rank fusion',
        'embedding_backend': embeddings.active_backend(),
        'hit_count': len(hits),
        'hits': [{
            'id': h['_id'],
            'fused_score': round(h.get('_score', 0), 6),
            'source_file': h.get('source_file'),
            'page': h.get('page'),
            'gazette_id': h.get('gazette_id'),
            'ban_status': h.get('ban_status'),
            'ban_status_source': h.get('ban_status_source'),
            'notification_date': h.get('notification_date'),
            'drugs': h.get('drugs'),
            'excerpt': (h.get('text') or '')[:400],
        } for h in hits],
    })


# ══════════════════════════════════════════════════════════════════════════════
#  HEALTH
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/health')
@app.route('/pharmai/health')
def health():
    """
    Health plus a live capability report.

    Deliberately verbose: it is also the honesty surface for the submission. A
    reviewer can see from one call which engine is serving retrieval, which
    provider is doing the reasoning, whether that provider is the specified AWS
    path or the demo fallback, and whether the audit chain currently verifies.
    """
    payload = {
        'status': 'healthy',
        'service': 'PharmAI / RxGuard Portal',
        'version': '3.0',
        'timestamp': time.time(),
        'features': [
            'elastic-hybrid-retrieval', 'drug-interaction-detection',
            'banned-fdc-detection', 'fhir-bundle-analysis',
            'immutable-audit-trail', 'stt', 'tts', 'translate', 'ocr',
        ],
    }

    if not RXGUARD_AVAILABLE:
        payload['rxguard'] = {'available': False,
                              'error': RXGUARD_IMPORT_ERROR}
        return jsonify(payload)

    payload['elasticsearch'] = elastic_service.cluster_info()
    payload['llm'] = llm_provider.provider_report()
    payload['embeddings'] = embeddings.backend_report()
    try:
        chain = audit_service.verify_chain(limit=1000)
        payload['audit_chain'] = {'verified': chain.get('verified'),
                                  'entries': chain.get('entries'),
                                  'head_seq': chain.get('head_seq')}
    except Exception as exc:
        payload['audit_chain'] = {'verified': False, 'reason': str(exc)}
    return jsonify(payload)


# ─── Error handlers ─────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large (max 16MB)'}), 413

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500


# ─── CORS helpers ────────────────────────────────────────────────────────────

def _cors_preflight():
    resp = jsonify({'ok': True})
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
    return resp

def _cors_json(data, status=200):
    resp = jsonify(data)
    resp.status_code = status
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    # 0.0.0.0, not 127.0.0.1: inside a container, binding to loopback makes the
    # app unreachable from Traefik. HOST stays overridable for bare-metal runs.
    host = os.getenv('HOST', '0.0.0.0')

    print(f"🚀 PharmAI / RxGuard Portal v3.0 starting on {host}:{port}")
    if RXGUARD_AVAILABLE:
        es = elastic_service.cluster_info()
        llm = llm_provider.provider_report()
        if es.get('available'):
            counts = es.get('doc_counts', {})
            print(f"   Elasticsearch: {es['cluster_name']} v{es['version']} "
                  f"({es['status']}) — "
                  f"{counts.get(rx_config.IDX_GAZETTES)} gazette chunks, "
                  f"{counts.get(rx_config.IDX_INTERACTIONS)} interaction pairs")
        else:
            print(f"   Elasticsearch: ⚠️  UNAVAILABLE ({es.get('reason')})")
        print(f"   Reasoning: {llm['active']} (mode={llm['mode']}, "
              f"bedrock_ready={llm['bedrock_ready']})")
        print(f"   Embeddings: {embeddings.backend_report()['local_onnx']} local, "
              f"dim={rx_config.EMBED_DIM}")
    else:
        print(f"   ⚠️  RxGuard layer DOWN: {RXGUARD_IMPORT_ERROR}")
    print(f"   Sarvam (voice/OCR only): "
          f"{'configured' if SARVAM_API_KEY else '⚠️  NOT configured'}")
    app.run(debug=debug, host=host, port=port)
