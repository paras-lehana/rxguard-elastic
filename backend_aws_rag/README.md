# Banned Pharma RAG API — AWS Bedrock + Kendra

**Indian pharmaceutical regulatory compliance API** powered by AWS Bedrock Knowledge Base (Kendra GenAI Index).

Replaces Google Gemini File Search with AWS Bedrock for CDSCO banned drugs analysis.

---

## 🏗 Architecture

```
Frontend [subdomain.aidhunik.com]
        │
        ▼
  FastAPI :4101          →  4 REST endpoints
        │
        ▼
  BedrockKBService       →  boto3 (bedrock-agent + bedrock-agent-runtime)
        │
        ▼
  AWS Bedrock KB         →  Kendra GenAI Index + Claude 3 Sonnet
```

## 📁 Project Structure

```
KnowledgeBaseAWS/
├── app/
│   ├── main.py                      # FastAPI app + CORS + health
│   ├── config.py                    # Pydantic Settings (.env)
│   ├── api/
│   │   ├── router.py               # Central router
│   │   └── endpoints/
│   │       ├── index.py            # POST /api/index
│   │       ├── documents.py        # GET /api/documents + DELETE
│   │       └── search.py           # POST /api/search (RAG)
│   ├── core/
│   │   ├── bedrock_client.py       # boto3 client factory
│   │   ├── bedrock_service.py      # KB operations
│   │   └── response_transformer.py # Format responses
│   ├── models/
│   │   └── schemas.py              # Pydantic models (29 fields)
│   ├── utils/
│   │   └── custom_prompt.py        # RAG prompt loader
│   └── data/
│       └── rag_system_prompt.txt   # Full CDSCO compliance prompt
├── sample/                          # Sample CDSCO documents for testing
│   ├── cdsco_banned_01Jan2018.pdf
│   ├── cdsco_banned_02Aug2024.pdf
│   ├── cdsco_banned_02Jun2023.pdf
│   ├── cdsco_banned_11Jan2019.pdf
│   ├── cdsco_banned_12Aug2024.pdf
│   ├── cdsco_banned_12Aug2024_2.pdf
│   ├── cdsco_banned_22Nov2021.pdf
│   ├── cdsco_banned_combined.pdf
│   ├── cdsco_banned_combined_short.pdf
│   ├── banned-drugs-cdsco-1940.pdf
│   └── delhi.pdf
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── .dockerignore
```

## 🚀 Quick Start

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env with your AWS credentials and Bedrock KB ID
```

**Required `.env` variables:**

| Variable | Description | Example |
|----------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | `wJal...` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `BEDROCK_KB_ID` | Bedrock Knowledge Base ID | `U8LJNJ0FQN` |
| `BEDROCK_MODEL_ID` | Foundation model | `anthropic.claude-3-sonnet-20240229-v1:0` |
| `PORT` | Server port | `4101` |

### 2. Run with Docker (Recommended)

```bash
docker-compose up --build
```

### 3. Run Locally

```bash
pip install -r requirements.txt
python -m app.main
```

### 4. Verify

```bash
# Health check
curl http://localhost:4101/health

# OpenAPI docs
open http://localhost:4101/docs
```

---

## 📡 API Endpoints

### POST `/api/index` — Upload & Index PDF

```bash
curl -X POST http://localhost:4101/api/index \
  -F "file=@sample/cdsco_banned_01Jan2018.pdf" \
  -F 'metadata={"source": "CDSCO"}'
```

**Response:**
```json
{
  "message": "Document indexed successfully",
  "result": {
    "done": true,
    "documentName": "KB-XXX/documents/YYY"
  }
}
```

### GET `/api/documents` — List Documents (Paginated)

```bash
# Page 1 with 10 items per page (default)
curl http://localhost:4101/api/documents

# Explicit pagination
curl "http://localhost:4101/api/documents?page=1&size=10"

# Page 2
curl "http://localhost:4101/api/documents?page=2&size=10"
```

**Query Parameters:**

| Param | Default | Range | Description |
|-------|---------|-------|-------------|
| `page` | `1` | `>= 1` | Page number (1-based) |
| `size` | `10` | `1-100` | Items per page |

**Response:**
```json
{
  "documents": [
    {
      "name": "KB-XXX/documents/YYY",
      "displayName": "cdsco_banned_01Jan2018.pdf",
      "state": "ACTIVE",
      "is_active": true,
      "metadata": []
    }
  ],
  "total": 12,
  "page": 1,
  "total_pages": 2,
  "page_size": 10
}
```

### POST `/api/documents/delete` — Delete Document (Soft + Hard Delete)

Deletion uses a two-step approach:
1. **Soft-delete**: Sets `_is_active=false` → immediately hidden from search/listing
2. **Hard-delete**: Permanently removes from Kendra index

```bash
curl -X POST http://localhost:4101/api/documents/delete \
  -H "Content-Type: application/json" \
  -d '{"documentId": "KB-XXX/documents/YYY"}'
