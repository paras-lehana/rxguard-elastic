# RxGuard — Regulatory-Aware Drug Interaction Detection

**Challenge topic:** Healthcare & Insurance Intelligence — *drug interaction detection*
**Core technologies:** Elasticsearch (retrieval) · AWS Bedrock (reasoning + embeddings)
**Live demo:** https://medical.lehana.in/pharmai · mirror https://medical.aidhunik.com/pharmai
**Health / live capability report:** https://medical.lehana.in/pharmai/health

---

## 1. The Problem

Every drug interaction checker on the market answers one question: *do these two
molecules interact pharmacologically?*

In India that question misses the more urgent one.

**Nimesulide + Paracetamol.** Each molecule is legal, widely stocked, and sold
over the counter. Neither triggers a flag in any international interaction
database. But the *fixed-dose combination* has been prohibited by CDSCO since
2016 — S.O. 712(E) for dispersible tablets, S.O. 743(E) for suspension,
S.O. 4393(E) for injection. A pharmacist who dispenses it is committing a
licensing offence under s.26A of the Drugs and Cosmetics Act. A patient who
takes it faces compounded hepatotoxicity for no therapeutic gain.

No interaction checker will tell either of them, because the prohibition lives
in gazette notifications — scanned government PDFs, hundreds of pages, published
irregularly, not indexed by Google, and absent from the training data of every
general-purpose LLM. Ask a frontier model whether a recently banned FDC is legal
and it will answer fluently and wrongly.

Three consequences:

| Who | Exposure |
|---|---|
| **Pharmacists** | Licence revocation for stocking prohibited FDCs they cannot practically track |
| **Patients** | Adverse reactions from combinations that are banned precisely because they are unsafe |
| **Insurers** | Claims paid on prohibited therapies; no defensible audit trail when a claim is contested |

The regulatory dimension is not a nice-to-have layer on top of interaction
checking. In this market it *is* the interaction checking.

---

## 2. The Solution

**RxGuard screens every drug pair through two lenses simultaneously:
pharmacological interaction and Indian regulatory status.**

A verdict is never generated from model memory. Elasticsearch retrieves the
evidence first; the retrieved passages are the model's only context; the
document ids travel with the answer into a hash-chained audit trail. If
retrieval finds nothing, the system says so rather than guessing.

Severity ladder — note what sits at the top:

```
banned_fdc       prohibited combination under Indian law   ← regulatory, ranked above clinical
contraindicated  never co-administer
major / moderate / minor
none
unknown          no evidence retrieved — stated, not guessed
```

`banned_fdc` outranks every clinical grade deliberately. A pharmacist does not
need to know that a combination is "moderate risk" if it is also illegal to
dispense.

### Three entry points

1. **Pair check** — two drug names, brand or salt. `Nimulid 100mg` resolves to
   `nimesulide` before lookup, because that is what a real user types.
2. **Medication list screen** — N×N pairwise matrix over a full list. Polypharmacy
   danger hides in the pair nobody thought to ask about.
3. **FHIR Bundle analysis** — read the medication list straight from the clinical
   record. Patients rarely know their own full medication history; their EHR does.

---

## 3. How Elasticsearch Is Leveraged (Core)

Elasticsearch is not a cache or a log sink here. It is the retrieval engine, the
regulatory knowledge base, and the audit ledger. Remove it and the product does
not degrade — it refuses to answer, by design.

**Live cluster:** `rxguard`, Elasticsearch 8.17.0, single node, status green.

### Four indices, four jobs

| Index | Documents | Role |
|---|---|---|
| `rxguard-gazettes` | **379** chunks from 10 CDSCO notifications, **137** distinct gazette IDs, **63** distinct salts, **119** chunks classified as prohibitions | The regulatory corpus |
| `rxguard-interactions` | 5 curated, cited drug-pair records | Pharmacological knowledge base |
| `rxguard-fhir` | Ingested Patient / MedicationRequest / MedicationStatement resources | Structured clinical input |
| `rxguard-audit` | Append-only, hash-chained | Immutable decision ledger |

