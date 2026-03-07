# PharmaAI v3.0 — Implementation Tasks

## Overview

**Project:** In-place upgrade of `/root/repo/pharmai_portal/frontend/`  
**Status:** 🔄 In Progress  
**Requirements:** See `requirements.md` (20 requirements)  
**Design:** See `design.md` (architecture, components, layout)

### Task Status Legend
- `- [ ]` Not started
- `- [-]` In progress
- `- [x]` Completed
- `- [~]` Queued (next)
- `- [ ]*` Optional/stretch goal

---

## Phase 1: Code Extraction & Modularization
> _Extract inline CSS/JS from 1487-line `index.html` into separate files_

- [ ] 1. Create directory structure
  - [ ] 1.1 Create `css/` directory
  - [ ] 1.2 Create `js/` directory
  - [ ] 1.3 Create `assets/` directory
  - [ ] 1.4 Create `assets/icons/` directory
  - _Req: Foundation for all subsequent work_

- [ ] 2. Extract CSS from `index.html`
  - [ ] 2.1 Extract Aura Design System variables and resets → `css/base.css`
  - [ ] 2.2 Extract layout styles (header, hero, tabs, footer) → `css/layout.css`
  - [ ] 2.3 Extract chat message styles (new) → `css/chat.css`
  - [ ] 2.4 Extract component styles (cards, modals, buttons, forms) → `css/components.css`
  - [ ] 2.5 Extract/create responsive media queries → `css/responsive.css`
  - [ ] 2.6 Remove all `<style>` blocks from `index.html`
  - [ ] 2.7 Add `<link>` tags for each CSS file in `index.html`
  - [ ] 2.8 Verify visual parity — page looks identical after extraction
  - _Req: R18 (Responsive), R19 (Theming)_

- [ ] 3. Extract JavaScript from `index.html`
  - [ ] 3.1 Extract utility functions → `js/utils.js` (formatTime, API helpers, markdown renderer)
  - [ ] 3.2 Extract DescopeAuth class → `js/auth.js`
  - [ ] 3.3 Extract search logic → `js/search.js` (incl. tier-1/tier-2 chain)
  - [ ] 3.4 Extract voice logic (STT recording, TTS playback) → `js/voice.js`
  - [ ] 3.5 Extract OCR/scanner logic → `js/ocr.js`
  - [ ] 3.6 Extract drug interaction logic → `js/interaction.js`
  - [ ] 3.7 Extract document upload/list/delete → `js/documents.js`
  - [ ] 3.8 Extract settings panel logic → `js/settings.js`
  - [ ] 3.9 Create `js/app.js` orchestrator (init, routing, event setup)
  - [ ] 3.10 Remove all `<script>` inline blocks from `index.html`
  - [ ] 3.11 Add `<script src=...>` tags for each JS file in `index.html`
  - [ ] 3.12 Verify all functionality works after extraction — search, OCR, voice, auth
  - _Req: Foundation for all features_

- [ ] 4. Update Flask `app.py` to serve static directories
  - [ ] 4.1 Add `static_folder` config to serve `css/`, `js/`, `assets/` directories
  - [ ] 4.2 Verify CSS/JS files load correctly via Flask dev server
  - [ ] 4.3 Test Docker container mounts include new directories
  - _Req: R20 (Backend Integration)_

---

## Phase 2: Layout Restructure (Perplexity-Style)
> _Transform tab-based layout to sidebar + chat layout_

- [ ] 5. Create new HTML layout skeleton
  - [ ] 5.1 Create top bar: hamburger button + logo + auth controls
  - [ ] 5.2 Create sidebar `<aside>` structure: new-chat button + space selector + session list
  - [ ] 5.3 Create main content area with `landingView` and `chatView` containers
  - [ ] 5.4 Keep fixed bottom search bar (reposition for new layout)
  - [ ] 5.5 Remove old hero section HTML
  - [ ] 5.6 Remove old tab navigation HTML
  - [ ] 5.7 Preserve tab panel content — convert to tool panels / modals
  - _Req: R1 (Conversational Search), R2 (Search History)_

- [ ] 6. Style the sidebar
  - [ ] 6.1 Sidebar base styles: 280px fixed left, dark teal background
  - [ ] 6.2 New Chat button: prominent teal, full width
  - [ ] 6.3 Space selector dropdown: icon + name, active indicator
  - [ ] 6.4 Session list items: title, timestamp, hover highlight
  - [ ] 6.5 Active session highlight style
  - [ ] 6.6 Session grouping: Today, Yesterday, Previous 7 Days, Older
  - [ ] 6.7 Session delete button (swipe or X icon)
  - [ ] 6.8 Sidebar collapse/expand animation (300ms slide)
  - [ ] 6.9 Sidebar overlay on mobile (backdrop + slide)
  - _Req: R2 (Search History Sidebar), R18 (Responsive)_

- [ ] 7. Style the chat area
  - [ ] 7.1 Chat messages container: flex column, scroll, padding
  - [ ] 7.2 User message bubble: right-aligned, teal bg, rounded
  - [ ] 7.3 AI message bubble: left-aligned, white bg, rounded, wider max-width
  - [ ] 7.4 System message: centered, small, gray
  - [ ] 7.5 Loading/thinking animation (3 bouncing dots)
  - [ ] 7.6 Auto-scroll to latest message
  - [ ] 7.7 Scroll-to-bottom FAB when scrolled up
  - _Req: R1 (Conversational Search)_

