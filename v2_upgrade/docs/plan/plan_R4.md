Detailed Implementation Plan: Phase R4 (Advanced Search & KB Viewing)
1. Spaces & Persona Management (Perplexity-style)
Objective: Enable customized AI behavior isolated by spaces (e.g., "Doctor Mode", "Patient Mode"). All threads within a space will inherit its custom system instruction.

Frontend UI (index.html & spaces.css):
Enhance the "Create Space" modal to feature a prominent textarea: Persona / System Instructions (Optional).

Frontend Logic (spaces.js & chat.js):
Currently, the application supports spaces locally, but doesn't strictly enforce personas in the API payload.

Update chat.js so that when a session is active, it continually references activeSpaceId and attaches space.systemInstruction properly injected into the request body.

Backend Logic (app.py):
Modify endpoints serving searches (primarily api_chat, api_doc_analysis, and search_tier2_aws).

Accept a dynamic persona_instruction parameter from the JSON body.
If provided, prepend or creatively append this persona_instruction to the overarching baseline PHARMAI_SYSTEM_PROMPT to enforce the user's custom instructions over the Bedrock LLM generation.

2. Pinned Searches & Bookmarks
Objective: Allow users to pin entire threads permanently to the top of the sidebar, and bookmark individual answer snippets for quick retrieval.

Thread Pinning:
Data Model: Add pinned: boolean to the Session schema in localStorage.

UI (sidebar): Update renderSessionList() to visually separate or sort pinned threads at the top (with a 📌 icon).

Interaction (chat.js): Add a <button id="pinThreadBtn"> to the top-right chat header. When clicked, toggle the pinned property and re-render the sidebar.

Message Bookmarking:
Data Model: Introduce a new STORAGE_KEY_BOOKMARKS = 'pharmai_bookmarks' array holding cloned message JSON blocks.

UI (chat blocks): Append a 🔖 Bookmark hover-action beneath individual AI responses in createMessageElement().

Display (index.html / UI panel): Create a dedicated "Bookmarks" tool panel (similar to Jan Aushadhi/OCR) to browse through saved snippets directly.

3. Sharing Spaces and Threads
Objective: Generate stable, shareable links (?share_id=xyz) allowing external individuals to access a read-only state of a user's threads or spaces.

Database Integration (app.py):
We will initialize a lightweight SQLite database locally utilizing the existing read-write volume: /data/pharmai.db.

Create a schema table: shared_threads (id TEXT PRIMARY KEY, type TEXT, payload JSON, created_at TIMESTAMP).

Backend API:

POST /api/share: Reads active chat thread JSON from the frontend, generates a short string ID (e.g., via uuid or nanoid), saves to SQLite, and returns the ID.
GET /api/share/<id>: Returns the stored JSON configuration to anonymous clients.

Frontend Architecture (app.js / chat.js):
Sender: Add a "Share 🔗" button that issues the POST request and displays an alert popup: URL Copied: https://medical.lehana.in...?share_id=abc.

Receiver: Inside app.js init(), parse window.location.search. If ?share_id= exists, lock the UI (disable text inputs), fetch the JSON via GET /api/share, and render the thread cleanly as a public read-only view.

4. Native KB PDF Viewer (Read View)
Objective: Allow users to click their Knowledge Base documents and visually read the original parsed PDF inside a browser tab or modal natively.

The Problem Mechanism: Currently, api_upload_files() streams file bytes directly directly to the AWS endpoint natively bypassing Docker limits, meaning the PDF vanishes from the internal server environment instantly.

Storage Modification (app.py):
Update api_upload_files(): Simultaneously save a physical copy using a fixed buffer path mapping into the R/W volume os.path.join('/data/pdfs/', secure_filename).
(Note: The volume mapping /root/repo/pharmai_portal/data:/data guarantees persistence across container reloads).

Backend Serving Endpoint (app.py):

Inject a new route natively passing binary chunks securely: GET /api/documents/view/<filename> acting as send_from_directory('/data/pdfs', filename).
Frontend UI Integration (documents.js):

Modify renderDocumentList() to wrap the .doc-name text in an <a href="/api/documents/view/${doc.name}" target="_blank"> tag, transforming it into a clickable active link.

Optionally add an "👁️ View" visual icon alongside the preexisting "🗑️ Delete" bin acting as a direct router.


Proceeding Instructions
Since you requested a detailed plan, this acts as your blueprint.
When you are ready, simply say "Implement Phase R4 into tasks" and I will construct the sub-elements within tasks.md and start methodically programming the features directly into your codebase just like the prior phases.