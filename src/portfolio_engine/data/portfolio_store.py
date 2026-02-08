"""
Portfolio Storage Module
========================
Persist portfolio configurations with hash-based deduplication.
Optimized for fast lookup and minimal I/O.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

import numpy as np


INDEX_FILENAME = "index.json"
DATA_FILENAME = "portfolios.jsonl"


def _normalize_for_hash(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _normalize_for_hash(v) for k, v in sorted(value.items(), key=lambda x: str(x[0]))}
    if isinstance(value, (list, tuple)):
        return [_normalize_for_hash(v) for v in value]
    if isinstance(value, set):
        return [_normalize_for_hash(v) for v in sorted(value, key=lambda x: str(x))]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.ndarray,)):
        return [_normalize_for_hash(v) for v in value.tolist()]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def _canonical_json(data: Any) -> str:
    normalized = _normalize_for_hash(data)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def build_config_hash(config: Dict[str, Any]) -> str:
    payload = _canonical_json(config).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_index(index_path: Path) -> Dict[str, Dict[str, Any]]:
    if not index_path.exists():
        return {}
    try:
        with index_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("hashes", {})
    except Exception:
        return {}


def _write_index(index_path: Path, hashes: Dict[str, Dict[str, Any]]) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated_at": datetime.utcnow().isoformat(),
        "hashes": hashes,
    }
    tmp_path = index_path.with_suffix(".json.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
    tmp_path.replace(index_path)


def persist_portfolio_config(
    config: Dict[str, Any],
    store_dir: str = "output/portfolio_store",
) -> Dict[str, Any]:
    """
    Save portfolio configuration if not already present.
    Uses hash-based deduplication for O(1) lookup.
    """
    store_path = Path(store_dir)
    index_path = store_path / INDEX_FILENAME
    data_path = store_path / DATA_FILENAME

    config_hash = build_config_hash(config)
    hashes = _load_index(index_path)

    if config_hash in hashes:
        return {
            "saved": False,
            "hash": config_hash,
            "reason": "duplicate",
        }

    store_path.mkdir(parents=True, exist_ok=True)
    entry = {
        "hash": config_hash,
        "saved_at": datetime.utcnow().isoformat(),
        "config": _normalize_for_hash(config),
    }

    with data_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, separators=(",", ":"), ensure_ascii=True) + "\n")

    hashes[config_hash] = {
        "saved_at": entry["saved_at"],
    }
    _write_index(index_path, hashes)

    return {
        "saved": True,
        "hash": config_hash,
        "reason": "new",
    }