- [ ] 8. Style the landing view
  - [ ] 8.1 Centered hero: "What would you like to know about medicines?"
  - [ ] 8.2 Template card grid (4-6 cards)
  - [ ] 8.3 Template cards: icon + title + subtitle, clickable
  - [ ] 8.4 Templates populate search bar on click
  - [ ] 8.5 Recent searches section (if no active session)
  - _Req: R1_

- [ ] 9. Restyle the bottom search bar
  - [ ] 9.1 Persistent fixed bottom positioning (clear of sidebar)
  - [ ] 9.2 Active space indicator (icon + name badge) left of input
  - [ ] 9.3 Mic button with recording state animation (red pulse)
  - [ ] 9.4 Submit button
  - [ ] 9.5 Attachment button (for images/prescriptions)
  - [ ] 9.6 Expand search bar on focus (subtle grow)
  - _Req: R1, R3 (Session-Maintained Search)_

---

## Phase 3: Session Management
> _Implement conversational session persistence_

- [ ] 10. Create session data model
  - [ ] 10.1 Define session schema: id, title, spaceId, messages[], createdAt, updatedAt
  - [ ] 10.2 Define message schema: role, content, timestamp, source, citations, metadata
  - [ ] 10.3 Session ID generation (crypto.randomUUID or fallback)
  - _Req: R3 (Session-Maintained Search)_

- [ ] 11. Implement session CRUD in `js/chat.js`
  - [ ] 11.1 `createSession(spaceId)` — new session object, store in localStorage
  - [ ] 11.2 `loadSession(sessionId)` — switch to session, render all messages
  - [ ] 11.3 `deleteSession(sessionId)` — remove from localStorage, handle active session
  - [ ] 11.4 `renameSession(sessionId, title)` — update session title
  - [ ] 11.5 `addMessage(sessionId, message)` — append to session, save
  - [ ] 11.6 `getAllSessions()` — sorted by updatedAt desc
  - [ ] 11.7 Session storage limit: cap at 50 sessions, FIFO eviction with warning
  - _Req: R3_

- [ ] 12. Implement "New Chat" flow
  - [ ] 12.1 Click "+ New Chat" → create session, show landing view
  - [ ] 12.2 First query from landing → switch to chat view, set session title from query
  - [ ] 12.3 Subsequent queries → append to active session
  - [ ] 12.4 No active session + query → auto-create session
  - _Req: R1, R3_

- [ ] 13. Implement session list in sidebar
  - [ ] 13.1 Render session list from localStorage
  - [ ] 13.2 Click session → load and display
  - [ ] 13.3 Group sessions by date (Today, Yesterday, etc.)
  - [ ] 13.4 Show session title (first query, truncated to 50 chars)
  - [ ] 13.5 Active session highlight
  - [ ] 13.6 Right-click / long-press context menu: Rename, Delete
  - _Req: R2 (Search History Sidebar)_

- [ ] 14. Implement conversation context in search
  - [ ] 14.1 Build conversation history array from session messages
  - [ ] 14.2 Send last 5 messages as context to backend `/api/search`
  - [ ] 14.3 Backend: inject conversation context into prompt
  - [ ] 14.4 Handle multi-turn queries: "What about paracetamol?" → understand context
  - _Req: R3 (Session-Maintained Search)_

---

## Phase 4: Spaces & Personas
> _Perplexity-style configurable workspaces_

- [ ] 15. Create space data model  
  - [ ] 15.1 Define space schema: id, name, instructions, icon, isDefault, createdAt
  - [ ] 15.2 Create default spaces: General (🔍), Doctor Mode (🩺), Pharmacist Mode (💊), Patient Mode (👤), Researcher Mode (🔬)
  - [ ] 15.3 Store spaces in localStorage key `pharmai_spaces`
  - _Req: R4 (Spaces & Personas)_

- [ ] 16. Implement space CRUD in `js/spaces.js`
  - [ ] 16.1 `createSpace(name, icon, instructions)` — save to localStorage
  - [ ] 16.2 `updateSpace(spaceId, data)` — update fields
  - [ ] 16.3 `deleteSpace(spaceId)` — prevent deleting default, cascade: update sessions
  - [ ] 16.4 `getActiveSpace()` — return current space config
  - [ ] 16.5 `setActiveSpace(spaceId)` — update indicator, persist selection
  - _Req: R4_

- [ ] 17. Implement space selector UI
  - [ ] 17.1 Dropdown in sidebar: list all spaces with icons
  - [ ] 17.2 Active space indicator in search bar (icon + short name)
  - [ ] 17.3 "Create Space" button at bottom of dropdown
  - [ ] 17.4 Space creation modal: name, icon picker, system instructions textarea
  - [ ] 17.5 Edit space modal (click settings icon on space)
  - _Req: R4_

- [ ] 18. Inject space system prompt into search
  - [ ] 18.1 When search executes, prepend space.instructions to query
  - [ ] 18.2 Backend: accept `systemPrompt` param in `/api/search`
  - [ ] 18.3 Backend: merge space prompt with existing PHARMAI_SYSTEM_PROMPT
  - [ ] 18.4 Show space badge on AI responses generated in that space
  - _Req: R4_

---

