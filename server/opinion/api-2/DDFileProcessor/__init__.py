# File: server/opinion/api-2/DDFileProcessor/__init__.py

import logging, os, json, uuid, textwrap, threading, re, time
import azure.functions as func
from shared.utils import send_custom_event_to_eventgrid, sleep_random_time
from shared.uploader import extract_text_with_new_client, get_blob_metadata, set_blob_metadata
from shared.uploader import read_from_blob_storage, handle_file_with_next_chunk_to_process
from shared.rag import create_chunks_and_embeddings_from_pages, create_chunks_and_embeddings_from_text, get_llm_summary, split_text_by_page
from shared.ddsearch import save_to_dd_search_index, search_similar_dd_documents, format_search_results_for_prompt
from shared.models import Folder, Document
from shared.models import DueDiligence, DueDiligenceMember, Document, PerspectiveRiskFinding, Folder, Perspective, PerspectiveRisk
from sqlalchemy import exists, and_, func as sa_func
from sqlalchemy.orm import joinedload
from shared.session import transactional_session
from shared.rag import generate_document_description, generate_all_folder_descriptions, call_llm_with
from shared.email_helper import send_processing_complete_email
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
from datetime import datetime, timedelta


class TimeoutMonitor:
    """
    Monitor function execution time and trigger re-queuing before timeout.
    Azure Functions timeout: 5 minutes (Consumption) or 10 minutes (max).
    """
    def __init__(self, max_execution_seconds: int = 240):  # 4 minutes safety margin
        self.start_time = time.time()
        self.max_execution_seconds = max_execution_seconds
        self.warned = False
    
    def should_stop(self) -> bool:
        """Check if we're approaching timeout"""
        elapsed = time.time() - self.start_time
        return elapsed >= self.max_execution_seconds
    
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds"""
        return time.time() - self.start_time
    
    def remaining_seconds(self) -> float:
        """Get remaining time before timeout"""
        return max(0, self.max_execution_seconds - self.elapsed_seconds())
    
    def log_status(self):
        """Log current status"""
        elapsed = self.elapsed_seconds()
        remaining = self.remaining_seconds()
        logging.info(f"⏱️ Elapsed: {elapsed:.1f}s | Remaining: {remaining:.1f}s")


def process_diligence_items_with_timeout(
    session, 
    dd_id: str, 
    email: str, 
    due_diligence,
    max_execution_seconds: int = 240  # 4 minutes to leave 1 min safety margin
):
    """
    Process risk items with timeout awareness and auto re-queuing.
    Similar to your file processing pattern.
    """
    timeout_monitor = TimeoutMonitor(max_execution_seconds)
    
    logging.info(f"🚀 Starting timeout-aware risk processing for DD {dd_id}, user {email}")
    logging.info(f"⏱️ Max execution time: {max_execution_seconds}s")
    
    # Get unprocessed risk items
    perspective_items = (session.query(PerspectiveRisk)
        .join(Perspective)
        .join(DueDiligenceMember)
        .filter(
            DueDiligenceMember.dd_id == dd_id,
            DueDiligenceMember.member_email == email,
            PerspectiveRisk.is_deleted == False,
            PerspectiveRisk.is_processed == False
        )
        .all())
    
    if not perspective_items:
        logging.info("✅ No unprocessed risk items found")
        return "completed"
    
    logging.info(f"📋 Found {len(perspective_items)} unprocessed risk items")
    
    # Classify question types first (fast operation)
    for item in perspective_items:
        if not item.question_type:
            item.question_type = classify_question_type(item.detail)
    session.commit()
    
    items_processed = 0
    docs_processed = 0
    
    # Process items SEQUENTIALLY with timeout checks
    for item in perspective_items:
        # Check timeout BEFORE starting each item
        if timeout_monitor.should_stop():
            logging.warning(f"⏱️ Approaching timeout after {timeout_monitor.elapsed_seconds():.1f}s")
            logging.info(f"✅ Processed {items_processed} items, {docs_processed} docs before timeout")
            break
        
        try:
            timeout_monitor.log_status()
            logging.info(f"🔄 Processing risk item {item.id}: {item.detail[:100]}")
            
            # Get relevant documents
            try:
                relevant_folder_ids, relevant_document_ids, search_strategy = get_relevant_folders_and_documents(
                    session, dd_id, item.detail, item.category, 
                    item.folder_scope or 'All Folders', due_diligence.briefing
                )
            except Exception as e:
                logging.error(f"Error in document selection: {str(e)}")
                relevant_folder_ids, relevant_document_ids, search_strategy = [], [], {}
            
            # Build base query
            docs_query = session.query(Document).join(Folder).filter(
                Folder.dd_id == dd_id,
                Document.is_original == False,
                Document.processing_status == "Complete",
            )

            if relevant_document_ids:
                docs_query = docs_query.filter(Document.id.in_(relevant_document_ids))
            elif relevant_folder_ids:
                docs_query = docs_query.filter(Folder.id.in_(relevant_folder_ids))

            # Compute cap BEFORE limiting
            already_docs_processed = session.query(
                sa_func.count(sa_func.distinct(PerspectiveRiskFinding.document_id))
            ).filter(
                PerspectiveRiskFinding.perspective_risk_id == item.id
            ).scalar() or 0

            MAX_DOCS_PER_RISK = int(os.getenv("MAX_DOCS_PER_RISK", "15"))
            remaining_slots = MAX_DOCS_PER_RISK - already_docs_processed
            if remaining_slots <= 0:
                logging.info(f"⛔ Risk {item.id} hit document cap ({MAX_DOCS_PER_RISK}), marking complete")
                item.is_processed = True
                session.commit()
                items_processed += 1
                continue

            # Exclude already-visited docs (including sentinel)
            docs_query = docs_query.filter(
                ~exists().where(
                    and_(
                        PerspectiveRiskFinding.document_id == Document.id,
                        PerspectiveRiskFinding.perspective_risk_id == item.id,
                    )
                )
            )

            batch_limit = min(10, remaining_slots)
            docs_to_process = docs_query.limit(batch_limit).all()

            if not docs_to_process:
                item.is_processed = True
                session.commit()
                items_processed += 1
                continue

            
            # Generate embeddings ONCE for this risk
            search_prompt = item.detail
            if search_strategy.get("primary_keywords"):
                search_prompt += " " + " ".join(search_strategy["primary_keywords"][:3])
            
            try:
                chunks_and_embeddings = create_chunks_and_embeddings_from_text(search_prompt)
                embeddings = [value for item_emb in chunks_and_embeddings for value in item_emb["embedding"]]
            except Exception as e:
                logging.error(f"Error creating embeddings: {str(e)}")
                item.is_processed = True
                session.commit()
                items_processed += 1
                continue
            
            # Process documents for this risk item
            accumulated_findings = []
            doc_count = 0
            
            for doc in docs_to_process:
                # Check timeout BEFORE each document
                if timeout_monitor.should_stop():
                    logging.warning(f"⏱️ Timeout approaching, stopping at doc {doc_count}/{len(docs_to_process)}")
                    break
                
                try:
                    logging.info(f"  📄 Processing doc {doc.id} - {doc.original_file_name}")
                    
                    # Search for relevant content
                    found_results = search_similar_dd_documents(
                        dd_id, None, [str(doc.id)], embeddings, search_prompt, False, 
                        int(os.environ.get("AISearch_K", "8"))
                    )
                    
                    formatted_results = format_search_results_for_prompt(found_results["value"])
                    
                    if not formatted_results:
                        logging.info(f"  ⚠️ No results found for doc {doc.id}")
                        try:
                            sentinel = PerspectiveRiskFinding(
                                perspective_risk_id=item.id,
                                document_id=doc.id,
                                finding_type="informational",
                                phrase="__internal:no-evidence__",  # easily filter in UI
                                status="Info",
                                confidence_score=0.0,
                                requires_action=False,
                                page_number=""
                            )
                            session.add(sentinel)
                            session.commit()
                        except Exception as e:
                            logging.warning(f"Failed to persist sentinel no-hit for doc {doc.id}: {e}")
                            session.rollback()

                        doc_count += 1
                        docs_processed += 1
                        continue

                    
                    # TWO-PHASE ANALYSIS
                    analysis_result = analyze_diligence_item_two_phase(
                        found_results,
                        item.detail,
                        item.category,
                        due_diligence.briefing,
                        item.question_type,
                        search_strategy
                    )
                    
                    # Create finding DATA (not objects)
                    doc_findings = create_findings_from_analysis(
                        session,
                        item.id,
                        doc.id,
                        analysis_result,
                        formatted_results
                    )
                    
                    accumulated_findings.extend(doc_findings)
                    logging.info(f"  ✅ Found {len(doc_findings)} findings from doc {doc.id}")
                    
                    doc_count += 1
                    docs_processed += 1
                    
                    # Small delay to avoid rate limiting
                    sleep_random_time(1, 2)
                    
                except Exception as e:
                    logging.error(f"❌ Error processing doc {doc.id}: {str(e)}")
                    doc_count += 1
                    docs_processed += 1
                    continue

            # Deduplicate and save findings for this risk
            if accumulated_findings:
                logging.info(f"📊 Deduplicating {len(accumulated_findings)} findings for risk {item.id}")
                
                try:
                    deduplicated = deduplicate_findings_intelligent(
                        accumulated_findings,
                        item.detail
                    )
                    
                    logging.info(f"   Result: {len(deduplicated)} unique findings")
                    
                    # Create ORM objects
                    findings_created = create_finding_objects_from_data(
                        session,
                        deduplicated
                    )
                    
                    session.commit()  # ✅ Commit findings
                    logging.info(f"✅ Created {len(findings_created)} findings for risk {item.id}")
                    
                except Exception as e:
                    logging.error(f"Error in deduplication: {str(e)}")
                    session.rollback()
            
            # ✅ CRITICAL: Check remaining docs AFTER commit
            # Use a fresh query that will see the just-committed findings
            session.expire_all()  # Force refresh from database
            
            docs_done = session.query(
                sa_func.count(sa_func.distinct(PerspectiveRiskFinding.document_id))
            ).filter(
                PerspectiveRiskFinding.perspective_risk_id == item.id
            ).scalar() or 0

            cap_reached = docs_done >= MAX_DOCS_PER_RISK
            
            remaining_docs_query = session.query(Document).join(Folder).filter(
                Folder.dd_id == dd_id,
                Document.is_original == False,
                Document.processing_status == "Complete"
            )

            # ✅ Apply the SAME folder filters used earlier
            if relevant_document_ids:
                remaining_docs_query = remaining_docs_query.filter(Document.id.in_(relevant_document_ids))
            elif relevant_folder_ids:
                remaining_docs_query = remaining_docs_query.filter(Folder.id.in_(relevant_folder_ids))

            # Exclude already processed
            remaining_docs_query = remaining_docs_query.filter(
                ~exists().where(
                    and_(
                        PerspectiveRiskFinding.document_id == Document.id,
                        PerspectiveRiskFinding.perspective_risk_id == item.id
                    )
                )
            )

            remaining_docs_count = remaining_docs_query.count()
            
            # ✅ Mark as processed ONLY if truly no more docs
            if cap_reached or remaining_docs_count == 0:
                item.is_processed = True
                session.commit()
                logging.info(f"✅ Risk item {item.id} marked complete (cap_reached={cap_reached}, remaining={remaining_docs_count})")
            else:
                logging.info(f"⏸️ Risk item {item.id} has {remaining_docs_count} more docs (will process next run)")
            
            items_processed += 1
            
        except Exception as e:
            logging.error(f"❌ Error processing risk item {item.id}: {str(e)}")
            logging.exception("Full traceback:")
            
            item.failed_attempt_count = (item.failed_attempt_count or 0) + 1
            
            # Mark as processed only after 3 failed attempts
            if item.failed_attempt_count >= 3:
                logging.error(f"⛔ Risk {item.id} failed 3 times, marking as processed")
                item.is_processed = True
            
            session.commit()
            items_processed += 1
            continue
    
    # Check if more work remains
    remaining_items = session.query(PerspectiveRisk).join(Perspective).join(DueDiligenceMember).filter(
        DueDiligenceMember.dd_id == dd_id,
        DueDiligenceMember.member_email == email,
        PerspectiveRisk.is_deleted == False,
        PerspectiveRisk.is_processed == False
    ).count()
    
    logging.info(f"📊 Batch summary: {items_processed} items, {docs_processed} docs, {timeout_monitor.elapsed_seconds():.1f}s elapsed")
    
    if remaining_items > 0:
        logging.info(f"🔄 More work remains ({remaining_items} items), re-queuing")
        try:
            send_custom_event_to_eventgrid(
                os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_ENDPOINT"],
                topic_key=os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_KEY"],
                subject="Process_Risks",
                data={"email": email, "dd_id": str(dd_id)},
                event_type="AIShop.DD.ProcessRisks"
            )
            return "processing_continued"
        except Exception as e:
            logging.error(f"Error re-queuing: {str(e)}")
            return "requeue_failed"
    else:
        logging.info("✅ All risk processing completed")
        
        # Calculate statistics for completion email
        total_risks_processed = session.query(PerspectiveRisk).join(Perspective).join(DueDiligenceMember).filter(
            DueDiligenceMember.dd_id == dd_id,
            DueDiligenceMember.member_email == email,
            PerspectiveRisk.is_deleted == False,
            PerspectiveRisk.is_processed == True
        ).count()
        
        total_findings = session.query(PerspectiveRiskFinding).join(PerspectiveRisk).join(Perspective).join(DueDiligenceMember).filter(
            DueDiligenceMember.dd_id == dd_id,
            DueDiligenceMember.member_email == email,
            PerspectiveRisk.is_deleted == False
        ).count()
        
        logging.info(f"📧 Sending completion email: {total_risks_processed} risks, {total_findings} findings")
        
        # Send completion email
        try:
            send_processing_complete_email(
                recipient_email=email if email != "simon@alchemylawafrica.com" else "sachin@theaishop.ai",
                dd_name=due_diligence.name if hasattr(due_diligence, 'name') else f"Project {dd_id}",
                dd_id=str(dd_id),
                total_documents=total_risks_processed,  # Reusing param for risk count
                processing_type="risk"
            )
        except Exception as e:
            logging.error(f"Failed to send risk completion email: {str(e)}")
        
        return "completed"
    
def identify_duplicate_clusters_with_embeddings(
    findings_data: List[Dict], 
    embeddings: List[List[float]], 
    similarity_threshold: float = 0.85
) -> List[List[int]]:
    """
    Group findings using pre-computed embeddings.
    Much faster than computing embeddings on-demand.
    """
    
    clusters = []
    processed = set()
    
    for i in range(len(findings_data)):
        if i in processed:
            continue
        
        cluster = [i]
        processed.add(i)
        emb1 = np.array(embeddings[i])
        
        for j in range(i + 1, len(findings_data)):
            if j in processed:
                continue
            
            # Must be same type
            if findings_data[i]["type"] != findings_data[j]["type"]:
                continue
            
            # Calculate cosine similarity directly
            emb2 = np.array(embeddings[j])
            similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
            
            if similarity >= similarity_threshold:
                cluster.append(j)
                processed.add(j)
        
        clusters.append(cluster)
    
    return clusters


def llm_merge_duplicate_findings(findings_group: List[Dict], question_detail: str) -> Dict:
    """
    Use LLM to intelligently merge duplicate findings into a single consolidated finding.
    """
    try:
        # ✅ Convert UUIDs to strings for JSON serialization
        serializable_findings = []
        for finding in findings_group:
            serializable = {**finding}  # Copy dict
            
            # Convert UUID fields to strings
            if isinstance(serializable.get("perspective_risk_id"), uuid.UUID):
                serializable["perspective_risk_id"] = str(serializable["perspective_risk_id"])
            
            if isinstance(serializable.get("document_id"), uuid.UUID):
                serializable["document_id"] = str(serializable["document_id"])
            
            # Convert list of UUIDs to strings
            if "document_ids" in serializable:
                serializable["document_ids"] = [
                    str(doc_id) if isinstance(doc_id, uuid.UUID) else doc_id
                    for doc_id in serializable["document_ids"]
                ]
            
            serializable_findings.append(serializable)
        
        findings_json = json.dumps(serializable_findings, indent=2)
        
        prompt = textwrap.dedent(f"""
            You are a legal deduplication specialist. Review these findings for the risk question:
            
            QUESTION: {question_detail}
            
            CANDIDATE FINDINGS (from different documents):
            {findings_json}
            
            TASK:
            1. Determine if these findings describe the SAME underlying risk/issue or DISTINCT issues
            
            2. DUPLICATE if:
               - Same underlying legal/compliance concern
               - Same parties/contracts/entities involved
               - Different evidence of the SAME problem
               - Overlapping time periods for the same issue
            
            3. NOT DUPLICATE if:
               - Different problems in similar areas
               - Different time periods for recurring issues
               - Different entities/contracts with similar issues
            
            4. If DUPLICATES, merge them by:
               - Use the most precise and comprehensive description
               - Combine ALL unique evidence quotes (concatenate with " | ")
               - Combine ALL document IDs and page numbers
               - Take the HIGHEST confidence score
               - Merge action items (remove duplicates)
               - Use the MOST SEVERE status (Red > Amber > Yellow/New > Green > Info)
            
            Return JSON only:
            {{
                "is_duplicate_group": true|false,
                "merged_finding": {{
                    "type": "positive|negative|gap|neutral|informational",
                    "phrase": "best consolidated description",
                    "direct_answer": "combined if applicable",
                    "evidence_quote": "all unique evidence concatenated",
                    "confidence_score": 0.0-1.0,
                    "status": "Red|Amber|Green|Info|New|Yellow",
                    "page_numbers": ["all", "unique", "pages"],
                    "document_ids": ["all", "unique", "doc", "ids"],
                    "action_items": ["all unique actions"],
                    "missing_documents": ["all unique missing items"],
                    "requires_action": true|false,
                    "action_priority": "high|medium|low"
                }},
                "explanation": "brief explanation of decision"
            }}
            
            If NOT duplicates, return is_duplicate_group=false and merged_finding=null.
        """)
        
        messages = [
            {"role": "system", "content": "You are a legal deduplication expert. Return only valid JSON."},
            {"role": "user", "content": prompt}
        ]
        
        response = call_llm_with(
            messages=messages,
            temperature=0.1,
            max_tokens=2000
        )
        
        result = parse_llm_response(response)
        
        if not result:
            return {
                "is_duplicate_group": False,
                "merged_finding": None,
                "explanation": "Could not parse LLM response"
            }
        
        # ✅ Convert document_ids back to UUIDs in merged finding if needed
        if result.get("merged_finding") and result["merged_finding"].get("document_ids"):
            result["merged_finding"]["document_ids"] = [
                uuid.UUID(doc_id) if isinstance(doc_id, str) else doc_id
                for doc_id in result["merged_finding"]["document_ids"]
            ]
        
        return result
        
    except Exception as e:
        logging.error(f"Error in LLM duplicate merging: {str(e)}")
        logging.exception("Full traceback:")
        return {
            "is_duplicate_group": False,
            "merged_finding": None,
            "explanation": f"Error: {str(e)}"
        }


def deduplicate_findings_intelligent(findings_data: List[Dict], question_detail: str) -> List[Dict]:
    if len(findings_data) <= 1:
        return findings_data
    
    # Group by type first
    by_type = {}
    for idx, finding in enumerate(findings_data):
        finding_type = finding.get("type", "neutral")
        if finding_type not in by_type:
            by_type[finding_type] = []
        by_type[finding_type].append((idx, finding))
    
    deduplicated = []
    
    for finding_type, typed_findings in by_type.items():
        if len(typed_findings) == 1:
            deduplicated.append(typed_findings[0][1])
            continue
        
        just_findings = [f[1] for f in typed_findings]
        
        # CREATE ALL EMBEDDINGS IN ONE BATCH
        all_texts = [f.get("phrase", "") or f.get("description", "") for f in just_findings]
        
        try:
            pages_format = [{"text": text, "page_number": 1, "chunk_index": i} 
                          for i, text in enumerate(all_texts)]
            embeddings_batch = create_chunks_and_embeddings_from_pages(pages_format)
            embeddings = [item["embedding"] for item in embeddings_batch]
        except Exception as e:
            logging.error(f"Embedding batch failed: {e}")
            deduplicated.extend(just_findings)
            continue
        
        clusters = identify_duplicate_clusters_with_embeddings(
            just_findings, embeddings, similarity_threshold=0.80
        )
        
        logging.info(f"   Found {len(clusters)} clusters")
        
        # Process each cluster
        for cluster_indices in clusters:
            if len(cluster_indices) == 1:
                deduplicated.append(just_findings[cluster_indices[0]])
                continue
            
            cluster_findings = [just_findings[i] for i in cluster_indices]
            
            logging.info(f"   🤖 LLM analyzing cluster of {len(cluster_findings)} similar findings")
            
            # ✅ CRITICAL: Get perspective_risk_id BEFORE LLM call
            # All findings in a cluster MUST have the same perspective_risk_id
            pr_id = next((f.get("perspective_risk_id") for f in cluster_findings if f.get("perspective_risk_id")), None)
            
            if pr_id is None:
                logging.error(f"❌ Cluster has no valid perspective_risk_id! Skipping deduplication for this cluster.")
                deduplicated.extend(cluster_findings)
                continue
            
            # Use LLM to merge
            merge_result = llm_merge_duplicate_findings(cluster_findings, question_detail)
            
            if merge_result.get("is_duplicate_group"):
                merged = merge_result.get("merged_finding") or {}
                
                # ✅ FORCE perspective_risk_id (don't trust LLM to preserve it)
                merged["perspective_risk_id"] = pr_id
                
                # Collect doc ids & pages from originals
                doc_ids = []
                for f in cluster_findings:
                    if f.get("document_ids"):
                        doc_ids.extend(f["document_ids"])
                    elif f.get("document_id"):
                        doc_ids.append(f["document_id"])
                doc_ids = list({str(x) for x in doc_ids})  # unique as strings
                
                page_numbers = []
                for f in cluster_findings:
                    page_numbers.extend(f.get("page_numbers", []))
                page_numbers = list(dict.fromkeys(page_numbers))  # preserve order, unique
                
                # Hydrate merged fields if missing/empty
                if not merged.get("document_ids"):
                    merged["document_ids"] = [uuid.UUID(x) for x in doc_ids]
                if not merged.get("page_numbers"):
                    merged["page_numbers"] = page_numbers
                if not merged.get("document_id"):
                    merged["document_id"] = merged["document_ids"][0] if merged["document_ids"] else cluster_findings[0].get("document_id")
                if not merged.get("finding_type") and merged.get("type"):
                    merged["finding_type"] = merged["type"]
                
                # ✅ VALIDATE before adding
                if not merged.get("perspective_risk_id"):
                    logging.error(f"❌ Merged finding still missing perspective_risk_id after hydration! Using originals.")
                    deduplicated.extend(cluster_findings)
                    continue
                
                if not merged.get("document_id"):
                    logging.error(f"❌ Merged finding missing document_id! Using originals.")
                    deduplicated.extend(cluster_findings)
                    continue
                
                deduplicated.append(merged)
            else:
                deduplicated.extend(cluster_findings)
    
    logging.info(f"✅ Deduplication complete: {len(findings_data)} → {len(deduplicated)} findings")
    
    return deduplicated

def classify_question_type(question_text: str) -> str:
    """
    Classify the type of question being asked
    """
    question_lower = question_text.lower()
    
    # Compliance check patterns
    compliance_patterns = [
        "is there", "does", "has", "have", "are there", "is it", "comply", 
        "valid", "in force", "effective", "current", "up to date"
    ]
    
    # Risk search patterns
    risk_patterns = [
        "risk", "issue", "problem", "concern", "violation", "breach", 
        "non-compliance", "default", "liability", "exposure"
    ]
    
    # Information gathering patterns
    info_patterns = [
        "what", "which", "when", "who", "how many", "how much", 
        "list", "describe", "explain", "summary"
    ]
    
    # Check patterns
    for pattern in compliance_patterns:
        if pattern in question_lower:
            return "compliance_check"
    
    for pattern in risk_patterns:
        if pattern in question_lower:
            return "risk_search"
    
    for pattern in info_patterns:
        if pattern in question_lower:
            return "information_gathering"
    
    return "verification"

def build_answer_prompt(question_text: str, question_type: str, category: str, 
                       doc_context: str, dd_briefing: str) -> str:
    """
    Build question-type-specific prompts for Phase 1 (answering)
    """
    
    base_context = f"""
