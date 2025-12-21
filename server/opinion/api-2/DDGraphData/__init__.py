"""
API endpoint for knowledge graph visualisation data.
Returns nodes and edges formatted for D3.js/Vis.js rendering.

Phase 7: Enterprise Features
"""

import azure.functions as func
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict
from sqlalchemy import text

from shared.session import transactional_session
from shared.audit import log_audit_event, AuditEventType

logger = logging.getLogger(__name__)

# Node type configurations for visualization
NODE_CONFIGS = {
    'party': {
        'color': '#4F46E5',  # Indigo
        'shape': 'circle',
        'size_base': 20
    },
    'agreement': {
        'color': '#059669',  # Emerald
        'shape': 'square',
        'size_base': 25
    },
    'trigger': {
        'color': '#DC2626',  # Red
        'shape': 'triangle',
        'size_base': 15
    },
    'obligation': {
        'color': '#D97706',  # Amber
        'shape': 'diamond',
        'size_base': 12
    },
    'document': {
        'color': '#6B7280',  # Gray
        'shape': 'rectangle',
        'size_base': 18
    }
}


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get graph visualisation data for a DD project.

    Query params:
        dd_id: DD project ID (required)
        view_type: 'full' | 'parties' | 'agreements' | 'triggers' | 'cluster' (default: 'full')
        focus_node: Optional node ID to center view on
        depth: How many hops from focus_node (default: 2)
        include_documents: Whether to include document nodes (default: false for performance)
    """
    try:
        dd_id = req.params.get('dd_id')
        if not dd_id:
            return func.HttpResponse(
                json.dumps({"error": "dd_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        view_type = req.params.get('view_type', 'full')
        focus_node = req.params.get('focus_node')
        depth = int(req.params.get('depth', 2))
        include_documents = req.params.get('include_documents', 'false').lower() == 'true'

        with transactional_session() as session:
            # Get graph data based on view type
            graph_data = get_graph_visualisation_data(
                session=session,
                dd_id=dd_id,
                view_type=view_type,
                focus_node=focus_node,
                depth=depth,
                include_documents=include_documents
            )

            # Log access audit event
            log_audit_event(
                session=session,
                event_type=AuditEventType.GRAPH_QUERIED.value,
                entity_type='dd',
                entity_id=dd_id,
                dd_id=dd_id,
                details={'view_type': view_type, 'focus_node': focus_node}
            )
            session.commit()

        return func.HttpResponse(
            json.dumps(graph_data, default=str),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error getting graph data: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def get_graph_visualisation_data(
    session,
    dd_id: str,
    view_type: str,
    focus_node: Optional[str],
    depth: int,
    include_documents: bool
) -> Dict[str, Any]:
    """
    Build graph data structure for visualisation.

    Returns:
        {
            "nodes": [...],
            "edges": [...],
            "metadata": {...},
            "clusters": [...],
            "stats": {...}
        }
    """
    nodes = []
    edges = []
    node_ids = set()  # Track which nodes we've added

    # Get parties
    parties = session.execute(
        text("""
            SELECT
                p.id,
                p.name,
                p.party_type,
                p.role,
                p.jurisdiction,
                COUNT(DISTINCT e.document_id) as doc_count,
                COUNT(DISTINCT e.agreement_id) as agreement_count
            FROM kg_party p
            LEFT JOIN kg_edge_party_to e ON p.id = e.party_id
            WHERE p.dd_id = :dd_id
            GROUP BY p.id, p.name, p.party_type, p.role, p.jurisdiction
        """),
        {'dd_id': dd_id}
    ).fetchall()

    for party in parties:
        node_id = f"party_{party.id}"
        nodes.append({
            'id': node_id,
            'label': party.name,
            'type': 'party',
            'color': NODE_CONFIGS['party']['color'],
            'shape': NODE_CONFIGS['party']['shape'],
            'size': NODE_CONFIGS['party']['size_base'] + (party.doc_count * 2),
            'metadata': {
                'party_type': party.party_type,
                'role': party.role,
                'jurisdiction': party.jurisdiction,
                'document_count': party.doc_count,
                'agreement_count': party.agreement_count
            }
        })
        node_ids.add(node_id)

    # Get agreements
    agreements = session.execute(
        text("""
            SELECT
                a.id,
                a.name,
                a.agreement_type,
                a.document_id,
                a.has_change_of_control,
                a.has_consent_requirement,
                a.has_assignment_restriction,
                a.effective_date,
                a.expiry_date,
                d.original_file_name
            FROM kg_agreement a
            LEFT JOIN document d ON a.document_id = d.id
            WHERE a.dd_id = :dd_id
        """),
        {'dd_id': dd_id}
    ).fetchall()

    for agreement in agreements:
        # Determine risk level based on flags
        risk_level = 'low'
        if agreement.has_change_of_control and agreement.has_consent_requirement:
            risk_level = 'critical'
        elif agreement.has_change_of_control or agreement.has_consent_requirement:
            risk_level = 'high'
        elif agreement.has_assignment_restriction:
            risk_level = 'medium'

        node_id = f"agreement_{agreement.id}"
        label = agreement.name
        if len(label) > 30:
            label = label[:27] + '...'

        nodes.append({
            'id': node_id,
            'label': label,
            'type': 'agreement',
            'color': NODE_CONFIGS['agreement']['color'],
            'shape': NODE_CONFIGS['agreement']['shape'],
            'size': NODE_CONFIGS['agreement']['size_base'],
            'metadata': {
                'full_name': agreement.name,
                'agreement_type': agreement.agreement_type,
                'document_id': str(agreement.document_id) if agreement.document_id else None,
                'document_name': agreement.original_file_name,
                'has_coc': agreement.has_change_of_control,
                'has_consent': agreement.has_consent_requirement,
                'has_assignment_restriction': agreement.has_assignment_restriction,
                'effective_date': agreement.effective_date.isoformat() if agreement.effective_date else None,
                'expiry_date': agreement.expiry_date.isoformat() if agreement.expiry_date else None,
                'risk_level': risk_level
            }
        })
        node_ids.add(node_id)

    # Get triggers
    triggers = session.execute(
        text("""
            SELECT
                t.id,
                t.trigger_type,
                t.description,
                t.consequences,
                t.clause_reference,
                t.agreement_id,
                a.name as agreement_name
            FROM kg_trigger t
            LEFT JOIN kg_agreement a ON t.agreement_id = a.id
            WHERE t.dd_id = :dd_id
        """),
        {'dd_id': dd_id}
    ).fetchall()

    for trigger in triggers:
        node_id = f"trigger_{trigger.id}"
        label = (trigger.trigger_type or 'Unknown').replace('_', ' ').title()

        nodes.append({
            'id': node_id,
            'label': label,
            'type': 'trigger',
            'color': NODE_CONFIGS['trigger']['color'],
            'shape': NODE_CONFIGS['trigger']['shape'],
            'size': NODE_CONFIGS['trigger']['size_base'],
            'metadata': {
                'trigger_type': trigger.trigger_type,
                'description': trigger.description,
                'consequences': trigger.consequences,
                'clause_reference': trigger.clause_reference,
                'agreement_name': trigger.agreement_name
            }
        })
        node_ids.add(node_id)

        # Edge: Agreement -> Trigger
        if trigger.agreement_id:
            agreement_node_id = f"agreement_{trigger.agreement_id}"
            if agreement_node_id in node_ids:
                edges.append({
                    'id': f"edge_agr_trg_{trigger.id}",
                    'source': agreement_node_id,
                    'target': node_id,
                    'type': 'HAS_TRIGGER',
                    'label': 'triggers',
                    'color': '#DC2626',
                    'width': 2
                })

    # Get PARTY_TO edges
    party_edges = session.execute(
        text("""
            SELECT e.id, e.party_id, e.agreement_id, e.document_id, e.role, e.target_type
            FROM kg_edge_party_to e
            WHERE e.dd_id = :dd_id
            AND e.agreement_id IS NOT NULL
        """),
        {'dd_id': dd_id}
    ).fetchall()

    for edge in party_edges:
        source_id = f"party_{edge.party_id}"
        target_id = f"agreement_{edge.agreement_id}"

        if source_id in node_ids and target_id in node_ids:
            edges.append({
                'id': f"edge_pty_{edge.id}",
                'source': source_id,
                'target': target_id,
                'type': 'PARTY_TO',
                'label': edge.role or '',
                'color': '#4F46E5',
                'width': 1
            })

    # Get REQUIRES_CONSENT edges
    consent_edges = session.execute(
        text("""
            SELECT rc.id, rc.agreement_id, rc.party_id, rc.consent_type, rc.clause_reference
            FROM kg_edge_requires_consent rc
            WHERE rc.dd_id = :dd_id
        """),
        {'dd_id': dd_id}
    ).fetchall()

    for edge in consent_edges:
        source_id = f"agreement_{edge.agreement_id}"
        target_id = f"party_{edge.party_id}"

        if source_id in node_ids and target_id in node_ids:
            edges.append({
                'id': f"edge_consent_{edge.id}",
                'source': source_id,
                'target': target_id,
                'type': 'REQUIRES_CONSENT',
                'label': edge.consent_type or 'Consent Required',
                'color': '#D97706',
                'width': 2,
                'dashed': True,
                'metadata': {
                    'clause_reference': edge.clause_reference
                }
            })

    # Get obligations if view_type includes them
    if view_type in ['full', 'obligations']:
        obligations = session.execute(
            text("""
                SELECT
                    o.id,
                    o.description,
                    o.obligation_type,
                    o.agreement_id,
                    o.obligor_party_id,
                    o.obligee_party_id,
                    o.is_material,
                    o.amount,
                    o.currency
                FROM kg_obligation o
                WHERE o.dd_id = :dd_id
                AND o.is_material = TRUE
                LIMIT 50
            """),
            {'dd_id': dd_id}
        ).fetchall()

        for obligation in obligations:
            node_id = f"obligation_{obligation.id}"
            label = (obligation.obligation_type or 'Obligation').replace('_', ' ').title()
            if len(label) > 20:
                label = label[:17] + '...'

            nodes.append({
                'id': node_id,
                'label': label,
                'type': 'obligation',
                'color': NODE_CONFIGS['obligation']['color'],
                'shape': NODE_CONFIGS['obligation']['shape'],
                'size': NODE_CONFIGS['obligation']['size_base'],
                'metadata': {
                    'description': obligation.description[:200] if obligation.description else None,
                    'obligation_type': obligation.obligation_type,
                    'is_material': obligation.is_material,
                    'amount': float(obligation.amount) if obligation.amount else None,
                    'currency': obligation.currency
                }
            })
            node_ids.add(node_id)

            # Edge: Agreement -> Obligation
            if obligation.agreement_id:
                agreement_node_id = f"agreement_{obligation.agreement_id}"
                if agreement_node_id in node_ids:
                    edges.append({
                        'id': f"edge_agr_obl_{obligation.id}",
                        'source': agreement_node_id,
                        'target': node_id,
                        'type': 'HAS_OBLIGATION',
                        'color': '#D97706',
                        'width': 1
                    })

    # Include documents if requested
    if include_documents:
        documents = session.execute(
            text("""
                SELECT DISTINCT
                    d.id,
                    d.original_file_name,
                    d.type as doc_type,
                    f.folder_category
                FROM document d
                JOIN folder f ON d.folder_id = f.id
                JOIN kg_agreement a ON a.document_id = d.id
                WHERE f.dd_id = :dd_id
                LIMIT 100
            """),
            {'dd_id': dd_id}
        ).fetchall()

        for doc in documents:
            node_id = f"document_{doc.id}"
            label = doc.original_file_name
            if len(label) > 25:
                label = label[:22] + '...'

            nodes.append({
                'id': node_id,
                'label': label,
                'type': 'document',
                'color': NODE_CONFIGS['document']['color'],
                'shape': NODE_CONFIGS['document']['shape'],
                'size': NODE_CONFIGS['document']['size_base'],
                'metadata': {
                    'full_name': doc.original_file_name,
                    'doc_type': doc.doc_type,
                    'folder_category': doc.folder_category
                }
            })
            node_ids.add(node_id)

    # Filter by view_type
    if view_type == 'parties':
        nodes = [n for n in nodes if n['type'] == 'party']
        edges = [e for e in edges if e['source'].startswith('party_') or e['target'].startswith('party_')]
    elif view_type == 'agreements':
        nodes = [n for n in nodes if n['type'] in ['agreement', 'party']]
        edges = [e for e in edges if 'agreement_' in e['source'] or 'agreement_' in e['target']]
    elif view_type == 'triggers':
        nodes = [n for n in nodes if n['type'] in ['trigger', 'agreement']]
        edges = [e for e in edges if 'trigger_' in e['source'] or 'trigger_' in e['target']]

    # Calculate stats
    stats = {
        'total_nodes': len(nodes),
        'total_edges': len(edges),
        'parties': len([n for n in nodes if n['type'] == 'party']),
        'agreements': len([n for n in nodes if n['type'] == 'agreement']),
        'triggers': len([n for n in nodes if n['type'] == 'trigger']),
        'obligations': len([n for n in nodes if n['type'] == 'obligation']),
        'coc_agreements': len([n for n in nodes if n['type'] == 'agreement' and n['metadata'].get('has_coc')]),
        'consent_required': len([n for n in nodes if n['type'] == 'agreement' and n['metadata'].get('has_consent')])
    }

    # Build clusters based on party connections
    clusters = build_graph_clusters(nodes, edges)

    return {
        'nodes': nodes,
        'edges': edges,
        'clusters': clusters,
        'stats': stats,
        'metadata': {
            'dd_id': dd_id,
            'view_type': view_type,
            'include_documents': include_documents,
            'generated_at': datetime.utcnow().isoformat()
        }
    }


def build_graph_clusters(nodes: List[Dict], edges: List[Dict]) -> List[Dict]:
    """
    Identify clusters of connected nodes for layout optimization.
    Uses BFS to find connected components.
    """
    # Build adjacency list
    adjacency = defaultdict(set)
    for edge in edges:
        adjacency[edge['source']].add(edge['target'])
        adjacency[edge['target']].add(edge['source'])

    # Find connected components using BFS
    visited = set()
    clusters = []

    for node in nodes:
        node_id = node['id']
        if node_id in visited:
            continue

        # BFS to find all connected nodes
        cluster_nodes = []
        queue = [node_id]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            cluster_nodes.append(current)

            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    queue.append(neighbor)

        if cluster_nodes:
            # Get the types in this cluster
            cluster_types = defaultdict(int)
            for cn in cluster_nodes:
                for n in nodes:
                    if n['id'] == cn:
                        cluster_types[n['type']] += 1
                        break

            clusters.append({
                'id': f"cluster_{len(clusters)}",
                'nodes': cluster_nodes,
                'size': len(cluster_nodes),
                'types': dict(cluster_types)
            })

    return sorted(clusters, key=lambda c: c['size'], reverse=True)
