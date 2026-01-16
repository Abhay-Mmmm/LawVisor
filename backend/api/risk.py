"""
LawVisor Risk API
=================
Direct access to risk data and regulation information.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from api.upload import get_document_store
from core.regulations import get_regulations_fetcher
from schemas import AnalysisStatusEnum, ErrorResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/risk", tags=["Risk"])


@router.get(
    "/{document_id}",
    responses={
        404: {"model": ErrorResponse, "description": "Document not found"},
        400: {"model": ErrorResponse, "description": "Analysis not complete"}
    },
    summary="Get risk report",
    description="Retrieve the full risk report for an analyzed document."
)
async def get_risk_report(document_id: str) -> dict[str, Any]:
    """
    Get the complete risk report for a document.
    
    Returns the full risk breakdown including:
    - Overall risk score and level
    - Category-level risks
    - Individual clause risks
    - Regulatory citations
    - Recommendations
    """
    store = get_document_store()
    
    if document_id not in store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "DocumentNotFound",
                "message": f"Document with ID '{document_id}' not found."
            }
        )
    
    doc = store[document_id]
    
    if doc["status"] != AnalysisStatusEnum.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "AnalysisNotComplete",
                "message": f"Document analysis is not complete. Status: {doc['status'].value}",
                "details": {
                    "current_status": doc["status"].value,
                    "error_message": doc.get("error_message")
                }
            }
        )
    
    risk_report = doc.get("risk_report")
    
    if not risk_report:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "ReportNotFound",
                "message": "Risk report data not found despite completed status."
            }
        )
    
    return risk_report.to_dict()


@router.get(
    "/{document_id}/summary",
    responses={
        404: {"model": ErrorResponse, "description": "Document not found"}
    },
    summary="Get risk summary",
    description="Get a condensed summary of the risk assessment."
)
async def get_risk_summary(document_id: str) -> dict[str, Any]:
    """Get a condensed risk summary."""
    store = get_document_store()
    
    if document_id not in store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "DocumentNotFound",
                "message": f"Document with ID '{document_id}' not found."
            }
        )
    
    doc = store[document_id]
    
    if doc["status"] != AnalysisStatusEnum.COMPLETED or not doc.get("risk_report"):
        return {
            "document_id": document_id,
            "status": doc["status"].value,
            "summary": None,
            "message": "Analysis not complete"
        }
    
    report = doc["risk_report"]
    
    return {
        "document_id": document_id,
        "overall_risk_score": round(report.overall_risk_score, 1),
        "overall_risk_level": report.overall_risk_level.value,
        "total_clauses": report.total_clauses_analyzed,
        "high_risk_clauses": report.high_risk_clause_count,
        "summary": report.summary,
        "top_violations": [
            r.violated_regulations[0] 
            for r in report.top_risks 
            if r.violated_regulations
        ][:5]
    }


@router.get(
    "/{document_id}/clauses/{clause_id}",
    responses={
        404: {"model": ErrorResponse, "description": "Document or clause not found"}
    },
    summary="Get clause risk details",
    description="Get detailed risk information for a specific clause."
)
async def get_clause_risk(document_id: str, clause_id: str) -> dict[str, Any]:
    """Get detailed risk information for a specific clause."""
    store = get_document_store()
    
    if document_id not in store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "DocumentNotFound",
                "message": f"Document with ID '{document_id}' not found."
            }
        )
    
    doc = store[document_id]
    
    if not doc.get("risk_report"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "AnalysisNotComplete",
                "message": "Document analysis is not complete."
            }
        )
    
    report = doc["risk_report"]
    
    # Find the clause
    for clause_risk in report.all_clause_risks:
        if clause_risk.clause_id == clause_id:
            return clause_risk.to_dict()
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "error": "ClauseNotFound",
            "message": f"Clause with ID '{clause_id}' not found in document."
        }
    )


# === Regulations Endpoints ===

@router.get(
    "/regulations/gdpr/{article_number}",
    summary="Get GDPR article",
    description="Fetch a specific GDPR article and its requirements."
)
async def get_gdpr_article(article_number: str) -> dict[str, Any]:
    """Fetch a specific GDPR article."""
    fetcher = get_regulations_fetcher()
    article = await fetcher.fetch_gdpr_article(article_number)
    
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "ArticleNotFound",
                "message": f"GDPR Article {article_number} not found."
            }
        )
    
    return article.to_dict()


@router.get(
    "/regulations/sec/{regulation_id}",
    summary="Get SEC regulation",
    description="Fetch a specific SEC regulation and its requirements."
)
async def get_sec_regulation(regulation_id: str) -> dict[str, Any]:
    """Fetch a specific SEC regulation."""
    fetcher = get_regulations_fetcher()
    regulation = await fetcher.fetch_sec_regulation(regulation_id)
    
    if not regulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "RegulationNotFound",
                "message": f"SEC Regulation {regulation_id} not found."
            }
        )
    
    return regulation.to_dict()


@router.get(
    "/regulations",
    summary="List available regulations",
    description="Get a list of all available regulations in the system."
)
async def list_regulations() -> dict[str, Any]:
    """List all available regulations."""
    fetcher = get_regulations_fetcher()
    
    gdpr_set = await fetcher.fetch_all_gdpr_articles()
    sec_set = await fetcher.fetch_all_sec_regulations()
    
    return {
        "gdpr": {
            "name": gdpr_set.name,
            "version": gdpr_set.version,
            "article_count": len(gdpr_set.articles),
            "articles": [
                {
                    "article_number": a.article_number,
                    "title": a.title,
                    "regulation_id": a.regulation_id
                }
                for a in gdpr_set.articles
            ]
        },
        "sec": {
            "name": sec_set.name,
            "version": sec_set.version,
            "regulation_count": len(sec_set.articles),
            "regulations": [
                {
                    "regulation_id": a.regulation_id,
                    "article_number": a.article_number,
                    "title": a.title
                }
                for a in sec_set.articles
            ]
        }
    }
