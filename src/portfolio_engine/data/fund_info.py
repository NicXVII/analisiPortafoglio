"""
Fund Info Module
================
Helpers to fetch sector allocation and top holdings for ETFs via yfinance.
Used only for reporting (non-core analytics).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

import yfinance as yf


def _coerce_sector_dict(raw: Any) -> Optional[Dict[str, float]]:
    if raw is None:
        return None

    if isinstance(raw, dict):
        return {str(k): float(v) for k, v in raw.items()}

    to_dict = getattr(raw, "to_dict", None)
    if callable(to_dict):
        data = to_dict()
        if isinstance(data, dict) and data:
            first_value = next(iter(data.values()))
            if isinstance(first_value, dict):
                return {str(k): float(v) for k, v in first_value.items()}
            return {str(k): float(v) for k, v in data.items()}

    return None


def _normalize_sector_weights(sectors: Dict[str, float]) -> Optional[Dict[str, float]]:
    if not sectors:
        return None

    total = sum(v for v in sectors.values() if v is not None)
    if total <= 0:
        return None

    if total > 1.5:
        sectors = {k: v / 100.0 for k, v in sectors.items()}
        total = sum(sectors.values())

    if abs(total - 1.0) > 0.05:
        sectors = {k: v / total for k, v in sectors.items()}

    return sectors


def get_sector_weightings(ticker: str) -> Optional[Dict[str, float]]:
    t = yf.Ticker(ticker)
    fund = getattr(t, "funds_data", None)
    if fund is None:
        return None

    raw = getattr(fund, "sector_weightings", None)
    sectors = _coerce_sector_dict(raw)
    return _normalize_sector_weights(sectors) if sectors else None


def get_top_holdings(ticker: str, top_n: int = 10) -> Optional[List[Dict[str, Any]]]:
    t = yf.Ticker(ticker)
    fund = getattr(t, "funds_data", None)
    if fund is None:
        return None

    raw = getattr(fund, "top_holdings", None)
    if raw is None:
        return None

    try:
        if hasattr(raw, "iloc") and hasattr(raw, "columns"):
            name_col = None
            pct_col = None
            for c in raw.columns:
                cl = str(c).strip().lower()
                if cl == "name":
                    name_col = c
                if "holding percent" in cl:
                    pct_col = c

            if name_col is None or pct_col is None:
                return None

            out: List[Dict[str, Any]] = []
            df = raw.head(top_n)
            for _, row in df.iterrows():
                name = str(row[name_col]).strip()
                if not name:
                    continue
                try:
                    pct = float(row[pct_col])
                except Exception:
                    continue
                if pct > 1.5:
                    pct = pct / 100.0

                symbol = None
                if isinstance(row.name, str) and row.name.strip():
                    symbol = row.name.strip()

                out.append({"name": name, "symbol": symbol, "weight": pct})

            return out if out else None
    except Exception:
        return None

    return None


def get_portfolio_sector_allocation(
    tickers: List[str],
    weights: List[float],
    min_slice_pct: float = 3.0
) -> Dict[str, Any]:
    total_w = sum(weights)
    if total_w <= 0:
        return {"sectors": {}, "missing": tickers, "unknown_pct": 100.0}
    weights = [w / total_w for w in weights]

    portfolio_sector: Dict[str, float] = {}
    missing: List[str] = []

    sector_map: Dict[str, Optional[Dict[str, float]]] = {}
    max_workers = min(8, max(1, len(tickers)))
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(get_sector_weightings, t): t for t in tickers}
        for fut in as_completed(futures):
            t = futures[fut]
            try:
                sector_map[t] = fut.result()
            except Exception:
                sector_map[t] = None

    for ticker, w in zip(tickers, weights):
        sectors = sector_map.get(ticker)
        if not sectors:
            missing.append(ticker)
            continue
        for sector, s_w in sectors.items():
            portfolio_sector[sector] = portfolio_sector.get(sector, 0.0) + w * s_w

    total_alloc = sum(portfolio_sector.values())
    unknown = max(0.0, 1.0 - total_alloc)
    if unknown > 0:
        portfolio_sector["Unknown"] = portfolio_sector.get("Unknown", 0.0) + unknown

    sector_pct = {k: v * 100.0 for k, v in portfolio_sector.items()}
    sector_pct = dict(sorted(sector_pct.items(), key=lambda x: x[1], reverse=True))

    grouped: Dict[str, float] = {}
    other_sum = 0.0
    for sector, pct in sector_pct.items():
        if pct < min_slice_pct:
            other_sum += pct
        else:
            grouped[sector] = pct
    if other_sum > 0:
        grouped["Other"] = other_sum

    grouped = dict(sorted(grouped.items(), key=lambda x: x[1], reverse=True))

    return {
        "sectors": grouped,
        "missing": missing,
        "unknown_pct": round(unknown * 100.0, 2),
    }


def get_top_holdings_by_ticker(
    tickers: List[str],
    top_n: int = 10
) -> Dict[str, Any]:
    by_ticker: Dict[str, List[Dict[str, Any]]] = {}
    missing: List[str] = []

    max_workers = min(8, max(1, len(tickers)))
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(get_top_holdings, t, top_n=top_n): t for t in tickers}
        for fut in as_completed(futures):
            ticker = futures[fut]
            try:
                holdings = fut.result()
            except Exception:
                holdings = None
            if not holdings:
                missing.append(ticker)
                continue
            by_ticker[ticker] = holdings

    return {"by_ticker": by_ticker, "missing": missing}
