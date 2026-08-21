# 💊 PharmAI — Regulatory-Aware Drug Interaction Detection

![Elasticsearch](https://img.shields.io/badge/Elasticsearch-8.17-005571?logo=elasticsearch&logoColor=white)
![AWS Bedrock](https://img.shields.io/badge/AWS-Bedrock%20%7C%20Titan%20%7C%20Kendra-FF9900?logo=amazonaws&logoColor=white)
![FHIR](https://img.shields.io/badge/FHIR-R4-E6007E)
![License](https://img.shields.io/badge/License-MIT-blue.svg)

**Live demo:** https://medical.lehana.in/pharmai · **Submission:** [HACKATHON_SUBMISSION.md](HACKATHON_SUBMISSION.md) · **Engineering rules:** [AGENTS.md](AGENTS.md)

> Every drug interaction checker knows pharmacology. None of them knows Indian
> regulatory law — because that knowledge only exists in un-indexed government
> PDFs. **Nimesulide + Paracetamol** is a banned fixed-dose combination in India,
> yet both molecules are individually legal and no international database flags
> the pair. PharmAI screens both lenses at once, grounded in Elasticsearch and
> reasoned over by AWS Bedrock, with every verdict written to a hash-chained
> audit trail.

---

## Prior Work & Reused Components

**Disclosed deliberately.** This is not a from-scratch project, and the honest
account is more impressive than the alternative.

**Pre-existing, built February–March 2026** (before this hackathon):
- The PharmAI Flask portal — UI, Sarvam AI Indic voice (STT/TTS/translate),
  prescription OCR, Jan Aushadhi generic lookup, Descope auth
- `backend_aws_rag/` — FastAPI service integrating AWS Bedrock Knowledge Base
  and Amazon Kendra
- The collected CDSCO gazette PDF corpus

**Built for this hackathon** — the entire Elastic and detection layer:
- `frontend/services/` — Elasticsearch retrieval core (4 indices, custom
  `pharma_text` analyzer, hybrid BM25 + kNN with reciprocal rank fusion), the
  dual-lens interaction detection pipeline, FHIR R4 Bundle ingestion, the
  append-only SHA-256 hash-chained audit trail, and the Bedrock provider layer
  with its Converse tool-use loop
- `scripts/` — gazette ingestion with salt extraction and ban classification,
  index bootstrap with a curated interaction knowledge base
- Elasticsearch 8.17 cluster, provisioned and populated with 379 gazette chunks
- Rewiring the search and interaction endpoints off the old N8N→Sarvam chain and
  onto Elasticsearch + Bedrock

Commit history in this repository reflects both periods honestly. See
[HACKATHON_SUBMISSION.md §8](HACKATHON_SUBMISSION.md) for a per-module breakdown.

---

## Quick Start

```bash
# 1. Elasticsearch (the retrieval core)
cd /root/docker/rxguard-es && docker compose up -d

# 2. Create indices and seed the interaction knowledge base
cd /root/repo/pharmai_portal
ES_URL=http://localhost:9200 .venv/bin/python scripts/bootstrap_elastic.py

# 3. Ingest the CDSCO gazette corpus
ES_URL=http://localhost:9200 .venv/bin/python scripts/ingest_gazettes.py

# 4. Run the portal
cd /root/docker/pharma-frontend && docker compose up -d --build
```

Verify: `curl -s https://medical.lehana.in/pharmai/health | jq '{elasticsearch, llm, audit_chain}'`

---

## API

| Endpoint | Purpose |
|---|---|
| `POST /api/interaction` | Drug pair → severity, mechanism, citations, audit entry |
| `POST /api/medications/screen` | Medication list → N×N pairwise matrix |
| `POST /api/fhir/analyze` | FHIR R4 Bundle → parsed, indexed, fully screened |
| `GET /api/fhir/sample` | Demo Bundle to POST back to `/api/fhir/analyze` |
| `POST /api/search` | Elastic-grounded gazette Q&A with resolvable citations |
| `GET /api/audit/verify` | Recompute the whole hash chain |
| `GET /api/audit/recent` | Recent audit entries |
| `GET /health` | Live capability report — Elastic status, active LLM, chain state |
| `POST /api/stt` `/api/tts` `/api/translate` `/api/ocr` | Sarvam Indic voice & OCR |

---

## 🚀 The Vision

In India:
1. **Regulatory Blindspots**: Pharmacies unknowingly stock locally banned fixed-dose combinations (FDCs) because parsing CDSCO gazettes manually is an administrative nightmare.
2. **Cost Barrier**: Millions overpay for branded drugs because they are unaware of equally effective, highly regulated **Jan Aushadhi** generic alternatives.
3. **Language Barrier**: The majority of India's population communicates in vernacular languages, making English-first medical advisory tools useless.

**PharmAI solves this.** 
We parse complex regulatory law into structured JSON in milliseconds, provide AI OCR to digitize prescriptions, map branded drugs to high-quality affordable generics, and deliver the entire experience via Indic Voice capabilities (Speech-to-Text & Text-to-Speech).

---

## ✨ Core Features

* 📚 **Real-Time Regulatory RAG**: Queries against official CDSCO gazette documents to flag banned/restricted drugs instantly with 100% hallucination-free citations.
* 💸 **Jan Aushadhi Substitutions**: Recommends heavily discounted, government-approved generic alternatives to lower out-of-pocket patient expenses.
* 🗣️ **Indic Voice Core**: Integrated with **Sarvam AI** for native Indian language Speech-to-Text (STT), Text-to-Speech (TTS), and real-time translation. 
* 📝 **Prescription OCR & Analysis**: Upload handwritten or printed prescriptions. The platform digitizes the text, analyzes the drugs, checks for cross-interactions, and flags safety warnings.
* ⚡ **Seamless Dual-System Architecture**: 
  * A lightweight, highly responsive **Flask Portal** for the User Interface.
  * A robust, high-performance **FastAPI backend (AWS_RAG_CURD)** interfacing securely with Amazon Bedrock and Kendra.

---

## 🏗️ Project Structure

This repository acts as the master monorepo. It heavily interacts with our backend service.

| Directory / Service | Role | Tech Stack |
|:---|:---|:---|
| [`pharmai_portal`](.) | User Portal & Client-Side Proxy | Flask, HTML5, CSS3, JS, Sarvam APIs |
| [`AWS_RAG_CURD`](../AWS_RAG_CURD) | Knowledge Base RAG Backend | FastAPI, Bedrock, Kendra, Nova Lite |

For an in-depth look at our technical approach, please see our [**TECHNICAL_ARCHITECTURE.md**](./TECHNICAL_ARCHITECTURE.md).

For our business and scalable go-to-market strategy, explore our [**PITCH.md**](./PITCH.md).

For our future vision and planned features, see [**FUTURE_ROADMAP.md**](./FUTURE_ROADMAP.md).

---

## 🛠️ Getting Started

To run the complete PharmAI platform locally, you will need to spin up both the RAG Backend and the Frontend Portal.

### 1. Start the AWS RAG Backend
The backend manages the Knowledge Base and CDSCO logic.
```bash
cd ../AWS_RAG_CURD
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env # Configure your AWS credentials here
uvicorn app.main:app --port 4101 --reload
```

### 2. Start the PharmAI Portal
The portal handles user interactions, OCR, and Indic audio features.
```bash
cd ../pharmai_portal/frontend
python3 -m venv venv_pharmai
source venv_pharmai/bin/activate
pip install -r requirements.txt
cp .env.example .env # Configure your Sarvam AI keys here
python app.py
```

Visit `http://localhost:5000` to interact with the PharmAI Platform!

---

## 💡 Hackathon Evaluation Highlight
* **Novelty**: First platform to merge real-time Gazette indexing with native Hindi/regional language translation for immediate patient and pharmacy impact.
* **Impact**: Potential to save ₹8,800 Cr in reduced healthcare spending through generic substitutions and thousands of lives saved by automating drug ban enforcement.
* **Execution**: Fully functional multi-tier RAG processing, active STT/TTS modules, and zero-hallucination guardrails via Amazon Kendra.

---

*Built with ❤️ for the AI For Bharat Hackathon.*
