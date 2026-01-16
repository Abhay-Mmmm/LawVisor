"""
Pytest configuration and fixtures for LawVisor tests.
"""
import os
import sys
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock environment variables before importing app
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("PINECONE_API_KEY", "test-pinecone-key")
os.environ.setdefault("PINECONE_ENVIRONMENT", "test-env")
os.environ.setdefault("LLM_MODEL", "llama-3.3-70b-versatile")
os.environ.setdefault("TESSERACT_PATH", "/usr/bin/tesseract")


@pytest.fixture(scope="session")
def mock_settings():
    """Mock settings for testing."""
    with patch.dict(os.environ, {
        "GROQ_API_KEY": "test-groq-key",
        "PINECONE_API_KEY": "test-pinecone-key",
        "PINECONE_ENVIRONMENT": "test-env",
        "LLM_MODEL": "llama-3.3-70b-versatile",
        "TESSERACT_PATH": "/usr/bin/tesseract",
    }):
        yield


@pytest.fixture
def test_client(mock_settings) -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app."""
    from main import app
    
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_pdf_content() -> bytes:
    """Generate sample PDF content for testing."""
    # Minimal valid PDF structure
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test Contract) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000214 00000 n 
trailer
<< /Size 5 /Root 1 0 R >>
startxref
306
%%EOF"""
    return pdf_content


@pytest.fixture
def sample_extracted_clauses():
    """Sample extracted clauses for testing."""
    return [
        {
            "clause_id": "clause-001",
            "clause_type": "data_protection",
            "text": "The Data Processor shall process personal data only on documented instructions from the Data Controller.",
            "page_number": 1,
            "confidence": 0.92,
            "metadata": {
                "section": "Data Processing",
                "paragraph": 3
            }
        },
        {
            "clause_id": "clause-002",
            "clause_type": "liability",
            "text": "Neither party shall be liable for any indirect, incidental, or consequential damages.",
            "page_number": 2,
            "confidence": 0.88,
            "metadata": {
                "section": "Limitation of Liability",
                "paragraph": 1
            }
        },
        {
            "clause_id": "clause-003",
            "clause_type": "termination",
            "text": "Either party may terminate this agreement with 30 days written notice.",
            "page_number": 4,
            "confidence": 0.95,
            "metadata": {
                "section": "Termination",
                "paragraph": 1
            }
        }
    ]


@pytest.fixture
def sample_risk_report():
    """Sample risk report for testing."""
    return {
        "document_id": "doc-test123",
        "overall_risk": 65,
        "overall_risk_level": "high",
        "total_clauses_analyzed": 3,
        "high_risk_clauses": [
            {
                "clause_id": "clause-002",
                "clause_type": "liability",
                "risk_level": "high",
                "risk_score": 78,
                "issues": ["Broad liability limitation may not be enforceable"],
                "citations": ["GDPR Article 82"]
            }
        ],
        "category_risks": {
            "data_protection": {"risk_score": 55, "clause_count": 1},
            "liability": {"risk_score": 78, "clause_count": 1},
            "termination": {"risk_score": 25, "clause_count": 1}
        },
        "citations": [
            {
                "source": "GDPR",
                "article": "Article 28",
                "text": "Processor requirements",
                "relevance": 0.89
            }
        ],
        "scoring_explanation": {
            "base_weighted_score": 52.7,
            "high_risk_penalty": 10,
            "density_adjustment": 2.3,
            "final_score": 65
        }
    }


@pytest.fixture
def mock_ocr_processor():
    """Mock OCR processor."""
    mock = MagicMock()
    mock.process_document.return_value = {
        "text": "Sample contract text with legal clauses...",
        "pages": 5,
        "confidence": 0.9,
        "document_type": "native"
    }
    return mock


@pytest.fixture
def mock_clause_extractor():
    """Mock clause extractor."""
    mock = MagicMock()
    mock.extract_clauses.return_value = {
        "clauses": [
            {
                "clause_id": "c1",
                "clause_type": "data_protection",
                "text": "Personal data processing clause",
                "confidence": 0.9
            }
        ],
        "total": 1
    }
    return mock


@pytest.fixture
def mock_rag_engine():
    """Mock RAG engine."""
    mock = MagicMock()
    mock.analyze_compliance.return_value = {
        "findings": [],
        "citations": [],
        "compliance_score": 80
    }
    return mock


@pytest.fixture
def mock_risk_engine():
    """Mock risk engine."""
    mock = MagicMock()
    mock.calculate_risk.return_value = {
        "overall_risk": 50,
        "risk_level": "medium"
    }
    return mock
