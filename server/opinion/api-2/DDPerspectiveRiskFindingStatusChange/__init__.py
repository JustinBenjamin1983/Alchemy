import logging
import os

import azure.functions as func

from shared.utils import auth_get_email

from shared.session import transactional_session
from shared.models import PerspectiveRiskFinding

def main(req: func.HttpRequest) -> func.HttpResponse:
    
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        email, err = auth_get_email(req)
        if err:
            return err
        
        data = req.get_json()

        status = data.get("status") # 'New', 'Red', 'Amber', 'Deleted'
        perspective_risk_finding_id = data.get("perspective_risk_finding_id", None)

        with transactional_session() as session:
           
                prf = session.get(PerspectiveRiskFinding, perspective_risk_finding_id)
                if prf is None:
                        return func.HttpResponse("Can't find PerspectiveRiskFinding", status_code=401)
                
                prf.status = status

        return func.HttpResponse("", mimetype="application/json", status_code=200)
    
    except Exception as e:
        logging.info(e)
        logging.error(str(e))
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
