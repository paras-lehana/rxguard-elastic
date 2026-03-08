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

- [x] 1. Create directory structure
  - [x] 1.1 Create `css/` directory
  - [x] 1.2 Create `js/` directory
  - [x] 1.3 Create `assets/` directory
  - [x] 1.4 Create `assets/icons/` directory
  - _Req: Foundation for all subsequent work_

- [x] 2. Extract CSS from `index.html`
  - [x] 2.1 Extract Aura Design System variables and resets → `css/base.css`
  - [x] 2.2 Extract layout styles (header, hero, tabs, footer) → `css/layout.css`
  - [x] 2.3 Extract chat message styles (new) → `css/chat.css`
  - [x] 2.4 Extract component styles (cards, modals, buttons, forms) → `css/components.css`
  - [x] 2.5 Extract/create responsive media queries → `css/responsive.css`
  - [x] 2.6 Remove all `<style>` blocks from `index.html`
  - [x] 2.7 Add `<link>` tags for each CSS file in `index.html`
  - [x] 2.8 Verify visual parity — page looks identical after extraction
  - _Req: R18 (Responsive), R19 (Theming)_

- [x] 3. Extract JavaScript from `index.html`
  - [x] 3.1 Extract utility functions → `js/utils.js` (formatTime, API helpers, markdown renderer)
  - [x] 3.2 Extract DescopeAuth class → `js/auth.js`
  - [x] 3.3 Extract search logic → `js/search.js` (incl. tier-1/tier-2 chain)
  - [x] 3.4 Extract voice logic (STT recording, TTS playback) → `js/voice.js`
  - [x] 3.5 Extract OCR/scanner logic → `js/ocr.js`
  - [x] 3.6 Extract drug interaction logic → `js/interaction.js`
  - [x] 3.7 Extract document upload/list/delete → `js/documents.js`
  - [x] 3.8 Extract settings panel logic → `js/settings.js`
  - [x] 3.9 Create `js/app.js` orchestrator (init, routing, event setup)
  - [x] 3.10 Remove all `<script>` inline blocks from `index.html`
  - [x] 3.11 Add `<script src=...>` tags for each JS file in `index.html`
  - [x] 3.12 Verify all functionality works after extraction — search, OCR, voice, auth
  - _Req: Foundation for all features_

- [x] 4. Update Flask `app.py` to serve static directories
  - [x] 4.1 Add `static_folder` config to serve `css/`, `js/`, `assets/` directories
  - [x] 4.2 Verify CSS/JS files load correctly via Flask dev server
  - [x] 4.3 Test Docker container mounts include new directories
  - _Req: R20 (Backend Integration)_

---

## Phase 2: Layout Restructure (Perplexity-Style)
> _Transform tab-based layout to sidebar + chat layout_

- [x] 5. Create new HTML layout skeleton
  - [x] 5.1 Create top bar: hamburger button + logo + auth controls
  - [x] 5.2 Create sidebar `<aside>` structure: new-chat button + space selector + session list
  - [x] 5.3 Create main content area with `landingView` and `chatView` containers
  - [x] 5.4 Keep fixed bottom search bar (reposition for new layout)
  - [x] 5.5 Remove old hero section HTML
  - [x] 5.6 Remove old tab navigation HTML
  - [x] 5.7 Preserve tab panel content — convert to tool panels / modals
  - _Req: R1 (Conversational Search), R2 (Search History)_

- [x] 6. Style the sidebar
  - [x] 6.1 Sidebar base styles: 280px fixed left, dark teal background
  - [x] 6.2 New Chat button: prominent teal, full width
  - [x] 6.3 Space selector dropdown: icon + name, active indicator
  - [x] 6.4 Session list items: title, timestamp, hover highlight
  - [x] 6.5 Active session highlight style
  - [x] 6.6 Session grouping: Today, Yesterday, Previous 7 Days, Older
  - [x] 6.7 Session delete button (swipe or X icon)
  - [x] 6.8 Sidebar collapse/expand animation (300ms slide)
  - [x] 6.9 Sidebar overlay on mobile (backdrop + slide)
  - _Req: R2 (Search History Sidebar), R18 (Responsive)_

- [x] 7. Style the chat area
  - [x] 7.1 Chat messages container: flex column, scroll, padding
  - [x] 7.2 User message bubble: right-aligned, teal bg, rounded
  - [x] 7.3 AI message bubble: left-aligned, white bg, rounded, wider max-width
  - [x] 7.4 System message: centered, small, gray
  - [x] 7.5 Loading/thinking animation (3 bouncing dots)
  - [x] 7.6 Auto-scroll to latest message
  - [x] 7.7 Scroll-to-bottom FAB when scrolled up
  - _Req: R1 (Conversational Search)_

- [x] 8. Style the landing view
  - [x] 8.1 Centered hero: "What would you like to know about medicines?"
  - [x] 8.2 Template card grid (4-6 cards)
  - [x] 8.3 Template cards: icon + title + subtitle, clickable
  - [x] 8.4 Templates populate search bar on click
  - [x] 8.5 Recent searches section (if no active session)
  - _Req: R1_

- [x] 9. Restyle the bottom search bar
  - [x] 9.1 Persistent fixed bottom positioning (clear of sidebar)
  - [x] 9.2 Active space indicator (icon + name badge) left of input
  - [x] 9.3 Mic button with recording state animation (red pulse)
  - [x] 9.4 Submit button
  - [x] 9.5 Attachment button (for images/prescriptions)
  - [x] 9.6 Expand search bar on focus (subtle grow)
  - _Req: R1, R3 (Session-Maintained Search)_

---

## Phase 3: Session Management
> _Implement conversational session persistence_

- [x] 10. Create session data model
  - [x] 10.1 Define session schema: id, title, spaceId, messages[], createdAt, updatedAt
  - [x] 10.2 Define message schema: role, content, timestamp, source, citations, metadata
  - [x] 10.3 Session ID generation (crypto.randomUUID or fallback)
  - _Req: R3 (Session-Maintained Search)_

- [x] 11. Implement session CRUD in `js/chat.js`
  - [x] 11.1 `createSession(spaceId)` — new session object, store in localStorage
  - [x] 11.2 `loadSession(sessionId)` — switch to session, render all messages
  - [x] 11.3 `deleteSession(sessionId)` — remove from localStorage, handle active session
  - [x] 11.4 `renameSession(sessionId, title)` — update session title
  - [x] 11.5 `addMessage(sessionId, message)` — append to session, save
  - [x] 11.6 `getAllSessions()` — sorted by updatedAt desc
  - [x] 11.7 Session storage limit: cap at 50 sessions, FIFO eviction with warning
  - _Req: R3_

