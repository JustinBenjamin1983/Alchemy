"""
Enhanced Finding model with deal impact classification.

Key improvement over original system: Includes deal_impact field
to distinguish between deal-blockers and routine issues.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from decimal import Decimal


class Severity(Enum):
    """Finding severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class DealImpact(Enum):
    """
    Deal impact classification - KEY IMPROVEMENT.

    The original system only had Red/Amber/Green.
    This provides actionable classification.
    """
    DEAL_BLOCKER = "deal_blocker"  # Transaction CANNOT close without resolution
    PRICE_CHIP = "price_chip"  # Affects valuation/consideration
    CONDITION_PRECEDENT = "condition_precedent"  # Must be resolved before closing
    WARRANTY_INDEMNITY = "warranty_indemnity"  # Allocate risk via contract
    POST_CLOSING = "post_closing"  # Can be resolved after completion
    NOTED = "noted"  # For information only


class FindingType(Enum):
    """Type of finding."""
    RISK = "risk"  # Identified risk/issue
    GAP = "gap"  # Missing information/document
    CONFLICT = "conflict"  # Cross-document conflict
    POSITIVE = "positive"  # Positive confirmation
    CALCULATION = "calculation"  # Calculated exposure
    CASCADE = "cascade"  # Part of a cascade chain


@dataclass
class FinancialExposure:
    """Financial exposure with calculation basis."""
    amount: Decimal
    currency: str = "ZAR"
    calculation_basis: Optional[str] = None
    exposure_type: Optional[str] = None  # liquidated_damages, acceleration, penalty, etc.
    triggered_by: Optional[str] = None


@dataclass
class Finding:
    """
    Enhanced finding model with deal impact classification.

    Attributes:
        finding_id: Unique identifier
        finding_type: Type of finding (risk, gap, conflict, etc.)
        description: Clear description of the finding
        source_document: Primary source document
        source_documents: All related source documents
        clause_reference: Specific clause reference(s)
        evidence_quote: Direct quote from document(s)
        severity: Severity level
        deal_impact: Deal impact classification
        financial_exposure: Calculated financial exposure if applicable
        action_required: What needs to be done
        related_findings: IDs of related findings (for cascade linking)
        confidence: Confidence score 0.0-1.0
        metadata: Additional metadata
    """
    finding_id: str
    finding_type: FindingType
    description: str
    source_document: str
    severity: Severity = Severity.MEDIUM
    deal_impact: DealImpact = DealImpact.NOTED

    # Optional fields
    source_documents: List[str] = field(default_factory=list)
    clause_reference: Optional[str] = None
    evidence_quote: Optional[str] = None
    financial_exposure: Optional[FinancialExposure] = None
    action_required: Optional[str] = None
    related_findings: List[str] = field(default_factory=list)
    confidence: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "finding_id": self.finding_id,
            "finding_type": self.finding_type.value,
            "description": self.description,
            "source_document": self.source_document,
            "source_documents": self.source_documents,
            "severity": self.severity.value,
            "deal_impact": self.deal_impact.value,
            "clause_reference": self.clause_reference,
            "evidence_quote": self.evidence_quote,
            "action_required": self.action_required,
            "related_findings": self.related_findings,
            "confidence": self.confidence,
        }

        if self.financial_exposure:
            result["financial_exposure"] = {
                "amount": float(self.financial_exposure.amount),
                "currency": self.financial_exposure.currency,
                "calculation_basis": self.financial_exposure.calculation_basis,
                "exposure_type": self.financial_exposure.exposure_type,
                "triggered_by": self.financial_exposure.triggered_by,
            }

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Finding":
        """Create Finding from dictionary."""
        financial_exposure = None
        if "financial_exposure" in data and data["financial_exposure"]:
            fe = data["financial_exposure"]
            financial_exposure = FinancialExposure(
                amount=Decimal(str(fe.get("amount", 0))),
                currency=fe.get("currency", "ZAR"),
                calculation_basis=fe.get("calculation_basis"),
                exposure_type=fe.get("exposure_type"),
                triggered_by=fe.get("triggered_by"),
            )

        return cls(
            finding_id=data.get("finding_id", ""),
            finding_type=FindingType(data.get("finding_type", "risk")),
            description=data.get("description", ""),
            source_document=data.get("source_document", ""),
            source_documents=data.get("source_documents", []),
            severity=Severity(data.get("severity", "medium")),
            deal_impact=DealImpact(data.get("deal_impact", "noted")),
            clause_reference=data.get("clause_reference"),
            evidence_quote=data.get("evidence_quote"),
            financial_exposure=financial_exposure,
            action_required=data.get("action_required"),
            related_findings=data.get("related_findings", []),
            confidence=data.get("confidence", 0.8),
            metadata=data.get("metadata", {}),
        )


def create_finding(
    description: str,
    source_document: str,
    finding_type: str = "risk",
    severity: str = "medium",
    deal_impact: str = "noted",
    **kwargs
) -> Finding:
    """
    Factory function to create a Finding with sensible defaults.
    """
    import uuid

    return Finding(
        finding_id=str(uuid.uuid4())[:8],
        finding_type=FindingType(finding_type),
        description=description,
        source_document=source_document,
        severity=Severity(severity),
        deal_impact=DealImpact(deal_impact),
        **kwargs
    )
