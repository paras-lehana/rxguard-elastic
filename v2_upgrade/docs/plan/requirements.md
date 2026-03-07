# PharmaAI v3.0 — Requirements Document (AWS AI for Bharat Round 2)

## Introduction

**Problem Statement:** India's 60,000+ drug ecosystem suffers from a compliance crisis. CDSCO bans 35+ drugs monthly, yet no centralized system exists for real-time verification. Patients unknowingly consume banned drugs. Pharma companies face ₹500 Cr+ annual litigation. Google and standalone LLMs fail at tracking regulatory changes. PharmaAI aims to be the definitive real-time drug compliance & health intelligence platform for India.

**Target Users:**
- **Patients** — Check prescriptions, find affordable alternatives, get health reminders
- **Doctors** — Real-time drug compliance dashboard with judicial order tracking
- **Pharmacists** — Drug ban alerts, Janaushadhi substitution recommendations
- **Pharma Companies** — Regulatory compliance SaaS, audit defense toolkit
- **Government (Janaushadhi Network)** — Inventory sync, automated substitution

**Key Value Proposition:** First-in-market platform combining real-time Gazette parsing + prescription OCR + health tracking + Janaushadhi cost optimization — all powered by AWS Bedrock KB + Sarvam AI.

**Project Context:**
- **Repository:** `/root/repo/pharmai_portal/`
- **Frontend Code:** `/root/repo/pharmai_portal/frontend/` (in-place upgrade)
- **AWS RAG Backend:** `/home/ubuntu/AWS_RAG_CURD/` (FastAPI + Bedrock KB + Kendra)
- **Existing Flask Proxy:** `/root/repo/pharmai_portal/frontend/app.py`
- **Docker Config:** `/root/docker/pharma-frontend/`
- **Live URL:** `https://medical.lehana.in/pharmai` and `https://medical.aidhunik.com/pharmai`
- **Tech Stack:** Vanilla HTML/CSS/JS frontend, Flask backend proxy, Sarvam AI APIs, AWS Bedrock KB, Kendra GenAI Index

---

## Glossary

