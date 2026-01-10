# Task #1: Decompose analyze_portfolio() - Implementation Plan

**Date:** 2026-01-09  
**Priority:** Bloccante (8h effort)  
**Status:** ⏳ PLANNED

## Overview

The `analyze_portfolio()` function in main.py is 589 lines long (lines 423-1011), making it:
- **Untestable**: Cannot unit test individual components
- **Unmaintainable**: Hard to understand flow
- **Fragile**: Changes risk breaking unrelated logic
- **Undebuggable**: 589-line stack traces are useless

**Goal:** Decompose into 6-8 focused functions, each <100 lines, single responsibility, independently testable.

## Current Structure Analysis

### Function Statistics
- **Total lines:** 589
- **Sections:** 20 major blocks
- **Complexity:** ~150 cyclomatic complexity
- **Dependencies:** 12 modules imported
- **Returns:** AnalysisResult (structured output)

### Identified Stages

**Stage 1: Data Loading & Validation** (103 lines)
```
Lines 479-582: CONFIG → DOWNLOAD → VALIDATION → INTEGRITY
├─ Parse config (9 lines)
├─ Risk intent validation (15 lines)
├─ Download portfolio data (4 lines)
├─ Download benchmark data (11 lines)
├─ Data validation (15 lines)
├─ Data integrity layer (46 lines)
└─ Survivorship bias check (3 lines)

Output: prices, benchmark_prices, data_integrity, is_provisional
```

**Stage 2: Portfolio Simulation & Metrics** (30 lines)
```
Lines 583-612: SIMULATION → METRICS → RISK CONTRIBUTION
├─ Simulate portfolio equity (3 lines)
├─ Calculate portfolio metrics (2 lines)
├─ Calculate per-asset metrics (9 lines)
├─ Risk contribution (2 lines)
└─ Asset summary DataFrame (14 lines)

Output: equity, port_ret, metrics, asset_df, risk_contrib
```

**Stage 3: Correlation Analysis** (28 lines)
```
Lines 614-641: CORRELATION → SHRINKAGE → DUAL-FRAMEWORK
├─ Raw correlation (1 line)
├─ Shrunk correlation (1 line)
├─ Dual-correlation framework (5 lines)
├─ Correlation assignment (3 lines)
└─ Shrinkage warning logging (18 lines)

Output: corr, corr_raw, shrinkage_delta, dual_corr
```

**Stage 4: Advanced Analysis** (69 lines)
```
Lines 643-710: CONDITIONAL → BENCHMARK → CRISIS → MONTE CARLO → COSTS → VALIDATION
├─ Conditional correlations (4 lines)
├─ Benchmark comparison (15 lines)
├─ Crisis detection (10 lines)
├─ Monte Carlo stress test (7 lines)
├─ Transaction costs (15 lines)
├─ Validation framework (1 line)
└─ Print validation warnings (5 lines)

Output: conditional_corr, benchmark_comparison, crisis_info, stress_test, cost_adjustment
```

**Stage 5: Gate Analysis** (135 lines)
```
Lines 782-916: RISK INTENT → GATE SYSTEM → EXCEPTION HANDLING
├─ Risk intent analysis (21 lines)
├─ Print risk intent (1 line)
├─ Gate system preparation (14 lines)
├─ Gate analysis execution (22 lines)
├─ Exception handling: INCONCLUSIVE (47 lines)
├─ Soft classification (11 lines)
├─ Print gate analysis (1 line)
└─ Propagate to regime_info (17 lines)

Output: risk_analysis, gate_result, soft_class, regime_info
```

**Stage 6: Output & Export** (95 lines)
```
Lines 918-1011: SENIOR ANALYSIS → EXPORT → PLOTS → STRUCTURED OUTPUT
├─ Senior architect analysis (9 lines)
├─ Export data (11 lines)
├─ Plot results (3 lines)
├─ Build structured result (7 lines)
├─ Save JSON (4 lines)
└─ Validation check (5 lines)

Output: analysis_result, PDF, charts, JSON
```

## Proposed Decomposition

### Architecture

```
analyze_portfolio()  [ORCHESTRATOR - 80 lines]
├─ _load_and_validate_data()        [Stage 1 - 90 lines]
├─ _calculate_portfolio_metrics()   [Stage 2 - 45 lines]
├─ _analyze_correlations()          [Stage 3 - 40 lines]
├─ _run_advanced_analysis()         [Stage 4 - 85 lines]
├─ _run_gate_validation()           [Stage 5 - 150 lines]
└─ _generate_output()               [Stage 6 - 100 lines]
```

