# LawVisor

**Multi-Modal AI Legal Risk Assistant**

> Enterprise-grade, explainable AI system for legal contract analysis. Not a chatbot — an auditable, regulation-anchored compliance platform.

<p align="center">
  <a href="#problem">Problem</a> •
  <a href="#solution">Solution</a> •
  <a href="#features">Features</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#api">API</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#deployment">Deployment</a>
</p>

---

## Problem

Legal contracts are dense, complex, and error-prone to manually review. Small businesses, startups, and non-legal professionals struggle to identify compliance risks related to:

- Data protection obligations
- Liability exposure
- Jurisdictional conflicts
- Regulatory requirements

Existing tools are either manual, opaque, or **hallucinate legal interpretations**.

## Solution

LawVisor is a multi-modal AI legal assistant that:

1. **Ingests** legal contracts (scanned or native PDFs)
2. **Extracts** structured clauses with confidence scoring
3. **Evaluates** compliance against real, verifiable regulations (GDPR / SEC)
4. **Produces** explainable, deterministic risk scores with citations

**LawVisor does not replace lawyers.** It accelerates legal review with transparent, auditable AI reasoning.

---

## Goals & Success Metrics

| Metric | Target |
|--------|--------|
| Clause extraction accuracy | ≥ 90% |
| OCR confidence threshold | ≥ 0.85 |
| Regulatory citation accuracy | 100% verified |
| API response time | < 3 seconds (avg) |
| Deployment readiness | One-click deploy |

### Core Principles

- ✅ **Zero hallucinated legal facts**
- ✅ **Explainable, clause-level risk analysis**
- ✅ **Production-ready MVP, not a demo**
- ✅ **Every AI claim cites regulation or reasoning chain**

---

## Target Users

| Persona | Need |
|---------|------|
| **Startup Founder** | Quick contract risk visibility |
| **Compliance Officer** | Regulation-mapped clause analysis |
| **Legal Analyst** | Explainable AI reasoning |
| **VC Due Diligence** | Deterministic scoring & citations |
| **Auditor** | Audit-ready, traceable outputs |

---

## Features

### 1. Document Ingestion

Accepts and preprocesses legal contracts reliably.

- ✅ PDF uploads (scanned + native)
- ✅ Automatic detection of scanned vs text-based PDFs
- ✅ Structure preservation (headers, tables, footnotes)
- ✅ Rejection if OCR confidence < threshold

**Output Schema:**
```json
{
  "document_id": "uuid",
  "status": "processed"
}
```

### 2. Clause Extraction

Converts raw legal text into structured, classified clauses.

**Mandatory Clause Types:**
- Data Protection
- Liability
- Termination
- Intellectual Property
- Jurisdiction

**Clause Schema:**
```json
{
  "clause_id": "C-12",
  "type": "Data Protection",
  "raw_text": "...",
  "confidence": 0.91
}
```

**Constraints:**
- Confidence scoring required
- No hardcoded classification logic
- Explainable extraction process

### 3. Regulatory Fetching

Retrieves real, up-to-date regulatory text from verifiable sources.

**Supported Regulations (MVP):**
- **GDPR**: Articles 5, 6, 7, 12, 13, 17, 25, 28, 32, 33, 44, 46
- **SEC**: Regulations 10b-5, FD, S-K, 13D

**Requirements:**
- Fetch from verifiable sources only
- Intelligent caching
- Normalized regulation text
- Graceful failure if unavailable

**Output Schema:**
```json
{
  "regulation": "GDPR Article 5(1)(c)",
  "source_url": "...",
  "last_updated": "2025-01-10"
}
```

### 4. RAG-Based Legal Reasoning

Compares contract clauses against regulations using semantic analysis.

**Process:**
1. Embed clause text
2. Retrieve relevant regulations
3. Perform semantic comparison
4. Identify mismatches

**Output Schema:**
```json
{
  "risk_level": "High",
  "violated_regulation": "GDPR Article 5(1)(c)",
  "explanation": "The clause allows excessive data retention...",
  "confidence": 0.92
}
```

**Constraints:**
- ❌ No hallucinated conclusions
- ✅ Every claim must cite regulation or reasoning chain

### 5. Risk Scoring Engine

Produces explainable, deterministic risk scores.

**Risk Levels:**
- **Clause-level** risk
- **Category-level** risk
- **Overall contract** risk (0–100)

**Scoring Rules:**
- No black-box scoring
- Weighted aggregation formula
- Deterministic, reproducible output

```
Risk Score = (Weighted Average × 0.6) + Max Risk Penalty + Density Adjustment
```

**Final Output:**
```json
{
  "overall_risk": 68,
  "high_risk_clauses": [...],
  "citations": [...],
  "scoring_explanation": {
    "base_weighted_score": 52.7,
    "high_risk_penalty": 10,
    "density_adjustment": 5.3,
    "final_score": 68
  }
}
```

---

## Architecture

### System Structure

```
lawvisor/
├── backend/
│   ├── api/
│   │   ├── upload.py          # Document upload handling
│   │   ├── analyze.py         # Analysis orchestration
│   │   └── risk.py            # Risk data access
│   ├── core/
│   │   ├── ocr.py             # OCR and text extraction
│   │   ├── clause_extractor.py # Clause classification
│   │   ├── rag_engine.py      # RAG compliance analysis
│   │   ├── risk_engine.py     # Risk scoring
│   │   ├── regulations.py     # Regulatory data fetching
│   │   └── config.py          # Configuration management
│   ├── schemas/               # Pydantic models
│   └── main.py                # FastAPI application
│
└── frontend/
    ├── src/
    │   ├── components/        # React components
    │   ├── lib/               # API client & utilities
    │   ├── pages/             # Next.js pages
    │   └── styles/            # Tailwind CSS
    └── package.json
```