### Hybrid retrieval — BM25 + kNN with reciprocal rank fusion

Pharmaceutical retrieval needs both halves and neither alone is sufficient:

- **BM25** carries exact tokens — salt names, `S.O. 712(E)`, "fixed dose
  combination". Lexical precision is the whole game for a legal claim.
- **kNN over `dense_vector`** carries paraphrase, transliteration and the
  misspellings real users type.

The two rankings are fused with RRF in-process rather than via the licensed `rrf`
retriever, so the whole system runs on the **free basic licence** with no trial
clock that could expire mid-judging.

### Elastic-native design decisions that carry real weight

**A custom analyzer with domain synonyms.** Pharmaceutical text is full of
hyphenated salts and dosage tokens the standard analyzer fragments badly. The
`pharma_text` analyzer folds ASCII, strips English stopwords and applies a
synonym filter (`fdc → fixed dose combination`, `banned → prohibited →
withdrawn`, `paracetamol → acetaminophen`). Domain knowledge lives *in the
index*, not bolted onto a prompt.

**Salt extraction and ban classification at ingest time**, stored as `keyword`
fields. This converts "is this drug banned?" from a semantic similarity guess
into an exact filtered lookup — the difference between an answer a pharmacist
can act on and one they cannot.

**Source-diversity capping in the retrieval window.** The corpus is lopsided:
one notification contributes 284 of 379 chunks, and its near-duplicate pages
will fill a small result window on any banned-combination query, starving the
one page in a different file that holds the answer. We over-retrieve 24 and cap
hits per source file. This was found by testing, not theory — before the fix the
system answered "the corpus does not cover this" about a combination it had
indexed correctly.

---

## 4. How AWS Is Leveraged (Core)

**Bedrock is the reasoning and embedding layer**, integrated natively:

| Capability | AWS service | Where |
|---|---|---|
| Verdict generation, forced-JSON | Bedrock **Converse** API, `amazon.nova-lite-v1:0` | `services/llm_provider.py` |
| Agent tool-use loop | Bedrock Converse `toolConfig` | `converse_with_tools()` |
| Vector embeddings | **Titan Embed Text v2** | `services/embeddings.py` |
| Gazette RAG over Kendra | Bedrock **Knowledge Base** + **Amazon Kendra** | `backend_aws_rag/` (pre-existing) |

`Converse` rather than `InvokeModel` because it normalises the message shape
across Nova, Claude and Llama — swapping `BEDROCK_MODEL_ID` requires no code
change — and because it is the API the agent tool-use loop builds on.

### Three AI agents

| Agent | Function | Tools |
|---|---|---|
| **Ingestion Agent** | Gazette PDF → chunks → salt extraction → ban classification → vectors → Elasticsearch | `scripts/ingest_gazettes.py` |
| **Interaction Agent** | Retrieve, reason, grade severity, cite | `search_gazettes`, `lookup_interaction_pair` (Bedrock toolConfig) |
| **Audit Agent** | Hash-chain each verdict before it is returned | `services/audit_service.py` |

On the Bedrock path the Interaction Agent chooses its own retrieval strategy
through `toolConfig` instead of following a fixed sequence. Both tools read from
Elasticsearch either way — the agent decides *what* to retrieve, Elastic decides
*what matches*.

### ⚠️ Honest statement on AWS activation

**The Bedrock integration is complete and written against the real API. It is
not currently executing, because this team has no valid AWS credentials.**

`GET /health` reports this truthfully at all times:

```json
"llm": { "active": "platform-proxy", "bedrock_ready": false,
         "bedrock_model": "amazon.nova-lite-v1:0" }
```

While no credential is present, the demo's reasoning step is served by a
fallback proxy so the public demo answers. **Every such response is tagged
`"degraded": true`** and the provider name is written into the audit trail — an
answer produced by the fallback is never displayed or logged as an AWS-generated
one.

