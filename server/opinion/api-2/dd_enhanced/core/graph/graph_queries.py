"""
Graph Query Engine for Knowledge Graph (Phase 5)

Provides query methods for DD analysis using the relational
knowledge graph. Supports:
- Party lookups and relationships
- Change of control cascade analysis
- Consent requirement discovery
- Financial exposure calculation
- Cross-document relationship traversal
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Result from a graph query."""
    success: bool
    data: Any
    error: Optional[str] = None
    query_time_ms: Optional[float] = None


@dataclass
class PartyInfo:
    """Aggregated party information."""
    party_id: int
    canonical_name: str
    all_names: List[str]
    party_types: List[str]
    document_count: int
    agreements: List[Dict[str, Any]] = field(default_factory=list)
    total_exposure: Optional[Decimal] = None


@dataclass
class CoCImpact:
    """Change of Control impact analysis result."""
    affected_agreements: List[Dict[str, Any]]
    required_consents: List[Dict[str, Any]]
    triggered_clauses: List[Dict[str, Any]]
    total_financial_exposure: Decimal
    cascade_depth: int  # How many levels of dependencies


@dataclass
class ConsentRequirement:
    """Consent requirement details."""
    agreement_id: int
    agreement_name: str
    document_id: str
    consent_type: str
    required_for: str
    threshold: Optional[str] = None
    notice_period: Optional[str] = None


