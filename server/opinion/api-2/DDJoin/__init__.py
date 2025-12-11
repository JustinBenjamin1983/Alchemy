# File: server/opinion/api-2/DDJoin/__init__.py


import logging
import os
import json
import azure.functions as func
from shared.utils import auth_get_email, send_custom_event_to_eventgrid
from shared.models import DueDiligenceMember, Perspective, PerspectiveRisk
from shared.session import transactional_session
from sqlalchemy import exists, and_
import uuid

def main(req: func.HttpRequest) -> func.HttpResponse:
    
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        
        email, err = auth_get_email(req)
        if err:
            return err
        
        data = req.get_json()
        dd_id = data["dd_id"]
        risks = data["risks"]
        lens = data["lens"]
        
        with transactional_session() as session:
            member = session.query(DueDiligenceMember).filter_by(dd_id=dd_id, member_email=email).first()
            
            if member:
                return func.HttpResponse(f"User {email} is already a member", status_code=500) # can't rejoin
            
            new_member_id = uuid.uuid4()
            if not member:
                member = DueDiligenceMember(id=new_member_id, dd_id=dd_id, member_email=email)
                session.add(member)
            
            # Create perspective risks with folder scope and proper field initialization
            perspective_risks = []
            for r in risks:
                risk = PerspectiveRisk(
                    category=r["category"], 
                    detail=r["description"],
                    folder_scope=r.get("folder", "All Folders"),  # Save the folder scope
                    is_deleted=False,  # IMPORTANT: Explicitly set to False
                    is_processed=False  # IMPORTANT: Explicitly set to False
                )
                perspective_risks.append(risk)
            
            perspective = Perspective(
                member_id=new_member_id,
                lens=lens,
                risks=perspective_risks
            )
            session.add(perspective)
            
            # user just added to DD, so process risk for them
            send_custom_event_to_eventgrid(
                os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_ENDPOINT"],
                topic_key=os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_KEY"],
                subject="Process_Risks",
                data={"email": email, "dd_id": dd_id},
                event_type="AIShop.DD.ProcessRisks"
            )
            
        return func.HttpResponse("", mimetype="application/json", status_code=200)
    except Exception as e:
        logging.info(e)
        logging.error(str(e))
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)