## Phase 5: Enhanced Search & Chat UX
> _Result rendering, citations, actions on messages_

- [ ] 19. Render AI responses as chat messages
  - [ ] 19.1 Parse markdown content with Marked.js
  - [ ] 19.2 Add drug status badge: 🚫 BANNED (red), ✅ APPROVED (green), ⚠️ RESTRICTED (amber)
  - [ ] 19.3 Add medicine name as message header
  - [ ] 19.4 Show source indicator: "AWS KB" or "Sarvam AI"
  - _Req: R1 (Conversational Search), R10 (Explainable AI)_

- [ ] 20. Implement citation rendering
  - [ ] 20.1 Parse citations from KB response
  - [ ] 20.2 Render inline citation markers [1], [2], [3] in answer text
  - [ ] 20.3 Citation footer: clickable references with document names
  - [ ] 20.4 Click citation → expand with excerpt text
  - [ ] 20.5 Source confidence indicator (high/medium/low)
  - _Req: R10 (Explainable AI Citations)_

- [ ] 21. Implement message action buttons
  - [ ] 21.1 Copy button — copy message content to clipboard
  - [ ] 21.2 TTS button — read message aloud (Sarvam TTS)
  - [ ] 21.3 Translate button — translate to selected language (Sarvam Translate)
  - [ ] 21.4 Export button — open PDF export for this result
  - [ ] 21.5 Share button — copy permalink (deep link to session)
  - [ ] 21.6 Re-ask button (↻) — re-run query with fresh results
  - _Req: R6 (Multilingual), R8 (Compliance PDF), R1_

- [ ] 22. Implement Janaushadhi cost comparison cards
  - [ ] 22.1 Parse Janaushadhi alternatives from KB response metadata
  - [ ] 22.2 Render comparison card: brand name vs generic alternative
  - [ ] 22.3 Show price difference and savings percentage
  - [ ] 22.4 "Add to savings tracker" button on each card
  - _Req: R9 (Janaushadhi Cost Comparison)_

- [ ] 23. Implement typing/thinking indicator
  - [ ] 23.1 Show animated dots while search is in progress
  - [ ] 23.2 Show "Searching AWS Knowledge Base..." or "Asking Sarvam AI..." text
  - [ ] 23.3 Cancel button to abort in-flight request
  - [ ] 23.4 Timeout after 60s with retry option
  - _Req: R1_

---

## Phase 6: Knowledge Base Document Upload
> _Upload PDFs/documents to AWS Bedrock KB_

- [ ] 24. Create KB upload UI
  - [ ] 24.1 Upload panel accessible from sidebar menu (📂 icon)
  - [ ] 24.2 Drag-and-drop zone with visual feedback (dashed border, highlight)
  - [ ] 24.3 File input: accept only PDF (`.pdf` extension filter)
  - [ ] 24.4 ℹ️ tooltip: "Upload pharmaceutical documents to enhance search results"
  - [ ] 24.5 Upload progress bar with percentage
  - [ ] 24.6 Success/error toast notifications
  - _Req: R3 (KB Uploader)_

- [ ] 25. Implement document list view
  - [ ] 25.1 List all uploaded documents from AWS KB
  - [ ] 25.2 Show document name, upload date, file size
  - [ ] 25.3 Delete button per document (with confirmation dialog)
  - [ ] 25.4 "Delete All" button (with double confirmation)
  - [ ] 25.5 Empty state: "No documents uploaded yet"
  - [ ] 25.6 Refresh button to re-fetch list
  - _Req: R3_

- [ ] 26. Backend: Proxy KB operations
  - [ ] 26.1 Add `/api/kb/upload` endpoint → proxy to AWS RAG `/api/index`
  - [ ] 26.2 Add `/api/kb/documents` endpoint → proxy to AWS RAG `/api/documents`
  - [ ] 26.3 Add `/api/kb/delete` endpoint → proxy to AWS RAG `/api/documents/delete`
  - [ ] 26.4 Add `/api/kb/delete-all` endpoint → delete all KB documents
  - [ ] 26.5 Add environment variable `AWS_RAG_BACKEND_URL` for backend URL
  - [ ] 26.6 Error handling: surface AWS errors as user-friendly messages
  - _Req: R3, R20 (Backend Integration)_

---

## Phase 7: Prescription OCR & Medicine Extraction
> _Camera/upload → OCR → structured medicine list → compliance check each_

- [ ] 27. Revamp prescription scanner UI
  - [ ] 27.1 Camera capture button (using `navigator.mediaDevices.getUserMedia`)
  - [ ] 27.2 Image upload area (drag-drop + file input)
  - [ ] 27.3 Image preview with crop/rotate controls
  - [ ] 27.4 "Scan Prescription" button
  - [ ] 27.5 Loading state: "Analyzing prescription..."
  - _Req: R5 (Prescription OCR), R12 (PWA Camera Scanner)_

- [ ] 28. Implement medicine extraction (LLM post-processing)
  - [ ] 28.1 Send OCR text to Sarvam sarvam-m with extraction prompt
  - [ ] 28.2 Prompt: "Extract all medicine names, dosages, frequencies from this prescription text"
  - [ ] 28.3 Parse response into structured list: [{name, dosage, frequency, duration}]
  - [ ] 28.4 Handle messy OCR: retry with "please try harder to extract medicine names"
  - [ ] 28.5 Backend: create `/api/prescription-parse` endpoint
  - _Req: R5_