- **CDSCO** — Central Drugs Standard Control Organisation (India's drug regulator)
- **FDC** — Fixed Dose Combination (specific multi-drug combos, many are banned)
- **Gazette** — Official Government of India publication announcing drug bans/approvals
- **KB** — Knowledge Base (AWS Bedrock Knowledge Base backed by Kendra GenAI Index)
- **RAG** — Retrieval-Augmented Generation (LLM + document retrieval)
- **Sarvam AI** — Indian AI platform providing STT, TTS, translation, and LLM services
- **Janaushadhi** — Government scheme providing affordable generic medicines
- **Space** — User-defined context/persona that customizes AI behavior (like Perplexity Spaces)
- **Session** — A single conversational thread with maintained query history
- **OCR** — Optical Character Recognition (extracting text from images/PDFs)

---

## Requirements

### Requirement 1: Perplexity-Style Conversational Search UI

**User Story:** As a patient or pharmacist, I want to search for drug information in a chat-like conversational interface, so that I can have a natural dialogue with the AI and maintain context across multiple queries.

#### Acceptance Criteria

1. WHEN the user lands on the home page, THE system SHALL display a clean, centered search bar with suggested search prompts (template cards) below it — no hero banner or feature grids cluttering the initial view.
2. WHEN the user submits a search query, THE system SHALL create a new session with a unique ID and transition to a conversational chat view displaying the query as a user message and the response as an AI message.
3. WHEN the user submits a follow-up query within the same session, THE system SHALL append it to the existing conversation thread (maintaining visual chat history) and send the full conversation context to the backend.
4. THE system SHALL render AI responses using rich markdown with status badges (✅ ALLOWED, 🚫 BANNED, ⚠️ RESTRICTED), collapsible sections, citation links, and source indicators.
5. WHEN the response includes cited documents, THE system SHALL display clickable citation markers that expand to show the source document name and relevant excerpt.
6. THE system SHALL maintain the fixed bottom search bar persistently across all views for quick follow-up queries.
7. WHEN the user starts typing, THE system SHALL show autocomplete suggestions from recent searches and popular queries.

---

### Requirement 2: Search History Sidebar (Hamburger Menu)

**User Story:** As a returning user, I want to access my past search sessions from a sidebar, so that I can continue previous conversations or reference earlier findings.

#### Acceptance Criteria

1. THE system SHALL display a hamburger menu icon (☰) in the top-left corner of the page.
2. WHEN the user clicks the hamburger icon, THE system SHALL slide open a sidebar from the left displaying a chronologically ordered list of past search sessions.
3. EACH session entry SHALL show: the first query text (truncated to 50 chars), a timestamp (relative: "2h ago", "Yesterday"), and the number of messages in that session.
4. WHEN the user clicks a past session, THE system SHALL load the full conversation history into the main chat view and restore the session context.
5. THE system SHALL store session history in `localStorage` with a maximum of 50 sessions. Sessions older than 30 days SHALL be automatically pruned.
6. THE sidebar SHALL include a "New Chat" button at the top that clears the current conversation and starts a fresh session.
7. THE sidebar SHALL include a search/filter input to search through past session titles.
8. THE system SHALL support deleting individual sessions via a swipe gesture or delete icon.

---

### Requirement 3: Knowledge Base Document Uploader

**User Story:** As an admin or researcher, I want to upload regulatory documents (PDFs) to the knowledge base through a clean upload interface, so that the AI can reference them during drug compliance searches.

#### Acceptance Criteria

1. THE system SHALL provide a dedicated "Upload" panel accessible from the navigation.
2. THE upload interface SHALL display a drag-and-drop zone labeled "Upload Reference Document" with a subtle (ℹ️) tooltip on hover indicating "Only PDF files are supported."
3. THE system SHALL NOT mention specific document types (gazette, CDSCO, etc.) in the upload UI — it must remain generalized.
4. WHEN a file is dropped or selected, THE system SHALL validate it is a PDF and show the filename, size, and an upload progress indicator.
5. WHEN the user clicks "Upload", THE system SHALL POST the file to the AWS RAG backend's `/api/index` endpoint and display success/failure status.
6. THE system SHALL display a list of currently indexed documents fetched from `/api/documents`, showing document name, status (ACTIVE/INDEXING), and a delete button.
7. THE upload zone SHALL reject non-PDF files with a clear error message.
8. THE system SHALL show upload progress with a percentage bar and support cancellation.
9. WHEN multiple files are dragged in, THE system SHALL queue them and upload sequentially with per-file status indicators.

---

### Requirement 4: Spaces & Persona Management

**User Story:** As a power user (doctor, pharmacist, researcher), I want to create custom Spaces with predefined system instructions, so that every new search session within that space uses my preferred AI behavior and context.

#### Acceptance Criteria

1. THE system SHALL provide a "Spaces" section accessible from the sidebar or navigation.
2. THE system SHALL ship with 3 default spaces:
   - **General** — Default PharmaAI behavior (no custom instructions)
   - **Doctor Mode** — "Provide clinical-grade responses with drug interactions, contraindications, and dosage details. Include CDSCO references."
   - **Patient Mode** — "Explain in simple language. Avoid medical jargon. Focus on safety and affordable alternatives."
3. WHEN the user creates a new space, THE system SHALL present a form with:
   - Space Name (required, max 50 chars)
   - System Instructions (required, textarea, max 2000 chars)
   - Icon/Emoji selector (optional)
4. WHEN a space is selected and the user starts a new search session, THE system SHALL prepend the space's system instructions to every query sent to the backend.
5. THE system SHALL visually indicate the currently active space in the search bar area (e.g., "Searching in: Doctor Mode 🩺").
6. Spaces SHALL be stored in `localStorage` with support for edit, delete, and duplicate operations.
7. THE system SHALL allow switching spaces mid-conversation by displaying a space selector dropdown near the search bar.
8. WHEN switching spaces, THE system SHALL start a new session (not modify the existing conversation's context).

---

### Requirement 5: Prescription OCR & Actionable Medicine Extraction

**User Story:** As a patient, I want to upload a photo of my prescription and have the AI automatically identify all medicines with dosages, then let me search for compliance information on each one.

#### Acceptance Criteria

1. THE system SHALL provide a dedicated "Prescription Scanner" tab/panel with camera capture (on mobile) and file upload support.
2. WHEN a prescription image is uploaded, THE system SHALL send it to the OCR endpoint and display a loading state ("Scanning prescription...").
3. WHEN OCR completes, THE system SHALL parse the extracted text using an LLM to identify individual medicines with structured fields: Medicine Name, Dosage, Frequency, Duration.
4. THE system SHALL display the extracted medicines as an editable checklist where users can:
   - Edit medicine names (to fix OCR errors)
   - Remove incorrectly detected items
   - Add manually missed medicines
5. THE extracted list SHALL include a prominent "Search All Medicines" button that triggers a batch search, creating a new session for each medicine or a consolidated session.
6. FOR EACH medicine, THE system SHALL show a mini compliance badge (✅/🚫/⚠️) once the search completes.
7. THE system SHALL support both image files (JPG, PNG, WebP) and PDF prescriptions.
8. ON mobile devices, THE system SHALL offer a "Take Photo" button using the device camera API for instant prescription capture.
9. THE OCR pipeline SHALL chain: Sarvam OCR → LLM extraction prompt → structured JSON output → UI checklist.

---

### Requirement 6: Multilingual Voice-First Interface

**User Story:** As a rural Indian user who may not be literate in English, I want to search for drug information by speaking in my language and get results read aloud to me.

#### Acceptance Criteria

1. THE voice search button (🎙️) SHALL be prominently placed in the search bar.
2. WHEN the user taps the mic button, THE system SHALL immediately begin recording and show a visual recording indicator (pulsing animation + "Listening...").
3. WHEN recording stops (tap again or 15s auto-stop), THE system SHALL send audio to Sarvam STT and transcribe in the detected language.
4. THE transcribed text SHALL auto-populate the search bar and auto-trigger a search.
5. WHEN results are displayed, THE system SHALL show a "Read Aloud" button per response message.
6. THE TTS SHALL use the user's preferred language setting (configured in Settings).
7. THE system SHALL support all 11 Sarvam-supported Indian languages: English, Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi, Odia.
8. THE system SHALL auto-detect the input language from STT and set response language accordingly.

---

### Requirement 7: Drug Interaction Checker

**User Story:** As a patient taking multiple medications, I want to check if two or more drugs are safe to take together.

#### Acceptance Criteria

1. THE drug interaction checker SHALL be accessible from a dedicated panel or as a quick-action from within a chat session.
2. THE system SHALL accept 2+ medicine names as input.
3. THE system SHALL display results with severity categorization: Safe ✅, Caution ⚠️, Dangerous 🚫.
4. THE results SHALL include: interaction mechanism, clinical significance, and recommendation.
5. THE interaction check SHALL use Sarvam AI's chat model with the PharmaAI system prompt.
6. THE system SHALL allow adding interaction results to the current session chat history.

---

### Requirement 8: Compliance PDF Export

**User Story:** As a hospital compliance officer, I want to generate a downloadable PDF report summarizing a drug's regulatory status with all referenced gazette notifications.

#### Acceptance Criteria

1. WHEN viewing a search result, THE system SHALL show an "Export PDF" action button.
2. THE generated PDF SHALL include: drug name, compliance status, gazette references, ban/approval dates, source documents, and a timestamp.
3. THE PDF SHALL include the PharmaAI branding and a disclaimer.
4. THE PDF generation SHALL happen client-side using a JS library (e.g., jsPDF or html2pdf).

---

### Requirement 9: Janaushadhi Cost Comparison Cards

**User Story:** As a patient, when I search for a drug, I want to see affordable Janaushadhi alternatives displayed as side-by-side comparison cards showing cost savings.

#### Acceptance Criteria

1. WHEN a drug search result is displayed AND the drug is not banned, THE system SHALL show a "Cheaper Alternatives" section with comparison cards.
2. EACH comparison card SHALL display: branded drug price, generic alternative name, generic price, savings percentage, and availability indicator.
3. THE cards SHALL use a visually appealing side-by-side layout with savings highlighted in green.
4. IF no alternatives are found, THE system SHALL display "No Janaushadhi alternatives available for this medicine."
5. THE cost data SHALL be fetched from the backend (initially mock data, later from Janaushadhi API integration).

---

### Requirement 10: Explainable AI — Source Citations

**User Story:** As a doctor or regulator, I want to see exactly which source documents the AI used to generate its response, so I can verify the information's accuracy.

#### Acceptance Criteria

1. WHEN the AI response includes citations from the KB, THE system SHALL display numbered citation markers [1], [2], etc. inline in the response text.
2. WHEN the user clicks a citation marker, THE system SHALL show a popover/tooltip with: source document name, relevant text excerpt, and confidence score.
3. THE system SHALL display a "Sources" section below the response listing all referenced documents.
4. IF the response comes from Sarvam AI (Tier 2), THE system SHALL clearly indicate "AI-generated response (not from regulatory database)" with appropriate styling.

---

### Requirement 11: Role-Based Default Workspaces

**User Story:** As PharmaAI, the system should ship with pre-configured role-based workspaces that provide tailored experiences for different user types without any setup.

#### Acceptance Criteria

1. THE system SHALL provide 3 immutable default spaces: Doctor Mode, Patient Mode, Pharmacist Mode.
2. DEFAULT spaces SHALL NOT be editable or deletable by users.
3. EACH default space SHALL have a distinct icon and color theme.
4. THE Patient Mode SHALL use simpler language and emphasize safety and cost.
5. THE Doctor Mode SHALL include clinical references and interaction warnings.
6. THE Pharmacist Mode SHALL emphasize regulatory compliance and substitution options.

---

### Requirement 12: PWA Camera Scanner

**User Story:** As a mobile user, I want to scan prescriptions directly from my phone's camera without downloading a separate app.

#### Acceptance Criteria

1. THE prescription scanner SHALL support `navigator.mediaDevices.getUserMedia` for camera access on mobile browsers.
2. THE system SHALL show a camera preview with a capture button overlay.
3. WHEN the user captures an image, THE system SHALL immediately process it through the OCR pipeline.
4. THE camera interface SHALL work on Chrome Android, Safari iOS, and other major mobile browsers.
5. THE system SHALL gracefully degrade to file upload on browsers that don't support camera API.

---

### Requirement 13: Progressive Enhancement & Offline Caching

**User Story:** As a rural user with poor connectivity, I want the app to load quickly and cache common drug statuses locally.

#### Acceptance Criteria

1. THE system SHALL register a Service Worker for asset caching (HTML, CSS, JS).
2. THE system SHALL cache the top 100 most-queried drug statuses in `localStorage` for offline access.
3. WHEN offline, THE system SHALL indicate "Offline — showing cached results" and display cached data if available.
4. WHEN the user comes back online, THE system SHALL sync and update the cache.
5. THE system SHALL implement a `manifest.json` for PWA installability.

---

### Requirement 14: Real-Time Push Notifications

**User Story:** As a pharmacist, I want to subscribe to specific drugs and receive alerts when their regulatory status changes.

#### Acceptance Criteria

1. THE system SHALL provide a "Watch this drug" toggle on search results.
2. Watched drugs SHALL be stored in `localStorage`.
3. THE system SHALL check for status changes periodically when the app is open (polling or SSE).
4. WHEN a status change is detected, THE system SHALL display an in-app notification toast.
5. (FUTURE) THE system SHALL support browser push notifications via service worker.

---

### Requirement 15: Enterprise API Key Management

**User Story:** As a pharma company IT admin, I want to generate API keys so our internal systems can query PharmaAI programmatically.

#### Acceptance Criteria

1. THE system SHALL provide an "API Keys" section in Settings for authenticated users.
2. THE admin SHALL be able to generate, view, and revoke API keys.
3. API keys SHALL be stored securely and displayed only once upon creation.
4. THE system SHALL show usage statistics per key (request count, last used).
5. (FUTURE) API key authentication SHALL be implemented in the Flask backend with rate limiting.

---

### Requirement 16: WhatsApp Bot Bridge

**User Story:** As a rural user without smartphone access to the web app, I want to query drug information via WhatsApp.

#### Acceptance Criteria

1. THE system SHALL provide a WhatsApp integration endpoint in the backend that accepts incoming messages from Meta's WhatsApp Business API.
2. THE endpoint SHALL parse the user's message, query the Bedrock KB, and return a formatted response.
3. THE response SHALL include the drug's compliance status, a brief summary, and a link to the full web report.
4. (FUTURE PHASE) THE system SHALL support media messages (prescription photos) for OCR processing via WhatsApp.

---

### Requirement 17: Gamified Substitution Cards with Savings Tracker

**User Story:** As a patient, I want to track how much money I've saved by switching to generic alternatives, displayed in a visually engaging way.

#### Acceptance Criteria

1. THE system SHALL maintain a "Savings" counter in `localStorage` that accumulates each time a user acknowledges a generic substitution.
2. THE system SHALL display a savings dashboard showing: total saved, number of substitutions, and a comparison chart.
3. Each substitution card SHALL show a clear visual comparison with animated cost savings (e.g., "You save ₹75/strip!").

---

### Requirement 18: Responsive Mobile-First Design

**User Story:** As a mobile-first Indian user, I need the entire application to work flawlessly on mobile screens.

#### Acceptance Criteria

1. THE entire UI SHALL be responsive with breakpoints at: 320px (small phone), 375px (standard phone), 768px (tablet), 1024px+ (desktop).
2. THE search bar SHALL span full width on mobile with appropriately sized touch targets (min 44px).
3. THE sidebar SHALL be a full-screen overlay on mobile devices.
4. ALL interactive elements SHALL have touch-friendly spacing (no elements closer than 8px apart).
5. THE chat messages SHALL have appropriate font sizes for mobile readability (min 14px body text).
6. THE system SHALL NOT require pinch-to-zoom for any content.

---

### Requirement 19: Theming & Accessibility

**User Story:** As a user with visual impairments, I need the app to be accessible and support high-contrast mode.

#### Acceptance Criteria

1. THE system SHALL maintain WCAG 2.1 AA color contrast ratios (minimum 4.5:1 for text).
2. ALL interactive elements SHALL have proper ARIA labels.
3. THE system SHALL support keyboard navigation (Tab, Enter, Escape).
4. THE system SHALL preserve the existing Aura Design System color palette (teal primary, amber accent).
5. THE system SHALL support a dark mode toggle stored in `localStorage`.

---

### Requirement 20: Backend Integration — AWS RAG Backend Proxy

**User Story:** As the system, I need the Flask backend to seamlessly proxy requests to the AWS RAG backend for document operations and KB search while maintaining the existing Sarvam AI integrations.

#### Acceptance Criteria

1. THE Flask backend SHALL proxy `/api/search` to the AWS RAG backend when a KB search is requested, falling back to Sarvam AI (Tier 2).
2. THE Flask backend SHALL proxy `/api/upload-files`, `/api/list-documents`, `/api/delete-document`, `/api/delete-all-documents` to the AWS RAG backend endpoints.
3. THE backend SHALL maintain session context by storing conversation history server-side (in-memory dict initially, DynamoDB later).
4. THE backend SHALL inject space system instructions into the Bedrock RAG prompt template when a space is active.
5. THE backend SHALL support a new `/api/prescription-parse` endpoint that chains OCR → LLM extraction → structured medicine list.
6. THE backend SHALL implement a `/api/export-pdf` endpoint for server-side PDF generation.
7. ALL existing endpoints (STT, TTS, translate, interaction, doc-analysis) SHALL continue working unchanged.
