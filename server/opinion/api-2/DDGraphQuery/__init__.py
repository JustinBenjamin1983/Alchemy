"""
DDGraphQuery API Endpoint

Exposes knowledge graph query capabilities for DD analysis.

Supported query types:
- summary: Get graph statistics
- parties: Get all parties with relationships
- party_agreements: Get agreements for a specific party
- coc_clauses: Get Change of Control clauses
- consent_requirements: Get consent requirements
- coc_cascade: Analyze Change of Control cascade effects
- financial_exposure: Get financial exposure summary
- related_documents: Get documents related to a specific document
- document_clusters: Get document clusters by party/type/reference
- key_dates: Get key dates
- conflicts: Find potential conflicts
- security_chain: Get security documents and obligations
"""

import logging
import os
import json
from dataclasses import asdict

import azure.functions as func
from shared.utils import auth_get_email
from shared.session import engine

from dd_enhanced.core.graph import GraphQueryEngine

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def main(req: func.HttpRequest) -> func.HttpResponse:
    """Handle graph query requests."""

    # Skip function-key check in dev mode
    if not DEV_MODE and req.headers.get('function-key') != os.environ.get("FUNCTION_KEY"):
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)

    try:
        email, err = auth_get_email(req)
        if err:
            return err

        # Get parameters
        dd_id = req.params.get("dd_id")
        query_type = req.params.get("query_type", "summary")

        if not dd_id:
            return func.HttpResponse(
                json.dumps({"error": "dd_id is required"}),
                mimetype="application/json",
                status_code=400
            )

        # Get raw connection for graph queries
        conn = engine.raw_connection()

        try:
            query_engine = GraphQueryEngine(conn)
            result = execute_query(query_engine, query_type, dd_id, req)

            if not result.success:
                return func.HttpResponse(
                    json.dumps({"error": result.error}),
                    mimetype="application/json",
                    status_code=500
                )

            # Convert result to JSON-serializable format
            response_data = serialize_result(result.data)

            return func.HttpResponse(
                json.dumps({
                    "success": True,
                    "query_type": query_type,
                    "dd_id": dd_id,
                    "data": response_data
                }),
                mimetype="application/json",
                status_code=200
            )

        finally:
            conn.close()

    except Exception as e:
        logging.error(f"Graph query error: {e}")
        logging.exception("Graph query error")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )


def execute_query(
    query_engine: GraphQueryEngine,
    query_type: str,
    dd_id: str,
    req: func.HttpRequest
):
    """Execute the appropriate query based on query_type."""

    if query_type == "summary":
        return query_engine.get_graph_summary(dd_id)

    elif query_type == "parties":
        return query_engine.get_all_parties(dd_id)

    elif query_type == "party_agreements":
        party_id = req.params.get("party_id")
        if not party_id:
            from dd_enhanced.core.graph import QueryResult
            return QueryResult(success=False, data=None, error="party_id is required")
        return query_engine.get_party_agreements(int(party_id))

    elif query_type == "coc_clauses":
        return query_engine.get_coc_clauses(dd_id)

    elif query_type == "consent_requirements":
        return query_engine.get_consent_requirements(dd_id)

    elif query_type == "coc_cascade":
        target_party = req.params.get("target_party")
        return query_engine.analyze_coc_cascade(dd_id, target_party)

    elif query_type == "financial_exposure":
        by_document = req.params.get("by_document", "").lower() == "true"
        by_currency = req.params.get("by_currency", "").lower() == "true"
        return query_engine.get_financial_exposure(dd_id, by_document, by_currency)

    elif query_type == "related_documents":
        document_id = req.params.get("document_id")
        if not document_id:
            from dd_enhanced.core.graph import QueryResult
            return QueryResult(success=False, data=None, error="document_id is required")
        max_depth = int(req.params.get("max_depth", "2"))
        return query_engine.get_related_documents(document_id, dd_id, max_depth)

    elif query_type == "document_clusters":
        cluster_by = req.params.get("cluster_by", "party")
        return query_engine.get_document_clusters(dd_id, cluster_by)

    elif query_type == "key_dates":
        date_type = req.params.get("date_type")
        return query_engine.get_key_dates(dd_id, date_type)

    elif query_type == "conflicts":
        return query_engine.find_conflicts(dd_id)

    elif query_type == "security_chain":
        return query_engine.get_security_chain(dd_id)

    else:
        from dd_enhanced.core.graph import QueryResult
        return QueryResult(
            success=False,
            data=None,
            error=f"Unknown query_type: {query_type}. Supported types: summary, parties, "
                  f"party_agreements, coc_clauses, consent_requirements, coc_cascade, "
                  f"financial_exposure, related_documents, document_clusters, key_dates, "
                  f"conflicts, security_chain"
        )


def serialize_result(data):
    """Convert dataclasses and special types to JSON-serializable format."""
    if data is None:
        return None

    if isinstance(data, list):
        return [serialize_result(item) for item in data]

    if isinstance(data, dict):
        return {k: serialize_result(v) for k, v in data.items()}

    if hasattr(data, '__dataclass_fields__'):
        return serialize_result(asdict(data))

    # Handle Decimal
    from decimal import Decimal
    if isinstance(data, Decimal):
        return float(data)

    return data