QUESTION: {question_text}
CATEGORY: {category}
DD CONTEXT: {dd_briefing if dd_briefing else 'N/A'}

DOCUMENTS:
{doc_context}
"""
    
    if question_type == "compliance_check":
        instruction = """
This is a COMPLIANCE CHECK question. Your task:
1. Determine if the requirement/item EXISTS or COMPLIES
2. Provide specific evidence of presence/absence
3. Note the source document and exact location
4. Assess completeness and validity

Return JSON only:
{
    "answer_found": true|false,
    "direct_answer": "Clear yes/no with explanation",
    "evidence": "Specific quote or reference from documents",
    "confidence": 0.0-1.0,
    "completeness": "complete|partial|unclear",
    "doc_refs": [{"filename": "...", "page": "..."}],
    "supporting_facts": ["fact 1", "fact 2"]
}
"""
    
    elif question_type == "risk_search":
        instruction = """
This is a RISK IDENTIFICATION question. Your task:
1. Identify specific risks, issues, or concerns in the documents
2. Assess severity based on what you find
3. Note supporting evidence with exact references
4. Don't speculate - only report what documents show

Return JSON only:
{
    "answer_found": true|false,
    "direct_answer": "Summary of identified risks or confirmation of none found",
    "risks_found": [{"description": "...", "evidence": "...", "severity": "high|medium|low"}],
    "confidence": 0.0-1.0,
    "doc_refs": [{"filename": "...", "page": "..."}]
}
"""
    
    elif question_type == "information_gathering":
        instruction = """
