# PharmAI MVP — Feature Test Guide

> **Live URL**: https://medical.lehana.in/pharmai/
> **Version**: 3.0.0 | **Last Tested**: 2026-03-07
> **Purpose**: Manual testing checklist for video submission and pitch demo

---

## Quick Reference: What to Demo

| # | Feature | Sarvam AI? | AWS? | Status | Demo Priority |
|---|---------|:----------:|:----:|:------:|:-------------:|
| 1 | AI Drug Safety Search | ✅ sarvam-m | ✅ Bedrock KB | ✅ Working | 🔴 Must Show |
| 2 | Multi-Language Translation | ✅ Mayura v1 | — | ✅ Working | 🔴 Must Show |
| 3 | Voice Search (STT) | ✅ Saaras v3 | — | ✅ Working | 🔴 Must Show |
| 4 | Prescription OCR Scanner | ✅ Parse/Doc + sarvam-m | — | ✅ Working | 🔴 Must Show |
| 5 | Drug Interaction Checker | ✅ sarvam-m | ✅ Bedrock KB | ✅ Working | 🔴 Must Show |
| 6 | Context-Aware Spaces | ✅ sarvam-m (system prompt) | — | ✅ Working | 🟡 Show if time |
| 7 | Text-to-Speech (Read Aloud) | ✅ Bulbul v2 | — | ✅ Working | 🟡 Show if time |
| 8 | Knowledge Base Upload | — | ✅ Bedrock KB S3 | ⚠️ AWS Backend | 🟡 Show if time |
| 9 | Session History & Chat | — | — | ✅ Working | 🟢 Auto-shown |
| 10 | Chat Export (Copy/PDF/Share) | — | — | ✅ Working | 🟢 Auto-shown |
| 11 | Multi-Language UI Settings | — | — | ✅ Working | 🟢 Auto-shown |
| 12 | Auth (Descope Sign-In) | — | — | ✅ Working | 🟢 Auto-shown |

---

## Feature 1: AI Drug Safety Search (MUST DEMO)

**What it does**: 2-tier search system. Tier 1 queries AWS Bedrock Knowledge Base (CDSCO regulatory data). Tier 2 falls back to Sarvam AI (sarvam-m model) for general pharmaceutical analysis.

**Sarvam AI used**: `sarvam-m` LLM for intelligent drug safety analysis
**AWS used**: Bedrock Knowledge Base with CDSCO/FSSAI regulatory documents

### Test Steps

1. Open https://medical.lehana.in/pharmai/
2. Type in the search bar: **"Is Nimesulide banned in India?"**
3. Press Enter or click the send button

### Expected Result
- Typing indicator shows "Searching knowledge base..."
- Response appears with a `source` badge (either `KB` for Tier 1 or `Sarvam` for Tier 2)
- Answer confirms Nimesulide is **BANNED** by CDSCO
- Response includes detailed regulatory reasoning

### More Test Queries (try 2-3 for video)
| Query | Expected Answer |
|-------|----------------|
| `Is Nimesulide banned in India?` | ✅ **BANNED** — CDSCO ban due to liver toxicity |
| `Is Paracetamol safe during pregnancy?` | Generally safe with caution, consult doctor |
| `Common side effects of Metformin 500mg` | GI issues, nausea, diarrhea, lactic acidosis (rare) |
| `What is the CDSCO status of Ranitidine?` | Suspended/Recalled due to NDMA contamination |
| `Active ingredients in Crocin Advance` | Paracetamol 500mg + Caffeine 65mg |
| `Is Pioglitazone safe to use?` | Restricted — requires monitoring for bladder cancer risk |

### What to Highlight in Video
- "Two-tier search using AWS Bedrock Knowledge Base and Sarvam-M"
- "Real CDSCO regulatory data — not Wikipedia"
- "Context-aware follow-up questions" (ask a follow-up in the same session)

### Follow-Up Test (Context Awareness)
After the Nimesulide query, type: **"What are safer alternatives?"**
- The AI should remember the context and suggest alternatives to Nimesulide specifically

---

## Feature 2: Multi-Language Translation (MUST DEMO)

**What it does**: Translates any AI response into 10 Indian languages using Sarvam AI Mayura v1 translation model.

**Sarvam AI used**: `mayura:v1` translation model

### Test Steps

1. First, get an AI response (do a drug search)
2. Click **Settings** (⚙️ in sidebar footer) → select **Hindi** (or any Indian language)
3. Go back to the chat (close settings, click a session)
4. On any AI response, click the **Translate** button

