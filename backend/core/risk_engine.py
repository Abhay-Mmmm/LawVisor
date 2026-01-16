"""
LawVisor Risk Engine Module
===========================
Calculates deterministic, explainable risk scores for contracts.
Produces clause-level, category-level, and overall contract risk.

Key Features:
- Multi-factor risk calculation
- Weighted scoring by clause importance
- Category aggregation
- Full explainability of scores
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from core.clause_extractor import ExtractedClause
from core.config import RISK_LEVELS
from core.rag_engine import ComplianceAnalysis

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk level categories."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"


@dataclass
class ClauseRisk:
    """Risk assessment for a single clause."""
    clause_id: str
    clause_type: str
    clause_title: str
    clause_text_preview: str
    risk_score: float  # 0-100
    risk_level: RiskLevel
    contributing_factors: list[dict[str, Any]]
    violated_regulations: list[str]
    recommendations: list[str]
    explanation: str
    confidence: float
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "clause_id": self.clause_id,
            "clause_type": self.clause_type,
            "clause_title": self.clause_title,
            "clause_text_preview": self.clause_text_preview,
            "risk_score": round(self.risk_score, 2),
            "risk_level": self.risk_level.value,
            "contributing_factors": self.contributing_factors,
            "violated_regulations": self.violated_regulations,
            "recommendations": self.recommendations,
            "explanation": self.explanation,
            "confidence": round(self.confidence, 2)
        }


@dataclass
class CategoryRisk:
    """Aggregated risk for a clause category."""
    category: str
    category_display: str
    risk_score: float  # 0-100
    risk_level: RiskLevel
    clause_count: int
    high_risk_clauses: int
    top_issues: list[str]
    clauses: list[ClauseRisk]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "category": self.category,
            "category_display": self.category_display,
            "risk_score": round(self.risk_score, 2),
            "risk_level": self.risk_level.value,
            "clause_count": self.clause_count,
            "high_risk_clauses": self.high_risk_clauses,
            "top_issues": self.top_issues,
            "clauses": [c.to_dict() for c in self.clauses]
        }


@dataclass
class ContractRiskReport:
    """Complete risk assessment for a contract."""
    document_id: str
    analyzed_at: datetime
    overall_risk_score: float  # 0-100
    overall_risk_level: RiskLevel
    total_clauses_analyzed: int
    high_risk_clause_count: int
    medium_risk_clause_count: int
    low_risk_clause_count: int
    category_risks: list[CategoryRisk]
    top_risks: list[ClauseRisk]  # Top 5 highest risk clauses
    all_clause_risks: list[ClauseRisk]
    summary: str
    citations: list[dict[str, str]]
    confidence: float
    scoring_breakdown: dict[str, Any]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "document_id": self.document_id,
            "analyzed_at": self.analyzed_at.isoformat(),
            "overall_risk_score": round(self.overall_risk_score, 2),
            "overall_risk_level": self.overall_risk_level.value,
            "total_clauses_analyzed": self.total_clauses_analyzed,
            "high_risk_clause_count": self.high_risk_clause_count,
            "medium_risk_clause_count": self.medium_risk_clause_count,
            "low_risk_clause_count": self.low_risk_clause_count,
            "category_risks": [c.to_dict() for c in self.category_risks],
            "top_risks": [r.to_dict() for r in self.top_risks],
            "all_clause_risks": [c.to_dict() for c in self.all_clause_risks],
            "summary": self.summary,
            "citations": self.citations,
            "confidence": round(self.confidence, 2),
            "scoring_breakdown": self.scoring_breakdown
        }


# Clause type importance weights for risk calculation
CLAUSE_TYPE_WEIGHTS = {
    "data_protection": 1.5,      # Critical for GDPR compliance
    "liability": 1.4,           # High business impact
    "indemnification": 1.4,     # High business impact
    "confidentiality": 1.3,     # Important for IP protection
    "intellectual_property": 1.3,
    "jurisdiction": 1.2,
    "termination": 1.2,
    "dispute_resolution": 1.1,
    "warranties": 1.1,
    "payment_terms": 1.0,
    "force_majeure": 1.0,
    "governing_law": 1.0,
    "amendment": 0.9,
    "assignment": 0.9,
    "severability": 0.8,
    "notices": 0.8,
    "entire_agreement": 0.7,
    "counterparts": 0.5,
    "unknown": 1.0
}

# Category display names
CATEGORY_DISPLAY_NAMES = {
    "data_protection": "Data Protection & Privacy",
    "liability": "Liability & Risk Allocation",
    "indemnification": "Indemnification",
    "confidentiality": "Confidentiality",
    "intellectual_property": "Intellectual Property",
    "jurisdiction": "Jurisdiction & Venue",
    "termination": "Termination Rights",
    "dispute_resolution": "Dispute Resolution",
    "warranties": "Warranties & Representations",
    "payment_terms": "Payment Terms",
    "force_majeure": "Force Majeure",
    "governing_law": "Governing Law",
    "amendment": "Amendment Provisions",
    "assignment": "Assignment Rights",
    "severability": "Severability",
    "notices": "Notices",
    "entire_agreement": "Entire Agreement",
    "counterparts": "Counterparts",
    "unknown": "Other Provisions"
}


class RiskEngine:
    """
    Calculates comprehensive risk scores for legal contracts.
    
    Scoring Methodology:
    1. Base score from compliance analysis (0-100)
    2. Apply clause type weight multiplier
    3. Factor in confidence level
    4. Aggregate by category (weighted average)
    5. Calculate overall score (weighted by category importance)
    
    All calculations are deterministic and explainable.
    """
    
    def __init__(self):
        self.clause_weights = CLAUSE_TYPE_WEIGHTS
        self.category_names = CATEGORY_DISPLAY_NAMES
    
    async def calculate_risk_report(
        self,
        document_id: str,
        clauses: list[ExtractedClause],
        analyses: list[ComplianceAnalysis]
    ) -> ContractRiskReport:
        """
        Calculate comprehensive risk report for a contract.
        
        Args:
            document_id: Unique document identifier
            clauses: Extracted clauses from the document
            analyses: Compliance analyses for each clause
            
        Returns:
            ContractRiskReport with full risk breakdown
        """
        logger.info(f"Calculating risk report for document: {document_id}")
        
        # Step 1: Calculate individual clause risks
        clause_risks = self._calculate_clause_risks(clauses, analyses)
        
        # Step 2: Aggregate by category
        category_risks = self._aggregate_by_category(clause_risks)
        
        # Step 3: Calculate overall contract risk
        overall_score, scoring_breakdown = self._calculate_overall_score(
            clause_risks, 
            category_risks
        )
        overall_level = self._score_to_level(overall_score)
        
        # Step 4: Extract top risks
        top_risks = sorted(
            clause_risks, 
            key=lambda r: r.risk_score, 
            reverse=True
        )[:5]
        
        # Step 5: Count risk levels
        high_risk_count = sum(
            1 for r in clause_risks 
            if r.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]
        )
        medium_risk_count = sum(
            1 for r in clause_risks 
            if r.risk_level == RiskLevel.MEDIUM
        )
        low_risk_count = sum(
            1 for r in clause_risks 
            if r.risk_level in [RiskLevel.LOW, RiskLevel.MINIMAL]
        )
        
        # Step 6: Generate summary
        summary = self._generate_summary(
            overall_score, 
            overall_level, 
            category_risks, 
            top_risks
        )
        
        # Step 7: Collect all citations
        citations = self._collect_citations(analyses)
        
        # Step 8: Calculate overall confidence
        avg_confidence = (
            sum(r.confidence for r in clause_risks) / len(clause_risks)
            if clause_risks else 0
        )
        
        return ContractRiskReport(
            document_id=document_id,
            analyzed_at=datetime.utcnow(),
            overall_risk_score=overall_score,
            overall_risk_level=overall_level,
            total_clauses_analyzed=len(clause_risks),
            high_risk_clause_count=high_risk_count,
            medium_risk_clause_count=medium_risk_count,
            low_risk_clause_count=low_risk_count,
            category_risks=category_risks,
            top_risks=top_risks,
            all_clause_risks=clause_risks,
            summary=summary,
            citations=citations,
            confidence=avg_confidence,
            scoring_breakdown=scoring_breakdown
        )
    
    def _calculate_clause_risks(
        self,
        clauses: list[ExtractedClause],
        analyses: list[ComplianceAnalysis]
    ) -> list[ClauseRisk]:
        """Calculate risk for each individual clause."""
        # Build analysis lookup
        analysis_map = {a.clause_id: a for a in analyses}
        
        clause_risks = []
        for clause in clauses:
            analysis = analysis_map.get(clause.clause_id)
            
            if analysis:
                # Get base risk score from analysis
                base_score = analysis.risk_score
                
                # Apply clause type weight
                weight = self.clause_weights.get(clause.clause_type.value, 1.0)
                weighted_score = min(100, base_score * weight)
                
                # Factor in confidence
                confidence_factor = 0.5 + (analysis.confidence * 0.5)
                final_score = weighted_score * confidence_factor
                
                # Build contributing factors
                contributing_factors = [
                    {
                        "factor": "Base Compliance Score",
                        "value": base_score,
                        "description": "Score from regulatory compliance analysis"
                    },
                    {
                        "factor": "Clause Type Weight",
                        "value": weight,
                        "description": f"Importance weight for {clause.clause_type.value}"
                    },
                    {
                        "factor": "Confidence Factor",
                        "value": confidence_factor,
                        "description": "Adjustment based on analysis confidence"
                    }
                ]
                
                clause_risks.append(ClauseRisk(
                    clause_id=clause.clause_id,
                    clause_type=clause.clause_type.value,
                    clause_title=clause.title,
                    clause_text_preview=clause.raw_text[:300] + "...",
                    risk_score=final_score,
                    risk_level=self._score_to_level(final_score),
                    contributing_factors=contributing_factors,
                    violated_regulations=analysis.violated_regulations,
                    recommendations=analysis.recommendations,
                    explanation=analysis.explanation,
                    confidence=analysis.confidence
                ))
            else:
                # No analysis available - assign medium risk
                clause_risks.append(ClauseRisk(
                    clause_id=clause.clause_id,
                    clause_type=clause.clause_type.value,
                    clause_title=clause.title,
                    clause_text_preview=clause.raw_text[:300] + "...",
                    risk_score=50,
                    risk_level=RiskLevel.MEDIUM,
                    contributing_factors=[
                        {
                            "factor": "Missing Analysis",
                            "value": 50,
                            "description": "Default score - analysis not available"
                        }
                    ],
                    violated_regulations=[],
                    recommendations=["Manual review recommended"],
                    explanation="Compliance analysis not available for this clause.",
                    confidence=0.0
                ))
        
        return clause_risks
    
    def _aggregate_by_category(
        self, 
        clause_risks: list[ClauseRisk]
    ) -> list[CategoryRisk]:
        """Aggregate clause risks by category."""
        # Group clauses by type
        categories: dict[str, list[ClauseRisk]] = {}
        for risk in clause_risks:
            cat = risk.clause_type
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(risk)
        
        # Calculate category-level risks
        category_risks = []
        for category, risks in categories.items():
            # Weighted average score
            total_weight = sum(
                self.clause_weights.get(r.clause_type, 1.0) 
                for r in risks
            )
            weighted_sum = sum(
                r.risk_score * self.clause_weights.get(r.clause_type, 1.0)
                for r in risks
            )
            avg_score = weighted_sum / total_weight if total_weight > 0 else 0
            
            # Count high risk clauses
            high_risk = sum(
                1 for r in risks 
                if r.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]
            )
            
            # Extract top issues
            top_issues = []
            for r in sorted(risks, key=lambda x: x.risk_score, reverse=True)[:3]:
                if r.violated_regulations:
                    top_issues.extend(r.violated_regulations[:2])
            top_issues = list(set(top_issues))[:5]
            
            category_risks.append(CategoryRisk(
                category=category,
                category_display=self.category_names.get(category, category),
                risk_score=avg_score,
                risk_level=self._score_to_level(avg_score),
                clause_count=len(risks),
                high_risk_clauses=high_risk,
                top_issues=top_issues,
                clauses=risks
            ))
        
        # Sort by risk score descending
        category_risks.sort(key=lambda c: c.risk_score, reverse=True)
        
        return category_risks
    
    def _calculate_overall_score(
        self,
        clause_risks: list[ClauseRisk],
        category_risks: list[CategoryRisk]
    ) -> tuple[float, dict[str, Any]]:
        """
        Calculate overall contract risk score.
        
        Uses a multi-factor approach:
        1. Weighted average of category scores (60%)
        2. Maximum clause risk penalty (20%)
        3. High-risk clause density (20%)
        """
        if not clause_risks:
            return 0.0, {}
        
        # Factor 1: Weighted average of all clause scores
        total_weight = sum(
            self.clause_weights.get(r.clause_type, 1.0) 
            for r in clause_risks
        )
        weighted_avg = sum(
            r.risk_score * self.clause_weights.get(r.clause_type, 1.0)
            for r in clause_risks
        ) / total_weight if total_weight > 0 else 0
        
        # Factor 2: Maximum risk penalty
        max_risk = max(r.risk_score for r in clause_risks)
        max_penalty = (max_risk - weighted_avg) * 0.3 if max_risk > weighted_avg else 0
        
        # Factor 3: High-risk density
        high_risk_count = sum(
            1 for r in clause_risks 
            if r.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]
        )
        density = high_risk_count / len(clause_risks) if clause_risks else 0
        density_penalty = density * 20  # Up to 20 points
        
        # Combined score
        overall = weighted_avg * 0.6 + max_penalty + density_penalty
        overall = min(100, max(0, overall))  # Clamp to 0-100
        
        breakdown = {
            "weighted_average": {
                "value": round(weighted_avg, 2),
                "weight": 0.6,
                "contribution": round(weighted_avg * 0.6, 2)
            },
            "max_risk_penalty": {
                "max_clause_score": round(max_risk, 2),
                "penalty": round(max_penalty, 2)
            },
            "high_risk_density": {
                "high_risk_count": high_risk_count,
                "total_clauses": len(clause_risks),
                "density": round(density, 2),
                "penalty": round(density_penalty, 2)
            },
            "formula": "overall = (weighted_avg × 0.6) + max_penalty + density_penalty"
        }
        
        return overall, breakdown
    
    def _score_to_level(self, score: float) -> RiskLevel:
        """Convert numeric score to risk level."""
        if score >= 80:
            return RiskLevel.CRITICAL
        elif score >= 60:
            return RiskLevel.HIGH
        elif score >= 40:
            return RiskLevel.MEDIUM
        elif score >= 20:
            return RiskLevel.LOW
        else:
            return RiskLevel.MINIMAL
    
    def _generate_summary(
        self,
        overall_score: float,
        overall_level: RiskLevel,
        category_risks: list[CategoryRisk],
        top_risks: list[ClauseRisk]
    ) -> str:
        """Generate human-readable summary of risk assessment."""
        # Level descriptions
        level_descriptions = {
            RiskLevel.CRITICAL: "requires immediate attention",
            RiskLevel.HIGH: "contains significant compliance concerns",
            RiskLevel.MEDIUM: "has moderate compliance issues that should be addressed",
            RiskLevel.LOW: "has minor issues that may warrant review",
            RiskLevel.MINIMAL: "appears to be well-structured with minimal compliance concerns"
        }
        
        summary_parts = [
            f"This contract has an overall risk score of {overall_score:.0f}/100 "
            f"({overall_level.value.upper()}) and {level_descriptions[overall_level]}."
        ]
        
        # Add category highlights
        high_risk_categories = [
            c for c in category_risks 
            if c.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]
        ]
        
        if high_risk_categories:
            cat_names = [c.category_display for c in high_risk_categories[:3]]
            summary_parts.append(
                f"Key areas of concern include: {', '.join(cat_names)}."
            )
        
        # Add top violations
        all_violations = []
        for risk in top_risks:
            all_violations.extend(risk.violated_regulations)
        unique_violations = list(set(all_violations))[:3]
        
        if unique_violations:
            summary_parts.append(
                f"Potentially violated regulations: {', '.join(unique_violations)}."
            )
        
        return " ".join(summary_parts)
    
    def _collect_citations(
        self, 
        analyses: list[ComplianceAnalysis]
    ) -> list[dict[str, str]]:
        """Collect all regulatory citations from analyses."""
        citations = []
        seen_ids = set()
        
        for analysis in analyses:
            for reg in analysis.matched_regulations:
                if reg.regulation_id not in seen_ids:
                    seen_ids.add(reg.regulation_id)
                    citations.append({
                        "regulation_id": reg.regulation_id,
                        "title": reg.title,
                        "source_url": reg.source_url,
                        "regulation_type": reg.regulation_type
                    })
        
        return citations
