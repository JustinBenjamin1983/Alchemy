# DDClassifyDocuments/__init__.py
"""
AI Document Classification Endpoint

Classifies documents in a DD project using Claude Haiku.
For each document:
1. Extracts first ~2000 tokens of text content
2. Calls Claude Haiku to classify into standardised categories
3. Extracts key parties mentioned in the document
4. Updates document record with classification results
5. Tracks progress in dd_organisation_status

This is Phase 1 of the Document Organisation feature.
"""
import logging
import os
import json
import datetime
import azure.functions as func

from shared.utils import auth_get_email
from shared.session import transactional_session
from shared.models import Document, Folder, DueDiligence, DDOrganisationStatus
from shared.audit import log_audit_event, AuditEventType

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"
LOCAL_STORAGE_PATH = os.environ.get("LOCAL_STORAGE_PATH", "")

# Standardised folder categories for classification
FOLDER_CATEGORIES = [
    "01_Corporate",
    "02_Commercial",
    "03_Financial",
    "04_Regulatory",
    "05_Employment",
    "06_Property",
    "07_Insurance",
    "08_Litigation",
    "09_Tax",
    "99_Needs_Review"
]

CLASSIFICATION_SYSTEM_PROMPT = """You are a legal document classifier for due diligence reviews.
Your task is to accurately classify legal and business documents into standardised categories.
Be precise and consistent. Always respond with valid JSON only."""

CLASSIFICATION_PROMPT = """Analyse this document and classify it into the appropriate category.

DOCUMENT CONTENT:
{document_text}

FILENAME: {filename}

Respond in JSON format only:
{{
    "category": "<one of: 01_Corporate, 02_Commercial, 03_Financial, 04_Regulatory, 05_Employment, 06_Property, 07_Insurance, 08_Litigation, 09_Tax, 99_Needs_Review>",
    "subcategory": "<specific subcategory within the category>",
    "document_type": "<specific document type, e.g., 'Shareholders Agreement', 'Mining Right', 'Loan Agreement'>",
    "confidence": <0-100 integer>,
    "key_parties": ["<party name 1>", "<party name 2>"],
    "reasoning": "<brief explanation for classification>"
}}

IMPORTANT Classification rules:
- The FILENAME is a strong indicator - legal documents typically have descriptive names
- If content is not available, classify based on filename with lower confidence (50-70%)
- Be specific with document_type - use exact legal document names
- Extract ALL party names mentioned (companies, individuals, government bodies)
- If genuinely unsure after considering both filename and content, use "99_Needs_Review"

Filename pattern hints:
- "MOI", "Memorandum of Incorporation" → 01_Corporate
- "Shareholders Agreement", "SHA" → 01_Corporate
- "Board Resolution" → 01_Corporate
- "Employment", "Contract" with person name → 05_Employment
- "MSA", "Service Agreement", "Supply Agreement", "SPA" (Sale and Purchase) → 02_Commercial
- "Facility", "Loan", "Mezzanine", "AFS" (Annual Financial Statements), "InterCompany" → 03_Financial
- "Insurance", "Surety Bond", "Policy" → 07_Insurance
- "Lease", "Title Deed", "Servitude" → 06_Property
- "BEE", "SARB", "Permit", "License", "Environmental" → 04_Regulatory
- "Tax", "SARS" → 09_Tax
- "Summons", "Court", "Settlement", "Litigation" → 08_Litigation

Category definitions:
- 01_Corporate: Constitutional documents (MOI, Shareholders Agreements), Board Resolutions, Share Certificates, Organograms
- 02_Commercial: Supply agreements, Offtake agreements, Service contracts (MSA), JV agreements, Sale & Purchase agreements (SPA)
- 03_Financial: Loan agreements, Facility agreements, Mezzanine finance, Security documents, Guarantees, Financial statements (AFS), InterCompany loans
- 04_Regulatory: Mining rights, Environmental authorisations, Water use licenses, Permits, BEE certificates, SARB correspondence
- 05_Employment: Employment contracts, HR policies, Union agreements, Benefit plans
- 06_Property: Title deeds, Lease agreements (fleet leases, property leases), Servitudes, Surface rights
- 07_Insurance: Insurance policies, Certificates of insurance, Surety bonds, Claims records
- 08_Litigation: Summons, Pleadings, Settlement agreements, Court orders
- 09_Tax: Tax returns, Tax assessments, Tax rulings, Tax clearance certificates
- 99_Needs_Review: ONLY use if document genuinely cannot be classified from filename or content"""


def get_claude_client():
    """Import and create Claude client (deferred to avoid import errors)."""
    import sys
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)

    from dd_enhanced.core.claude_client import ClaudeClient
    return ClaudeClient()


