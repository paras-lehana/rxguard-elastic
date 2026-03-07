Plan: Phase R2 — Fix 6 Critical Issues + UX Improvements
TL;DR: Remove redundant drug interaction feature entirely, replace drag-drop-first with click-to-upload-first UX on all upload zones, fix logout button click issue (z-index/pointer-events), debug and fix delete operations (field name mismatch), fill landing page whitespace with engaging features (recent activity, quick tools row, "How It Works" steps), and enhance sidebar with hover-to-peek and click-outside-to-close behavior.

Steps

1. Remove Drug Interaction Feature Entirely
The interaction panel is 100% redundant — interaction.js line 23 just calls performSearch(query) which is exactly what typing in the search bar does. Remove all traces:

Delete js/interaction.js file
In index.html: Remove <script src="js/interaction.js"> tag (around line 322), remove #toolPanel-interaction div (lines 157-178), remove sidebar #toolInteraction button (line 93)
In app.py: Remove api_interaction() endpoint (lines ~493-529), remove interaction-check from health features list
In app.js: Remove the "Drug Interaction" entry from TEMPLATE_QUERIES (line 79-81), remove toolInteraction event listener from setupSidebarToolButtons() (line 143), remove 'interaction' from showToolPanel logic
Replace the removed template card with something useful like "Check Side Effects" or "Compare Medicines"
2. Fix All Upload Zones — Click-to-Upload as Primary (Not Drag-Drop)
User is clear: drag-drop is secondary, click-to-upload must be primary.

OCR Upload Zone (index.html line 141):

Add onclick="document.getElementById('ocrFileInput').click()" and style="cursor:pointer" to #ocrDropZone
Change text from "Drop a prescription image here" → "Click to upload or drop a prescription image"
In ocr.js initOcr(): Add click listener on #ocrDropZone that triggers #ocrFileInput.click() with stopPropagation() on the file input
KB Upload Zone (index.html line 192):

Move #docUploadInput outside #docDropZone to prevent click event propagation loops (the <input> nested inside the <div onclick> causes the click to bubble back)
Or: Remove onclick attribute, add proper click listener in documents.js with stopPropagation() on the input
Change text from "Drop PDF documents here or click to upload" → "Click to upload PDF documents"
Backend CORS Fix (app.py line 598):

Add OPTIONS method to api_upload_files() route
Add _cors_preflight() handler
Change all jsonify() calls to _cors_json() in the upload function
3. Fix Logout Button Not Clickable
The logout button HTML exists at index.html line 53 and the click listener is wired at auth.js line 54. The logout() function at auth.js line 98 looks correct. Possible causes:

z-index overlap: Top bar is z-index: 900, sidebar is z-index: 800. When sidebar is open, the backdrop (z-index: 799) could sit over the top bar area on some browsers. But the top bar should be above.
.user-info container intercepting clicks: The .user-info div wraps the avatar, name, AND logout button. It has border-radius: var(--radius-full) which could clip the button on narrow viewports.
Descope SDK overlay: The Descope widget may overlay the top-right area.
Fix approach:

In auth.js: Add a direct document.addEventListener('click') backup listener that checks e.target.id === 'logoutBtn' or e.target.closest('#logoutBtn') — this ensures clicks always reach the logout handler even if event propagation is blocked
Add position: relative; z-index: 1; to .logout-btn in layout.css to ensure it's above any overlapping elements
Also add pointer-events: auto; explicitly to the logout button CSS
Also fix the auto-login issue: In init() at auth.js line 21, the early localStorage return skips Descope token validation. Change to: still show cached user data (for display), but asynchronously validate the Descope session — if invalid, clear the cache and show login state
4. Fill Landing Page Whitespace with Engaging Features
Currently all content is constrained to 520-560px max-width centered on screen, wasting ~60% of horizontal space on desktop. User wants useful features in that space.

Changes to css/layout.css and css/components.css:

Increase .landing-hero max-width from 560px → 900px
Increase .template-grid max-width from 520px → 850px
Change template grid from repeat(2, 1fr) → repeat(auto-fill, minmax(180px, 1fr)) (so it goes 3-4 columns on desktop, 2 on tablet, 1 on mobile)
New landing page sections (add to index.html inside .landing-view):

"How It Works" steps row — 3 horizontal cards: (1) "Type or speak your medicine query" (2) "AI searches 50,000+ drugs + CDSCO gazette" (3) "Get ban status, generics & savings". Spans full width with icons. This fills horizontal space and educates users.
"Quick Tools" horizontal bar — Upload Prescription, Voice Search, Browse KB — 3 large clickable cards below the template grid that link directly to tool panels. Provides direct access without needing the sidebar.
"Featured Searches" / Trending section — Show 6-8 commonly searched medicines as clickable pills/chips that auto-fill the search. e.g., "Paracetamol", "Augmentin 625", "Nimesulide", "Metformin". Spans full width.
5. Fix Delete Operations
Single document delete — field name mismatch:

documents.js line 115 sends { document_id: docId } but app.py line 659 expects documentId. Fix: change document_id → documentId in documents.js
Delete all documents:

app.py line 676 proxies to DELETE /api/documents/all on the AWS RAG backend. Need to verify this endpoint exists. If not, implement iterate-and-delete: fetch all docs via /api/documents, then delete each one.
Add better error handling and user feedback in documents.js deleteAllDocuments()
6. Sidebar UX Improvements
User wants: (a) sidebar opens on hover over hamburger area, (b) clicking sidebar tool buttons directly opens the panel without needing to open sidebar first, (c) clicking outside the sidebar closes it.

Changes to sidebar.js:

Add mouseenter listener on the hamburger button area (or left edge strip) that calls openSidebar() after a short delay (200ms) to enable hover-to-peek
Add mouseleave on the sidebar itself that calls closeSidebar() after a delay (500ms), cancelled if mouse re-enters
Backdrop click-to-close already exists at sidebar.js line 80 — verify it works on desktop too (currently may only have backdrop on mobile)
Changes to layout.css:

Show sidebar backdrop on desktop too (currently may be mobile-only via media query) so clicking outside closes it
Or: Add a desktop-specific behavior where clicking the main content area closes sidebar without a visible backdrop
Direct tool access:

In app.js setupSidebarToolButtons(): When a tool button is clicked in sidebar, call showToolPanel() AND closeSidebar() in sequence — currently closeSidebarMobile() only closes on mobile (line 47 of app.js)
Verification

Drug interaction: sidebar button, template card, panel, backend endpoint, JS file — all removed
OCR upload: click the drop zone on desktop → file picker opens
KB upload: click the zone on desktop → file picker opens, file uploads, response shows success/error
Logout: click button → user is logged out, landing page shown, sessions cleared
Landing page: on 1920px screen, content fills width with "How It Works" + "Quick Tools" + "Trending" sections
Delete document: delete single doc → actually deleted from KB
Delete all docs: confirm dialog → all docs removed
Sidebar: hover over hamburger → sidebar peeks open; click outside → closes; click tool button → panel opens directly
Decisions

Drug interaction: fully delete, not hide — user explicitly wants it gone
Upload: click-to-upload is primary, drag-drop kept as secondary (but not emphasized)
Landing page: add 3 new sections ("How It Works", "Quick Tools", "Trending Searches") to fill whitespace with useful engaging content rather than just widening existing content
Sidebar hover: 200ms enter delay, 500ms leave delay to prevent flickering
Auth: validate Descope token asynchronously, use localStorage only as display cache