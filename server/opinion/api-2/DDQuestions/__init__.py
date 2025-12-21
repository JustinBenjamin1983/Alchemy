# DDQuestions/__init__.py
import logging
import os
import json
import azure.functions as func

from shared.utils import auth_get_email
from shared.session import transactional_session
from shared.models import DDQuestion, DDQuestionReferencedDoc
from sqlalchemy.orm import joinedload

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"

def main(req: func.HttpRequest) -> func.HttpResponse:

    if not DEV_MODE and req.headers.get('function-key') != os.environ.get("FUNCTION_KEY"):
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        email, err = auth_get_email(req)
        if err:
            return err
        
        dd_id = req.params.get('dd_id')
        if not dd_id:
            return func.HttpResponse("Missing dd_id parameter", status_code=400)

        with transactional_session() as session:
            # Get all questions for this DD with their referenced documents
            questions = (
                session.query(DDQuestion)
                .options(joinedload(DDQuestion.referenced_documents))
                .filter(DDQuestion.dd_id == dd_id)
                .order_by(DDQuestion.created_at.desc())
                .all()
            )

            # Convert to dict format
            questions_data = []
            for question in questions:
                question_dict = {
                    "id": str(question.id),
                    "question": question.question,
                    "answer": question.answer,
                    "asked_by": question.asked_by,
                    "folder_id": str(question.folder_id) if question.folder_id else None,
                    "document_id": str(question.document_id) if question.document_id else None,
                    "folder_name": question.folder_name,
                    "document_name": question.document_name,
                    "created_at": question.created_at.isoformat() if question.created_at else None,
                    "referenced_documents": [
                        {
                            "doc_id": str(ref_doc.doc_id),  # Convert UUID to string
                            "filename": ref_doc.filename,
                            "page_number": ref_doc.page_number,
                            "folder_path": ref_doc.folder_path
                        }
                        for ref_doc in question.referenced_documents
                    ]
                }
                questions_data.append(question_dict)

        return func.HttpResponse(
            json.dumps(questions_data),
            mimetype="application/json",
            status_code=200
        )
    
    except Exception as e:
        logging.exception("Error getting DD questions")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)