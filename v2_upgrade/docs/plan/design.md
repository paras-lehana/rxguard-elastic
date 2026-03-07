# PharmaAI v3.0 — Design Document

## Overview

PharmaAI v3.0 upgrades the existing monolithic `index.html` + `app.py` portal into a Perplexity-style conversational drug intelligence platform. The upgrade is **in-place** — all changes go directly into `/root/repo/pharmai_portal/frontend/`. No new project or framework is created.

### Core Design Decision: Vanilla JS with Modular Architecture

We stay with **vanilla HTML/CSS/JS** (no React/Svelte) to maintain deployment simplicity (Flask serves the HTML), but we modularize the code into separate JS/CSS files loaded into `index.html`.

### Architecture Changes Summary

| Component | v2.0 (Current) | v3.0 (Upgrade) |
|-----------|----------------|-----------------|
| **Layout** | Hero + tab panels + fixed bottom search | Sidebar + main chat area + persistent bottom search |
| **Search** | One-shot query → result card | Conversational chat with session history |
| **Results** | Single markdown card | Chat messages with citations, badges, actions |
| **State** | `localStorage` (recent searches only) | `localStorage` (sessions, spaces, settings, cache) |
| **Backend** | Flask → N8N or Sarvam fallback | Flask → AWS RAG KB (primary) → Sarvam (fallback) |
| **OCR** | Raw text extraction | Structured medicine list with editable checklist |
| **Documents** | Proxied to `medical.lehana.in/ncert/api` | Direct proxy to AWS RAG backend |
| **File** | Single `index.html` (1487 lines) | `index.html` + extracted `js/` and `css/` modules |

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────────┐
│  Browser (Vanilla HTML/CSS/JS)                                      │
│  ┌──────────┐ ┌──────────────────────┐ ┌──────────┐ ┌───────────┐ │
│  │ Sidebar   │ │ Main Chat Area       │ │ Modals   │ │ Service   │ │
│  │ - History │ │ - Messages           │ │ - Auth   │ │ Worker    │ │
│  │ - Spaces  │ │ - Input Bar          │ │ - Space  │ │ - Cache   │ │
│  │ - New Chat│ │ - Citations          │ │ - Upload │ │ - Offline │ │
│  └──────────┘ └──────────────────────┘ └──────────┘ └───────────┘ │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ HTTP (fetch)
┌───────────────────────────▼─────────────────────────────────────────┐
│  Flask Backend (app.py)                                              │
│  ┌───────────────────┐ ┌────────────────┐ ┌───────────────────────┐ │
│  │ Search Proxy      │ │ Sarvam APIs    │ │ Session Store         │ │
│  │ - /api/search     │ │ - /api/stt     │ │ (in-memory dict →     │ │
│  │ - /api/kb/*       │ │ - /api/tts     │ │  DynamoDB later)      │ │
│  │                   │ │ - /api/ocr     │ │                       │ │
│  │                   │ │ - /api/translate│ │                       │ │
│  └────────┬──────────┘ └────────────────┘ └───────────────────────┘ │
└───────────┼─────────────────────────────────────────────────────────┘
            │ HTTP
┌───────────▼─────────────────────────────────────────────────────────┐
│  AWS RAG Backend (FastAPI @ /home/ubuntu/AWS_RAG_CURD)              │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌──────────────────────┐│
│  │ /api/search│ │ /api/index│ │/api/docs  │ │ Bedrock KB           ││
│  │ RAG Search │ │ Ingest    │ │ List/Del  │ │ + Kendra GenAI Index ││
│  └───────────┘ └───────────┘ └───────────┘ └──────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

- **Frontend:** Vanilla HTML5 + CSS3 (Aura Design System) + ES6 JavaScript
- **Backend Proxy:** Python Flask (existing `app.py`)
- **AI Search (Primary):** AWS Bedrock KB + Kendra GenAI Index (via AWS_RAG_CURD)
- **AI Search (Fallback):** Sarvam AI `sarvam-m` LLM
- **Voice:** Sarvam STT (Saaras v3) + Sarvam TTS (Bulbul v3)
- **Translation:** Sarvam Mayura v1
- **OCR:** Sarvam Parse/Document + LLM extraction
- **Auth:** Descope Web Component
- **Storage:** `localStorage` for client state, in-memory dict for sessions (Flask)
- **PDF Export:** html2pdf.js (client-side)

---

## Components and Interfaces

### 1. Frontend Module Structure

**New file layout under `/root/repo/pharmai_portal/frontend/`:**

```
frontend/
├── index.html             # Main HTML (restructured layout)
├── css/
│   ├── base.css           # Aura design system variables, resets, typography
│   ├── layout.css         # Sidebar, main area, header layout
│   ├── chat.css           # Chat messages, citations, badges
│   ├── components.css     # Cards, modals, upload zones, buttons
│   └── responsive.css     # Media queries and mobile styles
├── js/
│   ├── app.js             # Main orchestrator: init, routing, state
│   ├── auth.js            # Descope auth class (extracted from inline)
│   ├── chat.js            # Chat UI: render messages, sessions, scroll mgmt
│   ├── search.js          # Search logic: tier-1/tier-2, session context
│   ├── sidebar.js         # Sidebar: history, spaces, new chat
│   ├── spaces.js          # Space CRUD, selection, system prompt injection
│   ├── ocr.js             # Prescription scanner, medicine extraction, checklist
│   ├── documents.js       # KB document upload, list, delete
│   ├── voice.js           # STT recording, TTS playback
│   ├── interaction.js     # Drug interaction checker
│   ├── export.js          # PDF export, copy, share
│   ├── settings.js        # Language, theme, preferences
│   ├── notifications.js   # Toast system, watch alerts
│   └── utils.js           # Time formatting, markdown rendering, API helpers
├── assets/
│   ├── manifest.json      # PWA manifest
│   └── icons/             # App icons for PWA
├── sw.js                  # Service worker for offline caching
├── app.py                 # Flask backend (upgraded)
├── .env                   # Environment variables
└── requirements.txt       # Python dependencies
```

### 2. HTML Layout (Restructured `index.html`)

**New Layout Structure:**

```html
<body>
  <!-- Top Bar: Hamburger + Logo + Auth -->
  <header class="top-bar">
    <button id="sidebarToggle" class="hamburger">☰</button>
    <div class="logo">PharmaAI</div>
    <div class="auth-section">...</div>
  </header>

  <!-- Sidebar (slides from left) -->
  <aside id="sidebar" class="sidebar">
    <button class="new-chat-btn">+ New Chat</button>
    <div class="space-selector">...</div>
    <div class="session-list">...</div>
  </aside>

  <!-- Main Content Area -->
  <main class="main-content">
    <!-- Landing View (shown when no active session) -->
    <div id="landingView" class="landing">
      <h1>What would you like to know?</h1>
      <div class="template-grid">...</div>
    </div>

    <!-- Chat View (shown when session active) -->
    <div id="chatView" class="chat-view" style="display:none">
      <div class="chat-messages" id="chatMessages">
        <!-- Messages rendered here -->
      </div>
    </div>

    <!-- Tool Panels (upload, interaction, settings) -->
    <div id="toolPanel" class="tool-panel" style="display:none">
      <!-- Dynamic content based on selected tool -->
    </div>
  </main>

  <!-- Fixed Bottom Search Bar (always visible) -->
  <div class="search-bar-fixed">
    <form id="searchForm">
      <div class="search-container">
        <span class="active-space-indicator" id="spaceIndicator"></span>
        <input id="searchInput" placeholder="Ask about any medicine...">
        <button type="button" id="micBtn" class="mic-btn">🎙️</button>
        <button type="submit" class="search-submit">➤</button>
      </div>
    </form>
  </div>

  <!-- Modals -->
  <div id="authModal" class="modal">...</div>
  <div id="spaceModal" class="modal">...</div>

  <!-- Scripts (modular) -->
  <script src="js/utils.js"></script>
  <script src="js/auth.js"></script>
  <script src="js/sidebar.js"></script>
  <script src="js/spaces.js"></script>
  <script src="js/chat.js"></script>
  <script src="js/search.js"></script>
  <script src="js/voice.js"></script>
  <script src="js/ocr.js"></script>
  <script src="js/documents.js"></script>
  <script src="js/interaction.js"></script>
  <script src="js/export.js"></script>
  <script src="js/settings.js"></script>
  <script src="js/notifications.js"></script>
  <script src="js/app.js"></script>
</body>
```

### 3. State Management (Client-Side)

**`localStorage` Keys:**

```javascript
// State schema
const STATE_KEYS = {
  // Auth
  'pharmai_user': { email, name, loginTime },
  
  // Sessions
  'pharmai_sessions': [{
    id: 'session_xxx',
    title: 'First query text...',
    spaceId: 'default',
    messages: [
      { role: 'user', content: '...', timestamp: 1234567890 },
      { role: 'assistant', content: '...', timestamp: 1234567891, 
        source: 'kb|sarvam', citations: [...] }
    ],
    createdAt: 1234567890,
    updatedAt: 1234567891,
  }],
  
  // Spaces
  'pharmai_spaces': [{
    id: 'space_xxx',
    name: 'Doctor Mode',
    instructions: 'Provide clinical-grade...',
    icon: '🩺',
    isDefault: true,
    createdAt: 1234567890,
  }],
  
  // Settings
  'pharmai_lang': 'hi-IN',
  'pharmai_theme': 'light',
  'pharmai_active_space': 'default',
  'pharmai_active_session': null,
  
  // Cache
  'pharmai_drug_cache': { 'paracetamol': { status, timestamp, data } },
  
  // Watched drugs
  'pharmai_watched': ['paracetamol', 'nimesulide'],
  
  // Savings tracker
  'pharmai_savings': { total: 0, substitutions: [] },
};
```

### 4. Chat Message Rendering

**Message Types and Templates:**

```javascript
// User message
{
  role: 'user',
  content: 'Is Terfenadine banned in India?',
  timestamp: Date.now(),
}

// AI message (KB response)
{
  role: 'assistant',
  content: '🚫 **BANNED**\n\n**Medicine:** Terfenadine...',
  timestamp: Date.now(),
  source: 'kb',
  citations: [
    { docName: 'cdsco_banned_01Jan2018.pdf', excerpt: '...', score: 0.95 }
  ],
  metadata: {
    current_status: 'banned',
    gazette_id: 'GSR 123 E',
    medicine_name: 'Terfenadine',
  }
}

// System message
{
  role: 'system',
  content: 'Session started in Doctor Mode 🩺',
  timestamp: Date.now(),
}
```

### 5. Backend Changes (app.py)

**New/Modified Endpoints:**

```python
# Modified: /api/search now supports session context + spaces
@app.route('/api/search', methods=['POST'])
def api_search():
    """
    Enhanced search with session context and space support.
    
    Request body:
      query: str
      sessionId: str (optional — to continue a conversation)
      spaceId: str (optional — to apply space system prompt)
      history: list[{role, content}] (optional — conversation context)
    
    Response:
      answer: str (markdown)
      source: 'kb' | 'sarvam' | 'error'
      citations: list[{docName, excerpt}]
      sessionId: str
      metadata: dict (status, gazette, medicine_name, etc.)
    """

# New: /api/prescription-parse
@app.route('/api/prescription-parse', methods=['POST'])
def api_prescription_parse():
    """
    OCR → LLM extraction → structured medicine list.
    
    Request: multipart form with 'file'
    Response:
      medicines: list[{name, dosage, frequency, duration}]
      ocr_text: str (raw extracted text)
      confidence: float
    """

# New: /api/export-pdf
@app.route('/api/export-pdf', methods=['POST'])
def api_export_pdf():
    """
    Generate compliance report PDF.
    
    Request body:
      drug_name: str
      search_result: dict
    Response:
      pdf: base64 encoded PDF
    """
```

### 6. AWS RAG Backend Integration

**Connection Configuration:**

```python
# In app.py — AWS RAG backend proxy
AWS_RAG_BACKEND_URL = os.getenv('AWS_RAG_BACKEND_URL', 'https://medical.lehana.in/ncert/api')

# Search: proxy to AWS RAG backend
def search_tier1_kb(query, session_id, system_prompt=None):
    """Tier 1 — AWS Bedrock KB RAG Search."""
    payload = {'query': query}
    if session_id:
        payload['sessionId'] = session_id
    res = requests.post(
        f'{AWS_RAG_BACKEND_URL}/search',
        json=payload,
        timeout=45,
    )
    # Transform response to unified frontend format
    ...
```

---

## Database Schema

### Client-Side Storage (localStorage)

No server-side database for v3.0 MVP. All user data persists in `localStorage`:

| Key | Type | Max Size | Purpose |
|-----|------|----------|---------|
| `pharmai_sessions` | JSON array | ~5MB | Session history (50 sessions max) |
| `pharmai_spaces` | JSON array | ~100KB | User-defined spaces |
| `pharmai_user` | JSON object | ~1KB | Auth state |
| `pharmai_drug_cache` | JSON object | ~500KB | Offline drug cache (100 entries) |
| `pharmai_settings` | JSON object | ~1KB | Language, theme, preferences |

### Future: DynamoDB Schema (Post-MVP)

```
Table: pharmai_sessions
  PK: userId (Descope user ID)
  SK: sessionId
  Attributes: title, messages[], spaceId, createdAt, updatedAt

Table: pharmai_spaces
  PK: userId
  SK: spaceId
  Attributes: name, instructions, icon, isDefault, createdAt
```

---

## API Endpoints (Complete)

### Existing (Preserved As-Is)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/stt` | Speech-to-Text (Sarvam Saaras v3) |
| POST | `/api/tts` | Text-to-Speech (Sarvam Bulbul v3) |
| POST | `/api/translate` | Translation (Sarvam Mayura v1) |
| POST | `/api/interaction` | Drug interaction checker |
| GET | `/health` | Health check |

### Modified

| Method | Path | Changes |
|--------|------|---------|
| POST | `/api/search` | Add `history`, `spaceId` params; response includes `citations`, `metadata` |
| POST | `/api/ocr` | No changes to endpoint, but frontend post-processes differently |
| POST | `/api/doc-analysis` | No changes |

### New

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/prescription-parse` | OCR → LLM → structured medicine extraction |
| POST | `/api/kb/upload` | Proxy to AWS RAG `/api/index` |
| GET | `/api/kb/documents` | Proxy to AWS RAG `/api/documents` |
| POST | `/api/kb/delete` | Proxy to AWS RAG `/api/documents/delete` |
| DELETE | `/api/kb/delete-all` | Proxy to delete all documents |

### Deprecated (Redirect)

| Old Path | New Path | Reason |
|----------|----------|--------|
| `/api/upload-files` | `/api/kb/upload` | Cleaner naming |
| `/api/list-documents` | `/api/kb/documents` | Cleaner naming |
| `/api/delete-document` | `/api/kb/delete` | Cleaner naming |

---

## UI/UX Design Specifications

### Color Palette (Preserved from Aura Design System)

```css
:root {
  --primary: #0D9488;        /* Teal */
  --primary-dark: #065F55;   /* Dark Teal */
  --primary-light: #14B8A6;  /* Light Teal */
  --accent: #D97706;         /* Amber */
  --success: #059669;        /* Green */
  --danger: #DC2626;         /* Red */
  --warning: #D97706;        /* Amber */
  --bg-light: #F0FDFA;       /* Light teal wash */
  --bg-dark: #042F2E;        /* Dark mode bg */
}
```

### Layout Dimensions

```
Desktop (1024px+):
  Sidebar: 280px fixed left
  Main content: calc(100% - 280px)
  Search bar: 700px max-width, centered bottom

