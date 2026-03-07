## Plan: UX Redesign, AWS Bedrock Migration & Session Privacy

Going forward, every planning phase will be saved as a dedicated file in [v2_upgrade/docs/plan/](v2_upgrade/docs/plan/). This comprehensive plan resolves the 11 feature gaps identified, enforces user-level data isolation, transitions AI reasoning payloads to AWS Bedrock, introduces Jan Aushadhi generic alternatives, and streamlines the cluttered frontend.

**Steps**
1. **Log Plan**: Create a new file [v2_upgrade/docs/plan/plan_20260307_ux_aws_migration.md](v2_upgrade/docs/plan/plan_20260307_ux_aws_migration.md) containing these exact agreed-upon specifications for tracking.
2. **Landing Page & UI Polish**: Edit [frontend/index.html](frontend/index.html) to delete the 12 boxes, replacing them with a concise Hero and 4 simple action cards (Search, OCR, Interaction, Jan Aushadhi). Adjust [frontend/css/layout.css](frontend/css/layout.css) to stop the sidebar from auto-opening on load (which fixes the blurred screen) and condense the `.chat-container` whitespace.
3. **Session Privacy**: Modify `loadSessions` and `saveSessions` in [frontend/js/chat.js](frontend/js/chat.js) to append the Descope user ID (e.g., `pharmai_sessions_{userId}`). Update `onLogout` in [frontend/js/auth.js](frontend/js/auth.js) to instantly clear the UI state and hide data from the next user.
4. **AWS Bedrock Migration**: In [frontend/app.py](frontend/app.py), completely strip the Sarvam `sarvam-m` model from text reasoning endpoints (`/api/interaction`, `/api/doc-analysis`, and `search_tier2`). Replace them with a `boto3` integration connecting to AWS Bedrock. (Sarvam will be retained exclusively for STT, TTS, and OCR APIs). You have to use the /api/search that is already provided inthe backend api hosted in the folder /home/ubuntu/AWS_RAG_CURD. No other api should ideally be required for searching anything in our protal, indexing documents into the KB and listing documents from KB.
5. **Unified Upload System**: Update [frontend/index.html](frontend/index.html) and [frontend/css/components.css](frontend/css/components.css) to merge the mismatched KB drop zones and buttons into one functional drag-and-drop area with the HTML `multiple` attribute. Patch the upload handling in [frontend/app.py](frontend/app.py) to reliably route multiple files to AWS.
6. **Jan Aushadhi Feature**: Append instructions to the Python system prompts in [frontend/app.py](frontend/app.py) to forcefully request Pradhan Mantri Bhartiya Janaushadhi equivalents and cost-savings for all branded medicines. Add a UI parser in [frontend/js/utils.js](frontend/js/utils.js) to visually highlight these savings.
7. **Custom System Prompts**: Inject a text-area next to the spaces selector in [frontend/index.html](frontend/index.html) and bind it in [frontend/js/spaces.js](frontend/js/spaces.js) so users can define their own prompt instructions per chat.

**Verification**
- Load the portal while logged out: confirm the screen is unblurred, the 12 boxes are gone, and no prior chat sessions load.
- Log in and launch an interaction check: verify via logs that the AWS Bedrock client processes the request, bypassing the failing Sarvam APIs.
- Upload 2+ PDFs to the newly unified drop zone simultaneously and confirm success toasts.
- Query "Augmentin 625": ensure the result explicitly details Jan Aushadhi generic Amoxicillin savings.

**Decisions**
- **Plan Logging**: Adopted as standard protocol; execution agents will initiate tasks by dumping the approved plan into the docs directory first.
- **Privacy Mechanism**: Used user-keyed `localStorage` via Descope ID instead of configuring an entirely new database table for sessions, preserving the lean frontend architecture for MVP velocity.
