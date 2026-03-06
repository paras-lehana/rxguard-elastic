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

from flask import Flask, render_template_string, request, redirect, jsonify
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


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — Search API (2-tier)
# ══════════════════════════════════════════════════════════════════════════════

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
    result = search_medicine(query, session_id)
    return _cors_json({
        'status': 'success' if result['source'] != 'error' else 'error',
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
    """Drug Interaction Checker — Sarvam Chat."""
    if request.method == 'OPTIONS':
        return _cors_preflight()
    data = request.get_json(force=True)
    med_a = data.get('medicine_a', '').strip()
    med_b = data.get('medicine_b', '').strip()
    if not med_a or not med_b:
        return jsonify({'error': 'Both medicine names required'}), 400
    prompt = (
        f"Are {med_a} and {med_b} safe to take together in India? "
        "Provide: interaction type, severity (Safe/Caution/Dangerous), "
        "mechanism, and recommendation. Use markdown."
    )
    try:
        res = requests.post(
            f'{SARVAM_BASE}/v1/chat/completions',
            headers=sarvam_headers(),
            json={
                'model': 'sarvam-m',
                'messages': [
                    {'role': 'system', 'content': PHARMAI_SYSTEM_PROMPT},
                    {'role': 'user', 'content': prompt},
                ],
                'temperature': 0.5,
                'max_tokens': 1024,
            },
            timeout=45,
        )
        rj = res.json()
        content = rj.get('choices', [{}])[0].get('message', {}).get('content', '')
        return _cors_json({'answer': content or 'No interaction data available.'})
    except Exception as e:
        return _cors_json({'error': str(e)}, 500)


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
    index_results = []
    for fpath in uploaded:
        try:
            with open(fpath, 'rb') as fp:
                res = requests.post(
                    'https://medical.lehana.in/ncert/api/index',
                    files={'file': (os.path.basename(fpath), fp, 'application/pdf')},
                    data={'metadata': json.dumps({'source': 'CDSCO', 'type': 'pharmaceutical_document', 'year': str(time.localtime().tm_year)})},
                    timeout=120,
                )
            index_results.append({'file': os.path.basename(fpath), 'indexed': res.status_code == 200})
        except Exception as e:
            index_results.append({'file': os.path.basename(fpath), 'indexed': False, 'error': str(e)})
        finally:
            try:
                os.remove(fpath)
            except OSError:
                pass
    ok = sum(1 for r in index_results if r['indexed'])
    return jsonify({'success': ok > 0, 'message': f'Indexed {ok}/{len(uploaded)} file(s)', 'count': len(uploaded), 'results': index_results})


@app.route('/api/list-documents', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/pharmai/api/list-documents', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/documents', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/pharmai/api/documents', methods=['GET', 'POST', 'OPTIONS'])
def api_list_documents():
    if request.method == 'OPTIONS':
        return _cors_preflight()
    try:
        res = requests.get('https://medical.lehana.in/ncert/api/documents', timeout=30)
        if res.status_code == 200:
            return _cors_json(res.json().get('documents', []))
        return _cors_json({'error': f'API status {res.status_code}'}, res.status_code)
    except Exception as e:
        return _cors_json({'error': str(e)}, 503)


@app.route('/api/delete-document', methods=['POST', 'DELETE', 'OPTIONS'])
@app.route('/pharmai/api/delete-document', methods=['POST', 'DELETE', 'OPTIONS'])
def api_delete_document():
    if request.method == 'OPTIONS':
        return _cors_preflight()
    data = request.get_json(force=True)
    doc_id = data.get('documentId')
    if not doc_id:
        return jsonify({'error': 'No documentId'}), 400
    try:
        res = requests.post('https://medical.lehana.in/ncert/api/documents/delete', json={'documentId': doc_id}, timeout=30)
        return _cors_json(res.json(), res.status_code)
    except Exception as e:
        return _cors_json({'error': str(e)}, 500)


@app.route('/api/delete-all-documents', methods=['DELETE', 'POST', 'OPTIONS'])
@app.route('/pharmai/api/delete-all-documents', methods=['DELETE', 'POST', 'OPTIONS'])
def api_delete_all_documents():
    if request.method == 'OPTIONS':
        return _cors_preflight()
    try:
        res = requests.delete('https://medical.lehana.in/ncert/api/documents/all', timeout=60)
        return _cors_json(res.json(), res.status_code)
    except Exception as e:
        return _cors_json({'error': str(e)}, 500)


# ══════════════════════════════════════════════════════════════════════════════
#  HEALTH
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/health')
@app.route('/pharmai/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'PharmAI Portal',
        'version': '2.0',
        'timestamp': time.time(),
        'features': ['2-tier-search', 'stt', 'tts', 'translate', 'ocr', 'interaction-check', 'doc-analysis'],
    })


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
    print(f"🚀 PharmAI Portal v2.0 starting on port {port}")
    print(f"   Features: 2-tier search, STT, TTS, Translate, OCR, Interaction Check, Doc Analysis")
    print(f"   N8N: {'configured' if PHARMA_INSIGHT_URL else '⚠️  NOT configured'}")
    print(f"   Sarvam: {'configured' if SARVAM_API_KEY else '⚠️  NOT configured'}")
    app.run(debug=debug, host='0.0.0.0', port=port)
