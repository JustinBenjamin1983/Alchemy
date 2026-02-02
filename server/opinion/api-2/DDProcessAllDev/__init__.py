# DDProcessAllDev - Dev mode document processor using Claude
# This endpoint processes all unprocessed documents in a DD project using Claude AI

import logging
import os
import json
from typing import List, Dict, Any
import azure.functions as func
from shared.session import transactional_session
from shared.models import Document, DueDiligence, DueDiligenceMember, Folder, PerspectiveRisk, PerspectiveRiskFinding, Perspective
from shared.dev_adapters.claude_llm import call_llm_with
from shared.dev_adapters.local_search import add_to_index
from shared.dev_adapters.dev_config import get_dev_config

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"

# Risk analysis prompt template
RISK_ANALYSIS_PROMPT = """You are a legal due diligence expert analyzing documents for a {transaction_type} transaction.

Analyze the following document and identify potential risks, issues, and key findings relevant to due diligence.

IMPORTANT: The document text contains [PAGE X] markers indicating page boundaries.
For EACH finding, you MUST extract the actual page number from these markers.

Document: {filename}
Content:
{content}

For each risk found, provide:
1. Risk Category (e.g., Regulatory Compliance, Financial, Legal, Operational, Environmental)
2. Severity: High, Medium, or Low
3. Description: Brief description of the risk
4. Specific Finding: The exact clause, provision, or issue found
5. Page Number: The ACTUAL page number (integer) from the [PAGE X] markers where this was found
6. Clause Reference: The clause/section reference (e.g., "Clause 8.2.5")
7. Recommendation: Suggested action or further investigation needed

Respond in JSON format:
{{
    "document_summary": "Brief summary of document contents",
    "risks": [
        {{
            "category": "category name",
            "severity": "High|Medium|Low",
            "description": "risk description",
            "finding": "specific text or clause that raises concern",
            "actual_page_number": 1,
            "clause_reference": "Clause X.X",
            "recommendation": "suggested action"
        }}
    ],
    "key_dates": ["list of important dates mentioned"],
    "key_parties": ["list of parties mentioned"],
    "key_obligations": ["list of key obligations identified"]
}}
"""


def extract_text_from_file(file_path: str) -> str:
    """Extract text content from a file (PDF, DOCX, TXT)"""
    import os

    if not os.path.exists(file_path):
        logging.warning(f"File not found: {file_path}")
        return ""

    ext = os.path.splitext(file_path)[1].lower()
    return extract_text_from_file_with_extension(file_path, ext.lstrip('.'))


def extract_text_from_file_with_extension(file_path: str, extension: str) -> str:
    """Extract text content from a file, using the provided extension to determine file type.
    This is needed because in dev mode files are stored without extensions."""
    import os

    if not os.path.exists(file_path):
        logging.warning(f"File not found: {file_path}")
        return ""

    ext = extension.lower().lstrip('.')

    try:
        if ext == 'txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()

        elif ext == 'pdf':
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(file_path)
                text_parts = []
                for page_num, page in enumerate(doc, start=1):
                    page_text = page.get_text()
                    if page_text.strip():
                        text_parts.append(f"\n[PAGE {page_num}]\n{page_text}")
                doc.close()
                return "".join(text_parts)
            except ImportError:
                logging.warning("PyMuPDF not installed, trying pdfplumber")
                try:
                    import pdfplumber
                    with pdfplumber.open(file_path) as pdf:
                        text_parts = []
                        for page_num, page in enumerate(pdf.pages, start=1):
                            page_text = page.extract_text() or ""
                            if page_text.strip():
                                text_parts.append(f"\n[PAGE {page_num}]\n{page_text}")
                        return "".join(text_parts)
                except ImportError:
                    logging.error("No PDF library available")
                    return f"[PDF file - {os.path.basename(file_path)}]"

        elif ext in ['docx', 'doc']:
            try:
                from docx import Document as DocxDocument
                doc = DocxDocument(file_path)
                return "\n".join([para.text for para in doc.paragraphs])
            except ImportError:
                logging.error("python-docx not installed")
                return f"[Word document - {os.path.basename(file_path)}]"
            except Exception as e:
                logging.error(f"Error reading docx: {e}")
                # Try reading as binary and extracting text
                return ""

        else:
            # Try to read as text
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()

    except Exception as e:
        logging.error(f"Error extracting text from {file_path}: {e}")
        return ""


