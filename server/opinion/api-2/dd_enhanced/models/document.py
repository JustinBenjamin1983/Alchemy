"""
Document metadata model.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import date


@dataclass
class ExtractedDate:
    """An extracted date with context."""
    date_value: Optional[date]
    date_string: str  # Original string from document
    date_type: str  # expiry, effective, execution, deadline
    context: str  # Surrounding text
    source_document: str
    is_critical: bool = False  # True if this is a deadline/expiry


@dataclass
class ExtractedAmount:
    """An extracted financial amount with context."""
    amount: float
    currency: str
    amount_string: str  # Original string
    amount_type: str  # revenue, liability, exposure, loan, fee
    context: str
    source_document: str
    calculation_possible: bool = False


@dataclass
class ExtractedParty:
    """An extracted party/entity."""
    name: str
    role: str  # borrower, lender, lessor, lessee, supplier, customer
    source_document: str


@dataclass
class ExtractedClause:
    """An extracted clause of interest."""
    clause_type: str  # change_of_control, termination, assignment, consent
    clause_reference: str  # e.g., "Clause 5.2"
    clause_text: str
    source_document: str
    triggers: List[str] = field(default_factory=list)
    consequences: List[str] = field(default_factory=list)


@dataclass
class DocumentMetadata:
    """
    Structured metadata extracted from a document.

    This is populated during Pass 1 (Extract & Index).
    """
    filename: str
    doc_type: str
    word_count: int

    # Extracted entities
    parties: List[ExtractedParty] = field(default_factory=list)
    dates: List[ExtractedDate] = field(default_factory=list)
    amounts: List[ExtractedAmount] = field(default_factory=list)
    clauses: List[ExtractedClause] = field(default_factory=list)

    # Document-specific
    effective_date: Optional[date] = None
    expiry_date: Optional[date] = None
    governing_law: Optional[str] = None

    # Summary
    ai_summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "filename": self.filename,
            "doc_type": self.doc_type,
            "word_count": self.word_count,
            "parties": [
                {"name": p.name, "role": p.role, "source": p.source_document}
                for p in self.parties
            ],
            "dates": [
                {
                    "date": d.date_value.isoformat() if d.date_value else None,
                    "string": d.date_string,
                    "type": d.date_type,
                    "context": d.context,
                    "critical": d.is_critical,
                }
                for d in self.dates
            ],
            "amounts": [
                {
                    "amount": a.amount,
                    "currency": a.currency,
                    "type": a.amount_type,
                    "context": a.context,
                }
                for a in self.amounts
            ],
            "clauses": [
                {
                    "type": c.clause_type,
                    "reference": c.clause_reference,
                    "text": c.clause_text[:500],  # Truncate for summary
                    "triggers": c.triggers,
                    "consequences": c.consequences,
                }
                for c in self.clauses
            ],
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "governing_law": self.governing_law,
            "ai_summary": self.ai_summary,
        }
