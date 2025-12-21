"""
Entity Transformer for Knowledge Graph (Phase 5)

Transforms Pass 1 extraction output into graph entities.
Reuses existing extracted data to avoid duplicate API calls.

Pass 1 outputs:
- key_dates: [{date, description, is_critical, source_document}]
- financial_figures: [{amount, currency, context, amount_type, source_document}]
- coc_clauses: [{clause_reference, trigger, consequence, source_document}]
- consent_requirements: [{consent_from, for_what, clause_reference, source_document}]
- parties: [{name, role, party_type, source_document}]
- covenants: [{description, obligor, clause_reference, source_document}]

This module transforms these into:
- PartyEntity, AgreementEntity, ObligationEntity, TriggerEntity, AmountEntity, DateEntity
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class GraphEntity:
    """Base class for all graph entities."""
    source_document_id: str
    source_document_name: str


@dataclass
class PartyEntity(GraphEntity):
    """A party (legal entity) extracted from documents."""
    name: str
    normalized_name: str
    party_type: Optional[str] = None  # company, individual, government, trust
    role: Optional[str] = None  # buyer, seller, borrower, lender
    jurisdiction: Optional[str] = None
    registration_number: Optional[str] = None


@dataclass
class AgreementEntity(GraphEntity):
    """An agreement/contract extracted from a document."""
    name: str
    agreement_type: Optional[str] = None
    effective_date: Optional[str] = None
    expiry_date: Optional[str] = None
    governing_law: Optional[str] = None
    has_change_of_control: bool = False
    has_assignment_restriction: bool = False
    has_consent_requirement: bool = False
    parties: List[str] = field(default_factory=list)


@dataclass
class ObligationEntity(GraphEntity):
    """An obligation or commitment from a document."""
    description: str
    obligation_type: Optional[str] = None  # payment, delivery, consent, notification
    obligor: Optional[str] = None
    obligee: Optional[str] = None
    clause_reference: Optional[str] = None
    due_date: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    is_material: bool = False


@dataclass
class TriggerEntity(GraphEntity):
    """A triggering event (CoC, default, etc.)."""
    trigger_type: str  # change_of_control, default, termination, expiry, breach
    description: str
    clause_reference: Optional[str] = None
    threshold: Optional[str] = None
    consequences: Optional[str] = None
    affected_obligations: List[str] = field(default_factory=list)


@dataclass
class AmountEntity(GraphEntity):
    """A monetary amount from a document."""
    value: float
    currency: str
    context: str
    amount_type: Optional[str] = None  # principal, limit, fee, penalty
    clause_reference: Optional[str] = None


@dataclass
class DateEntity(GraphEntity):
    """A significant date from a document."""
    date_value: Optional[str] = None  # YYYY-MM-DD format
    date_description: Optional[str] = None  # For relative dates
    significance: Optional[str] = None
    date_type: Optional[str] = None  # effective, expiry, deadline
    is_critical: bool = False


@dataclass
class DocumentEntities:
    """All entities extracted from a single document."""
    document_id: str
    document_name: str
    folder_category: Optional[str]
    document_type: Optional[str]

    parties: List[PartyEntity] = field(default_factory=list)
    agreements: List[AgreementEntity] = field(default_factory=list)
    obligations: List[ObligationEntity] = field(default_factory=list)
    triggers: List[TriggerEntity] = field(default_factory=list)
    amounts: List[AmountEntity] = field(default_factory=list)
    dates: List[DateEntity] = field(default_factory=list)

    # Cross-references found in this document
    cross_references: List[str] = field(default_factory=list)


class EntityTransformer:
    """
    Transforms Pass 1 extraction output into graph entities.

    This is the key cost-saving component - it reuses Pass 1 data
    instead of making new API calls for entity extraction.
    """

    def __init__(self):
        self._party_normalizer = PartyNameNormalizer()

    def transform_document(
        self,
        document: Dict[str, Any],
        pass1_extraction: Dict[str, Any]
    ) -> DocumentEntities:
        """
        Transform Pass 1 extraction for a document into graph entities.

        Args:
            document: Document dict with id, original_file_name, folder_category, etc.
            pass1_extraction: Pass 1 output for this document

        Returns:
            DocumentEntities with all extracted entities
        """
        doc_id = str(document.get('id', ''))
        doc_name = document.get('original_file_name', document.get('filename', 'Unknown'))
        folder_category = document.get('folder_category', '')
        doc_type = document.get('ai_document_type', document.get('doc_type', ''))

        entities = DocumentEntities(
            document_id=doc_id,
            document_name=doc_name,
            folder_category=folder_category,
            document_type=doc_type
        )

        # Transform parties
        entities.parties = self._transform_parties(
            pass1_extraction.get('parties', []),
            doc_id, doc_name
        )

        # Transform financial figures to amounts
        entities.amounts = self._transform_amounts(
            pass1_extraction.get('financial_figures', []),
            doc_id, doc_name
        )

        # Transform key dates
        entities.dates = self._transform_dates(
            pass1_extraction.get('key_dates', []),
            doc_id, doc_name
        )

        # Transform CoC clauses to triggers
        entities.triggers = self._transform_coc_to_triggers(
            pass1_extraction.get('coc_clauses', []),
            doc_id, doc_name
        )

        # Transform consent requirements to triggers + obligations
        consent_triggers, consent_obligations = self._transform_consent_requirements(
            pass1_extraction.get('consent_requirements', []),
            doc_id, doc_name
        )
        entities.triggers.extend(consent_triggers)
        entities.obligations.extend(consent_obligations)

        # Transform covenants to obligations
        entities.obligations.extend(self._transform_covenants(
            pass1_extraction.get('covenants', []),
            doc_id, doc_name
        ))

        # Create agreement entity from document metadata and extraction
        agreement = self._create_agreement_from_document(
            document, pass1_extraction, doc_id, doc_name
        )
        if agreement:
            entities.agreements.append(agreement)

        return entities

    def _transform_parties(
        self,
        parties: List[Dict],
        doc_id: str,
        doc_name: str
    ) -> List[PartyEntity]:
        """Transform Pass 1 parties to PartyEntity objects."""
        result = []

        for party in parties:
            name = party.get('name', '').strip()
            if not name:
                continue

            normalized = self._party_normalizer.normalize(name)

            result.append(PartyEntity(
                source_document_id=doc_id,
                source_document_name=doc_name,
                name=name,
                normalized_name=normalized,
                party_type=party.get('party_type', party.get('type')),
                role=party.get('role'),
                jurisdiction=party.get('jurisdiction'),
                registration_number=party.get('registration_number', party.get('reg_number'))
            ))

        return result

    def _transform_amounts(
        self,
        figures: List[Dict],
        doc_id: str,
        doc_name: str
    ) -> List[AmountEntity]:
        """Transform Pass 1 financial_figures to AmountEntity objects."""
        result = []

        for fig in figures:
            # Handle different field names from Pass 1
            amount = fig.get('amount', fig.get('value'))
            if amount is None:
                continue

            # Parse amount if it's a string
            if isinstance(amount, str):
                amount = self._parse_amount_string(amount)
                if amount is None:
                    continue

            result.append(AmountEntity(
                source_document_id=doc_id,
                source_document_name=doc_name,
                value=float(amount),
                currency=fig.get('currency', 'ZAR'),
                context=fig.get('context', fig.get('description', '')),
                amount_type=fig.get('amount_type', fig.get('type')),
                clause_reference=fig.get('clause_reference', fig.get('clause'))
            ))

        return result

    def _transform_dates(
        self,
        dates: List[Dict],
        doc_id: str,
        doc_name: str
    ) -> List[DateEntity]:
        """Transform Pass 1 key_dates to DateEntity objects."""
        result = []

        for date_item in dates:
            date_str = date_item.get('date', date_item.get('date_value'))
            description = date_item.get('description', date_item.get('significance', ''))

            # Try to parse the date
            parsed_date = self._parse_date_string(date_str) if date_str else None

            result.append(DateEntity(
                source_document_id=doc_id,
                source_document_name=doc_name,
                date_value=parsed_date,
                date_description=date_str if not parsed_date else None,
                significance=description,
                date_type=date_item.get('date_type', date_item.get('type')),
                is_critical=date_item.get('is_critical', False)
            ))

        return result

    def _transform_coc_to_triggers(
        self,
        coc_clauses: List[Dict],
        doc_id: str,
        doc_name: str
    ) -> List[TriggerEntity]:
        """Transform Pass 1 coc_clauses to TriggerEntity objects."""
        result = []

        for coc in coc_clauses:
            trigger_desc = coc.get('trigger', coc.get('description', 'Change of control'))
            consequences = coc.get('consequence', coc.get('consequences', ''))

            result.append(TriggerEntity(
                source_document_id=doc_id,
                source_document_name=doc_name,
                trigger_type='change_of_control',
                description=trigger_desc,
                clause_reference=coc.get('clause_reference', coc.get('clause')),
                threshold=coc.get('threshold'),
                consequences=consequences,
                affected_obligations=coc.get('affected_obligations', [])
            ))

        return result

    def _transform_consent_requirements(
        self,
        consent_reqs: List[Dict],
        doc_id: str,
        doc_name: str
    ) -> tuple:
        """
        Transform Pass 1 consent_requirements to triggers and obligations.

        Returns:
            Tuple of (triggers, obligations)
        """
        triggers = []
        obligations = []

        for req in consent_reqs:
            consent_from = req.get('consent_from', req.get('party', ''))
            for_what = req.get('for_what', req.get('action', req.get('description', '')))

            # Create a trigger for the consent requirement
            triggers.append(TriggerEntity(
                source_document_id=doc_id,
                source_document_name=doc_name,
                trigger_type='consent_required',
                description=f"Consent required from {consent_from} for {for_what}",
                clause_reference=req.get('clause_reference', req.get('clause')),
                threshold=None,
                consequences=f"Transaction blocked without consent from {consent_from}",
                affected_obligations=[]
            ))

            # Also create an obligation to obtain consent
            obligations.append(ObligationEntity(
                source_document_id=doc_id,
                source_document_name=doc_name,
                description=f"Obtain consent from {consent_from} for {for_what}",
                obligation_type='consent',
                obligor=None,  # Usually the buyer in M&A context
                obligee=consent_from,
                clause_reference=req.get('clause_reference', req.get('clause')),
                is_material=True  # Consent requirements are typically material
            ))

        return triggers, obligations

    def _transform_covenants(
        self,
        covenants: List[Dict],
        doc_id: str,
        doc_name: str
    ) -> List[ObligationEntity]:
        """Transform Pass 1 covenants to ObligationEntity objects."""
        result = []

        for covenant in covenants:
            description = covenant.get('description', covenant.get('covenant', ''))
            if not description:
                continue

            result.append(ObligationEntity(
                source_document_id=doc_id,
                source_document_name=doc_name,
                description=description,
                obligation_type=covenant.get('type', 'compliance'),
                obligor=covenant.get('obligor'),
                obligee=covenant.get('obligee', covenant.get('beneficiary')),
                clause_reference=covenant.get('clause_reference', covenant.get('clause')),
                due_date=covenant.get('due_date'),
                amount=covenant.get('amount'),
                currency=covenant.get('currency'),
                is_material=covenant.get('is_material', False)
            ))

        return result

    def _create_agreement_from_document(
        self,
        document: Dict[str, Any],
        pass1_extraction: Dict[str, Any],
        doc_id: str,
        doc_name: str
    ) -> Optional[AgreementEntity]:
        """
        Create an AgreementEntity from document metadata and Pass 1 extraction.
        """
        doc_type = document.get('ai_document_type', document.get('doc_type', ''))

        # Determine agreement type from document type
        agreement_type = self._map_doc_type_to_agreement_type(doc_type)

        # Check for CoC, assignment, consent flags
        has_coc = len(pass1_extraction.get('coc_clauses', [])) > 0
        has_consent = len(pass1_extraction.get('consent_requirements', [])) > 0

        # Extract dates
        dates = pass1_extraction.get('key_dates', [])
        effective_date = None
        expiry_date = None

        for date_item in dates:
            date_type = date_item.get('date_type', date_item.get('type', '')).lower()
            date_str = date_item.get('date', date_item.get('date_value'))

            if 'effective' in date_type or 'commencement' in date_type:
                effective_date = self._parse_date_string(date_str)
            elif 'expiry' in date_type or 'termination' in date_type or 'end' in date_type:
                expiry_date = self._parse_date_string(date_str)

        # Get party names
        party_names = [p.get('name', '') for p in pass1_extraction.get('parties', [])]

        return AgreementEntity(
            source_document_id=doc_id,
            source_document_name=doc_name,
            name=doc_name,  # Use document name as agreement name
            agreement_type=agreement_type,
            effective_date=effective_date,
            expiry_date=expiry_date,
            governing_law=None,  # Would need relationship enrichment to extract
            has_change_of_control=has_coc,
            has_assignment_restriction=False,  # Would need enrichment
            has_consent_requirement=has_consent,
            parties=party_names
        )

    def _map_doc_type_to_agreement_type(self, doc_type: str) -> str:
        """Map document type to agreement type."""
        doc_type_lower = doc_type.lower() if doc_type else ''

        mapping = {
            'loan': 'loan',
            'facility': 'loan',
            'credit': 'loan',
            'shareholders': 'shareholders',
            'sha': 'shareholders',
            'lease': 'lease',
            'rental': 'lease',
            'supply': 'supply',
            'offtake': 'offtake',
            'service': 'service',
            'employment': 'employment',
            'guarantee': 'guarantee',
            'suretyship': 'guarantee',
            'mortgage': 'security',
            'pledge': 'security',
            'cession': 'security',
            'mining right': 'mining_right',
            'prospecting': 'mining_right',
            'environmental': 'environmental',
            'water use': 'environmental',
            'moi': 'constitutional',
            'constitution': 'constitutional',
            'resolution': 'corporate',
            'power of attorney': 'corporate',
        }

        for keyword, agreement_type in mapping.items():
            if keyword in doc_type_lower:
                return agreement_type

        return 'other'

    def _parse_amount_string(self, amount_str: str) -> Optional[float]:
        """Parse an amount string to a float."""
        if not amount_str:
            return None

        # Remove currency symbols and whitespace
        cleaned = re.sub(r'[R$€£,\s]', '', str(amount_str))

        # Handle million/billion suffixes
        multiplier = 1
        if 'm' in cleaned.lower():
            multiplier = 1_000_000
            cleaned = re.sub(r'[mM].*', '', cleaned)
        elif 'b' in cleaned.lower():
            multiplier = 1_000_000_000
            cleaned = re.sub(r'[bB].*', '', cleaned)

        try:
            return float(cleaned) * multiplier
        except ValueError:
            return None

    def _parse_date_string(self, date_str: str) -> Optional[str]:
        """Parse a date string to YYYY-MM-DD format."""
        if not date_str:
            return None

        # Common date formats
        formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y/%m/%d',
            '%d %B %Y',
            '%d %b %Y',
            '%B %d, %Y',
            '%b %d, %Y',
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        return None


class PartyNameNormalizer:
    """
    Normalizes party names for deduplication across documents.

    "ABC Pty Ltd" and "ABC (Proprietary) Limited" should match.
    """

    # Suffixes to remove for normalization
    SUFFIXES = [
        r'\s*\(Pty\)\s*Ltd\.?',
        r'\s*\(Proprietary\)\s*Limited',
        r'\s*Proprietary\s*Limited',
        r'\s*Pty\s*Ltd\.?',
        r'\s*Limited',
        r'\s*Ltd\.?',
        r'\s*Inc\.?',
        r'\s*Incorporated',
        r'\s*LLC',
        r'\s*LLP',
        r'\s*PLC',
        r'\s*SA\s*$',
        r'\s*NPC',
        r'\s*RF\s*$',
        r'\s*\(RF\)',
        r'\s*\(NPC\)',
        r'\s*CC\s*$',  # Close Corporation
    ]

    def normalize(self, name: str) -> str:
        """
        Normalize a party name for matching.

        Args:
            name: Original party name

        Returns:
            Normalized name (lowercase, no suffixes, single spaces)
        """
        if not name:
            return ''

        normalized = name.strip()

        # Remove suffixes
        for suffix_pattern in self.SUFFIXES:
            normalized = re.sub(suffix_pattern, '', normalized, flags=re.IGNORECASE)

        # Lowercase
        normalized = normalized.lower()

        # Remove extra whitespace
        normalized = ' '.join(normalized.split())

        # Remove trailing punctuation
        normalized = normalized.rstrip('.,;:')

        return normalized


def transform_all_documents(
    documents: List[Dict[str, Any]],
    pass1_results: Dict[str, Any],
    progress_callback: Optional[callable] = None
) -> List[DocumentEntities]:
    """
    Transform Pass 1 results for all documents into graph entities.

    Args:
        documents: List of document dicts
        pass1_results: Pass 1 output with 'document_extractions' dict
        progress_callback: Optional callback(current, total, message)

    Returns:
        List of DocumentEntities for all documents
    """
    transformer = EntityTransformer()
    doc_extractions = pass1_results.get('document_extractions', {})

    results = []
    total = len(documents)

    for i, doc in enumerate(documents):
        doc_name = doc.get('original_file_name', doc.get('filename', ''))

        # Find extraction for this document
        extraction = doc_extractions.get(doc_name, {})

        if progress_callback:
            progress_callback(i + 1, total, f"Transforming: {doc_name}")

        try:
            entities = transformer.transform_document(doc, extraction)
            results.append(entities)
        except Exception as e:
            logger.warning(f"Failed to transform entities for {doc_name}: {e}")
            # Create empty entities for failed documents
            results.append(DocumentEntities(
                document_id=str(doc.get('id', '')),
                document_name=doc_name,
                folder_category=doc.get('folder_category'),
                document_type=doc.get('ai_document_type')
            ))

    return results
