"""
Runtime Config Loader
=====================
Load portfolio configurations from JSON/YAML files and normalize into
the runtime config format used by the engine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception as exc:
        raise RuntimeError("PyYAML not installed. Install with `pip install pyyaml`.") from exc
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("YAML config must be a mapping at top level.")
    return data


def load_config_file(path: str) -> Dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    suffix = file_path.suffix.lower()
    if suffix in {".yml", ".yaml"}:
        return _load_yaml(file_path)
    if suffix == ".json":
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("JSON config must be an object at top level.")
        return data

    raise ValueError(f"Unsupported config format: {suffix}. Use .json or .yaml/.yml.")


def _extract_portfolio(raw: Dict[str, Any]) -> Optional[Tuple[list, list]]:
    # Accept "portfolio" or "PORTFOLIO" as ticker->weight mapping
    portfolio = raw.get("portfolio") or raw.get("PORTFOLIO")
    if isinstance(portfolio, dict) and portfolio:
        tickers = list(portfolio.keys())
        weights = list(portfolio.values())
        return tickers, weights
    return None


def _merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    merged.update(override)
    return merged


def build_runtime_config(raw: Dict[str, Any], base: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Normalize external config into runtime format.
    """
    config: Dict[str, Any] = dict(base or {})

    # Portfolio mapping -> tickers/weights
    extracted = _extract_portfolio(raw)
    if extracted:
        config["tickers"], config["weights"] = extracted

    # Direct tickers/weights
    if "tickers" in raw and "weights" in raw:
        config["tickers"] = raw["tickers"]
        config["weights"] = raw["weights"]

    # Analysis section
    analysis = raw.get("analysis") or raw.get("ANALYSIS")
    if isinstance(analysis, dict):
        config.update(analysis)

    # Export section
    export = raw.get("export") or raw.get("EXPORT")
    if isinstance(export, dict):
        current = config.get("export", {})
        config["export"] = _merge_dict(current, export)

    # Simple top-level overrides
    for key in [
        "risk_intent",
        "run_integration_tests",
        "portfolio_storage",
        "show_plots",
        "reporting",
    ]:
        if key in raw:
            config[key] = raw[key]

    return config
