"""
DDProcessEnhancedStart - Async DD Processing Launcher

This endpoint:
1. Validates the request and creates a checkpoint record
2. Spawns a background thread to run processing
3. Returns 202 Accepted immediately

The frontend polls DDProgressEnhanced to get real-time progress updates.

DEV MODE: Uses threading for background processing (no EventGrid/Durable Functions dependency)
"""
import logging
import os
import json
import threading
import uuid as uuid_module
import datetime
from typing import Dict, Any

import azure.functions as func

from shared.session import transactional_session
from shared.models import (
    Document, DueDiligence, DueDiligenceMember, Folder,
    PerspectiveRisk, PerspectiveRiskFinding, Perspective, DDWizardDraft,
    DDProcessingCheckpoint
)

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"

# Global dict to track running processes (for dev mode)
_running_processes: Dict[str, threading.Thread] = {}


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Start async DD processing.

    Returns 202 Accepted immediately with checkpoint_id.
    Frontend should poll DDProgressEnhanced for updates.

    Query params:
        dd_id: The DD project ID (required)

    Body (optional JSON):
        include_tier3: bool - Include deep-dive questions (default: false)
        use_clustered_pass3: bool - Use optimized Pass 3 (default: true)
    """
    # Only allow in dev mode for now
    if not DEV_MODE:
        return func.HttpResponse(
            json.dumps({"error": "This endpoint is only available in dev mode"}),
            status_code=403,
            mimetype="application/json"
        )

    try:
        # Get dd_id from query params
        dd_id = req.params.get('dd_id')
        if not dd_id:
            return func.HttpResponse(
                json.dumps({"error": "dd_id parameter required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Validate UUID format
        try:
            uuid_module.UUID(dd_id)
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid dd_id format"}),
                status_code=400,
                mimetype="application/json"
            )

        # Parse options from body
        options = {}
        try:
            body = req.get_json()
            options = body if isinstance(body, dict) else {}
        except (ValueError, TypeError):
            pass

        include_tier3 = options.get('include_tier3', False)
        use_clustered_pass3 = options.get('use_clustered_pass3', True)

        logging.info(f"[DDProcessEnhancedStart] Starting async processing for DD: {dd_id}")

        # Check if already processing
        if dd_id in _running_processes:
            thread = _running_processes[dd_id]
            if thread.is_alive():
                return func.HttpResponse(
                    json.dumps({
                        "error": "Processing already in progress for this DD",
                        "dd_id": dd_id
                    }),
                    status_code=409,  # Conflict
                    mimetype="application/json"
                )
            else:
                # Clean up dead thread
                del _running_processes[dd_id]

        # Initialize checkpoint in database
        with transactional_session() as session:
            # Validate DD exists
            dd = session.query(DueDiligence).filter(DueDiligence.id == dd_id).first()
            if not dd:
                return func.HttpResponse(
                    json.dumps({"error": "DD not found"}),
                    status_code=404,
                    mimetype="application/json"
                )

            # Get document count
            folders = session.query(Folder).filter(Folder.dd_id == dd_id).all()
            folder_ids = [f.id for f in folders]

            doc_count = session.query(Document).filter(
                Document.folder_id.in_(folder_ids)
            ).count() if folder_ids else 0

            if doc_count == 0:
                return func.HttpResponse(
                    json.dumps({"error": "No documents found in this DD project"}),
                    status_code=400,
                    mimetype="application/json"
                )

            # Delete existing checkpoint if any
            existing = session.query(DDProcessingCheckpoint).filter(
                DDProcessingCheckpoint.dd_id == dd_id
            ).first()
            if existing:
                session.delete(existing)
                session.flush()

            # Create new checkpoint
            checkpoint = DDProcessingCheckpoint(
                dd_id=dd_id,
                status='processing',
                current_pass=1,
                current_stage='queued',
                total_documents=doc_count,
                documents_processed=0,
                pass1_progress=0,
                pass2_progress=0,
                pass3_progress=0,
                pass4_progress=0,
                findings_total=0,
                findings_critical=0,
                findings_high=0,
                findings_medium=0,
                findings_low=0,
                findings_deal_blockers=0,
                findings_cps=0,
                total_input_tokens=0,
                total_output_tokens=0,
                estimated_cost_usd=0.0,
                started_at=datetime.datetime.utcnow()
            )
            session.add(checkpoint)
            session.commit()

            checkpoint_id = str(checkpoint.id)

        # Spawn background thread
        thread = threading.Thread(
            target=_run_processing_in_background,
            args=(dd_id, checkpoint_id, include_tier3, use_clustered_pass3),
            daemon=True
        )
        thread.start()
        _running_processes[dd_id] = thread

        logging.info(f"[DDProcessEnhancedStart] Background thread started for DD: {dd_id}")

        return func.HttpResponse(
            json.dumps({
                "status": "accepted",
                "message": "Processing started",
                "dd_id": dd_id,
                "checkpoint_id": checkpoint_id,
                "total_documents": doc_count,
                "poll_url": f"/api/dd-progress-enhanced?dd_id={dd_id}"
            }),
            status_code=202,
            mimetype="application/json"
        )

    except Exception as e:
        logging.exception(f"[DDProcessEnhancedStart] Error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def _run_processing_in_background(
    dd_id: str,
    checkpoint_id: str,
    include_tier3: bool,
    use_clustered_pass3: bool
):
    """
    Background worker that processes DD with granular checkpoint updates.

    This runs in a separate thread and updates the checkpoint after:
    - Each document in Pass 1
    - Each document in Pass 2
    - Each cluster in Pass 3
    - Pass 4 completion
    """
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dd_enhanced'))

    from shared.dev_adapters.dev_config import get_dev_config
    from config.blueprints.loader import load_blueprint
    from core.claude_client import ClaudeClient
    from core.document_clusters import group_documents_by_cluster
    from core.question_prioritizer import prioritize_questions

    try:
        logging.info(f"[BackgroundProcessor] Starting for DD: {dd_id}")

        # Phase 1: Load data
        _update_checkpoint(checkpoint_id, {
            'current_stage': 'loading_data',
            'current_pass': 1
        })

        load_result = _load_dd_data_for_processing(dd_id)
        if load_result.get("error"):
            _update_checkpoint(checkpoint_id, {
                'status': 'failed',
                'last_error': load_result["error"]
            })
            return

        doc_dicts = load_result["doc_dicts"]
        blueprint = load_result["blueprint"]
        transaction_context = load_result["transaction_context"]
        transaction_context_str = load_result["transaction_context_str"]
        reference_docs = load_result["reference_docs"]
        owned_by = load_result["owned_by"]

        total_docs = len(doc_dicts)

        _update_checkpoint(checkpoint_id, {
            'current_stage': 'pass1_extraction',
            'total_documents': total_docs
        })

        # Initialize Claude client
        client = ClaudeClient()

        # ===== PASS 1: Extract (with per-document updates) =====
        logging.info(f"[BackgroundProcessor] Pass 1: Extracting from {total_docs} documents")

        pass1_results = _run_pass1_with_progress(
            doc_dicts, client, checkpoint_id, total_docs
        )

        # ===== Prioritize questions for Pass 2 =====
        prioritized_questions = prioritize_questions(
            blueprint=blueprint,
            transaction_context=transaction_context,
            include_tier3=include_tier3,
            max_questions=150
        )

        total_questions = sum(len(q.get("questions", [])) for q in prioritized_questions)

        _update_checkpoint(checkpoint_id, {
            'current_pass': 2,
            'current_stage': 'pass2_analysis',
            'pass1_progress': 100,
            'total_questions': total_questions
        })

        # ===== PASS 2: Per-document analysis (with per-document updates) =====
        logging.info(f"[BackgroundProcessor] Pass 2: Analyzing {total_docs} documents")

        pass2_findings = _run_pass2_with_progress(
            doc_dicts, reference_docs, blueprint, client, checkpoint_id,
            transaction_context_str, prioritized_questions, total_docs
        )

        # ===== PASS 3: Cross-document analysis =====
        _update_checkpoint(checkpoint_id, {
            'current_pass': 3,
            'current_stage': 'pass3_crossdoc',
            'pass2_progress': 100
        })

        logging.info("[BackgroundProcessor] Pass 3: Cross-document analysis")

        if use_clustered_pass3:
            pass3_results = _run_pass3_clustered_with_progress(
                doc_dicts, pass1_results, blueprint, client, checkpoint_id
            )
        else:
            pass3_results = _run_pass3_simple(
                doc_dicts, pass2_findings, blueprint, client
            )
            _update_checkpoint(checkpoint_id, {'pass3_progress': 100})

        # ===== PASS 4: Synthesis =====
        _update_checkpoint(checkpoint_id, {
            'current_pass': 4,
            'current_stage': 'pass4_synthesis',
            'pass3_progress': 100
        })

        logging.info("[BackgroundProcessor] Pass 4: Final synthesis")

        from core.pass4_synthesize import run_pass4_synthesis
        pass4_results = run_pass4_synthesis(
            doc_dicts, pass1_results, pass2_findings, pass3_results, client, verbose=False
        )

        _update_checkpoint(checkpoint_id, {
            'pass4_progress': 100,
            'current_stage': 'storing_findings'
        })

        # ===== Store findings =====
        logging.info("[BackgroundProcessor] Storing findings in database")

        store_result = _store_findings_to_db(
            dd_id, owned_by, doc_dicts, pass4_results, pass3_results, blueprint
        )

        # Get final cost summary
        cost_summary = client.get_cost_summary()

        # Update checkpoint with final stats
        all_findings = pass4_results.get("all_findings", [])
        cross_doc_findings = pass3_results.get("cross_doc_findings", [])

        # Count findings by severity
        critical = sum(1 for f in all_findings if f.get("severity") == "critical")
        high = sum(1 for f in all_findings if f.get("severity") == "high")
        medium = sum(1 for f in all_findings if f.get("severity") == "medium")
        low = sum(1 for f in all_findings if f.get("severity") == "low")

        deal_blockers = sum(1 for f in all_findings if f.get("deal_impact") == "deal_blocker")
        cps = sum(1 for f in all_findings if f.get("deal_impact") == "condition_precedent")

        _update_checkpoint(checkpoint_id, {
            'status': 'completed',
            'current_stage': 'completed',
            'completed_at': datetime.datetime.utcnow(),
            'findings_total': len(all_findings) + len(cross_doc_findings),
            'findings_critical': critical,
            'findings_high': high,
            'findings_medium': medium,
            'findings_low': low,
            'findings_deal_blockers': deal_blockers,
            'findings_cps': cps,
            'total_input_tokens': cost_summary['total_input_tokens'],
            'total_output_tokens': cost_summary['total_output_tokens'],
            'estimated_cost_usd': cost_summary['total_cost_usd'],
            'cost_by_model': cost_summary['breakdown']
        })

        logging.info(f"[BackgroundProcessor] Processing complete for DD: {dd_id}")

    except Exception as e:
        logging.exception(f"[BackgroundProcessor] Error: {e}")
        _update_checkpoint(checkpoint_id, {
            'status': 'failed',
            'last_error': str(e)[:1000],
            'retry_count': 1
        })

    finally:
        # Clean up thread reference
        if dd_id in _running_processes:
            del _running_processes[dd_id]


def _update_checkpoint(checkpoint_id: str, updates: Dict[str, Any]):
    """Update checkpoint with fresh database session."""
    try:
        with transactional_session() as session:
            checkpoint = session.query(DDProcessingCheckpoint).filter(
                DDProcessingCheckpoint.id == checkpoint_id
            ).first()
            if checkpoint:
                for key, value in updates.items():
                    setattr(checkpoint, key, value)
                checkpoint.last_updated = datetime.datetime.utcnow()
                session.commit()
    except Exception as e:
        logging.warning(f"[BackgroundProcessor] Failed to update checkpoint: {e}")


def _load_dd_data_for_processing(dd_id: str) -> Dict[str, Any]:
    """Load DD data for processing."""
    from config.blueprints.loader import load_blueprint
    from shared.dev_adapters.dev_config import get_dev_config
    from DDProcessAllDev import extract_text_from_file_with_extension

    try:
        with transactional_session() as session:
            dd = session.query(DueDiligence).filter(DueDiligence.id == dd_id).first()
            if not dd:
                return {"error": "DD not found"}

            dd_name = dd.name
            dd_briefing = dd.briefing
            owned_by = dd.owned_by

            # Get wizard draft for transaction context
            draft = session.query(DDWizardDraft).filter(
                DDWizardDraft.owned_by == owned_by,
                DDWizardDraft.transaction_name == dd_name
            ).first()

            transaction_type = draft.transaction_type if draft else "General"
            transaction_type_code = _map_transaction_type(transaction_type)

            # Load blueprint
            try:
                blueprint = load_blueprint(transaction_type_code)
            except ValueError:
                blueprint = load_blueprint("ma_corporate")

            # Build transaction context
            transaction_context = {}
            if draft:
                if draft.known_concerns:
                    try:
                        transaction_context['known_concerns'] = json.loads(draft.known_concerns)
                    except:
                        pass
                if draft.critical_priorities:
                    try:
                        transaction_context['critical_priorities'] = json.loads(draft.critical_priorities)
                    except:
                        pass

            # Get folders and documents
            folders = session.query(Folder).filter(Folder.dd_id == dd_id).all()
            folder_ids = [f.id for f in folders]
            folder_lookup = {str(f.id): f for f in folders}

            documents = session.query(Document).filter(
                Document.folder_id.in_(folder_ids)
            ).all()

            if not documents:
                return {"error": "No documents found"}

            # Extract document content
            dev_config = get_dev_config()
            local_storage_path = dev_config.get("local_storage_path", "/tmp/dd_storage")

            doc_dicts = []
            for doc in documents:
                file_path = os.path.join(local_storage_path, "docs", str(doc.id))
                extension = doc.type if doc.type else os.path.splitext(doc.original_file_name)[1].lstrip('.')

                try:
                    content = extract_text_from_file_with_extension(file_path, extension)
                except:
                    content = ""

                if content:
                    folder = folder_lookup.get(str(doc.folder_id))
                    doc_dicts.append({
                        "id": str(doc.id),
                        "filename": doc.original_file_name,
                        "text": content,
                        "doc_type": _classify_doc_type(doc.original_file_name, folder),
                        "word_count": len(content.split()),
                        "folder_path": folder.path if folder else ""
                    })

            if not doc_dicts:
                return {"error": "Could not extract content from any documents"}

            # Identify reference documents
            reference_docs = [d for d in doc_dicts if d.get("doc_type") in ["constitutional", "governance"]]

            # Build transaction context string
            transaction_context_str = f"This is a {blueprint.get('transaction_type', 'corporate')} transaction.\nProject: {dd_name}"
            if dd_briefing:
                transaction_context_str += f"\nBriefing: {dd_briefing}"

            return {
                "doc_dicts": doc_dicts,
                "blueprint": blueprint,
                "transaction_context": transaction_context,
                "transaction_context_str": transaction_context_str,
                "reference_docs": reference_docs,
                "owned_by": owned_by,
                "dd_name": dd_name
            }

    except Exception as e:
        logging.exception(f"[BackgroundProcessor] Error loading DD data: {e}")
        return {"error": str(e)}


def _run_pass1_with_progress(doc_dicts, client, checkpoint_id, total_docs):
    """Run Pass 1 with per-document progress updates."""
    from core.pass1_extract import extract_document

    combined_results = {
        "key_dates": [],
        "financial_figures": [],
        "coc_clauses": [],
        "consent_requirements": [],
        "key_parties": [],
        "document_summaries": {}
    }

    for idx, doc in enumerate(doc_dicts):
        try:
            _update_checkpoint(checkpoint_id, {
                'current_document_id': doc.get("id"),
                'current_document_name': doc.get("filename", ""),
                'documents_processed': idx,
                'pass1_progress': int((idx / total_docs) * 100)
            })

            result = extract_document(doc, client)

            # Merge results
            combined_results["key_dates"].extend(result.get("key_dates", []))
            combined_results["financial_figures"].extend(result.get("financial_figures", []))
            combined_results["coc_clauses"].extend(result.get("coc_clauses", []))
            combined_results["consent_requirements"].extend(result.get("consent_requirements", []))
            combined_results["key_parties"].extend(result.get("key_parties", []))
            combined_results["document_summaries"][doc["filename"]] = result.get("summary", "")

        except Exception as e:
            logging.warning(f"[BackgroundProcessor] Pass 1 error for {doc.get('filename')}: {e}")

    _update_checkpoint(checkpoint_id, {
        'documents_processed': total_docs,
        'pass1_progress': 100,
        'pass1_extractions': combined_results,
        'current_document_name': None
    })

    return combined_results


def _run_pass2_with_progress(
    doc_dicts, reference_docs, blueprint, client, checkpoint_id,
    transaction_context_str, prioritized_questions, total_docs
):
    """Run Pass 2 with per-document progress updates."""
    from core.pass2_analyze import analyze_document

    all_findings = []

    # Create RefDoc objects
    class RefDoc:
        def __init__(self, d):
            self.filename = d['filename']
            self.text = d['text']
            self.doc_type = d.get('doc_type', '')

    ref_doc_objects = [RefDoc(d) for d in reference_docs]

    for idx, doc in enumerate(doc_dicts):
        try:
            _update_checkpoint(checkpoint_id, {
                'current_document_id': doc.get("id"),
                'current_document_name': doc.get("filename", ""),
                'documents_processed': idx,
                'pass2_progress': int((idx / total_docs) * 100)
            })

            findings = analyze_document(
                doc, ref_doc_objects, blueprint, client,
                transaction_context=transaction_context_str,
                prioritized_questions=prioritized_questions
            )

            # Update finding counts as we go
            if findings:
                all_findings.extend(findings)
                critical = sum(1 for f in all_findings if f.get("severity") == "critical")
                high = sum(1 for f in all_findings if f.get("severity") == "high")

                _update_checkpoint(checkpoint_id, {
                    'findings_total': len(all_findings),
                    'findings_critical': critical,
                    'findings_high': high
                })

        except Exception as e:
            logging.warning(f"[BackgroundProcessor] Pass 2 error for {doc.get('filename')}: {e}")

    _update_checkpoint(checkpoint_id, {
        'documents_processed': total_docs,
        'pass2_progress': 100,
        'current_document_name': None
    })

    return all_findings


def _run_pass3_clustered_with_progress(doc_dicts, pass1_results, blueprint, client, checkpoint_id):
    """Run Pass 3 with per-cluster progress updates."""
    from core.document_clusters import group_documents_by_cluster
    from core.pass3_clustered import analyze_cluster

    clustered_docs = group_documents_by_cluster(doc_dicts)
    total_clusters = len(clustered_docs)

    _update_checkpoint(checkpoint_id, {
        'clusters_total': total_clusters,
        'clusters_processed': {}
    })

    all_cross_doc_findings = []
    clusters_status = {}

    for idx, (cluster_name, docs) in enumerate(clustered_docs.items()):
        try:
            _update_checkpoint(checkpoint_id, {
                'current_stage': f'pass3_{cluster_name}',
                'pass3_progress': int((idx / total_clusters) * 100)
            })

            cluster_results = analyze_cluster(
                cluster_name, docs, pass1_results, blueprint, client
            )

            findings = cluster_results.get("cross_doc_findings", [])
            all_cross_doc_findings.extend(findings)
            clusters_status[cluster_name] = {"status": "completed", "findings": len(findings)}

            _update_checkpoint(checkpoint_id, {
                'clusters_processed': clusters_status
            })

        except Exception as e:
            logging.warning(f"[BackgroundProcessor] Pass 3 error for cluster {cluster_name}: {e}")
            clusters_status[cluster_name] = {"status": "error", "error": str(e)}

    return {
        "cross_doc_findings": all_cross_doc_findings,
        "clusters_analyzed": total_clusters,
        "conflicts": [],
        "cascade_analysis": {"cascade_items": []},
        "authorization_issues": [],
        "consent_matrix": []
    }


def _run_pass3_simple(doc_dicts, pass2_findings, blueprint, client):
    """Run simple Pass 3 without clustering."""
    from core.pass3_crossdoc import run_pass3_crossdoc_synthesis
    return run_pass3_crossdoc_synthesis(doc_dicts, pass2_findings, blueprint, client, verbose=False)


def _store_findings_to_db(dd_id, owned_by, doc_dicts, pass4_results, pass3_results, blueprint):
    """Store all findings to database."""
    try:
        with transactional_session() as session:
            # Get folders and documents
            folders = session.query(Folder).filter(Folder.dd_id == dd_id).all()
            folder_ids = [f.id for f in folders]

            documents = session.query(Document).filter(
                Document.folder_id.in_(folder_ids)
            ).all()

            doc_lookup = {doc.original_file_name: doc for doc in documents}

            # Get or create member
            member = session.query(DueDiligenceMember).filter(
                DueDiligenceMember.dd_id == dd_id,
                DueDiligenceMember.member_email == owned_by
            ).first()

            if not member:
                member = DueDiligenceMember(dd_id=dd_id, member_email=owned_by)
                session.add(member)
                session.flush()

            # Get or create perspective
            perspective = session.query(Perspective).filter(
                Perspective.member_id == member.id,
                Perspective.lens == "Enhanced AI Analysis"
            ).first()

            if not perspective:
                perspective = Perspective(member_id=member.id, lens="Enhanced AI Analysis")
                session.add(perspective)
                session.flush()

            # Store findings
            all_findings = pass4_results.get("all_findings", [])
            risk_cache = {}
            stored_count = 0

            for finding in all_findings:
                try:
                    category = finding.get("category", "General")

                    if category not in risk_cache:
                        risk = session.query(PerspectiveRisk).filter(
                            PerspectiveRisk.perspective_id == perspective.id,
                            PerspectiveRisk.category == category
                        ).first()

                        if not risk:
                            risk = PerspectiveRisk(
                                perspective_id=perspective.id,
                                category=category,
                                detail=f"Risks related to {category}"
                            )
                            session.add(risk)
                            session.flush()

                        risk_cache[category] = risk

                    risk = risk_cache[category]

                    # Get document
                    source_doc = finding.get("source_document", "")
                    doc = doc_lookup.get(source_doc)
                    doc_id = doc.id if doc else None

                    # Map severity
                    severity = finding.get("severity", "medium")
                    status_map = {"critical": "Red", "high": "Red", "medium": "Amber", "low": "Green"}
                    status = status_map.get(severity.lower(), "Amber")

                    # Create finding
                    db_finding = PerspectiveRiskFinding(
                        perspective_risk_id=risk.id,
                        document_id=doc_id,
                        phrase=finding.get("description", "")[:2000],
                        page_number=finding.get("clause_reference", ""),
                        status=status,
                        finding_type=finding.get("finding_type", "negative"),
                        confidence_score=0.85,
                        requires_action=finding.get("deal_impact") in ["deal_blocker", "condition_precedent"],
                        action_priority=_map_priority(finding.get("deal_impact")),
                        direct_answer=finding.get("action_required", "")[:500] if finding.get("action_required") else "",
                        evidence_quote=finding.get("evidence_quote", "")[:500] if finding.get("evidence_quote") else "",
                        deal_impact=finding.get("deal_impact", "none") if finding.get("deal_impact") else "none",
                        clause_reference=finding.get("clause_reference", "")[:100] if finding.get("clause_reference") else None,
                        analysis_pass=finding.get("pass", 2)
                    )
                    session.add(db_finding)
                    stored_count += 1

                except Exception as e:
                    logging.warning(f"[BackgroundProcessor] Could not store finding: {e}")

            # Store cross-doc findings
            cross_doc_findings = pass3_results.get("cross_doc_findings", [])

            cross_doc_risk = session.query(PerspectiveRisk).filter(
                PerspectiveRisk.perspective_id == perspective.id,
                PerspectiveRisk.category == "Cross-Document Analysis"
            ).first()

            if not cross_doc_risk and cross_doc_findings:
                cross_doc_risk = PerspectiveRisk(
                    perspective_id=perspective.id,
                    category="Cross-Document Analysis",
                    detail="Issues identified by analyzing multiple documents together"
                )
                session.add(cross_doc_risk)
                session.flush()

            for finding in cross_doc_findings:
                try:
                    severity = finding.get("severity", "high")
                    status_map = {"critical": "Red", "high": "Red", "medium": "Amber", "low": "Green"}
                    status = status_map.get(severity.lower(), "Amber")

                    db_finding = PerspectiveRiskFinding(
                        perspective_risk_id=cross_doc_risk.id,
                        document_id=None,
                        phrase=finding.get("description", "")[:2000],
                        page_number=finding.get("clause_reference", ""),
                        status=status,
                        finding_type="conflict",
                        confidence_score=0.9,
                        requires_action=True,
                        action_priority="high",
                        direct_answer=finding.get("action_required", "")[:500] if finding.get("action_required") else "",
                        deal_impact="condition_precedent",
                        cross_doc_source=finding.get("source_document", "")[:200],
                        analysis_pass=3
                    )
                    session.add(db_finding)
                    stored_count += 1

                except Exception as e:
                    logging.warning(f"[BackgroundProcessor] Could not store cross-doc finding: {e}")

            # Update document statuses
            for doc in documents:
                doc.processing_status = 'processed'

            session.commit()

            return {"stored_count": stored_count}

    except Exception as e:
        logging.exception(f"[BackgroundProcessor] Error storing findings: {e}")
        return {"error": str(e)}


def _map_transaction_type(transaction_type: str) -> str:
    """Map transaction type to blueprint code."""
    mapping = {
        "Mining & Resources": "mining_resources",
        "M&A / Corporate": "ma_corporate",
        "Banking & Finance": "banking_finance",
        "Real Estate": "real_estate",
        "General": "ma_corporate"
    }

    for key, code in mapping.items():
        if key.lower() in transaction_type.lower():
            return code

    return "ma_corporate"


def _classify_doc_type(filename: str, folder) -> str:
    """Classify document type."""
    filename_lower = filename.lower()

    if any(term in filename_lower for term in ['moi', 'memorandum', 'articles']):
        return 'constitutional'
    if any(term in filename_lower for term in ['resolution', 'minutes']):
        return 'governance'
    if any(term in filename_lower for term in ['license', 'permit', 'certificate']):
        return 'regulatory'
    if any(term in filename_lower for term in ['financial', 'audit', 'afs']):
        return 'financial'

    return 'contract'


def _map_priority(deal_impact: str) -> str:
    """Map deal impact to priority."""
    mapping = {
        "deal_blocker": "critical",
        "condition_precedent": "high",
        "price_chip": "medium",
        "warranty_indemnity": "medium",
        "post_closing": "low"
    }
    return mapping.get(deal_impact, "medium")
