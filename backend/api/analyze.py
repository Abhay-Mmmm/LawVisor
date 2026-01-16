"""
LawVisor Analyze API
====================
Orchestrates the full document analysis pipeline.
Combines OCR, clause extraction, RAG analysis, and risk scoring.
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from api.upload import get_document_store
from core import (
    ClauseExtractor,
    ContractRiskReport,
    OCRError,
    OCRProcessor,
    RAGEngine,
    RiskEngine,
)
from schemas import (
    AnalysisStatusEnum,
    AnalyzeRequest,
    AnalyzeResponse,
    CategoryRiskSchema,
    CitationSchema,
    ClauseRiskSchema,
    ContributingFactorSchema,
    DocumentStatusResponse,
    ErrorResponse,
    RiskLevelEnum,
    RiskReportSchema,
    ScoringBreakdownSchema,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["Analyze"])


def convert_risk_report_to_schema(report: ContractRiskReport) -> RiskReportSchema:
    """Convert internal risk report to API schema."""
    # Convert clause risks
    high_risk_clauses = [
        ClauseRiskSchema(
            clause_id=r.clause_id,
            clause_type=r.clause_type,
            clause_title=r.clause_title,
            clause_text_preview=r.clause_text_preview[:500],
            risk_score=r.risk_score,
            risk_level=RiskLevelEnum(r.risk_level.value),
            contributing_factors=[
                ContributingFactorSchema(**f) for f in r.contributing_factors
            ],
            violated_regulations=r.violated_regulations,
            recommendations=r.recommendations,
            explanation=r.explanation,
            confidence=r.confidence
        )
        for r in report.top_risks
    ]
    
    # Convert category risks
    category_risks = [
        CategoryRiskSchema(
            category=c.category,
            category_display=c.category_display,
            risk_score=c.risk_score,
            risk_level=RiskLevelEnum(c.risk_level.value),
            clause_count=c.clause_count,
            high_risk_clauses=c.high_risk_clauses,
            top_issues=c.top_issues
        )
        for c in report.category_risks
    ]
    
    # Convert citations
    citations = [
        CitationSchema(**c) for c in report.citations
    ]
    
    # Convert scoring breakdown
    scoring_breakdown = ScoringBreakdownSchema(
        weighted_average=report.scoring_breakdown.get("weighted_average", {}),
        max_risk_penalty=report.scoring_breakdown.get("max_risk_penalty", {}),
        high_risk_density=report.scoring_breakdown.get("high_risk_density", {}),
        formula=report.scoring_breakdown.get("formula", "")
    )
    
    return RiskReportSchema(
        document_id=report.document_id,
        analyzed_at=report.analyzed_at,
        overall_risk=report.overall_risk_score,
        overall_risk_level=RiskLevelEnum(report.overall_risk_level.value),
        total_clauses_analyzed=report.total_clauses_analyzed,
        high_risk_clause_count=report.high_risk_clause_count,
        medium_risk_clause_count=report.medium_risk_clause_count,
        low_risk_clause_count=report.low_risk_clause_count,
        category_risks=category_risks,
        high_risk_clauses=high_risk_clauses,
        summary=report.summary,
        citations=citations,
        confidence=report.confidence,
        scoring_breakdown=scoring_breakdown
    )


async def run_analysis_pipeline(document_id: str, file_path: Path) -> ContractRiskReport:
    """
    Run the complete document analysis pipeline.
    
    Pipeline steps:
    1. OCR / Text Extraction
    2. Clause Extraction & Classification
    3. RAG Compliance Analysis
    4. Risk Scoring
    
    Args:
        document_id: Unique document identifier
        file_path: Path to the PDF file
        
    Returns:
        ContractRiskReport with complete analysis
    """
    logger.info(f"Starting analysis pipeline for {document_id}")
    
    # Step 1: OCR Processing
    logger.info(f"[{document_id}] Step 1: OCR Processing")
    ocr_processor = OCRProcessor()
    document_content = await ocr_processor.process_document(file_path, document_id)
    logger.info(
        f"[{document_id}] OCR complete: {document_content.total_pages} pages, "
        f"confidence: {document_content.overall_confidence:.2f}"
    )
    
    # Step 2: Clause Extraction
    logger.info(f"[{document_id}] Step 2: Clause Extraction")
    clause_extractor = ClauseExtractor()
    extraction_result = await clause_extractor.extract_clauses(document_content)
    logger.info(
        f"[{document_id}] Extracted {extraction_result.total_clauses} clauses"
    )
    
    # Step 3: RAG Compliance Analysis
    logger.info(f"[{document_id}] Step 3: RAG Compliance Analysis")
    rag_engine = RAGEngine()
    compliance_analyses = await rag_engine.analyze_clauses(extraction_result.clauses)
    logger.info(
        f"[{document_id}] Compliance analysis complete for "
        f"{len(compliance_analyses)} clauses"
    )
    
    # Step 4: Risk Scoring
    logger.info(f"[{document_id}] Step 4: Risk Scoring")
    risk_engine = RiskEngine()
    risk_report = await risk_engine.calculate_risk_report(
        document_id,
        extraction_result.clauses,
        compliance_analyses
    )
    logger.info(
        f"[{document_id}] Risk report complete: "
        f"Overall score: {risk_report.overall_risk_score:.1f}"
    )
    
    return risk_report


async def process_document_async(document_id: str):
    """
    Background task to process a document.
    Updates document store with results.
    """
    store = get_document_store()
    
    if document_id not in store:
        logger.error(f"Document {document_id} not found in store")
        return
    
    doc = store[document_id]
    doc["status"] = AnalysisStatusEnum.PROCESSING
    doc["analysis_started_at"] = datetime.utcnow()
    
    try:
        file_path = Path(doc["file_path"])
        
        if not file_path.exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")
        
        # Run the analysis pipeline
        risk_report = await run_analysis_pipeline(document_id, file_path)
        
        # Update store with results
        doc["status"] = AnalysisStatusEnum.COMPLETED
        doc["analysis_completed_at"] = datetime.utcnow()
        doc["risk_report"] = risk_report
        doc["error_message"] = None
        
        logger.info(f"Document {document_id} analysis completed successfully")
        
    except OCRError as e:
        logger.error(f"OCR error for {document_id}: {e}")
        doc["status"] = AnalysisStatusEnum.FAILED
        doc["error_message"] = f"OCR processing failed: {str(e)}"
        
    except Exception as e:
        logger.exception(f"Analysis failed for {document_id}: {e}")
        doc["status"] = AnalysisStatusEnum.FAILED
        doc["error_message"] = f"Analysis failed: {str(e)}"


@router.post(
    "/{document_id}",
    response_model=AnalyzeResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Document not found"},
        409: {"model": ErrorResponse, "description": "Analysis already in progress"},
        500: {"model": ErrorResponse, "description": "Analysis failed"}
    },
    summary="Analyze a document",
    description="""
    Initiate analysis of an uploaded document.
    
    This endpoint starts the analysis pipeline which includes:
    1. **OCR Processing**: Extract text from the PDF (handles both native and scanned)
    2. **Clause Extraction**: Identify and classify legal clauses
    3. **Compliance Analysis**: Check clauses against GDPR and SEC regulations
    4. **Risk Scoring**: Calculate clause-level and overall risk scores
    
    The analysis runs synchronously and returns the complete risk report.
    For large documents, this may take 30-60 seconds.
    """
)
async def analyze_document(
    document_id: str,
    request: AnalyzeRequest | None = None
) -> AnalyzeResponse:
    """
    Analyze an uploaded document and return the risk report.
    """
    store = get_document_store()
    
    # Check if document exists
    if document_id not in store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "DocumentNotFound",
                "message": f"Document with ID '{document_id}' not found.",
                "details": {"document_id": document_id}
            }
        )
    
    doc = store[document_id]
    
    # Check if already processing
    if doc["status"] == AnalysisStatusEnum.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "AnalysisInProgress",
                "message": "Document analysis is already in progress.",
                "details": {
                    "document_id": document_id,
                    "started_at": doc.get("analysis_started_at")
                }
            }
        )
    
    # Check if already completed
    if doc["status"] == AnalysisStatusEnum.COMPLETED and doc.get("risk_report"):
        return AnalyzeResponse(
            document_id=document_id,
            status=AnalysisStatusEnum.COMPLETED,
            risk_report=convert_risk_report_to_schema(doc["risk_report"]),
            processing_time_seconds=None
        )
    
    # Run analysis
    start_time = time.time()
    
    try:
        doc["status"] = AnalysisStatusEnum.PROCESSING
        doc["analysis_started_at"] = datetime.utcnow()
        
        file_path = Path(doc["file_path"])
        
        if not file_path.exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")
        
        # Run the analysis pipeline
        risk_report = await run_analysis_pipeline(document_id, file_path)
        
        # Update store
        doc["status"] = AnalysisStatusEnum.COMPLETED
        doc["analysis_completed_at"] = datetime.utcnow()
        doc["risk_report"] = risk_report
        
        processing_time = time.time() - start_time
        
        return AnalyzeResponse(
            document_id=document_id,
            status=AnalysisStatusEnum.COMPLETED,
            risk_report=convert_risk_report_to_schema(risk_report),
            processing_time_seconds=round(processing_time, 2)
        )
        
    except OCRError as e:
        doc["status"] = AnalysisStatusEnum.FAILED
        doc["error_message"] = str(e)
        
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "OCRError",
                "message": str(e),
                "details": {
                    "document_id": document_id,
                    "suggestion": "Document may be too low quality. Try uploading a higher resolution scan."
                }
            }
        )
        
    except Exception as e:
        logger.exception(f"Analysis failed for {document_id}")
        doc["status"] = AnalysisStatusEnum.FAILED
        doc["error_message"] = str(e)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "AnalysisFailed",
                "message": f"Document analysis failed: {str(e)}",
                "details": {"document_id": document_id}
            }
        )


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Document not found"}
    },
    summary="Get analysis status",
    description="Check the current status of a document analysis."
)
async def get_analysis_status(document_id: str) -> DocumentStatusResponse:
    """Get the current status of document analysis."""
    store = get_document_store()
    
    if document_id not in store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "DocumentNotFound",
                "message": f"Document with ID '{document_id}' not found.",
                "details": {"document_id": document_id}
            }
        )
    
    doc = store[document_id]
    
    return DocumentStatusResponse(
        document_id=doc["document_id"],
        filename=doc["filename"],
        status=doc["status"],
        upload_timestamp=doc["upload_timestamp"],
        analysis_started_at=doc.get("analysis_started_at"),
        analysis_completed_at=doc.get("analysis_completed_at"),
        error_message=doc.get("error_message")
    )
