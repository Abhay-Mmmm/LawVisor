"""
Tests for the RiskEngine module.
"""
import pytest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestRiskScoreCalculation:
    """Tests for risk score calculation logic."""
    
    def test_risk_score_range(self):
        """Test that risk scores are within 0-100 range."""
        # This would test the actual RiskEngine
        # For now, test the concept
        risk_scores = [0, 25, 50, 75, 100]
        
        for score in risk_scores:
            assert 0 <= score <= 100
    
    def test_risk_level_mapping(self):
        """Test risk level to score mapping."""
        from core.config import RISK_LEVELS
        
        # Verify risk levels are defined correctly
        assert "low" in RISK_LEVELS
        assert "medium" in RISK_LEVELS
        assert "high" in RISK_LEVELS
        assert "critical" in RISK_LEVELS
        
        # Verify thresholds are in order
        assert RISK_LEVELS["low"]["max"] < RISK_LEVELS["medium"]["max"]
        assert RISK_LEVELS["medium"]["max"] < RISK_LEVELS["high"]["max"]
    
    def test_clause_type_weights(self):
        """Test that clause type weights are properly defined."""
        from core.risk_engine import RiskEngine
        
        engine = RiskEngine()
        weights = engine.CLAUSE_TYPE_WEIGHTS
        
        # Verify weights exist
        assert len(weights) > 0
        
        # Verify all weights are positive
        for clause_type, weight in weights.items():
            assert weight > 0, f"Weight for {clause_type} should be positive"
            assert weight <= 2.0, f"Weight for {clause_type} should not exceed 2.0"
    
    def test_weighted_average_calculation(self):
        """Test weighted average risk calculation."""
        # Sample data
        clause_risks = [
            {"type": "data_protection", "risk": 60},
            {"type": "liability", "risk": 80},
            {"type": "general", "risk": 40}
        ]
        
        weights = {
            "data_protection": 1.5,
            "liability": 1.8,
            "general": 1.0
        }
        
        # Calculate weighted average
        total_weighted_risk = sum(
            c["risk"] * weights.get(c["type"], 1.0)
            for c in clause_risks
        )
        total_weight = sum(
            weights.get(c["type"], 1.0)
            for c in clause_risks
        )
        
        weighted_avg = total_weighted_risk / total_weight
        
        # Verify calculation
        expected = (60 * 1.5 + 80 * 1.8 + 40 * 1.0) / (1.5 + 1.8 + 1.0)
        assert abs(weighted_avg - expected) < 0.01


class TestRiskLevelClassification:
    """Tests for risk level classification."""
    
    @pytest.mark.parametrize("score,expected_level", [
        (0, "minimal"),
        (20, "low"),
        (30, "low"),
        (50, "medium"),
        (60, "high"),
        (70, "high"),
        (80, "critical"),
        (100, "critical"),
    ])
    def test_score_to_level_mapping(self, score, expected_level):
        """Test that scores map to correct risk levels."""
        from core.risk_engine import RiskEngine

        engine = RiskEngine()
        level = engine._score_to_level(score)

        assert level == expected_level


class TestRiskReportGeneration:
    """Tests for risk report generation."""
    
    def test_report_structure(self, sample_risk_report):
        """Test that risk report has required fields."""
        required_fields = [
            "document_id",
            "overall_risk",
            "overall_risk_level",
            "total_clauses_analyzed",
            "high_risk_clauses",
            "category_risks",
            "citations",
            "scoring_explanation"
        ]
        
        for field in required_fields:
            assert field in sample_risk_report
    
    def test_high_risk_clauses_identified(self, sample_risk_report):
        """Test that high risk clauses are properly identified."""
        high_risk = sample_risk_report["high_risk_clauses"]
        
        assert isinstance(high_risk, list)
        for clause in high_risk:
            assert clause["risk_level"] in ["high", "critical"]
            assert clause["risk_score"] >= 60
    
    def test_category_risks_aggregated(self, sample_risk_report):
        """Test that risks are aggregated by category."""
        category_risks = sample_risk_report["category_risks"]
        
        assert isinstance(category_risks, dict)
        for category, data in category_risks.items():
            assert "risk_score" in data
            assert "clause_count" in data
            assert data["clause_count"] > 0
    
    def test_scoring_explanation_transparent(self, sample_risk_report):
        """Test that scoring explanation is transparent."""
        explanation = sample_risk_report["scoring_explanation"]
        
        required_components = [
            "base_weighted_score",
            "high_risk_penalty",
            "density_adjustment",
            "final_score"
        ]
        
        for component in required_components:
            assert component in explanation


