"""
Test Suite for Structured Output (Issue #3)
============================================

Tests AnalysisResult, MetricsSnapshot, and JSON serialization.
Run with: python test_structured_output.py
"""

import sys
import json
from datetime import datetime
from typing import List

# Test imports
try:
    from portfolio_engine.models.portfolio import (
        AnalysisResult,
        MetricsSnapshot,
        PrescriptiveAction,
        FinalVerdictType,
        PortfolioStructureType
    )
    print("✅ All models imported successfully")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)


def test_metrics_snapshot():
    """Test MetricsSnapshot creation and to_dict()."""
    print("\n🧪 Testing MetricsSnapshot...")
    
    metrics = MetricsSnapshot(
        cagr=0.08,
        sharpe=0.75,
        sortino=0.90,
        max_drawdown=-0.25,
        volatility=0.15,
        var_95=-0.03,
        cvar_95=-0.05,
        cagr_ci_lower=0.05,
        cagr_ci_upper=0.11,
        calmar_ratio=0.32
    )
    
    assert metrics.cagr == 0.08
    assert metrics.sharpe == 0.75
    assert metrics.max_drawdown == -0.25
    
    # Test to_dict
    metrics_dict = metrics.to_dict()
    assert isinstance(metrics_dict, dict)
    assert 'cagr' in metrics_dict
    assert 'sharpe' in metrics_dict
    assert metrics_dict['cagr'] == 0.08
    
    print("  ✅ MetricsSnapshot OK")
    print("  ✅ to_dict() OK")


def test_prescriptive_action():
    """Test PrescriptiveAction creation."""
    print("\n🧪 Testing PrescriptiveAction...")
    
    action = PrescriptiveAction(
        issue_code="INTENT_MISMATCH",
        priority="HIGH",
        confidence=0.85,
        description="Portfolio beta too low for declared GROWTH intent",
        actions=[
            "Increase equity allocation",
            "Add high-beta growth funds"
        ],
        blockers=["Current structure OK"],
        data_quality_impact="NONE"
    )
    
    assert action.issue_code == "INTENT_MISMATCH"
    assert action.priority == "HIGH"
    assert action.confidence == 0.85
    assert len(action.actions) == 2
    
    # Test to_dict
    action_dict = action.to_dict()
    assert isinstance(action_dict, dict)
    assert action_dict['issue_code'] == "INTENT_MISMATCH"
    assert action_dict['priority'] == "HIGH"
    
    print("  ✅ PrescriptiveAction OK")
    print("  ✅ to_dict() OK")


def test_analysis_result_basic():
    """Test AnalysisResult creation."""
    print("\n🧪 Testing AnalysisResult (basic)...")
    
    metrics = MetricsSnapshot(
        cagr=0.08,
        sharpe=0.75,
        sortino=0.90,
        max_drawdown=-0.25,
        volatility=0.15,
        var_95=-0.03,
        cvar_95=-0.05
    )
    
    action = PrescriptiveAction(
        issue_code="TEST",
        priority="LOW",
        confidence=0.5,
        description="Test action",
        actions=["Test"]
    )
    
    result = AnalysisResult(
        verdict=FinalVerdictType.STRUCTURALLY_COHERENT_INTENT_MATCH,
        verdict_message="Portfolio is structurally coherent",
        verdict_confidence=85,
        risk_intent="GROWTH",
        structure_type=PortfolioStructureType.GLOBAL_CORE,
        portfolio_composition={"VTI": 0.60, "VXUS": 0.40},
        metrics=metrics,
        is_actionable=True,
        data_quality_issues=[],
        quality_score=90,
        prescriptive_actions=[action],
        allowed_actions=["Portfolio restructuring"],
        prohibited_actions=[],
        analysis_timestamp=datetime.now()
    )
    
    assert result.verdict == FinalVerdictType.STRUCTURALLY_COHERENT_INTENT_MATCH
    assert result.verdict_confidence == 85
    assert result.risk_intent == "GROWTH"
    assert result.is_actionable == True
    assert result.quality_score == 90
    
    print("  ✅ AnalysisResult creation OK")