This is an INFORMATION GATHERING question. Your task:
1. Extract the specific factual information requested
2. Provide exact figures, names, dates as found in documents
3. Note any discrepancies between different sources
4. Indicate if information is incomplete or missing

Return JSON only:
{
    "answer_found": true|false,
    "direct_answer": "The requested information is...",
    "extracted_facts": {"key1": "value1", "key2": "value2"},
    "evidence": "Source references",
    "confidence": 0.0-1.0,
    "discrepancies": ["any contradictions found"],
    "doc_refs": [{"filename": "...", "page": "..."}]
}
"""
    
    else:  # verification
        instruction = """
This is a VERIFICATION question. Your task:
1. Check if stated information is accurate against documents
2. Identify any errors or misstatements
3. Note supporting or contradicting evidence
4. Assess reliability of the verification

Return JSON only:
{
    "answer_found": true|false,
    "direct_answer": "Verified/Not verified with explanation",
    "verification_result": "confirmed|contradicted|unclear",
    "evidence": "Supporting or contradicting information",
    "confidence": 0.0-1.0,
    "doc_refs": [{"filename": "...", "page": "..."}]
}
"""
    
    return base_context + instruction

def build_risk_prompt(question_text: str, category: str, doc_context: str, 
                     dd_briefing: str, answer_data: Dict) -> str:
    """
    Build Phase 2 risk identification prompt based on Phase 1 answer
    """
    
    return f"""
