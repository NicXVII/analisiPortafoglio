"""
Test Suite for Type Safety (Issue #2 Phase 4)
==============================================

Basic tests to verify dataclass constructors and type consistency.
Run with: python test_models.py
"""

import sys
from datetime import datetime
from typing import List

# Test imports
try:
    from portfolio_engine.models.portfolio import (
        RiskIntentLevel,
        FinalVerdictType,
        PortfolioStructureType,
        BenchmarkCategory,
        RiskIntentSpec,
        DataQuality,
        ComponentRisk,
        IntentGateCheck,
        StructuralGateCheck,
        BenchmarkComparison,
        GateResult
    )
    print("✅ All models imported successfully")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)


def test_enums():
    """Test enum values are accessible."""
    print("\n🧪 Testing Enums...")
    
    # RiskIntentLevel
    assert RiskIntentLevel.CONSERVATIVE == "CONSERVATIVE"
    assert RiskIntentLevel.AGGRESSIVE == "AGGRESSIVE"
    print("  ✅ RiskIntentLevel enum OK")
    
    # FinalVerdictType
    assert FinalVerdictType.STRUCTURALLY_COHERENT_INTENT_MATCH == "STRUCTURALLY_COHERENT_INTENT_MATCH"
    assert FinalVerdictType.INCONCLUSIVE_DATA_FAIL == "INCONCLUSIVE_DATA_FAIL"
    print("  ✅ FinalVerdictType enum OK")
    
    # PortfolioStructureType
    assert PortfolioStructureType.GLOBAL_CORE == "GLOBAL_CORE"
    assert PortfolioStructureType.OPPORTUNISTIC == "OPPORTUNISTIC"
    print("  ✅ PortfolioStructureType enum OK")
    
    # BenchmarkCategory
    assert BenchmarkCategory.SAME_CATEGORY == "SAME_CATEGORY"
    assert BenchmarkCategory.OPPORTUNITY_COST == "OPPORTUNITY_COST"
    print("  ✅ BenchmarkCategory enum OK")


def test_risk_intent_spec():
    """Test RiskIntentSpec dataclass."""
    print("\n🧪 Testing RiskIntentSpec...")
    
    spec = RiskIntentSpec(
        level=RiskIntentLevel.MODERATE,
        beta_range=(0.6, 0.8),
        min_beta_acceptable=0.5,
        beta_fail_threshold=0.4,
        max_dd_expected=-0.15,
        benchmark="BND",
        description="Test spec",
        vol_expected=(0.05, 0.10)
    )
    
    assert spec.level == RiskIntentLevel.MODERATE, f"Level mismatch: {spec.level}"
    assert spec.beta_range == (0.6, 0.8), f"Beta range mismatch: {spec.beta_range}"
    assert spec.is_beta_in_range(0.7), "Beta 0.7 should be in range"
    assert not spec.is_beta_in_range(0.9), "Beta 0.9 should not be in range"
    assert spec.is_beta_acceptable(0.75), "Beta 0.75 should be acceptable"
    assert spec.is_beta_fail(0.3), "Beta 0.3 should be fail"
    
    print("  ✅ RiskIntentSpec OK")


def test_data_quality():
    """Test DataQuality dataclass."""
    print("\n🧪 Testing DataQuality...")
    
    # Good quality
    dq_good = DataQuality(
        nan_ratio=0.05,
        earliest_date=datetime(2020, 1, 1),
        latest_date=datetime(2022, 1, 1),
        trading_days=500,
        overlapping_days=500,
        staggered_entry=False
    )
    assert dq_good.is_pass
    assert not dq_good.is_warning
    print("  ✅ DataQuality PASS case OK")
    
    # Warning case
    dq_warn = DataQuality(
        nan_ratio=0.15,
        earliest_date=datetime(2021, 1, 1),
        latest_date=datetime(2022, 1, 1),
        trading_days=300,
        overlapping_days=300,
        staggered_entry=False
    )
    # nan_ratio 0.15 is still < 0.20, so is_pass is True but is_warning is also True
    assert dq_warn.is_pass  # Changed: 0.15 <= 0.20 is still a pass
    assert dq_warn.is_warning  # But it's in warning zone (0.10-0.20)
    print("  ✅ DataQuality WARNING case OK")


def test_component_risk():
    """Test ComponentRisk dataclass."""
    print("\n🧪 Testing ComponentRisk...")
    
    cr = ComponentRisk(
        ticker="VTI",
        weight=0.60,
        mcr=0.012,
        ccr=0.0072,
        ccr_percent=0.75
    )
    
    assert cr.ticker == "VTI"
    assert cr.weight == 0.60
    assert cr.ccr_percent == 0.75
    assert abs(cr.risk_leverage - 1.25) < 0.01  # 0.75 / 0.60
    print("  ✅ ComponentRisk OK")


def test_intent_gate_check():
    """Test IntentGateCheck dataclass."""
    print("\n🧪 Testing IntentGateCheck...")
    
    spec = RiskIntentSpec(
        level=RiskIntentLevel.GROWTH,
        beta_range=(0.8, 1.2),
        min_beta_acceptable=0.7,
        beta_fail_threshold=0.6,
        max_dd_expected=-0.30,
        benchmark="VT",
        description="Growth portfolio"
    )
    
    gate = IntentGateCheck(
        portfolio_beta=0.95,
        intent_spec=spec,
        beta_window_years=5.0,
        verdict="PASS",
        confidence_score=85,
        beta_state="PASS",
        is_valid=True
    )
    
    assert gate.portfolio_beta == 0.95
    assert gate.verdict == "PASS"
    assert gate.confidence_score == 85
    assert gate.is_pass
    assert not gate.is_fail
    print("  ✅ IntentGateCheck OK")