### Function Signatures

```python
def _load_and_validate_data(
    config: Dict[str, Any]
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict, bool, str]:
    """
    Stage 1: Load and validate all data.
    
    Returns:
        prices: Portfolio price data
        benchmark_prices: Benchmark price data
        data_integrity: Data integrity info
        is_provisional: Whether analysis is provisional
        risk_intent: Validated risk intent
    """

def _calculate_portfolio_metrics(
    prices: pd.DataFrame,
    weights: np.ndarray,
    tickers: List[str],
    rebalance: str,
    risk_free: float,
    var_conf: float,
    data_integrity: Dict
) -> Tuple[pd.Series, pd.Series, Dict, pd.DataFrame, pd.DataFrame]:
    """
    Stage 2: Calculate portfolio and asset-level metrics.
    
    Returns:
        equity: Portfolio equity curve
        port_ret: Portfolio returns
        metrics: Portfolio metrics dict
        asset_df: Asset-level metrics DataFrame
        risk_contrib: Risk contribution DataFrame
    """

def _analyze_correlations(
    simple_ret: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame, float, Any]:
    """
    Stage 3: Calculate correlation matrices with shrinkage.
    
    Returns:
        corr: Shrunk correlation (for calculations)
        corr_raw: Raw correlation (for diagnosis)
        shrinkage_delta: Shrinkage intensity
        dual_corr: Dual-correlation framework object
    """

def _run_advanced_analysis(
    simple_ret: pd.DataFrame,
    port_ret: pd.Series,
    weights: np.ndarray,
    tickers: List[str],
    metrics: Dict,
    prices: pd.DataFrame,
    benchmark_prices: pd.DataFrame,
    rebalance: str
) -> Tuple[Dict, Dict, Dict, Dict, Dict]:
    """
    Stage 4: Run advanced analysis (conditional, benchmark, crisis, costs).
    
    Returns:
        conditional_corr: Conditional correlations
        benchmark_comparison: Benchmark comparison results
        crisis_info: Crisis detection info
        stress_test: Monte Carlo stress test results
        cost_adjustment: Transaction costs & tax drag
    """

def _run_gate_validation(
    risk_intent: str,
    port_ret: pd.Series,
    prices: pd.DataFrame,
    simple_ret: pd.DataFrame,
    weights: np.ndarray,
    tickers: List[str],
    metrics: Dict,
    corr: pd.DataFrame,
    risk_contrib: pd.DataFrame,
    data_integrity: Dict,
    benchmark_comparison: Dict,
    override: Optional[UserAcknowledgment]
) -> Tuple[Dict, Dict, Dict, Dict]:
    """
    Stage 5: Run risk intent analysis and gate system validation.
    
    Raises:
        INCONCLUSIVEVerdictError: If verdict is inconclusive without override
        
    Returns:
        risk_analysis: Risk intent analysis results
        gate_result: Gate system results
        soft_class: Soft classification results
        regime_info: Regime info with gate results
    """

def _generate_output(
    config: Dict,
    equity: pd.Series,
    port_ret: pd.Series,
    prices: pd.DataFrame,
    metrics: Dict,
    risk_contrib: pd.DataFrame,
    asset_df: pd.DataFrame,
    corr: pd.DataFrame,
    tickers: List[str],
    weights: np.ndarray,
    regime_info: Dict,
    gate_result: Dict,
    risk_analysis: Dict
) -> AnalysisResult:
    """
    Stage 6: Generate all output (reports, exports, structured data).
    
    Returns:
        analysis_result: Structured analysis result
    """
```

### Orchestrator Function

