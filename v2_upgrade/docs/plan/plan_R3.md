1. Prescription Scanner (OCR) Bug

Root Cause: In frontend/js/ocr.js, images are converted to Base64 using readAsDataURL(), which leaves a long prefix header on the string (e.g., data:image/jpeg;base64,...). In frontend/app.py, the backend applies a raw base64.b64decode() on this entire string. This blindly encodes the header as bytes, corrupting the image file fully. Sarvam API parses the corrupted file, fails silently to find text, and returns "No text detected."

Action: In frontend/app.py, update api_ocr() with a split routine (image_b64.split(',', 1)[1]) to strip the header before passing to Sarvam.

2. Knowledge Base (KB) Glitches

2.1 Individual Delete: documents.js relies on doc.id, but the AWS Backend returns the ID natively under the key name (e.g., "name": "U8LJNJ0FQN/documents/cdsco..."). Because doc.id is undefined, the delete API is passed a blank payload.

Action: Update app.py api_list_documents() to remap d['id'] = d.get('name') so the frontend actually gets the correct ID UUID.

2.2 Delete All Click Box: CSS layout text-wrapping forces the .doc-header metadata text (span.doc-count) to stretch invisibly over the middle and right side of your HTML button, making it an unclickable dead zone.

Action: Add position: relative; z-index: 10; directly to the Delete button styling in documents.js.

2.3 Post-Delete Ghost Search: While deletion triggers to AWS Kendra successfully, Kendra sometimes holds vector indexes for a few minutes OR the local JS session caches the context.

Action: We will auto-flush the frontend session array after deleteAllDocuments() happens.

2.4 0 KB Document Size: The AWS RAG list_documents API simply doesn't return file sizes (only filenames and metadata states). The JS handles this missing property with a fallback doc.size || 0 KB.

Action: Remove the 0 KB label loop from documents.js renderDocumentList() entirely, replacing it simply with Uploaded PDF.

2.5 Upload Failures: Your app.py has app.config['UPLOAD_FOLDER'] = '../data'. Because your Docker instance's frontend mount is strictly structured ("Mode": "ro" read-only), f.save() physically lacks permission to write to this parent folder and crashes the ingestion.

Action: Refactor /api/upload-files in app.py to use Python's built-in tempfile.NamedTemporaryFile module which utilizes internal RAM/tmp allocation, guaranteeing a successful relay payload to AWS.

3. Unwanted Sarvam AI Search Mentions & Output Formatting

3.1 & 3.2 Sarvam Rendering: In frontend/js/chat.js (line 212), there is a hardcoded ternary condition written: msg.source === 'kb' ? '📚 AWS KB' : '🤖 Sarvam AI'. 
Because app.py changed the tier signature from 'kb' back to 'aws-bedrock', the JS defaults everything to rendering the '🤖 Sarvam AI' badge.

3.3 Elimination:

Action: I will rewrite the ternary in chat.js to unconditionally drop Sarvam badges from text search: msg.source === 'aws-bedrock' ? '🔬 AWS Bedrock KB' : '🔬 AI Analysis'. Sarvam will be explicitly restricted to OCR/STT/TTS API endpoints only.

3.4 Friendly Formatting: The horrible triple BANNED text happens because:
Your exact Bedrock RAG system prompt instructs "format Status:"
Python's app.py natively injects the word "🚫 BANNED" based on regex dictionary mapping.
app.py forcibly concatenates f"\n🔬 **AI Analysis (AWS Bedrock KB)**\n\n" in the actual text response payload.

Action: I will strip these hardcoded Python string injections in target_tier2_aws() and rewrite PHARMAI_SYSTEM_PROMPT to enforce the Bedrock LLM to provide a highly conversational, fluid, and non-repetitive response.

4. Jan Aushadhi Realities
4.1 & 4.2 Where is it?: Currently, there is zero implementation of a Jan Aushadhi database, API, or JSON mapping in the backend.

4.3 What we need to do: The "savings" and "Jan Aushadhi alternatives" you’ve seen the AI spit out were exactly that: 100% LLM prompt engineering hallucinations. Because the app.py prompt aggressively demands Bedrock strictly output "percentage cost savings compared to branded prices," the LLM invents fake numbers based on its general context model to appease the prompt.

Action for Hackathon: Rather than using LLM for these, i have pdf and i would prefer we upload that in the KB too and you use it as it is from there. I want you to create me a separate panel just like medicine prescription for jan aushadi and add these saving and jan aushadhi alternative part into that but also keep a good UI for locating near by jan aushadhi and getting the full list of medicines.

These will be running from KB only and I shall be uploading PDFs there. Make sure UI and UX that you create are professional only and well drafted.