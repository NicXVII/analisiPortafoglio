"""
Crisis Definitions Module
=========================
Single source of truth for crisis period definitions.

AUDIT FIX C2: This module centralizes KNOWN_CRISIS_PERIODS which was
previously duplicated in analysis.py and regime_detection.py.

All modules should import from here to ensure consistency.
"""

from dataclasses import dataclass
from datetime import date
from typing import List, Optional
import pandas as pd


@dataclass
class CrisisPeriod:
    """
    Represents a known historical crisis period.
    
    Attributes:
        name: Human-readable crisis name
        start: Start date of crisis (str 'YYYY-MM-DD')
        end: End date of crisis (str 'YYYY-MM-DD')
        crisis_type: Type of crisis (SYSTEMIC_CRISIS, REGIONAL_STRESS, etc.)
        max_dd_typical: Expected max drawdown during this crisis
        trigger: Post-hoc description of what triggered the crisis
        severity: MILD, MODERATE, or SEVERE
        detection_method: Always POST_HOC - these are retrospectively identified
    """
    name: str
    start: str  # 'YYYY-MM-DD' format for backward compatibility
    end: str    # 'YYYY-MM-DD' format for backward compatibility
    crisis_type: str  # SYSTEMIC_CRISIS, REGIONAL_STRESS, SECTOR_STRESS, VOLATILITY_SPIKE, TIGHTENING
    max_dd_typical: float
    trigger: str
    severity: str = "MODERATE"  # 'MILD', 'MODERATE', 'SEVERE'
    detection_method: str = "POST_HOC"
    
    def __post_init__(self):
        """Add disclaimer about retrospective identification."""
        self.disclaimer = (
            f"Crisis period '{self.name}' identified retrospectively. "
            f"Real-time detection would not have known end date ({self.end})."
        )
    
    def contains_date(self, check_date) -> bool:
        """Check if a date falls within this crisis period."""
        if isinstance(check_date, str):
            check_str = check_date
        elif isinstance(check_date, pd.Timestamp):
            check_str = check_date.strftime('%Y-%m-%d')
        elif isinstance(check_date, date):
            check_str = check_date.strftime('%Y-%m-%d')
        else:
            check_str = str(check_date)
        return self.start <= check_str <= self.end
    
    def to_dict(self) -> dict:
        """Convert to dictionary format for backward compatibility."""
        return {
            'name': self.name,
            'start': self.start,
            'end': self.end,
            'type': self.crisis_type,
            'max_dd_typical': self.max_dd_typical,
            'trigger': self.trigger,
        }


# =============================================================================
# KNOWN CRISIS PERIODS - SINGLE SOURCE OF TRUTH
# =============================================================================
# NOTE: These are POST-HOC identified periods. The triggers are observations
# made after the fact, NOT real-time detection signals.
# Dates are S&P500 peak-to-trough, not arbitrary values.

_CRISIS_PERIODS_INTERNAL: List[CrisisPeriod] = [
    CrisisPeriod(
        name="GFC",
        start="2007-10-09",  # S&P500 peak
        end="2009-03-09",    # S&P500 trough
        crisis_type="SYSTEMIC_CRISIS",
        max_dd_typical=-0.57,
        trigger="Post-hoc: S&P500 -57%, VIX picco 80.86 (Nov 2008)",
        severity="SEVERE"
    ),
    CrisisPeriod(
        name="Euro Crisis",
        start="2011-04-29",
        end="2011-10-03",
        crisis_type="REGIONAL_STRESS",
        max_dd_typical=-0.19,
        trigger="Post-hoc: PIIGS spread >500bps, S&P -19%",
        severity="MODERATE"
    ),
    CrisisPeriod(
        name="China Deval / Oil Crash",
        start="2015-08-17",
        end="2016-02-11",
        crisis_type="SECTOR_STRESS",
        max_dd_typical=-0.14,
        trigger="Post-hoc: Yuan -3% in 2 giorni, WTI $26, S&P -14%",
        severity="MODERATE"
    ),
    CrisisPeriod(
        name="Vol-mageddon",
        start="2018-01-26",
        end="2018-02-08",
        crisis_type="VOLATILITY_SPIKE",
        max_dd_typical=-0.10,
        trigger="Post-hoc: VIX +116% in 1 giorno (Feb 5), XIV -96%",
        severity="MILD"
    ),
    CrisisPeriod(
        name="Q4 2018 Selloff",
        start="2018-10-03",
        end="2018-12-24",
        crisis_type="VOLATILITY_SPIKE",
        max_dd_typical=-0.20,
        trigger="Post-hoc: Fed hawkish, S&P -20% in Q4",
        severity="MODERATE"
    ),
    CrisisPeriod(
        name="COVID Crash",
        start="2020-02-19",
        end="2020-03-23",
        crisis_type="SYSTEMIC_CRISIS",
        max_dd_typical=-0.34,
        trigger="Post-hoc: S&P -34% in 33 giorni, VIX 82.69",
        severity="SEVERE"
    ),
    CrisisPeriod(
        name="Rate Tightening 2022",
        start="2022-01-03",
        end="2022-10-12",
        crisis_type="TIGHTENING",
        max_dd_typical=-0.25,
        trigger="Post-hoc: Fed +425bps, S&P -25%, bonds -13%",
        severity="MODERATE"
    ),
]