- [x] 12. Implement "New Chat" flow
  - [x] 12.1 Click "+ New Chat" → create session, show landing view
  - [x] 12.2 First query from landing → switch to chat view, set session title from query
  - [x] 12.3 Subsequent queries → append to active session
  - [x] 12.4 No active session + query → auto-create session
  - _Req: R1, R3_

- [x] 13. Implement session list in sidebar
  - [x] 13.1 Render session list from localStorage
  - [x] 13.2 Click session → load and display
  - [x] 13.3 Group sessions by date (Today, Yesterday, etc.)
  - [x] 13.4 Show session title (first query, truncated to 50 chars)
  - [x] 13.5 Active session highlight
  - [x] 13.6 Right-click / long-press context menu: Rename, Delete
  - _Req: R2 (Search History Sidebar)_

- [x] 14. Implement conversation context in search
  - [x] 14.1 Build conversation history array from session messages
  - [x] 14.2 Send last 5 messages as context to backend `/api/search`
  - [x] 14.3 Backend: inject conversation context into prompt
  - [x] 14.4 Handle multi-turn queries: "What about paracetamol?" → understand context
  - _Req: R3 (Session-Maintained Search)_

---

## Phase 4: Spaces & Personas
> _Perplexity-style configurable workspaces_

- [x] 15. Create space data model  
  - [x] 15.1 Define space schema: id, name, instructions, icon, isDefault, createdAt
  - [x] 15.2 Create default spaces: General (🔍), Doctor Mode (🩺), Pharmacist Mode (💊), Patient Mode (👤), Researcher Mode (🔬)
  - [x] 15.3 Store spaces in localStorage key `pharmai_spaces`
  - _Req: R4 (Spaces & Personas)_

- [x] 16. Implement space CRUD in `js/spaces.js`
  - [x] 16.1 `createSpace(name, icon, instructions)` — save to localStorage
  - [x] 16.2 `updateSpace(spaceId, data)` — update fields
  - [x] 16.3 `deleteSpace(spaceId)` — prevent deleting default, cascade: update sessions
  - [x] 16.4 `getActiveSpace()` — return current space config
  - [x] 16.5 `setActiveSpace(spaceId)` — update indicator, persist selection
  - _Req: R4_

- [x] 17. Implement space selector UI
  - [x] 17.1 Dropdown in sidebar: list all spaces with icons
  - [x] 17.2 Active space indicator in search bar (icon + short name)
  - [x] 17.3 "Create Space" button at bottom of dropdown
  - [x] 17.4 Space creation modal: name, icon picker, system instructions textarea
  - [x] 17.5 Edit space modal (click settings icon on space)
  - _Req: R4_

- [x] 18. Inject space system prompt into search
  - [x] 18.1 When search executes, prepend space.instructions to query
  - [x] 18.2 Backend: accept `systemPrompt` param in `/api/search`
  - [x] 18.3 Backend: merge space prompt with existing PHARMAI_SYSTEM_PROMPT
  - [x] 18.4 Show space badge on AI responses generated in that space
  - _Req: R4_

---

## Phase 5: Enhanced Search & Chat UX
> _Result rendering, citations, actions on messages_

- [x] 19. Render AI responses as chat messages
  - [x] 19.1 Parse markdown content with Marked.js
  - [x] 19.2 Add drug status badge: 🚫 BANNED (red), ✅ APPROVED (green), ⚠️ RESTRICTED (amber)
  - [x] 19.3 Add medicine name as message header
  - [x] 19.4 Show source indicator: "AWS KB" or "Sarvam AI"
  - _Req: R1 (Conversational Search), R10 (Explainable AI)_

- [x] 20. Implement citation rendering
  - [x] 20.1 Parse citations from KB response
  - [x] 20.2 Render inline citation markers [1], [2], [3] in answer text
  - [x] 20.3 Citation footer: clickable references with document names
  - [x] 20.4 Click citation → expand with excerpt text
  - [x] 20.5 Source confidence indicator (high/medium/low)
  - _Req: R10 (Explainable AI Citations)_

- [x] 21. Implement message action buttons
  - [x] 21.1 Copy button — copy message content to clipboard
  - [x] 21.2 TTS button — read message aloud (Sarvam TTS)
  - [x] 21.3 Translate button — translate to selected language (Sarvam Translate)
  - [x] 21.4 Export button — open PDF export for this result
  - [x] 21.5 Share button — copy permalink (deep link to session)
  - [x] 21.6 Re-ask button (↻) — re-run query with fresh results
  - _Req: R6 (Multilingual), R8 (Compliance PDF), R1_

- [x] 22. Implement Janaushadhi cost comparison cards
  - [x] 22.1 Parse Janaushadhi alternatives from KB response metadata
  - [x] 22.2 Render comparison card: brand name vs generic alternative
  - [x] 22.3 Show price difference and savings percentage
  - [x] 22.4 "Add to savings tracker" button on each card
  - _Req: R9 (Janaushadhi Cost Comparison)_

- [x] 23. Implement typing/thinking indicator
  - [x] 23.1 Show animated dots while search is in progress
  - [x] 23.2 Show "Searching AWS Knowledge Base..." or "Asking Sarvam AI..." text
  - [x] 23.3 Cancel button to abort in-flight request
  - [x] 23.4 Timeout after 60s with retry option
  - _Req: R1_

---

## Phase 6: Knowledge Base Document Upload
> _Upload PDFs/documents to AWS Bedrock KB_

- [x] 24. Create KB upload UI
  - [x] 24.1 Upload panel accessible from sidebar menu (📂 icon)
  - [x] 24.2 Drag-and-drop zone with visual feedback (dashed border, highlight)
  - [x] 24.3 File input: accept only PDF (`.pdf` extension filter)
  - [x] 24.4 ℹ️ tooltip: "Upload pharmaceutical documents to enhance search results"
  - [x] 24.5 Upload progress bar with percentage
  - [x] 24.6 Success/error toast notifications
  - _Req: R3 (KB Uploader)_

- [x] 25. Implement document list view
  - [x] 25.1 List all uploaded documents from AWS KB
  - [x] 25.2 Show document name, upload date, file size
  - [x] 25.3 Delete button per document (with confirmation dialog)
  - [x] 25.4 "Delete All" button (with double confirmation)
  - [x] 25.5 Empty state: "No documents uploaded yet"
  - [x] 25.6 Refresh button to re-fetch list
  - _Req: R3_