def test_analysis_result_methods():
    """Test AnalysisResult helper methods."""
    print("\n🧪 Testing AnalysisResult methods...")
    
    metrics = MetricsSnapshot(
        cagr=0.08,
        sharpe=0.75,
        sortino=0.90,
        max_drawdown=-0.25,
        volatility=0.15,
        var_95=-0.03,
        cvar_95=-0.05
    )
    
    # Test PASS verdict
    result_pass = AnalysisResult(
        verdict=FinalVerdictType.STRUCTURALLY_COHERENT_INTENT_MATCH,
        verdict_message="Pass",
        verdict_confidence=85,
        risk_intent="GROWTH",
        structure_type=PortfolioStructureType.GLOBAL_CORE,
        portfolio_composition={"VTI": 1.0},
        metrics=metrics,
        is_actionable=True,
        data_quality_issues=[],
        quality_score=90,
        prescriptive_actions=[],
        allowed_actions=[],
        prohibited_actions=[],
        analysis_timestamp=datetime.now()
    )
    
    assert result_pass.is_pass() == True
    assert result_pass.is_fail() == False
    assert result_pass.is_inconclusive() == False
    print("  ✅ is_pass() OK")
    
    # Test FAIL verdict
    result_fail = AnalysisResult(
        verdict=FinalVerdictType.STRUCTURALLY_FRAGILE,
        verdict_message="Fail",
        verdict_confidence=85,
        risk_intent="GROWTH",
        structure_type=PortfolioStructureType.OPPORTUNISTIC,
        portfolio_composition={"VTI": 1.0},
        metrics=metrics,
        is_actionable=True,
        data_quality_issues=[],
        quality_score=50,
        prescriptive_actions=[],
        allowed_actions=[],
        prohibited_actions=[],
        analysis_timestamp=datetime.now()
    )
    
    assert result_fail.is_pass() == False
    assert result_fail.is_fail() == True
    assert result_fail.is_inconclusive() == False
    print("  ✅ is_fail() OK")
    
    # Test INCONCLUSIVE verdict
    result_inconcl = AnalysisResult(
        verdict=FinalVerdictType.INCONCLUSIVE_DATA_FAIL,
        verdict_message="Inconclusive",
        verdict_confidence=40,
        risk_intent="GROWTH",
        structure_type=PortfolioStructureType.GLOBAL_CORE,
        portfolio_composition={"VTI": 1.0},
        metrics=metrics,
        is_actionable=False,
        data_quality_issues=["High NaN ratio"],
        quality_score=30,
        prescriptive_actions=[],
        allowed_actions=[],
        prohibited_actions=["Portfolio restructuring"],
        analysis_timestamp=datetime.now()
    )
    
    assert result_inconcl.is_pass() == False
    assert result_inconcl.is_fail() == False
    assert result_inconcl.is_inconclusive() == True
    print("  ✅ is_inconclusive() OK")


def test_validate_for_production():
    """Test validate_for_production() method."""
    print("\n🧪 Testing validate_for_production()...")
    
    metrics = MetricsSnapshot(
        cagr=0.08,
        sharpe=0.75,
        sortino=0.90,
        max_drawdown=-0.25,
        volatility=0.15,
        var_95=-0.03,
        cvar_95=-0.05
    )
    
    # Valid result
    result_valid = AnalysisResult(
        verdict=FinalVerdictType.STRUCTURALLY_COHERENT_INTENT_MATCH,
        verdict_message="Pass",
        verdict_confidence=85,
        risk_intent="GROWTH",
        structure_type=PortfolioStructureType.GLOBAL_CORE,
        portfolio_composition={"VTI": 1.0},
        metrics=metrics,
        is_actionable=True,
        data_quality_issues=[],
        quality_score=90,
        prescriptive_actions=[],
        allowed_actions=["Portfolio restructuring"],
        prohibited_actions=[],
        analysis_timestamp=datetime.now()
    )
    
    is_valid, issues = result_valid.validate_for_production()
    assert is_valid == True
    assert len(issues) == 0
    print("  ✅ PASS case validates OK")
    
    # INCONCLUSIVE result
    result_inconcl = AnalysisResult(
        verdict=FinalVerdictType.INCONCLUSIVE_DATA_FAIL,
        verdict_message="Inconclusive",
        verdict_confidence=40,
        risk_intent="GROWTH",
        structure_type=PortfolioStructureType.GLOBAL_CORE,
        portfolio_composition={"VTI": 1.0},
        metrics=metrics,
        is_actionable=False,
        data_quality_issues=["High NaN ratio"],
        quality_score=30,
        prescriptive_actions=[],
        allowed_actions=[],
        prohibited_actions=["Portfolio restructuring"],
        analysis_timestamp=datetime.now()
    )
    
    is_valid, issues = result_inconcl.validate_for_production()
    assert is_valid == False
    assert len(issues) > 0
    assert any("INCONCLUSIVE" in issue for issue in issues)
    print("  ✅ INCONCLUSIVE case blocks production OK")
    
    # Low quality result
    result_low_quality = AnalysisResult(
        verdict=FinalVerdictType.STRUCTURALLY_COHERENT_INTENT_MATCH,
        verdict_message="Pass but low quality",
        verdict_confidence=45,
        risk_intent="GROWTH",
        structure_type=PortfolioStructureType.GLOBAL_CORE,
        portfolio_composition={"VTI": 1.0},
        metrics=metrics,
        is_actionable=True,
        data_quality_issues=["Issue1", "Issue2", "Issue3"],
        quality_score=35,
        prescriptive_actions=[],
        allowed_actions=[],
        prohibited_actions=[],
        analysis_timestamp=datetime.now()
    )
    
    is_valid, issues = result_low_quality.validate_for_production()
    assert is_valid == False
    assert len(issues) >= 2  # Quality score + data issues
    print("  ✅ Low quality case blocks production OK")