- [ ] 29. Implement medicine checklist UI
  - [ ] 29.1 Render extracted medicines as interactive checklist cards
  - [ ] 29.2 Each card: checkbox + medicine name + dosage + frequency
  - [ ] 29.3 "Check All" button → bulk compliance lookup
  - [ ] 29.4 Individual "Check" button per medicine
  - [ ] 29.5 Status indicators per medicine: ✅ Safe, 🚫 Banned, ⚠️ Warning, ⏳ Checking
  - [ ] 29.6 Click on medicine → full search result in chat view
  - [ ] 29.7 "Add all to chat" button → create new session with all medicine queries
  - _Req: R5, R7 (Drug Interaction)_

- [ ] 30. Backend: prescription parse endpoint
  - [ ] 30.1 Create `/api/prescription-parse` in `app.py`
  - [ ] 30.2 Accept multipart form data with image file
  - [ ] 30.3 Step 1: Send image to Sarvam OCR API
  - [ ] 30.4 Step 2: Send OCR text to Sarvam sarvam-m for extraction
  - [ ] 30.5 Step 3: Return structured medicine list + raw OCR text
  - [ ] 30.6 Error handling: OCR failure, extraction failure, empty prescription
  - _Req: R5_

---

## Phase 8: Voice Integration Enhancement
> _Better STT/TTS with language awareness_

- [ ] 31. Enhance STT (Speech-to-Text)
  - [ ] 31.1 Use selected language for STT (not hardcoded `hi-IN`)
  - [ ] 31.2 Visual recording indicator (red dot + waveform animation)
  - [ ] 31.3 Cancel recording button
  - [ ] 31.4 Auto-stop after 30 seconds
  - [ ] 31.5 Insert recognized text into search bar
  - [ ] 31.6 Confidence indicator on recognized text
  - _Req: R6 (Multilingual Voice-First)_

- [ ] 32. Enhance TTS (Text-to-Speech)
  - [ ] 32.1 Per-message TTS button in chat
  - [ ] 32.2 Auto-detect language of response for TTS
  - [ ] 32.3 Stop/pause button during playback
  - [ ] 32.4 Queue TTS if multiple messages selected
  - [ ] 32.5 Support all 10 Indian + 1 English language
  - _Req: R6_

- [ ] 33. Implement auto-translate on responses
  - [ ] 33.1 If user language ≠ English, auto-translate response
  - [ ] 33.2 Show both original (English) and translated response
  - [ ] 33.3 Toggle between original and translated
  - [ ] 33.4 Translate button available even when language is English
  - _Req: R6_

---

## Phase 9: Drug Interaction Checker
> _Upgrade existing interaction tab to chat-integrated cards_

- [ ] 34. Upgrade interaction checker UI
  - [ ] 34.1 Move from separate tab → accessible via toolbar icon or command
  - [ ] 34.2 Multi-drug input field (comma-separated or tag-style chips)
  - [ ] 34.3 "Check Interactions" button
  - [ ] 34.4 Results appear as chat message in current session
  - _Req: R7 (Drug Interaction Checker)_

- [ ] 35. Enhance interaction results rendering 
  - [ ] 35.1 Severity-coded badges: Critical (red), Moderate (amber), Minor (green)
  - [ ] 35.2 Expandable sections for each interaction pair
  - [ ] 35.3 Clinical significance and mechanism of action
  - [ ] 35.4 "Learn more" links to authoritative sources
  - _Req: R7_

---

## Phase 10: Compliance PDF Export
> _Generate printable drug compliance reports_

- [ ] 36. Implement client-side PDF generation
  - [ ] 36.1 Add html2pdf.js library (CDN)
  - [ ] 36.2 Create PDF template: header, drug info, status, citations, timestamp
  - [ ] 36.3 Include PharmaAI branding and disclaimer
  - [ ] 36.4 Export button on each AI response message
  - [ ] 36.5 Export entire session as multi-page PDF
  - _Req: R8 (Compliance PDF Export)_

- [ ] 37. PDF content formatting
  - [ ] 37.1 Drug status section: name, status badge, gazette reference
  - [ ] 37.2 Compliance details: ban date, uplift date, restrictions
  - [ ] 37.3 Alternative medicines section
  - [ ] 37.4 Citations and sources
  - [ ] 37.5 Timestamp and query context
  - [ ] 37.6 Legal disclaimer footer
  - _Req: R8_

---

## Phase 11: Settings & Personalization
> _Language, theme, accessibility preferences_

- [ ] 38. Language settings panel
  - [ ] 38.1 Language selector: 11 Indian languages + English
  - [ ] 38.2 Persist selected language in localStorage
  - [ ] 38.3 Apply language to STT/TTS/Translation automatically
  - [ ] 38.4 UI labels remain in English (content translates)
  - _Req: R6_

- [ ] 39. Theme settings
  - [ ] 39.1 Light/Dark mode toggle
  - [ ] 39.2 Dark mode CSS: use `--bg-dark`, `--text-dark` variables
  - [ ] 39.3 Persist preference in localStorage
  - [ ] 39.4 System preference detection (prefers-color-scheme)
  - [ ] 39.5 Smooth transition animation
  - _Req: R19 (Theming & Accessibility)_

