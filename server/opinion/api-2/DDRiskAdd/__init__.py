# File: server/opinion/api-2/DDRiskAdd/__init__.py
import logging
import os
import json
import azure.functions as func
from shared.utils import auth_get_email, send_custom_event_to_eventgrid
from shared.models import Perspective, PerspectiveRisk, DueDiligenceMember, DueDiligence
from shared.session import transactional_session
import uuid

def main(req: func.HttpRequest) -> func.HttpResponse:
    
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        
        data = req.get_json()
        dd_id = data["dd_id"]
        
        if "risks" in data:
            risks = data["risks"]
        else:
            risks = [{
                "category": data["category"],
                "detail": data["detail"],
                "folder_scope": data.get("folder_scope", "All Folders")
            }]
        
        email, err = auth_get_email(req)
        if err:
            return err
        
        with transactional_session() as session:
            # First check if user is the owner
            due_diligence = session.query(DueDiligence).filter(
                DueDiligence.id == dd_id
            ).first()
            
            if not due_diligence:
                return func.HttpResponse("Due diligence not found", status_code=404)
            
            # Check if user is owner or member
            is_owner = due_diligence.owned_by == email
            
            perspective = (
                session.query(Perspective)
                .join(DueDiligenceMember, Perspective.member_id == DueDiligenceMember.id)
                .filter(
                    DueDiligenceMember.dd_id == dd_id,
                    DueDiligenceMember.member_email == email
                )
                .first()
            )
            
            # If user is owner but doesn't have a perspective, create one
            if is_owner and not perspective:
                logging.info(f"Owner {email} doesn't have perspective, creating membership and perspective")
                
                # Create member record
                new_member_id = uuid.uuid4()
                member = DueDiligenceMember(id=new_member_id, dd_id=dd_id, member_email=email)
                session.add(member)
                session.flush()  # Get the member ID
                
                # Create perspective
                perspective = Perspective(
                    member_id=new_member_id,
                    lens="Project Owner",  # Default lens for owner
                    risks=[]
                )
                session.add(perspective)
                session.flush()  # Get the perspective
            
            # If still no perspective and not owner, deny access
            if not perspective and not is_owner:
                return func.HttpResponse("User is not a member or owner of this due diligence", status_code=400)
            
            # Add all risks with proper field initialization
            for risk_data in risks:
                new_risk = PerspectiveRisk(
                    category=risk_data["category"],
                    detail=risk_data["detail"],
                    folder_scope=risk_data.get("folder_scope", "All Folders"),
                    is_deleted=False,
                    is_processed=False  
                )
                perspective.risks.append(new_risk)
            
            session.commit()
            
            # Trigger risk processing
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