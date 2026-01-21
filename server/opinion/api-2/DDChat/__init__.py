# Enhanced DDChat/__init__.py
import logging
import os
import json
import textwrap
import azure.functions as func
from shared.utils import auth_get_email
from shared.session import transactional_session
from shared.models import (
    Folder, DueDiligence, DueDiligenceMember, Perspective, Document,
    DDQuestion, DDQuestionReferencedDoc, PerspectiveRisk, PerspectiveRiskFinding,
    DDAnalysisRun
)

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"
COGNITIVE_SEARCH_AVAILABLE = bool(os.environ.get("COGNITIVE_SEARCH_ENDPOINT", "").strip())

# Only import search dependencies if Cognitive Search is available
if COGNITIVE_SEARCH_AVAILABLE:
    from shared.rag import create_chunks_and_embeddings_from_text, get_llm_summary, get_llm_summaryChat, assess_legal_risks, combine_multiple_responses
    from shared.ddsearch import search_similar_dd_documents, format_search_results_for_prompt


def get_findings_context(session, dd_id, run_id=None, limit=50):
    """
    Query findings from the database for the current DD/run.
    Returns formatted context string for the LLM prompt.
    """
    try:
        # Build query for findings
        query = (
            session.query(
                PerspectiveRiskFinding.phrase,
                PerspectiveRiskFinding.status,
                PerspectiveRiskFinding.page_number,
                PerspectiveRiskFinding.evidence_quote,
                PerspectiveRiskFinding.deal_impact,
                PerspectiveRiskFinding.financial_exposure_amount,
                PerspectiveRiskFinding.financial_exposure_currency,
                PerspectiveRiskFinding.financial_exposure_calculation,
                PerspectiveRiskFinding.finding_type,
                PerspectiveRiskFinding.confidence_score,
                PerspectiveRiskFinding.direct_answer,
                PerspectiveRiskFinding.is_cross_document,
                PerspectiveRiskFinding.source_cluster,
                PerspectiveRisk.category,
                Document.original_file_name,
                Folder.path.label("folder_path")
            )
            .join(PerspectiveRisk, PerspectiveRisk.id == PerspectiveRiskFinding.perspective_risk_id)
            .join(Perspective, Perspective.id == PerspectiveRisk.perspective_id)
            .join(DueDiligenceMember, DueDiligenceMember.id == Perspective.member_id)
            .outerjoin(Document, Document.id == PerspectiveRiskFinding.document_id)
            .outerjoin(Folder, Folder.id == Document.folder_id)
            .filter(DueDiligenceMember.dd_id == dd_id)
        )

        # Filter by run_id if provided
        if run_id:
            query = query.filter(PerspectiveRiskFinding.run_id == run_id)

        # Order by severity (critical first) and confidence
        query = query.order_by(
            PerspectiveRiskFinding.status.desc(),
            PerspectiveRiskFinding.confidence_score.desc()
        ).limit(limit)

        findings = query.all()

        if not findings:
            return ""

        # Format findings for context
        findings_text = []
        for f in findings:
            finding_str = f"""
### Finding: {f.category or 'Uncategorized'} - {f.status or 'Unknown'}
Document: {f.original_file_name or 'Cross-document analysis'} (Page {f.page_number or 'N/A'})
Description: {f.phrase}
"""
            if f.evidence_quote:
                finding_str += f'Evidence: "{f.evidence_quote}"\n'

            if f.direct_answer:
                finding_str += f"Direct Answer: {f.direct_answer}\n"

            if f.deal_impact and f.deal_impact != 'none':
                finding_str += f"Deal Impact: {f.deal_impact}\n"

            if f.financial_exposure_amount:
                finding_str += f"Financial Exposure: {f.financial_exposure_currency or 'ZAR'} {f.financial_exposure_amount:,.2f}"
                if f.financial_exposure_calculation:
                    finding_str += f" ({f.financial_exposure_calculation})"
                finding_str += "\n"

            if f.is_cross_document:
                finding_str += f"Cross-Document Analysis: Yes (Cluster: {f.source_cluster or 'general'})\n"

            finding_str += "---"
            findings_text.append(finding_str)

        return "\n".join(findings_text)

    except Exception as e:
        logging.error(f"Error getting findings context: {str(e)}")
        return ""


