"""
PharmAI Portal — Flask Backend v3.1
====================================
Serves the frontend and proxies API calls to:
  - AWS Bedrock Knowledge Base (via RAG backend at localhost:4101) for search, interaction, doc-analysis
  - Sarvam AI for STT, TTS, OCR, and Translation ONLY
Keeps API keys server-side (never exposed to browser).

Endpoints:
  GET  /                       → Main portal page
  GET  /pharmai                → Same (Traefik compat)
  GET  /analyze, /pharmai/analyze → Results page
  POST /api/search             → 2-tier medicine search (N8N → AWS Bedrock KB)
  POST /api/stt                → Speech-to-Text (Sarvam Saaras v3)
  POST /api/tts                → Text-to-Speech (Sarvam Bulbul v2)
  POST /api/translate          → Translation (Sarvam Mayura v1)
  POST /api/ocr                → Document OCR (Sarvam parse/document)
  POST /api/interaction        → Drug interaction check (AWS Bedrock KB)
  POST /api/doc-analysis       → AI document analysis (Sarvam OCR + AWS Bedrock KB)
  POST /api/upload-files       → PDF upload & index (AWS Bedrock KB)
  POST /api/list-documents     → List indexed documents (AWS Bedrock KB)
  POST /api/delete-document    → Delete a document (AWS Bedrock KB)
  DELETE /api/delete-all-documents → Delete all documents (AWS Bedrock KB)
  GET  /health                 → Health check
"""

from flask import Flask, send_from_directory, request, redirect, jsonify
import os
import zipfile
from io import BytesIO
from PIL import Image
import requests
import json
import base64
import tempfile
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

# AWS RAG Backend — Knowledge Base search, document indexing, and listing
# Hosted at /home/ubuntu/AWS_RAG_CURD/, container 'knowledge-base-aws' on port 4101
# NOTE: Accessible via localhost:4101 from the host; pharma-frontend container
# must use host.docker.internal or 172.18.0.1 (Docker host gateway)
AWS_RAG_BASE_URL = os.getenv('AWS_RAG_BASE_URL', 'http://172.18.0.1:4101')