class TestEdgeCases:
    """Tests for edge cases in risk calculation."""

    def test_empty_clauses_list(self):
        """Test handling of empty clauses list."""
        import asyncio
        from core.risk_engine import RiskEngine

        engine = RiskEngine()
        result = asyncio.run(engine.calculate_risk_report(
            document_id="test-doc",
            clauses=[],
            analyses=[]
        ))

        assert result.overall_risk_score == 0
        assert result.total_clauses_analyzed == 0

    def test_all_high_risk_clauses(self):
        """Test handling when all clauses are high risk."""
        import asyncio
        from core.risk_engine import RiskEngine
        from core.clause_extractor import ExtractedClause, ClauseType
        from core.rag_engine import ComplianceAnalysis

        engine = RiskEngine()

        clauses = [
            ExtractedClause(
                clause_id=f"c{i}",
                clause_type=ClauseType.LIABILITY,
                title="Limitation of Liability",
                raw_text="Broad liability limitation clause with no cap.",
                normalized_text="broad liability limitation clause with no cap",
                page_number=1,
                start_position=0,
                end_position=50,
                confidence=0.9,
                sub_clauses=[],
                metadata={}
            )
            for i in range(5)
        ]

        analyses = [
            ComplianceAnalysis(
                clause_id=f"c{i}",
                clause_type="liability",
                clause_text="Broad liability limitation clause with no cap.",
                is_compliant=False,
                risk_level="high",
                risk_score=85.0,
                violated_regulations=["GDPR Article 82"],
                matched_regulations=[],
                explanation="Unlimited liability exposure identified.",
                reasoning_chain=["Clause removes all liability caps."],
                recommendations=["Introduce a liability cap."],
                confidence=0.9
            )
            for i in range(5)
        ]

        result = asyncio.run(engine.calculate_risk_report(
            document_id="test-doc",
            clauses=clauses,
            analyses=analyses
        ))

        assert result.overall_risk_score >= 70
        assert result.overall_risk_level in ["high", "critical"]

    def test_all_low_risk_clauses(self):
        """Test handling when all clauses are low risk."""
        import asyncio
        from core.risk_engine import RiskEngine
        from core.clause_extractor import ExtractedClause, ClauseType
        from core.rag_engine import ComplianceAnalysis

        engine = RiskEngine()

        clauses = [
            ExtractedClause(
                clause_id=f"c{i}",
                clause_type=ClauseType.COUNTERPARTS,
                title="Counterparts",
                raw_text="This agreement may be executed in counterparts.",
                normalized_text="this agreement may be executed in counterparts",
                page_number=1,
                start_position=0,
                end_position=50,
                confidence=0.9,
                sub_clauses=[],
                metadata={}
            )
            for i in range(5)
        ]

        analyses = [
            ComplianceAnalysis(
                clause_id=f"c{i}",
                clause_type="counterparts",
                clause_text="This agreement may be executed in counterparts.",
                is_compliant=True,
                risk_level="minimal",
                risk_score=10.0,
                violated_regulations=[],
                matched_regulations=[],
                explanation="Standard boilerplate, fully compliant.",
                reasoning_chain=["No regulatory issues identified."],
                recommendations=[],
                confidence=0.9
            )
            for i in range(5)
        ]

        result = asyncio.run(engine.calculate_risk_report(
            document_id="test-doc",
            clauses=clauses,
            analyses=analyses
        ))

        assert result.overall_risk_score <= 30
        assert result.overall_risk_level in ["low", "minimal"]