def get_synthesis_context(session, dd_id, run_id=None):
    """
    Get synthesis data (executive summary, deal assessment) for broader context.
    """
    try:
        query = session.query(DDAnalysisRun).filter(DDAnalysisRun.dd_id == dd_id)

        if run_id:
            query = query.filter(DDAnalysisRun.id == run_id)
        else:
            # Get most recent completed run
            query = query.filter(DDAnalysisRun.status == "completed").order_by(DDAnalysisRun.completed_at.desc())

        run = query.first()

        if not run or not run.synthesis_data:
            return ""

        synthesis = run.synthesis_data
        context_parts = []

        # Executive summary
        if synthesis.get("executive_summary"):
            context_parts.append(f"**Executive Summary:** {synthesis['executive_summary']}")

        # Deal assessment
        if synthesis.get("deal_assessment"):
            assessment = synthesis["deal_assessment"]
            if assessment.get("can_proceed") is not None:
                context_parts.append(f"**Can Proceed:** {'Yes' if assessment['can_proceed'] else 'No'}")
            if assessment.get("overall_risk_rating"):
                context_parts.append(f"**Overall Risk Rating:** {assessment['overall_risk_rating']}")
            if assessment.get("blocking_issues"):
                context_parts.append(f"**Blocking Issues:** {', '.join(assessment['blocking_issues'])}")
            if assessment.get("key_risks"):
                context_parts.append(f"**Key Risks:** {', '.join(assessment['key_risks'])}")

        # Deal blockers
        if synthesis.get("deal_blockers"):
            blockers = synthesis["deal_blockers"]
            if blockers:
                blocker_list = [f"- {b.get('issue', 'Unknown')}: {b.get('description', '')}" for b in blockers[:5]]
                context_parts.append(f"**Deal Blockers:**\n" + "\n".join(blocker_list))

        # Conditions precedent
        if synthesis.get("conditions_precedent"):
            cps = synthesis["conditions_precedent"]
            if cps:
                cp_list = [f"- {cp.get('description', 'Unknown')}" for cp in cps[:5]]
                context_parts.append(f"**Conditions Precedent:**\n" + "\n".join(cp_list))

        # Financial exposure summary
        if synthesis.get("financial_exposures"):
            exposures = synthesis["financial_exposures"]
            if exposures.get("items"):
                total = sum(item.get("amount", 0) for item in exposures["items"] if item.get("amount"))
                context_parts.append(f"**Total Financial Exposure:** ZAR {total:,.2f}")

        return "\n\n".join(context_parts)

    except Exception as e:
        logging.error(f"Error getting synthesis context: {str(e)}")
        return ""


def main(req: func.HttpRequest) -> func.HttpResponse:

    # Skip function-key check in dev mode
    if not DEV_MODE and req.headers.get('function-key') != os.environ.get("FUNCTION_KEY"):
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)

    try:
        email, err = auth_get_email(req)
        if err:
            return err

        data = req.get_json()
        question = data["question"]
        dd_id = data["dd_id"]
        run_id = data.get("run_id")  # Analysis run ID for findings context
        document_ids = data.get("document_ids", [])  # Now accepts multiple
        folder_ids = data.get("folder_ids", [])      # Now accepts multiple

        # Handle legacy single references
        if data.get("document_id"):
            document_ids = [data["document_id"]]
        if data.get("folder_id"):
            folder_ids = [data["folder_id"]]

        due_diligence_briefing = None
        perspective_lens = None

        with transactional_session() as session:
            # Get DD briefing and perspective
            result = (
                session.query(DueDiligence.briefing, Perspective.lens)
                .outerjoin(DueDiligenceMember, DueDiligenceMember.dd_id == DueDiligence.id)
                .outerjoin(Perspective, Perspective.member_id == DueDiligenceMember.id)
                .filter(DueDiligence.id == dd_id)
                .first()
            )
            
            if result is None:
                return func.HttpResponse("No such due-diligence", status_code=404)
            
            due_diligence_briefing = result.briefing
            perspective_lens = result.lens or "(no perspective set)"

            # Get findings and synthesis context from the DD pipeline
            findings_context = get_findings_context(session, dd_id, run_id)
            synthesis_context = get_synthesis_context(session, dd_id, run_id)

            logging.info(f"Retrieved {len(findings_context)} chars of findings context")

            # Check if Cognitive Search is available
            if not COGNITIVE_SEARCH_AVAILABLE:
                logging.info("Cognitive Search not available - using direct Claude with findings")
                response = direct_claude_chat(
                    question, dd_id, due_diligence_briefing, perspective_lens, session,
                    findings_context, synthesis_context
                )
            else:
                # Determine search scope
                has_specific_references = bool(document_ids or folder_ids)

                if not has_specific_references:
                    # Case 1: No specific references - search whole DD
                    logging.info("No specific references - searching entire DD")
                    response = search_entire_dd(
                        question, dd_id, due_diligence_briefing, perspective_lens, session,
                        findings_context, synthesis_context
                    )

                elif len(document_ids) + len(folder_ids) == 1:
                    # Case 2: Single reference - current behavior
                    logging.info("Single reference - using current search method")
                    response = search_single_reference(
                        question, dd_id, document_ids, folder_ids,
                        due_diligence_briefing, perspective_lens, session,
                        findings_context, synthesis_context
                    )

                else:
                    # Case 3: Multiple references - separate searches and combine
                    logging.info(f"Multiple references - {len(document_ids)} docs, {len(folder_ids)} folders")
                    response = search_multiple_references(
                        question, dd_id, document_ids, folder_ids,
                        due_diligence_briefing, perspective_lens, session,
                        findings_context, synthesis_context
                    )
            
            # Save question to database
            save_question_to_db(
                session, dd_id, question, response, email, 
                document_ids, folder_ids
            )
            
            return func.HttpResponse(
                json.dumps(response), 
                mimetype="application/json", 
                status_code=200
            )
    
    except Exception as e:
        logging.error(f"Error in DDChat: {str(e)}")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)


