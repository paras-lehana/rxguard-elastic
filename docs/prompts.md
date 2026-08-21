# Prompt Log — PharmAI / RxGuard Portal

> **Purpose**: Indexed record of all prompts, decisions, and outcomes for this project.
> **Last updated**: 2026-08-21 (second pass)

| # | Date | Time | Topic | Type | Status | Link |
|---|------|------|-------|------|--------|------|
| 1 | 2026-08-21 | 12:35 | Locate the banned pharma project | Research | 📋 Logged Only | [→](#2026-08-21-1235---locate-the-banned-pharma-project) |
| 2 | 2026-08-21 | 12:45 | Recast onto Elastic + AWS for hackathon | Feature | ⚠️ Partial | [→](#2026-08-21-1245---recast-onto-elastic--aws-for-hackathon) |
| 3 | 2026-08-21 | 14:05 | Close out deferred items | Refactor | ✅ Done | [→](#2026-08-21-1405---close-out-deferred-items) |

---

## [2026-08-21 12:35] - Locate the banned pharma project

**Metadata**:
- **Type**: Research
- **Files Changed**: 0
- **Project**: pharmai_portal

### Original Prompt
> listen do one thing, first find the banned pharma project on our server and just get all the details if it's running and where it is and all / and we will do the changes afterwards / for now you just need to get the details, don't modify anything

### Response Summary
Found five pharma codebases and three deployment configs, none publicly reachable.
`repo/pharmai_portal` is the flagship (route `medical.lehana.in/pharmai`, container
`pharma-frontend` not running); `ideas/pharmai` had 3 containers up but a broken
portal and a dashboard repurposed for an NCERT education hackathon;
`ideas/pharmai-scrapper` down; `ideas/AI-For-Bharat-Round-1` and
`saved/research/offline-banned-pharma` are docs only. Only `gemini-files.lehana.in`
answered. Nothing was modified.

<br/>

---

## [2026-08-21 12:45] - Recast onto Elastic + AWS for hackathon

**Metadata**:
- **Type**: Feature
- **Files Changed**: 16 (7 new service modules, 2 scripts, app.py, 3 JS files, index.html, README, AGENTS.md, HACKATHON_SUBMISSION.md)
- **Project**: pharmai_portal
- **Branch**: `elastic-hackathon`
- **Commits**: `0f04128`, `44d0063`

### Original Prompt
> look at the current requriements of the hackathon what it wants so we need to provide them which will be using it's tech which is elastic search and aws i think or we need to atleast mention in the pitch whatever we gonna give them / but first read the submission and projects requirements, the third point is for you to cast this project into that drug detection thing / so you need to work smartly with minimal changes and beat the hackathon at best / because we already have working prototype and it's working smooth as far as i remember we just need to mould it into the hackathon requirements and we will give the same demo link / and one more thing here you can suggest me if i need to give you the github new link or should we use the old github because i doubt if we give github old link then judegs might check the dates etc / so first understand this and do the changes and keep the backup of the current project so that if we need to get it revresed we will easily do it
>
> (followed by the three requirement blocks: Idea Submission, Project Requirements — Elasticsearch + AWS LLM core, and Healthcare & Insurance Intelligence — drug interaction detection, FHIR, immutable audit trail, explainable insights)

### Pre-Flight Context
> - Read-only phase first, then backup before any edit (user asked for a reversible backup)
> - Hard constraint: Elasticsearch + AWS LLM as core; external tools must not replace them
> - Challenge topic: drug interaction detection + FHIR + immutable audit trail + explainable
> - Same demo link must keep working → route stays `medical.lehana.in/pharmai`
> - Check for existing ES cluster and AWS creds before proposing anything

### Post-Execution Summaries

#### A. Business Summary

**DONE**

- **Backup taken first.** 14MB archive plus a git tag, so the pre-hackathon state can be restored with one command.
- **The product now answers a question no competitor can.** Every drug pair is checked two ways at once: does it interact medically, and is the combination *illegal to sell in India*. Nimesulide + Paracetamol is the proof case — both legal alone, the combination banned since 2016, and no international database flags it. A tester types two brand names and gets a 🚫 BANNED verdict quoting the real government notification number.
- **It works from brand names, not just chemical names.** "Nimulid 100mg" and "Crocin 650" resolve correctly — the way a real patient or pharmacist types.
- **A full prescription can be screened at once**, including reading the medication list straight out of a clinical record (FHIR), rather than checking pairs one at a time.
- **Every verdict is permanently recorded in a tamper-evident log.** We proved it by deliberately altering a record; the system named the exact entry that had been changed. This matters for insurance claim disputes.
- **The demo link is unchanged** — `medical.lehana.in/pharmai` works on mobile.

**PARTIALLY DONE**

- **The AWS half is built but not switched on.** We have no valid AWS account credentials, so the AI reasoning currently runs on our own service. The AWS integration is finished and turns on by pasting in a key — no further development. The submission states this plainly rather than claiming otherwise, because a reviewer could disprove a false claim in one click.

**Extra business-relevant findings**

- **The website was completely broken and nobody knew.** Every stylesheet and script was failing to load, so the page had no design and no working buttons. Health checks were passing the whole time. Fixed — the page now loads clean.
- **A status label was contradicting itself**, showing "🚫 BANNED" above text saying no ban information was found. On a medicine-safety tool that is dangerous. Fixed.
- **The Knowledge Base tab was calling a shut-down service from an unrelated school-education project.** It now shows the real indexed government corpus.
- **The login popup appears immediately on opening the site** and blocks the page. Judges hitting a login wall first is a scoring risk — worth changing before submission.

#### B. Technical Summary

**DONE**

- **Backup** — `/root/backups/pharmai/` (14M tarball incl. `.git` and uncommitted work), git tag `pre-elastic-hackathon-2026-08-21` at `ae272dd`, docker configs and `traefik_dynamic.yml` snapshot.
- **Elasticsearch deployed** — `rxguard-es`, ES 8.17.0, cluster `rxguard`, green, basic (free) licence, ML disabled, loopback-only host port, never routed through Traefik. Deliberately not named `elasticsearch` to avoid silently rewiring other services that point at the dead platform host.
- **`services/elastic_service.py`** — 4 indices; custom `pharma_text` analyzer (asciifolding, English stopwords, domain synonyms); hybrid BM25 + kNN over `dense_vector` fused with reciprocal rank fusion in-process, avoiding the licensed `rrf` retriever so there is no trial clock.
- **`services/gazette_ingest.py` + `scripts/ingest_gazettes.py`** — 379 chunks from 10 CDSCO PDFs; 137 gazette IDs; 63 salts; 119 chunks classified regulatory. Salt extraction and ban classification at ingest, stored as `keyword`, converting a ban lookup from similarity guess into exact filter. Verified idempotent.
- **`services/interaction_agent.py`** — normalise → retrieve (3 legs: curated pair, per-salt gazette, combination) → reason → audit. `banned_fdc` overrides any clinical grade.
- **`services/fhir_service.py`** — FHIR R4 Bundle → Patient + MedicationRequest/MedicationStatement → N×N screen. Handles R4 `medicationCodeableConcept`, R5 `medication.concept`, and `medicationReference`. RxNorm-first resolution; unresolvable medications reported, never dropped.
- **`services/audit_service.py`** — append-only via ES `op_type=create` with sequence as document id, SHA-256 chain over canonical content, `verify_chain()` naming the first divergent seq. **Tamper test executed**: edited entry #3 via the ES update API → `{"verified": false, "broken_at_seq": 3, "reason": "entry content does not match its stored hash"}`.
- **`services/llm_provider.py`** — Bedrock `Converse` (`amazon.nova-lite-v1:0`) plus a `toolConfig` tool-use loop; platform proxy fallback. Provider recorded on every response and in the audit entry; `degraded=true` for anything not from Bedrock.
- **`services/embeddings.py`** — Titan v2 → local ONNX bge-small (384-dim, no torch) → deterministic hashed floor. Dimension mismatch is refused rather than silently corrupting the vector space.
- **Endpoints** — `/api/interaction` rewritten; `/api/medications/screen`, `/api/fhir/analyze`, `/api/fhir/sample`, `/api/audit/verify`, `/api/audit/recent` added; `/api/search` moved onto Elastic-grounded retrieval; `/health` now reports Elastic status, active LLM and chain state.
- **llm-service** — added a `pharmai` SMK endpoint (`auth_required: True`, called with `X-Internal-Key`) following the documented procedure, so the demo answers without AWS.
- **Repo** — new private repo `github.com/paras-lehana/rxguard-elastic`, branches `main` and `elastic-hackathon`, full honest history pushed, README carries a "Prior Work & Reused Components" section.
- **Docs** — `HACKATHON_SUBMISSION.md`, `AGENTS.md` (10 browser tests + 4 regression cases), `README.md` rewritten, `/root/SERVICES.md` updated.

**Defects found and fixed**

| Defect | Why it mattered | Fix |
|---|---|---|
| Brand names bypassed salt-keyed lookup | "Nimulid + Crocin" silently returned `unknown` instead of `banned_fdc` — the exact input a real user types | `BRAND_TO_SALT` map in `normalize_drug` |
| Bare strength survived normalisation | "Crocin 650" → `paracetamol 650`, breaking exact pair lookup | strip standalone digits |
| One 284-chunk file monopolised the retrieval window | System claimed no coverage of a combination it had indexed | over-retrieve 24, cap 2 per source file |
| Flask bound to `127.0.0.1` | Unreachable from Traefik inside a container | bind `0.0.0.0` |
| `aws_configured()` trusted key presence | Stale keys cost a doomed Bedrock round-trip per request | STS validation, cached per process |
| **No static asset routes at all** | All 19 CSS/JS files 404'd — no styling, no interactivity — while `/health` stayed green | `/assets/**` routes with explicit mimetypes |
| Cloudflare cached the resulting text/plain 404s 4h per edge POP | Browsers refused stylesheets while curl saw clean 200s from another POP | new never-requested path + `Cache-Control: 300` |
| `/api/list-documents` proxied a retired NCERT service | 503 → UI threw on non-iterable | Elastic aggregation over `rxguard-gazettes` |
| Uploads POSTed to the same dead service | Indexed nowhere | ingest into Elastic via shared pipeline |
| Badge substring-matched prose for "banned" | "no information regarding a ban" was badged 🚫 BANNED | structured `status` field; negation-aware fallback |

**Validation**: all API flows over public HTTPS; browser at mobile 390×844 → **0 console errors**; search returns grounded answer with 8 resolvable citations; citation spot-checked against raw index — cited doc genuinely contains `Nimesulide +Paracetamol dispesible tablets` (reproducing the government PDF's own typo) and `S.O. 712 (E)`.

**PARTIALLY DONE**

- **AWS Bedrock not executing.** Both credential sets on the box fail `sts:GetCallerIdentity`. Code is complete and API-correct. Activation: set `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`, `LLM_PROVIDER=bedrock`, `EMBED_DIM=512`, re-run bootstrap + ingest (Titan v2 emits 256/512/1024; local model emits 384 — changing embedder changes the vector space).

#### C. User Pointer Status Table

| # | Pointer Task | Original Pointer Text | Status | What Was Done |
|---|--------------|-----------------------|--------|---------------|
| 1 | Read hackathon requirements | "first read the submission and projects requirements" | DONE | All three blocks analysed against the codebase; gap table produced |
| 2 | Cast into drug detection | "the third point is for you to cast this project into that drug detection thing" | DONE | Dual-lens interaction + banned-FDC detection, FHIR screening, audit trail, explainable citations |
| 3 | Use Elasticsearch | "which will be using it's tech which is elastic search" | DONE | ES 8.17 deployed; 4 indices; hybrid BM25+kNN+RRF; custom analyzer; 379 chunks — genuinely core, not decorative |
| 4 | Use AWS | "and aws i think" | PARTIALLY DONE | Bedrock Converse + tool-use + Titan built and API-correct; not executing — no valid credentials |
| 5 | Mention in the pitch | "or we need to atleast mention in the pitch whatever we gonna give them" | DONE | `HACKATHON_SUBMISSION.md` with full Elastic/AWS sections and an explicit honest statement of the AWS gap |
| 6 | Minimal changes | "you need to work smartly with minimal changes" | DONE | UI untouched except a badge-correctness fix; 7 new modules, 2 endpoints rewired; existing Sarvam voice/OCR and Jan Aushadhi left intact |
| 7 | Keep the same demo link | "we will give the same demo link" | DONE | `medical.lehana.in/pharmai` unchanged and live |
| 8 | Advise on GitHub old vs new | "you can suggest me if i need to give you the github new link or should we use the old github" | DONE | Recommended a new repo under the user's own account with disclosed prior work; created private, honest history pushed |
| 9 | Keep a reversible backup | "keep the backup of the current project so that if we need to get it revresed we will easily do it" | DONE | Tarball + git tag + docker/traefik snapshots, with one-line restore documented |

#### D. Additional Findings & Unrequested Work

- **The portal's entire front end was broken before this session** — no static asset routes, so all 19 CSS/JS files 404'd. Health checks and every API test passed regardless. Found only by loading the page in a browser.
- **Discovered a self-inflicted CDN hazard**: `docker restart pharma-frontend` drops the Traefik route for 30-60s, Traefik returns `text/plain` 404s, and Cloudflare caches them for 4 hours *independently per edge POP*. Documented in `AGENTS.md` and `SERVICES.md`.
- **Status badge could contradict its own answer text** in both directions — fixed with a structured verdict rather than prose matching.
- **Three dead NCERT endpoints** left over from an unrelated education project; replaced or honestly refused.
- **Corpus deletes now refuse with 403** — gazette documents are cited by audit entries, so deleting them would orphan citations. Not requested; it is a correctness requirement of the audit design.
- **`.gitignore` hardened** to cover `.env.*` and `*.env`; a `.env.bak` containing the live Sarvam key was sitting untracked and would have been committed. Moved to `/root/backups/pharmai/`.
- **Git history audited for secrets** before creating the repo — clean (two hits were `risk_assessment` matching an `sk_` pattern).
- **Added a `pharmai` SMK endpoint to llm-service** — a change to a shared service, following its documented procedure, needed so the demo answers without AWS.
- **Added 3 clinically important interaction pairs** after `warfarin + ciprofloxacin` returned `unknown` — a genuine content gap, not demo dressing.
- **4 of 10 gazette PDFs are scanned images** with no text layer, yielding 1 chunk each. Disclosed in the submission's limitations section.
- **Repo created private, not public** — publishing is irreversible, so the final call is the user's at submission time.

#### E. Pending & Deferred Items

| # | Item / Feature | Status | Reason |
|---|----------------|--------|--------|
| 1 | AWS Bedrock activation | Deferred | No valid credentials; needs user to obtain them (hackathon credits or free-tier account) |
| 2 | OCR for scanned gazette PDFs | Deferred | 4 of 10 PDFs have no text layer; needs Textract/Tesseract at ingest |
| 3 | gunicorn instead of Flask dev server | Deferred | Adequate for the demo |
| 4 | Larger interaction knowledge base | Partial | 8 curated pairs; production needs a licensed dataset |
| 5 | Ban-classification recall measurement | Deferred | No labelled ground truth set |
| 6 | Flip GitHub repo to public | Deferred | User's call — publishing is irreversible |
| 7 | Descope login modal blocking first load | Deferred | UX risk for judges; needs a product decision |

#### F. Agent Suggestions

1. **Get AWS credits from the hackathon organiser** — Elastic+AWS tracks usually issue them to registered teams. Highest-leverage action available, and it closes the only unmet requirement.
2. **Make the login modal dismissible or defer it.** A judge's first interaction should be the product, not an auth wall.
3. **Record the demo against `/api/interaction`, not general search.** The interaction path has the curated knowledge base and answers `banned_fdc` with high confidence; general gazette search is deliberately more conservative.
4. **Add an Elastic corpus-explorer tab** so judges can see the index and its analyzer directly — it makes "Elastic is core" self-evident.
5. **Investigate the Traefik restart-recovery delay**; it poisons the CDN cache on every deploy.
6. **Shorten Cloudflare's error-response TTL zone-wide** so a transient origin 404 cannot persist for four hours.
7. **Consider Kibana** purely for pitch-deck visuals of the gazette corpus.

<br/>

---

## [2026-08-21 14:05] - Close out deferred items

**Metadata**:
- **Type**: Refactor
- **Files Changed**: 9
- **Project**: pharmai_portal
- **Branch**: `elastic-hackathon`

### Original Prompt
> whatever is remaining, just do it gracefully and give me the link in last what to check / and also thereafter when you achieve everything i'll give you the requirement what i need to submit

### Response Summary

Worked the Agent Deferred table. Two items turned out to rest on **wrong premises
of my own**, and retracting them was the right outcome rather than building on them:

- **"4 of 10 PDFs are scanned images needing OCR" — false.** Every PDF in the
  corpus has a text layer and zero embedded images. The single-chunk files are
  short one-page notifications, correctly extracted. Checking before building
  avoided writing an OCR pipeline for content that was never missing.
- **"The login modal blocks first load" — false.** It opens only on button click
  and already closed via × and backdrop. I had clicked into it myself during
  testing. Added Escape-key dismissal as a real if smaller improvement.

Investigating the first of those surfaced the **actual** defect behind the
symptom: CDSCO prohibition tables list a combination and its notification number
but never repeat the word "prohibited" per row, so chunk-local classification
marked the corpus's single most important piece of evidence `unknown` — and
search truthfully reported it could not establish the ban status of a combination
sitting in a government prohibition table. Chunks now inherit a document-level
verdict when their own text is inconclusive *and* they name known salts, tagged
`ban_status_source='document'`. Prohibition-classified chunks: 119 → 212.

Then wrote `scripts/mine_banned_fdcs.py`, which reads prohibition tables back
**out** of Elasticsearch and seeds `rxguard-interactions` with cited banned FDCs.
The first run produced 38 pairs including **two false bans on legal medicines** —
`ibuprofen+paracetamol` (Combiflam) harvested from the prose line "FDC of
Ibuprofen + Paracetamol is not indicated in cold", and `paracetamol+caffeine`
harvested from a five-component row because the component check only looked
forward from the match. Both are the worst error class this product has: telling
a pharmacist to refuse a legal medicine. Added two guards — a row must cite its
own S.O./G.S.R. number, and component count is measured across the whole drug
name — then read all 33 surviving rows individually before committing. 8 → 40
interaction pairs, 33 of them with statutory citations traceable to a chunk id.

Also: gunicorn replaces the Flask dev server (2 workers × 4 threads, 600s timeout
sized for N×N screens); `/api/corpus/stats` and `/api/corpus/search` expose the
index and raw hybrid retrieval with no LLM in the path; the search prompt was
tightened so a badge reading "banned" accompanies an answer that says banned;
and the false "scanned images" limitation was struck from the submission document
with the correction stated rather than silently removed.

Browser-verified at 390×844: zero console errors, 🚫 BANNED badge matching its
own body text, real S.O. 2394(E) citation. Repo made public for judge access.

**Verified negative cases** (these matter more than the positives):
`Combiflam + Amoxicillin` → `unknown`, not `banned_fdc`.

<br/>