def test_structural_gate_check():
    """Test StructuralGateCheck dataclass."""
    print("\n🧪 Testing StructuralGateCheck...")
    
    gate = StructuralGateCheck(
        structure_type=PortfolioStructureType.GLOBAL_CORE,
        confidence=0.85,
        max_position=0.40,
        top3_concentration=0.70,
        hhi=0.35,
        effective_positions=5.5,
        verdict="PASS"
    )
    
    assert gate.hhi == 0.35
    assert gate.effective_positions == 5.5
    assert gate.structure_type == PortfolioStructureType.GLOBAL_CORE
    assert gate.is_pass
    print("  ✅ StructuralGateCheck OK")


def test_benchmark_comparison():
    """Test BenchmarkComparison dataclass."""
    print("\n🧪 Testing BenchmarkComparison...")
    
    bench = BenchmarkComparison(
        benchmark_name="VT",
        category=BenchmarkCategory.SAME_CATEGORY,
        portfolio_cagr=0.10,
        benchmark_cagr=0.08,
        excess_return=0.02,
        portfolio_sharpe=0.90,
        benchmark_sharpe=0.75,
        tracking_error=0.03,
        information_ratio=0.67,
        beta=1.05,
        alpha=0.015,
        verdict="PASS"
    )
    
    assert bench.benchmark_name == "VT"
    assert bench.category == BenchmarkCategory.SAME_CATEGORY
    assert bench.excess_return == 0.02
    print("  ✅ BenchmarkComparison OK")


def test_gate_result():
    """Test GateResult dataclass."""
    print("\n🧪 Testing GateResult...")
    
    dq = DataQuality(
        nan_ratio=0.05,
        earliest_date=datetime(2020, 1, 1),
        latest_date=datetime(2022, 1, 1),
        trading_days=500,
        overlapping_days=500,
        staggered_entry=False
    )
    
    spec = RiskIntentSpec(
        level=RiskIntentLevel.GROWTH,
        beta_range=(0.8, 1.2),
        min_beta_acceptable=0.7,
        beta_fail_threshold=0.6,
        max_dd_expected=-0.30,
        benchmark="VT",
        description="Growth portfolio"
    )
    
    intent = IntentGateCheck(
        portfolio_beta=0.95,
        intent_spec=spec,
        beta_window_years=5.0,
        verdict="PASS",
        confidence_score=85,
        beta_state="PASS",
        is_valid=True
    )
    
    structural = StructuralGateCheck(
        structure_type=PortfolioStructureType.GLOBAL_CORE,
        confidence=0.85,
        max_position=0.40,
        top3_concentration=0.70,
        hhi=0.35,
        effective_positions=5.5,
        verdict="PASS"
    )
    
    result = GateResult(
        data_quality=dq,
        intent_check=intent,
        structural_check=structural,
        final_verdict=FinalVerdictType.STRUCTURALLY_COHERENT_INTENT_MATCH,
        verdict_confidence=85
    )
    
    assert result.final_verdict == FinalVerdictType.STRUCTURALLY_COHERENT_INTENT_MATCH
    assert result.verdict_confidence == 85
    assert result.is_intent_misaligned == False
    assert result.is_inconclusive == False
    
    # Test to_dict for backward compatibility
    result_dict = result.to_dict()
    assert isinstance(result_dict, dict)
    assert 'verdict' in result_dict
    assert 'confidence' in result_dict
    print("  ✅ GateResult OK")
    print("  ✅ to_dict() backward compatibility OK")


def test_gate_result_inconclusive():
    """Test GateResult with INCONCLUSIVE verdict."""
    print("\n🧪 Testing GateResult INCONCLUSIVE...")
    
    dq = DataQuality(
        nan_ratio=0.25,
        earliest_date=datetime(2021, 1, 1),
        latest_date=datetime(2022, 1, 1),
        trading_days=200,
        overlapping_days=200,
        staggered_entry=False
    )
    
    spec = RiskIntentSpec(
        level=RiskIntentLevel.GROWTH,
        beta_range=(0.8, 1.2),
        min_beta_acceptable=0.7,
        beta_fail_threshold=0.6,
        max_dd_expected=-0.30,
        benchmark="VT",
        description="Growth portfolio"
    )
    
    intent = IntentGateCheck(
        portfolio_beta=0.95,
        intent_spec=spec,
        beta_window_years=2.0,
        verdict="INCONCLUSIVE",
        confidence_score=40,
        beta_state="INCONCLUSIVE",
        is_valid=False
    )
    
    structural = StructuralGateCheck(
        structure_type=PortfolioStructureType.OPPORTUNISTIC,
        confidence=0.45,
        max_position=0.50,
        top3_concentration=0.85,
        hhi=0.45,
        effective_positions=3.5,
        verdict="BLOCKED"
    )
    
    result = GateResult(
        data_quality=dq,
        intent_check=intent,
        structural_check=structural,
        final_verdict=FinalVerdictType.INCONCLUSIVE_DATA_FAIL,
        verdict_confidence=40
    )
    
    assert result.is_inconclusive == True
    assert result.is_intent_misaligned == False
    print("  ✅ GateResult INCONCLUSIVE detection OK")


def run_all_tests():
    """Run all tests."""
    print("=" * 70)
    print("RUNNING TYPE SAFETY TESTS (Issue #2 Phase 4)")
    print("=" * 70)
    
    try:
        test_enums()
        test_risk_intent_spec()
        test_data_quality()
        test_component_risk()
        test_intent_gate_check()
        test_structural_gate_check()
        test_benchmark_comparison()
        test_gate_result()
        test_gate_result_inconclusive()
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