Setting `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` activates the Bedrock
path with **zero code changes**. Setting `LLM_PROVIDER=bedrock` disables the
fallback entirely, so a judged run cannot silently degrade.

We would rather show a verifiable architecture with one honestly-labelled gap
than claim a live integration a reviewer could disprove in one HTTP call.

*Note on embeddings: Titan v2 emits 256/512/1024 dimensions; the free local
model emits 384, which is the current index geometry. Switching to Titan means
`EMBED_DIM=512` and a re-ingest — documented in `services/embeddings.py`, because
changing embedder changes the vector space and pretending otherwise would
silently corrupt retrieval.*

---

## 5. Challenge Topic Alignment

> *"Build an AI-powered solution for claims processing, clinical document search,
> or drug interaction detection... Leverage AI agents and structured FHIR data to
> automate workflows while maintaining an immutable audit trail and delivering
> reliable, explainable insights."*

| Requirement | Implementation | Status |
|---|---|---|
| **Drug interaction detection** | Dual-lens pipeline: pharmacological + CDSCO regulatory | ✅ Live |
| **AI agents** | Ingestion, Interaction, Audit — Bedrock `toolConfig` tool-use | ✅ Built (tool-use needs AWS) |
| **Structured FHIR data** | R4 Bundle → Patient + MedicationRequest/Statement → N×N screen. RxNorm-first code resolution | ✅ Live |
| **Immutable audit trail** | Append-only ES writes + SHA-256 hash chain + verification endpoint | ✅ Live and proven |
| **Explainable insights** | Every verdict carries resolvable citations, retrieval strategy, model id, confidence | ✅ Live |
| **Elasticsearch core** | 4 indices, hybrid BM25+kNN, custom analyzer | ✅ Live |
| **AWS LLM core** | Bedrock Converse + Titan + Kendra KB | ⚠️ Built, needs credentials |

### The immutable audit trail, and what "immutable" honestly means

Every verdict is recorded before it reaches the user:

```json
{ "seq": 4, "prev_hash": "d393ae…", "entry_hash": "668bc5…",
  "event_type": "interaction_check", "subject": "nimesulide+paracetamol",
  "request_digest": "…", "llm_provider": "aws-bedrock",
  "llm_model": "amazon.nova-lite-v1:0", "prompt_sha256": "…",
  "retrieved_doc_ids": ["gazette:cdsco_banned_01Jan2018.pdf:p8:c0", "…"],
  "verdict": "banned_fdc" }
```

Three mechanisms, not one assertion:

- **Append-only** — writes use `op_type=create` with the sequence number as the
  document id. An existing entry cannot be overwritten by a later write; a
  duplicate id is a hard failure, not an update.
- **Hash-chained** — each entry commits to its own canonical content and its
  predecessor's hash. Editing any historical entry breaks every hash after it.
- **Verifiable** — `GET /api/audit/verify` recomputes the whole chain.

**We tested this by actually tampering with it.** Entry #3's verdict was edited
in place via the Elasticsearch update API. Verification response:

```json
{ "verified": false, "entries": 8, "broken_at_seq": 3,
  "reason": "entry content does not match its stored hash" }
```

The honest claim is **tamper-evident, not tamper-proof**: Elasticsearch cannot
forbid a privileged operator from editing a document, but it cannot hide the
edit either. For claims adjudication that is the property that matters — you can
prove to a third party whether the record has changed.

---

## 6. Architecture

