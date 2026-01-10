"""
Exception Hierarchy for Gate System Enforcement
================================================
Implements production-grade enforcement of INCONCLUSIVE verdicts.

Critical Rule: INCONCLUSIVE verdicts must BLOCK portfolio restructuring.
This module ensures that rule is enforced programmatically, not just via warnings.
"""

from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass


# =============================================================================
# BASE EXCEPTION HIERARCHY
# =============================================================================

class InstitutionalGateException(Exception):
    """
    Base exception for gate system enforcement.
    
    All gate-related exceptions inherit from this to allow
    catching all institutional blocks with a single except clause.
    """
    pass


class INCONCLUSIVEVerdictError(InstitutionalGateException):
    """
    Raised when analysis verdict is INCONCLUSIVE.
    
    INCONCLUSIVE verdicts indicate insufficient data quality to make
    reliable portfolio decisions. This exception prevents accidental
    misuse of unreliable analysis results.
    
    Recovery Options:
    1. Improve data quality (collect more history, fix NaN)
    2. Use alternative methodology (proxy correlations, longer beta window)
    3. Provide explicit UserAcknowledgment with documented reason
    
    Args:
        verdict_type: Type of INCONCLUSIVE (DATA_FAIL, BETA_WINDOW, etc.)
        reason: Human-readable explanation of why INCONCLUSIVE
        allowed_actions: List of actions that ARE permitted
        prohibited_actions: List of actions that are BLOCKED
        data_quality_details: Technical details about data issues
    """
    
    def __init__(
        self,
        verdict_type: str,
        reason: str,
        allowed_actions: List[str],
        prohibited_actions: Optional[List[str]] = None,
        data_quality_details: Optional[dict] = None
    ):
        self.verdict_type = verdict_type
        self.reason = reason
        self.allowed_actions = allowed_actions
        self.prohibited_actions = prohibited_actions or [
            "Portfolio restructuring",
            "Asset weight recommendations",
            "Rebalancing decisions"
        ]
        self.data_quality_details = data_quality_details or {}
        
        # Construct detailed error message
        msg_parts = [
            f"\n{'='*70}",
            f"INCONCLUSIVE VERDICT RAISED: {verdict_type}",
            f"{'='*70}",
            f"\nREASON: {reason}",
            f"\n\n🚫 PROHIBITED ACTIONS:",
        ]
        
        for action in self.prohibited_actions:
            msg_parts.append(f"   • {action}")
        
        msg_parts.append(f"\n\n✅ ALLOWED ACTIONS:")
        for action in self.allowed_actions:
            msg_parts.append(f"   • {action}")
        
        if data_quality_details:
            msg_parts.append(f"\n\n📊 DATA QUALITY DETAILS:")
            for key, value in data_quality_details.items():
                msg_parts.append(f"   • {key}: {value}")
        
        msg_parts.extend([
            f"\n\n⚠️  TO OVERRIDE THIS BLOCK:",
            f"   Use UserAcknowledgment with documented reason:",
            f"   ```python",
            f"   from portfolio_engine.utils.exceptions import UserAcknowledgment",
            f"   ack = UserAcknowledgment(",
            f"       timestamp=datetime.now(),",
            f"       user_id='analyst_001',",
            f"       verdict_type='{verdict_type}',",
            f"       reason_for_override='Interim analysis with stale data',",
            f"       responsibility_acceptance=True",
            f"   )",
            f"   result = analyze_portfolio(config, override=ack)",
            f"   ```",
            f"\n{'='*70}\n"
        ])
        
        super().__init__('\n'.join(msg_parts))


class DataIntegrityError(INCONCLUSIVEVerdictError):
    """
    Raised when correlation matrix has excessive NaN (>20%).
    
    This prevents diversification analysis with unreliable correlation data.
    """
    
    def __init__(self, corr_nan_ratio: float, threshold: float = 0.20, details: dict = None):
        super().__init__(
            verdict_type="DATA_INTEGRITY_FAIL",
            reason=f"Correlation matrix has {corr_nan_ratio:.1%} NaN (>{threshold:.0%} threshold)",
            allowed_actions=[
                "Collect more historical data",
                "Use proxy correlations for missing pairs",
                "Remove problematic tickers with sparse data",
                "Use alternative correlation estimation (shrinkage, factor models)"
            ],
            prohibited_actions=[
                "Diversification verdict",
                "Correlation-based recommendations",
                "CCR severity judgments",
                "Portfolio restructuring based on correlation"
            ],
            data_quality_details=details or {
                'corr_nan_ratio': f'{corr_nan_ratio:.1%}',
                'threshold': f'{threshold:.0%}',
                'impact': 'Correlation analysis unreliable'
            }
        )