# ─── Flask App ───────────────────────────────────────────────────────────────
# static_folder='.': Serve CSS/JS/assets from the same dir as app.py
app = Flask(__name__, static_folder='.', static_url_path='/static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'pharmai-portal-secret-2026')
app.config['UPLOAD_FOLDER'] = '../data'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max for KB uploads

# Create upload directory (may fail if container is strictly read-only, which is fine since we use memory now)
upload_path = os.path.abspath(app.config['UPLOAD_FOLDER'])
try:
    os.makedirs(upload_path, exist_ok=True)
except OSError:
    pass

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


def _sarvam_async_ocr(file_bytes, filename):
    import time
    import requests
    import zipfile
    from io import BytesIO
    from PIL import Image

    if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        try:
            img = Image.open(BytesIO(file_bytes)).convert('RGB')
            pdf_bytes = BytesIO()
            img.save(pdf_bytes, format='PDF', resolution=100.0)
            file_bytes = pdf_bytes.getvalue()
            filename = filename.rsplit('.', 1)[0] + '.pdf'
        except Exception as e:
            return {"error": f"Failed to convert image to PDF: {str(e)}"}

    headers = {'api-subscription-key': SARVAM_API_KEY, 'Content-Type': 'application/json'}
    # 1. Init Job
    payload = {"job_parameters": {"language": "en-IN", "output_format": "md"}}
    res = requests.post(f"{SARVAM_BASE}/doc-digitization/job/v1", headers=headers, json=payload)
    if not res.ok: return {"error": f"Job init failed: {res.text}"}
    job_id = res.json().get('job_id')

    # 2. Get Upload URLs
    res = requests.post(f"{SARVAM_BASE}/doc-digitization/job/v1/upload-files", headers=headers, json={"job_id": job_id, "files": [filename]})
    if not res.ok: return {"error": f"Upload URL failed: {res.text}"}
    upload_url = res.json().get("upload_urls", {}).get(filename).get("file_url")

    # 3. PUT bytes to Azure
    put_headers = {"x-ms-blob-type": "BlockBlob", "Content-Type": "application/pdf"}
    up_res = requests.put(upload_url, data=file_bytes, headers=put_headers)
    if not up_res.ok: return {"error": f"Azure PUT failed: {up_res.text}"}

    # 4. Start Job
    res = requests.post(f"{SARVAM_BASE}/doc-digitization/job/v1/{job_id}/start", headers=headers)
    if not res.ok: return {"error": f"Task start failed: {res.text}"}

    # 5. Poll
    status_data = {}
    for _ in range(30):
        time.sleep(3)
        res = requests.get(f"{SARVAM_BASE}/doc-digitization/job/v1/{job_id}/status", headers={"api-subscription-key": SARVAM_API_KEY})
        if res.ok:
            status_data = res.json()
            if status_data.get('job_state') in ['Completed', 'Success', 'Failed']: break
    if status_data.get('job_state') not in ['Completed', 'Success']:
        return {"error": f"Job didn't complete. State: {status_data.get('job_state')}"}

    # 6. Download Links
    job_details = status_data.get("job_details", [])
    output_files = [o.get("file_name") for d in job_details for o in d.get("outputs", [])]
    if not output_files: return {"error": "No output files in job details."}

    res = requests.post(f"{SARVAM_BASE}/doc-digitization/job/v1/{job_id}/download-files", headers=headers, json={"files": output_files})
    if not res.ok: return {"error": f"Download links failed: {res.text}"}
    
    dl_urls = res.json().get("download_urls", {})
    file_url = list(dl_urls.values())[0].get("file_url")

    # 7. Extract ZIP
    import re
    zip_res = requests.get(file_url)
    try:
        with zipfile.ZipFile(BytesIO(zip_res.content)) as z:
            for name in z.namelist():
                if name.endswith('.md'):
                    raw_text = z.read(name).decode('utf-8')
                    # Strip base64 image tags to prevent token limits
                    clean_text = re.sub(r'!\[.*?\]\(data:image/[^\)]+\)', '', raw_text)
                    return {"text": clean_text, "raw": {"job_id": job_id}}
    except Exception as e:
        return {"error": f"Failed to unzip: {str(e)}"}
    return {"error": "No .md file found in results zip."}



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
    "from a medicine package, provide a comprehensive analysis. Include the "
    "regulatory status in India (such as whether it is allowed, restricted, or banned by CDSCO/FSSAI), "
    "safety details (side effects, contraindications, drug interactions), "
    "and usage guidelines.\n\n"
    "**� Bulk Regulatory Lookup:**\n"
    "If given a list of multiple medicines, perform a bulk regulatory lookup. "
    "List each medicine individually and definitively state if it is ALLOWED, RESTRICTED, or BANNED by CDSCO.\n\n"
    "**�💰 Jan Aushadhi (Generic) Alternatives:**\n"
    "For EVERY branded medicine mentioned, mention if an equivalent generic medicine is available "
    "under Pradhan Mantri Bhartiya Janaushadhi Pariyojana (PMBJP).\n"
    "Do NOT fabricate prices or percentage savings if you are not certain. "
    "Instead, simply state that generic alternatives from PMBJP are usually significantly cheaper.\n"
    "Mention how the user can locate a nearby Jan Aushadhi Kendra.\n\n"
    "Be concise, accurate, and highly conversational. Keep the response fluid and natural. "
    "Respond in the same language the user uses. "
    "Use Markdown for formatting."
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


def search_tier2_aws(query, history=None, space_context=None):
    """Tier 2 — AWS Bedrock Knowledge Base via RAG backend at /api/search.
    
    WHY: AWS Bedrock provides domain-specific pharmaceutical knowledge via
    a curated Knowledge Base with CDSCO/FSSAI documents, far superior to
    a generic Sarvam chat completion for drug safety queries.
    The RAG backend handles vector search + Bedrock model inference internally.
    """
    try:
        # Build the search query with optional space context prepended
        search_query = query
        if space_context:
            search_query = f"[Context: {space_context}] {query}"

        # Include conversation history summary for follow-up context
        if history and isinstance(history, list):
            recent = history[-4:]  # Last 4 exchanges for context
            history_text = ' | '.join(
                f"{h.get('role', 'user')}: {h.get('content', '')[:200]}"
                for h in recent if h.get('role') in ('user', 'assistant')
            )
            if history_text:
                search_query = f"{query}\n\n[Previous conversation context: {history_text}]"

        res = requests.post(
            f'{AWS_RAG_BASE_URL}/api/search',
            json={'query': search_query, 'session_id': f'pharmai-web-{int(time.time())}'},
            timeout=60,
        )
        if res.status_code == 200:
            data = res.json()
            # AWS RAG backend response format:
            # - 'text': main summary text
            # - 'results': dict with detailed structured fields
            # - 'current_status': 'open' | 'banned' | 'restricted' etc.
            # - 'medicine_searched': the query medicine name
            answer = data.get('text') or data.get('answer') or data.get('response') or data.get('result', '')
            
            # Let Bedrock handle it naturally
            if data.get('medicine_searched'):
                results = data.get('results', {})
                summary = ''
                if isinstance(results, dict):
                    summary = results.get('summary', '')
                elif isinstance(results, str):
                    summary = results
                
                if summary:
                    answer = summary
            
            if answer:
                if "unable to assist you with this request" in answer:
                    print("[SEARCH T2] AWS RAG refused (empty KB). Falling back to Tier 3.")
                    return None
                return {'source': 'aws-bedrock', 'answer': answer}
        print(f"[SEARCH T2] AWS RAG status={res.status_code}")
    except Exception as e:
        print(f"[SEARCH T2] AWS RAG error: {e}")
    return None

def search_tier3_bedrock_direct(query, history=None, space_context=None):
    """Tier 3 — AWS Bedrock Direct Fallback.
    Handles general AI chat directly via our chat API endpoint.
    """
    system_prompt = "You are PharmAI, a helpful AI pharmaceutical assistant. Be concise."
    if space_context:
        system_prompt += f"\nContext focus: {space_context}"
    
    messages = []
    if history and isinstance(history, list):
        for h in history[-4:]:
            if h.get('role') in ('user', 'assistant'):
                messages.append({"role": h['role'], "content": h.get('content', '')})
    
    messages.append({"role": "user", "content": query})

    try:
        res = requests.post(f'{AWS_RAG_BASE_URL}/api/chat', json={
            "system": system_prompt,
            "messages": messages
        }, timeout=30)
        
        if res.status_code == 200:
            data = res.json()
            return {'source': 'bedrock-direct', 'answer': data.get('response', '')}
    except Exception as e:
        print(f"[SEARCH T3] Bedrock chat error: {e}")
    return None


def search_medicine(query, session_id, history=None, space_context=None):
    """Execute the full 3-tier search fallback chain with optional context.
    Tier 1: N8N RAG Pipeline (structured drug lookup)
    Tier 2: AWS Bedrock Knowledge Base (general pharma AI search)
    Tier 3: AWS Bedrock Direct (general AI conversation)
    """
    result = search_tier1_n8n(query, session_id)
    if result:
        return result
    result = search_tier2_aws(query, history=history, space_context=space_context)
    if result:
        return result
    result = search_tier3_bedrock_direct(query, history=history, space_context=space_context)
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


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — Static File Serving
# ══════════════════════════════════════════════════════════════════════════════

# Serve the main index.html and static assets (CSS, JS) directly.
# WHY send_from_directory: The new v2 frontend uses external CSS/JS files
# instead of inline <style>/<script>. render_template_string won't work
# because the HTML now references relative paths like css/base.css and js/app.js.

FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route('/')
@app.route('/pharmai')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/css/<path:filename>')
@app.route('/pharmai/css/<path:filename>')
def serve_css(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'css'), filename)