- [ ] 40. Accessibility settings
  - [ ] 40.1 Font size selector: Small / Medium / Large
  - [ ] 40.2 High contrast mode toggle
  - [ ] 40.3 Reduce motion toggle
  - [ ] 40.4 Screen reader aria-labels on all interactive elements
  - [ ] 40.5 Focus visible indicators on keyboard navigation
  - _Req: R19_

---

## Phase 12: Notifications & Alerts
> _Drug watch list and regulatory update alerts_

- [ ] 41. Implement toast notification system
  - [ ] 41.1 Create `js/notifications.js` with `showToast(message, type, duration)`
  - [ ] 41.2 Types: success (green), error (red), warning (amber), info (teal)
  - [ ] 41.3 Toast container: top-right, stack up to 3
  - [ ] 41.4 Auto-dismiss after 5s with progress bar
  - [ ] 41.5 Manual dismiss (X button)
  - _Req: R14 (Push Notifications — client-side)_

- [ ] 42. Implement drug watch list
  - [ ] 42.1 "Watch" button on search results
  - [ ] 42.2 Store watched drugs in localStorage `pharmai_watched`
  - [ ] 42.3 Watched drugs panel in sidebar
  - [ ] 42.4 Visual indicator for status changes (if cached data differs)
  - _Req: R14_

---

## Phase 13: PWA & Offline Support
> _Service worker, manifest, offline caching_

- [ ] 43. Create PWA manifest
  - [ ] 43.1 Create `assets/manifest.json` with app name, icons, theme color
  - [ ] 43.2 Add icons: 192x192 and 512x512 PNG
  - [ ] 43.3 Set `display: standalone`, `start_url: /pharmai/`
  - [ ] 43.4 Link manifest in `index.html`
  - _Req: R12 (PWA Camera Scanner)_

- [ ] 44. Create service worker
  - [ ] 44.1 Create `sw.js` with cache-first strategy for static assets
  - [ ] 44.2 Cache CSS, JS files, CDN libraries
  - [ ] 44.3 Network-first for API calls
  - [ ] 44.4 Offline fallback page
  - [ ] 44.5 Register service worker in `js/app.js`
  - _Req: R13 (Progressive Offline Caching)_

- [ ] 45. Implement drug data cache
  - [ ] 45.1 Cache search results in localStorage (key: drug name → result)
  - [ ] 45.2 Cap at 100 entries with LRU eviction
  - [ ] 45.3 TTL: 7 days per cached result
  - [ ] 45.4 Offline mode: search cached results first
  - [ ] 45.5 Clear cache button in settings
  - _Req: R13_

---

## Phase 14: Backend Upgrades (Flask app.py)
> _Enhance Flask backend for all new features_

- [ ] 46. Restructure search endpoint for sessions
  - [ ] 46.1 Accept `history` array in `/api/search` request body
  - [ ] 46.2 Accept `spaceId` and `systemPrompt` params
  - [ ] 46.3 Build contextual prompt from history + space instructions
  - [ ] 46.4 Send to AWS RAG backend as primary search
  - [ ] 46.5 Fallback to Sarvam sarvam-m on AWS failure
  - [ ] 46.6 Return unified response: answer, source, citations, metadata, sessionId
  - _Req: R3, R4, R20_

- [ ] 47. Add AWS RAG backend proxy routes
  - [ ] 47.1 `POST /api/kb/upload` → proxy to AWS `/api/index`
  - [ ] 47.2 `GET /api/kb/documents` → proxy to AWS `/api/documents`
  - [ ] 47.3 `POST /api/kb/delete` → proxy to AWS `/api/documents/delete`
  - [ ] 47.4 `DELETE /api/kb/delete-all` → delete all KB documents
  - [ ] 47.5 Add `AWS_RAG_BACKEND_URL` environment variable
  - [ ] 47.6 Add timeout handling (45s for search, 120s for upload)
  - _Req: R3, R20_

- [ ] 48. Create prescription parse endpoint
  - [ ] 48.1 `POST /api/prescription-parse` — accept multipart image
  - [ ] 48.2 Step 1: Call Sarvam OCR parse/document
  - [ ] 48.3 Step 2: Call Sarvam sarvam-m with extraction prompt
  - [ ] 48.4 Step 3: Parse LLM response into structured medicine list
  - [ ] 48.5 Retry logic: if extraction fails, re-prompt with "concentrate on medicine names"
  - [ ] 48.6 Return: medicines[], ocr_text, confidence
  - _Req: R5_

- [ ] 49. Enhance existing endpoints
  - [ ] 49.1 `/api/stt` — accept language param (currently hardcoded `hi-IN`)
  - [ ] 49.2 `/api/tts` — accept language param for multi-language support
  - [ ] 49.3 `/api/translate` — accept source and target language
  - [ ] 49.4 `/api/interaction` — return severity-coded results
  - [ ] 49.5 Health endpoint: add version number `3.0`, component status
  - _Req: R6, R7, R20_

- [ ] 50. Add CORS and error handling improvements
  - [ ] 50.1 Standardize error response format: `{success: false, error: str, code: int}`
  - [ ] 50.2 Add request logging for debugging
  - [ ] 50.3 Add rate limiting headers
  - [ ] 50.4 Add CORS headers for potential separate frontend deployment
  - _Req: R20_

---

