# Task Log — PharmAI / RxGuard Portal

> **Purpose**: Structured task tracker for every session, with status and time-stamped logs.
> **Last updated**: 2026-08-21

---

## Session: 2026-08-21 — Recast onto Elasticsearch + AWS Bedrock for hackathon

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Locate the "banned pharma" project | ✅ Done | 5 codebases found; `repo/pharmai_portal` is the flagship. `backend_aws_rag/.env.example` is headed "Banned Pharma RAG API" |
| 2 | Read hackathon submission + project requirements | ✅ Done | Elastic + AWS LLM core; topic = drug interaction detection + FHIR + audit trail |
| 3 | Back up the project reversibly | ✅ Done | 14M tarball + git tag `pre-elastic-hackathon-2026-08-21` + docker/traefik configs |
| 4 | Stand up Elasticsearch | ✅ Done | `rxguard-es` 8.17.0, cluster green, basic licence |
| 5 | Build Elastic retrieval core | ✅ Done | 4 indices, `pharma_text` analyzer, hybrid BM25+kNN with RRF |
| 6 | Ingest CDSCO gazette corpus | ✅ Done | 379 chunks, 137 gazette IDs, 63 salts, 119 regulatory chunks |
| 7 | Build AWS Bedrock integration | ⚠️ Partial | Converse + tool-use + Titan written and correct; **not executing — no valid AWS credentials** |
| 8 | Drug interaction detection pipeline | ✅ Done | Dual-lens (pharmacological + CDSCO); `banned_fdc` outranks clinical severity |
| 9 | FHIR R4 Bundle ingestion | ✅ Done | Patient + MedicationRequest/Statement → N×N screen, RxNorm-first |
| 10 | Immutable audit trail | ✅ Done | Append-only + SHA-256 chain + verify endpoint; tamper test passes |
| 11 | Rewire endpoints off N8N/Sarvam | ✅ Done | Reasoning + retrieval now Elastic+Bedrock; Sarvam limited to voice/OCR |
| 12 | Write submission/pitch document | ✅ Done | `HACKATHON_SUBMISSION.md`, including honest AWS-gap statement |
| 13 | Create AGENTS.md | ✅ Done | With 10 browser test cases + 4 regression cases |
| 14 | New GitHub repo with prior-work disclosure | ✅ Done | `paras-lehana/rxguard-elastic`, **private** — user flips to public at submission |
| 15 | Browser validation, mobile 390×844 | ✅ Done | Found 4 defects curl could not; all fixed; zero console errors |
| 16 | Update platform SERVICES.md | ✅ Done | Both new services registered with gotchas |

**Log**:
- 12:35 — Discovery: 5 pharma codebases, 3 deployment configs, nothing publicly reachable
- 12:42 — Confirmed both AWS credential sets dead (`InvalidClientTokenId`); no ES cluster anywhere
- 12:47 — Backup taken; `pharmai` SMK endpoint added to llm-service for the demo fallback
- 12:52 — Elasticsearch 8.17 deployed, cluster green
- 12:58 — 379 gazette chunks ingested with local ONNX embeddings
- 13:00 — First end-to-end verdict; found brand-name normalisation bug (Nimulid → unknown)
- 13:03 — Brand→salt map added; `banned_fdc` now correct with high confidence
- 13:05 — Audit chain tamper test: detects the exact broken sequence number
- 13:07 — Container deployed; all API flows pass over public HTTPS
- 13:11 — **Browser test reveals the entire UI is broken** — 19 assets 404, no static routes
- 13:16 — Static routes added; NCERT dead endpoints replaced with Elastic aggregation
- 13:21 — Assets moved to `/assets/**` to escape Cloudflare-cached 404s; zero console errors
- 13:24 — Found badge contradicting its own text; replaced prose-sniffing with structured status
- 13:26 — Committed, pushed, registry updated

---

## 🕐 Agent Deferred

> Items scoped but not completed — carried forward until explicitly resolved.

| # | Item | Deferred On | Reason | Status |
|---|------|-------------|--------|--------|
| 1 | Activate AWS Bedrock | 2026-08-21 | No valid AWS credentials. Integration complete; needs `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` in `frontend/.env`, then `LLM_PROVIDER=bedrock`, `EMBED_DIM=512`, re-run bootstrap + ingest | ⏳ Pending — user action |
| 2 | OCR the scanned gazette PDFs | 2026-08-21 | 4 of 10 PDFs have no text layer, yielding 1 chunk each. Needs Textract or Tesseract at ingest | ⏳ Pending |
| 3 | Replace Flask dev server with gunicorn | 2026-08-21 | Works for the demo; not production-grade | ⏳ Pending |
| 4 | Expand interaction knowledge base | 2026-08-21 | 8 curated pairs demonstrate the architecture; production needs a licensed dataset | ⏳ Pending |
| 5 | Measure ban-classification recall | 2026-08-21 | Regex flags 119/379 chunks; precision looks good, recall unmeasured against a labelled set | ⏳ Pending |
| 6 | Flip GitHub repo to public | 2026-08-21 | Created private deliberately — publishing is irreversible and is the user's call at submission time | ⏳ Pending — user action |

---

## 💡 Agent Suggestions

> Agent recommendations, not user requests.

| # | Suggestion | Raised On | Priority | Status |
|---|-----------|-----------|----------|--------|
| 1 | Get AWS credits from the hackathon organiser's portal/Discord — Elastic+AWS tracks usually issue them to registered teams. Highest-leverage 10 minutes available | 2026-08-21 | High | ⏳ Open |
| 2 | Make the Descope login modal dismissible or defer it — judges hitting a forced auth wall on first load is a scoring risk | 2026-08-21 | High | ⏳ Open |
| 3 | Add an Elastic-powered "corpus explorer" tab so judges can see the index directly | 2026-08-21 | Med | ⏳ Open |
| 4 | Record the demo video against the interaction endpoint, not general search — the interaction path has the curated KB and answers with high confidence | 2026-08-21 | High | ⏳ Open |
| 5 | Add Kibana for pitch-deck visuals of the gazette corpus | 2026-08-21 | Low | ⏳ Open |
| 6 | Investigate why the Traefik route takes 30-60s to recover after `docker restart`; it poisons the Cloudflare cache each time | 2026-08-21 | Med | ⏳ Open |
| 7 | Set a shorter Cloudflare `max-age` for error responses zone-wide, so a transient origin 404 cannot persist 4 hours | 2026-08-21 | Med | ⏳ Open |