@app.route('/js/<path:filename>')
@app.route('/pharmai/js/<path:filename>')
def serve_js(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'js'), filename)

@app.route('/assets/<path:filename>')
@app.route('/pharmai/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'assets'), filename)


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
    history = data.get('history')           # Optional: conversation history for context
    space_context = data.get('space_context')  # Optional: space persona instruction
    extract_medicines = data.get('extract_medicines', False)
    if not query:
        return jsonify({'status': 'error', 'error': 'No query provided'}), 400
    print(f"[SEARCH] query='{query}' session={session_id} history_len={len(history) if history else 0}")
    if extract_medicines:
        # Bypass Tier 1 completely, ensure strict JSON array output via AWS Bedrock
        strict_query = query + "\n\nCRITICAL: You MUST output ONLY a valid JSON array. No markdown blocks, no chat text, just raw JSON like [{\"name\": \"...\", \"dosage\": \"...\", \"frequency\": \"...\"}]."
        result = search_tier3_bedrock_direct(strict_query, history=None, space_context=None)
        if not result:
            result = {'source': 'error', 'answer': '[]'}
    else:
        result = search_medicine(query, session_id, history=history, space_context=space_context)
    return _cors_json({
        'status': 'success' if result['source'] != 'error' else 'error',
        **result,
    })


@app.route('/api/janaushadhi/query', methods=['POST', 'OPTIONS'])
@app.route('/pharmai/api/janaushadhi/query', methods=['POST', 'OPTIONS'])
def api_janaushadhi_query():
    """
    Jan Aushadhi Agentic RAG Pipeline (Phase R9).
    
    Medicine Flow:  User Input → LLM (identify generic salts) → KB (fetch details) → LLM (curate HTML table)
    Location Flow:  User Input → KB (fetch kendra addresses) → LLM (curate HTML table)
    
    Returns {"success": true, "type": "...", "html": "<styled HTML table>"} on success.
    The frontend renders the HTML directly — no client-side JSON parsing needed.
    """
    if request.method == 'OPTIONS':
        return _cors_preflight()
    try:
        import time as _time
        start_time = _time.time()

        data = request.json or {}
        query = data.get('query', '').strip()
        intent_type = data.get('type', '')

        if not query:
            return jsonify({"success": False, "error": "No query provided"}), 400

        print(f"[JanAushadhi] Incoming: type={intent_type}, query='{query}'")

        if intent_type == 'medicine_alternative':
            html = _janaushadhi_medicine_flow(query)
        elif intent_type == 'kendra_locator':
            html = _janaushadhi_location_flow(query)
        else:
            return jsonify({"success": False, "error": f"Invalid type: {intent_type}"}), 400

        elapsed = round(_time.time() - start_time, 2)
        print(f"[JanAushadhi] Completed in {elapsed}s, html_length={len(html)}")

        return _cors_json({"success": True, "type": intent_type, "html": html})
        
    except Exception as e:
        print(f"[JanAushadhi] ERROR: {str(e)}")
        return _cors_json({"success": False, "error": str(e)}, 500)


# ── Jan Aushadhi Helper Functions ────────────────────────────────────────────

def _llm_chat(system_prompt, user_message):
    """
    Call the pure LLM endpoint (AWS Bedrock Claude via /api/chat).
    No Knowledge Base retrieval — just direct LLM conversation.
    Used for: identifying generic salts, curating final HTML responses.
    """
    try:
        payload = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": user_message}]}
            ],
            "system": system_prompt,
        }
        res = requests.post(
            f'{AWS_RAG_BASE_URL}/api/chat',
            json=payload,
            timeout=30,
        )
        if res.ok:
            return res.json().get('response', '')
        else:
            print(f"[JanAushadhi] LLM chat failed: HTTP {res.status_code}")
            return ''
    except Exception as e:
        print(f"[JanAushadhi] LLM chat error: {str(e)}")
        return ''