## Phase 15: Role-Based Defaults
> _Different default views based on user role_

- [ ] 51. Implement role detection
  - [ ] 51.1 Parse Descope user tenant/role from auth token
  - [ ] 51.2 Map roles: doctor, pharmacist, patient, admin, researcher
  - [ ] 51.3 Default if no role: patient
  - _Req: R11 (Role-Based Default Workspaces)_

- [ ] 52. Role-specific defaults
  - [ ] 52.1 Doctor: auto-select "Doctor Mode" space, show clinical templates
  - [ ] 52.2 Pharmacist: auto-select "Pharmacist Mode", show stock/inventory templates
  - [ ] 52.3 Patient: auto-select "Patient Mode", show simple language templates
  - [ ] 52.4 Researcher: auto-select "Researcher Mode", show technical templates
  - [ ] 52.5 Admin: show KB upload panel by default, full access
  - _Req: R11_

---

## Phase 16: Savings Tracker
> _Gamified Janaushadhi substitution tracking_

- [ ] 53. Implement savings tracker
  - [ ] 53.1 Store substitutions in localStorage: [{brand, generic, savings, date}]
  - [ ] 53.2 Running total counter (animated on update)
  - [ ] 53.3 Savings dashboard accessible from sidebar
  - [ ] 53.4 Monthly savings breakdown chart (CSS bar chart, no library)
  - [ ] 53.5 "Your savings so far: ₹X" badge in sidebar
  - _Req: R17 (Gamified Savings Tracker)_

- [ ] 54. Savings interaction points
  - [ ] 54.1 "Track this saving" button on Janaushadhi cards
  - [ ] 54.2 Auto-suggest after compliance check: "Save ₹X with generic alternative"
  - [ ] 54.3 Share savings summary (copy to clipboard)
  - _Req: R17_

---

## Phase 17: WhatsApp Bot Bridge
> _Send and receive queries via WhatsApp_

- [ ] 55. WhatsApp integration endpoints
  - [ ] 55.1 Add `/api/whatsapp/webhook` endpoint for incoming messages
  - [ ] 55.2 Process text queries through standard search pipeline
  - [ ] 55.3 Return formatted results for WhatsApp (plain text with emojis)
  - [ ] 55.4 Handle image messages (prescription OCR)
  - _Req: R16 (WhatsApp Bot Bridge)_

- [ ] 56. N8N workflow for WhatsApp
  - [ ] 56.1 Create N8N workflow: WhatsApp → PharmaAI API → WhatsApp response
  - [ ] 56.2 Use Twilio or WhatsApp Business API
  - [ ] 56.3 Rate limiting: 10 queries/user/day
  - _Req: R16_

---

## Phase 18: Enterprise Features
> _API key management for bulk integrations_

- [ ] 57. API key management
  - [ ] 57.1 Generate API keys tied to Descope user
  - [ ] 57.2 Key management panel in settings
  - [ ] 57.3 Usage tracking per key
  - [ ] 57.4 Rate limiting per key
  - _Req: R15 (Enterprise API Key Management) — Stretch_

---

## Phase 19: Responsive & Mobile Optimization
> _Ensure perfect experience on all devices_

- [ ] 58. Mobile layout optimization
  - [ ] 58.1 Sidebar → full-screen overlay on mobile
  - [ ] 58.2 Touch gestures: swipe right → open sidebar
  - [ ] 58.3 Chat messages: full-width on mobile
  - [ ] 58.4 Bottom search bar: 95% width, 16px font (prevent iOS zoom)
  - [ ] 58.5 Safe area insets for notched phones
  - _Req: R18 (Responsive Mobile-First)_

- [ ] 59. Tablet layout optimization
  - [ ] 59.1 Sidebar: collapsible (not always visible)
  - [ ] 59.2 Chat area: max-width 800px centered
  - [ ] 59.3 Tool panels: side-by-side if space permits
  - _Req: R18_

- [ ] 60. Performance optimization
  - [ ] 60.1 Lazy load images (prescription previews)
  - [ ] 60.2 Debounce search input (300ms)
  - [ ] 60.3 Virtual scroll for long session lists (50+ sessions)
  - [ ] 60.4 Minimize DOM nodes (reuse message templates)
  - _Req: R18_

---

## Phase 20: Integration Testing & Polish
> _End-to-end testing of all features_

- [ ] 61. Test session management
  - [ ] 61.1 Create session, add messages, refresh page → session persists
  - [ ] 61.2 Switch between sessions → correct messages show
  - [ ] 61.3 Delete session → removed from sidebar
  - [ ] 61.4 50+ sessions → oldest evicted with warning
  - _Req: R3_

- [ ] 62. Test spaces
  - [ ] 62.1 Create custom space with instructions
  - [ ] 62.2 Search in space → instructions affect response
  - [ ] 62.3 Switch spaces → search uses new space context
  - [ ] 62.4 Delete space → sessions reassigned to General
  - _Req: R4_

- [ ] 63. Test search pipeline
  - [ ] 63.1 Query → gets KB response with citations
  - [ ] 63.2 KB failure → falls back to Sarvam
  - [ ] 63.3 Both fail → graceful error message
  - [ ] 63.4 Multi-turn conversation → context preserved
  - _Req: R1, R3, R20_