```python
@log_performance(logger)
def analyze_portfolio(
    config: Dict[str, Any], 
    override: Optional[UserAcknowledgment] = None
) -> Optional[AnalysisResult]:
    """
    Main portfolio analysis orchestrator.
    
    Coordinates 6 analysis stages:
    1. Load & validate data
    2. Calculate metrics
    3. Analyze correlations
    4. Run advanced analysis
    5. Validate with gate system
    6. Generate output
    
    Args:
        config: Portfolio configuration
        override: Override for INCONCLUSIVE verdicts
        
    Returns:
        AnalysisResult with validation status
        
    Raises:
        INCONCLUSIVEVerdictError: If gate system blocks analysis
        ValueError: Invalid configuration
        RuntimeError: Data download/processing errors
    """
    logger.info("Starting portfolio analysis")
    
    # Stage 1: Data loading (90 lines → 1 call)
    prices, benchmark_prices, data_integrity, is_provisional, risk_intent = \
        _load_and_validate_data(config)
    
    # Stage 2: Metrics calculation (45 lines → 1 call)
    tickers = config["tickers"]
    weights = np.array(config["weights"], dtype=float)
    weights = weights / weights.sum()
    
    equity, port_ret, metrics, asset_df, risk_contrib = \
        _calculate_portfolio_metrics(
            prices, weights, tickers,
            config.get("rebalance"),
            config["risk_free_annual"],
            config.get("var_confidence", 0.95),
            data_integrity
        )
    
    # Stage 3: Correlation analysis (40 lines → 1 call)
    simple_ret = calculate_simple_returns(prices)
    corr, corr_raw, shrinkage_delta, dual_corr = \
        _analyze_correlations(simple_ret)
    
    # Stage 4: Advanced analysis (85 lines → 1 call)
    conditional_corr, benchmark_comparison, crisis_info, stress_test, cost_adjustment = \
        _run_advanced_analysis(
            simple_ret, port_ret, weights, tickers, metrics,
            prices, benchmark_prices, config.get("rebalance")
        )
    
    # Stage 5: Gate validation (150 lines → 1 call)
    risk_analysis, gate_result, soft_class, regime_info = \
        _run_gate_validation(
            risk_intent, port_ret, prices, simple_ret,
            weights, tickers, metrics, corr, risk_contrib,
            data_integrity, benchmark_comparison, override
        )
    
    # Stage 6: Output generation (100 lines → 1 call)
    analysis_result = _generate_output(
        config, equity, port_ret, prices, metrics,
        risk_contrib, asset_df, corr, tickers, weights,
        regime_info, gate_result, risk_analysis
    )
    
    logger.info("Portfolio analysis completed")
    return analysis_result
```

## Benefits

### Testability ✅
```python
# Before: Cannot test data loading separately
analyze_portfolio(config)  # 589 lines execute

# After: Test each stage independently
def test_load_and_validate_data():
    config = {"tickers": ["VT"], "weights": [1.0], ...}
    prices, bench, integrity, provisional, intent = _load_and_validate_data(config)
    assert not prices.empty
    assert integrity['policy'] in ['COMMON_START', 'STAGGERED_ENTRY']
    
def test_calculate_portfolio_metrics():
    # Mock prices DataFrame
    prices = pd.DataFrame({...})
    equity, ret, metrics, assets, risk = _calculate_portfolio_metrics(
        prices, weights=[1.0], tickers=["VT"], ...
    )
    assert metrics['cagr'] > 0
    assert 0 < metrics['sharpe'] < 10
```

### Maintainability ✅
- Each function <150 lines (readable in one screen)
- Single responsibility (easier to modify)
- Clear inputs/outputs (no hidden dependencies)
- Self-documenting (function names describe purpose)

### Debuggability ✅
```python
# Before: 589-line stack trace
File "main.py", line 789, in analyze_portfolio
    gate_result = run_gate_analysis(...)
    
# After: Precise error location
File "main.py", line 423, in analyze_portfolio
    risk_analysis, gate_result, ... = _run_gate_validation(...)
File "main.py", line 854, in _run_gate_validation
    gate_result = run_gate_analysis(...)
```

### Performance Tracking ✅
```python
# Using @log_performance decorator on each stage
2026-01-09 18:00:00 | INFO | main | Starting portfolio analysis
2026-01-09 18:00:05 | INFO | main | Completed _load_and_validate_data in 5.2s
2026-01-09 18:00:07 | INFO | main | Completed _calculate_portfolio_metrics in 1.8s
2026-01-09 18:00:08 | INFO | main | Completed _analyze_correlations in 0.9s
2026-01-09 18:00:10 | INFO | main | Completed _run_advanced_analysis in 2.3s
2026-01-09 18:00:15 | INFO | main | Completed _run_gate_validation in 4.5s
2026-01-09 18:00:16 | INFO | main | Completed _generate_output in 1.1s
2026-01-09 18:00:16 | INFO | main | Portfolio analysis completed
```

## Implementation Steps

### Phase 1: Extract Data Loading (2h)
1. Create `_load_and_validate_data()` function
2. Move lines 479-582 into function
3. Return tuple of outputs
4. Update orchestrator to call function
5. Add unit tests for data loading

### Phase 2: Extract Metrics Calculation (1h)
1. Create `_calculate_portfolio_metrics()` function
2. Move lines 583-612 into function
3. Return tuple of outputs
4. Update orchestrator to call function
5. Add unit tests for metrics

