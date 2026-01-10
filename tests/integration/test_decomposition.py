"""
Unit Tests for Decomposed analyze_portfolio() Functions
=======================================================
Tests for Stage 1, 2, and 3 extraction.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from portfolio_engine.core.main_legacy import _load_and_validate_data, _calculate_portfolio_metrics, _analyze_correlations
from portfolio_engine.config.user_config import get_config


class TestStage1DataLoading:
    """Test Stage 1: Data Loading & Validation"""
    
    def test_load_and_validate_data_basic(self):
        """Test basic data loading functionality."""
        config = get_config()
        
        # Execute
        prices, benchmark_prices, data_integrity, is_provisional, risk_intent = \
            _load_and_validate_data(config)
        
        # Assertions
        assert isinstance(prices, pd.DataFrame), "prices should be DataFrame"
        assert not prices.empty, "prices should not be empty"
        assert isinstance(benchmark_prices, pd.DataFrame), "benchmark_prices should be DataFrame"
        assert isinstance(data_integrity, dict), "data_integrity should be dict"
        assert isinstance(is_provisional, bool), "is_provisional should be bool"
        assert isinstance(risk_intent, str), "risk_intent should be string"
        assert risk_intent in ['CONSERVATIVE', 'MODERATE', 'GROWTH', 'AGGRESSIVE'], \
            "risk_intent should be valid value"
    
    def test_data_integrity_policy(self):
        """Test that data integrity policy is set correctly."""
        config = get_config()
        
        prices, benchmark_prices, data_integrity, is_provisional, risk_intent = \
            _load_and_validate_data(config)
        
        assert 'policy' in data_integrity, "policy should be in data_integrity"
        assert data_integrity['policy'] in ['COMMON_START', 'STAGGERED_ENTRY'], \
            "policy should be valid value"
    
    def test_tickers_present_in_prices(self):
        """Test that all tickers are present in loaded data."""
        config = get_config()
        
        prices, benchmark_prices, data_integrity, is_provisional, risk_intent = \
            _load_and_validate_data(config)
        
        for ticker in config['tickers']:
            assert ticker in prices.columns, f"Ticker {ticker} should be in prices"
    
    def test_benchmark_tickers_loaded(self):
        """Test that benchmark tickers are loaded."""
        config = get_config()
        
        prices, benchmark_prices, data_integrity, is_provisional, risk_intent = \
            _load_and_validate_data(config)
        
        # At least one benchmark should be loaded
        assert len(benchmark_prices.columns) > 0, "At least one benchmark should be loaded"
        
        # VT, SPY, or BND should be present
        benchmark_tickers = ['VT', 'SPY', 'BND']
        found_benchmarks = [t for t in benchmark_tickers if t in benchmark_prices.columns or t in prices.columns]
        assert len(found_benchmarks) > 0, "At least one benchmark ticker should be present"


class TestStage2MetricsCalculation:
    """Test Stage 2: Portfolio Metrics Calculation"""
    
    def test_calculate_portfolio_metrics_basic(self):
        """Test basic portfolio metrics calculation."""
        config = get_config()
        
        # Load data first
        prices, _, data_integrity, _, _ = _load_and_validate_data(config)
        
        # Prepare inputs
        tickers = config['tickers']
        weights = np.array(config['weights'], dtype=float)
        weights = weights / weights.sum()
        
        # Execute
        equity, port_ret, metrics, asset_df, risk_contrib, conditional_ccr = \
            _calculate_portfolio_metrics(
                prices, weights, tickers,
                config.get('rebalance'),
                config['risk_free_annual'],
                config.get('var_confidence', 0.95),
                data_integrity
            )
        
        # Assertions
        assert isinstance(equity, pd.Series), "equity should be Series"
        assert isinstance(port_ret, pd.Series), "port_ret should be Series"
        assert isinstance(metrics, dict), "metrics should be dict"
        assert isinstance(asset_df, pd.DataFrame), "asset_df should be DataFrame"
        assert isinstance(risk_contrib, pd.DataFrame), "risk_contrib should be DataFrame"
        assert isinstance(conditional_ccr, dict), "conditional_ccr should be dict"
    
    def test_metrics_keys_present(self):
        """Test that all expected metric keys are present."""
        config = get_config()
        prices, _, data_integrity, _, _ = _load_and_validate_data(config)
        
        tickers = config['tickers']
        weights = np.array(config['weights'], dtype=float)
        weights = weights / weights.sum()
        
        equity, port_ret, metrics, asset_df, risk_contrib, conditional_ccr = \
            _calculate_portfolio_metrics(
                prices, weights, tickers,
                config.get('rebalance'),
                config['risk_free_annual'],
                config.get('var_confidence', 0.95),
                data_integrity
            )
        
        # Check key metrics
        expected_keys = ['cagr', 'volatility', 'sharpe', 'sortino', 'max_drawdown']
        for key in expected_keys:
            assert key in metrics, f"Metric {key} should be in metrics dict"
    
    def test_asset_df_structure(self):
        """Test that asset_df has correct structure."""
        config = get_config()
        prices, _, data_integrity, _, _ = _load_and_validate_data(config)
        
        tickers = config['tickers']
        weights = np.array(config['weights'], dtype=float)
        weights = weights / weights.sum()
        
        equity, port_ret, metrics, asset_df, risk_contrib, conditional_ccr = \
            _calculate_portfolio_metrics(
                prices, weights, tickers,
                config.get('rebalance'),
                config['risk_free_annual'],
                config.get('var_confidence', 0.95),
                data_integrity
            )
        
        # Check columns
        assert 'Weight' in asset_df.columns, "Weight column should be present"
        assert 'CAGR' in asset_df.columns, "CAGR column should be present"
        assert 'Vol' in asset_df.columns, "Vol column should be present"
        assert 'RiskContrib%' in asset_df.columns, "RiskContrib% column should be present"
        
        # Check index
        assert all(t in asset_df.index for t in tickers), "All tickers should be in index"


class TestStage3CorrelationAnalysis:
    """Test Stage 3: Correlation Analysis"""
    
    def test_analyze_correlations_basic(self):
        """Test basic correlation analysis."""
        config = get_config()
        prices, _, _, _, _ = _load_and_validate_data(config)
        
        # Execute
        corr, corr_raw, shrinkage_delta, dual_corr, simple_ret = \
            _analyze_correlations(prices)
        
        # Assertions
        assert isinstance(corr, pd.DataFrame), "corr should be DataFrame"
        assert isinstance(corr_raw, pd.DataFrame), "corr_raw should be DataFrame"
        assert isinstance(shrinkage_delta, (float, type(None))), "shrinkage_delta should be float or None"
        assert isinstance(simple_ret, pd.DataFrame), "simple_ret should be DataFrame"
    
    def test_correlation_matrix_shape(self):
        """Test that correlation matrices have correct shape."""
        config = get_config()
        prices, _, _, _, _ = _load_and_validate_data(config)
        
        corr, corr_raw, shrinkage_delta, dual_corr, simple_ret = \
            _analyze_correlations(prices)
        
        n_assets = len(prices.columns)
        assert corr.shape == (n_assets, n_assets), "corr should be square matrix"
        assert corr_raw.shape == (n_assets, n_assets), "corr_raw should be square matrix"
    
    def test_correlation_values_valid(self):
        """Test that correlation values are in valid range [-1, 1]."""
        config = get_config()
        prices, _, _, _, _ = _load_and_validate_data(config)
        
        corr, corr_raw, shrinkage_delta, dual_corr, simple_ret = \
            _analyze_correlations(prices)
        
        # Check raw correlation
        assert (corr_raw >= -1).all().all(), "Raw correlations should be >= -1"
        assert (corr_raw <= 1).all().all(), "Raw correlations should be <= 1"
        
        # Check shrunk correlation
        assert (corr >= -1).all().all(), "Shrunk correlations should be >= -1"
        assert (corr <= 1).all().all(), "Shrunk correlations should be <= 1"
    
    def test_simple_returns_calculated(self):
        """Test that simple returns are calculated correctly."""
        config = get_config()
        prices, _, _, _, _ = _load_and_validate_data(config)
        
        corr, corr_raw, shrinkage_delta, dual_corr, simple_ret = \
            _analyze_correlations(prices)
        
        # Check shape - returns have NAs dropped, so may have less rows
        assert simple_ret.shape[0] <= prices.shape[0], \
            "Returns should have at most same rows as prices"
        assert simple_ret.shape[1] == prices.shape[1], \
            "Returns should have same columns as prices"
        
        # Check no NaN values (they should be dropped)
        assert not simple_ret.isnull().any().any(), \
            "Simple returns should not contain NaN values"


class TestIntegration:
    """Integration tests for full pipeline"""
    
    def test_full_pipeline_stages_1_2_3(self):
        """Test that stages 1, 2, 3 work together."""
        config = get_config()
        
        # Stage 1
        prices, benchmark_prices, data_integrity, is_provisional, risk_intent = \
            _load_and_validate_data(config)
        
        # Stage 2
        tickers = config['tickers']
        weights = np.array(config['weights'], dtype=float)
        weights = weights / weights.sum()
        
        equity, port_ret, metrics, asset_df, risk_contrib, conditional_ccr = \
            _calculate_portfolio_metrics(
                prices, weights, tickers,
                config.get('rebalance'),
                config['risk_free_annual'],
                config.get('var_confidence', 0.95),
                data_integrity
            )
        
        # Stage 3
        corr, corr_raw, shrinkage_delta, dual_corr, simple_ret = \
            _analyze_correlations(prices)
        
        # Integration checks
        assert len(equity) > 0, "Equity curve should have data"
        assert len(port_ret) > 0, "Portfolio returns should have data"
        assert 'cagr' in metrics, "Metrics should include CAGR"
        assert corr.shape[0] == len(tickers), "Correlation matrix should match ticker count"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