```

**Response:**
```json
{"message": "Document deleted successfully"}
```

> **Note**: Requires `_is_active` custom attribute registered in Kendra index.
> Set `ENABLE_SOFT_DELETE=false` in `.env` to disable if not configured.

### POST `/api/documents/delete_all` — Bulk Delete All Documents

Deletes **every document** in the Knowledge Base. Internally:
1. Paginates through Kendra to collect all document IDs
2. Soft-deletes each (sets `_is_active=false`) for immediate hiding
3. Hard-deletes in batches of 10

```bash
curl -X POST http://localhost:4101/api/documents/delete_all
```

**Response:**
```json
{
  "message": "All 10 documents deleted successfully.",
  "deleted_count": 10,
  "failed_count": 0,
  "failed_ids": []
}
```

> **WARNING**: This is a destructive operation. All documents will be permanently removed.

### POST `/api/search` — RAG Search (Critical)

```bash
curl -X POST http://localhost:4101/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Is nimesulide banned in India?", "sessionId": "pharma-001"}'
```

**Response (29 fields):**
```json
{
  "query": "Is nimesulide banned in India?",
  "medicine_searched": "nimesulide",
  "total_results": "1",
  "current_status": "banned",
  "results": {
    "gazette_id": "GSR 91(E)",
    "pdf_name": "cdsco_banned_01Jan2018.pdf",
    "medicine_name": "nimesulide",
    "date_of_ban": "10 Feb 2011",
    "date_of_uplift": "N/A",
    "summary": "Nimesulide banned by CDSCO under Section 26A...",
    "reasons_for_ban": "Risk of hepatotoxicity...",
    "reasons_for_uplift": "N/A",
    "drug_category": "single_drug",
    "population_restriction": "children",
    "schedule_classification": "N/A",
    "controlled_status": "N/A",
    "source_authority": "CDSCO",
    "act_reference": "Drugs and Cosmetics Act 1940 Section 26A",
    "name_image_match": "N/A",
    "source_banned": "file",
    "source_internet": "",
    "source_approved": "never banned",
    "source_scheduled": "",
    "source_scheduled_file": "",
    "source_controlled": "",
    "keyword": "nimesulide",
    "misc": "",
    "reasoning": "Found in CDSCO banned drugs list...",
    "itemid": "N/A"
  },
  "text": "Nimesulide is banned...",
  "sessionId": "pharma-001"
}
```

---

## 📝 Sample Documents

The `sample/` folder contains 11 CDSCO regulatory PDFs for testing:

| File | Description |
|------|-------------|
| `cdsco_banned_01Jan2018.pdf` | Banned drugs list till 2017 |
| `cdsco_banned_22Nov2021.pdf` | Additional banned drugs (Nov 2021) |
| `cdsco_banned_02Jun2023.pdf` | Additional banned drugs (Jun 2023) |
| `cdsco_banned_02Aug2024.pdf` | Additional banned drugs (Aug 2024) |
| `cdsco_banned_12Aug2024.pdf` | Banned drugs (12 Aug 2024) |
| `cdsco_banned_12Aug2024_2.pdf` | Banned drugs batch 2 (12 Aug 2024) |
| `cdsco_banned_11Jan2019.pdf` | Banned drugs (Jan 2019) |
| `cdsco_banned_combined.pdf` | Combined banned drugs list |
| `cdsco_banned_combined_short.pdf` | Short combined list |
| `banned-drugs-cdsco-1940.pdf` | Historical CDSCO 1940 Act drugs |
| `delhi.pdf` | Delhi drugs department + import banned |

**Upload all samples:**
```bash
for pdf in sample/*.pdf; do
  echo "Uploading: $pdf"
  curl -X POST http://localhost:4101/api/index \
    -F "file=@$pdf" \
    -F "metadata={\"source\": \"CDSCO\"}"
done
```

---

## ⚙️ Configuration

All configuration is via environment variables (`.env` file). Change `BEDROCK_KB_ID` → restart → works with a different KB.

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_REGION` | `us-east-1` | AWS region |
| `BEDROCK_MODEL_ID` | `anthropic.claude-3-sonnet-20240229-v1:0` | Foundation model |
| `PORT` | `4101` | Server port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `ENABLE_SOFT_DELETE` | `true` | Enable soft-delete (set `_is_active=false` before hard-delete). Disable if Kendra attribute not registered. |

### Kendra Soft-Delete Setup

For soft-delete to work, register the `_is_active` custom attribute in your Kendra index:

1. **Via AWS Console**: Amazon Kendra → Select Index → Facets/Custom Attributes → Add attribute:
   - Name: `_is_active`
   - Type: `STRING_VALUE`
   - Searchable: No
   - Displayable: Yes
   - Facetable: Yes

2. **Via API** (one-time): The service includes a `register_is_active_attribute()` helper method.

If not configured, set `ENABLE_SOFT_DELETE=false` — deletion will still work but without the instant-hide behavior.

---

## 🐳 Docker

```bash
# Build
docker-compose build

# Start
docker-compose up -d

# Logs
docker-compose logs -f api

# Stop
docker-compose down

# Restart with new KB
# Edit .env → change BEDROCK_KB_ID
docker-compose restart
```

---

## 📄 License

Internal project — Indian pharmaceutical regulatory compliance.