def direct_claude_chat(question, dd_id, briefing, lens, session, findings_context="", synthesis_context=""):
    """
    Answer questions using findings from the DD pipeline.
    Falls back to general guidance if no findings are available.
    """
    import anthropic

    # Get list of documents in this DD for context
    documents = (
        session.query(Document.id, Document.original_file_name, Folder.path)
        .outerjoin(Folder, Folder.id == Document.folder_id)
        .filter(Document.dd_id == dd_id)
        .limit(50)
        .all()
    )

    doc_list = "\n".join([
        f"- {doc.original_file_name} (in {doc.path or 'root'})"
        for doc in documents
    ]) if documents else "No documents uploaded yet."

    # Build prompt with findings context if available
    if findings_context:
        prompt = textwrap.dedent(f"""
            You are a South African corporate transactional partner in a prestigious South African law firm with over 30 years of experience.

            You are assisting with a due diligence exercise. The client's overall objective is:
            {briefing or "Not specified"}

            Your perspective on this due diligence is:
            {lens}

            ## ANALYZED FINDINGS FROM DD PIPELINE
            The following findings have been extracted and analyzed from the uploaded documents during the due diligence process:

            {findings_context}

            ## DEAL ASSESSMENT SUMMARY
            {synthesis_context if synthesis_context else "No synthesis data available yet."}

            ## Documents in this DD:
            {doc_list}

            ## USER'S QUESTION:
            {question}

            ## INSTRUCTIONS:
            Answer the question based primarily on the analyzed findings above. When citing information:
            - Reference the specific document and page number
            - Quote the relevant evidence when available
            - If the information is not in the findings, clearly state that it was not found in the analyzed documents
            - Do NOT make up information that is not in the findings
        """)
    else:
        prompt = textwrap.dedent(f"""
            You are a South African corporate transactional partner in a prestigious South African law firm with over 30 years of experience.

            You are assisting with a due diligence exercise. The client's overall objective is:
            {briefing or "Not specified"}

            Your perspective on this due diligence is:
            {lens}

            Documents available in this due diligence:
            {doc_list}

            NOTE: No analyzed findings are available yet. The DD analysis may not have been run, or no findings were extracted. You can only provide general guidance based on the DD context and your legal expertise.

            User's question: {question}

            Please provide a helpful response. If the question requires specific document content, explain that the DD analysis needs to be run first to extract findings.
        """)

    try:
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        answer = message.content[0].text
    except Exception as e:
        logging.error(f"Claude API error: {str(e)}")
        answer = f"I apologize, but I encountered an error processing your question. Please try again later. (Error: {str(e)})"

    return {
        "answer": answer,
        "documents_referenced": [],
        "risks": [],
        "search_scope": "findings_context" if findings_context else "direct_chat_fallback",
        "note": "Response based on analyzed DD findings" if findings_context else "No findings available - general guidance only"
    }


def search_entire_dd(question, dd_id, briefing, lens, session, findings_context="", synthesis_context=""):
    """Search the entire due diligence without specific document/folder constraints"""

    chunks_and_embeddings = create_chunks_and_embeddings_from_text(question)
    embeddings = [value for item in chunks_and_embeddings for value in item["embedding"]]

    # Search without hierarchy or document constraints
    found_results = search_similar_dd_documents(
        dd_id, None, None, embeddings, question, False,
        int(os.environ.get("AISearch_K", "10"))
    )

    formatted_results = format_search_results_for_prompt(found_results["value"])

    llm_prompt = create_base_prompt(question, briefing, lens, findings_context, synthesis_context)
    llm_answer = get_llm_summaryChat(formatted_results, llm_prompt)

    # Assess risks in the response
    risks = assess_legal_risks(llm_answer, formatted_results, briefing)

    return {
        "answer": llm_answer if llm_answer != "NONE" else None,
        "documents_referenced": format_referenced_docs(formatted_results),
        "risks": risks,
        "search_scope": "entire_dd_with_findings" if findings_context else "entire_dd"
    }