def _kb_search(query, system_prompt=None):
    """
    Call the Jan Aushadhi RAG endpoint (/api/janaushadhi/search).
    Searches the Knowledge Base with a generic prompt (no CDSCO overlay).
    Used for: fetching medicine details, kendra locations from uploaded PDFs.
    """
    try:
        payload = {"query": query}
        if system_prompt:
            payload["system_prompt"] = system_prompt
        res = requests.post(
            f'{AWS_RAG_BASE_URL}/api/janaushadhi/search',
            json=payload,
            timeout=45,
        )
        if res.ok:
            return res.json().get('text', '')
        else:
            print(f"[JanAushadhi] KB search failed: HTTP {res.status_code}")
            return ''
    except Exception as e:
        print(f"[JanAushadhi] KB search error: {str(e)}")
        return ''


def _janaushadhi_medicine_flow(query):
    """
    Medicine Alternative Pipeline:
      Step 1 — LLM: Identify the generic salt/chemical name from the brand name.
      Step 2 — KB:  Search the Jan Aushadhi Knowledge Base for products with that salt.
      Step 3 — LLM: Curate a styled HTML table combining user query + KB results.
    
    If KB has no data (empty or "sorry"), the LLM curator uses its own pharma knowledge
    and clearly indicates that pricing is not from the database.
    """
    # ── Step 1: LLM — Identify Generic Salt ──────────────────────
    print(f"[JanAushadhi:Medicine] Step 1 — Identifying generic salt for '{query}'")
    generic_salts = _llm_chat(
        system_prompt=(
            "You are a pharmaceutical expert. The user will give you a medicine brand name. "
            "Identify the generic salt/chemical compound name(s) for this medicine. "
            "Reply with ONLY the generic salt name(s), comma-separated if multiple, nothing else. "
            "Do NOT include dosage forms or strengths unless the user specified them. "
            "Example: User says 'Crocin' → you reply 'Paracetamol (Acetaminophen)'. "
            "Example: User says 'Combiflam' → you reply 'Ibuprofen, Paracetamol'."
        ),
        user_message=f"What is the generic salt for: {query}"
    )
    print(f"[JanAushadhi:Medicine] Step 1 done: salts='{generic_salts}'")

    # ── Step 2: KB — Search for Jan Aushadhi products ────────────
    kb_query = f"Find Jan Aushadhi medicines containing {generic_salts or query}. List the product name, composition, pack size, and MRP."
    print(f"[JanAushadhi:Medicine] Step 2 — KB search: '{kb_query[:80]}'")
    kb_text = _kb_search(kb_query)
    kb_useful = kb_text and len(kb_text) > 30 and 'sorry' not in kb_text.lower() and 'unable to assist' not in kb_text.lower()
    print(f"[JanAushadhi:Medicine] Step 2 done: kb_len={len(kb_text)}, useful={kb_useful}")

    # ── Step 3: LLM — Curate HTML table ──────────────────────────
    if kb_useful:
        curate_context = f"Knowledge Base results:\n{kb_text}"
        data_note = ""
    else:
        curate_context = "The Knowledge Base had no data for this medicine."
        data_note = " Since our database doesn't have specific pricing, use your pharmaceutical knowledge to provide generic alternative information and clearly note that prices should be verified at the nearest Jan Aushadhi Kendra."

    print(f"[JanAushadhi:Medicine] Step 3 — Curating HTML response")
    html = _llm_chat(
        system_prompt=(
            f"You are a Jan Aushadhi medicine advisor helping Indian patients find affordable generic alternatives. "
            f"The user searched for '{query}'. The generic salt is '{generic_salts or 'unknown'}'. "
            f"{curate_context} "
            f"Create a helpful HTML response with: "
            f"1) A brief intro paragraph (2-3 sentences) explaining what the generic alternative is and how Jan Aushadhi helps save money. "
            f"2) An HTML <table> with these columns: Jan Aushadhi Product | Generic Salt/Composition | Pack Size | MRP (₹) | Estimated Savings. "
            f"Style the table inline: border-collapse:collapse; width:100%. "
            f"Header row: background:#10b981; color:white; padding:10px 14px; text-align:left; font-weight:600. "
            f"Data cells: padding:8px 14px; border-bottom:1px solid #e5e7eb. "
            f"Even rows: background:#f0fdf4. "
            f"3) A small note at the bottom encouraging the user to consult a doctor before substituting medicines. "
            f"{data_note} "
            f"Output ONLY valid HTML. No markdown fences. No explanatory text outside the HTML."
        ),
        user_message=f"Create the Jan Aushadhi alternatives table for: {query}"
    )
    print(f"[JanAushadhi:Medicine] Step 3 done: html_len={len(html)}")

    return html or '<p style="color:#b91c1c;">Unable to generate response. Please try again.</p>'


