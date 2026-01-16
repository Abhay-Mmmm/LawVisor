"""
LawVisor Core Module
====================
Core business logic for legal document analysis.

Modules:
- ocr: Document ingestion and text extraction
- clause_extractor: Legal clause extraction and classification
- regulations: Regulatory data fetching and caching
- rag_engine: RAG-based compliance analysis
- risk_engine: Risk scoring and reporting
- config: Application configuration
"""

from core.clause_extractor import ClauseExtractor, ClauseType, ExtractedClause, ExtractionResult
from core.config import CLAUSE_TYPES, RISK_LEVELS, get_settings
from core.ocr import DocumentContent, DocumentType, OCRError, OCRProcessor, PageContent
from core.rag_engine import ComplianceAnalysis, RAGEngine, RetrievedContext
from core.regulations import (
    RegulationArticle,
    RegulationSet,
    RegulationsFetcher,
    RegulationType,
    get_regulations_fetcher,
)
from core.risk_engine import (
    CategoryRisk,
    ClauseRisk,
    ContractRiskReport,
    RiskEngine,
    RiskLevel,
)

__all__ = [
    # OCR
    "OCRProcessor",
    "DocumentContent",
    "DocumentType",
    "PageContent",
    "OCRError",
    # Clause Extraction
    "ClauseExtractor",
    "ExtractedClause",
    "ExtractionResult",
    "ClauseType",
    # Regulations
    "RegulationsFetcher",
    "RegulationArticle",
    "RegulationSet",
    "RegulationType",
    "get_regulations_fetcher",
    # RAG Engine
    "RAGEngine",
    "ComplianceAnalysis",
    "RetrievedContext",
    # Risk Engine
    "RiskEngine",
    "ClauseRisk",
    "CategoryRisk",
    "ContractRiskReport",
    "RiskLevel",
    # Config
    "get_settings",
    "CLAUSE_TYPES",
    "RISK_LEVELS",
]