- [x] 26. Backend: Proxy KB operations
  - [x] 26.1 Add `/api/kb/upload` endpoint → proxy to AWS RAG `/api/index`
  - [x] 26.2 Add `/api/kb/documents` endpoint → proxy to AWS RAG `/api/documents`
  - [x] 26.3 Add `/api/kb/delete` endpoint → proxy to AWS RAG `/api/documents/delete`
  - [x] 26.4 Add `/api/kb/delete-all` endpoint → delete all KB documents
  - [x] 26.5 Add environment variable `AWS_RAG_BACKEND_URL` for backend URL
  - [x] 26.6 Error handling: surface AWS errors as user-friendly messages
  - _Req: R3, R20 (Backend Integration)_

---

## Phase 7: Prescription OCR & Medicine Extraction
> _Camera/upload → OCR → structured medicine list → compliance check each_

- [x] 27. Revamp prescription scanner UI
  - [x] 27.1 Camera capture button (using `navigator.mediaDevices.getUserMedia`)
  - [x] 27.2 Image upload area (drag-drop + file input)
  - [x] 27.3 Image preview with crop/rotate controls
  - [x] 27.4 "Scan Prescription" button
  - [x] 27.5 Loading state: "Analyzing prescription..."
  - _Req: R5 (Prescription OCR), R12 (PWA Camera Scanner)_

- [x] 28. Implement medicine extraction (LLM post-processing)
  - [x] 28.1 Send OCR text to Sarvam sarvam-m with extraction prompt
  - [x] 28.2 Prompt: "Extract all medicine names, dosages, frequencies from this prescription text"
  - [x] 28.3 Parse response into structured list: [{name, dosage, frequency, duration}]
  - [x] 28.4 Handle messy OCR: retry with "please try harder to extract medicine names"
  - [x] 28.5 Backend: create `/api/prescription-parse` endpoint
  - _Req: R5_

- [x] 29. Implement medicine checklist UI
  - [x] 29.1 Render extracted medicines as interactive checklist cards
  - [x] 29.2 Each card: checkbox + medicine name + dosage + frequency
  - [x] 29.3 "Check All" button → bulk compliance lookup
  - [x] 29.4 Individual "Check" button per medicine
  - [x] 29.5 Status indicators per medicine: ✅ Safe, 🚫 Banned, ⚠️ Warning, ⏳ Checking
  - [x] 29.6 Click on medicine → full search result in chat view
  - [x] 29.7 "Add all to chat" button → create new session with all medicine queries
  - _Req: R5, R7 (Drug Interaction)_

- [x] 30. Backend: prescription parse endpoint
  - [x] 30.1 Create `/api/prescription-parse` in `app.py`
  - [x] 30.2 Accept multipart form data with image file
  - [x] 30.3 Step 1: Send image to Sarvam OCR API
  - [x] 30.4 Step 2: Send OCR text to Sarvam sarvam-m for extraction
  - [x] 30.5 Step 3: Return structured medicine list + raw OCR text
  - [x] 30.6 Error handling: OCR failure, extraction failure, empty prescription
  - _Req: R5_

---

## Phase 8: Voice Integration Enhancement
> _Better STT/TTS with language awareness_

- [x] 31. Enhance STT (Speech-to-Text)
  - [x] 31.1 Use selected language for STT (not hardcoded `hi-IN`)
  - [x] 31.2 Visual recording indicator (red dot + waveform animation)
  - [x] 31.3 Cancel recording button
  - [x] 31.4 Auto-stop after 30 seconds
  - [x] 31.5 Insert recognized text into search bar
  - [x] 31.6 Confidence indicator on recognized text
  - _Req: R6 (Multilingual Voice-First)_

- [x] 32. Enhance TTS (Text-to-Speech)
  - [x] 32.1 Per-message TTS button in chat
  - [x] 32.2 Auto-detect language of response for TTS
  - [x] 32.3 Stop/pause button during playback
  - [x] 32.4 Queue TTS if multiple messages selected
  - [x] 32.5 Support all 10 Indian + 1 English language
  - _Req: R6_

- [x] 33. Implement auto-translate on responses
  - [x] 33.1 If user language ≠ English, auto-translate response
  - [x] 33.2 Show both original (English) and translated response
  - [x] 33.3 Toggle between original and translated
  - [x] 33.4 Translate button available even when language is English
  - _Req: R6_

---

## Phase 9: Drug Interaction Checker
> _Upgrade existing interaction tab to chat-integrated cards_

- [x] 34. Upgrade interaction checker UI
  - [x] 34.1 Move from separate tab → accessible via toolbar icon or command
  - [x] 34.2 Multi-drug input field (comma-separated or tag-style chips)
  - [x] 34.3 "Check Interactions" button
  - [x] 34.4 Results appear as chat message in current session
  - _Req: R7 (Drug Interaction Checker)_

- [x] 35. Enhance interaction results rendering 
  - [x] 35.1 Severity-coded badges: Critical (red), Moderate (amber), Minor (green)
  - [x] 35.2 Expandable sections for each interaction pair
  - [x] 35.3 Clinical significance and mechanism of action
  - [x] 35.4 "Learn more" links to authoritative sources
  - _Req: R7_

---

## Phase 10: Compliance PDF Export
> _Generate printable drug compliance reports_

- [x] 36. Implement client-side PDF generation
  - [x] 36.1 Add html2pdf.js library (CDN)
  - [x] 36.2 Create PDF template: header, drug info, status, citations, timestamp
  - [x] 36.3 Include PharmaAI branding and disclaimer
  - [x] 36.4 Export button on each AI response message
  - [x] 36.5 Export entire session as multi-page PDF
  - _Req: R8 (Compliance PDF Export)_

- [x] 37. PDF content formatting
  - [x] 37.1 Drug status section: name, status badge, gazette reference
  - [x] 37.2 Compliance details: ban date, uplift date, restrictions
  - [x] 37.3 Alternative medicines section
  - [x] 37.4 Citations and sources
  - [x] 37.5 Timestamp and query context
  - [x] 37.6 Legal disclaimer footer
  - _Req: R8_

---

## Phase 11: Settings & Personalization
> _Language, theme, accessibility preferences_

- [x] 38. Language settings panel
  - [x] 38.1 Language selector: 11 Indian languages + English
  - [x] 38.2 Persist selected language in localStorage
  - [x] 38.3 Apply language to STT/TTS/Translation automatically
  - [x] 38.4 UI labels remain in English (content translates)
  - _Req: R6_