def test_json_serialization():
    """Test JSON serialization."""
    print("\n🧪 Testing JSON serialization...")
    
    metrics = MetricsSnapshot(
        cagr=0.08,
        sharpe=0.75,
        sortino=0.90,
        max_drawdown=-0.25,
        volatility=0.15,
        var_95=-0.03,
        cvar_95=-0.05
    )
    
    action = PrescriptiveAction(
        issue_code="TEST",
        priority="MEDIUM",
        confidence=0.75,
        description="Test action",
        actions=["Action 1", "Action 2"]
    )
    
    result = AnalysisResult(
        verdict=FinalVerdictType.STRUCTURALLY_COHERENT_INTENT_MATCH,
        verdict_message="Portfolio OK",
        verdict_confidence=85,
        risk_intent="GROWTH",
        structure_type=PortfolioStructureType.GLOBAL_CORE,
        portfolio_composition={"VTI": 0.60, "VXUS": 0.40},
        metrics=metrics,
        is_actionable=True,
        data_quality_issues=[],
        quality_score=90,
        prescriptive_actions=[action],
        allowed_actions=["Portfolio restructuring"],
        prohibited_actions=[],
        analysis_timestamp=datetime.now()
    )
    
    # Test to_dict
    result_dict = result.to_dict()
    assert isinstance(result_dict, dict)
    assert 'verdict' in result_dict
    assert 'portfolio' in result_dict
    assert 'metrics' in result_dict
    assert result_dict['verdict']['type'] == 'STRUCTURALLY_COHERENT_INTENT_MATCH'
    print("  ✅ to_dict() OK")
    
    # Test to_json
    result_json = result.to_json()
    assert isinstance(result_json, str)
    
    # Parse JSON to verify it's valid
    parsed = json.loads(result_json)
    assert parsed['verdict']['type'] == 'STRUCTURALLY_COHERENT_INTENT_MATCH'
    assert parsed['portfolio']['risk_intent'] == 'GROWTH'
    assert parsed['quality']['score'] == 90
    print("  ✅ to_json() OK")
    print("  ✅ JSON is valid and parseable")


def test_str_representation():
    """Test __str__ method."""
    print("\n🧪 Testing __str__ representation...")
    
    metrics = MetricsSnapshot(
        cagr=0.08,
        sharpe=0.75,
        sortino=0.90,
        max_drawdown=-0.25,
        volatility=0.15,
        var_95=-0.03,
        cvar_95=-0.05
    )
    
    result = AnalysisResult(
        verdict=FinalVerdictType.STRUCTURALLY_COHERENT_INTENT_MATCH,
        verdict_message="Pass",
        verdict_confidence=85,
        risk_intent="GROWTH",
        structure_type=PortfolioStructureType.GLOBAL_CORE,
        portfolio_composition={"VTI": 1.0},
        metrics=metrics,
        is_actionable=True,
        data_quality_issues=[],
        quality_score=90,
        prescriptive_actions=[],
        allowed_actions=[],
        prohibited_actions=[],
        analysis_timestamp=datetime.now()
    )
    
    str_repr = str(result)
    assert isinstance(str_repr, str)
    assert "AnalysisResult" in str_repr
    assert "quality_score=90" in str_repr
    assert "CAGR=" in str_repr
    print("  ✅ __str__ representation OK")


def run_all_tests():
    """Run all structured output tests."""
    print("=" * 70)
    print("RUNNING STRUCTURED OUTPUT TESTS (Issue #3)")
    print("=" * 70)
    
    try:
        test_metrics_snapshot()
        test_prescriptive_action()
        test_analysis_result_basic()
        test_analysis_result_methods()
        test_validate_for_production()
        test_json_serialization()
        test_str_representation()
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED - Structured Output Implementation OK")
        print("=" * 70)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
