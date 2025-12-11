"""
Cascade analysis models - KEY NEW FEATURE.

The original system treats each finding in isolation.
This model represents how a single trigger event (e.g., change of control)
cascades through multiple documents and creates interconnected consequences.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from decimal import Decimal
from enum import Enum


class ConsentStatus(Enum):
    """Status of required consent."""
    REQUIRED = "required"
    OBTAINED = "obtained"
    PENDING = "pending"
    WAIVED = "waived"
    NOT_APPLICABLE = "not_applicable"


class RiskLevel(Enum):
    """Risk level for cascade items."""
    CRITICAL = "critical"  # Deal cannot close without resolution
    HIGH = "high"  # Significant risk, needs attention
    MEDIUM = "medium"  # Moderate risk
    LOW = "low"  # Minor risk


@dataclass
class CascadeItem:
    """
    A single item in a cascade chain.

    Represents one contract/document affected by the trigger event.
    """
    document: str
    clause_reference: str
    trigger_threshold: str  # e.g., ">50% shares", "change of control"
    consequence: str  # What happens when triggered

    # Consent requirements
    consent_required: bool = False
    consent_from: Optional[str] = None
    consent_status: ConsentStatus = ConsentStatus.REQUIRED
    notice_period_days: Optional[int] = None

    # Financial impact
    financial_exposure_amount: Optional[Decimal] = None
    financial_exposure_currency: str = "ZAR"
    financial_exposure_type: Optional[str] = None  # liquidated_damages, termination_fee, acceleration
    calculation_basis: Optional[str] = None

    # Risk assessment
    can_be_waived: bool = True
    risk_level: RiskLevel = RiskLevel.MEDIUM
    deal_impact: str = "condition_precedent"  # deal_blocker, condition_precedent, warranty_indemnity

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "document": self.document,
            "clause_reference": self.clause_reference,
            "trigger_threshold": self.trigger_threshold,
            "consequence": self.consequence,
            "consent_required": self.consent_required,
            "consent_from": self.consent_from,
            "consent_status": self.consent_status.value,
            "notice_period_days": self.notice_period_days,
            "financial_exposure": {
                "amount": float(self.financial_exposure_amount) if self.financial_exposure_amount else None,
                "currency": self.financial_exposure_currency,
                "type": self.financial_exposure_type,
                "calculation_basis": self.calculation_basis,
            } if self.financial_exposure_amount else None,
            "can_be_waived": self.can_be_waived,
            "risk_level": self.risk_level.value,
            "deal_impact": self.deal_impact,
        }


@dataclass
class CascadeTrigger:
    """The event that triggers the cascade."""
    event_type: str  # change_of_control, assignment, insolvency
    description: str
    threshold: str  # e.g., "acquisition of >50% shares"
    transaction_matches: bool = True  # Does the planned transaction trigger this?


@dataclass
class CascadeAnalysis:
    """
    Complete cascade analysis for a trigger event.

    This is the KEY ARCHITECTURAL IMPROVEMENT: Instead of treating
    7 separate "change of control" findings as independent issues,
    we link them as a single cascade with a common trigger.
    """
    trigger: CascadeTrigger
    cascade_items: List[CascadeItem] = field(default_factory=list)

    # Aggregated analysis
    total_financial_exposure: Decimal = Decimal("0")
    total_financial_exposure_currency: str = "ZAR"

    # Critical path to closing
    critical_path: List[str] = field(default_factory=list)

    # Summary
    summary: Optional[str] = None

    def add_item(self, item: CascadeItem):
        """Add a cascade item and update totals."""
        self.cascade_items.append(item)
        if item.financial_exposure_amount:
            self.total_financial_exposure += item.financial_exposure_amount

    def get_deal_blockers(self) -> List[CascadeItem]:
        """Get items that are deal blockers."""
        return [
            item for item in self.cascade_items
            if item.deal_impact == "deal_blocker" or item.risk_level == RiskLevel.CRITICAL
        ]

    def get_consents_required(self) -> List[CascadeItem]:
        """Get items requiring consent."""
        return [
            item for item in self.cascade_items
            if item.consent_required and item.consent_status == ConsentStatus.REQUIRED
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trigger": {
                "event_type": self.trigger.event_type,
                "description": self.trigger.description,
                "threshold": self.trigger.threshold,
                "transaction_matches": self.trigger.transaction_matches,
            },
            "cascade_items": [item.to_dict() for item in self.cascade_items],
            "total_financial_exposure": {
                "amount": float(self.total_financial_exposure),
                "currency": self.total_financial_exposure_currency,
            },
            "critical_path": self.critical_path,
            "summary": self.summary,
            "deal_blockers_count": len(self.get_deal_blockers()),
            "consents_required_count": len(self.get_consents_required()),
        }


@dataclass
class ConsentMatrixItem:
    """An item in the consent matrix."""
    contract: str
    counterparty: str
    consent_type: str  # written_consent, notification, approval
    trigger: str  # What triggers the consent requirement
    deadline: Optional[str] = None
    consequence_if_not_obtained: Optional[str] = None
    status: ConsentStatus = ConsentStatus.REQUIRED
    responsible_party: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract": self.contract,
            "counterparty": self.counterparty,
            "consent_type": self.consent_type,
            "trigger": self.trigger,
            "deadline": self.deadline,
            "consequence_if_not_obtained": self.consequence_if_not_obtained,
            "status": self.status.value,
            "responsible_party": self.responsible_party,
            "notes": self.notes,
        }