- [ ] 64. Test OCR pipeline
  - [ ] 64.1 Upload prescription image → OCR text extracted
  - [ ] 64.2 Medicine list extracted from OCR text
  - [ ] 64.3 Check all medicines → compliance status shown
  - [ ] 64.4 Click medicine → full search in chat
  - _Req: R5_

- [ ] 65. Test voice features
  - [ ] 65.1 Record voice → text appears in search bar
  - [ ] 65.2 Click TTS on response → audio plays
  - [ ] 65.3 Different languages → correct STT/TTS model used
  - _Req: R6_

- [ ] 66. Test document upload
  - [ ] 66.1 Upload PDF → appears in document list
  - [ ] 66.2 Search for content from uploaded PDF → found in results
  - [ ] 66.3 Delete document → no longer in results
  - _Req: R3_

- [ ] 67. Test responsive design
  - [ ] 67.1 Desktop (1440px) → sidebar + chat side by side
  - [ ] 67.2 Tablet (768px) → sidebar collapsible
  - [ ] 67.3 Mobile (375px) → sidebar overlay, full-width chat
  - [ ] 67.4 Test on Chrome, Firefox, Safari mobile
  - _Req: R18_

- [ ] 68. Test accessibility
  - [ ] 68.1 Keyboard navigation: Tab through all controls
  - [ ] 68.2 Screen reader: all images have alt text, buttons have labels
  - [ ] 68.3 Color contrast: meets WCAG AA standard
  - [ ] 68.4 Focus indicators visible on all interactive elements
  - _Req: R19_

---

## Phase 21: Docker & Deployment
> _Update Docker config for new file structure_

- [ ] 69. Update Dockerfile
  - [ ] 69.1 Verify volume mount includes `css/`, `js/`, `assets/` dirs
  - [ ] 69.2 Update Flask static file serving config
  - [ ] 69.3 Add `sw.js` to root serving path
  - _Req: R20_

- [ ] 70. Update docker-compose.yml
  - [ ] 70.1 Add `AWS_RAG_BACKEND_URL` environment variable
  - [ ] 70.2 Verify health check path
  - [ ] 70.3 Test: `docker compose up -d --build`
  - _Req: R20_

- [ ] 71. Verify production deployment
  - [ ] 71.1 `curl -I https://medical.lehana.in/pharmai/` → 200 OK
  - [ ] 71.2 `curl -I https://medical.aidhunik.com/pharmai/` → 200 OK
  - [ ] 71.3 CSS/JS files load correctly via Traefik
  - [ ] 71.4 All API endpoints reachable
  - [ ] 71.5 Health check returns v3.0
  - _Req: R20_

---

## Phase 22: Documentation
> _README, CHANGELOG, inline docs_

- [ ] 72. Update README.md
  - [ ] 72.1 Update version to 3.0
  - [ ] 72.2 Add file index for new `css/`, `js/`, `assets/` structure
  - [ ] 72.3 Document all new features
  - [ ] 72.4 Update API endpoint reference
  - [ ] 72.5 Add architecture diagram
  - [ ] 72.6 Add Quick Start section
  - _Req: Documentation standards_

- [ ] 73. Create CHANGELOG.md
  - [ ] 73.1 Document all changes from v2.0 → v3.0
  - [ ] 73.2 Sections: Added, Changed, Fixed, Technical
  - _Req: Documentation standards_

- [ ] 74. Create DEV_DEMO.md
  - [ ] 74.1 curl commands for every API endpoint
  - [ ] 74.2 Step-by-step testing scenarios
  - [ ] 74.3 Configuration constants reference
  - _Req: Documentation standards_

- [ ] 75. Update inline documentation
  - [ ] 75.1 JSDoc comments on all JS functions
  - [ ] 75.2 Python docstrings on all Flask endpoints
  - [ ] 75.3 CSS section comments
  - _Req: Documentation standards_

---

## Phase 23: Hackathon Deliverables
> _Pitch and competition documentation_

- [ ] 76. Update PITCH.md for Round 2
  - [ ] 76.1 Update feature list with all v3.0 features
  - [ ] 76.2 Update architecture diagram
  - [ ] 76.3 Add demo screenshots
  - [ ] 76.4 Update metrics and impact projections
  - _Req: Hackathon submission_

- [ ] 77. Create demo script
  - [ ] 77.1 Step-by-step demo flow for judges
  - [ ] 77.2 Pre-loaded sample queries
  - [ ] 77.3 Screenshot capture guide
  - _Req: Hackathon submission_

---

## Phase 24: Advanced Sarvam AI Features
> _Maximize Sarvam AI platform usage for hackathon points_

- [ ] 78. Sarvam voice navigation
  - [ ] 78.1 Voice commands: "new chat", "switch to doctor mode", "show my history"
  - [ ] 78.2 Parse voice intent using Sarvam chat model
  - [ ] 78.3 Execute command from voice recognition
  - _Req: R6 (Multilingual Voice-First)_

- [ ] 79. Sarvam document summarization
  - [ ] 79.1 Post-upload: auto-summarize document using Sarvam chat
  - [ ] 79.2 Show summary in document list 
  - [ ] 79.3 Use summary for better search context
  - _Req: R6_

- [ ] 80. Multi-language search
  - [ ] 80.1 Detect input language using Sarvam
  - [ ] 80.2 Auto-translate non-English queries to English for KB search
  - [ ] 80.3 Auto-translate response back to user's language
  - [ ] 80.4 Show bilingual results (English + user language)
  - _Req: R6_

