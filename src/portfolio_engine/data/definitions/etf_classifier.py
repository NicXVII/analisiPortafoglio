"""
ETF Classifier (deterministico)
===============================

Obiettivo: classificare i ticker senza usare metriche calcolate (no volatilità),
evitando logiche circolari. Utilizza:
1) Lookup esplicito in etf_taxonomy.json
2) Regole di keyword matching
3) Fallback a UNKNOWN

Restituisce categoria, profilo di rischio, metodo e livello di confidenza.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, List

TAXONOMY_PATH = Path(__file__).parent / "etf_taxonomy.json"


class ETFClassifier:
    """Classificatore deterministico basato su tassonomia + keyword."""

    def __init__(self, taxonomy_path: Path = TAXONOMY_PATH):
        self.taxonomy = self._load_taxonomy(taxonomy_path)
        self.keyword_rules = self._build_keyword_rules()

    def _load_taxonomy(self, path: Path) -> Dict:
        if path.exists():
            try:
                return json.loads(path.read_text())
            except json.JSONDecodeError:
                return {}
        return {}

    def _build_keyword_rules(self) -> Dict[str, Dict]:
        return {
            "FIXED_INCOME": {
                "keywords": ["AGG", "BND", "GOVT", "TREAS", "CORP", "HY", "IG", "TIP", "TIPS"],
                "category": "FIXED_INCOME",
                "risk_profile": "LOW",
            },
            "COMMODITY_GOLD": {
                "keywords": ["GLD", "IAU", "SGLD", "GOLD", "PHYS"],
                "category": "COMMODITY",
                "risk_profile": "MEDIUM",
            },
            "REIT": {
                "keywords": ["REIT", "VNQ", "IYR", "XLRE"],
                "category": "REAL_ESTATE",
                "risk_profile": "MEDIUM_HIGH",
            },
            "EMERGING": {
                "keywords": ["EM", "EEM", "VWO", "IEMG", "EMIM"],
                "category": "EQUITY_EMERGING",
                "risk_profile": "HIGH",
            },
            "SMALL_CAP": {
                "keywords": ["SMALL", "SML", "WSML", "VB", "IJR", "IUSN"],
                "category": "EQUITY_SMALL",
                "risk_profile": "HIGH",
            },
            "VALUE": {
                "keywords": ["VALUE", "VTV", "IWD", "VLUE"],
                "category": "EQUITY_VALUE",
                "risk_profile": "MEDIUM_HIGH",
            },
            "THEMATIC": {
                "keywords": ["ARK", "ROBOT", "SEMI", "CYBER", "CLEAN", "SOLAR", "GENOME", "ESPO", "BOTZ", "ROBO"],
                "category": "EQUITY_THEMATIC",
                "risk_profile": "VERY_HIGH",
                "survivorship_risk": "HIGH",
            },
            "LEVERAGED": {
                "keywords": ["TQQQ", "SQQQ", "UPRO", "SPXU", "UVXY", "TECL", "LABU", "SOXL"],
                "category": "LEVERAGED",
                "risk_profile": "EXTREME",
                "survivorship_risk": "VERY_HIGH",
            },
        }

    def classify(self, ticker: str) -> Dict[str, str]:
        t = ticker.upper().replace(".L", "").replace(".DE", "")

        # 1) lookup tassonomia
        if ticker in self.taxonomy:
            entry = self.taxonomy[ticker]
            return {
                "ticker": ticker,
                "category": entry.get("category", "UNKNOWN"),
                "risk_profile": entry.get("risk_profile", "UNKNOWN"),
                "method": "TAXONOMY_LOOKUP",
                "survivorship_risk": entry.get("survivorship_risk", "NORMAL"),
                "confidence": "HIGH",
            }

        # 2) keyword matching
        for rule_name, rule in self.keyword_rules.items():
            if any(kw in t for kw in rule["keywords"]):
                return {
                    "ticker": ticker,
                    "category": rule["category"],
                    "risk_profile": rule["risk_profile"],
                    "method": f"KEYWORD:{rule_name}",
                    "survivorship_risk": rule.get("survivorship_risk", "NORMAL"),
                    "confidence": "MEDIUM",
                }

        # 3) default
        return {
            "ticker": ticker,
            "category": "EQUITY_UNKNOWN",
            "risk_profile": "UNKNOWN",
            "method": "DEFAULT",
            "survivorship_risk": "UNKNOWN",
            "confidence": "LOW",
            "warning": f"Ticker {ticker} non classificato. Aggiungere a etf_taxonomy.json.",
        }


_classifier: Optional[ETFClassifier] = None


def get_classifier() -> ETFClassifier:
    global _classifier
    if _classifier is None:
        _classifier = ETFClassifier()
    return _classifier


def classify_ticker(ticker: str) -> Dict[str, str]:
    return get_classifier().classify(ticker)


def classify_portfolio(tickers: List[str]) -> Dict[str, Dict[str, str]]:
    classifier = get_classifier()
    return {t: classifier.classify(t) for t in tickers}