# BACKWARD COMPATIBILITY: Export as list of dicts (old format)
# This allows existing code to work without modification
KNOWN_CRISIS_PERIODS: List[dict] = [cp.to_dict() for cp in _CRISIS_PERIODS_INTERNAL]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_crisis_periods() -> List[CrisisPeriod]:
    """
    Return a copy of crisis periods as CrisisPeriod objects.
    
    Returns:
        List of CrisisPeriod objects
    """
    return list(_CRISIS_PERIODS_INTERNAL)


def get_crisis_periods_dict() -> List[dict]:
    """
    Return crisis periods as list of dicts for backward compatibility.
    
    This matches the old format used in analysis.py and regime_detection.py.
    
    Returns:
        List of dictionaries with 'name', 'start', 'end', 'type', 'max_dd_typical', 'trigger' keys
    """
    return list(KNOWN_CRISIS_PERIODS)  # Already in dict format


def is_crisis_date(check_date) -> bool:
    """
    Check if a date falls within any known crisis period.
    
    Args:
        check_date: date object or string 'YYYY-MM-DD' or pandas Timestamp
        
    Returns:
        True if date is within a crisis period
    """
    for crisis in _CRISIS_PERIODS_INTERNAL:
        if crisis.contains_date(check_date):
            return True
    return False


def get_crisis_for_date(check_date) -> Optional[CrisisPeriod]:
    """
    Get the crisis period containing a specific date.
    
    Args:
        check_date: date object or string 'YYYY-MM-DD' or pandas Timestamp
        
    Returns:
        CrisisPeriod if date is in a crisis, None otherwise
    """
    for crisis in _CRISIS_PERIODS_INTERNAL:
        if crisis.contains_date(check_date):
            return crisis
    return None


def get_crisis_date_ranges() -> List[tuple]:
    """
    Get crisis periods as (start, end) tuples of pandas Timestamps.
    
    Useful for masking DataFrames.
    
    Returns:
        List of (start_timestamp, end_timestamp) tuples
    """
    return [
        (pd.Timestamp(cp.start), pd.Timestamp(cp.end))
        for cp in _CRISIS_PERIODS_INTERNAL
    ]


def filter_crisis_returns(returns: pd.DataFrame) -> pd.DataFrame:
    """
    Filter returns DataFrame to only include crisis periods.
    
    Args:
        returns: DataFrame with DatetimeIndex
        
    Returns:
        DataFrame containing only rows during crisis periods
    """
    mask = pd.Series(False, index=returns.index)
    
    for crisis in _CRISIS_PERIODS_INTERNAL:
        start = pd.Timestamp(crisis.start)
        end = pd.Timestamp(crisis.end)
        mask |= (returns.index >= start) & (returns.index <= end)
    
    return returns[mask]


def get_severe_crises() -> List[CrisisPeriod]:
    """Get only SEVERE crisis periods (GFC, COVID)."""
    return [cp for cp in _CRISIS_PERIODS_INTERNAL if cp.severity == "SEVERE"]


def get_moderate_crises() -> List[CrisisPeriod]:
    """Get MODERATE crisis periods."""
    return [cp for cp in _CRISIS_PERIODS_INTERNAL if cp.severity == "MODERATE"]