You've just answered the question: "{question_text}"

Your answer was: "{answer_data.get('direct_answer', '')}"

Now conduct a RISK ANALYSIS on the same documents. Look for:
- Red flags or concerns (even if they don't directly answer the question)
- Missing required documents or information
- Expired or expiring items (dates, licenses, agreements)
- Inconsistencies or discrepancies between documents
- Non-compliance indicators
- Financial or operational concerns
- Unusual terms or conditions

CATEGORY: {category}
DD CONTEXT: {dd_briefing if dd_briefing else 'N/A'}

DOCUMENTS:
{doc_context}

Return JSON only:
{{
    "risks": [
        {{
            "description": "Specific risk identified",
            "severity": "red|amber|yellow",
            "evidence": "What indicates this risk",
            "doc_refs": [{{"filename": "...", "page": "..."}}],
            "requires_action": true|false,
            "action_items": ["specific action needed"]
        }}
    ],
    "gaps": [
        {{
            "description": "Missing information or documentation",
            "importance": "critical|important|minor",
            "missing_items": ["what's missing"]
        }}
    ],
    "positive_findings": [
        {{
            "description": "Positive confirmation or compliance found",
            "evidence": "Supporting information"
        }}
    ]
}}

IMPORTANT: Only include items you actually found in the documents. Do not speculate or list generic risks.
If no risks are found, return empty arrays.
"""

def parse_llm_response(response_text: str) -> Dict:
    """
    Robust JSON parsing with multiple fallback methods
    """
    try:
        return json.loads(response_text.strip())
    except:
        pass
    
    # Method 2: Extract from code block
    try:
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
    except:
        pass
    
    # Method 3: Find JSON object in text
    try:
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except:
        pass
    
    # Method 4: Find JSON array
    try:
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            return {"data": json.loads(json_match.group())}
    except:
        pass
    
    logging.error(f"Could not parse LLM response as JSON. Response: {response_text[:200]}")
    return {}

def analyze_diligence_item_two_phase(
    found_results: Dict, 
    question_text: str, 
    category: str, 
    dd_briefing: str,
    question_type: str,
    search_strategy: Dict
) -> Dict:
    """
    Two-phase analysis: Phase 1 answers the question, Phase 2 identifies risks
    """
    try:
        formatted_results = format_search_results_for_prompt(found_results["value"])
        
        if not formatted_results:
            return {
                "answer_found": False,
                "direct_answer": "Unable to find relevant information in documents",
                "risks": [],
                "gaps": [],
                "positive_findings": [],
                "confidence": 0.0
            }
        
        # Prepare document context - with o3-mini we can be more generous
        doc_context = "\n\n".join([
            f"Document: {result['filename']}\n"
            f"Page: {result['page_number']}\n"
            f"Content: {result['content'][:1000]}..."  # Increased from 500 to 1000
            for result in formatted_results[:8]  # Increased from 5 to 8
        ])
        
        # PHASE 1: Answer the question
        logging.info(f"Phase 1: Answering question type '{question_type}'")
        answer_prompt = build_answer_prompt(
            question_text, question_type, category, doc_context, dd_briefing
        )
        
        answer_response = call_llm_with(
            messages=[
                {"role": "system", "content": "You are a legal analyst. Return only valid JSON."},
                {"role": "user", "content": answer_prompt}
            ],
            temperature=0.1,
            max_tokens=3000  # Increased for o3-mini
        )
        
        answer_data = parse_llm_response(answer_response)
        
        if not answer_data:
            answer_data = {
                "answer_found": False,
                "direct_answer": "Could not parse analysis",
                "confidence": 0.3
            }
        
        # PHASE 2: Identify risks (only if answer found something meaningful)
        risk_data = {"risks": [], "gaps": [], "positive_findings": []}
        
        if answer_data.get("answer_found", False):
            logging.info("Phase 2: Identifying risks")
            risk_prompt = build_risk_prompt(
                question_text, category, doc_context, dd_briefing, answer_data
            )
            
            risk_response = call_llm_with(
                messages=[
                    {"role": "system", "content": "You are a legal risk analyst. Return only valid JSON."},
                    {"role": "user", "content": risk_prompt}
                ],
                temperature=0.1,
                max_tokens=3000
            )
            
            risk_data = parse_llm_response(risk_response)
            if not risk_data:
                risk_data = {"risks": [], "gaps": [], "positive_findings": []}
        
        # Combine both phases
        return {
            "answer_found": answer_data.get("answer_found", False),
            "direct_answer": answer_data.get("direct_answer", ""),
            "evidence": answer_data.get("evidence", ""),
            "confidence": answer_data.get("confidence", 0.5),
            "doc_refs": answer_data.get("doc_refs", []),
            "risks": risk_data.get("risks", []),
            "gaps": risk_data.get("gaps", []),
            "positive_findings": risk_data.get("positive_findings", []),
            "discrepancies": answer_data.get("discrepancies", [])
        }
        
    except Exception as e:
        logging.error(f"Error in two-phase analysis: {str(e)}")
        logging.exception("Full traceback:")
        return {
            "answer_found": False,
            "direct_answer": f"Analysis error: {str(e)}",
            "risks": [],
            "gaps": [],
            "positive_findings": [],
            "confidence": 0.0
        }
        
def create_findings_from_analysis(session, perspective_risk_id, doc_id, 
                                  analysis_result: Dict, formatted_results: List) -> List[Dict]:
    """
    Create finding DATA DICTIONARIES (not ORM objects) from analysis results.
    Returns list of finding dictionaries for deduplication.
    
    NOTE: This now returns data instead of creating objects directly.
    """
    findings_data = []
    
    # 1. ANSWER finding (informational)
    direct_answer = analysis_result.get("direct_answer", "")
    if direct_answer and len(direct_answer) > 20:
        doc_refs = analysis_result.get("doc_refs", [])
        page_numbers = [str(ref.get("page", "")) for ref in doc_refs if ref.get("page")] or \
                      [str(r.get("page_number", "")) for r in formatted_results[:3]]
        
        findings_data.append({
            "type": "informational",
            "perspective_risk_id": perspective_risk_id,
            "document_id": doc_id,
            "document_ids": [doc_id],
            "phrase": direct_answer[:500],
            "direct_answer": direct_answer,
            "evidence_quote": analysis_result.get("evidence", "")[:1000],
            "confidence_score": analysis_result.get("confidence", 0.5),
            "page_numbers": page_numbers,
            "status": "Info",
            "requires_action": False
        })
    
    # 2. POSITIVE findings
    for positive in analysis_result.get("positive_findings", []):
        if not positive.get("description"):
            continue
        
        page_numbers = [str(r.get("page_number", "")) for r in formatted_results[:2]]
        
        findings_data.append({
            "type": "positive",
            "perspective_risk_id": perspective_risk_id,
            "document_id": doc_id,
            "document_ids": [doc_id],
            "phrase": positive.get("description", ""),
            "evidence_quote": positive.get("evidence", ""),
            "status": "Green",
            "confidence_score": 0.85,
            "requires_action": False,
            "page_numbers": page_numbers
        })
    
    # 3. NEGATIVE findings (risks)
    severity_map = {"red": "Red", "amber": "Amber", "yellow": "New"}
    
    for risk in analysis_result.get("risks", []):
        if not risk.get("description"):
            continue
        
        severity = risk.get("severity", "yellow")
        status = severity_map.get(severity, "New")
        
        risk_doc_refs = risk.get("doc_refs", [])
        risk_pages = [str(ref.get("page", "")) for ref in risk_doc_refs if ref.get("page")]
        if not risk_pages:
            risk_pages = [str(r.get("page_number", "")) for r in formatted_results[:2]]
        
        findings_data.append({
            "type": "negative",
            "perspective_risk_id": perspective_risk_id,
            "document_id": doc_id,
            "document_ids": [doc_id],
            "phrase": risk.get("description", ""),
            "evidence_quote": risk.get("evidence", "")[:1000],
            "status": status,
            "confidence_score": 0.8,
            "requires_action": risk.get("requires_action", True),
            "action_priority": "high" if severity == "red" else ("medium" if severity == "amber" else "low"),
            "action_items": risk.get("action_items", []),
            "page_numbers": risk_pages
        })
    
    # 4. GAP findings
    for gap in analysis_result.get("gaps", []):
        if not gap.get("description"):
            continue
        
        findings_data.append({
            "type": "gap",
            "perspective_risk_id": perspective_risk_id,
            "document_id": doc_id,
            "document_ids": [doc_id],
            "phrase": gap.get("description", ""),
            "missing_documents": gap.get("missing_items", []),
            "status": "Info",
            "confidence_score": 0.9,
            "requires_action": gap.get("importance") in ["critical", "important"],
            "page_numbers": []
        })
    
    # 5. NEUTRAL findings (discrepancies)
    for discrepancy in analysis_result.get("discrepancies", []):
        if not discrepancy:
            continue
        
        findings_data.append({
            "type": "neutral",
            "perspective_risk_id": perspective_risk_id,
            "document_id": doc_id,
            "document_ids": [doc_id],
            "phrase": f"Discrepancy identified: {discrepancy}",
            "status": "Amber",
            "confidence_score": 0.75,
            "requires_action": True,
            "page_numbers": []
        })
    
    return findings_data


def create_finding_objects_from_data(session, deduplicated_findings: List[Dict]) -> List[str]:
    """
    Create PerspectiveRiskFinding ORM objects from deduplicated finding dictionaries.
    This is the final step after deduplication.
    """
    findings_created = []
    
    for finding_dict in deduplicated_findings:
        # ✅ VALIDATE perspective_risk_id FIRST
        perspective_risk_id = finding_dict.get("perspective_risk_id")
        if not perspective_risk_id:
            logging.error(f"❌ SKIPPING finding with missing perspective_risk_id: {finding_dict.get('phrase', 'Unknown')[:100]}")
            continue
        
        finding_type = finding_dict.get("type")
        
        # Handle merged findings that may have multiple document IDs
        doc_ids = finding_dict.get("document_ids", [])
        primary_doc_id = doc_ids[0] if doc_ids else finding_dict.get("document_id")
        if not primary_doc_id:
            logging.warning(f"❌ SKIPPING finding with missing document_id: {finding_dict.get('phrase', 'Unknown')[:50]}")
            continue
        
        # Combine page numbers
        page_numbers = finding_dict.get("page_numbers", [])
        page_str = ", ".join([str(p) for p in page_numbers if p]) if page_numbers else ""
        
        # Handle action_items (could be list or None)
        action_items = finding_dict.get("action_items")
        action_items_json = json.dumps(action_items) if action_items else None
        
        # Handle missing_documents
        missing_docs = finding_dict.get("missing_documents")
        missing_docs_json = json.dumps(missing_docs) if missing_docs else None
        
        try:
            # Create the finding object
            finding_obj = PerspectiveRiskFinding(
                perspective_risk_id=perspective_risk_id,  # ✅ Now guaranteed to be valid
                document_id=primary_doc_id,
                finding_type=finding_type,
                phrase=finding_dict.get("phrase", "")[:500],
                direct_answer=finding_dict.get("direct_answer"),
                evidence_quote=finding_dict.get("evidence_quote", "")[:1000] if finding_dict.get("evidence_quote") else None,
                confidence_score=finding_dict.get("confidence_score", 0.5),
                status=finding_dict.get("status", "New"),
                page_number=page_str,
                requires_action=finding_dict.get("requires_action", False),
                action_priority=finding_dict.get("action_priority"),
                action_items=action_items_json,
                missing_documents=missing_docs_json
            )
            
            session.add(finding_obj)
            findings_created.append(finding_type)
        except Exception as e:
            logging.error(f"❌ Error creating finding object: {str(e)}")
            logging.error(f"   Finding data: {finding_dict}")
            continue
    
    return findings_created

    
def get_relevant_folders_and_documents(session, dd_id: str, risk_description: str, risk_category: str, folder_scope: str, due_diligence_briefing: str) -> Tuple[List[uuid.UUID], List[uuid.UUID], Dict]:
    """
    Use LLM to intelligently identify relevant folders and documents based on descriptions
    Returns (relevant_folder_ids, relevant_document_ids, search_strategy)
    """
    try:
        # Get all folders with descriptions
        folders_query = session.query(Folder).filter(Folder.dd_id == dd_id).all()
        
        # Filter by folder scope if specified
        if folder_scope and folder_scope != "All Folders":
            folders_query = [f for f in folders_query if folder_scope.lower() in f.folder_name.lower() or folder_scope.lower() in f.path.lower()]
        
        # Get documents with descriptions from relevant folders
        folder_ids = [str(f.id) for f in folders_query]
        documents_query = (session.query(Document)
                          .filter(Document.folder_id.in_(folder_ids))
                          .filter(Document.is_original == False)
                          .filter(Document.processing_status == "Complete")
                          .filter(Document.description.isnot(None))
                          .all())
        
        # REDUCE DATA SIZE - Only include essential info
        folder_info = []
        for folder in folders_query[:15]:  # Reduced from 20 to 15
            doc_count = len([d for d in documents_query if d.folder_id == folder.id])
            if doc_count > 0:
                folder_info.append({
                    "id": str(folder.id),
                    "name": folder.folder_name[:50],  # Limit name length
                    "desc": (folder.description or "")[:100]  # Shortened key and limited length
                })
        
        # Limit document info even more
        document_info = []
        for doc in documents_query[:15]:  # Reduced from 20 to 15
            document_info.append({
                "id": str(doc.id),
                "name": doc.original_file_name[:50],
                "desc": (doc.description or "")[:100]
            })
        
        # EVEN SHORTER PROMPT - removed folder paths and document count
        relevance_prompt = textwrap.dedent(f"""
            Legal AI: Identify relevant folders for: {risk_description[:150]}
            Category: {risk_category}
            
            Folders:
            {json.dumps(folder_info, separators=(',',':'))}
            
            Docs:
            {json.dumps(document_info, separators=(',',':'))}
            
            Return JSON:
            {{
                "relevant_folders": [{{"id": "full-uuid-here", "relevance_score": 0.9}}],
                "relevant_documents": [{{"id": "full-uuid-here", "relevance_score": 0.8}}],
                "search_strategy": {{"primary_keywords": ["kw1", "kw2"]}}
            }}
            
            CRITICAL: Return COMPLETE UUIDs (36 chars each). Include items with score >= 0.6.
        """)
        
        messages = [
            {"role": "system", "content": "Legal AI assistant. Return ONLY valid JSON with complete UUIDs."},
            {"role": "user", "content": relevance_prompt}
        ]
        
        # INCREASED TOKEN LIMIT to prevent truncation
        llm_response = call_llm_with(messages=messages, temperature=0.1, max_tokens=6000)  # Increased from 4000
        
        logging.info(f"LLM relevance response (first 300 chars): {llm_response[:300]}")
        
        # Better JSON parsing
        response_data = None
        
        # Try 1: Parse as-is
        try:
            response_data = json.loads(llm_response.strip())
        except json.JSONDecodeError:
            pass
        
        # Try 2: Extract JSON from markdown code block
        if not response_data:
            try:
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
                if json_match:
                    response_data = json.loads(json_match.group(1))
            except:
                pass
        
        # Try 3: Find JSON object in text
        if not response_data:
            try:
                json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                if json_match:
                    response_data = json.loads(json_match.group())
            except:
                pass
        
        if response_data and isinstance(response_data, dict):
            try:
                # Convert to UUID objects, filtering out any invalid UUIDs
                relevant_folder_ids = []
                for item in response_data.get("relevant_folders", []):
                    if isinstance(item, dict) and item.get("relevance_score", 0) >= 0.6:
                        try:
                            uuid_str = str(item["id"]).strip()
                            
                            # ✅ ADD UUID LENGTH VALIDATION
                            if len(uuid_str) != 36:
                                logging.warning(f"Skipping invalid UUID length ({len(uuid_str)} chars): {uuid_str}")
                                continue
                            
                            relevant_folder_ids.append(uuid.UUID(uuid_str))
                        except (ValueError, TypeError, KeyError) as e:
                            logging.warning(f"Skipping invalid folder UUID: {item.get('id')}: {e}")
                
                relevant_document_ids = []
                for item in response_data.get("relevant_documents", []):
                    if isinstance(item, dict) and item.get("relevance_score", 0) >= 0.6:
                        try:
                            uuid_str = str(item["id"]).strip()
                            
                            # ✅ ADD UUID LENGTH VALIDATION
                            if len(uuid_str) != 36:
                                logging.warning(f"Skipping invalid UUID length ({len(uuid_str)} chars): {uuid_str}")
                                continue
                            
                            relevant_document_ids.append(uuid.UUID(uuid_str))
                        except (ValueError, TypeError, KeyError) as e:
                            logging.warning(f"Skipping invalid document UUID: {item.get('id')}: {e}")
                
                search_strategy = response_data.get("search_strategy", {})
                
                logging.info(f"LLM identified {len(relevant_folder_ids)} relevant folders and {len(relevant_document_ids)} relevant documents")
                return relevant_folder_ids, relevant_document_ids, search_strategy
            except Exception as e:
                logging.error(f"Error extracting data from parsed JSON: {str(e)}")
        
        # IMPROVED FALLBACK
        logging.warning("Could not parse LLM relevance response, using intelligent fallback")
        
        # Simple keyword-based fallback
        risk_keywords = risk_description.lower().split()[:5]
        relevant_folder_ids = []
        
        for folder in folders_query:
            folder_text = f"{folder.folder_name} {folder.path} {folder.description or ''}".lower()
            if any(keyword in folder_text for keyword in risk_keywords if len(keyword) > 3):
                relevant_folder_ids.append(folder.id)  # Already a UUID object from DB
        
        # Limit fallback to prevent runaway processing
        if len(relevant_folder_ids) > 10:
            relevant_folder_ids = relevant_folder_ids[:10]
        
        if not relevant_folder_ids:
            # If no keyword matches, use first 5 folders as last resort
            relevant_folder_ids = [f.id for f in folders_query[:5]]
        
        logging.info(f"Fallback identified {len(relevant_folder_ids)} relevant folders")
        return relevant_folder_ids, [], {"primary_keywords": risk_keywords[:3]}
            
    except Exception as e:
        logging.error(f"Error in relevance analysis: {str(e)}")
        # Final fallback - just use first 5 folders (UUID objects from DB)
        folder_objs = session.query(Folder).filter(Folder.dd_id == dd_id).limit(5).all()
        return [f.id for f in folder_objs], [], {}

    
def process_document_batch_parallel(session, dd_id: str, email: str, max_concurrent: int = 20):
    """
    Process multiple documents in parallel using ThreadPoolExecutor.
    Returns number of documents processed.
    """
    logging.info(f"Starting parallel batch processing for DD {dd_id}, max_concurrent={max_concurrent}")
    
    try:
        # Get pending documents
        pending_docs = session.query(Document).join(Folder).filter(
            Folder.dd_id == dd_id,
            Document.processing_status.in_(["Pending", "Queued"]),
            Document.is_original == False
        ).limit(max_concurrent).all()
        
        if not pending_docs:
            logging.info("No pending documents found for parallel processing")
            return 0
        
        logging.info(f"Found {len(pending_docs)} documents to process in parallel")
        
        # Mark all as "In progress" to prevent duplicate processing
        for doc in pending_docs:
            doc.processing_status = "In progress"
        session.commit()
        
        # Process in parallel
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            # Submit all tasks
            future_to_doc = {
                executor.submit(
                    process_single_document_complete,
                    str(doc.id),
                    dd_id,
                    email,
                    doc.original_file_name,
                    doc.type,
                    doc.folder.path,
                    doc.folder.hierarchy
                ): doc for doc in pending_docs
            }
            
            # Wait for completion and handle results
            completed_count = 0
            failed_count = 0
            
            for future in as_completed(future_to_doc):
                doc = future_to_doc[future]
                try:
                    result = future.result(timeout=300)  # 5 min timeout per doc
                    if result["status"] == "success":
                        logging.info(f"✅ Document {doc.id} ({doc.original_file_name}) completed successfully")
                        completed_count += 1
                        
                        # Update document in database
                        with transactional_session() as update_session:
                            db_doc = update_session.query(Document).filter(Document.id == doc.id).first()
                            if db_doc:
                                db_doc.processing_status = "Complete"
                                
                                # Generate description if not present
                                if not db_doc.description and result.get("initial_content"):
                                    try:
                                        db_doc.description = generate_document_description(
                                            filename=db_doc.original_file_name,
                                            file_content=result["initial_content"],
                                            file_type=db_doc.type,
                                            folder_path=db_doc.folder.path if db_doc.folder else None
                                        )
                                    except Exception as desc_error:
                                        logging.warning(f"Failed to generate description: {desc_error}")
                                        db_doc.description = f"{db_doc.type.upper()} document: {db_doc.original_file_name}"
                                
                                update_session.commit()
                    else:
                        logging.error(f"❌ Document {doc.id} failed: {result.get('error')}")
                        failed_count += 1
                        
                        # Mark as failed
                        with transactional_session() as update_session:
                            db_doc = update_session.query(Document).filter(Document.id == doc.id).first()
                            if db_doc:
                                db_doc.processing_status = result.get("final_status", "Failed")
                                update_session.commit()
                                
                except Exception as e:
                    logging.error(f"❌ Exception processing document {doc.id}: {str(e)}")
                    failed_count += 1
                    
                    # Mark as failed
                    try:
                        with transactional_session() as update_session:
                            db_doc = update_session.query(Document).filter(Document.id == doc.id).first()
                            if db_doc:
                                db_doc.processing_status = "Failed"
                                update_session.commit()
                    except Exception as db_error:
                        logging.error(f"Failed to update status for {doc.id}: {db_error}")
        
        logging.info(f"Parallel batch complete: {completed_count} succeeded, {failed_count} failed")
        return completed_count
        
    except Exception as e:
        logging.exception(f"Error in parallel batch processing: {str(e)}")
        return 0


def process_single_document_complete(doc_id: str, dd_id: str, email: str, 
                                     filename: str, extension: str,
                                     folder_path: str, folder_hierarchy: str):
    """
    Process a single document completely (called in parallel).
    This function is thread-safe and self-contained.
    
    Returns dict with status and details.
    """
    try:
        logging.info(f"🔄 Starting OCR for {doc_id} - {filename}")
        
        # Read blob
        file_contents = read_from_blob_storage(
            os.environ["DD_DOCS_BLOB_STORAGE_CONNECTION_STRING"],
            os.environ["DD_DOCS_STORAGE_CONTAINER_NAME"],
            doc_id
        )
        
        if not file_contents:
            logging.warning(f"Empty file: {doc_id}")
            return {"status": "failed", "error": "Empty file", "final_status": "Failed"}
        
        # Check if unsupported
        SUPPORTED = {"pdf", "docx", "pptx", "xlsx", "jpg", "jpeg", "png", "bmp", "tiff"}
        if extension not in SUPPORTED:
            logging.info(f"Unsupported type {extension}: {doc_id}")
            return {"status": "failed", "error": f"Unsupported type: {extension}", "final_status": "Unsupported"}
        
        # OCR - THIS IS THE PARALLEL PART
        start_time = time.time()
        pages = extract_text_with_new_client(file_contents, extension, filename)
        ocr_time = time.time() - start_time
        
        logging.info(f"⚡ OCR completed in {ocr_time:.2f}s for {filename}")
        
        if not pages:
            logging.warning(f"No text extracted: {doc_id}")
            return {"status": "failed", "error": "No text extracted", "final_status": "Failed"}
        
        # Get initial content for description
        initial_content = ""
        if isinstance(pages, list) and len(pages) > 0:
            content_chunks = []
            for page in pages[:3]:  # First 3 pages
                page_text = page.get("text", "") if isinstance(page, dict) else str(page)
                content_chunks.append(page_text)
                if len(" ".join(content_chunks)) > 1000:
                    break
            initial_content = " ".join(content_chunks)[:1000]
        
        # Chunk and embed (sequential per doc, but that's fast)
        pages_chunked = split_text_by_page(pages, chunk_size=800, chunk_overlap=80)
        chunks_and_embeddings = create_chunks_and_embeddings_from_pages(pages_chunked)
        
        # Index
        save_to_dd_search_index(
            dd_id,
            doc_id,
            folder_path,
            folder_hierarchy,
            chunks_and_embeddings,
            filename
        )
        
        total_time = time.time() - start_time
        logging.info(f"✅ Complete processing in {total_time:.2f}s: {filename}")
        
        return {
            "status": "success",
            "pages": len(pages),
            "chunks": len(chunks_and_embeddings),
            "ocr_time": ocr_time,
            "total_time": total_time,
            "initial_content": initial_content
        }
        
    except Exception as e:
        logging.error(f"Error processing {doc_id}: {str(e)}")
        logging.exception("Full traceback:")
        return {
            "status": "failed",
            "error": str(e),
            "final_status": "Failed"
        }
    
    
def main(req: func.HttpRequest) -> func.HttpResponse:

    if req.params.get('function-key') != os.environ["FUNCTION_KEY"]:
        return func.HttpResponse("", status_code=401)
       
    try:
        events = req.get_json()

        if not isinstance(events, list):
            return func.HttpResponse("Unhandled event", status_code=200) # TODO
        
        first_event = events[0]
        event_type = first_event.get("eventType")

        if event_type == "Microsoft.EventGrid.SubscriptionValidationEvent":
            validation_code = first_event["data"]["validationCode"]
            return func.HttpResponse(
                json.dumps({"validationResponse": validation_code}),
                status_code=200,
                mimetype="application/json"
            )

        elif event_type == "AIShop.DD.ProcessRisks":
            email = first_event["data"]["email"]
            dd_id = uuid.UUID(first_event["data"]["dd_id"])
            logging.info(f"⏱️ TIMEOUT-AWARE RISK PROCESSING for {dd_id=}")
            
            with transactional_session() as session:
                due_diligence = session.query(DueDiligence).filter(
                    DueDiligence.id == dd_id
                ).first()
                
                member = session.query(DueDiligenceMember).filter(
                    DueDiligenceMember.dd_id == dd_id,
                    DueDiligenceMember.member_email == email
                ).first()
                
                if not member:
                    logging.info(f"{email} is not a member")
                    return func.HttpResponse(f"{email} is not a member", status_code=500)
                
                # Use timeout-aware processing (240 seconds = 4 minutes)
                result = process_diligence_items_with_timeout(
                    session, 
                    dd_id, 
                    email, 
                    due_diligence,
                    max_execution_seconds=240  # 4 min, leaving 1 min safety margin
                )
                
                if result == "processing_continued":
                    return func.HttpResponse("Processing continues (re-queued)", status_code=200)
                elif result == "completed":
                    return func.HttpResponse("Risk processing completed", status_code=200)
                else:
                    return func.HttpResponse(f"Processing result: {result}", status_code=200)


                
        # Handle DD File Processing
        elif event_type == "AIShop.DD.BlobMetadataUpdated":
            logging.info("AIShop.DD.BlobMetadataUpdated")
            with transactional_session() as session: 
                doc_id = first_event["data"]["doc_id"]
                dd_id = first_event["data"]["dd_id"]
                email = first_event["data"]["email"]
                
                due_diligence = session.query(DueDiligence).filter(
                    DueDiligence.id == dd_id
                ).first()
                
                member = session.query(DueDiligenceMember).filter(
                    DueDiligenceMember.dd_id == dd_id,
                    DueDiligenceMember.member_email == email
                ).first()
                

                db_doc = (
                    session.query(Document)
                    .options(joinedload(Document.folder))
                    .filter(Document.id == doc_id)
                    .first()
                )

                metadata = get_blob_metadata(os.environ["DD_DOCS_BLOB_STORAGE_CONNECTION_STRING"], os.environ["DD_DOCS_STORAGE_CONTAINER_NAME"], doc_id)
                logging.info(f"processing {dd_id=} {doc_id=} {metadata['original_file_name']}")

                file_contents = read_from_blob_storage(os.environ["DD_DOCS_BLOB_STORAGE_CONNECTION_STRING"], os.environ["DD_DOCS_STORAGE_CONTAINER_NAME"], doc_id)
              
                if not file_contents:
                    logging.warning(f"{doc_id} is empty – marking as Failed")

                    db_doc.processing_status = "Failed"

                    metadata["done"] = "true"
                    set_blob_metadata(
                        os.environ["DD_DOCS_BLOB_STORAGE_CONNECTION_STRING"],
                        os.environ["DD_DOCS_STORAGE_CONTAINER_NAME"],
                        doc_id,
                        metadata
                    )
                    session.commit()

                    db_next_doc = (
                        session.query(Document)
                        .join(Document.folder)
                        .filter(
                            Folder.dd_id == dd_id,
                            Document.processing_status.notin_(("Complete", "Unsupported", "Failed")),
                            Document.id != doc_id,
                            Document.is_original.is_(False)
                        )
                        .first()
                    )
                    session.commit()

                    if db_next_doc:
                        logging.info(f"Empty file skipped; moving on to {db_next_doc.id}")
                        db_next_doc.processing_status = "In progress"
                        session.commit()

                        # seed its metadata (next_chunk_to_process = 0)
                        set_blob_metadata(
                            os.environ["DD_DOCS_BLOB_STORAGE_CONNECTION_STRING"],
                            os.environ["DD_DOCS_STORAGE_CONTAINER_NAME"],
                            str(db_next_doc.id),
                            {
                                "original_file_name": db_next_doc.original_file_name,
                                "extension": db_next_doc.type,
                                "is_dd": "True",
                                "doc_id": str(db_next_doc.id),
                                "dd_id": dd_id,
                                "next_chunk_to_process": "0"
                            }
                        )

                        send_custom_event_to_eventgrid(
                            os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_ENDPOINT"],
                            topic_key=os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_KEY"],
                            subject=str(db_next_doc.id),
                            data={"doc_id": str(db_next_doc.id),
                                "dd_id": dd_id,
                                "email": email},
                            event_type="AIShop.DD.BlobMetadataUpdated"
                        )
                    else:
                        logging.info("No more docs, kicking off risk analysis")
                        if member:
                            send_custom_event_to_eventgrid(
                            os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_ENDPOINT"],
                            topic_key=os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_KEY"],
                            subject="Process_Risks",
                            data={"email": email, "dd_id": dd_id},
                            event_type="AIShop.DD.ProcessRisks"
                        )

                    return func.HttpResponse("Empty blob skipped", status_code=200)

                
                next_chunk_to_process = int(metadata["next_chunk_to_process"])

                logging.info(f"check: folder.path {db_doc.folder.path}")
                logging.info(f"check: folder.hierarchy {db_doc.folder.hierarchy}")

                chunk_stop, pages_chunked, status = handle_file_with_next_chunk_to_process(
                    file_contents, metadata["original_file_name"], metadata["extension"], 
                    dd_id,
                    doc_id, 
                    db_doc.folder.path, db_doc.folder.hierarchy,  next_chunk_to_process)
                
                if status in ["unsupported", "failed"]:
                    logging.info(f"File {metadata['original_file_name']} marked as {status}")
                    
                    # Update status based on the result
                    if status == "unsupported":
                        db_doc.processing_status = "Unsupported"
                    else:  # status == "failed"
                        db_doc.processing_status = "Failed"
                    
                    # Mark as done in metadata
                    metadata["done"] = "true"
                    set_blob_metadata(
                        os.environ["DD_DOCS_BLOB_STORAGE_CONNECTION_STRING"], 
                        os.environ["DD_DOCS_STORAGE_CONTAINER_NAME"], 
                        doc_id, 
                        metadata
                    )
                    session.commit()
                    
                    # Move to next document
                    db_next_doc = (
                        session.query(Document)
                        .join(Document.folder)
                        .filter(
                            Folder.dd_id == dd_id,
                            Document.processing_status.notin_(("Complete", "Unsupported", "Failed")),
                            Document.id != doc_id,
                            Document.is_original.is_(False)
                        )
                        .first()
                    )
                    
                    if db_next_doc:
                        logging.info(f"{status.capitalize()} file skipped; moving on to {db_next_doc.id}")
                        db_next_doc.processing_status = "In progress"
                        session.commit()
                        # seed its metadata (next_chunk_to_process = 0)
                        set_blob_metadata(
                            os.environ["DD_DOCS_BLOB_STORAGE_CONNECTION_STRING"],
                            os.environ["DD_DOCS_STORAGE_CONTAINER_NAME"],
                            str(db_next_doc.id),
                            {
                                "original_file_name": db_next_doc.original_file_name,
                                "extension": db_next_doc.type,
                                "is_dd": "True",
                                "doc_id": str(db_next_doc.id),
                                "dd_id": dd_id,
                                "next_chunk_to_process": "0"
                            }
                        )
                        send_custom_event_to_eventgrid(
                            os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_ENDPOINT"],
                            topic_key=os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_KEY"],
                            subject=str(db_next_doc.id),
                            data={"doc_id": str(db_next_doc.id),
                                "dd_id": dd_id,
                                "email": email},
                            event_type="AIShop.DD.BlobMetadataUpdated"
                        )
                    else:
                        logging.info("No more docs, kicking off risk analysis")
                        if member:
                            send_custom_event_to_eventgrid(
                                os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_ENDPOINT"],
                                topic_key=os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_KEY"],
                                subject="Process_Risks",
                                data={"email": email, "dd_id": dd_id},
                                event_type="AIShop.DD.ProcessRisks"
                            )
                    
                    return func.HttpResponse(f"File {status}", status_code=200)
                
                
                
                more_work_to_do = chunk_stop < pages_chunked
                if more_work_to_do:
                    logging.info(f"more work to do, updated doc in dd {metadata['original_file_name']}")

                    metadata["next_chunk_to_process"] = str(chunk_stop)
                    
                    if db_doc.processing_status != "In progress":
                        db_doc.processing_status = "In progress"
                    
                    

                    set_blob_metadata(os.environ["DD_DOCS_BLOB_STORAGE_CONNECTION_STRING"], os.environ["DD_DOCS_STORAGE_CONTAINER_NAME"], doc_id, metadata)
                    send_custom_event_to_eventgrid(os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_ENDPOINT"],
                                    topic_key = os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_KEY"],
                                    subject = doc_id,
                                    data = {"doc_id": doc_id, "dd_id": dd_id, "email": email},
                                    event_type = "AIShop.DD.BlobMetadataUpdated")
                    logging.info(" added to queue for next round")
                    return func.HttpResponse("Processing", status_code=200)
                # In the main() function, in the BlobMetadataUpdated handler
                # Replace the section starting at "else: # done with this file"
                    
                else:
                    # ✅ DONE WITH THIS FILE
                    logging.info(f"DONE WITH CHUNKING {metadata['original_file_name']}")
                    metadata["next_chunk_to_process"] = str(chunk_stop)
                    metadata.update({"done": "true", "next_chunk_to_process": "0"})
                    
                    # Generate document description
                    if not db_doc.description:
                        try:
                            logging.info(f"Generating AI description for {metadata['original_file_name']}")
                            initial_content = ""
                            if isinstance(pages_chunked, list) and len(pages_chunked) > 0:
                                content_chunks = []
                                char_count = 0
                                for chunk in pages_chunked[:5]:
                                    chunk_text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
                                    content_chunks.append(chunk_text)
                                    char_count += len(chunk_text)
                                    if char_count > 1000:
                                        break
                                initial_content = " ".join(content_chunks)
                            
                            if not initial_content and file_contents:
                                try:
                                    initial_content = file_contents[:1000].decode('utf-8', errors='ignore')
                                except:
                                    initial_content = "Binary file - content not directly readable"
                            
                            db_doc.description = generate_document_description(
                                filename=metadata['original_file_name'],
                                file_content=initial_content,
                                file_type=metadata['extension'],
                                folder_path=db_doc.folder.path if db_doc.folder else None
                            )
                            logging.info(f"Generated description: {db_doc.description[:100]}...")
                        except Exception as e:
                            logging.error(f"Failed to generate description: {str(e)}")
                            db_doc.description = f"{metadata['extension'].upper()} document: {metadata['original_file_name']}"
                    
                    set_blob_metadata(os.environ["DD_DOCS_BLOB_STORAGE_CONNECTION_STRING"], 
                                    os.environ["DD_DOCS_STORAGE_CONTAINER_NAME"], doc_id, metadata)
                    db_doc.processing_status = "Complete"
                    session.commit()  # ✅ COMMIT BEFORE CHECKING
                    
                    if metadata.get("single_file", False):
                        logging.info("Single file process finished")
                        if member:
                            send_custom_event_to_eventgrid(
                                os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_ENDPOINT"],
                                topic_key=os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_KEY"],
                                subject="Process_Risks",
                                data={"email": email, "dd_id": dd_id},
                                event_type="AIShop.DD.ProcessRisks"
                            )
                        return func.HttpResponse("Processed", status_code=200)
                    
                    # ✅ CHECK FOR PARALLEL PROCESSING *BEFORE* MARKING ANYTHING
                    logging.info("Checking for parallel batch processing opportunity")
                    
                    remaining_count = session.query(Document).join(Folder).filter(
                        Folder.dd_id == dd_id,
                        Document.processing_status.in_(["Pending", "Queued"]),
                        Document.is_original == False
                    ).count()
                    
                    logging.info(f"Remaining pending documents: {remaining_count}")
                    
                    # ✅ DECIDE: PARALLEL OR SEQUENTIAL
                    if remaining_count >= 5:
                        logging.info(f"🚀 Starting PARALLEL processing for {remaining_count} documents")
                        
                        # Process batch in parallel
                        processed_count = process_document_batch_parallel(
                            session, dd_id, email, max_concurrent=20
                        )
                        
                        logging.info(f"Parallel batch processed {processed_count} documents")
                        
                        # Check if more work remains
                        remaining_after_batch = session.query(Document).join(Folder).filter(
                            Folder.dd_id == dd_id,
                            Document.processing_status.in_(["Pending", "Queued"]),
                            Document.is_original == False
                        ).count()
                        
                        if remaining_after_batch > 0:
                            logging.info(f"More work remains ({remaining_after_batch} docs), queueing next document")
                            
                            # NOW mark next doc as in progress
                            next_doc = session.query(Document).join(Folder).filter(
                                Folder.dd_id == dd_id,
                                Document.processing_status.in_(["Pending", "Queued"]),
                                Document.is_original == False
                            ).first()
                            
                            if next_doc:
                                next_doc.processing_status = "In progress"
                                session.commit()
                                
                                set_blob_metadata(
                                    os.environ["DD_DOCS_BLOB_STORAGE_CONNECTION_STRING"],
                                    os.environ["DD_DOCS_STORAGE_CONTAINER_NAME"],
                                    str(next_doc.id),
                                    {
                                        "original_file_name": next_doc.original_file_name,
                                        "extension": next_doc.type,
                                        "is_dd": "True",
                                        "doc_id": str(next_doc.id),
                                        "dd_id": dd_id,
                                        "next_chunk_to_process": "0"
                                    }
                                )
                                
                                send_custom_event_to_eventgrid(
                                    os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_ENDPOINT"],
                                    topic_key=os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_KEY"],
                                    subject=str(next_doc.id),
                                    data={"doc_id": str(next_doc.id), "dd_id": dd_id, "email": email},
                                    event_type="AIShop.DD.BlobMetadataUpdated"
                                )
                        else:
                            # All done - completion logic
                            logging.info("All documents processed after parallel batch")
                            
                            try:
                                generate_all_folder_descriptions(dd_id, session)
                            except Exception as e:
                                logging.error(f"Failed to generate folder descriptions: {str(e)}")
                            
                            total_processed_docs = session.query(Document).join(Folder).filter(
                                Folder.dd_id == dd_id,
                                Document.processing_status == "Complete",
                                Document.is_original == False
                            ).count()
                            
                            try:
                                send_processing_complete_email(
                                    recipient_email=email if email != "simon@alchemylawafrica.com" else "sachin@theaishop.ai",
                                    dd_name=due_diligence.name if hasattr(due_diligence, 'name') else f"Project {dd_id}",
                                    dd_id=str(dd_id),
                                    total_documents=total_processed_docs,
                                    processing_type="document"
                                )
                            except Exception as e:
                                logging.error(f"Failed to send email: {str(e)}")
                            
                            if member:
                                send_custom_event_to_eventgrid(
                                    os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_ENDPOINT"],
                                    topic_key=os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_KEY"],
                                    subject="Process_Risks",
                                    data={"email": email, "dd_id": dd_id},
                                    event_type="AIShop.DD.ProcessRisks"
                                )
                        
                        return func.HttpResponse("Parallel batch processed", status_code=200)
                    
                    else:
                        # ✅ SEQUENTIAL PROCESSING (count < 5)
                        logging.info("Sequential: checking for next doc")
                        
                        db_next_doc = session.query(Document).join(Folder).filter(
                            Folder.dd_id == dd_id,
                            Document.processing_status.in_(["Pending", "Queued"]),  # ✅ Check Pending/Queued
                            Document.is_original == False
                        ).first()
                        
                        if db_next_doc:
                            logging.info(f"Sequential: processing next doc {db_next_doc.id}")
                            db_next_doc.processing_status = "In progress"  # ✅ NOW mark it
                            session.commit()
                            
                            set_blob_metadata(
                                os.environ["DD_DOCS_BLOB_STORAGE_CONNECTION_STRING"],
                                os.environ["DD_DOCS_STORAGE_CONTAINER_NAME"],
                                str(db_next_doc.id),
                                {
                                    "original_file_name": db_next_doc.original_file_name,
                                    "extension": db_next_doc.type,
                                    "is_dd": "True",
                                    "doc_id": str(db_next_doc.id),
                                    "dd_id": dd_id,
                                    "next_chunk_to_process": "0"
                                }
                            )
                            
                            send_custom_event_to_eventgrid(
                                os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_ENDPOINT"],
                                topic_key=os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_KEY"],
                                subject=str(db_next_doc.id),
                                data={"doc_id": str(db_next_doc.id), "dd_id": dd_id, "email": email},
                                event_type="AIShop.DD.BlobMetadataUpdated"
                            )
                            
                            return func.HttpResponse("Processed", status_code=200)
                        
                        else:
                            # All done - completion logic
                            logging.info("No more documents to process")
                            
                            try:
                                generate_all_folder_descriptions(dd_id, session)
                            except Exception as e:
                                logging.error(f"Failed to generate folder descriptions: {str(e)}")
                            
                            total_processed_docs = session.query(Document).join(Folder).filter(
                                Folder.dd_id == dd_id,
                                Document.processing_status == "Complete",
                                Document.is_original == False
                            ).count()
                            
                            try:
                                send_processing_complete_email(
                                    recipient_email=email if email != "simon@alchemylawafrica.com" else "sachin@theaishop.ai",
                                    dd_name=due_diligence.name if hasattr(due_diligence, 'name') else f"Project {dd_id}",
                                    dd_id=str(dd_id),
                                    total_documents=total_processed_docs,
                                    processing_type="document"
                                )
                            except Exception as e:
                                logging.error(f"Failed to send email: {str(e)}")
                            
                            if member:
                                send_custom_event_to_eventgrid(
                                    os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_ENDPOINT"],
                                    topic_key=os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_KEY"],
                                    subject="Process_Risks",
                                    data={"email": email, "dd_id": dd_id},
                                    event_type="AIShop.DD.ProcessRisks"
                                )
                            
                            return func.HttpResponse("Processed", status_code=200)
        else:
            logging.info(f"Unknown event type {event_type}")
            raise ValueError(f"Unknown event type {event_type}")

    except Exception as e:
        logging.info(f"FAILED")
        logging.info(e)
        logging.exception("Function failed to process Event Grid event")
        return func.HttpResponse("Error", status_code=500)