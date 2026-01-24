# DDGetBlueprintRequirements/__init__.py
"""
Get Blueprint Document Requirements Endpoint

Returns expected documents per category based on transaction type.
Used by Checkpoint A to show inline document requirements.

GET /api/dd-get-blueprint-requirements?transaction_type=mining_resources&dd_id=xxx

Returns:
{
    "transaction_type": "mining_resources",
    "transaction_name": "Mining & Resources Acquisition",
    "requirements": {
        "01_Corporate": {
            "relevance": "high",
            "expected_documents": ["MOI", "Shareholders Agreement", ...],
            "found_documents": [...],  // If dd_id provided
            "missing_documents": [...]  // If dd_id provided
        },
        ...
    }
}
"""
import logging
import os
import json
import yaml
import azure.functions as func

from shared.utils import auth_get_email
from shared.session import transactional_session
from shared.models import Document, Folder, DueDiligence

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"

# Path to blueprint YAML files
BLUEPRINT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "dd_enhanced", "config", "blueprints"
)

# Category code mapping (01_Corporate_Governance -> 01_Corporate)
CATEGORY_CODE_MAP = {
    "01_Corporate_Governance": "01_Corporate",
    "02_Commercial": "02_Commercial",
    "03_Financial": "03_Financial",
    "04_Regulatory": "04_Regulatory",
    "05_Employment": "05_Employment",
    "06_Property": "06_Property",
    "07_Insurance": "07_Insurance",
    "08_Litigation": "08_Litigation",
    "09_Tax": "09_Tax",
    "99_Needs_Review": "99_Needs_Review",
}


