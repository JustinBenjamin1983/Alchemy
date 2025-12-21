"""
DD Document Registry API Endpoints

Provides document registry functionality for DD projects:
- Get document registry for transaction types
- Classify uploaded documents
- Identify missing documents
- Generate document request lists
"""

import logging
import os
import json
import sys

import azure.functions as func
from shared.utils import auth_get_email

# Add dd_enhanced to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dd_enhanced'))

from config.documents.registry import (
    load_document_registry,
    list_available_registries,
    classify_document,
    get_missing_documents,
    generate_document_request_list,
    get_folder_structure,
    get_document_count_by_priority,
    DocumentPriority,
)
from config.blueprints.loader import load_blueprint, list_available_blueprints


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main handler for document registry operations.

    Routes based on 'action' parameter:
    - list_registries: List available transaction types
    - get_registry: Get full registry for a transaction type
    - classify: Auto-classify a document
    - missing: Get list of missing documents
    - request_list: Generate document request list
    - folders: Get folder structure
    - blueprint: Get blueprint for transaction type
    - transaction_types: Get all transaction types with metadata
    """

    # Skip function-key check in dev mode
    dev_mode = os.environ.get("DEV_MODE", "").lower() == "true"
    if not dev_mode and req.headers.get('function-key') != os.environ.get("FUNCTION_KEY"):
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)

    try:
        email, err = auth_get_email(req)
        if err:
            return err

        action = req.params.get("action", "list_registries")

        if action == "list_registries":
            return handle_list_registries()

        elif action == "transaction_types":
            return handle_transaction_types()

        elif action == "get_registry":
            transaction_type = req.params.get("transaction_type")
            if not transaction_type:
                return func.HttpResponse(
                    json.dumps({"error": "transaction_type is required"}),
                    mimetype="application/json",
                    status_code=400
                )
            return handle_get_registry(transaction_type)

        elif action == "classify":
            return handle_classify(req)

        elif action == "missing":
            return handle_missing(req)

        elif action == "request_list":
            transaction_type = req.params.get("transaction_type")
            priority = req.params.get("priority", "required")
            if not transaction_type:
                return func.HttpResponse(
                    json.dumps({"error": "transaction_type is required"}),
                    mimetype="application/json",
                    status_code=400
                )
            return handle_request_list(transaction_type, priority)

        elif action == "folders":
            transaction_type = req.params.get("transaction_type")
            if not transaction_type:
                return func.HttpResponse(
                    json.dumps({"error": "transaction_type is required"}),
                    mimetype="application/json",
                    status_code=400
                )
            return handle_folders(transaction_type)

        elif action == "blueprint":
            transaction_type = req.params.get("transaction_type")
            if not transaction_type:
                return func.HttpResponse(
                    json.dumps({"error": "transaction_type is required"}),
                    mimetype="application/json",
                    status_code=400
                )
            return handle_blueprint(transaction_type)

        else:
            return func.HttpResponse(
                json.dumps({"error": f"Unknown action: {action}"}),
                mimetype="application/json",
                status_code=400
            )

    except Exception as e:
        logging.error(str(e))
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )


def handle_list_registries():
    """List all available document registries."""
    registries = list_available_registries()
    return func.HttpResponse(
        json.dumps({
            "success": True,
            "data": registries
        }),
        mimetype="application/json",
        status_code=200
    )


def handle_transaction_types():
    """Get all transaction types with metadata."""
    registries = list_available_registries()

    transaction_types = []
    for reg_name in registries:
        try:
            registry = load_document_registry(reg_name)
            priority_counts = get_document_count_by_priority(reg_name)

            # Get blueprint info if available
            blueprint_info = None
            try:
                blueprint = load_blueprint(reg_name)

                # Count questions from risk_categories (standard_questions)
                risk_category_questions = sum(
                    len(cat.get("standard_questions", []))
                    for cat in blueprint.get("risk_categories", [])
                )

                # Count questions from folder_questions
                folder_questions = 0
                for folder_data in blueprint.get("folder_questions", {}).values():
                    folder_questions += len(folder_data.get("questions", []))

                blueprint_info = {
                    "name": blueprint.get("transaction_type", reg_name),
                    "description": blueprint.get("description", ""),
                    "risk_categories": len(blueprint.get("risk_categories", [])),
                    "total_questions": risk_category_questions + folder_questions
                }
            except Exception:
                pass

            transaction_types.append({
                "code": reg_name,
                "name": _format_transaction_name(reg_name),
                "document_count": len(registry.get("documents", [])),
                "folder_count": len(registry.get("folder_structure", [])),
                "priority_counts": priority_counts,
                "blueprint": blueprint_info
            })
        except Exception as e:
            logging.warning(f"Could not load registry {reg_name}: {e}")

    return func.HttpResponse(
        json.dumps({
            "success": True,
            "data": transaction_types
        }),
        mimetype="application/json",
        status_code=200
    )


def handle_get_registry(transaction_type: str):
    """Get the full document registry for a transaction type."""
    try:
        registry = load_document_registry(transaction_type)
        priority_counts = get_document_count_by_priority(transaction_type)

        return func.HttpResponse(
            json.dumps({
                "success": True,
                "data": {
                    "transaction_type": transaction_type,
                    "folder_structure": registry.get("folder_structure", []),
                    "categories": list(registry.get("categories", {}).values()),
                    "documents": registry.get("documents", []),
                    "priority_counts": priority_counts
                }
            }),
            mimetype="application/json",
            status_code=200
        )
    except ValueError as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=404
        )


def handle_classify(req: func.HttpRequest):
    """Auto-classify a document based on filename and content preview."""
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body"}),
            mimetype="application/json",
            status_code=400
        )

    filename = body.get("filename")
    content_preview = body.get("content_preview", "")
    transaction_type = body.get("transaction_type")

    if not filename or not transaction_type:
        return func.HttpResponse(
            json.dumps({"error": "filename and transaction_type are required"}),
            mimetype="application/json",
            status_code=400
        )

    category, folder, confidence = classify_document(
        filename=filename,
        content_preview=content_preview,
        transaction_type=transaction_type
    )

    return func.HttpResponse(
        json.dumps({
            "success": True,
            "data": {
                "category": category,
                "folder": folder,
                "confidence": confidence
            }
        }),
        mimetype="application/json",
        status_code=200
    )


def handle_missing(req: func.HttpRequest):
    """Get list of missing documents based on what's uploaded."""
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body"}),
            mimetype="application/json",
            status_code=400
        )

    transaction_type = body.get("transaction_type")
    uploaded_docs = body.get("uploaded_docs", [])
    priority_threshold = body.get("priority_threshold", "required")

    if not transaction_type:
        return func.HttpResponse(
            json.dumps({"error": "transaction_type is required"}),
            mimetype="application/json",
            status_code=400
        )

    try:
        priority_enum = DocumentPriority(priority_threshold)
    except ValueError:
        priority_enum = DocumentPriority.REQUIRED

    missing = get_missing_documents(
        transaction_type=transaction_type,
        uploaded_docs=uploaded_docs,
        priority_threshold=priority_enum
    )

    return func.HttpResponse(
        json.dumps({
            "success": True,
            "data": [
                {
                    "name": doc.name,
                    "category": doc.category,
                    "folder": doc.folder,
                    "priority": doc.priority.value,
                    "description": doc.description,
                    "request_template": doc.request_template
                }
                for doc in missing
            ]
        }),
        mimetype="application/json",
        status_code=200
    )


