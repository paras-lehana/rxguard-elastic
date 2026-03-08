The "Empty KB" Rejection (Bedrock Native Behavior)

Why it happens: The phrase "Sorry, I am unable to assist you with this request." is the hardcoded default response of the AWS Bedrock Knowledge Base (RetrieveAndGenerate API) when it fails to find any matching chunks in its vector database. Because your KB is empty, it always fails the retrieval step and refuses to answer, rather than using its underlying Claude model to just answer the question generally.
The Fix: We need to intercept this specific rejection string in app.py. When AWS Bedrock gives up because of an empty KB, we must instantly route the query to a "Tier 3" fallback (either Sarvam's standard LLM or a direct non-RAG Bedrock prompt) so the system remains resilient and answers base medical queries gracefully.
The Base64 "Gibberish" Pollution

Why it happens: Sarvam's new document digitization explicitly injects cropped images directly into the Markdown text as raw base64 data URIs (e.g., ![Image](data:image/jpeg;base64,/9j/4AAQ...)). This results in thousands of characters of gibberish.
The Impact: When you hit "Search This Text", this massive base64 block blows past token limits and breaks the JSON extraction prompt completely, resulting in "No medicines detected."
The Fix: We must run a Python Regex (re.sub) right at the end of the _sarvam_async_ocr loop to cleanly scrub all ![Image](data:image...) artifacts out of the text before it ever reaches the user or the extraction AI.
Background Async OCR (UX)

Why it blocks: Currently, ocr.js overrides the DOM container and expects the user to sit there.
The Fix: We will switch this to a true background promise. You click "Scan", we show a transient "toast" notification ("Scanning in background..."). You can freely navigate to the chat or interact checker. 15 seconds later, a success toast pops up: "Scan complete! View medicines", which you can click to jump straight back to the populated checklist.
📋 Detailed Execution Plan: Phase R6 (Resilience update)
Step 1: Clean the Sarvam Markdown (Fix 2)

Edit app.py _sarvam_async_ocr()
Add Regex to strip data URIs from the returned Markdown string.
Outcome: Clean text with just the layout and text (no images), ensuring JSON extraction works perfectly every time.
Step 2: Intelligent Empty-KB Fallback (Fix 3)

Edit app.py search_tier2_aws()
Add a detection condition: if "Sorry, I am unable to assist" in answer:
Implement a direct fallback function (e.g., search_tier3_llm()) that hits an LLM (Bedrock non-RAG or Sarvam-m) configured with the PHARMAI_SYSTEM_PROMPT to answer general drug queries without relying on uploaded documents.
Outcome: Fail-safe chat. If you ask about Nimesulide and there are no PDFs, the AI still acts as your pharma assistant.
Step 3: Non-Blocking Background Scanner UX (Fix 1)

Edit ocr.js processOcrImage()
Convert the localized UI spinner into a global toast("document processing...", "info").
Remove any locking UI overlays so the user can navigate the app.
Provide a callback that triggers toast("Scan successful! Click here.", "success") that binds an onclick event to return them to the OCR tab.


As per the planner the tasks can be 

---

## Phase 16: Phase R6 - Resilience, Safety, and Async UX
> _Implement safeguards against base64 bloating, Handle AWS empty KB blocks natively, and improve Scanner UI UX._

- [ ] 55. Implement Sarvam Base64 Stripper
  - [ ] 55.1 Identify Markdown string received from Sarvam in `_sarvam_async_ocr`
  - [ ] 55.2 Apply Python `re.sub` regex isolating and cleanly slicing `![Image](data:image/jpeg;base64, ...)` bloat to prevent token limit crashes

- [ ] 56. Build AWS Empty KB Fallback Protocol
  - [ ] 56.1 Identify exactly where "Sorry, I am unable to assist you with this request." rejection is caught in `search_tier2_aws`
  - [ ] 56.2 Introduce `search_tier3_llm()` or standard fallback path to route queries straight to Claude/Bedrock generative models un-grounded, using `PHARMAI_SYSTEM_PROMPT`
  - [ ] 56.3 Return gracefully so users searching for valid medicines still receive full medical interaction checks independent of DB state

- [ ] 57. Upgrade Scanner UX to Non-Blocking Status
  - [ ] 57.1 Deprecate physical "Lock overlay" / full div spinner in `js/ocr.js` `processOcrImage`
  - [ ] 57.2 Launch asynchronous global native `toast('Scanning document in background...', 'info')` popup instead
  - [ ] 57.3 Return users to a free-roaming UI allowing usage of chat modules while standard python logic executes `time.sleep` polling
  - [ ] 57.4 Execute a final visual `toast('Scan Complete! View medicines')` trigger capable of recalling the user context immediately