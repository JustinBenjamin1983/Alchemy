import logging
import os
import json

import azure.functions as func
from shared.utils import auth_get_email
from shared.session import transactional_session
from shared.models import Document, DueDiligence, Folder
from sqlalchemy import exists, case, and_
from sqlalchemy.orm import joinedload

def main(req: func.HttpRequest) -> func.HttpResponse:
    
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        
        email, err = auth_get_email(req)
        if err:
            return err
        
        dd_id = req.params.get("dd_id")
        result = {}

        with transactional_session() as session:
            has_in_progress_docs = case(
                (
                    exists().where(
                        and_(
                            Folder.dd_id == DueDiligence.id,
                            Document.folder_id == Folder.id,
                            Document.processing_status == "In progress"
                        )
                    ),
                    True
                ),
                else_=False
            ).label("has_in_progress_docs")
            due_diligence, has_in_progress_docs = (
                session.query(DueDiligence, has_in_progress_docs)
                .filter(DueDiligence.id == dd_id)
                .options(
                    joinedload(DueDiligence.folders).joinedload(Folder.documents)
                )
                .first()
            )

            if not due_diligence:
                raise ValueError(f"DueDiligence {dd_id} not found")

            result = {
                "dd_id": str(due_diligence.id),
                "name": due_diligence.name,
                "briefing": due_diligence.briefing,
                "owned_by": due_diligence.owned_by,
                "original_file_name": due_diligence.original_file_name,
                "created_at": due_diligence.created_at.isoformat(),
                "has_in_progress_docs": has_in_progress_docs,
                "folders": []
            }
            
            for folder in due_diligence.folders:
                folder_data = {
                    "folder_id": str(folder.id),
                    "folder_name": folder.folder_name,
                    "level": folder.path.count("/"),
                    "hierarchy": folder.hierarchy,
                    "description":folder.description,
                    "documents": [
                        {
                            "document_id": str(doc.id),
                            "original_file_name": doc.original_file_name,
                            "type": doc.type,
                            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                            "processing_status": doc.processing_status,
                            "size_in_bytes": doc.size_in_bytes,
                            "is_original": doc.is_original,
                            "description":doc.description
                        }
                        for doc in folder.documents
                    ]
                }

                result["folders"].append(folder_data)
            
            result["folders"] = [
                {**f_outer, "has_children": any(
                    (f_outer["folder_id"] + "/" in f_inner["hierarchy"] or "/" + f_outer["folder_id"] in f_inner["hierarchy"])  and f_inner["folder_id"] != f_outer["folder_id"]
                    for f_inner in result["folders"]
                )}
                for f_outer in result["folders"]
            ]
            
            result["folders"] = [
                folder for folder in result["folders"]
                if not (
                    len(folder["documents"]) == 1 and folder["documents"][0]["is_original"]
                )
            ]

        return func.HttpResponse(json.dumps(result), mimetype="application/json", status_code=200)

    except Exception as e:
        logging.info(e)
        logging.error(str(e))
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
