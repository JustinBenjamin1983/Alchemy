"""
Graph Builder for Knowledge Graph (Phase 5)

Populates the relational graph tables from extracted entities.
Handles deduplication, relationship creation, and progress tracking.
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
import uuid
import logging
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from .entity_transformer import (
    DocumentEntities,
    PartyEntity,
    AgreementEntity,
    ObligationEntity,
    TriggerEntity,
    AmountEntity,
    DateEntity,
)
from .relationship_enricher import RelationshipEnrichment

logger = logging.getLogger(__name__)


@dataclass
class GraphStats:
    """Statistics about the built graph."""
    parties: int = 0
    agreements: int = 0
    obligations: int = 0
    triggers: int = 0
    amounts: int = 0
    dates: int = 0
    edges: int = 0
    documents_processed: int = 0
    errors: int = 0


class KnowledgeGraphBuilder:
    """
    Builds the knowledge graph from extracted entities.

    Responsibilities:
    - Deduplicate parties by normalized name
    - Create vertices (nodes) in kg_* tables
    - Create edges (relationships) in kg_edge_* tables
    - Track build progress
    """

    def __init__(self, db_session: Session, dd_id: str, run_id: Optional[str] = None):
        self.db = db_session
        self.dd_id = dd_id
        self.run_id = run_id

        # Cache for deduplication
        self._party_cache: Dict[str, str] = {}  # normalized_name -> party_id
        self._agreement_cache: Dict[str, str] = {}  # document_id -> agreement_id
        self._document_cache: Dict[str, str] = {}  # document_name -> document_id

    def clear_existing_graph(self) -> None:
        """
        Clear existing graph data for this DD before rebuilding.
        Called when rebuilding the graph from scratch.
        """
        logger.info(f"Clearing existing graph for DD {self.dd_id}")

        # Delete in reverse dependency order
        tables_to_clear = [
            'kg_edge_secures',
            'kg_edge_conflicts_with',
            'kg_edge_references',
            'kg_edge_requires_consent',
            'kg_edge_triggers',
            'kg_edge_party_to',
            'kg_date',
            'kg_amount',
            'kg_trigger',
            'kg_obligation',
            'kg_agreement',
            'kg_party',
            'kg_build_status',
        ]

        for table in tables_to_clear:
            self.db.execute(
                text(f"DELETE FROM {table} WHERE dd_id = :dd_id"),
                {'dd_id': self.dd_id}
            )

        self.db.commit()
        logger.info(f"Cleared graph data from {len(tables_to_clear)} tables")

    def build_graph(
        self,
        document_entities: List[DocumentEntities],
        enrichments: Optional[List[RelationshipEnrichment]] = None,
        progress_callback: Optional[callable] = None
    ) -> GraphStats:
        """
        Build the knowledge graph from extracted entities.

        Args:
            document_entities: List of DocumentEntities from entity transformer
            enrichments: Optional relationship enrichments from Claude
            progress_callback: Optional callback(current, total, message)

        Returns:
            GraphStats with counts of created nodes and edges
        """
        stats = GraphStats()
        total_docs = len(document_entities)

        # Create build status record
        build_status_id = self._create_build_status(total_docs)

        # Build enrichment lookup if provided
        enrichment_lookup: Dict[str, RelationshipEnrichment] = {}
        if enrichments:
            for e in enrichments:
                enrichment_lookup[e.document_id] = e

        logger.info(f"Building graph for {total_docs} documents")

        try:
            for i, doc_entities in enumerate(document_entities):
                if progress_callback:
                    progress_callback(
                        i + 1,
                        total_docs,
                        f"Building graph: {doc_entities.document_name}"
                    )

                try:
                    doc_stats = self._process_document(
                        doc_entities,
                        enrichment_lookup.get(doc_entities.document_id)
                    )
                    stats.parties += doc_stats.parties
                    stats.agreements += doc_stats.agreements
                    stats.obligations += doc_stats.obligations
                    stats.triggers += doc_stats.triggers
                    stats.amounts += doc_stats.amounts
                    stats.dates += doc_stats.dates
                    stats.edges += doc_stats.edges
                    stats.documents_processed += 1
                except Exception as e:
                    logger.error(f"Error processing {doc_entities.document_name}: {e}")
                    stats.errors += 1

                # Commit periodically to avoid large transactions
                if (i + 1) % 50 == 0:
                    self.db.commit()
                    self._update_build_status(build_status_id, stats)

            # Resolve cross-references after all documents processed
            refs_resolved = self._resolve_cross_references(enrichments or [])
            stats.edges += refs_resolved

            # Final commit
            self.db.commit()

            # Update build status to completed
            self._complete_build_status(build_status_id, stats)

            logger.info(f"Graph build complete: {stats}")

        except Exception as e:
            logger.error(f"Graph build failed: {e}")
            self._fail_build_status(build_status_id, str(e))
            raise

        return stats

    def _process_document(
        self,
        doc_entities: DocumentEntities,
        enrichment: Optional[RelationshipEnrichment]
    ) -> GraphStats:
        """Process a single document's entities into the graph."""
        stats = GraphStats()

        # Process parties (with deduplication)
        party_ids = self._process_parties(doc_entities.parties)
        stats.parties = len([p for p in party_ids.values() if p])

        # Process agreement
        agreement_id = None
        if doc_entities.agreements:
            agreement = doc_entities.agreements[0]

            # Merge enrichment data
            if enrichment:
                if enrichment.governing_law:
                    agreement.governing_law = enrichment.governing_law
                if enrichment.has_assignment_restriction:
                    agreement.has_assignment_restriction = True

            agreement_id = self._create_agreement(agreement, doc_entities.document_id)
            if agreement_id:
                stats.agreements = 1

                # Create PARTY_TO edges for agreement parties
                for party_name in agreement.parties:
                    normalized = self._normalize_party_name(party_name)
                    party_id = party_ids.get(normalized) or self._party_cache.get(normalized)
                    if party_id:
                        self._create_party_to_edge(party_id, 'agreement', agreement_id, doc_entities.document_id)
                        stats.edges += 1

        # Process obligations
        for obligation in doc_entities.obligations:
            obligation_id = self._create_obligation(
                obligation,
                doc_entities.document_id,
                agreement_id,
                party_ids
            )
            if obligation_id:
                stats.obligations += 1

        # Process triggers
        for trigger in doc_entities.triggers:
            trigger_id = self._create_trigger(
                trigger,
                doc_entities.document_id,
                agreement_id
            )
            if trigger_id:
                stats.triggers += 1

        # Process additional triggers from enrichment
        if enrichment:
            for trigger_data in enrichment.additional_triggers:
                trigger = TriggerEntity(
                    source_document_id=doc_entities.document_id,
                    source_document_name=doc_entities.document_name,
                    trigger_type=trigger_data.get('trigger_type', 'other'),
                    description=trigger_data.get('description', ''),
                    clause_reference=trigger_data.get('clause_reference')
                )
                trigger_id = self._create_trigger(trigger, doc_entities.document_id, agreement_id)
                if trigger_id:
                    stats.triggers += 1

        # Process amounts
        for amount in doc_entities.amounts:
            amount_id = self._create_amount(amount, doc_entities.document_id)
            if amount_id:
                stats.amounts += 1

        # Process dates
        for date in doc_entities.dates:
            date_id = self._create_date(date, doc_entities.document_id)
            if date_id:
                stats.dates += 1

        return stats

    def _process_parties(self, parties: List[PartyEntity]) -> Dict[str, str]:
        """Process parties with deduplication. Returns normalized_name -> party_id mapping."""
        party_ids = {}

        for party in parties:
            normalized = party.normalized_name

            # Check cache first
            if normalized in self._party_cache:
                party_ids[normalized] = self._party_cache[normalized]
                # Update source_documents array
                self._add_party_source_document(
                    self._party_cache[normalized],
                    party.source_document_id
                )
                continue

            # Check database
            result = self.db.execute(
                text("""
                    SELECT id FROM kg_party
                    WHERE dd_id = :dd_id AND normalized_name = :normalized_name
                """),
                {'dd_id': self.dd_id, 'normalized_name': normalized}
            ).fetchone()

            if result:
                party_id = str(result[0])
                self._add_party_source_document(party_id, party.source_document_id)
            else:
                # Create new party
                party_id = str(uuid.uuid4())
                self.db.execute(
                    text("""
                        INSERT INTO kg_party (id, dd_id, run_id, name, normalized_name, party_type, role,
                                             jurisdiction, registration_number, first_seen_document_id, source_documents)
                        VALUES (:id, :dd_id, :run_id, :name, :normalized_name, :party_type, :role,
                                :jurisdiction, :registration_number, :first_seen_document_id, :source_documents)
                    """),
                    {
                        'id': party_id,
                        'dd_id': self.dd_id,
                        'run_id': self.run_id,
                        'name': party.name,
                        'normalized_name': normalized,
                        'party_type': party.party_type,
                        'role': party.role,
                        'jurisdiction': party.jurisdiction,
                        'registration_number': party.registration_number,
                        'first_seen_document_id': party.source_document_id or None,
                        'source_documents': f'["{party.source_document_id}"]' if party.source_document_id else '[]'
                    }
                )

            self._party_cache[normalized] = party_id
            party_ids[normalized] = party_id

        return party_ids

    def _add_party_source_document(self, party_id: str, document_id: str) -> None:
        """Add a document to a party's source_documents array."""
        if not document_id:
            return

        self.db.execute(
            text("""
                UPDATE kg_party
                SET source_documents = source_documents || :doc_id::jsonb
                WHERE id = :party_id
                AND NOT source_documents @> :doc_id::jsonb
            """),
            {'party_id': party_id, 'doc_id': f'["{document_id}"]'}
        )

    def _create_agreement(
        self,
        agreement: AgreementEntity,
        document_id: str
    ) -> Optional[str]:
        """Create an agreement node."""
        agreement_id = str(uuid.uuid4())

        self.db.execute(
            text("""
                INSERT INTO kg_agreement (id, dd_id, run_id, document_id, name, agreement_type,
                                         effective_date, expiry_date, governing_law,
                                         has_change_of_control, has_assignment_restriction, has_consent_requirement)
                VALUES (:id, :dd_id, :run_id, :document_id, :name, :agreement_type,
                        :effective_date, :expiry_date, :governing_law,
                        :has_change_of_control, :has_assignment_restriction, :has_consent_requirement)
            """),
            {
                'id': agreement_id,
                'dd_id': self.dd_id,
                'run_id': self.run_id,
                'document_id': document_id or None,
                'name': agreement.name,
                'agreement_type': agreement.agreement_type,
                'effective_date': agreement.effective_date,
                'expiry_date': agreement.expiry_date,
                'governing_law': agreement.governing_law,
                'has_change_of_control': agreement.has_change_of_control,
                'has_assignment_restriction': agreement.has_assignment_restriction,
                'has_consent_requirement': agreement.has_consent_requirement
            }
        )

        self._agreement_cache[document_id] = agreement_id
        return agreement_id

    def _create_obligation(
        self,
        obligation: ObligationEntity,
        document_id: str,
        agreement_id: Optional[str],
        party_ids: Dict[str, str]
    ) -> Optional[str]:
        """Create an obligation node."""
        obligation_id = str(uuid.uuid4())

        # Try to find obligor/obligee party IDs
        obligor_id = None
        obligee_id = None
        if obligation.obligor:
            normalized = self._normalize_party_name(obligation.obligor)
            obligor_id = party_ids.get(normalized) or self._party_cache.get(normalized)
        if obligation.obligee:
            normalized = self._normalize_party_name(obligation.obligee)
            obligee_id = party_ids.get(normalized) or self._party_cache.get(normalized)

        self.db.execute(
            text("""
                INSERT INTO kg_obligation (id, dd_id, run_id, document_id, agreement_id, description,
                                          obligation_type, obligor_party_id, obligee_party_id,
                                          clause_reference, due_date, due_date_description,
                                          amount, currency, is_material)
                VALUES (:id, :dd_id, :run_id, :document_id, :agreement_id, :description,
                        :obligation_type, :obligor_party_id, :obligee_party_id,
                        :clause_reference, :due_date, :due_date_description,
                        :amount, :currency, :is_material)
            """),
            {
                'id': obligation_id,
                'dd_id': self.dd_id,
                'run_id': self.run_id,
                'document_id': document_id or None,
                'agreement_id': agreement_id,
                'description': obligation.description,
                'obligation_type': obligation.obligation_type,
                'obligor_party_id': obligor_id,
                'obligee_party_id': obligee_id,
                'clause_reference': obligation.clause_reference,
                'due_date': obligation.due_date if self._is_valid_date(obligation.due_date) else None,
                'due_date_description': obligation.due_date if not self._is_valid_date(obligation.due_date) else None,
                'amount': obligation.amount,
                'currency': obligation.currency,
                'is_material': obligation.is_material
            }
        )

        return obligation_id

    def _create_trigger(
        self,
        trigger: TriggerEntity,
        document_id: str,
        agreement_id: Optional[str]
    ) -> Optional[str]:
        """Create a trigger node."""
        trigger_id = str(uuid.uuid4())

        self.db.execute(
            text("""
                INSERT INTO kg_trigger (id, dd_id, run_id, document_id, agreement_id, trigger_type,
                                       description, clause_reference, threshold_description, consequences)
                VALUES (:id, :dd_id, :run_id, :document_id, :agreement_id, :trigger_type,
                        :description, :clause_reference, :threshold_description, :consequences)
            """),
            {
                'id': trigger_id,
                'dd_id': self.dd_id,
                'run_id': self.run_id,
                'document_id': document_id or None,
                'agreement_id': agreement_id,
                'trigger_type': trigger.trigger_type,
                'description': trigger.description,
                'clause_reference': trigger.clause_reference,
                'threshold_description': trigger.threshold,
                'consequences': trigger.consequences
            }
        )

        return trigger_id

    def _create_amount(
        self,
        amount: AmountEntity,
        document_id: str
    ) -> Optional[str]:
        """Create an amount node."""
        amount_id = str(uuid.uuid4())

        self.db.execute(
            text("""
                INSERT INTO kg_amount (id, dd_id, run_id, document_id, value, currency,
                                      context, amount_type, clause_reference)
                VALUES (:id, :dd_id, :run_id, :document_id, :value, :currency,
                        :context, :amount_type, :clause_reference)
            """),
            {
                'id': amount_id,
                'dd_id': self.dd_id,
                'run_id': self.run_id,
                'document_id': document_id or None,
                'value': amount.value,
                'currency': amount.currency,
                'context': amount.context,
                'amount_type': amount.amount_type,
                'clause_reference': amount.clause_reference
            }
        )

        return amount_id

    def _create_date(
        self,
        date: DateEntity,
        document_id: str
    ) -> Optional[str]:
        """Create a date node."""
        date_id = str(uuid.uuid4())

        self.db.execute(
            text("""
                INSERT INTO kg_date (id, dd_id, run_id, document_id, date_value,
                                    date_description, significance, date_type, is_critical)
                VALUES (:id, :dd_id, :run_id, :document_id, :date_value,
                        :date_description, :significance, :date_type, :is_critical)
            """),
            {
                'id': date_id,
                'dd_id': self.dd_id,
                'run_id': self.run_id,
                'document_id': document_id or None,
                'date_value': date.date_value,
                'date_description': date.date_description,
                'significance': date.significance,
                'date_type': date.date_type,
                'is_critical': date.is_critical
            }
        )

        return date_id

    def _create_party_to_edge(
        self,
        party_id: str,
        target_type: str,
        target_id: str,
        document_id: Optional[str] = None
    ) -> None:
        """Create a PARTY_TO edge."""
        self.db.execute(
            text("""
                INSERT INTO kg_edge_party_to (dd_id, party_id, target_type, agreement_id, document_id, role)
                VALUES (:dd_id, :party_id, :target_type, :agreement_id, :document_id, NULL)
                ON CONFLICT (party_id, target_type, document_id, agreement_id) DO NOTHING
            """),
            {
                'dd_id': self.dd_id,
                'party_id': party_id,
                'target_type': target_type,
                'agreement_id': target_id if target_type == 'agreement' else None,
                'document_id': document_id if target_type == 'document' else target_id
            }
        )

    def _resolve_cross_references(
        self,
        enrichments: List[RelationshipEnrichment]
    ) -> int:
        """
        Resolve cross-references to actual document/agreement IDs.
        Returns count of edges created.
        """
        edges_created = 0

        # Build document name -> ID lookup
        doc_lookup = {}
        result = self.db.execute(
            text("""
                SELECT d.id, d.original_file_name, a.id as agreement_id
                FROM document d
                JOIN folder f ON d.folder_id = f.id
                LEFT JOIN kg_agreement a ON a.document_id = d.id
                WHERE f.dd_id = :dd_id
            """),
            {'dd_id': self.dd_id}
        ).fetchall()

        for row in result:
            doc_name = row[1].lower() if row[1] else ''
            doc_lookup[doc_name] = {
                'document_id': str(row[0]),
                'agreement_id': str(row[2]) if row[2] else None
            }

        # Process each enrichment's cross-references
        for enrichment in enrichments:
            source_doc_id = enrichment.document_id

            for ref in enrichment.cross_references:
                ref_text = ref.get('reference_text', '').lower()
                ref_type = ref.get('reference_type', 'refers_to')
                likely_type = ref.get('likely_document_type', '').lower()

                # Try to find the target document
                target_doc = self._find_referenced_document(
                    ref_text, likely_type, doc_lookup
                )

                if target_doc:
                    self.db.execute(
                        text("""
                            INSERT INTO kg_edge_references (dd_id, source_document_id, target_document_id,
                                                           source_agreement_id, target_agreement_id,
                                                           reference_type, reference_text)
                            VALUES (:dd_id, :source_doc, :target_doc,
                                    :source_agreement, :target_agreement,
                                    :ref_type, :ref_text)
                        """),
                        {
                            'dd_id': self.dd_id,
                            'source_doc': source_doc_id,
                            'target_doc': target_doc.get('document_id'),
                            'source_agreement': self._agreement_cache.get(source_doc_id),
                            'target_agreement': target_doc.get('agreement_id'),
                            'ref_type': ref_type,
                            'ref_text': ref.get('reference_text', '')[:500]
                        }
                    )
                    edges_created += 1

        return edges_created

    def _find_referenced_document(
        self,
        ref_text: str,
        likely_type: str,
        doc_lookup: Dict[str, Dict]
    ) -> Optional[Dict]:
        """Find a document that matches a cross-reference."""
        # Simple matching - look for document names in the reference text
        for doc_name, doc_info in doc_lookup.items():
            # Check if document name appears in reference text
            if doc_name and doc_name in ref_text:
                return doc_info

            # Check if likely_type matches document name
            if likely_type and likely_type in doc_name:
                return doc_info

        return None

    def _normalize_party_name(self, name: str) -> str:
        """Normalize a party name for matching."""
        import re
        if not name:
            return ''

        normalized = name.strip()

        # Remove common suffixes
        suffixes = [
            r'\s*\(Pty\)\s*Ltd\.?',
            r'\s*\(Proprietary\)\s*Limited',
            r'\s*Pty\s*Ltd\.?',
            r'\s*Limited',
            r'\s*Ltd\.?',
        ]
        for suffix in suffixes:
            normalized = re.sub(suffix, '', normalized, flags=re.IGNORECASE)

        return ' '.join(normalized.lower().split())

    def _is_valid_date(self, date_str: Optional[str]) -> bool:
        """Check if a string is a valid YYYY-MM-DD date."""
        if not date_str:
            return False
        import re
        return bool(re.match(r'^\d{4}-\d{2}-\d{2}$', date_str))

    def _create_build_status(self, total_docs: int) -> str:
        """Create a build status record."""
        status_id = str(uuid.uuid4())

        self.db.execute(
            text("""
                INSERT INTO kg_build_status (id, dd_id, run_id, status, total_documents, started_at)
                VALUES (:id, :dd_id, :run_id, 'building', :total_docs, NOW())
                ON CONFLICT (dd_id, run_id) DO UPDATE SET
                    status = 'building',
                    total_documents = :total_docs,
                    started_at = NOW(),
                    error_message = NULL
            """),
            {
                'id': status_id,
                'dd_id': self.dd_id,
                'run_id': self.run_id,
                'total_docs': total_docs
            }
        )
        self.db.commit()

        return status_id

    def _update_build_status(self, status_id: str, stats: GraphStats) -> None:
        """Update build status with current stats."""
        self.db.execute(
            text("""
                UPDATE kg_build_status SET
                    party_count = :parties,
                    agreement_count = :agreements,
                    obligation_count = :obligations,
                    trigger_count = :triggers,
                    amount_count = :amounts,
                    date_count = :dates,
                    edge_count = :edges,
                    documents_processed = :docs_processed,
                    updated_at = NOW()
                WHERE id = :status_id
            """),
            {
                'status_id': status_id,
                'parties': stats.parties,
                'agreements': stats.agreements,
                'obligations': stats.obligations,
                'triggers': stats.triggers,
                'amounts': stats.amounts,
                'dates': stats.dates,
                'edges': stats.edges,
                'docs_processed': stats.documents_processed
            }
        )

    def _complete_build_status(self, status_id: str, stats: GraphStats) -> None:
        """Mark build status as completed."""
        self.db.execute(
            text("""
                UPDATE kg_build_status SET
                    status = 'completed',
                    party_count = :parties,
                    agreement_count = :agreements,
                    obligation_count = :obligations,
                    trigger_count = :triggers,
                    amount_count = :amounts,
                    date_count = :dates,
                    edge_count = :edges,
                    documents_processed = :docs_processed,
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE id = :status_id
            """),
            {
                'status_id': status_id,
                'parties': stats.parties,
                'agreements': stats.agreements,
                'obligations': stats.obligations,
                'triggers': stats.triggers,
                'amounts': stats.amounts,
                'dates': stats.dates,
                'edges': stats.edges,
                'docs_processed': stats.documents_processed
            }
        )

    def _fail_build_status(self, status_id: str, error: str) -> None:
        """Mark build status as failed."""
        self.db.execute(
            text("""
                UPDATE kg_build_status SET
                    status = 'failed',
                    error_message = :error,
                    updated_at = NOW()
                WHERE id = :status_id
            """),
            {'status_id': status_id, 'error': error[:500]}
        )
        self.db.commit()
