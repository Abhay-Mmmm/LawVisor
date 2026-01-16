"""
LawVisor API Schemas
====================
Pydantic models for API request/response validation.
All API contracts are defined here for type safety and documentation.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# === Enums ===

class DocumentTypeEnum(str, Enum):
    """Type of PDF document."""
    NATIVE = "native"
    SCANNED = "scanned"
    HYBRID = "hybrid"


class ClauseTypeEnum(str, Enum):
    """Legal clause type classifications."""
    DATA_PROTECTION = "data_protection"
    LIABILITY = "liability"
    TERMINATION = "termination"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    JURISDICTION = "jurisdiction"
    CONFIDENTIALITY = "confidentiality"
    INDEMNIFICATION = "indemnification"
    FORCE_MAJEURE = "force_majeure"
    PAYMENT_TERMS = "payment_terms"
    WARRANTIES = "warranties"
    DISPUTE_RESOLUTION = "dispute_resolution"
    AMENDMENT = "amendment"
    ASSIGNMENT = "assignment"
    GOVERNING_LAW = "governing_law"
    SEVERABILITY = "severability"
    NOTICES = "notices"
    ENTIRE_AGREEMENT = "entire_agreement"
    COUNTERPARTS = "counterparts"
    UNKNOWN = "unknown"


class RiskLevelEnum(str, Enum):
    """Risk level categories."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"