- [x] 39. Theme settings
  - [x] 39.1 Light/Dark mode toggle
  - [x] 39.2 Dark mode CSS: use `--bg-dark`, `--text-dark` variables
  - [x] 39.3 Persist preference in localStorage
  - [x] 39.4 System preference detection (prefers-color-scheme)
  - [x] 39.5 Smooth transition animation
  - _Req: R19 (Theming & Accessibility)_

- [x] 40. Accessibility settings
  - [x] 40.1 Font size selector: Small / Medium / Large
  - [x] 40.2 High contrast mode toggle
  - [x] 40.3 Reduce motion toggle
  - [x] 40.4 Screen reader aria-labels on all interactive elements
  - [x] 40.5 Focus visible indicators on keyboard navigation
  - _Req: R19_

---

## Phase 12: Notifications & Alerts
> _Drug watch list and regulatory update alerts_

- [x] 41. Implement toast notification system
  - [x] 41.1 Create `js/notifications.js` with `showToast(message, type, duration)`
  - [x] 41.2 Types: success (green), error (red), warning (amber), info (teal)
  - [x] 41.3 Toast container: top-right, stack up to 3
  - [x] 41.4 Auto-dismiss after 5s with progress bar
  - [x] 41.5 Manual dismiss (X button)
  - _Req: R14 (Push Notifications — client-side)_

- [x] 42. Implement drug watch list
  - [x] 42.1 "Watch" button on search results
  - [x] 42.2 Store watched drugs in localStorage `pharmai_watched`
  - [x] 42.3 Watched drugs panel in sidebar
  - [x] 42.4 Visual indicator for status changes (if cached data differs)
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

- [x] 46. Restructure search endpoint for sessions
  - [x] 46.1 Accept `history` array in `/api/search` request body
  - [x] 46.2 Accept `spaceId` and `systemPrompt` params
  - [x] 46.3 Build contextual prompt from history + space instructions
  - [x] 46.4 Send to AWS RAG backend as primary search
  - [x] 46.5 Fallback to Sarvam sarvam-m on AWS failure
  - [x] 46.6 Return unified response: answer, source, citations, metadata, sessionId
  - _Req: R3, R4, R20_

- [x] 47. Add AWS RAG backend proxy routes
  - [x] 47.1 `POST /api/kb/upload` → proxy to AWS `/api/index`
  - [x] 47.2 `GET /api/kb/documents` → proxy to AWS `/api/documents`
  - [x] 47.3 `POST /api/kb/delete` → proxy to AWS `/api/documents/delete`
  - [x] 47.4 `DELETE /api/kb/delete-all` → delete all KB documents
  - [x] 47.5 Add `AWS_RAG_BACKEND_URL` environment variable
  - [x] 47.6 Add timeout handling (45s for search, 120s for upload)
  - _Req: R3, R20_

- [x] 48. Create prescription parse endpoint
  - [x] 48.1 `POST /api/prescription-parse` — accept multipart image
  - [x] 48.2 Step 1: Call Sarvam OCR parse/document
  - [x] 48.3 Step 2: Call Sarvam sarvam-m with extraction prompt
  - [x] 48.4 Step 3: Parse LLM response into structured medicine list
  - [x] 48.5 Retry logic: if extraction fails, re-prompt with "concentrate on medicine names"
  - [x] 48.6 Return: medicines[], ocr_text, confidence
  - _Req: R5_

- [x] 49. Enhance existing endpoints
  - [x] 49.1 `/api/stt` — accept language param (currently hardcoded `hi-IN`)
  - [x] 49.2 `/api/tts` — accept language param for multi-language support
  - [x] 49.3 `/api/translate` — accept source and target language
  - [x] 49.4 `/api/interaction` — return severity-coded results
  - [x] 49.5 Health endpoint: add version number `3.0`, component status
  - _Req: R6, R7, R20_

- [x] 50. Add CORS and error handling improvements
  - [x] 50.1 Standardize error response format: `{success: false, error: str, code: int}`
  - [x] 50.2 Add request logging for debugging
  - [x] 50.3 Add rate limiting headers
  - [x] 50.4 Add CORS headers for potential separate frontend deployment
  - _Req: R20_

---

## Phase 15: Urgent OCR Refactor (Phase R5)
> _Migrate from deprecated Sarvam sync OCR to strictly validated Async Jobs with AWS Bedrock extraction rules._

- [x] 51. Refactor `api_ocr` for Sarvam Async Job
  - [x] 51.1 Generate presigned URL via `/doc-digitization/job/v1`
  - [x] 51.2 Upload image to provided S3 URL
  - [x] 51.3 Trigger job with job_id via `/doc-digitization/job/v1/{job_id}` 
  - [x] 51.4 Implement blocking `time.sleep(1)` loop polling `/doc-digitization/job/v1/{job_id}` up to 10s
  - [x] 51.5 Download and reconstruct OCR text from output payload

- [x] 52. Adapt Frontend `ocr.js` State Persistence
  - [x] 52.1 Ensure "Extracting Text..." UI loader remains active for ~15 seconds without timing out
  - [x] 52.2 Check JS timeout thresholds on backend API calls to prevent front-end disconnect during the longer polling stage
  - [x] 52.3 Ensure error messaging for asynchronous failure cases bubble up correctly

- [x] 53. Implement Bedrock JSON Medicine Extraction
  - [x] 53.1 Inside backend extraction (`api_prescription_parse` or `app.py` wrapper): change LLM prompt to purely format extraction as an array of JSON objects
  - [x] 53.2 Strict prompt injection: `{"name": "...", "dosage": "...", "frequency": "..."}`
  - [x] 53.3 Bypass Sarvam's textual LLM for extraction—route directly to Bedrock Claude for entity extraction to guarantee structured layout

- [x] 54. Bedrock Interactive Compliance Search 
  - [x] 54.1 Update `/api/search` System Prompt to iterate over multiple medicine inputs accurately
  - [x] 54.2 Verify frontend mapping `parseMedicineList()` works seamlessly with Bedrock's output to render the checkbox list


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

- [x] 58. Mobile layout optimization
  - [x] 58.1 Sidebar → full-screen overlay on mobile
  - [x] 58.2 Touch gestures: swipe right → open sidebar
  - [x] 58.3 Chat messages: full-width on mobile
  - [x] 58.4 Bottom search bar: 95% width, 16px font (prevent iOS zoom)
  - [x] 58.5 Safe area insets for notched phones
  - _Req: R18 (Responsive Mobile-First)_

