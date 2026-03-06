# 🧬 Pharmaceutical Compliance RAG System

An advanced **Retrieval Augmented Generation (RAG)** system specifically designed for pharmaceutical regulatory compliance in India. This system helps **government platforms** analyze drug regulations, bans, scheduling, and compliance status according to **CDSCO (Central Drugs Standard Control Organisation)** guidelines.

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Docker Deployment](#-docker-deployment)
- [API Reference](#-api-reference)
- [File Descriptions](#-file-descriptions)
- [Regulatory Categories](#-regulatory-categories)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

## 🚀 Features

### Core Capabilities
- **Government Pharmaceutical Compliance Analysis**: Automated drug regulatory status checking
- **CDSCO Regulatory Document Processing**: Analysis of official Indian drug regulations  
- **Drug Ban Detection**: Identifies banned substances according to latest gazette notifications
- **Schedule Classification**: Determines Schedule H/H1/X drug categories
- **Controlled Substance Analysis**: NDPS Act compliance checking
- **Gazette Notification Processing**: Real-time regulatory updates processing
- **Enhanced Context Processing**: Bigger context windows for complex pharmaceutical queries

### Technical Features  
- **Pathway AI Framework**: Advanced RAG implementation with pharmaceutical optimizations
- **OpenRouter LLM Integration**: Claude Sonnet 4 model for intelligent analysis
- **Semantic Search**: SentenceTransformer embeddings for accurate document retrieval
- **Professional REST API**: Comprehensive endpoints for pharmaceutical compliance queries
- **Comprehensive Logging**: Structured logging for compliance monitoring and debugging
- **Persistent Caching**: Enhanced performance with intelligent caching system
- **Safety Alerts**: Public health notifications and warnings

## 🚀 Key Features

### Real-time Document Monitoring
- **Live Indexing**: Automatically processes new documents as they arrive
- **Vector Search**: Semantic similarity search for regulatory queries
- **Metadata Extraction**: Extracts key information like drug names, dates, and regulatory actions
- **Multi-format Support**: PDF, DOC, DOCX, and text document processing

### REST API Endpoints
- `POST /v1/retrieve` - Query documents with natural language or keywords
- `GET /v1/statistics` - View indexing statistics and system health
- `GET /v1/inputs` - List all indexed documents and their metadata

### Specialized for Pharmaceutical Documents
- **Regulatory Language Processing**: Optimized for legal and pharmaceutical terminology
- **Multi-language Support**: Handles English and Hindi text (for Gazette documents)
- **Table Extraction**: Preserves complex document structures and tables
- **Citation Tracking**: Maintains page references for regulatory compliance

## 📁 Project Structure

```
pharma-rag-query/
├── app_openrouter_enhanced.py    # Main application entry point
├── app_openrouter_enhanced.yaml  # Enhanced configuration for document processing
├── requirements.txt              # Python dependencies
├── README.md                     # This documentation
├── data/                         # Directory for regulatory documents (Gazette PDFs, etc.)
├── Cache_Enhanced/               # Caching directory for processed documents
├── tests/                        # Test suite
├── scripts/                      # Deployment and utility scripts
├── docs/                         # Documentation
├── examples/                     # Usage examples
└── archived/                     # Legacy files
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- Virtual environment (recommended)

### Local Development Setup

1. **Clone and Navigate**
   ```bash
   cd pharma-rag-query
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Add Your Documents**
   ```bash
   # Place your Gazette of India PDFs and regulatory documents in the data/ directory
   cp /path/to/gazette-documents/*.pdf data/
   ```

5. **Start the Application**
   ```bash
   python app_openrouter_enhanced.py
   ```

   The application will be available at `http://localhost:8001`

## 🐳 Docker Deployment

### Quick Start (PharmAI Portal)

```bash
cd /root/repo/pharmai_portal
docker compose up -d --build
```

### Service

| Service | URL | Internal Port | Description |
|---------|-----|---------------|-------------|
| pharmai-portal | https://pharmai.lehana.in | 5000 | Flask-based PharmAI web portal |

### Routing Model

- Traefik routing is configured via Docker labels (auto-discovery), not file-provider backend IP mappings.
- Router rule supports both domains: `pharmai.lehana.in` and `pharmai.aidhunik.com`.
- Health endpoint: `/health` (also available as `/pharmai/health`).

### Environment Variables

```bash
cp .env.example .env
```

Minimum portal variables:

- `PORT=5000`
- `FLASK_DEBUG=false`
- `SERVER_HOST=backend-pharmai-portal`

### Logs

```bash
docker compose logs -f pharmai-portal
```

### Virtual Environment Deployment

The system is designed for virtual environment deployment:

1. **Using Start Script**
   ```bash
   ./scripts/start.sh
   ```

2. **Manual Startup**
   ```bash
   source venv/bin/activate
   python app_openrouter_enhanced.py
   ```

## 📖 Usage Examples

### Query for Drug Bans
```bash
curl -X POST "http://localhost:8001/v1/pw_ai_answer" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Which drugs were banned in the latest gazette notification?",
    "model": "anthropic/claude-3.5-sonnet"
  }'
```

### Search for Specific Drug Information
```bash
curl -X POST "http://localhost:8001/v1/pw_ai_answer" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Analyze regulatory status of tramadol for government compliance",
    "model": "anthropic/claude-3.5-sonnet"
  }'
```

### Check System Statistics
```bash
curl -X GET "http://localhost:8000/v1/statistics"
```

### List Indexed Documents
```bash
curl -X GET "http://localhost:8000/v1/inputs"
```

## ⚙️ Configuration

The `app.yaml` file contains all configuration options:

### Key Settings
- **Data Sources**: Configure file paths and monitoring intervals
- **Embedding Model**: Uses `mixedbread-ai/mxbai-embed-large-v1` for pharmaceutical text
- **Text Splitting**: 512 tokens with 50-token overlap for regulatory context
- **Parser Settings**: High-resolution parsing for tables and complex layouts
- **Caching**: Enabled for improved performance

### Pharmaceutical-Specific Settings
```yaml
pharma_settings:
  priority_terms:
    - "banned"
    - "prohibited" 
    - "schedule"
    - "controlled substance"
    - "drug"
    - "pharmaceutical"
    - "compliance"
    - "gazette"
```

## 🏗️ Architecture

### Document Processing Pipeline
1. **Document Ingestion**: Monitors data/ directory for new files
2. **Parsing**: Extracts text using Unstructured library with high-resolution parsing
3. **Chunking**: Splits documents into 512-token chunks with overlap
4. **Embedding**: Converts text to vectors using specialized embedding model
5. **Indexing**: Stores vectors in retrievable index with metadata
6. **API Service**: Provides REST endpoints for querying

### Technology Stack
- **Pathway AI**: Real-time data processing framework
- **Sentence Transformers**: For document embeddings
- **Unstructured**: Document parsing and extraction
- **FastAPI**: REST API framework
- **Python Virtual Environment**: Isolated deployment environment

## 🔧 Development

### Adding New Data Sources
To monitor additional document sources, update the `$sources` section in `app.yaml`:

```yaml
$sources:
  - !pw.io.fs.read
    path: additional-docs
    format: binary
    with_metadata: true
```

### Customizing for Other Regulatory Bodies
1. Update `pharma_settings.priority_terms` in `app.yaml`
2. Add language support in parser configuration
3. Modify document type filters as needed

### Performance Tuning
- Adjust `max_tokens` in splitter for different chunk sizes
- Modify `reserved_space` in retriever for larger document collections
- Enable/disable caching based on use case

## 🚨 Monitoring & Troubleshooting

### Health Checks
- Application health: `GET /v1/statistics`
- Document count: Check the `indexed_documents` field
- Processing errors: Monitor application logs

### Common Issues
1. **Documents not indexing**: Check file permissions in data/ directory
2. **Memory issues**: Reduce `max_tokens` or `reserved_space` settings
3. **Slow queries**: Enable caching and check embedding model performance

## 📊 API Reference

### POST /v1/retrieve
Query pharmaceutical documents using natural language.

**Request Body:**
```json
{
  "query": "string",     // Your search query
  "k": 5,               // Number of results to return
  "metadata_filter": {} // Optional metadata filtering
}
```

**Response:**
```json
{
  "results": [
    {
      "text": "Document content...",
      "metadata": {
        "filename": "gazette-2024-01.pdf",
        "page": 15,
        "publication_date": "2024-01-15"
      },
      "score": 0.85
    }
  ]
}
```

### GET /v1/statistics
Returns system statistics and health information.

### GET /v1/inputs
Lists all indexed documents with metadata.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add your changes with tests
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review Pathway documentation: https://pathway.com/developers
3. Open an issue in the repository

---

**Built with ❤️ for pharmaceutical compliance and regulatory monitoring**