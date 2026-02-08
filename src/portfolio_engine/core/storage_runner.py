"""
Storage Runner
==============
Handles portfolio configuration persistence with deduplication.
"""

from __future__ import annotations

from typing import Any, Dict

from portfolio_engine.data.portfolio_store import persist_portfolio_config


def auto_save_portfolio(config: Dict[str, Any], logger) -> None:
    """
    Persist current portfolio configuration if enabled.
    """
    try:
        storage_cfg = config.get("portfolio_storage", {})
        if storage_cfg.get("enabled", True):
            storage_dir = storage_cfg.get("store_dir", "output/portfolio_store")
            storage_result = persist_portfolio_config(config, store_dir=storage_dir)
            if storage_result.get("saved"):
                logger.info(f"Portfolio storage: saved (hash={storage_result.get('hash')})")
            else:
                logger.info(f"Portfolio storage: duplicate skipped (hash={storage_result.get('hash')})")
    except Exception as exc:
        logger.warning(f"Portfolio storage skipped: {exc}")
