#!/usr/bin/env python3
"""
Portfolio Analysis CLI Entry Point
==================================
Minimal CLI wrapper for portfolio analysis.

Usage:
    python -m scripts.analyze_portfolio
    # or after pip install -e .
    analyze-portfolio
"""

import sys
from pathlib import Path

# Add src to path for development
src_path = Path(__file__).parent.parent / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

from portfolio_engine.core.main_legacy import analyze_portfolio, run_analysis_to_pdf
from portfolio_engine.config.user_config import get_config


def main():
    """Run portfolio analysis with current configuration."""
    print("=" * 70)
    print("PORTFOLIO ANALYSIS ENGINE v2.1.0")
    print("=" * 70)
    print()
    
    config = get_config()
    
    # Run analysis with PDF output
    run_analysis_to_pdf(
        config=config,
        pdf_path="output/portfolio_analysis.pdf"
    )
    
    print()
    print("=" * 70)
    print("Analysis complete! Check output/ directory for reports.")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
