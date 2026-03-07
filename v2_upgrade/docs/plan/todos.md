# Phase R2 Todos

- [x] Task 1: Remove Drug Interaction Feature Entirely (Deleted js/interaction.js, script tag and html struct in index.html, endpoint from app.py, array entry and init func from app.js)
  - Delete `js/interaction.js`.
  - Remove `<script src="js/interaction.js">` tag in `index.html`.
  - Remove `#toolPanel-interaction` div in `index.html`.
  - Remove `#toolInteraction` button in sidebar from `index.html`.
  - Remove `api_interaction()` endpoint in `app.py`.
  - Remove "interaction-check" from health features list in `app.py`.
  - Remove "Drug Interaction" template in `app.js` (`TEMPLATE_QUERIES`).
  - Remove `toolInteraction` logic in `app.js` (`setupSidebarToolButtons()` and `showToolPanel()`).
  - Replace the removed template card with "Check Side Effects" or "Compare Medicines" in `app.js`.

- [x] Task 2: Fix All Upload Zones (Click-to-Upload) (Added onclicks to zones, event.stopPropagation to hidden inputs, and CORS proper handling to app.py upload files endpoint)
  - OCR Upload Zone:
    - Add `onclick="document.getElementById('ocrFileInput').click()"` and `style="cursor: pointer"` to `#ocrDropZone` in `index.html`.
    - Change text in `#ocrDropZone` to "Click to upload or drop a prescription image".
    - In `ocr.js` `initOcr()`, add click listener on `#ocrDropZone` that triggers `#ocrFileInput.click()` and stop propagation on the `<input>`.
  - KB Upload Zone:
    - Move `#docUploadInput` outside `#docDropZone` in `index.html` (or remove `onclick` attribute and add click listener with stopping propagation in JS).
    - Change text in `#docDropZone` to "Click to upload PDF documents".
  - Backend CORS Fix:
    - Add `OPTIONS` method to `api_upload_files()` in `app.py`.
    - Add `_cors_preflight()` handler logic for `OPTIONS`.
    - Change any standard `jsonify()` statements in `api_upload_files()` to `_cors_json()`.

- [x] Task 3: Fix Logout Button Not Clickable & Auto-login (Added setTimeout async check for Descope token + z-index/position+global click listener to logout btn)
  - In `auth.js`, add direct `document.addEventListener('click')` backup listener for `#logoutBtn`.
  - Ensure `.logout-btn` has `position: relative; z-index: 1000; pointer-events: auto;` in `layout.css`.
  - Update `DescopeAuth.init()` in `auth.js` to validate the Descope session token asynchronously if `localStorage` has the user, and clear it / log out if validation fails, rather than completely bypassing check.

- [x] Task 4: Fill Landing Page Whitespace with Engaging Features (Updated max-widths in layout.css and components.css, and injected Quick Tools, Trending Searches, How It Works into index.html)
  - Increase `.landing-hero` `max-width` to `900px` and `.template-grid` `max-width` to `850px` in `layout.css`.
  - Change `.template-grid` to `grid-template-columns: repeat(auto-fill, minmax(180px, 1fr))`.
  - Add inside `.landing-view` on `index.html`:
    - "How It Works" horizontal cards spanning full width.
    - "Quick Tools" horizontal row bridging tool panels.
    - "Featured Searches" / Trending pills.

- [x] Task 5: Fix Delete Operations (Fixed documentId parameter sync in app.py/documents.js and implemented fetch-and-delete fallback iteration loop for Delete All)
  - In `documents.js` `deleteDocument()`, change `document_id:` to `documentId:` in the JSON payload sent to backend.
  - Implement/Fix "Delete all documents" endpoint in backend/frontend. E.g., handling iteration deletion if `api_delete_all_documents` is not on AWS RAG backend.

- [x] Task 6: Sidebar UX Improvements (Added mouseenter/mouseleave delays, wired backdrop click, forced closeSidebar on tool panel click)
  - In `sidebar.js`, add `mouseenter` event to hamburger/sidebar area to trigger `openSidebar()` with 200ms delay.
  - Add `mouseleave` to sidebar to close after 500ms delay (cancelled on re-enter).
  - Ensure backdrop click-to-close works on desktop as well (update `layout.css` to show backdrop).
  - Modify `app.js` `setupSidebarToolButtons()` to call `closeSidebar()` when clicking a tool button, even on desktop.