### Data Flow

```
┌─────────────┐    ┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌─────────────┐
│   PDF       │───▶│    OCR      │───▶│   Clause     │───▶│    RAG      │───▶│    Risk     │
│   Upload    │    │  Processing │    │  Extraction  │    │  Analysis   │    │   Scoring   │
└─────────────┘    └─────────────┘    └──────────────┘    └─────────────┘    └─────────────┘
       │                  │                  │                  │                  │
       ▼                  ▼                  ▼                  ▼                  ▼
   Validate          Extract Text       Classify          Compare with       Calculate
   & Store          (native/scan)       with LLM         Regulations        Risk Scores
```

---

## Tech Stack

### AI & ML
| Component | Technology |
|-----------|------------|
| LLM | OpenAI (GPT-4o / GPT-4o-mini) |
| OCR | pytesseract, OpenCV, pdfplumber |
| Embeddings | sentence-transformers (local) |
| Vector DB | Pinecone |

### Backend
| Component | Technology |
|-----------|------------|
| Framework | FastAPI (async-first) |
| Language | Python 3.10+ |
| Validation | Pydantic v2 |
| Logging | structlog |

### Frontend
| Component | Technology |
|-----------|------------|
| Framework | Next.js 14 / React 18 |
| Styling | Tailwind CSS |
| Deployment | Vercel |

---

## API Specification

### Upload Document

```http
POST /upload
Content-Type: multipart/form-data
```

**Request:** `file: <PDF file>`

**Response:**
```json
{
  "document_id": "doc-abc123def456",
  "filename": "contract.pdf",
  "file_size_bytes": 1024000,
  "status": "pending",
  "message": "Document uploaded successfully."
}
```

### Analyze Document

```http
POST /analyze/{document_id}
```

**Response:**
```json
{
  "document_id": "doc-abc123def456",
  "status": "completed",
  "risk_report": {
    "overall_risk": 68,
    "overall_risk_level": "high",
    "total_clauses_analyzed": 24,
    "high_risk_clauses": [...],
    "citations": [...]
  },
  "processing_time_seconds": 45.2
}
```

### Get Risk Report

```http
GET /risk/{document_id}
```

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Tesseract OCR
- API keys: OpenAI + Pinecone

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run server
uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Visit `http://localhost:3000` to access the application.

### Windows-Specific Setup

1. **Tesseract OCR**:
   - Download: https://github.com/UB-Mannheim/tesseract/wiki
   - Install to: `C:\Program Files\Tesseract-OCR`
   - Set `.env`: `TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe`

2. **Poppler** (for pdf2image):
   - Download: https://github.com/osborn-poppler-for-windows/releases
   - Add `bin` folder to PATH

---

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `LLM_MODEL` | Model identifier (default: `gpt-4o-mini`) | No |
| `PINECONE_API_KEY` | Pinecone vector DB key | Yes |
| `PINECONE_ENVIRONMENT` | Pinecone environment | Yes |
| `TESSERACT_PATH` | Path to Tesseract binary | Yes |
| `OCR_CONFIDENCE_THRESHOLD` | Minimum OCR confidence (default: 0.85) | No |

---

## Deployment

### Backend (Docker)

```bash
cd backend
docker build -t lawvisor-backend .
docker run -p 8000:8000 --env-file .env lawvisor-backend
```

### Docker Compose

```bash
cd backend
docker-compose up -d
```

### Frontend (Vercel)

1. Push frontend to GitHub
2. Connect to Vercel
3. Set: `NEXT_PUBLIC_API_URL=https://your-api.com`
4. Deploy

---

## Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| **Security** | Environment-based API keys, no hardcoded secrets |
| **Explainability** | Mandatory reasoning for all AI outputs |
| **Reliability** | Graceful failure handling |
| **Scalability** | Modular, async-first architecture |
| **Compliance** | Zero legal hallucinations |

---

## Failure Conditions

LawVisor **halts analysis** if:

- ❌ Regulatory data cannot be verified
- ❌ OCR confidence < threshold
- ❌ Embedding retrieval confidence is insufficient

---

## Limitations

| Limitation | Description |
|------------|-------------|
| **Not legal advice** | LawVisor provides AI-assisted analysis, not legal opinions |
| **English only** | Currently optimized for English legal documents |
| **Regulatory scope** | Limited to GDPR and SEC (MVP) |
| **Document size** | Complex documents may require longer processing |

---

## Future Enhancements

- [ ] Multi-jurisdiction support (CCPA, HIPAA, SOX)
- [ ] Redlining suggestions
- [ ] Contract comparison / diff
- [ ] Audit-ready export (PDF / JSON)
- [ ] Human-in-the-loop review
- [ ] Webhook integrations
- [ ] Batch processing API

---

## Out of Scope (MVP)

- ❌ Legal advice generation
- ❌ Court case predictions
- ❌ Automated contract rewriting

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <strong>LawVisor</strong> — Auditable. Deterministic. Regulation-Anchored.
</p>