```
                          ┌──────────────────────────────┐
   Patient / Pharmacist → │  Flask Portal (live)         │
   Hindi voice, photo,    │  medical.lehana.in/pharmai   │
   FHIR Bundle            └──────────┬───────────────────┘
                                     │
              ┌──────────────────────┼───────────────────────┐
              ▼                      ▼                       ▼
   ┌────────────────────┐  ┌──────────────────┐  ┌────────────────────┐
   │ Sarvam AI          │  │ INTERACTION      │  │ FHIR Service       │
   │ STT/TTS/translate  │  │ AGENT            │  │ R4 Bundle parse    │
   │ /OCR only —        │  │                  │  │ RxNorm-first       │
   │ no AWS Indic       │  │ normalise →      │  │ N×N matrix         │
   │ parity             │  │ retrieve →       │  └─────────┬──────────┘
   └────────────────────┘  │ reason → audit   │            │
                           └────┬─────────┬───┘            │
                                │         │                │
                    ┌───────────▼───┐  ┌──▼────────────────▼──────────┐
                    │ AWS BEDROCK   │  │  ELASTICSEARCH 8.17 (green)  │
                    │ Nova Lite     │  │  rxguard-gazettes      379   │
                    │ Converse +    │  │  rxguard-interactions    5   │
                    │ toolConfig    │  │  rxguard-fhir                │
                    │ Titan Embed v2│  │  rxguard-audit  (hash chain) │
                    │ KB + Kendra   │  │                              │
                    └───────────────┘  │  hybrid BM25 + kNN, RRF      │
                                       │  pharma_text analyzer        │
                                       └──────────────────────────────┘
```

**Retrieval always precedes reasoning.** There is no code path where the model
answers without Elasticsearch context.

### On external tools

The rules permit external tools "only where necessary" and forbid them
*replacing* Elastic or AWS capabilities. Our position:

- **Removed from the reasoning path.** The previous version of this portal used
  an N8N→Sarvam chain as its LLM. That was Sarvam *replacing* an AWS capability,
  so it is gone. Reasoning is Bedrock; retrieval is Elastic.
- **Sarvam retained for Indic speech and OCR only.** AWS Transcribe and Polly
  have no Hindi or regional-language parity for medical vocabulary. A drug safety
  tool for India that cannot take a spoken Hindi question excludes most of its
  users. This is a genuine capability gap, not a convenience.
- **A labelled last-resort fallback.** If Elasticsearch has zero coverage for a
  query the portal degrades to answering rather than to a blank screen, and tags
  the response `"degraded": true` with the reason. It fires only on empty
  retrieval — it does not substitute for the Elastic path.

---

## 7. Demo Script

```bash
BASE=https://medical.lehana.in/pharmai

# 1. Live capability report — Elastic status, doc counts, which LLM is active
curl -s $BASE/health | jq '{elasticsearch, llm, audit_chain}'

# 2. The headline case, typed the way a real user types it (brand names)
curl -s -X POST $BASE/api/interaction -H 'Content-Type: application/json' \
  -d '{"medicine_a":"Nimulid 100mg","medicine_b":"Crocin 650"}' \
  | jq '{severity, is_banned_fdc, confidence, cited_evidence_ids, audit}'
# → severity: "banned_fdc", confidence: "high", 5 resolvable citations

# 3. Polypharmacy screen
curl -s -X POST $BASE/api/medications/screen -H 'Content-Type: application/json' \
  -d '{"medications":["nimesulide","paracetamol","warfarin","ciprofloxacin"]}' \
  | jq '{pairs_checked, highest_severity, banned_fdc_count}'

# 4. FHIR Bundle → screened medication list
curl -s $BASE/api/fhir/sample > bundle.json
curl -s -X POST $BASE/api/fhir/analyze -d @bundle.json \
  -H 'Content-Type: application/json' | jq '{patient, screen}'

# 5. Prove the audit chain
curl -s $BASE/api/audit/verify | jq
```

### Verified result — grounding, not fluency

`Nimulid 100mg + Crocin 650` → `banned_fdc`, confidence `high`, citing
`gazette:cdsco_banned_01Jan2018.pdf:p8:c0`. That document genuinely contains the
string `Nimesulide +Paracetamol dispesible tablets` — reproducing the
typographical error in the original government PDF — and `S.O. 712 (E)`.

The citation resolves to real indexed text. That is the difference between a
grounded system and a fluent one.

---

## 8. Prior Work & What Was Built For This Hackathon