- [x] 59. Tablet layout optimization
  - [x] 59.1 Sidebar: collapsible (not always visible)
  - [x] 59.2 Chat area: max-width 800px centered
  - [x] 59.3 Tool panels: side-by-side if space permits
  - _Req: R18_

- [x] 60. Performance optimization
  - [x] 60.1 Lazy load images (prescription previews)
  - [x] 60.2 Debounce search input (300ms)
  - [x] 60.3 Virtual scroll for long session lists (50+ sessions)
  - [x] 60.4 Minimize DOM nodes (reuse message templates)
  - _Req: R18_

---

## Phase 20: Integration Testing & Polish
> _End-to-end testing of all features_

- [x] 61. Test session management
  - [x] 61.1 Create session, add messages, refresh page → session persists
  - [x] 61.2 Switch between sessions → correct messages show
  - [x] 61.3 Delete session → removed from sidebar
  - [x] 61.4 50+ sessions → oldest evicted with warning
  - _Req: R3_

- [x] 62. Test spaces
  - [x] 62.1 Create custom space with instructions
  - [x] 62.2 Search in space → instructions affect response
  - [x] 62.3 Switch spaces → search uses new space context
  - [x] 62.4 Delete space → sessions reassigned to General
  - _Req: R4_

- [x] 63. Test search pipeline
  - [x] 63.1 Query → gets KB response with citations
  - [x] 63.2 KB failure → falls back to Sarvam
  - [x] 63.3 Both fail → graceful error message
  - [x] 63.4 Multi-turn conversation → context preserved
  - _Req: R1, R3, R20_

- [x] 64. Test OCR pipeline
  - [x] 64.1 Upload prescription image → OCR text extracted
  - [x] 64.2 Medicine list extracted from OCR text
  - [x] 64.3 Check all medicines → compliance status shown
  - [x] 64.4 Click medicine → full search in chat
  - _Req: R5_

- [x] 65. Test voice features
  - [x] 65.1 Record voice → text appears in search bar
  - [x] 65.2 Click TTS on response → audio plays
  - [x] 65.3 Different languages → correct STT/TTS model used
  - _Req: R6_

- [x] 66. Test document upload
  - [x] 66.1 Upload PDF → appears in document list
  - [x] 66.2 Search for content from uploaded PDF → found in results
  - [x] 66.3 Delete document → no longer in results
  - _Req: R3_

- [x] 67. Test responsive design
  - [x] 67.1 Desktop (1440px) → sidebar + chat side by side
  - [x] 67.2 Tablet (768px) → sidebar collapsible
  - [x] 67.3 Mobile (375px) → sidebar overlay, full-width chat
  - [x] 67.4 Test on Chrome, Firefox, Safari mobile
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

- [x] 69. Update Dockerfile
  - [x] 69.1 Verify volume mount includes `css/`, `js/`, `assets/` dirs
  - [x] 69.2 Update Flask static file serving config
  - [x] 69.3 Add `sw.js` to root serving path
  - _Req: R20_

- [x] 70. Update docker-compose.yml
  - [x] 70.1 Add `AWS_RAG_BACKEND_URL` environment variable
  - [x] 70.2 Verify health check path
  - [x] 70.3 Test: `docker compose up -d --build`
  - _Req: R20_

- [x] 71. Verify production deployment
  - [x] 71.1 `curl -I https://medical.lehana.in/pharmai/` → 200 OK
  - [x] 71.2 `curl -I https://medical.aidhunik.com/pharmai/` → 200 OK
  - [x] 71.3 CSS/JS files load correctly via Traefik
  - [x] 71.4 All API endpoints reachable
  - [x] 71.5 Health check returns v3.0
  - _Req: R20_

---

## Phase 22: Documentation
> _README, CHANGELOG, inline docs_

- [x] 72. Update README.md
  - [x] 72.1 Update version to 3.0
  - [x] 72.2 Add file index for new `css/`, `js/`, `assets/` structure
  - [x] 72.3 Document all new features
  - [x] 72.4 Update API endpoint reference
  - [x] 72.5 Add architecture diagram
  - [x] 72.6 Add Quick Start section
  - _Req: Documentation standards_

- [x] 73. Create CHANGELOG.md
  - [x] 73.1 Document all changes from v2.0 → v3.0
  - [x] 73.2 Sections: Added, Changed, Fixed, Technical
  - _Req: Documentation standards_

- [x] 74. Create DEV_DEMO.md
  - [x] 74.1 curl commands for every API endpoint
  - [x] 74.2 Step-by-step testing scenarios
  - [x] 74.3 Configuration constants reference
  - _Req: Documentation standards_

- [x] 75. Update inline documentation
  - [x] 75.1 JSDoc comments on all JS functions
  - [x] 75.2 Python docstrings on all Flask endpoints
  - [x] 75.3 CSS section comments
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

- [x] 77. Create demo script
  - [x] 77.1 Step-by-step demo flow for judges
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

- [x] 87. Bug Fixes (Identified during testing)
  - [x] 87.1 Fix Sarvam Bulbul TTS speaker validation error (change `meera` to `anushka`, `bulbul:v3` to `bulbul:v2`)
  - [x] 87.2 Fix CSS bugs (Toast animations, inline styles, dark mode toggle)
  - [x] 87.3 Fix index.html CSS/JS loading versions

---

## Phase R1: UX Redesign, AWS Bedrock Migration & Session Privacy
> **Reference**: [plan_R1.md](plan_R1.md)

### R1.1 — Fix Broken Proxy URLs (CRITICAL — root cause of "Unable to reach medicine databases")
- [x] R1.1.1 In `app.py`, change `api_upload_files()` proxy URL from `https://medical.lehana.in/ncert/api/index` → `http://localhost:4101/api/index`
- [x] R1.1.2 In `app.py`, change `api_list_documents()` proxy URL from `https://medical.lehana.in/ncert/api/documents` → `http://localhost:4101/api/documents`
- [x] R1.1.3 In `app.py`, change `api_delete_document()` proxy URL from `https://medical.lehana.in/ncert/api/documents/delete` → `http://localhost:4101/api/documents/delete`
- [x] R1.1.4 In `app.py`, change `api_delete_all_documents()` proxy URL from `https://medical.lehana.in/ncert/api/documents/all` → `http://localhost:4101/api/documents/all`