def load_blueprint(transaction_type: str) -> dict | None:
    """Load a blueprint YAML file by transaction type code."""
    blueprint_file = os.path.join(BLUEPRINT_PATH, f"{transaction_type}.yaml")

    if not os.path.exists(blueprint_file):
        logging.warning(f"Blueprint file not found: {blueprint_file}")
        return None

    try:
        with open(blueprint_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.error(f"Failed to load blueprint {blueprint_file}: {e}")
        return None


def get_documents_by_category(dd_id: str) -> dict[str, list[dict]]:
    """Get all documents for a DD project grouped by ai_category."""
    import uuid as uuid_module

    dd_uuid = uuid_module.UUID(dd_id) if isinstance(dd_id, str) else dd_id
    docs_by_category: dict[str, list[dict]] = {}

    with transactional_session() as session:
        # Get all folders for this DD
        folders = session.query(Folder).filter(Folder.dd_id == dd_uuid).all()
        folder_ids = [f.id for f in folders]

        if not folder_ids:
            return docs_by_category

        # Get all documents (excluding the original ZIP)
        documents = (
            session.query(Document)
            .filter(
                Document.folder_id.in_(folder_ids),
                Document.is_original == False
            )
            .all()
        )

        for doc in documents:
            category = doc.ai_category or "99_Needs_Review"
            if category not in docs_by_category:
                docs_by_category[category] = []

            docs_by_category[category].append({
                "id": str(doc.id),
                "filename": doc.original_file_name,
                "document_type": doc.ai_document_type,
                "confidence": doc.ai_confidence,
                "classification_status": doc.classification_status,
            })

    return docs_by_category


def match_documents_to_requirements(
    expected_docs: list[str],
    found_docs: list[dict]
) -> tuple[list[dict], list[str]]:
    """
    Match found documents to expected document types.

    Returns:
        (found_matches, missing_types)
    """
    found_matches = []
    expected_remaining = set(expected_docs)

    for doc in found_docs:
        doc_type = doc.get("document_type", "").lower()
        filename = doc.get("filename", "").lower()

        # Try to match by document type or filename
        matched_type = None
        for expected in expected_remaining:
            expected_lower = expected.lower()
            # Match if document type contains expected type
            if expected_lower in doc_type or expected_lower in filename:
                matched_type = expected
                break
            # Also check for common abbreviations
            if expected_lower == "moi" and ("memorandum of incorporation" in doc_type or "memorandum of incorporation" in filename):
                matched_type = expected
                break

        found_matches.append({
            **doc,
            "matched_type": matched_type,
        })

        if matched_type:
            expected_remaining.discard(matched_type)

    return found_matches, list(expected_remaining)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get blueprint document requirements for a transaction type.

    GET /api/dd-get-blueprint-requirements?transaction_type=mining_resources&dd_id=xxx

    Query parameters:
        transaction_type (required): The blueprint code (e.g., mining_resources, ma_corporate)
        dd_id (optional): DD project ID to include found/missing document matching

    Returns:
        JSON with requirements per category
    """

    # Auth check
    if not DEV_MODE and req.headers.get('function-key') != os.environ.get("FUNCTION_KEY"):
        logging.info("No matching value in header")
        return func.HttpResponse("", status_code=401)

    try:
        email, err = auth_get_email(req)
        if err:
            return err

        # Get query parameters
        transaction_type = req.params.get("transaction_type")
        dd_id = req.params.get("dd_id")

        if not transaction_type:
            return func.HttpResponse(
                json.dumps({"error": "transaction_type parameter is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Load the blueprint
        blueprint = load_blueprint(transaction_type)
        if not blueprint:
            return func.HttpResponse(
                json.dumps({"error": f"Blueprint '{transaction_type}' not found"}),
                status_code=404,
                mimetype="application/json"
            )

        # Get documents by category if dd_id provided
        docs_by_category = {}
        if dd_id:
            docs_by_category = get_documents_by_category(dd_id)

        # Build requirements response
        requirements = {}
        folder_structure = blueprint.get("folder_structure", {})

        for folder_key, folder_config in folder_structure.items():
            # Map blueprint folder name to standard category code
            category_code = CATEGORY_CODE_MAP.get(folder_key, folder_key)

            expected_docs = folder_config.get("expected_documents", [])
            found_docs = docs_by_category.get(category_code, [])

            # Match documents to requirements
            if dd_id:
                found_matches, missing_docs = match_documents_to_requirements(
                    expected_docs, found_docs
                )
            else:
                found_matches = []
                missing_docs = expected_docs

            requirements[category_code] = {
                "folder_name": folder_key,
                "relevance": folder_config.get("relevance", "medium"),
                "subcategories": folder_config.get("subcategories", []),
                "expected_documents": expected_docs,
                "found_documents": found_matches,
                "missing_documents": missing_docs,
                "document_count": len(found_docs),
                "is_complete": len(missing_docs) == 0 if expected_docs else True,
            }

        # Add 99_Needs_Review if there are unclassified documents
        needs_review_docs = docs_by_category.get("99_Needs_Review", [])
        if needs_review_docs or "99_Needs_Review" in folder_structure:
            requirements["99_Needs_Review"] = {
                "folder_name": "99_Needs_Review",
                "relevance": "n/a",
                "subcategories": ["Unclassified", "Low Confidence"],
                "expected_documents": [],
                "found_documents": needs_review_docs,
                "missing_documents": [],
                "document_count": len(needs_review_docs),
                "is_complete": len(needs_review_docs) == 0,
                "requires_action": len(needs_review_docs) > 0,
            }

        response = {
            "transaction_type": transaction_type,
            "transaction_name": blueprint.get("transaction_type", transaction_type),
            "description": blueprint.get("description", ""),
            "jurisdiction": blueprint.get("jurisdiction", "South Africa"),
            "requirements": requirements,
            "summary": {
                "total_expected": sum(
                    len(r.get("expected_documents", []))
                    for r in requirements.values()
                ),
                "total_found": sum(
                    len(r.get("found_documents", []))
                    for r in requirements.values()
                ),
                "total_missing": sum(
                    len(r.get("missing_documents", []))
                    for r in requirements.values()
                ),
                "needs_review_count": len(needs_review_docs),
                "categories_complete": sum(
                    1 for r in requirements.values()
                    if r.get("is_complete", False)
                ),
                "total_categories": len(requirements),
            }
        }

        return func.HttpResponse(
            json.dumps(response),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"[DDGetBlueprintRequirements] Error: {str(e)}")
        logging.exception("Full traceback:")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