---

## Phase 25: Final Polish & Edge Cases
> _Handle all edge cases and polish UX_

- [ ] 81. Error states
  - [ ] 81.1 Network offline → show cached results + offline banner
  - [ ] 81.2 Backend timeout → retry button + last cached result
  - [ ] 81.3 Auth expired → re-show login modal
  - [ ] 81.4 localStorage full → evict oldest sessions + warn user
  - [ ] 81.5 OCR fails → suggest manual text input

- [ ] 82. Loading states
  - [ ] 82.1 Skeleton loaders for session list
  - [ ] 82.2 Shimmer effect for chat messages loading
  - [ ] 82.3 Progress bar for document upload
  - [ ] 82.4 Disabled buttons during async operations

- [ ] 83. Empty states
  - [ ] 83.1 No sessions → show welcome message + template cards
  - [ ] 83.2 No spaces → show default space only
  - [ ] 83.3 No documents → show upload CTA
  - [ ] 83.4 No saved drugs → show "start tracking" message

- [ ] 84. Keyboard shortcuts
  - [ ] 84.1 `/` → focus search bar
  - [ ] 84.2 `Ctrl+N` → new chat
  - [ ] 84.3 `Ctrl+K` → open command palette
  - [ ] 84.4 `Esc` → close sidebar/modal/panel

- [ ] 85. Animations and transitions
  - [ ] 85.1 Message appear animation (fade in from bottom)
  - [ ] 85.2 Sidebar slide animation (300ms ease-out)
  - [ ] 85.3 Modal backdrop fade
  - [ ] 85.4 Badge pulse on new information
  - [ ] 85.5 Scroll-to-bottom button bounce

- [ ] 86. Security hardening
  - [ ] 86.1 Sanitize all user input before DOM insertion
  - [ ] 86.2 CSP headers in Flask responses
  - [ ] 86.3 API key never exposed to frontend
  - [ ] 86.4 Rate limiting on backend endpoints

---

## Task Summary

| Phase | Tasks | Count |
|-------|-------|-------|
| 1: Code Extraction | 1-4 | 4 main (31 sub) |
| 2: Layout Restructure | 5-9 | 5 main (39 sub) |
| 3: Session Management | 10-14 | 5 main (25 sub) |
| 4: Spaces & Personas | 15-18 | 4 main (19 sub) |
| 5: Enhanced Search UX | 19-23 | 5 main (25 sub) |
| 6: KB Document Upload | 24-26 | 3 main (18 sub) |
| 7: Prescription OCR | 27-30 | 4 main (23 sub) |
| 8: Voice Enhancement | 31-33 | 3 main (15 sub) |
| 9: Drug Interaction | 34-35 | 2 main (8 sub) |
| 10: PDF Export | 36-37 | 2 main (11 sub) |
| 11: Settings | 38-40 | 3 main (14 sub) |
| 12: Notifications | 41-42 | 2 main (9 sub) |
| 13: PWA & Offline | 43-45 | 3 main (14 sub) |
| 14: Backend Upgrades | 46-50 | 5 main (22 sub) |
| 15: Role-Based | 51-52 | 2 main (8 sub) |
| 16: Savings Tracker | 53-54 | 2 main (8 sub) |
| 17: WhatsApp Bot | 55-56 | 2 main (6 sub) |
| 18: Enterprise | 57 | 1 main (4 sub) |
| 19: Responsive | 58-60 | 3 main (12 sub) |
| 20: Testing | 61-68 | 8 main (28 sub) |
| 21: Docker Deployment | 69-71 | 3 main (11 sub) |
| 22: Documentation | 72-75 | 4 main (13 sub) |
| 23: Hackathon | 76-77 | 2 main (6 sub) |
| 24: Sarvam Advanced | 78-80 | 3 main (9 sub) |
| 25: Polish & Edge Cases | 81-86 | 6 main (22 sub) |
| **TOTAL** | **1-86** | **86 main, 390+ sub-tasks** |

---

## Priority Order (Implementation Sequence)

**MVP Critical (Must Ship):**
1. Phase 1: Code Extraction (foundation)
2. Phase 2: Layout Restructure (visual change)
3. Phase 3: Session Management (core feature)
4. Phase 14: Backend Upgrades (enable all features)
5. Phase 5: Enhanced Search UX (chat rendering)
6. Phase 6: KB Document Upload (hackathon differentiator)

**High Priority (Should Ship):**
7. Phase 4: Spaces & Personas
8. Phase 7: Prescription OCR
9. Phase 8: Voice Enhancement
10. Phase 9: Drug Interaction
11. Phase 10: PDF Export

**Medium Priority (Nice to Have):**
12. Phase 11: Settings
13. Phase 12: Notifications
14. Phase 19: Responsive
15. Phase 24: Sarvam Advanced
16. Phase 25: Polish

**Low Priority (Stretch):**
17. Phase 13: PWA & Offline
18. Phase 15: Role-Based
19. Phase 16: Savings Tracker
20. Phase 17: WhatsApp Bot
21. Phase 18: Enterprise

**Always (Non-negotiable):**
22. Phase 20: Testing
23. Phase 21: Docker Deployment
24. Phase 22: Documentation
25. Phase 23: Hackathon Deliverables