def analyze_document_with_claude(filename: str, content: str, transaction_type: str) -> Dict:
    """Use Claude to analyze a document for risks"""

    # Truncate content if too long (Claude has context limits)
    max_content_length = 100000  # ~25k tokens
    if len(content) > max_content_length:
        content = content[:max_content_length] + "\n\n[Content truncated due to length...]"

    prompt = RISK_ANALYSIS_PROMPT.format(
        transaction_type=transaction_type,
        filename=filename,
        content=content
    )

    messages = [
        {"role": "system", "content": "You are an expert legal due diligence analyst. Respond only with valid JSON."},
        {"role": "user", "content": prompt}
    ]

    try:
        response = call_llm_with(
            messages=messages,
            temperature=0,
            max_tokens=4000
        )

        # Parse JSON from response
        # Find JSON object in response
        start = response.find('{')
        end = response.rfind('}') + 1
        if start != -1 and end > start:
            json_str = response[start:end]
            return json.loads(json_str)
        else:
            logging.warning(f"No JSON found in Claude response for {filename}")
            return {"document_summary": "Analysis failed - no structured output", "risks": []}

    except json.JSONDecodeError as e:
        logging.error(f"JSON parse error for {filename}: {e}")
        return {"document_summary": "Analysis failed - JSON parse error", "risks": []}
    except Exception as e:
        logging.error(f"Claude analysis error for {filename}: {e}")
        return {"document_summary": f"Analysis failed: {str(e)}", "risks": []}