def extract_text_from_document(doc_id: str, file_type: str) -> str:
    """Extract text content from a document for classification."""
    # Import the existing text extraction utility
    from DDProcessAllDev import extract_text_from_file_with_extension

    if DEV_MODE and LOCAL_STORAGE_PATH:
        file_path = os.path.join(LOCAL_STORAGE_PATH, "docs", doc_id)
    else:
        # For non-dev mode, we'd need to download from blob storage
        # For now, this is DEV_MODE focused
        file_path = os.path.join("/tmp/dd_storage", "docs", doc_id)

    try:
        text = extract_text_from_file_with_extension(file_path, file_type)

        # Truncate to approximately 2000 tokens (~8000 characters)
        max_chars = 8000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[... truncated for classification ...]"

        return text
    except Exception as e:
        logging.warning(f"Failed to extract text from {doc_id}: {e}")
        return ""


def classify_document(client, doc_text: str, filename: str) -> dict:
    """
    Classify a document using Claude Haiku.

    Returns dict with: category, subcategory, document_type, confidence, key_parties, reasoning
    """
    # Even if text extraction failed, try to classify based on filename
    # Many legal documents have descriptive filenames that indicate their type
    if not doc_text.strip():
        logging.info(f"[DDClassifyDocuments] No text extracted for {filename}, attempting filename-based classification")
        doc_text = f"[No text content available - classify based on filename only]\n\nFilename: {filename}"

    prompt = CLASSIFICATION_PROMPT.format(
        document_text=doc_text,
        filename=filename
    )

    try:
        response = client.complete(
            prompt=prompt,
            system=CLASSIFICATION_SYSTEM_PROMPT,
            model="haiku",  # Use Haiku for fast, cheap classification
            max_tokens=1024,
            temperature=0.1,
            json_mode=True
        )

        if "error" in response:
            logging.warning(f"Classification parse error for {filename}: {response.get('error')}")
            # Try to extract what we can from the raw response
            return {
                "category": "99_Needs_Review",
                "subcategory": "Classification Error",
                "document_type": "Unknown",
                "confidence": 0,
                "key_parties": [],
                "reasoning": f"Classification parse error: {response.get('error')}"
            }

        # Validate category
        category = response.get("category", "99_Needs_Review")
        if category not in FOLDER_CATEGORIES:
            category = "99_Needs_Review"

        # Ensure confidence is a number
        confidence = response.get("confidence", 50)
        if not isinstance(confidence, (int, float)):
            try:
                confidence = int(confidence)
            except:
                confidence = 50
        confidence = max(0, min(100, confidence))  # Clamp to 0-100

        # Ensure key_parties is a list
        key_parties = response.get("key_parties", [])
        if not isinstance(key_parties, list):
            key_parties = [key_parties] if key_parties else []

        return {
            "category": category,
            "subcategory": response.get("subcategory", ""),
            "document_type": response.get("document_type", "Unknown"),
            "confidence": confidence,
            "key_parties": key_parties,
            "reasoning": response.get("reasoning", "")
        }

    except Exception as e:
        logging.error(f"Classification API error for {filename}: {e}")
        return {
            "category": "99_Needs_Review",
            "subcategory": "API Error",
            "document_type": "Unknown",
            "confidence": 0,
            "key_parties": [],
            "reasoning": f"API error: {str(e)}"
        }


def update_organisation_status(session, dd_id: str, classified_count: int,
                               total_documents: int, low_confidence_count: int,
                               failed_count: int, category_counts: dict,
                               status: str = "classifying", error_message: str = None):
    """Update the organisation status record for a DD project."""
    import uuid as uuid_module

    dd_uuid = uuid_module.UUID(dd_id) if isinstance(dd_id, str) else dd_id

    org_status = session.query(DDOrganisationStatus).filter(
        DDOrganisationStatus.dd_id == dd_uuid
    ).first()

    if not org_status:
        # Create new status record
        org_status = DDOrganisationStatus(
            dd_id=dd_uuid,
            status=status,
            total_documents=total_documents,
            classified_count=classified_count,
            low_confidence_count=low_confidence_count,
            failed_count=failed_count,
            category_counts=category_counts,
            started_at=datetime.datetime.utcnow() if status == "classifying" else None
        )
        session.add(org_status)
    else:
        org_status.status = status
        org_status.total_documents = total_documents
        org_status.classified_count = classified_count
        org_status.low_confidence_count = low_confidence_count
        org_status.failed_count = failed_count
        org_status.category_counts = category_counts
        org_status.updated_at = datetime.datetime.utcnow()
        if error_message:
            org_status.error_message = error_message
        if status == "completed":
            org_status.completed_at = datetime.datetime.utcnow()

    session.commit()


