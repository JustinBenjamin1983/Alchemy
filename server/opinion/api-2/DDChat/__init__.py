# Enhanced DDChat/__init__.py
import logging
import os
import json
import textwrap
import azure.functions as func
from shared.utils import auth_get_email
from shared.rag import create_chunks_and_embeddings_from_text, get_llm_summary, get_llm_summaryChat, assess_legal_risks, combine_multiple_responses
from shared.ddsearch import search_similar_dd_documents, format_search_results_for_prompt
from shared.session import transactional_session
from shared.models import Folder, DueDiligence, DueDiligenceMember, Perspective, Document, DDQuestion, DDQuestionReferencedDoc

def main(req: func.HttpRequest) -> func.HttpResponse:
    
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        email, err = auth_get_email(req)
        if err:
            return err
        
        data = req.get_json()
        question = data["question"]
        dd_id = data["dd_id"]
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
            
            # Determine search scope
            has_specific_references = bool(document_ids or folder_ids)
            
            if not has_specific_references:
                # Case 1: No specific references - search whole DD
                logging.info("No specific references - searching entire DD")
                response = search_entire_dd(
                    question, dd_id, due_diligence_briefing, perspective_lens, session
                )
            
            elif len(document_ids) + len(folder_ids) == 1:
                # Case 2: Single reference - current behavior
                logging.info("Single reference - using current search method")
                response = search_single_reference(
                    question, dd_id, document_ids, folder_ids, 
                    due_diligence_briefing, perspective_lens, session
                )
            
            else:
                # Case 3: Multiple references - separate searches and combine
                logging.info(f"Multiple references - {len(document_ids)} docs, {len(folder_ids)} folders")
                response = search_multiple_references(
                    question, dd_id, document_ids, folder_ids,
                    due_diligence_briefing, perspective_lens, session
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


def search_entire_dd(question, dd_id, briefing, lens, session):
    """Search the entire due diligence without specific document/folder constraints"""
    
    chunks_and_embeddings = create_chunks_and_embeddings_from_text(question)
    embeddings = [value for item in chunks_and_embeddings for value in item["embedding"]]
    
    # Search without hierarchy or document constraints
    found_results = search_similar_dd_documents(
        dd_id, None, None, embeddings, question, False, 
        int(os.environ.get("AISearch_K", "10"))
    )
    
    formatted_results = format_search_results_for_prompt(found_results["value"])
    
    llm_prompt = create_base_prompt(question, briefing, lens)
    llm_answer = get_llm_summaryChat(formatted_results, llm_prompt)
    
    # Assess risks in the response
    risks = assess_legal_risks(llm_answer, formatted_results, briefing)
    
    return {
        "answer": llm_answer if llm_answer != "NONE" else None,
        "documents_referenced": format_referenced_docs(formatted_results),
        "risks": risks,
        "search_scope": "entire_dd"
    }


def search_single_reference(question, dd_id, document_ids, folder_ids, briefing, lens, session):
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
    
    llm_prompt = create_base_prompt(question, briefing, lens)
    llm_answer = get_llm_summaryChat(formatted_results, llm_prompt)
    
    # Assess risks
    risks = assess_legal_risks(llm_answer, formatted_results, briefing)
    
    return {
        "answer": llm_answer if llm_answer != "NONE" else None,
        "documents_referenced": format_referenced_docs(formatted_results),
        "risks": risks,
        "search_scope": "single_reference"
    }


def search_multiple_references(question, dd_id, document_ids, folder_ids, briefing, lens, session):
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
            llm_prompt = create_base_prompt(question, briefing, lens)
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
            llm_prompt = create_base_prompt(question, briefing, lens)
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


def create_base_prompt(question, briefing, lens):
    """Create the base LLM prompt"""
    return textwrap.dedent(f"""
        You are a South African corporate transactional partner in a prestigious South African law firm with over 30 years of experience in drafting opinions.
        You have vast knowledge of all areas of company and corporate law, law of contract, law of property, insolvency law, law of sale and purchase and the law of cession, all as applied in South Africa.
        
        You are performing a due diligence with the overall objective from the client as:
        {briefing}
        
        Your perspective on this due diligence is: 
        {lens}
        
        As part of a due diligence exercise, you wish to compose a good answer to the following question based on your review of documentation supplied by the client:
        {question}
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