### R1.2 — AWS Bedrock Migration (Replace sarvam-m with AWS RAG)
- [x] R1.2.1 Add `AWS_RAG_BASE_URL` constant in `app.py` pointing to `http://localhost:4101`
- [x] R1.2.2 Rewrite `search_tier2_sarvam()` → `search_tier2_aws()` to call `AWS_RAG_BASE_URL/api/search` instead of Sarvam `sarvam-m`
- [x] R1.2.3 Update `search_medicine()` to call `search_tier2_aws()` instead of `search_tier2_sarvam()`
- [x] R1.2.4 Rewrite `api_interaction()` to use AWS RAG `/api/search` instead of Sarvam `sarvam-m` chat completions
- [x] R1.2.5 Rewrite `api_doc_analysis()` Step 2 (AI Interpretation) to use AWS RAG `/api/search` instead of Sarvam `sarvam-m`
- [x] R1.2.6 Remove all `sarvam-m` model references from text-reasoning endpoints (keep Sarvam for STT/TTS/OCR/Translate only)
- [x] R1.2.7 Update docstring and startup print to reflect AWS RAG backend instead of Sarvam for reasoning

### R1.3 — Jan Aushadhi System Prompt Enhancement
- [x] R1.3.1 Append Jan Aushadhi instructions to `PHARMAI_SYSTEM_PROMPT` in `app.py` — request generic equivalents + cost savings for every branded medicine
- [x] R1.3.2 Add a Jan Aushadhi-specific section in the search prompt format with price comparison formatting

### R1.4 — Landing Page Redesign (Remove 12 boxes → 4 action cards)
- [x] R1.4.1 Remove 6 static `.feature-card` divs from `index.html` (the features-grid section)
- [x] R1.4.2 Reduce `TEMPLATE_QUERIES` in `app.js` from 6 items to 4 focused action cards: Search, OCR Scan, Drug Interaction, Jan Aushadhi
- [x] R1.4.3 Update `renderTemplateCards()` to render 4 action-oriented cards with clearer CTAs
- [x] R1.4.4 Update `.features-grid` CSS to 2x2 grid or remove entirely; adjust `.landing-view` padding/whitespace
- [x] R1.4.5 Tighten `.landing-hero` spacing: reduce margins, padding, and font sizes for conciseness
- [x] R1.4.6 Update hero badge text and stats-row to reflect AWS Bedrock branding

### R1.5 — Sidebar Auto-Open & Blur Fix
- [x] R1.5.1 In `sidebar.js` `initSidebar()`, remove automatic `openSidebar()` call on desktop (>=1024px) — sidebar should start closed
- [x] R1.5.2 Reduce `.sidebar-backdrop` blur from `blur(4px)` to `blur(2px)` in `layout.css`
- [x] R1.5.3 Verify landing view is unblurred on first load (both mobile and desktop)

### R1.6 — Session Privacy (User-Keyed localStorage)
- [x] R1.6.1 In `auth.js` `onSuccess()`, store Descope `userId` (or email hash) in the user object for keying
- [x] R1.6.2 In `chat.js`, change `STORAGE_KEY_SESSIONS` from fixed `'pharmai_sessions'` to dynamic `'pharmai_sessions_' + userId`
- [x] R1.6.3 Create helper `getUserStorageKey()` that returns user-scoped key or falls back to anonymous key
- [x] R1.6.4 Update `loadSessions()` and `saveSessions()` to use user-scoped storage key
- [x] R1.6.5 Update `STORAGE_KEY_ACTIVE` to also be user-scoped (`pharmai_active_session_{userId}`)
- [x] R1.6.6 In `auth.js` `logout()`, clear the chat UI: call `showLandingView()`, reset `sessions = []`, reset `activeSessionId = null`
- [x] R1.6.7 Verify: log out + log in as different user → old sessions must NOT appear

### R1.7 — Unified Upload System
- [x] R1.7.1 In `index.html` Documents panel, remove separate `#docUploadBtn` button — merge into the drop zone click
- [x] R1.7.2 Make `#docDropZone` clickable (trigger `#docUploadInput` on click) with `multiple` attribute already present
- [x] R1.7.3 Update drop zone text to "Drop PDFs here or click to upload" for clarity
- [x] R1.7.4 Verify multi-file upload works: drop 2+ PDFs and confirm all get indexed

### R1.8 — Custom System Prompts Per Space
- [x] R1.8.1 In `index.html`, add inline editable textarea below the space selector dropdown for current space's system instruction
- [x] R1.8.2 In `spaces.js`, bind the textarea to the active space's `systemInstruction` field with auto-save on blur/change
- [x] R1.8.3 Show the system instruction textarea only when a non-default space is active
- [x] R1.8.4 Verify: editing the textarea updates the space instruction and affects subsequent search queries

### R1.9 — Remove Drug Interaction Duplication
- [x] R1.9.1 Merge interaction checker into the main search flow — remove separate `api_interaction()` sarvam-m endpoint from `app.py`
- [x] R1.9.2 Keep the interaction tool panel UI but have it feed into `performSearch()` (already done in `interaction.js`)
- [x] R1.9.3 Update tool panel description to clarify it's an AI-powered interaction search, not a separate database

### R1.10 — Version Bump & Health Endpoint Update
- [x] R1.10.1 Bump `APP_VERSION` in `app.js` from `'3.0.0'` → `'3.1.0'`
- [x] R1.10.2 Bump health endpoint version in `app.py` from `'2.1'` → `'3.1'`
- [x] R1.10.3 Update all `?v=3.0` cache-busting parameters in `index.html` to `?v=3.1`
- [x] R1.10.4 Update startup print message in `app.py` to reflect v3.1 and AWS RAG backend
- [x] R1.10.5 Update health `features` list to include `'aws-rag'`, `'jan-aushadhi'`, `'session-privacy'`

