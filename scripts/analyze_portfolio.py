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
import os
import argparse
from pathlib import Path

# Add src to path for development
src_path = Path(__file__).parent.parent / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

from portfolio_engine.core.main_legacy import analyze_portfolio, run_analysis_to_pdf
from portfolio_engine.config.user_config import get_config
from portfolio_engine.config.loader import load_config_file, build_runtime_config


def main():
    """Run portfolio analysis with current configuration."""
    parser = argparse.ArgumentParser(description="Run portfolio analysis")
    parser.add_argument("--config", help="Path to JSON/YAML config file", default=None)
    args = parser.parse_args()

    print("=" * 70)
    print("PORTFOLIO ANALYSIS ENGINE v2.1.0")
    print("=" * 70)
    print()

    base_config = get_config()
    config_path = args.config or os.environ.get("PORTFOLIO_CONFIG_PATH")
    if config_path:
        raw = load_config_file(config_path)
        config = build_runtime_config(raw, base=base_config)
        print(f"Using external config: {config_path}")
    else:
        config = base_config
    
    # Run analysis with PDF output (path fixed relative to project root)
    project_root = Path(__file__).parent.parent
    pdf_path = project_root / "output" / "portfolio_analysis.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    run_analysis_to_pdf(
        config=config,
        pdf_path=str(pdf_path)
    )
    
    print()
    print("=" * 70)
    print("Analysis complete! Check output/ directory for reports.")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
