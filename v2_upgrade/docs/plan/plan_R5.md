🛠️ The Implementation Plan: "Gen-AI Powered Vision Module"
Here is the exact step-by-step strategy for updating your OCR logic natively to incorporate both the new Sarvam Async Pipeline alongside your AWS Bedrock RAG routing logic.

1. The New Python Asynchronous Orchestrator (app.py)
We will rewrite api_ocr() into a local polling loop that gracefully manages Sarvam's new API signature while the frontend waits perfectly.

Step A (Creation): Submits your Base64 decoded img_bytes natively to POST /doc-digitization/job/v1/upload-files to initialize a processing unit and obtain an AWS S3 Presigned URL from Sarvam.
Step B (Upload): Python pushes the image bytes (requests.put) into that presigned URL securely.
Step C (Trigger): Python hits POST {job_id}/start to commence Sarvam's neural processing.
Step D (Polling Loop): Uses a while True: loop executing every 2 seconds hitting {job_id}/status. Once it returns "Completed", it fetches the parsed Markdown via /download-links and returns {"text": extractedmd} back to ocr.js.

2. Frontend Abstraction & Loading States (ocr.js)
Update UI Feedback: Because async document intelligence takes between 4-10 seconds, ocr.js currently flashes immediately. We must ensure the ocrProcessing display block ("Parsing text...") remains statically visible until data.text is physically resolved from the new Python loop pipeline.

3. Bedrock Knowledge Base Routing (Medicine Extraction)
The user dropped an image. It got parsed. What's next?

ocr.js natively captures the output text, bundles it, and dynamically issues a silent internal /api/search query strictly reading: "Extract all medicine/drug names from the following prescription text and return ONLY a JSON array."
Route Enforcement: In app.py, we will write a strict condition inside api_doc_analysis / /api/search that looks for this explicit "Extract JSON" system instruction.
Bedrock Handoff: Instead of trying to reason natively, we pipe this extraction query specifically into AWS Bedrock (Claude 3.5 Sonnet). Bedrock excels at rigid JSON architectures. It will parse the raw OCR string and output perfectly formatted JSON tuples: {"name": "Nimesulide", "dosage": "100mg"}.
ocr.js reads this JSON and ticks the interactive checkboxes on the UI.

4. Interactive Bedrock "Compliance Search" (The Handshake)
Once the checkboxes are generated in the scanner tab, the user clicks "Search Select Medicines".
This triggers performSearch('Search these: X, Y, Z') traversing directly into the global chat.
The global chat immediately hits search_tier2_aws(), referencing your PHARMAI_SYSTEM_PROMPT.
(Action Item): We will adjust the System Prompt instruction strictly dictating to Bedrock: "If given a list of medicines, perform a bulk regulatory lookup. List each medicine and definitively state if it is ALLOWED, RESTRICTED, or BANNED by CDSCO."
Next Steps for Implementation
To begin integrating this module rapidly so your OCR comes back online before your hackathon, I will create the tasks natively inside tasks.md and immediately execute the Python API refactor in app.py. Let me know if you approve this architectural workflow!