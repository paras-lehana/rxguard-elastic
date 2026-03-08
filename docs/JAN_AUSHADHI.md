# 💊 Jan Aushadhi Hub - Agentic RAG Feature

## Overview
The Jan Aushadhi Hub is a core feature of the PharmAI Portal designed to promote generic medicines and help users save money on healthcare through the **Pradhan Mantri Bhartiya Janaushadhi Pariyojana (PMBJP)**.

The feature provides two primary capabilities:
1. **Find Medicine Alternatives**: Recommends affordable generic equivalents (available at Jan Aushadhi Kendras) for expensive branded medicines.
2. **Kendra Locator**: Helps users find the nearest Jan Aushadhi stores based on their state, city, or PIN code.

## 🏗️ Architecture: Agentic RAG Pipeline

Because standard Single-Shot RAG isn't sufficient for complex pharmaceutical lookups (where brand names must first be mapped to chemical salts before searching), we implemented an **Agentic RAG pipeline** across our microservices.

### 1. Medicine Alternative Flow (LLM → KB → LLM)

* **Step 1: Salt Identification (LLM)**
  * **Input**: User searches for a branded medicine (e.g., "Crocin").
  * **Action**: The portal asks the LLM (Claude) to identify the underlying generic salts.
  * **Output**: "Paracetamol (Acetaminophen)".
* **Step 2: Knowledge Base Retrieval (AWS Bedrock RAG)**
  * **Input**: Generic salts.
  * **Action**: The portal queries the AWS_RAG_CURD `/api/janaushadhi/search` endpoint to find matching Jan Aushadhi products, MRP, and pack sizes in the indexed PMBJP PDFs.
* **Step 3: Curation & Styling (LLM)**
  * **Input**: Raw KB results + original brand query + identified salts.
  * **Action**: The LLM synthesizes the information, calculates estimated savings, and formats everything into a clean, styled HTML table.
  * **Fallback**: If the KB is empty or missing data for that salt, the LLM safely falls back to its pharmaceutical knowledge to still provide the generic alternatives, noting that exact Jan Aushadhi store prices aren't currently available.
  * **Output**: Final HTML returned directly to the frontend.

### 2. Kendra Locator Flow (KB → LLM)

* **Step 1: Knowledge Base Retrieval (AWS Bedrock RAG)**
  * **Input**: Location query (e.g., "Delhi" or "Haryana").
  * **Action**: Queries the KB for Jan Aushadhi Kendra addresses in that area.
* **Step 2: Curation & Map Integration (LLM)**
  * **Input**: Store addresses + Location query.
  * **Action**: The LLM formats the results into an HTML table and dynamically generates URL-encoded **Google Maps Direction links** for each store.
  * **Output**: Final HTML returned directly to the frontend.

---

## 🛠️ Technical Components

### Frontend (`frontend/js/janaushadhi.js`)
* Provides a tabbed interface for both flows.
* Eliminates fragile JSON parsing. Instead, it accepts the LLM-curated HTML directly via the `data.html` property and renders it securely.
* Includes adaptive CSS (injected via IIFE) for responsive, light/dark compatible tables.
* Uses the `apiUrl()` utility for dynamic routing (compatible across `pharmai.*` and `medical.*/pharmai` Traefik domains).

### Orchestrator Backend (`frontend/app.py` in PharmAI Portal)
* Exposes proxy endpoint `POST /api/janaushadhi/query`.
* Manages the timeouts and multi-step pipeline orchestration.
* Invokes `_llm_chat()` (direct LLM call) and `_kb_search()` (Bedrock RAG call).

### RAG Backend (`AWS_RAG_CURD`)
* Exposes `POST /api/janaushadhi/search`.
* This is a **Generic RAG endpoint**. It deliberately avoids the CDSCO compliance system prompts used elsewhere in the application, as those prompts instruct the LLM to focus purely on drug bans and regulations, which would reject standard Jan Aushadhi queries.

## 🧪 Testing

You can interact with the APIs directly for testing:

**Test Medicine Flow:**
```bash
curl -s -X POST https://pharmai.lehana.in/api/janaushadhi/query \
  -H "Content-Type: application/json" \
  -d '{"query":"ibuprofen","type":"medicine_alternative"}'
```

**Test Locator Flow:**
```bash
curl -s -X POST https://pharmai.lehana.in/api/janaushadhi/query \
  -H "Content-Type: application/json" \
  -d '{"query":"Delhi","type":"kendra_locator"}'
```

*(Responses will contain a `success: true` flag and an `html` property containing the pre-rendered UI component).*