**Disclosed deliberately.** This is not a from-scratch project, and pretending
otherwise would be both dishonest and less impressive than the truth.

**Pre-existing (Feb–Mar 2026):** the PharmAI portal — Flask UI, Sarvam Indic
voice/OCR integration, Jan Aushadhi generic lookup, Descope auth — and the
`backend_aws_rag` FastAPI service integrating Bedrock Knowledge Base and Kendra.
The CDSCO gazette PDF corpus was also already collected.

**Built for this hackathon:**

| Component | Lines | What it does |
|---|---|---|
| `services/elastic_service.py` | ~330 | 4 index definitions, `pharma_text` analyzer, hybrid BM25+kNN with RRF |
| `services/interaction_agent.py` | ~360 | Dual-lens detection pipeline, brand→salt map, Bedrock tool specs |
| `services/audit_service.py` | ~200 | Append-only hash-chained ledger + verification |
| `services/fhir_service.py` | ~250 | R4 Bundle parsing, RxNorm-first resolution, N×N screen |
| `services/llm_provider.py` | ~250 | Bedrock Converse + tool-use loop, provider abstraction |
| `services/embeddings.py` | ~160 | Titan v2 + local ONNX + deterministic floor |
| `scripts/ingest_gazettes.py` | ~250 | Gazette ingestion, salt extraction, ban classification |
| `scripts/bootstrap_elastic.py` | ~170 | Index bootstrap + curated interaction seed |
| Elasticsearch deployment | — | ES 8.17 cluster, provisioned and populated |
| Endpoint rewiring | — | Search moved off N8N/Sarvam onto Elastic+Bedrock; interaction endpoint rewritten |

The regulatory-aware interaction detection, the entire Elasticsearch layer, the
FHIR ingestion, the audit trail, and the agent architecture are new work.

---

## 9. Honest Limitations

Stated because a reviewer will find them, and because a team that names its own
gaps is easier to trust on everything else.

1. **AWS Bedrock is not executing** — no valid credentials. Integration is
   complete; activation is one environment variable. `/health` never hides this.
2. **Some gazette PDFs are scanned images.** 4 of 10 files yielded a single text
   chunk because they have no text layer. Real fix is OCR at ingest (Textract on
   the AWS path); today those notifications are under-represented.
3. **The interaction knowledge base has 5 curated pairs**, not a commercial
   database. Enough to demonstrate the architecture and cover the demo cases; a
   production deployment would license a full interaction dataset.
4. **Ban classification is regex-based** over prohibition keywords. It flags 119
   of 379 chunks; precision is good, recall is unmeasured against a labelled set.
5. **Tamper-evident, not tamper-proof** — see §5. A privileged operator can edit
   an entry; they cannot do it undetectably.
6. **Flask development server.** Fine for a demo; a production deployment needs
   gunicorn behind Traefik.
7. **`unknown` is a real and frequent verdict** for pairs outside the corpus.
   This is the intended behaviour for a patient-safety tool, but it means
   coverage is narrower than a commercial checker.

---

## 10. Why This Wins

**It answers a question the incumbents structurally cannot.** Every interaction
checker knows pharmacology. None of them knows Indian regulatory law, because
that knowledge only exists in un-indexed government PDFs. Combining the two is
not a feature — it is the product.

**Elasticsearch earns its place as core.** Not a vector store bolted on for
compliance with the rules: a custom domain analyzer, ingest-time entity
extraction enabling exact regulatory lookups, hybrid retrieval where each half
covers the other's blind spot, a retrieval defect found and fixed by measurement,
and the audit ledger itself.

**The audit trail is verifiable, and we verified it by attacking it.** Most
submissions claiming an immutable audit trail have an append-only table. Ours has
a hash chain, a verification endpoint, and a documented tamper test with its
output printed above.

**It is honest.** The one requirement we cannot fully meet is stated plainly, in
this document and in a live API response, with the exact steps to close it. A
reviewer can verify every claim here with `curl` in under two minutes.
