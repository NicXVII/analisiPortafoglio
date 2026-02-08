"""
Yahoo Finance Client
====================
Download price data with local cache and hash indexing.
"""

from __future__ import annotations

import hashlib
import json
import os
import gzip
from datetime import datetime
from typing import Optional

import pandas as pd
import yfinance as yf


CACHE_DIR = ".data_cache"
CACHE_INDEX = "index.json"
CACHE_TTL_SECONDS = 86400
CACHE_MAX_AGE_SECONDS = 7 * 86400


def _get_cache_key(tickers: list, start: str, end: str) -> str:
    key_str = f"{sorted(tickers)}_{start}_{end}"
    return hashlib.md5(key_str.encode()).hexdigest()


def _get_cache_path(cache_key: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{cache_key}.pkl.gz")


def _load_cache_index() -> dict:
    index_path = os.path.join(CACHE_DIR, CACHE_INDEX)
    if not os.path.exists(index_path):
        return {}
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload.get("hashes", {})
    except Exception:
        return {}


def _write_cache_index(index: dict) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    index_path = os.path.join(CACHE_DIR, CACHE_INDEX)
    tmp_path = index_path + ".tmp"
    payload = {
        "version": 1,
        "updated_at": datetime.now().isoformat(),
        "hashes": index,
    }
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
    os.replace(tmp_path, index_path)


def _cleanup_cache(max_age_seconds: int = CACHE_MAX_AGE_SECONDS) -> None:
    """
    Remove cache entries older than max_age_seconds and prune missing files.
    Keeps the cache directory from growing indefinitely.
    """
    if not os.path.exists(CACHE_DIR):
        return
    index = _load_cache_index()
    if not index:
        return

    now_ts = datetime.now().timestamp()
    changed = False
    for cache_key, meta in list(index.items()):
        path = meta.get("path") or _get_cache_path(cache_key)
        try:
            if not os.path.exists(path):
                index.pop(cache_key, None)
                changed = True
                continue
            age = now_ts - os.path.getmtime(path)
            if age > max_age_seconds:
                os.remove(path)
                index.pop(cache_key, None)
                changed = True
        except Exception:
            # Ignore cleanup errors to avoid breaking downloads
            continue

    if changed:
        _write_cache_index(index)


def _load_from_cache(cache_key: str) -> Optional[pd.DataFrame]:
    cache_path = _get_cache_path(cache_key)
    if os.path.exists(cache_path):
        cache_age = datetime.now().timestamp() - os.path.getmtime(cache_path)
        if cache_age < CACHE_TTL_SECONDS:
            try:
                with gzip.open(cache_path, "rb") as f:
                    return pd.read_pickle(f)
            except Exception:
                return None
    return None


def _save_to_cache(cache_key: str, data: pd.DataFrame) -> None:
    try:
        cache_path = _get_cache_path(cache_key)
        with gzip.open(cache_path, "wb") as f:
            data.to_pickle(f)

        index = _load_cache_index()
        index[cache_key] = {
            "saved_at": datetime.now().isoformat(),
            "rows": int(data.shape[0]) if hasattr(data, "shape") else None,
            "cols": int(data.shape[1]) if hasattr(data, "shape") else None,
            "path": cache_path,
        }
        _write_cache_index(index)
    except Exception:
        pass


def download_prices(
    tickers: list,
    start: str,
    end: Optional[str] = None,
    use_cache: bool = True
) -> pd.DataFrame:
    end_str = end or datetime.now().strftime("%Y-%m-%d")

    cache_key = None
    if use_cache:
        _cleanup_cache()
        cache_key = _get_cache_key(tickers, start, end_str)
        cached = _load_from_cache(cache_key)
        if cached is not None:
            empty_cols = [c for c in cached.columns if cached[c].isna().all()]
            if not empty_cols:
                return cached

    data = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)

    if isinstance(data.columns, pd.MultiIndex):
        data = data["Close"]
    else:
        if len(tickers) == 1:
            data = data[["Close"]].rename(columns={"Close": tickers[0]})
        else:
            data = data["Close"]

    if not data.empty:
        empty_cols = [c for c in data.columns if data[c].isna().all()]
        if empty_cols:
            for t in empty_cols:
                try:
                    single = yf.download(t, start=start, end=end, auto_adjust=True, progress=False)
                    if isinstance(single.columns, pd.MultiIndex):
                        single = single["Close"]
                    else:
                        single = single[["Close"]].rename(columns={"Close": t})
                    if not single.empty:
                        data[t] = single[t]
                except Exception:
                    pass

    if use_cache and cache_key is not None and data is not None and not data.empty:
        _save_to_cache(cache_key, data)

    return data