def search_single_reference(question, dd_id, document_ids, folder_ids, briefing, lens, session, findings_context="", synthesis_context=""):
    """Handle single document or folder reference - current behavior"""

    chunks_and_embeddings = create_chunks_and_embeddings_from_text(question)
    embeddings = [value for item in chunks_and_embeddings for value in item["embedding"]]

    hierarchy = None
    document_id = document_ids[0] if document_ids else None
    folder_id = folder_ids[0] if folder_ids else None

    if folder_id:
        folder = session.get(Folder, folder_id)
        if folder:
            hierarchy = folder.hierarchy

    found_results = search_similar_dd_documents(
        dd_id, hierarchy, [document_id] if document_id else None,
        embeddings, question, False, int(os.environ.get("AISearch_K", "10"))
    )

    formatted_results = format_search_results_for_prompt(found_results["value"])

    llm_prompt = create_base_prompt(question, briefing, lens, findings_context, synthesis_context)
    llm_answer = get_llm_summaryChat(formatted_results, llm_prompt)

    # Assess risks
    risks = assess_legal_risks(llm_answer, formatted_results, briefing)

    return {
        "answer": llm_answer if llm_answer != "NONE" else None,
        "documents_referenced": format_referenced_docs(formatted_results),
        "risks": risks,
        "search_scope": "single_reference_with_findings" if findings_context else "single_reference"
    }


def search_multiple_references(question, dd_id, document_ids, folder_ids, briefing, lens, session, findings_context="", synthesis_context=""):
    """Handle multiple document/folder references with separate searches and combination"""

    chunks_and_embeddings = create_chunks_and_embeddings_from_text(question)
    embeddings = [value for item in chunks_and_embeddings for value in item["embedding"]]

    individual_responses = []
    all_referenced_docs = []
    all_risks = []

    # Process each document reference
    for doc_id in document_ids:
        logging.info(f"Processing document reference: {doc_id}")

        found_results = search_similar_dd_documents(
            dd_id, None, [doc_id], embeddings, question, False,
            int(os.environ.get("AISearch_K", "5"))
        )

        formatted_results = format_search_results_for_prompt(found_results["value"])

        if formatted_results:
            llm_prompt = create_base_prompt(question, briefing, lens, findings_context, synthesis_context)
            answer = get_llm_summaryChat(formatted_results, llm_prompt)

            if answer and answer != "NONE":
                individual_responses.append({
                    "source_type": "document",
                    "source_id": doc_id,
                    "answer": answer,
                    "documents": formatted_results
                })
                all_referenced_docs.extend(formatted_results)

                # Assess risks for this response
                risks = assess_legal_risks(answer, formatted_results, briefing)
                all_risks.extend(risks)

    # Process each folder reference
    for folder_id in folder_ids:
        logging.info(f"Processing folder reference: {folder_id}")

        folder = session.get(Folder, folder_id)
        hierarchy = folder.hierarchy if folder else None

        found_results = search_similar_dd_documents(
            dd_id, hierarchy, None, embeddings, question, False,
            int(os.environ.get("AISearch_K", "5"))
        )

        formatted_results = format_search_results_for_prompt(found_results["value"])

        if formatted_results:
            llm_prompt = create_base_prompt(question, briefing, lens, findings_context, synthesis_context)
            answer = get_llm_summaryChat(formatted_results, llm_prompt)
            
            if answer and answer != "NONE":
                individual_responses.append({
                    "source_type": "folder",
                    "source_id": folder_id,
                    "answer": answer,
                    "documents": formatted_results
                })
                all_referenced_docs.extend(formatted_results)
                
                # Assess risks for this response
                risks = assess_legal_risks(answer, formatted_results, briefing)
                all_risks.extend(risks)
    
    # Combine all individual responses
    if individual_responses:
        combined_answer = combine_multiple_responses(
            question, individual_responses, briefing, lens
        )
        
        # Deduplicate referenced documents
        unique_docs = {}
        for doc in all_referenced_docs:
            key = f"{doc['doc_id']}-{doc['page_number']}"
            if key not in unique_docs:
                unique_docs[key] = doc
        
        # Consolidate and rank risks
        consolidated_risks = consolidate_risks(all_risks)
        
        return {
            "answer": combined_answer,
            "documents_referenced": list(unique_docs.values()),
            "risks": consolidated_risks,
            "search_scope": "multiple_references",
            "individual_responses": len(individual_responses)
        }
    
    else:
        return {
            "answer": "No relevant information found in the specified documents/folders.",
            "documents_referenced": [],
            "risks": [],
            "search_scope": "multiple_references",
            "individual_responses": 0
        }