### R1.11 — End-to-End Testing
- [x] R1.11.0 Fix answer extraction bug: AWS RAG returns `text` field, not `answer` — fixed in search_tier2_aws, api_interaction, api_doc_analysis
- [x] R1.11.1 Test search via AWS RAG: query "Augmentin 625" → ✅ returns "ALLOWED" with explanation from Bedrock KB
- [x] R1.11.1b Test banned drug: query "Nimesulide" → ✅ returns "🚫 BANNED" badge with gazette reference
- [x] R1.11.2 Test document upload: .txt rejected (correct - only pdf/png/jpg/jpeg/webp allowed)
- [x] R1.11.3 Test document list: verify `/api/list-documents` → ✅ returns documents from AWS RAG backend (delhi.pdf, cdsco_banned etc.)
- [x] R1.11.4 Test document delete: `/api/delete-document` → ✅ returns "Document deleted successfully"
- [ ] R1.11.5 Test OCR flow: requires image file upload (browser-only — Sarvam OCR needs real image)
- [x] R1.11.6 Test drug interaction: Aspirin + Warfarin → ✅ returns severity "Dangerous", mechanism, Jan Aushadhi alternatives
- [ ] R1.11.7 Test session privacy: browser-only test (localStorage per-user keying)
- [ ] R1.11.8 Test landing page: browser-only test (4 action cards, no blur, no auto-open sidebar)
- [ ] R1.11.9 Test unified upload: browser-only test (drag PDFs into drop zone)
- [ ] R1.11.10 Test custom system prompts: browser-only test (create space with instruction)
- [x] R1.11.11 Test public Traefik URL: search via `https://medical.lehana.in/pharmai/api/search` → ✅ works
- [x] R1.11.12 Test TTS: POST `/api/tts` with `en-IN` → ✅ returns base64 audio (Sarvam Bulbul v2)
- [x] R1.11.13 Test health: `/health` → ✅ v3.1 with all new features listed

## Phase R3: Bug Fixes, OCR, Knowledge Base, & Jan Aushadhi

### Task 1: Prescription Scanner (OCR) Bug Fix
- [x] 1.1 In `frontend/app.py`, locate `api_ocr()`. The image payload contains a base64 header (`data:image/jpeg;base64,...`). Add logic to strip this header using `image_b64.split(',', 1)[1]` before `base64.b64decode()`.

### Task 2: Knowledge Base (KB) Glitches Resolution
- [x] 2.1 Individual Delete bug: In `frontend/app.py`, inside `api_list_documents()`, traverse the array of documents returned by backend and enforce `d['id'] = d.get('name')` so the correct ID is passed to frontend `js/documents.js` for deletion targeting. Completed: Fixed
- [x] 2.2 Delete All unclickable dead zone: In `frontend/css/components.css` (or `documents.css` if it exists) or directly modifying `frontend/js/documents.js`, ensure the "Delete All" button has `position: relative; z-index: 10;` to counteract `span.doc-count` overlap. Completed: Fixed
- [x] 2.3 Post-Delete Ghost Search logic: Inside `frontend/js/documents.js`, inside `deleteAllDocuments()` (and maybe individual delete too), flush the frontend chat session or context array to clear stale Bedrock vectors cached locally. Completed: Fixed
- [x] 2.4 "0 KB" label removal: Inside `frontend/js/documents.js`, in the `renderDocumentList()` function, remove `doc.size || '0 KB'` data-binding logic. Replace it visually with a generic "Uploaded PDF" label. Completed: Fixed
- [x] 2.5 Upload crash resolution: In `frontend/app.py` `api_upload_files()`, replace the `f.save(fpath)` into `../data/` logic. Import and use python's `tempfile.NamedTemporaryFile` or RAM buffering to bypass the read-only mounted container structure, guaranteeing AWS API transmission. Completed: Refactored api_upload_files to use memory bytes.

### Task 3: Unwanted Sarvam AI Search Mentions & Output Formatting
- [x] 3.1 Badge correction: In `frontend/js/chat.js` (around line 212), rewrite the ternary evaluating `msg.source`. Ensure `msg.source === 'aws-bedrock' ? '🔬 AWS Bedrock KB' : '🔬 AI Analysis'` instead of defaulting non-kb to `'🤖 Sarvam AI'`. Only TTS/STT/OCR should be labeled Sarvam.
- [x] 3.2 Formatting cleanup: In `frontend/app.py` `target_tier2_aws()`, remove the forcibly injected `\n🔬 **AI Analysis (AWS Bedrock KB)**\n\n` strings from final payloads to avoid duplication.
- [x] 3.3 Remove Regex Banned: In `frontend/app.py` `target_tier2_aws()`, remove regex mapping that forcefully injects `"🚫 BANNED"` prefix tags to the output. Let the LLM handle conversation naturally.
- [x] 3.4 Prompt relaxation: Deep dive `PHARMAI_SYSTEM_PROMPT` in `app.py`. Strip directives like "format Status:" that force BANNED repetition, ensuring a natural, fluid flow. Completed: Refactored app.py and chat.js to remove hardcoded Sarvam badges, forced BANNED strings, and relaxed prompts.

### Task 4: Jan Aushadhi Architecture Switch (LLM -> KB/UI)
- [x] 4.1 Remove Hallucination Prompting: Edit `PHARMAI_SYSTEM_PROMPT` in `app.py` to stop explicitly commanding the LLM to invent "percentage cost savings compared to branded prices". Completed: Suppressed hallucination in prompt.
- [x] 4.2 Jan Aushadhi UI Setup: In `frontend/index.html`, duplicate/create a tool panel for Jan Aushadhi (akin to the prescription scanner / KB). Add a sidebar button to trigger it. Completed: Built dedicated UI panel with Store Locator link and specific Knowledge Base PDF ingestion components.
- [x] 4.3 Add Jan Aushadhi PDF ingestion inside this same UI panel to explicitly allow queries running over those KB files exclusively, enabling real facts extraction. Completed: Built dedicated UI panel with Store Locator link and specific Knowledge Base PDF ingestion components.
- [x] 4.4 Add UI components in the Jan Aushadhi panel to allow location of nearby stores and getting full medicine lists via RAG. Completed: Built dedicated UI panel with Store Locator link and specific Knowledge Base PDF ingestion components.

## R3: Bulk Deletion Backend API
- [x] Create `POST /api/documents/delete_all` in AWS RAG
- [x] Integrate document soft/hard deletions
- [x] Format output correctly (`deleted_count`, `failed_count`)

## R4: Bulk Deletion Frontend Proxy Integration
- [x] Write R4 Plan Document
- [x] Remove sequential iterative delete call in `/api/delete-all-documents` route located in `frontend/app.py`
- [x] Issue direct cross-container POST to the AWS RAG backend and parse counts to UI

---

## Phase 16: Phase R6 - Resilience, Safety, and Async UX
> _Implement safeguards against base64 bloating, Handle AWS empty KB blocks natively, and improve Scanner UI UX._

- [ ] 55. Implement Sarvam Base64 Stripper
  - [ ] 55.1 Go to `_sarvam_async_ocr` in `app.py`.
  - [ ] 55.2 Apply Python `re.sub` regex isolating and cleanly slicing `![Image](data:image/jpeg;base64, ...)` bloat to prevent token limit crashes before returning the text.