def classify_documents_for_dd(dd_id: str, reset: bool = False) -> dict:
    """
    Classify all pending documents for a DD project.

    This function can be called directly (e.g., from a background thread in DDStart)
    or via the HTTP endpoint.

    Args:
        dd_id: The UUID of the DD project
        reset: If True, reset all documents to pending status first (for restart)

    Returns:
        dict with classification results including status, counts, and per-document results
    """
    import uuid as uuid_module

    logging.info(f"[DDClassifyDocuments] Starting classification for DD: {dd_id}")

    # Initialize Claude client
    try:
        client = get_claude_client()
    except Exception as e:
        logging.error(f"Failed to initialize Claude client: {e}")
        return {"error": f"Failed to initialize AI client: {str(e)}", "status": "failed"}

    results = []
    category_counts = {cat: 0 for cat in FOLDER_CATEGORIES}
    classified_count = 0
    failed_count = 0
    low_confidence_count = 0

    # Ensure dd_id is a UUID
    dd_uuid = uuid_module.UUID(dd_id) if isinstance(dd_id, str) else dd_id

    with transactional_session() as session:
        # Verify DD exists
        dd = session.query(DueDiligence).filter(DueDiligence.id == dd_uuid).first()
        if not dd:
            return {"error": f"Due diligence {dd_id} not found", "status": "failed"}

        # Get all folders for this DD
        folders = session.query(Folder).filter(Folder.dd_id == dd_uuid).all()
        folder_ids = [f.id for f in folders]

        # If reset=True, reset all documents to pending status first
        if reset:
            logging.info(f"[DDClassifyDocuments] Resetting all documents to pending status")
            all_docs = (
                session.query(Document)
                .filter(
                    Document.folder_id.in_(folder_ids),
                    Document.is_original == False
                )
                .all()
            )
            for doc in all_docs:
                doc.classification_status = "pending"
                doc.ai_category = None
                doc.ai_subcategory = None
                doc.ai_document_type = None
                doc.ai_confidence = None
                doc.ai_key_parties = None
                doc.ai_classification_reasoning = None
                doc.classification_error = None
            session.commit()
            logging.info(f"[DDClassifyDocuments] Reset {len(all_docs)} documents to pending")

        # Get documents that need classification (pending status, not the original ZIP)
        pending_docs = (
            session.query(Document)
            .filter(
                Document.folder_id.in_(folder_ids),
                Document.classification_status == "pending",
                Document.is_original == False
            )
            .all()
        )

        total_documents = len(pending_docs)
        logging.info(f"[DDClassifyDocuments] Found {total_documents} documents to classify")

        if total_documents == 0:
            # Check if there are any classified documents already
            all_docs = (
                session.query(Document)
                .filter(
                    Document.folder_id.in_(folder_ids),
                    Document.is_original == False
                )
                .all()
            )

            if all_docs:
                # Count existing classifications
                for doc in all_docs:
                    if doc.classification_status == "classified" and doc.ai_category:
                        category_counts[doc.ai_category] = category_counts.get(doc.ai_category, 0) + 1
                        classified_count += 1
                        if doc.ai_confidence and doc.ai_confidence < 70:
                            low_confidence_count += 1

            update_organisation_status(
                session, str(dd_uuid), classified_count, len(all_docs),
                low_confidence_count, failed_count, category_counts,
                status="classified"
            )

            return {
                "dd_id": str(dd_uuid),
                "status": "classified",
                "message": "No pending documents to classify - all documents already classified",
                "total_documents": len(all_docs),
                "classified_count": classified_count,
                "category_counts": category_counts
            }

        # Update status to classifying
        update_organisation_status(
            session, str(dd_uuid), 0, total_documents, 0, 0, category_counts,
            status="classifying"
        )

        # Process each document
        for idx, doc in enumerate(pending_docs):
            doc_id = str(doc.id)
            filename = doc.original_file_name
            file_type = doc.type or filename.split('.')[-1] if '.' in filename else 'pdf'

            logging.info(f"[DDClassifyDocuments] Classifying {idx + 1}/{total_documents}: {filename}")

            # Update document status to classifying
            doc.classification_status = "classifying"
            session.commit()

            try:
                # Extract text from document
                doc_text = extract_text_from_document(doc_id, file_type)

                # Even if text extraction fails, we still try to classify based on filename
                # The classify_document function handles empty text by using filename
                if not doc_text.strip():
                    logging.warning(f"[DDClassifyDocuments] No text extracted from {filename} - will classify by filename")

                # Classify document (handles both with-content and filename-only cases)
                classification = classify_document(client, doc_text, filename)

                # Update document with classification results
                doc.ai_category = classification["category"]
                doc.ai_subcategory = classification["subcategory"]
                doc.ai_document_type = classification["document_type"]
                doc.ai_confidence = classification["confidence"]
                doc.ai_key_parties = classification["key_parties"]
                doc.ai_classification_reasoning = classification["reasoning"]
                doc.category_source = "ai"
                doc.classification_status = "classified"
                doc.classification_error = None
                doc.classified_at = datetime.datetime.utcnow()

                session.commit()

                # Log audit event for document classification
                try:
                    log_audit_event(
                        session=session,
                        event_type=AuditEventType.DOCUMENT_CLASSIFIED,
                        entity_type="document",
                        entity_id=doc_id,
                        dd_id=str(dd_uuid),
                        details={
                            "filename": filename,
                            "category": classification["category"],
                            "confidence": classification["confidence"]
                        }
                    )
                    session.commit()
                except Exception as audit_err:
                    logging.warning(f"[DDClassifyDocuments] Audit logging failed: {audit_err}")

                # Update counts
                classified_count += 1
                category_counts[classification["category"]] += 1

                if classification["confidence"] < 70:
                    low_confidence_count += 1

                results.append({
                    "doc_id": doc_id,
                    "filename": filename,
                    "category": classification["category"],
                    "subcategory": classification["subcategory"],
                    "document_type": classification["document_type"],
                    "confidence": classification["confidence"],
                    "key_parties": classification["key_parties"],
                    "status": "classified"
                })

            except Exception as e:
                logging.error(f"[DDClassifyDocuments] Error classifying {filename}: {e}")

                # Mark as failed
                doc.classification_status = "failed"
                doc.classification_error = str(e)[:500]
                doc.ai_category = "99_Needs_Review"
                doc.ai_confidence = 0
                doc.category_source = "ai"
                doc.classified_at = datetime.datetime.utcnow()
                session.commit()

                failed_count += 1
                category_counts["99_Needs_Review"] += 1

                results.append({
                    "doc_id": doc_id,
                    "filename": filename,
                    "status": "failed",
                    "error": str(e)[:200]
                })

            # Update progress after each document
            update_organisation_status(
                session, str(dd_uuid), classified_count, total_documents,
                low_confidence_count, failed_count, category_counts,
                status="classifying"
            )

        # Mark as classified (next step is 'organising' in DDOrganiseFolders)
        # Status flow: pending → classifying → classified → organising → organised → completed
        final_status = "classified" if failed_count < total_documents else "failed"
        update_organisation_status(
            session, str(dd_uuid), classified_count, total_documents,
            low_confidence_count, failed_count, category_counts,
            status=final_status
        )

        # Get cost summary from Claude client
        cost_summary = client.get_cost_summary() if hasattr(client, 'get_cost_summary') else {}

        response = {
            "dd_id": str(dd_uuid),
            "status": final_status,
            "total_documents": total_documents,
            "classified_count": classified_count,
            "failed_count": failed_count,
            "low_confidence_count": low_confidence_count,
            "category_counts": category_counts,
            "results": results,
            "cost": cost_summary
        }

        logging.info(f"[DDClassifyDocuments] Completed: {classified_count}/{total_documents} classified, {failed_count} failed")

        return response


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Classify documents in a DD project.

    POST /api/dd-classify-documents
    Body: {
        "dd_id": "uuid"
    }

    Returns: {
        "dd_id": "uuid",
        "status": "completed|failed",
        "total_documents": 45,
        "classified_count": 43,
        "failed_count": 2,
        "low_confidence_count": 5,
        "category_counts": {"01_Corporate": 10, "02_Commercial": 8, ...},
        "results": [
            {
                "doc_id": "uuid",
                "filename": "example.pdf",
                "category": "01_Corporate",
                "subcategory": "Constitutional",
                "document_type": "Shareholders Agreement",
                "confidence": 92,
                "key_parties": ["ABC Holdings", "XYZ Ltd"],
                "status": "classified|failed"
            }
        ]
    }
    """

    # Auth check
    if not DEV_MODE and req.headers.get('function-key') != os.environ.get("FUNCTION_KEY"):
        logging.info("No matching value in header")
        return func.HttpResponse("", status_code=401)

    try:
        email, err = auth_get_email(req)
        if err:
            return err

        # Parse request body
        try:
            req_body = req.get_json()
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON body"}),
                status_code=400,
                mimetype="application/json"
            )

        dd_id = req_body.get("dd_id")
        reset = req_body.get("reset", False)  # If True, reset all docs and reclassify

        if not dd_id:
            return func.HttpResponse(
                json.dumps({"error": "dd_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Use the shared classification function
        result = classify_documents_for_dd(dd_id, reset=reset)

        # Check for errors in result
        if "error" in result:
            status_code = 404 if "not found" in result.get("error", "") else 500
            return func.HttpResponse(
                json.dumps(result),
                status_code=status_code,
                mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps(result),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"[DDClassifyDocuments] Error: {str(e)}")
        logging.exception("Full traceback:")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