class GraphQueryEngine:
    """
    Query engine for the DD knowledge graph.

    Provides efficient queries across the relational graph
    for DD analysis and reporting.
    """

    def __init__(self, connection):
        """
        Initialize with database connection.

        Args:
            connection: psycopg2 connection object
        """
        self.conn = connection

    def get_all_parties(self, dd_id: str) -> QueryResult:
        """
        Get all parties in a DD with their aggregated info.

        Returns parties with:
        - All name variations
        - Agreement counts
        - Party types
        - Total financial exposure
        """
        try:
            with self.conn.cursor() as cur:
                # Get parties with their names and types
                cur.execute("""
                    SELECT
                        p.id,
                        p.canonical_name,
                        ARRAY_AGG(DISTINCT p.name) as all_names,
                        ARRAY_AGG(DISTINCT p.party_type) FILTER (WHERE p.party_type IS NOT NULL) as party_types,
                        COUNT(DISTINCT e.agreement_id) as agreement_count
                    FROM kg_party p
                    LEFT JOIN kg_edge_party_to e ON p.id = e.party_id
                    WHERE p.dd_id = %s
                    GROUP BY p.id, p.canonical_name
                    ORDER BY agreement_count DESC, p.canonical_name
                """, (dd_id,))

                parties = []
                for row in cur.fetchall():
                    parties.append(PartyInfo(
                        party_id=row[0],
                        canonical_name=row[1],
                        all_names=row[2] or [],
                        party_types=row[3] or [],
                        document_count=row[4] or 0
                    ))

                return QueryResult(success=True, data=parties)

        except Exception as e:
            logger.error(f"Error getting parties for DD {dd_id}: {e}")
            return QueryResult(success=False, data=None, error=str(e))

    def get_party_agreements(self, party_id: int) -> QueryResult:
        """
        Get all agreements a party is involved in.

        Returns agreements with:
        - Agreement details
        - Party's role
        - Related obligations
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        a.id,
                        a.document_id,
                        a.document_name,
                        a.agreement_type,
                        a.effective_date,
                        a.expiry_date,
                        a.governing_law,
                        e.role
                    FROM kg_agreement a
                    JOIN kg_edge_party_to e ON a.id = e.agreement_id
                    WHERE e.party_id = %s
                    ORDER BY a.document_name
                """, (party_id,))

                agreements = []
                for row in cur.fetchall():
                    agreements.append({
                        'agreement_id': row[0],
                        'document_id': row[1],
                        'document_name': row[2],
                        'agreement_type': row[3],
                        'effective_date': str(row[4]) if row[4] else None,
                        'expiry_date': str(row[5]) if row[5] else None,
                        'governing_law': row[6],
                        'party_role': row[7]
                    })

                return QueryResult(success=True, data=agreements)

        except Exception as e:
            logger.error(f"Error getting agreements for party {party_id}: {e}")
            return QueryResult(success=False, data=None, error=str(e))

    def get_coc_clauses(self, dd_id: str) -> QueryResult:
        """
        Get all Change of Control clauses in a DD.

        Returns triggers with:
        - Source agreement
        - Trigger details
        - Consequences
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        t.id,
                        t.source_document_id,
                        t.source_document_name,
                        t.trigger_type,
                        t.description,
                        t.consequence,
                        t.clause_reference,
                        t.threshold,
                        t.affected_party
                    FROM kg_trigger t
                    WHERE t.dd_id = %s
                    AND LOWER(t.trigger_type) LIKE '%change%control%'
                    ORDER BY t.source_document_name
                """, (dd_id,))

                clauses = []
                for row in cur.fetchall():
                    clauses.append({
                        'trigger_id': row[0],
                        'document_id': row[1],
                        'document_name': row[2],
                        'trigger_type': row[3],
                        'description': row[4],
                        'consequence': row[5],
                        'clause_reference': row[6],
                        'threshold': row[7],
                        'affected_party': row[8]
                    })

                return QueryResult(success=True, data=clauses)

        except Exception as e:
            logger.error(f"Error getting CoC clauses for DD {dd_id}: {e}")
            return QueryResult(success=False, data=None, error=str(e))

    def get_consent_requirements(self, dd_id: str) -> QueryResult:
        """
        Get all consent requirements in a DD.

        Returns consent requirements with:
        - Source agreement
        - Consent type and threshold
        - Notice requirements
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        o.id,
                        o.source_document_id,
                        o.source_document_name,
                        o.obligation_type,
                        o.description,
                        o.threshold,
                        o.deadline,
                        e.consent_type,
                        e.required_for
                    FROM kg_obligation o
                    LEFT JOIN kg_edge_requires_consent e ON o.id = e.obligation_id
                    WHERE o.dd_id = %s
                    AND (
                        LOWER(o.obligation_type) LIKE '%consent%'
                        OR e.id IS NOT NULL
                    )
                    ORDER BY o.source_document_name
                """, (dd_id,))

                consents = []
                for row in cur.fetchall():
                    consents.append(ConsentRequirement(
                        agreement_id=row[0],
                        agreement_name=row[2],
                        document_id=row[1],
                        consent_type=row[7] or row[3],
                        required_for=row[8] or row[4],
                        threshold=row[5],
                        notice_period=row[6]
                    ))

                return QueryResult(success=True, data=consents)

        except Exception as e:
            logger.error(f"Error getting consent requirements for DD {dd_id}: {e}")
            return QueryResult(success=False, data=None, error=str(e))

    def analyze_coc_cascade(
        self,
        dd_id: str,
        target_party: Optional[str] = None
    ) -> QueryResult:
        """
        Analyze cascade effects of a Change of Control event.

        For a given party (or all parties), determines:
        - Which agreements are affected
        - What consents are required
        - Total financial exposure
        - Cascade depth (agreements that trigger other agreements)

        Args:
            dd_id: DD identifier
            target_party: Optional party name to analyze (defaults to target company)

        Returns:
            CoCImpact with full cascade analysis
        """
        try:
            with self.conn.cursor() as cur:
                # Get all CoC triggers
                cur.execute("""
                    SELECT
                        t.id,
                        t.source_document_id,
                        t.source_document_name,
                        t.description,
                        t.consequence,
                        t.threshold,
                        t.affected_party,
                        a.id as agreement_id
                    FROM kg_trigger t
                    LEFT JOIN kg_agreement a ON t.source_document_id = a.document_id
                    WHERE t.dd_id = %s
                    AND LOWER(t.trigger_type) LIKE '%change%control%'
                """, (dd_id,))

                triggered_clauses = []
                affected_agreement_ids = set()

                for row in cur.fetchall():
                    triggered_clauses.append({
                        'trigger_id': row[0],
                        'document_id': row[1],
                        'document_name': row[2],
                        'description': row[3],
                        'consequence': row[4],
                        'threshold': row[5],
                        'affected_party': row[6]
                    })
                    if row[7]:
                        affected_agreement_ids.add(row[7])

                # Get affected agreements with details
                affected_agreements = []
                if affected_agreement_ids:
                    placeholders = ','.join(['%s'] * len(affected_agreement_ids))
                    cur.execute(f"""
                        SELECT
                            a.id,
                            a.document_id,
                            a.document_name,
                            a.agreement_type,
                            a.governing_law
                        FROM kg_agreement a
                        WHERE a.id IN ({placeholders})
                    """, tuple(affected_agreement_ids))

                    for row in cur.fetchall():
                        affected_agreements.append({
                            'agreement_id': row[0],
                            'document_id': row[1],
                            'document_name': row[2],
                            'agreement_type': row[3],
                            'governing_law': row[4]
                        })

                # Get consent requirements for affected agreements
                required_consents = []
                if affected_agreement_ids:
                    placeholders = ','.join(['%s'] * len(affected_agreement_ids))
                    cur.execute(f"""
                        SELECT
                            e.id,
                            a.document_name,
                            e.consent_type,
                            e.required_for
                        FROM kg_edge_requires_consent e
                        JOIN kg_agreement a ON e.agreement_id = a.id
                        WHERE e.agreement_id IN ({placeholders})
                    """, tuple(affected_agreement_ids))

                    for row in cur.fetchall():
                        required_consents.append({
                            'consent_id': row[0],
                            'agreement_name': row[1],
                            'consent_type': row[2],
                            'required_for': row[3]
                        })

                # Calculate total financial exposure
                total_exposure = Decimal('0')
                if affected_agreement_ids:
                    placeholders = ','.join(['%s'] * len(affected_agreement_ids))
                    cur.execute(f"""
                        SELECT COALESCE(SUM(am.amount), 0)
                        FROM kg_amount am
                        JOIN kg_agreement a ON am.source_document_id = a.document_id
                        WHERE a.id IN ({placeholders})
                        AND am.dd_id = %s
                    """, tuple(affected_agreement_ids) + (dd_id,))

                    result = cur.fetchone()
                    if result and result[0]:
                        total_exposure = Decimal(str(result[0]))

                # Calculate cascade depth by checking references
                cascade_depth = 1
                cur.execute("""
                    SELECT COUNT(DISTINCT r.target_document_id)
                    FROM kg_edge_references r
                    WHERE r.dd_id = %s
                    AND r.source_document_id IN (
                        SELECT DISTINCT document_id FROM kg_agreement WHERE dd_id = %s
                    )
                """, (dd_id, dd_id))
                ref_count = cur.fetchone()[0]
                if ref_count > 0:
                    cascade_depth = 2  # At least two levels of dependencies

                impact = CoCImpact(
                    affected_agreements=affected_agreements,
                    required_consents=required_consents,
                    triggered_clauses=triggered_clauses,
                    total_financial_exposure=total_exposure,
                    cascade_depth=cascade_depth
                )

                return QueryResult(success=True, data=impact)

        except Exception as e:
            logger.error(f"Error analyzing CoC cascade for DD {dd_id}: {e}")
            return QueryResult(success=False, data=None, error=str(e))

    def get_financial_exposure(
        self,
        dd_id: str,
        by_document: bool = False,
        by_currency: bool = False
    ) -> QueryResult:
        """
        Calculate total financial exposure in a DD.

        Args:
            dd_id: DD identifier
            by_document: Group by source document
            by_currency: Group by currency

        Returns:
            Financial exposure summary
        """
        try:
            with self.conn.cursor() as cur:
                if by_document:
                    cur.execute("""
                        SELECT
                            am.source_document_name,
                            am.currency,
                            SUM(am.amount) as total,
                            COUNT(*) as count
                        FROM kg_amount am
                        WHERE am.dd_id = %s
                        GROUP BY am.source_document_name, am.currency
                        ORDER BY total DESC
                    """, (dd_id,))

                    result = []
                    for row in cur.fetchall():
                        result.append({
                            'document_name': row[0],
                            'currency': row[1],
                            'total_amount': float(row[2]) if row[2] else 0,
                            'item_count': row[3]
                        })

                elif by_currency:
                    cur.execute("""
                        SELECT
                            am.currency,
                            SUM(am.amount) as total,
                            COUNT(*) as count
                        FROM kg_amount am
                        WHERE am.dd_id = %s
                        GROUP BY am.currency
                        ORDER BY total DESC
                    """, (dd_id,))

                    result = []
                    for row in cur.fetchall():
                        result.append({
                            'currency': row[0],
                            'total_amount': float(row[1]) if row[1] else 0,
                            'item_count': row[2]
                        })

                else:
                    cur.execute("""
                        SELECT
                            COALESCE(SUM(am.amount), 0) as total,
                            COUNT(*) as count,
                            COUNT(DISTINCT am.currency) as currency_count
                        FROM kg_amount am
                        WHERE am.dd_id = %s
                    """, (dd_id,))

                    row = cur.fetchone()
                    result = {
                        'total_amount': float(row[0]) if row[0] else 0,
                        'item_count': row[1],
                        'currency_count': row[2]
                    }

                return QueryResult(success=True, data=result)

        except Exception as e:
            logger.error(f"Error calculating financial exposure for DD {dd_id}: {e}")
            return QueryResult(success=False, data=None, error=str(e))

    def get_related_documents(
        self,
        document_id: str,
        dd_id: str,
        max_depth: int = 2
    ) -> QueryResult:
        """
        Find documents related to a given document.

        Uses cross-references and shared parties to find related docs.

        Args:
            document_id: Source document ID
            dd_id: DD identifier
            max_depth: Maximum relationship depth to traverse

        Returns:
            List of related documents with relationship type
        """
        try:
            with self.conn.cursor() as cur:
                related = {}

                # Direct references
                cur.execute("""
                    SELECT
                        r.target_document_id,
                        r.reference_type,
                        a.document_name
                    FROM kg_edge_references r
                    LEFT JOIN kg_agreement a ON r.target_document_id = a.document_id
                    WHERE r.source_document_id = %s
                    AND r.dd_id = %s
                """, (document_id, dd_id))

                for row in cur.fetchall():
                    if row[0] not in related:
                        related[row[0]] = {
                            'document_id': row[0],
                            'document_name': row[2],
                            'relationships': [],
                            'depth': 1
                        }
                    related[row[0]]['relationships'].append({
                        'type': 'references',
                        'subtype': row[1]
                    })

                # Reverse references (documents that reference this one)
                cur.execute("""
                    SELECT
                        r.source_document_id,
                        r.reference_type,
                        a.document_name
                    FROM kg_edge_references r
                    LEFT JOIN kg_agreement a ON r.source_document_id = a.document_id
                    WHERE r.target_document_id = %s
                    AND r.dd_id = %s
                """, (document_id, dd_id))

                for row in cur.fetchall():
                    if row[0] not in related:
                        related[row[0]] = {
                            'document_id': row[0],
                            'document_name': row[2],
                            'relationships': [],
                            'depth': 1
                        }
                    related[row[0]]['relationships'].append({
                        'type': 'referenced_by',
                        'subtype': row[1]
                    })

                # Shared parties (documents with same parties)
                cur.execute("""
                    SELECT DISTINCT
                        a2.document_id,
                        a2.document_name,
                        p.canonical_name
                    FROM kg_agreement a1
                    JOIN kg_edge_party_to e1 ON a1.id = e1.agreement_id
                    JOIN kg_party p ON e1.party_id = p.id
                    JOIN kg_edge_party_to e2 ON p.id = e2.party_id
                    JOIN kg_agreement a2 ON e2.agreement_id = a2.id
                    WHERE a1.document_id = %s
                    AND a2.document_id != %s
                    AND a1.dd_id = %s
                """, (document_id, document_id, dd_id))

                for row in cur.fetchall():
                    if row[0] not in related:
                        related[row[0]] = {
                            'document_id': row[0],
                            'document_name': row[1],
                            'relationships': [],
                            'depth': 1
                        }
                    # Only add if not already added
                    if not any(r['type'] == 'shared_party' and r.get('party') == row[2]
                              for r in related[row[0]]['relationships']):
                        related[row[0]]['relationships'].append({
                            'type': 'shared_party',
                            'party': row[2]
                        })

                return QueryResult(success=True, data=list(related.values()))

        except Exception as e:
            logger.error(f"Error finding related documents for {document_id}: {e}")
            return QueryResult(success=False, data=None, error=str(e))

    def get_document_clusters(
        self,
        dd_id: str,
        cluster_by: str = 'party'
    ) -> QueryResult:
        """
        Cluster documents by relationship.

        Args:
            dd_id: DD identifier
            cluster_by: 'party', 'type', or 'reference'

        Returns:
            Document clusters with shared characteristics
        """
        try:
            with self.conn.cursor() as cur:
                if cluster_by == 'party':
                    # Cluster by shared parties
                    cur.execute("""
                        SELECT
                            p.canonical_name,
                            ARRAY_AGG(DISTINCT a.document_name) as documents,
                            COUNT(DISTINCT a.id) as doc_count
                        FROM kg_party p
                        JOIN kg_edge_party_to e ON p.id = e.party_id
                        JOIN kg_agreement a ON e.agreement_id = a.id
                        WHERE p.dd_id = %s
                        GROUP BY p.canonical_name
                        HAVING COUNT(DISTINCT a.id) > 1
                        ORDER BY doc_count DESC
                    """, (dd_id,))

                    clusters = []
                    for row in cur.fetchall():
                        clusters.append({
                            'cluster_key': row[0],
                            'cluster_type': 'party',
                            'documents': row[1],
                            'document_count': row[2]
                        })

                elif cluster_by == 'type':
                    # Cluster by agreement type
                    cur.execute("""
                        SELECT
                            a.agreement_type,
                            ARRAY_AGG(DISTINCT a.document_name) as documents,
                            COUNT(*) as doc_count
                        FROM kg_agreement a
                        WHERE a.dd_id = %s
                        AND a.agreement_type IS NOT NULL
                        GROUP BY a.agreement_type
                        ORDER BY doc_count DESC
                    """, (dd_id,))

                    clusters = []
                    for row in cur.fetchall():
                        clusters.append({
                            'cluster_key': row[0],
                            'cluster_type': 'agreement_type',
                            'documents': row[1],
                            'document_count': row[2]
                        })

                elif cluster_by == 'reference':
                    # Cluster by cross-references
                    cur.execute("""
                        WITH reference_groups AS (
                            SELECT
                                LEAST(source_document_id, target_document_id) as doc1,
                                GREATEST(source_document_id, target_document_id) as doc2
                            FROM kg_edge_references
                            WHERE dd_id = %s
                        )
                        SELECT
                            doc1,
                            doc2,
                            a1.document_name as doc1_name,
                            a2.document_name as doc2_name
                        FROM reference_groups rg
                        LEFT JOIN kg_agreement a1 ON rg.doc1 = a1.document_id
                        LEFT JOIN kg_agreement a2 ON rg.doc2 = a2.document_id
                    """, (dd_id,))

                    clusters = []
                    for row in cur.fetchall():
                        clusters.append({
                            'cluster_key': f"{row[0]}-{row[1]}",
                            'cluster_type': 'reference',
                            'documents': [row[2], row[3]],
                            'document_count': 2
                        })
                else:
                    return QueryResult(
                        success=False,
                        data=None,
                        error=f"Unknown cluster_by: {cluster_by}"
                    )

                return QueryResult(success=True, data=clusters)

        except Exception as e:
            logger.error(f"Error clustering documents for DD {dd_id}: {e}")
            return QueryResult(success=False, data=None, error=str(e))

    def get_key_dates(
        self,
        dd_id: str,
        date_type: Optional[str] = None
    ) -> QueryResult:
        """
        Get key dates from the knowledge graph.

        Args:
            dd_id: DD identifier
            date_type: Optional filter (expiry, effective, deadline, etc.)

        Returns:
            List of dates with source documents
        """
        try:
            with self.conn.cursor() as cur:
                if date_type:
                    cur.execute("""
                        SELECT
                            d.id,
                            d.source_document_id,
                            d.source_document_name,
                            d.date_type,
                            d.date_value,
                            d.description
                        FROM kg_date d
                        WHERE d.dd_id = %s
                        AND LOWER(d.date_type) = LOWER(%s)
                        ORDER BY d.date_value
                    """, (dd_id, date_type))
                else:
                    cur.execute("""
                        SELECT
                            d.id,
                            d.source_document_id,
                            d.source_document_name,
                            d.date_type,
                            d.date_value,
                            d.description
                        FROM kg_date d
                        WHERE d.dd_id = %s
                        ORDER BY d.date_value
                    """, (dd_id,))

                dates = []
                for row in cur.fetchall():
                    dates.append({
                        'date_id': row[0],
                        'document_id': row[1],
                        'document_name': row[2],
                        'date_type': row[3],
                        'date_value': str(row[4]) if row[4] else None,
                        'description': row[5]
                    })

                return QueryResult(success=True, data=dates)

        except Exception as e:
            logger.error(f"Error getting key dates for DD {dd_id}: {e}")
            return QueryResult(success=False, data=None, error=str(e))

    def get_graph_summary(self, dd_id: str) -> QueryResult:
        """
        Get a summary of the knowledge graph for a DD.

        Returns counts and key statistics.
        """
        try:
            with self.conn.cursor() as cur:
                summary = {}

                # Vertex counts
                for table, label in [
                    ('kg_party', 'parties'),
                    ('kg_agreement', 'agreements'),
                    ('kg_obligation', 'obligations'),
                    ('kg_trigger', 'triggers'),
                    ('kg_amount', 'amounts'),
                    ('kg_date', 'dates')
                ]:
                    cur.execute(f"SELECT COUNT(*) FROM {table} WHERE dd_id = %s", (dd_id,))
                    summary[label] = cur.fetchone()[0]

                # Edge counts
                for table, label in [
                    ('kg_edge_party_to', 'party_to_edges'),
                    ('kg_edge_triggers', 'trigger_edges'),
                    ('kg_edge_requires_consent', 'consent_edges'),
                    ('kg_edge_references', 'reference_edges'),
                    ('kg_edge_conflicts_with', 'conflict_edges'),
                    ('kg_edge_secures', 'security_edges')
                ]:
                    cur.execute(f"SELECT COUNT(*) FROM {table} WHERE dd_id = %s", (dd_id,))
                    summary[label] = cur.fetchone()[0]

                # Calculate totals
                summary['total_vertices'] = sum([
                    summary['parties'],
                    summary['agreements'],
                    summary['obligations'],
                    summary['triggers'],
                    summary['amounts'],
                    summary['dates']
                ])

                summary['total_edges'] = sum([
                    summary['party_to_edges'],
                    summary['trigger_edges'],
                    summary['consent_edges'],
                    summary['reference_edges'],
                    summary['conflict_edges'],
                    summary['security_edges']
                ])

                # Build status
                cur.execute("""
                    SELECT status, started_at, completed_at, error_message
                    FROM kg_build_status
                    WHERE dd_id = %s
                    ORDER BY started_at DESC
                    LIMIT 1
                """, (dd_id,))

                status_row = cur.fetchone()
                if status_row:
                    summary['build_status'] = status_row[0]
                    summary['build_started'] = str(status_row[1]) if status_row[1] else None
                    summary['build_completed'] = str(status_row[2]) if status_row[2] else None
                    summary['build_error'] = status_row[3]

                return QueryResult(success=True, data=summary)

        except Exception as e:
            logger.error(f"Error getting graph summary for DD {dd_id}: {e}")
            return QueryResult(success=False, data=None, error=str(e))

    def find_conflicts(self, dd_id: str) -> QueryResult:
        """
        Find potential conflicts between documents/clauses.

        Returns conflict edges with details.
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        c.id,
                        c.source_document_id,
                        c.target_document_id,
                        c.conflict_type,
                        c.description,
                        a1.document_name as source_doc_name,
                        a2.document_name as target_doc_name
                    FROM kg_edge_conflicts_with c
                    LEFT JOIN kg_agreement a1 ON c.source_document_id = a1.document_id
                    LEFT JOIN kg_agreement a2 ON c.target_document_id = a2.document_id
                    WHERE c.dd_id = %s
                """, (dd_id,))

                conflicts = []
                for row in cur.fetchall():
                    conflicts.append({
                        'conflict_id': row[0],
                        'source_document_id': row[1],
                        'target_document_id': row[2],
                        'conflict_type': row[3],
                        'description': row[4],
                        'source_document_name': row[5],
                        'target_document_name': row[6]
                    })

                return QueryResult(success=True, data=conflicts)

        except Exception as e:
            logger.error(f"Error finding conflicts for DD {dd_id}: {e}")
            return QueryResult(success=False, data=None, error=str(e))

    def get_security_chain(self, dd_id: str) -> QueryResult:
        """
        Get security documents and their secured obligations.

        Returns security chain showing what secures what.
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        s.id,
                        s.security_document_id,
                        s.secured_obligation_id,
                        s.security_type,
                        a.document_name as security_doc_name,
                        o.description as obligation_description,
                        o.source_document_name as obligation_doc_name
                    FROM kg_edge_secures s
                    LEFT JOIN kg_agreement a ON s.security_document_id = a.document_id
                    LEFT JOIN kg_obligation o ON s.secured_obligation_id = o.id
                    WHERE s.dd_id = %s
                """, (dd_id,))

                security_chain = []
                for row in cur.fetchall():
                    security_chain.append({
                        'security_id': row[0],
                        'security_document_id': row[1],
                        'secured_obligation_id': row[2],
                        'security_type': row[3],
                        'security_document_name': row[4],
                        'obligation_description': row[5],
                        'obligation_document_name': row[6]
                    })

                return QueryResult(success=True, data=security_chain)

        except Exception as e:
            logger.error(f"Error getting security chain for DD {dd_id}: {e}")
            return QueryResult(success=False, data=None, error=str(e))

    # =========================================================================
    # Convenience methods for synthesis pipeline (Phase 6)
    # These wrap existing methods with the interface expected by the synthesizer
    # =========================================================================

    def find_change_of_control_clauses(self, dd_id: str) -> Dict[str, Any]:
        """
        Find all Change of Control clauses.
        Wrapper for synthesis pipeline.

        Returns:
            Dict with 'clauses' list and 'summary' string
        """
        result = self.get_coc_clauses(dd_id)
        if not result.success:
            return {'clauses': [], 'summary': 'Error retrieving CoC clauses', 'error': result.error}

        clauses = result.data or []
        return {
            'clauses': clauses,
            'count': len(clauses),
            'summary': f"{len(clauses)} Change of Control clauses found across documents"
        }

    def find_consent_requirements(self, dd_id: str) -> Dict[str, Any]:
        """
        Find all consent requirements.
        Wrapper for synthesis pipeline.

        Returns:
            Dict with 'requirements' list and 'summary' string
        """
        result = self.get_consent_requirements(dd_id)
        if not result.success:
            return {'requirements': [], 'summary': 'Error retrieving consent requirements', 'error': result.error}

        requirements = result.data or []
        # Convert ConsentRequirement objects to dicts
        req_dicts = []
        for req in requirements:
            if hasattr(req, '__dict__'):
                req_dicts.append({
                    'agreement_name': req.agreement_name,
                    'document_id': req.document_id,
                    'consent_type': req.consent_type,
                    'required_for': req.required_for,
                    'threshold': req.threshold,
                    'notice_period': req.notice_period
                })
            else:
                req_dicts.append(req)

        return {
            'requirements': req_dicts,
            'count': len(req_dicts),
            'summary': f"{len(req_dicts)} consent requirements identified"
        }

    def find_cascade_effects(self, dd_id: str, trigger_type: str = 'change_of_control') -> Dict[str, Any]:
        """
        Find cascade effects for a given trigger type.
        Wrapper for synthesis pipeline.

        Args:
            dd_id: DD identifier
            trigger_type: Type of trigger to analyze (default: change_of_control)

        Returns:
            Dict with 'affected_agreements', 'required_consents', 'summary'
        """
        result = self.analyze_coc_cascade(dd_id)
        if not result.success:
            return {'affected_agreements': [], 'summary': 'Error analyzing cascade', 'error': result.error}

        impact = result.data
        if not impact:
            return {'affected_agreements': [], 'summary': 'No cascade effects found'}

        return {
            'affected_agreements': impact.affected_agreements,
            'required_consents': impact.required_consents,
            'triggered_clauses': impact.triggered_clauses,
            'total_financial_exposure': float(impact.total_financial_exposure),
            'cascade_depth': impact.cascade_depth,
            'summary': f"{len(impact.affected_agreements)} agreements affected, "
                      f"{len(impact.required_consents)} consents required, "
                      f"cascade depth: {impact.cascade_depth}"
        }

    def cluster_by_relationship(self, dd_id: str) -> List[Dict[str, Any]]:
        """
        Cluster documents by relationships (parties, types, references).
        Wrapper for synthesis pipeline.

        Returns:
            List of clusters with cluster_id, cluster_type, document_ids, document_count
        """
        clusters = []

        # Get party-based clusters
        party_result = self.get_document_clusters(dd_id, cluster_by='party')
        if party_result.success and party_result.data:
            for i, cluster in enumerate(party_result.data):
                clusters.append({
                    'cluster_id': f"party_{i}_{cluster.get('cluster_key', 'unknown')[:20]}",
                    'cluster_type': 'party',
                    'cluster_key': cluster.get('cluster_key'),
                    'documents': cluster.get('documents', []),
                    'document_count': cluster.get('document_count', 0)
                })

        # Get type-based clusters
        type_result = self.get_document_clusters(dd_id, cluster_by='type')
        if type_result.success and type_result.data:
            for i, cluster in enumerate(type_result.data):
                clusters.append({
                    'cluster_id': f"type_{i}_{cluster.get('cluster_key', 'unknown')[:20]}",
                    'cluster_type': 'agreement_type',
                    'cluster_key': cluster.get('cluster_key'),
                    'documents': cluster.get('documents', []),
                    'document_count': cluster.get('document_count', 0)
                })

        # Sort by document count (largest clusters first)
        clusters.sort(key=lambda c: c['document_count'], reverse=True)

        return clusters

    def get_key_parties(self, dd_id: str, limit: int = 20) -> Dict[str, Any]:
        """
        Get key parties with most agreements.
        Wrapper for synthesis pipeline.

        Returns:
            Dict with 'parties' list, 'count', and 'summary'
        """
        result = self.get_all_parties(dd_id)
        if not result.success:
            return {'parties': [], 'count': 0, 'summary': 'Error retrieving parties'}

        parties = result.data or []
        # Convert PartyInfo objects to dicts
        party_dicts = []
        for party in parties[:limit]:
            if hasattr(party, '__dict__'):
                party_dicts.append({
                    'party_id': party.party_id,
                    'name': party.canonical_name,
                    'all_names': party.all_names,
                    'party_types': party.party_types,
                    'agreement_count': party.document_count
                })
            else:
                party_dicts.append(party)

        return {
            'parties': party_dicts,
            'count': len(parties),
            'summary': f"{len(parties)} parties identified, top parties: " +
                      ", ".join(p.get('name', 'Unknown') for p in party_dicts[:5])
        }

    def get_graph_insights_for_synthesis(self, dd_id: str) -> Dict[str, Any]:
        """
        Get all graph insights needed for synthesis in a single call.

        Returns:
            Dict with change_of_control, cascade_effects, consent_requirements, key_parties
        """
        return {
            'change_of_control': self.find_change_of_control_clauses(dd_id),
            'cascade_effects': self.find_cascade_effects(dd_id),
            'consent_requirements': self.find_consent_requirements(dd_id),
            'key_parties': self.get_key_parties(dd_id)
        }