### Phase 3: Extract Correlation Analysis (1h)
1. Create `_analyze_correlations()` function
2. Move lines 614-641 into function
3. Return tuple of outputs
4. Update orchestrator to call function
5. Add unit tests for correlation

### Phase 4: Extract Advanced Analysis (1.5h)
1. Create `_run_advanced_analysis()` function
2. Move lines 643-710 into function
3. Return tuple of outputs
4. Update orchestrator to call function
5. Add unit tests for advanced analysis

### Phase 5: Extract Gate Validation (2h)
1. Create `_run_gate_validation()` function
2. Move lines 782-916 into function
3. Handle exception flow properly
4. Return tuple of outputs
5. Update orchestrator to call function
6. Add unit tests for gate validation

### Phase 6: Extract Output Generation (0.5h)
1. Create `_generate_output()` function
2. Move lines 918-1011 into function
3. Return AnalysisResult
4. Update orchestrator to call function
5. Add integration tests

## Testing Strategy

### Unit Tests (12h - Task #2)
```python
# test_data_loading.py
def test_load_valid_data():
    """Test loading valid portfolio data."""
    
def test_load_missing_ticker():
    """Test error handling for missing tickers."""
    
def test_data_integrity_staggered():
    """Test staggered entry data integrity."""

# test_metrics_calculation.py
def test_calculate_basic_metrics():
    """Test basic portfolio metrics calculation."""
    
def test_calculate_with_rebalancing():
    """Test metrics with rebalancing."""

# test_correlation_analysis.py
def test_shrunk_correlation():
    """Test Ledoit-Wolf shrinkage."""
    
def test_dual_framework():
    """Test dual-correlation framework."""

# test_advanced_analysis.py
def test_crisis_detection():
    """Test crisis period detection."""
    
def test_monte_carlo_stress():
    """Test Monte Carlo stress testing."""

# test_gate_validation.py
def test_gate_pass():
    """Test gate system with passing portfolio."""
    
def test_gate_fail_inconclusive():
    """Test gate system with INCONCLUSIVE verdict."""
    
def test_gate_override():
    """Test override mechanism."""

# test_output_generation.py
def test_structured_output():
    """Test structured output generation."""
    
def test_export_formats():
    """Test export to CSV/Excel/JSON."""
```

### Integration Tests
```python
def test_full_analysis():
    """Test complete analysis pipeline."""
    config = get_test_config()
    result = analyze_portfolio(config)
    assert result.validate_for_production()[0]

def test_analysis_with_override():
    """Test analysis with override."""
    config = get_inconclusive_config()
    override = create_test_override()
    result = analyze_portfolio(config, override=override)
    assert result is not None
```

## Risks & Mitigation

### Risk 1: Breaking Existing Behavior
**Mitigation:**
- Extract functions one at a time
- Run full test suite after each extraction
- Keep original function as reference until all tests pass

### Risk 2: Complex Data Flow
**Mitigation:**
- Document all inputs/outputs clearly
- Use type hints for all parameters
- Add comprehensive docstrings

### Risk 3: Exception Handling
**Mitigation:**
- Preserve all exception raising behavior
- Test error paths explicitly
- Document exception flow in docstrings

## Success Criteria

1. ✅ No function > 150 lines
2. ✅ All 6 stages extracted
3. ✅ Type hints on all functions
4. ✅ Docstrings with examples
5. ✅ Unit tests for each function
6. ✅ Integration tests pass
7. ✅ No regression in analysis results
8. ✅ Performance tracking per stage

## Next Actions

**Priority Order:**
1. ⏳ Extract Phase 1: Data Loading (2h)
2. ⏳ Extract Phase 2: Metrics Calculation (1h)
3. ⏳ Extract Phase 3: Correlation Analysis (1h)
4. ⏳ Extract Phase 4: Advanced Analysis (1.5h)
5. ⏳ Extract Phase 5: Gate Validation (2h)
6. ⏳ Extract Phase 6: Output Generation (0.5h)

**Total Estimated Effort:** 8h

**Dependencies:**
- ✅ Task #3: Logging Framework (COMPLETE)
- ✅ Task #4: Global State Removal (COMPLETE)

**Enables:**
- ⏳ Task #2: Test Coverage → 60% (12h)

## Conclusion

This decomposition will transform a 589-line monolithic function into a well-structured, testable, maintainable architecture. Each component can be independently tested, debugged, and modified without affecting others.

**Current Status:** PLANNED  
**Next Step:** Begin Phase 1 (Extract Data Loading)  
**Estimated Completion:** 8h of focused development work