def _janaushadhi_location_flow(query):
    """
    Kendra Locator Pipeline:
      Step 1 — KB:  Search the Knowledge Base for Kendras in the user's location.
      Step 2 — LLM: Curate a styled HTML table with Google Maps direction links.
    
    If KB has no data, the LLM provides general guidance on finding Kendras.
    """
    # ── Step 1: KB — Search for Kendras ──────────────────────────
    kb_query = query  # Send raw location string for accurate Bedrock chunk retrieval
    kb_system_prompt = (
        f"You are a helpful pharmaceutical knowledge assistant. The user is searching for Jan Aushadhi Kendras in '{query}'. "
        "Review the retrieved document chunks. If you find Kendras in or near this location, "
        "list them all, including store name, owner name, full address, and PIN code. "
        "If none are found, clearly state that you are unable to assist."
    )
    print(f"[JanAushadhi:Location] Step 1 — KB search: '{kb_query[:8000]}'")
    kb_text = _kb_search(query=kb_query, system_prompt=kb_system_prompt)
    kb_useful = kb_text and len(kb_text) > 30 and 'sorry' not in kb_text.lower() and 'unable to assist' not in kb_text.lower()
    print(f"[JanAushadhi:Location] Step 1 done: kb_len={len(kb_text)}, useful={kb_useful}")

    # ── Step 2: LLM — Curate HTML table with Maps links ─────────
    if kb_useful:
        curate_context = f"Knowledge Base results:\n{kb_text}"
        data_note = ""
    else:
        curate_context = "The Knowledge Base had no Kendra data for this location."
        data_note = (
            " Since our database doesn't have Kendras for this location, provide general guidance: "
            "tell the user to visit https://janaushadhi.gov.in for the official PMBJP Kendra directory, "
            "or search Google Maps for 'Jan Aushadhi Kendra near [location]'. "
            "Still create a helpful HTML response with these suggestions formatted nicely."
        )

    print(f"[JanAushadhi:Location] Step 2 — Curating HTML response")
    html = _llm_chat(
        system_prompt=(
            f"You are a Jan Aushadhi Kendra locator assistant helping users find nearby PMBJP stores in India. "
            f"The user is looking for Kendras in '{query}'. "
            f"{curate_context} "
            f"Create a helpful HTML response with: "
            f"1) A brief intro paragraph (1-2 sentences) about Jan Aushadhi Kendras in {query}. "
            f"2) An HTML <table> with columns: Kendra Name | Full Address | PIN Code | Directions. "
            f"For the Directions column, create a clickable link: "
            f"<a href='https://www.google.com/maps/dir/?api=1&destination=ENCODED_ADDRESS' target='_blank' "
            f"style='background:#10b981;color:white;padding:4px 10px;border-radius:4px;text-decoration:none;font-size:0.85rem;'>🗺️ Get Directions</a> "
            f"where ENCODED_ADDRESS is the URL-encoded full address string. "
            f"Style the table inline: border-collapse:collapse; width:100%. "
            f"Header row: background:#10b981; color:white; padding:10px 14px; text-align:left; font-weight:600. "
            f"Data cells: padding:8px 14px; border-bottom:1px solid #e5e7eb. "
            f"Even rows: background:#f0fdf4. "
            f"3) A note that the user can click 'Get Directions' to open Google Maps navigation. "
            f"{data_note} "
            f"Output ONLY valid HTML. No markdown fences. No explanatory text outside the HTML."
        ),
        user_message=f"Create the Kendra locator table for: {query}"
    )
    print(f"[JanAushadhi:Location] Step 2 done: html_len={len(html)}")

    return html or '<p style="color:#b91c1c;">Unable to generate location response. Please try again.</p>'


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — Sarvam AI Features
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/stt', methods=['POST', 'OPTIONS'])
@app.route('/pharmai/api/stt', methods=['POST', 'OPTIONS'])
def api_stt():
    """Speech-to-Text — Sarvam Saaras v3.
    Accepts either:
      - multipart/form-data with 'file' field (legacy)
      - JSON with 'audio' field (base64-encoded) — used by v2 frontend
    """
    if request.method == 'OPTIONS':
        return _cors_preflight()

    # JSON-based request (base64 audio from v2 frontend)
    if request.is_json:
        data = request.get_json(force=True)
        audio_b64 = data.get('audio', '')
        lang = data.get('language', 'en-IN')
        if not audio_b64:
            return jsonify({'error': 'No audio provided'}), 400
        try:
            audio_bytes = base64.b64decode(audio_b64)
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            with open(tmp_path, 'rb') as f:
                res = requests.post(
                    f'{SARVAM_BASE}/speech-to-text',
                    headers={'api-subscription-key': SARVAM_API_KEY},
                    files={'file': ('audio.webm', f, 'audio/webm')},
                    data={'model': 'saaras:v3', 'mode': 'transcribe', 'language_code': lang},
                    timeout=30,
                )
            os.unlink(tmp_path)
            return _cors_json(res.json(), res.status_code)
        except Exception as e:
            return _cors_json({'error': str(e)}, 500)

    # Legacy: multipart file upload
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
                'speaker': 'anushka',
                'model': 'bulbul:v2',
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
    """Document OCR — Sarvam parse/document.
    Accepts either:
      - multipart/form-data with 'file' field (legacy)
      - JSON with 'image' field (base64-encoded) — used by v2 frontend
    """
    if request.method == 'OPTIONS':
        return _cors_preflight()

    try:
        file_bytes = None
        filename = "document.pdf"
        
        # Check if JSON-based request (base64 image from v2 frontend)
        if request.is_json:
            data = request.get_json(force=True)
            image_b64 = data.get('image', '')
            if not image_b64:
                return jsonify({'error': 'No image provided'}), 400
            if ',' in image_b64:
                image_b64 = image_b64.split(',', 1)[1]
            import base64
            file_bytes = base64.b64decode(image_b64)
            filename = "document.jpg" # Base64 usually comes from image
        elif 'file' in request.files:
            doc = request.files['file']
            file_bytes = doc.read()
            filename = doc.filename
        else:
            return jsonify({'error': 'No file provided'}), 400
            
        result = _sarvam_async_ocr(file_bytes, filename)
        if "error" in result:
            return _cors_json({'error': result["error"]}, 500)
            
        extracted = result.get("text", "")
        rj = result.get("raw", {})
        return _cors_json({'text': extracted, 'raw': rj})
        
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
        file_bytes = doc.read()
        filename = doc.filename
        
        ocr_result = _sarvam_async_ocr(file_bytes, filename)
        if "error" in ocr_result:
            return _cors_json({'error': f'OCR failed: {ocr_result["error"]}'}, 500)
            
        ocr_text = ocr_result.get("text", "")

    except Exception as e:
        return _cors_json({'error': f'OCR failed: {e}'}, 500)
    if not ocr_text.strip():
        return _cors_json({'error': 'Could not extract text from document.'}, 400)

    # Step 2: AI Interpretation via AWS Bedrock Knowledge Base
    analysis_prompt = (
        f"I have a medical document with the following extracted text:\n\n"
        f"---\n{ocr_text[:15000]}\n---\n\n"
        "Please analyze this document and provide:\n"
        "1. **Document Type** (prescription, blood test, X-ray report, etc.)\n"
        "2. **Key Findings** from the document\n"
        "3. **Medicines mentioned** and their safety status in India\n"
        "4. **Jan Aushadhi Alternatives** — generic equivalents with cost savings\n"
        "5. **Recommendations** or flags for the patient\n"
        "Use markdown formatting."
    )
    try:
        res = requests.post(
            f'{AWS_RAG_BASE_URL}/api/search',
            json={'query': analysis_prompt, 'session_id': f'pharmai-docanalysis-{int(time.time())}'},
            timeout=60,
        )
        if res.status_code == 200:
            rj = res.json()
            # AWS RAG returns 'text' field with summary, 'results.summary' for detail
            analysis = rj.get('text') or rj.get('answer') or rj.get('response') or rj.get('result', '')
            if not analysis and isinstance(rj.get('results'), dict):
                analysis = rj['results'].get('summary', '')
        else:
            analysis = 'Analysis could not be generated.'
        return _cors_json({
            'ocr_text': ocr_text[:2000],
            'analysis': analysis or 'Analysis could not be generated.',
        })
    except Exception as e:
        return _cors_json({'error': f'Analysis failed: {e}'}, 500)


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — Document Upload & Management
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/upload-files', methods=['POST', 'OPTIONS'])
@app.route('/pharmai/api/upload-files', methods=['POST', 'OPTIONS'])
def api_upload_files():
    if request.method == 'OPTIONS':
        return _cors_preflight()
    if 'files' not in request.files:
        return _cors_json({'success': False, 'message': 'No files provided'}, 400)
    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return _cors_json({'success': False, 'message': 'No files selected'}, 400)
    
    index_results = []
    valid_count = 0
    
    for f in files:
        if f and f.filename and allowed_file(f.filename):
            valid_count += 1
            fname = secure_filename(f.filename)
            try:
                # Send the file bytes directly to AWS RAG to avoid writing to read-only container volumes
                file_bytes = f.read()
                res = requests.post(
                    f'{AWS_RAG_BASE_URL}/api/index',
                    files={'file': (fname, file_bytes, 'application/pdf')},
                    data={'metadata': json.dumps({'source': 'CDSCO', 'type': 'pharmaceutical_document', 'year': str(time.localtime().tm_year)})},
                    timeout=120,
                )
                index_results.append({'file': fname, 'indexed': res.status_code == 200})
            except Exception as e:
                index_results.append({'file': fname, 'indexed': False, 'error': str(e)})
                
    if valid_count == 0:
        return _cors_json({'success': False, 'message': 'No valid files uploaded'}, 400)
        
    ok = sum(1 for r in index_results if r.get('indexed', False))
    return _cors_json({'success': ok > 0, 'message': f'Indexed {ok}/{valid_count} file(s)', 'count': valid_count, 'results': index_results})