class BetaWindowError(INCONCLUSIVEVerdictError):
    """
    Raised when beta calculation window is too short (<3 years).
    
    Beta estimates are unreliable with insufficient history.
    """
    
    def __init__(self, window_years: float, min_years: float = 3.0, details: dict = None):
        super().__init__(
            verdict_type="BETA_WINDOW_INSUFFICIENT",
            reason=f"Beta window {window_years:.1f}y < {min_years:.0f}y minimum required for reliable estimation",
            allowed_actions=[
                "Wait for more historical data to accumulate",
                "Use longer backtest period if available",
                "Use proxy benchmark beta for intent validation",
                "Accept provisional beta estimate with documented caveat"
            ],
            prohibited_actions=[
                "Risk Intent validation",
                "Beta-adjusted metrics",
                "Intent-based portfolio recommendations",
                "Structural recommendations based on beta alignment"
            ],
            data_quality_details=details or {
                'beta_window_years': f'{window_years:.1f}',
                'min_required_years': f'{min_years:.0f}',
                'impact': 'Intent validation inconclusive'
            }
        )


class IntentFailStructureInconclusiveError(INCONCLUSIVEVerdictError):
    """
    Raised when Intent FAIL is certain but structure is inconclusive.
    
    This unique state allows intent correction while blocking structural recommendations.
    """
    
    def __init__(self, intent_details: dict, structure_issue: str):
        super().__init__(
            verdict_type="INTENT_FAIL_STRUCTURE_INCONCLUSIVE",
            reason=f"Intent mismatch confirmed but structure unverifiable: {structure_issue}",
            allowed_actions=[
                "Change Risk Intent to match observed beta",
                "Document intent mismatch in IPS",
                "Improve correlation data for structural analysis"
            ],
            prohibited_actions=[
                "Structural diversification recommendations",
                "CCR-based asset changes",
                "Portfolio restructuring (structure unknown)"
            ],
            data_quality_details=intent_details
        )


# =============================================================================
# USER ACKNOWLEDGMENT SYSTEM
# =============================================================================

@dataclass
class UserAcknowledgment:
    """
    Explicit user override for INCONCLUSIVE verdicts.
    
    Required Fields:
        timestamp: When override was created
        user_id: Who authorized the override (for audit trail)
        verdict_type: Which INCONCLUSIVE verdict is being overridden
        reason_for_override: Why proceeding despite INCONCLUSIVE
        responsibility_acceptance: Must be True - explicit acceptance
    
    Optional Fields:
        approval_level: Authority level (analyst, senior, CIO)
        documented_in: Reference to documentation (IPS section, memo)
        expires_at: When override expires (for temporary use)
    
    Example:
        ack = UserAcknowledgment(
            timestamp=datetime.now(),
            user_id='senior_analyst_john',
            verdict_type='DATA_INTEGRITY_FAIL',
            reason_for_override='Using stale data for interim quarterly review',
            responsibility_acceptance=True,
            approval_level='SENIOR_ANALYST',
            documented_in='Q1_2026_Interim_Review_Memo',
            expires_at=datetime(2026, 4, 1)
        )
    """
    timestamp: datetime
    user_id: str
    verdict_type: str
    reason_for_override: str
    responsibility_acceptance: bool
    
    # Optional fields
    approval_level: Optional[str] = None  # "ANALYST", "SENIOR", "CIO"
    documented_in: Optional[str] = None
    expires_at: Optional[datetime] = None
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate override is properly documented.
        
        Returns:
            (is_valid, error_message)
        """
        if not self.responsibility_acceptance:
            return False, "responsibility_acceptance must be True"
        
        if not self.user_id or not self.user_id.strip():
            return False, "user_id is required"
        
        if not self.reason_for_override or len(self.reason_for_override) < 20:
            return False, "reason_for_override must be detailed (min 20 chars)"
        
        if self.expires_at and self.expires_at < datetime.now():
            return False, "Override has expired"
        
        return True, None
    
    def to_audit_log(self) -> dict:
        """Export to audit log format."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'verdict_type': self.verdict_type,
            'reason': self.reason_for_override,
            'approval_level': self.approval_level,
            'documented_in': self.documented_in,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }


# =============================================================================
# OVERRIDE LOGGING
# =============================================================================

_override_audit_trail = []

def log_override(override: UserAcknowledgment) -> None:
    """
    Log override to audit trail.
    
    In production, this should write to:
    - Database
    - Audit log file
    - Compliance system
    
    For now, maintains in-memory trail.
    """
    _override_audit_trail.append({
        'timestamp': datetime.now().isoformat(),
        'override': override.to_audit_log()
    })
    
    # TODO: Production implementation
    # - Write to persistent storage
    # - Alert compliance team for critical overrides
    # - Integrate with audit system


def get_override_history(user_id: Optional[str] = None) -> List[dict]:
    """
    Retrieve override history.
    
    Args:
        user_id: Filter by user (None = all overrides)
    
    Returns:
        List of override records
    """
    if user_id is None:
        return _override_audit_trail.copy()
    
    return [
        entry for entry in _override_audit_trail
        if entry['override']['user_id'] == user_id
    ]