- [ ] 56. Build AWS Empty KB Fallback Protocol
  - [ ] 56.1 Identify exactly where "Sorry, I am unable to assist you with this request." rejection is caught in `search_tier2_aws`.
  - [ ] 56.2 Add a new function `search_tier3_llm` to fallback on standard `PHARMAI_SYSTEM_PROMPT` querying Sarvam or Claude without RAG.
  - [ ] 56.3 Return gracefully so users searching for valid medicines still receive full medical interaction checks independent of DB state.

- [ ] 57. Upgrade Scanner UX to Non-Blocking Status
  - [ ] 57.1 Overhaul `js/ocr.js` `processOcrImage` to not block UI.
  - [ ] 57.2 Launch asynchronous global native `toast('Scanning document in background...', 'info')` popup instead of `ocrLoading` block.
  - [ ] 57.3 Return users to a free-roaming UI allowing usage of chat modules while backend processes OCR.
  - [ ] 57.4 Execute a final visual `toast('Scan Complete! Click to View Medicines.', 'success')` trigger capable of recalling the user context immediately and switching back to OCR tab.

---

## Phase R7: Jan Aushadhi Full Implementation
> _Redesign the Jan Aushadhi tool within the existing pharmai_portal with an accurate RAG knowledge base for generic alternatives and kendra locators._

- [x] 58. Frontend UI Redesign (Jan Aushadhi Panel) - Completed: Redesigned the Jan Aushadhi tool window to a clean tabbed structure with specific input fields for medicines and kendras.
  - [x] 58.1 Update `frontend/index.html` to locate the existing Jan Aushadhi `<div id="janAushadhiPanel">`.
  - [x] 58.2 Create a clean, modern tabbed interface within the panel for "Find Alternatives" and "Find a Kendra".
  - [x] 58.3 Build Tab 1 (Find Alternatives): Add an input field for the prescribed medicine name.
  - [x] 58.4 Build Tab 1 Results Container: Create a dynamic table/grid displaying the original medicine, Jan Aushadhi generic equivalent, MRP, and computed savings.
  - [x] 58.5 Build Tab 2 (Find a Kendra): Add an input field for City/State.
  - [x] 58.6 Build Tab 2 Results Container: Create a scrollable list of store result cards.
  - [x] 58.7 Add a "Get Directions" button to each locator card template.
  - [x] 58.8 Implement Smart URL construction for the "Get Directions" button (`https://www.google.com/maps/dir/?api=1&destination=${encodedAddress}`) with `target="_blank"`.

- [x] 59. Backend Intent Router - Completed: Built the /api/janaushadhi/query endpoint interfacing with AWS RAG, enforcing structured JSON with robust regex fallbacks.
  - [x] 59.1 Create a new endpoint in `frontend/app.py`, e.g., `@app.route('/api/janaushadhi/query', methods=['POST'])`.
  - [x] 59.2 Implement LLM Intent Classification logic inside the endpoint.
  - [x] 59.3 Pass the incoming query to an LLM router to classify the request as either `medicine_alternative` or `kendra_locator`.
  - [x] 59.4 Extract the relevant entity from the query (Medicine Pattern vs City/State Pattern) using the LLM.

- [x] 60. RAG Integrations for Medicine and Locate - Completed: Built the /api/janaushadhi/query endpoint interfacing with AWS RAG, enforcing structured JSON with robust regex fallbacks.
  - [x] 60.1 Implement logic for Medicine Query (`medicine_alternative`): Route query to the AWS RAG backend specifically targeting the Medicine PDF.
  - [x] 60.2 Construct Medicine RAG prompt: "Find the Jan Aushadhi equivalent and MRP for {medicine}".
  - [x] 60.3 Implement logic for Location Query (`kendra_locator`): Route query to the AWS RAG specifically targeting the Location PDF.
  - [x] 60.4 Construct Location RAG prompt: "Provide the exact addresses of all Jan Aushadhi Kendras located in {City/State}".
  - [x] 60.5 Enforce a strict structured JSON output layer post-RAG for Location queries (normalized array format: `locations: [{ name, address, pin }]`).
  - [x] 60.6 Enforce a strict structured JSON output layer post-RAG for Medicine queries (normalized array format: `medicines: [{ generic_name, original_name, mrp, savings_percentage }]`).
  - [x] 60.7 Integrate with the existing `/api/kb/upload` pipeline to ensure smooth ingestion of the two PDF files (Medicine and Kendra Locations) to the AWS RAG infrastructure.

- [ ] 61. Frontend Rendering Logic
  - [ ] 61.1 Update `frontend/js/main.js` (or the relevant main controller for Jan Aushadhi).
  - [ ] 61.2 Implement an async fetch call to `/api/janaushadhi/query` handling user input from both tabs.
  - [ ] 61.3 Add a loading state UI for both the "Find Alternatives" and "Find a Kendra" actions.
  - [ ] 61.4 Process the structured JSON responses (medicines vs locations arrays).
  - [ ] 61.5 Bind `medicines: [{...}]` payload to the Tab 1 Results table DOM elements.
  - [ ] 61.6 Bind `locations: [{...}]` payload to the Tab 2 Results store cards DOM elements.
  - [ ] 61.7 Handle edge cases, empty states, and errors (e.g., if no kendra is found, show a friendly fallback message).

- [ ] 62. Verification & Testing
  - [ ] 62.1 Run local server using `flask run` (or existing startup script).
  - [ ] 62.2 Test UI by typing a city (e.g., "Kerkera, Haryana") and confirm the Google Maps link successfully resolves to the generated text address.
  - [ ] 62.3 Test UI by typing a common drug (e.g., "Paracetamol 500mg").
  - [ ] 62.4 Verify the returned generic matches the uploaded RAG PDF and not raw LLM hallucination.

## Phase R8: Bedrock Direct chat, OCR constraints and removal of OpenRouter fallback

- [x] 58. Create `/api/chat` route in `AWS_RAG_CURD`. Use `boto3` client to call Anthropic Claude via Bedrock `InvokeModel` API block.
- [x] 59. Update `pharmai_portal/frontend/app.py` to remove OpenRouter / Gemini traces completely.
- [x] 60. Create `search_tier3_bedrock_direct()` mapped to the new `/api/chat` endpoint in `pharmai_portal/frontend/app.py`.
- [x] 61. In `pharmai_portal/frontend/app.py`, under the `extract_medicines` flow, reroute it to use this new Direct Chat Bedrock function instead of `search_tier2_aws`.
- [x] 62. In `pharmai_portal/frontend/app.py`, expand the max token limit in `doc-analysis` from 3,000 characters to 15,000.