### Expected Result
- Loading spinner on the Translate button
- A new system message: "🌐 Translated to Hindi"
- Translated text appears as a new assistant message
- Translation is grammatically correct in the target language

### Supported Languages
| Language | Code | Native Script |
|----------|------|---------------|
| English | en-IN | English |
| Hindi | hi-IN | हिन्दी |
| Bengali | bn-IN | বাংলা |
| Tamil | ta-IN | தமிழ் |
| Telugu | te-IN | తెలుగు |
| Marathi | mr-IN | मराठी |
| Gujarati | gu-IN | ગુજરાતી |
| Kannada | kn-IN | ಕನ್ನಡ |
| Malayalam | ml-IN | മലയാളം |
| Punjabi | pa-IN | ਪੰਜਾਬੀ |
| Odia | od-IN | ଓଡ଼ିଆ |

### What to Highlight in Video
- "11 Indian languages supported via Sarvam AI Mayura v1"
- "One-click translation of any response — accessible healthcare in every language"
- "India has 22 official languages. We support 11 for maximum accessibility"

---

## Feature 3: Voice Search — Speech-to-Text (MUST DEMO)

**What it does**: User speaks into the microphone in any supported Indian language. Audio is sent to Sarvam AI Saaras v3 (STT) for transcription, then auto-searches.

**Sarvam AI used**: `saaras:v3` speech-to-text model

### Test Steps

1. Click the **microphone button** (🎙️) next to the search bar
2. Allow microphone access if prompted
3. Speak clearly: **"Is Aspirin safe for children?"**
4. Click the mic button again to stop, OR wait 15 seconds (auto-stop)

### Expected Result
- Mic button turns **red** with pulse animation (recording state)
- Toast: "Listening... tap again to stop"
- After stopping: typing indicator "Transcribing..."
- Transcribed text appears in search bar
- Auto-search triggers if transcript is > 5 characters
- AI responds with drug safety information

### Tips for Demo
- Speak clearly in a quiet environment
- Try in English first, then switch language in Settings and speak Hindi
- The voice search works in ALL 11 supported languages

### What to Highlight in Video
- "Voice-first design — pharmacists and doctors can search hands-free"
- "Supports speaking in any of 11 Indian languages via Sarvam Saaras v3"
- "Auto-transcribes and instantly searches"

---

## Feature 4: Prescription OCR Scanner (MUST DEMO)

**What it does**: Upload a prescription image → Sarvam OCR extracts text → Sarvam-M LLM extracts medicine names, dosages, and frequencies → Interactive checklist to check safety of each medicine.

**Sarvam AI used**: `parse/document` OCR + `sarvam-m` LLM for medicine extraction

### Test Steps

1. Click **📷 Prescription Scanner** in the sidebar footer
2. Upload a prescription image (photo of a real prescription or a test image)
   - Drag-and-drop into the upload zone, OR
   - Click the upload zone to browse files, OR
   - Click "📱 Use Camera" on mobile
3. Wait for OCR processing

### Expected Result
- Image preview displayed
- Loading: "Scanning prescription..."
- Raw extracted text shown under "📄 Extracted Text"
- Loading: "Extracting medicines..."
- Medicine checklist appears: **💊 Extracted Medicines (N)**
- Each medicine shows: ☑️ Name | Dosage | Frequency | 🔍 button
- Action buttons: "🔍 Search Selected" | "Select All" | "Deselect All"

### Test Scenarios
| Action | Expected |
|--------|----------|
| Click 🔍 on individual medicine | Searches that specific drug for safety info |
| Select multiple → "Search Selected" | Batch drug interaction + safety analysis |
| "Search This Text" button on raw OCR | Sends full prescription text for analysis |

### What to Highlight in Video
- "Upload any prescription — AI reads it and identifies every medicine"
- "One-click safety check for all medicines on a prescription"
- "Pharmacist's digital assistant — catches dangerous drugs instantly"

### If You Don't Have a Prescription Image
Create a test image with text like:
```
Dr. Smith Medical Clinic
Rx:
1. Tab Paracetamol 500mg - 1 BD x 5 days
2. Tab Azithromycin 250mg - 1 OD x 3 days
3. Syp Ambroxol 30mg/5ml - 10ml TDS x 5 days
```

---

## Feature 5: Drug Interaction Checker (MUST DEMO)

**What it does**: Enter two drug names → AI analyzes potential interactions with severity, mechanism, clinical significance, and safer alternatives.

