import logging
import os
import json

import azure.functions as func

from shared.utils import auth_get_email, send_custom_event_to_eventgrid
from shared.models import PerspectiveRisk, PerspectiveRiskFinding
from shared.session import transactional_session

def main(req: func.HttpRequest) -> func.HttpResponse:
    
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        
        data = req.get_json()

        perspective_risk_id = data["perspective_risk_id"]
        detail = data["detail"]
        dd_id = data["dd_id"]

        email, err = auth_get_email(req)
        if err:
            return err
        
        with transactional_session() as session:
            pr = session.get(PerspectiveRisk, perspective_risk_id)
            if not pr:
                return func.HttpResponse(f"Can't find perspective risk {perspective_risk_id=}", status_code=404)
            
            pr.detail = detail

            # invalidate associated perspective risk findings
            session.query(PerspectiveRiskFinding).filter(
                PerspectiveRiskFinding.perspective_risk_id == perspective_risk_id
            ).update({PerspectiveRiskFinding.status: "Deleted"}, synchronize_session="fetch")
            session.commit()
            send_custom_event_to_eventgrid(os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_ENDPOINT"],
                        topic_key = os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_KEY"],
                        subject = "Process_Risks",
                        data = {"email": email, "dd_id": dd_id},
                        event_type = "AIShop.DD.ProcessRisks")

        return func.HttpResponse("", mimetype="application/json", status_code=200)
           

    except Exception as e:
        logging.info(e)
        logging.error(str(e))
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