def handle_request_list(transaction_type: str, priority: str):
    """Generate a document request list."""
    try:
        priority_enum = DocumentPriority(priority)
    except ValueError:
        priority_enum = DocumentPriority.REQUIRED

    request_list = generate_document_request_list(
        transaction_type=transaction_type,
        priority_threshold=priority_enum
    )

    return func.HttpResponse(
        json.dumps({
            "success": True,
            "data": {
                "markdown": request_list,
                "transaction_type": transaction_type,
                "priority": priority
            }
        }),
        mimetype="application/json",
        status_code=200
    )


def handle_folders(transaction_type: str):
    """Get the recommended folder structure."""
    folders = get_folder_structure(transaction_type)
    return func.HttpResponse(
        json.dumps({
            "success": True,
            "data": folders
        }),
        mimetype="application/json",
        status_code=200
    )


def handle_blueprint(transaction_type: str):
    """Get the DD blueprint for a transaction type."""
    try:
        blueprint = load_blueprint(transaction_type)
        return func.HttpResponse(
            json.dumps({
                "success": True,
                "data": blueprint
            }),
            mimetype="application/json",
            status_code=200
        )
    except ValueError as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=404
        )


def _format_transaction_name(code: str) -> str:
    """Convert transaction type code to display name."""
    name_map = {
        "mining_resources": "Mining & Resources",
        "ma_corporate": "M&A / Corporate",
        "banking_finance": "Banking & Finance",
        "real_estate": "Real Estate & Property",
        "competition_regulatory": "Competition & Regulatory",
        "employment_labor": "Employment & Labor",
        "ip_technology": "IP & Technology",
        "bee_transformation": "BEE & Transformation",
        "energy_power": "Energy & Power",
        "infrastructure_ppp": "Infrastructure & PPP"
    }
    return name_map.get(code, code.replace("_", " ").title())