**Sarvam AI used**: `sarvam-m` LLM for interaction analysis
**AWS used**: Bedrock KB for CDSCO-sourced interaction data

### Test Steps

1. Click **💊 Drug Interactions** in the sidebar footer
2. Enter **Medicine A**: `Warfarin`
3. Enter **Medicine B**: `Aspirin`
4. Click **🔬 Check Interaction**

### Expected Result
- Switches to chat view with the interaction query
- AI responds with:
  - **Severity**: Major/Moderate/Minor
  - **Mechanism** of interaction
  - **Clinical significance**
  - **Management** recommendations
  - **Alternatives** if needed

### More Test Pairs
| Medicine A | Medicine B | Expected Severity |
|-----------|-----------|------------------|
| Warfarin | Aspirin | **Major** — increased bleeding risk |
| Metformin | Alcohol | **Moderate** — lactic acidosis risk |
| Lisinopril | Potassium | **Moderate** — hyperkalemia risk |
| Ciprofloxacin | Theophylline | **Major** — theophylline toxicity |
| Amoxicillin | Paracetamol | **None/Minor** — generally safe |

### What to Highlight in Video
- "Drug-drug interaction check powered by AI — critical for poly-pharmacy patients"
- "India has a massive generic drug market — interaction checking is essential"
- "Severity assessment + mechanism + clinical significance + alternatives"

---

## Feature 6: Context-Aware Spaces (SHOW IF TIME)

**What it does**: Perplexity-style "Spaces" that modify AI behavior based on who's asking — Doctor, Pharmacist, Patient, or Researcher. Each space has a system instruction that changes the tone and depth of responses.

### Test Steps

1. Click the space selector dropdown (shows "🔍 General" by default)
2. Switch to **🩺 Doctor** space
3. Search: **"Interaction between Warfarin and Amiodarone"**
4. Switch to **👤 Patient** space
5. Search the same query again
6. Compare the two responses

### Expected Difference
| Space | Response Style |
|-------|---------------|
| 🩺 Doctor | Medical terminology, clinical data, drug mechanisms, evidence-based |
| 💊 Pharmacist | Dispensing guidelines, Schedule H/X classifications, storage conditions |
| 👤 Patient | Simple language, practical advice, "when to see a doctor" |
| 🔬 Researcher | Pharmacokinetics/dynamics, clinical trial data, molecular details |

### What to Highlight in Video
- "Same question, different persona — AI adapts its response"
- "Pharmacists get technical dosing info; patients get plain language"
- "Custom spaces: create your own with specific system instructions"

---

## Feature 7: Text-to-Speech — Read Aloud (SHOW IF TIME)

**What it does**: Reads any AI response aloud using Sarvam AI Bulbul v2 TTS with `anushka` voice.

**Sarvam AI used**: `bulbul:v2` text-to-speech model, `anushka` speaker

### Test Steps

1. Get an AI response from any search
2. Click the **Read** button (🔊) on the response

### Expected Result
- Button shows playing state (animated pulse)
- Audio playback starts within 2-3 seconds
- Clear, natural-sounding female Indian voice
- Works in all 11 supported languages

### Status: ✅ Working
- Fixed 2026-03-07: Updated speaker from deprecated `meera` to `anushka`, model `bulbul:v2`
- Audio generation confirmed (base64 audio returned, ~100KB per response)

---

## Feature 8: Knowledge Base Upload (SHOW IF TIME)

**What it does**: Upload pharmaceutical PDFs → AWS Bedrock KB indexes them → AI includes them in search results via RAG (Retrieval-Augmented Generation).

**AWS used**: S3 + Bedrock Knowledge Base

### Test Steps

1. Click **📚 Knowledge Base** in sidebar footer
2. Upload a PDF (pharmaceutical document, drug monograph, etc.)
3. Wait for upload confirmation
4. Search for content that's in the uploaded PDF

### Current Status: ⚠️ AWS Backend Dependency
- Requires AWS RAG backend running on the EC2 instance
- Document list may return 503 if backend is down
- **For video**: Show the upload UI, explain the RAG architecture

---

## Feature 9: Session History & Chat (AUTO-SHOWN)

**What it does**: All conversations are saved as sessions with full history. Sessions persist across page reloads (localStorage). Follow-up questions maintain context.

### Test Steps (happens automatically)

1. Do a search → Session auto-created in sidebar
2. Ask a follow-up → Context maintained
3. Create a **+ New Chat** → Fresh session
4. Click an old session in sidebar → Full history restored
5. Delete a session → Swipe or right-click