def main(req: func.HttpRequest) -> func.HttpResponse:
    """Process all unprocessed documents in a DD project using Claude"""

    # Only allow in dev mode
    if not DEV_MODE:
        return func.HttpResponse(
            json.dumps({"error": "This endpoint is only available in dev mode"}),
            status_code=403,
            mimetype="application/json"
        )

    try:
        dd_id_str = req.params.get('dd_id')
        if not dd_id_str:
            return func.HttpResponse(
                json.dumps({"error": "dd_id parameter required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Convert to UUID for proper comparison
        import uuid as uuid_module
        try:
            dd_id = uuid_module.UUID(dd_id_str)
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid dd_id format"}),
                status_code=400,
                mimetype="application/json"
            )

        logging.info(f"[DDProcessAllDev] Starting processing for DD: {dd_id}")

        with transactional_session() as session:
            # Get the DD and its documents
            dd = session.query(DueDiligence).filter(DueDiligence.id == dd_id).first()
            if not dd:
                return func.HttpResponse(
                    json.dumps({"error": "DD not found"}),
                    status_code=404,
                    mimetype="application/json"
                )

            # Get transaction type from dd.project_setup (linked by dd_id)
            project_setup = dd.project_setup or {}
            transaction_type = project_setup.get("transactionType") or "General"

            # Get all documents that haven't been processed
            # Include 'Queued' which is the status after ZIP extraction
            documents = session.query(Document).join(Folder).filter(
                Folder.dd_id == dd_id,
                Document.processing_status.in_(['uploaded', 'not_started', 'Not started', 'Queued', 'queued'])
            ).all()

            if not documents:
                return func.HttpResponse(
                    json.dumps({
                        "message": "No unprocessed documents found",
                        "processed": 0,
                        "risks_found": 0
                    }),
                    status_code=200,
                    mimetype="application/json"
                )

            logging.info(f"[DDProcessAllDev] Found {len(documents)} documents to process")

            # Get or create a member for the DD owner (needed for perspective)
            # Use str() to ensure consistent comparison
            logging.info(f"[DDProcessAllDev] Looking for member: dd_id={dd_id}, email={dd.owned_by}")
            member = session.query(DueDiligenceMember).filter(
                DueDiligenceMember.dd_id == str(dd_id),
                DueDiligenceMember.member_email == dd.owned_by
            ).first()
            logging.info(f"[DDProcessAllDev] Found member: {member}")

            if not member:
                # Double-check with raw SQL to debug
                from sqlalchemy import text
                result = session.execute(
                    text("SELECT id FROM due_diligence_member WHERE dd_id = :dd_id AND member_email = :email"),
                    {"dd_id": str(dd_id), "email": dd.owned_by}
                ).fetchone()
                if result:
                    logging.info(f"[DDProcessAllDev] Found member via raw SQL: {result[0]}")
                    member = session.query(DueDiligenceMember).filter(
                        DueDiligenceMember.id == result[0]
                    ).first()
                else:
                    logging.info(f"[DDProcessAllDev] Creating new member")
                    member = DueDiligenceMember(
                        dd_id=str(dd_id),
                        member_email=dd.owned_by
                    )
                    session.add(member)
                    session.flush()

            # Get or create the default perspective for findings
            perspective = session.query(Perspective).filter(
                Perspective.member_id == member.id
            ).first()

            if not perspective:
                perspective = Perspective(
                    member_id=member.id,
                    lens="AI Analysis - Automated risk analysis"
                )
                session.add(perspective)
                session.flush()

            processed_count = 0
            total_risks_found = 0
            results = []

            for doc in documents:
                logging.info(f"[DDProcessAllDev] Processing: {doc.original_file_name}")

                # Update status to processing
                doc.processing_status = 'processing'
                session.flush()

                try:
                    # Get file path - in dev mode, files are stored by document ID in .local_storage/docs/
                    dev_config = get_dev_config()
                    local_storage_path = dev_config.get("local_storage_path", "/tmp/dd_storage")

                    # Files are stored as {doc_id} (without extension), with metadata in {doc_id}.meta.json
                    file_path = os.path.join(local_storage_path, "docs", str(doc.id))

                    # Get extension from document type
                    extension = doc.type if doc.type else os.path.splitext(doc.original_file_name)[1].lstrip('.')

                    logging.info(f"[DDProcessAllDev] Looking for file at: {file_path} (extension: {extension})")

                    # Extract text
                    content = extract_text_from_file_with_extension(file_path, extension)

                    if not content:
                        logging.warning(f"[DDProcessAllDev] No content extracted from {doc.original_file_name}")
                        doc.processing_status = 'error'
                        results.append({
                            "filename": doc.original_file_name,
                            "status": "error",
                            "message": "Could not extract text content"
                        })
                        continue

                    # Analyze with Claude
                    analysis = analyze_document_with_claude(
                        doc.original_file_name,
                        content,
                        transaction_type
                    )

                    # Index the content for search
                    add_to_index(f"dd_{dd_id}", [{
                        'id': str(doc.id),
                        'content': content,
                        'filename': doc.original_file_name,
                        'doc_id': str(doc.id),
                        'folder_id': str(doc.folder_id)
                    }])

                    # Create risk findings
                    risks = analysis.get('risks', [])
                    for risk_data in risks:
                        # Get or create the risk category
                        category = risk_data.get('category', 'General')
                        description = risk_data.get('description', f"Risks related to {category}")

                        risk = session.query(PerspectiveRisk).filter(
                            PerspectiveRisk.perspective_id == perspective.id,
                            PerspectiveRisk.category == category
                        ).first()

                        if not risk:
                            risk = PerspectiveRisk(
                                perspective_id=perspective.id,
                                category=category,
                                detail=description
                            )
                            session.add(risk)
                            session.flush()

                        # Map severity to status
                        # critical and high both map to Red, medium to Amber, low to Green
                        severity = risk_data.get('severity', 'medium').lower()
                        status_map = {'critical': 'Red', 'high': 'Red', 'medium': 'Amber', 'low': 'Green'}
                        finding_status = status_map.get(severity, 'Amber')

                        # Build the phrase from finding + recommendation
                        finding_text = risk_data.get('finding', '')
                        recommendation = risk_data.get('recommendation', '')
                        phrase = f"{finding_text}\n\nRecommendation: {recommendation}" if recommendation else finding_text

                        finding = PerspectiveRiskFinding(
                            perspective_risk_id=risk.id,
                            document_id=doc.id,
                            phrase=phrase or "See document for details",
                            page_number=risk_data.get('clause_reference') or risk_data.get('reference', 'N/A'),
                            actual_page_number=risk_data.get('actual_page_number'),  # Integer page from [PAGE X] markers
                            clause_reference=risk_data.get('clause_reference'),
                            status=finding_status,
                            finding_type='negative',
                            confidence_score=0.8,
                            requires_action=severity in ('critical', 'high'),
                            action_priority=severity if severity in ('critical', 'high', 'medium', 'low') else 'medium',
                            direct_answer=description,
                            evidence_quote=finding_text
                        )
                        session.add(finding)
                        total_risks_found += 1

                    # Update document status
                    doc.processing_status = 'processed'
                    processed_count += 1

                    results.append({
                        "filename": doc.original_file_name,
                        "status": "processed",
                        "risks_found": len(risks),
                        "summary": analysis.get('document_summary', '')[:200]
                    })

                    logging.info(f"[DDProcessAllDev] Processed {doc.original_file_name}: {len(risks)} risks found")

                except Exception as e:
                    logging.error(f"[DDProcessAllDev] Error processing {doc.original_file_name}: {e}")
                    doc.processing_status = 'error'
                    results.append({
                        "filename": doc.original_file_name,
                        "status": "error",
                        "message": str(e)
                    })

            session.commit()

            return func.HttpResponse(
                json.dumps({
                    "message": f"Processing complete",
                    "processed": processed_count,
                    "total_documents": len(documents),
                    "risks_found": total_risks_found,
                    "results": results
                }),
                status_code=200,
                mimetype="application/json"
            )

    except Exception as e:
        logging.exception(f"[DDProcessAllDev] Error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