class AnalysisStatusEnum(str, Enum):
    """Status of document analysis."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# === Upload Schemas ===

class UploadResponse(BaseModel):
    """Response for document upload."""
    document_id: str = Field(..., description="Unique identifier for the uploaded document")
    filename: str = Field(..., description="Original filename")
    file_size_bytes: int = Field(..., description="File size in bytes")
    upload_timestamp: datetime = Field(..., description="Timestamp of upload")
    status: AnalysisStatusEnum = Field(..., description="Current processing status")
    message: str = Field(..., description="Status message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "doc-abc123def456",
                "filename": "contract.pdf",
                "file_size_bytes": 1024000,
                "upload_timestamp": "2024-01-15T10:30:00Z",
                "status": "pending",
                "message": "Document uploaded successfully. Ready for analysis."
            }
        }


# === Clause Schemas ===

class ClauseSchema(BaseModel):
    """Schema for an extracted clause."""
    clause_id: str = Field(..., description="Unique clause identifier")
    clause_type: ClauseTypeEnum = Field(..., description="Classification of the clause")
    title: str = Field(..., description="Clause title or heading")
    raw_text: str = Field(..., description="Original text of the clause")
    normalized_text: str = Field(..., description="Cleaned and normalized text")
    page_number: int = Field(..., description="Page where clause appears")
    confidence: float = Field(..., ge=0, le=1, description="Extraction confidence (0-1)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "clause_id": "CL-abc123",
                "clause_type": "data_protection",
                "title": "Data Processing Agreement",
                "raw_text": "The Processor shall process personal data...",
                "normalized_text": "The processor shall process personal data...",
                "page_number": 3,
                "confidence": 0.92
            }
        }


class ExtractionResultSchema(BaseModel):
    """Result of clause extraction."""
    document_id: str
    extracted_at: datetime
    clauses: list[ClauseSchema]
    total_clauses: int
    clause_type_distribution: dict[str, int]
    average_confidence: float


# === Risk Assessment Schemas ===

class ContributingFactorSchema(BaseModel):
    """A factor contributing to risk score."""
    factor: str = Field(..., description="Name of the factor")
    value: float = Field(..., description="Factor value")
    description: str = Field(..., description="Explanation of the factor")


class ClauseRiskSchema(BaseModel):
    """Risk assessment for a single clause."""
    clause_id: str
    clause_type: ClauseTypeEnum
    clause_title: str
    clause_text_preview: str = Field(..., max_length=500)
    risk_score: float = Field(..., ge=0, le=100)
    risk_level: RiskLevelEnum
    contributing_factors: list[ContributingFactorSchema]
    violated_regulations: list[str]
    recommendations: list[str]
    explanation: str
    confidence: float = Field(..., ge=0, le=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "clause_id": "CL-abc123",
                "clause_type": "data_protection",
                "clause_title": "Data Processing Agreement",
                "clause_text_preview": "The Processor shall process personal data...",
                "risk_score": 72.5,
                "risk_level": "high",
                "contributing_factors": [
                    {
                        "factor": "Base Compliance Score",
                        "value": 65,
                        "description": "Score from regulatory compliance analysis"
                    }
                ],
                "violated_regulations": ["GDPR Article 5(1)(c)"],
                "recommendations": [
                    "Add explicit data minimization provisions",
                    "Include specific retention periods"
                ],
                "explanation": "This clause lacks data minimization requirements...",
                "confidence": 0.85
            }
        }


class CategoryRiskSchema(BaseModel):
    """Aggregated risk for a clause category."""
    category: str
    category_display: str
    risk_score: float = Field(..., ge=0, le=100)
    risk_level: RiskLevelEnum
    clause_count: int
    high_risk_clauses: int
    top_issues: list[str]


class CitationSchema(BaseModel):
    """A regulatory citation."""
    regulation_id: str
    title: str
    source_url: str
    regulation_type: str


class ScoringBreakdownSchema(BaseModel):
    """Breakdown of how overall score was calculated."""
    weighted_average: dict[str, float]
    max_risk_penalty: dict[str, float]
    high_risk_density: dict[str, Any]
    formula: str


class RiskReportSchema(BaseModel):
    """Complete risk assessment report."""
    document_id: str
    analyzed_at: datetime
    overall_risk_score: float = Field(..., ge=0, le=100, alias="overall_risk")
    overall_risk_level: RiskLevelEnum
    total_clauses_analyzed: int
    high_risk_clause_count: int
    medium_risk_clause_count: int
    low_risk_clause_count: int
    category_risks: list[CategoryRiskSchema]
    high_risk_clauses: list[ClauseRiskSchema]
    summary: str
    citations: list[CitationSchema]
    confidence: float = Field(..., ge=0, le=1)
    scoring_breakdown: ScoringBreakdownSchema
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "document_id": "doc-abc123def456",
                "analyzed_at": "2024-01-15T10:45:00Z",
                "overall_risk": 68,
                "overall_risk_level": "high",
                "total_clauses_analyzed": 24,
                "high_risk_clause_count": 5,
                "medium_risk_clause_count": 8,
                "low_risk_clause_count": 11,
                "category_risks": [],
                "high_risk_clauses": [],
                "summary": "This contract has an overall risk score of 68/100...",
                "citations": [],
                "confidence": 0.87,
                "scoring_breakdown": {}
            }
        }


# === Analysis Request/Response ===

class AnalyzeRequest(BaseModel):
    """Request to analyze a document."""
    include_all_clauses: bool = Field(
        default=False, 
        description="Include all clause risks in response, not just high-risk"
    )
    max_clauses: int | None = Field(
        default=None, 
        ge=1, 
        le=100,
        description="Maximum number of clauses to analyze"
    )


class AnalyzeResponse(BaseModel):
    """Response for document analysis."""
    document_id: str
    status: AnalysisStatusEnum
    risk_report: RiskReportSchema | None = None
    processing_time_seconds: float | None = None
    error_message: str | None = None


# === Status Schemas ===

class DocumentStatusResponse(BaseModel):
    """Response for document status check."""
    document_id: str
    filename: str
    status: AnalysisStatusEnum
    upload_timestamp: datetime
    analysis_started_at: datetime | None = None
    analysis_completed_at: datetime | None = None
    error_message: str | None = None


# === Error Schemas ===

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: dict[str, Any] | None = Field(None, description="Additional error details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid file format. Only PDF files are accepted.",
                "details": {"accepted_formats": ["application/pdf"]}
            }
        }


# === Health Check ===

class HealthCheckResponse(BaseModel):
    """API health check response."""
    status: str = Field(..., description="API status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(..., description="Current server timestamp")
    services: dict[str, str] = Field(..., description="Status of dependent services")