@app.route('/api/list-documents', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/pharmai/api/list-documents', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/documents', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/pharmai/api/documents', methods=['GET', 'POST', 'OPTIONS'])
def api_list_documents():
    if request.method == 'OPTIONS':
        return _cors_preflight()
    try:
        res = requests.get(f'{AWS_RAG_BASE_URL}/api/documents', timeout=30)
        if res.status_code == 200:
            docs = res.json().get('documents', [])
            for d in docs:
                d['id'] = d.get('name')
            return _cors_json(docs)
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
        res = requests.post(f'{AWS_RAG_BASE_URL}/api/documents/delete', json={'documentId': doc_id}, timeout=30)
        return _cors_json(res.json(), res.status_code)
    except Exception as e:
        return _cors_json({'error': str(e)}, 500)


@app.route('/api/delete-all-documents', methods=['DELETE', 'POST', 'OPTIONS'])
@app.route('/pharmai/api/delete-all-documents', methods=['DELETE', 'POST', 'OPTIONS'])
def api_delete_all_documents():
    if request.method == 'OPTIONS':
        return _cors_preflight()
    try:
        # Fetch all documents first
        list_res = requests.get(f'{AWS_RAG_BASE_URL}/api/documents', timeout=30)
        if list_res.status_code == 200:
            docs = list_res.json().get('documents', [])
            deleted_count = 0
            for doc in docs:
                doc_id = doc.get('document_id') or doc.get('id')
                if doc_id:
                    requests.post(f'{AWS_RAG_BASE_URL}/api/documents/delete', json={'documentId': doc_id}, timeout=30)
                    deleted_count += 1
            return _cors_json({'success': True, 'message': f'Deleted {deleted_count} documents.', 'count': deleted_count}, 200)
            
        # Fallback to direct call if GET failed
        res = requests.delete(f'{AWS_RAG_BASE_URL}/api/documents/all', timeout=60)
        return _cors_json(res.json(), res.status_code)
    except Exception as e:
        return _cors_json({'error': str(e)}, 500)


# ══════════════════════════════════════════════════════════════════════════════
#  External Links & Redirects
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/demo')
@app.route('/pharmai/demo')
def redirect_to_demo():
    """Redirects to the project demo video."""
    # TODO: Change this URL to the actual YouTube demo video link
    DEMO_VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    return redirect(DEMO_VIDEO_URL)

@app.route('/apk')
@app.route('/pharmai/apk')
def redirect_to_apk():
    """Redirects to the Google Drive link containing the mobile APK."""
    # TODO: Change this URL to the actual Drive link containing the APK
    APK_DRIVE_URL = "https://drive.google.com/drive/folders/dummy-link-for-apk"
    return redirect(APK_DRIVE_URL)

# ══════════════════════════════════════════════════════════════════════════════
#  HEALTH
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/health')
@app.route('/pharmai/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'PharmAI Portal',
        'version': '3.1',
        'timestamp': time.time(),
        'features': ['aws-rag', 'jan-aushadhi', 'session-privacy', '2-tier-search', 'session-history', 'spaces', 'stt', 'tts', 'translate', 'ocr', 'prescription-scan', 'doc-analysis', 'kb-upload'],
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
    print(f"🚀 PharmAI Portal v3.1 starting on port {port}")
    print(f"   Features: AWS RAG + Jan Aushadhi + Session Privacy + STT/TTS/Translate/OCR")
    print(f"   AWS RAG: {AWS_RAG_BASE_URL}")
    print(f"   N8N: {'configured' if PHARMA_INSIGHT_URL else '⚠️  NOT configured'}")
    print(f"   Sarvam (STT/TTS/OCR only): {'configured' if SARVAM_API_KEY else '⚠️  NOT configured'}")
    app.run(debug=debug, host='0.0.0.0', port=port)