def create_base_prompt(question, briefing, lens, findings_context="", synthesis_context=""):
    """Create the base LLM prompt with optional findings context"""

    # Build findings section if available
    findings_section = ""
    if findings_context:
        findings_section = f"""
        ## ANALYZED FINDINGS FROM DD PIPELINE
        The following findings have been extracted and analyzed from the uploaded documents:

        {findings_context}

        ## DEAL ASSESSMENT SUMMARY
        {synthesis_context if synthesis_context else "No synthesis data available yet."}

        """

    return textwrap.dedent(f"""
        You are a South African corporate transactional partner in a prestigious South African law firm with over 30 years of experience in drafting opinions.
        You have vast knowledge of all areas of company and corporate law, law of contract, law of property, insolvency law, law of sale and purchase and the law of cession, all as applied in South Africa.

        You are performing a due diligence with the overall objective from the client as:
        {briefing}

        Your perspective on this due diligence is:
        {lens}
        {findings_section}
        As part of a due diligence exercise, you wish to compose a good answer to the following question based on your review of documentation supplied by the client:
        {question}

        IMPORTANT: When answering, prioritize information from the ANALYZED FINDINGS above. Cite specific documents and page numbers when available. If information is not in the findings, say so clearly.
    """)


def format_referenced_docs(formatted_results):
    """Format referenced documents for response"""
    return [
        {
            "doc_id": item["doc_id"],
            "filename": item["filename"],
            "page_number": item["page_number"],
            "folder_path": item["folder_path"]
        }
        for item in formatted_results
    ]


def consolidate_risks(all_risks):
    """Consolidate and rank risks from multiple sources"""
    risk_map = {}
    
    for risk in all_risks:
        risk_key = risk.get("description", "Unknown risk")
        
        if risk_key in risk_map:
            # If risk already exists, take the higher severity
            existing_level = risk_map[risk_key]["level"]
            new_level = risk["level"]
            
            severity_order = {"yellow": 1, "amber": 2, "red": 3}
            if severity_order.get(new_level, 0) > severity_order.get(existing_level, 0):
                risk_map[risk_key] = risk
        else:
            risk_map[risk_key] = risk
    
    # Sort by severity (red first, then amber, then yellow)
    severity_order = {"red": 3, "amber": 2, "yellow": 1}
    sorted_risks = sorted(
        risk_map.values(), 
        key=lambda x: severity_order.get(x["level"], 0), 
        reverse=True
    )
    
    return sorted_risks[:10]  # Limit to top 10 risks


def save_question_to_db(session, dd_id, question, response, email, document_ids, folder_ids):
    """Save the question and response to database"""
    
    try:
        # Get names for storage
        folder_names = []
        document_names = []
        
        for folder_id in folder_ids:
            folder = session.get(Folder, folder_id)
            if folder:
                folder_names.append(folder.folder_name)
        
        for doc_id in document_ids:
            document = session.get(Document, doc_id)
            if document:
                document_names.append(document.original_file_name)
        
        # Save question
        dd_question = DDQuestion(
            dd_id=dd_id,
            question=question,
            answer=response.get("answer"),
            asked_by=email,
            folder_id=folder_ids[0] if len(folder_ids) == 1 else None,
            document_id=document_ids[0] if len(document_ids) == 1 else None,
            folder_name=folder_names[0] if len(folder_names) == 1 else ", ".join(folder_names),
            document_name=document_names[0] if len(document_names) == 1 else ", ".join(document_names)
        )
        
        session.add(dd_question)
        session.flush()
        
        # Save referenced documents
        for doc in response.get("documents_referenced", []):
            referenced_doc = DDQuestionReferencedDoc(
                question_id=dd_question.id,
                doc_id=doc["doc_id"],
                filename=doc["filename"],
                page_number=doc["page_number"],
                folder_path=doc["folder_path"]
            )
            session.add(referenced_doc)
        
        session.commit()
        
    except Exception as e:
        logging.error(f"Error saving question to DB: {str(e)}")
        session.rollback()