### What to Highlight
- "Full conversation history — just like ChatGPT"
- "Context-aware follow-ups across the same session"
- "Up to 50 sessions stored locally"

---

## Feature 10: Chat Export — Copy / PDF / Share (AUTO-SHOWN)

**What it does**: Export chat conversations as clipboard text, PDF report, or shareable link.

### Test Steps

1. Have an active chat with messages
2. Click **Settings** (⚙️) in sidebar
3. Under "Export", click:
   - **📋 Copy Chat** → Copies formatted conversation to clipboard
   - **📄 Export PDF** → Generates and downloads a professional PDF report
   - **🔗 Share** → Copy shareable link (if supported)

### What to Highlight
- "Professional PDF reports for pharmacists and hospitals"
- "One-click copy for medical records"

---

## Feature 11: Multi-Language UI Settings (AUTO-SHOWN)

**What it does**: Language selection that affects STT, TTS, and Translation targets. 11 Indian languages.

### Test Steps

1. Click **⚙️ Settings** in sidebar footer
2. See the language grid with 11 languages
3. Select **Hindi** (or any language)
4. Language is now active for Voice Search, TTS, and Translation

---

## Feature 12: Descope Authentication (AUTO-SHOWN)

**What it does**: Sign-up/Sign-in with Descope SSO. Shows user avatar and name in top bar when logged in.

### Test Steps

1. Click **Login / Sign Up** in top bar
2. Auth modal appears with Descope widget
3. Sign in with email/password or social login
4. After login: avatar + name shown in top bar, logout button visible

---

## Recommended Demo Flow (3-5 min video)

### Sequence for Maximum Impact

```
1. [0:00] Open PharmAI → Show the landing page
   → Point out: template cards, features grid, professional UI

2. [0:30] Search: "Is Nimesulide banned in India?"
   → AI response with BANNED status, CDSCO info
   → Highlight: "Real regulatory data, not Wikipedia"

3. [1:00] Follow-up: "What are safer alternatives?"
   → Context-aware response → "Remembers what we were discussing"

4. [1:30] Switch to Hindi → Translate the response
   → Show translated text in Hindi
   → "11 Indian languages, powered by Sarvam AI Mayura"
   → Click Read Aloud on translated response
   → "Natural-sounding TTS in Indian languages — Sarvam Bulbul"

5. [2:00] Voice Search: Speak "Is Aspirin safe for children?"
   → Mic records → Transcription → Auto-search
   → "Voice-first design in any Indian language — Sarvam Saaras v3"

6. [2:30] Drug Interaction: Warfarin + Aspirin
   → Major interaction detected → Alternatives suggested
   → "Critical for poly-pharmacy — catches dangerous combinations"

7. [3:00] Prescription Scanner: Upload prescription image
   → OCR extracts text → Medicines identified → Safety checklist
   → "Upload any prescription, AI reads it, checks every medicine"

8. [3:30] Switch Spaces: Doctor vs Patient
   → Same query, different depth → "Contextual AI responses"

9. [4:00] Export PDF → Professional report downloaded
   → "Ready for hospital records and pharmacist documentation"

10. [4:30] Wrap-up: Highlight tech stack
    → "Sarvam AI (STT, TTS, Translation, LLM, OCR) + AWS Bedrock KB + CDSCO data"
    → "Making pharmaceutical safety accessible in every Indian language"
```

---

## Known Issues & Workarounds

| Issue | Status | Workaround for Demo |
|-------|--------|---------------------|
| ~~TTS returns "No audio generated"~~ | ✅ Fixed | Updated speaker to `anushka` + model `bulbul:v2` — TTS now works |
| Document list returns 503 | ⚠️ AWS backend may be down | Show upload UI, explain RAG architecture |
| Tier 1 (KB) may fall back to Tier 2 (Sarvam) | Normal behavior | Both tiers work — Sarvam provides great responses |
| First search may be slow (~3-5s) | Cold start | Do a warm-up search before recording video |

---

## Tech Stack Summary (for Pitch)

```
Frontend:  Vanilla HTML/CSS/JS SPA
Backend:   Flask (Python) → Proxy to Sarvam AI & AWS
AI/ML:     Sarvam AI (STT, TTS, Translation, OCR, LLM)
           AWS Bedrock Knowledge Base (CDSCO regulatory data)
Auth:      Descope SSO
Hosting:   Docker on Lehana.in (Traefik reverse proxy)
Data:      CDSCO banned drugs database (50,000+ entries)
Languages: 11 Indian languages
```