Tablet (768px-1023px):
  Sidebar: overlay (slide from left)
  Main content: 100%
  Search bar: 90% width

Mobile (< 768px):
  Sidebar: full-screen overlay
  Main content: 100%
  Search bar: 95% width, full bottom
```

### Chat Message Styling

```
User message:
  - Right-aligned
  - Background: --primary with white text
  - Border-radius: 16px 16px 4px 16px
  - Max-width: 80%

AI message:
  - Left-aligned  
  - Background: white with --text color
  - Border-radius: 16px 16px 16px 4px
  - Max-width: 85%
  - Includes: status badge, citation markers, action buttons

System message:
  - Center-aligned
  - Background: transparent
  - Font-size: 0.8rem, gray
```

---

## Migration Strategy

### Phase 1: File Extraction (No visual change)
1. Extract CSS from `index.html` → `css/` files
2. Extract JS from `index.html` → `js/` files  
3. Verify everything still works identically

### Phase 2: Layout Restructure
1. Add sidebar HTML structure
2. Replace hero + tabs with landing/chat views
3. Move search bar to persistent bottom

### Phase 3: Feature Implementation
1. Session management in `js/chat.js`
2. Spaces in `js/spaces.js`
3. Enhanced OCR pipeline
4. Citation rendering

### Phase 4: Backend Upgrades
1. Session-aware search endpoint
2. Prescription parse endpoint
3. AWS RAG backend proxy routes

### Phase 5: Polish & PWA
1. Responsive refinement
2. Service worker
3. PDF export
4. Accessibility
