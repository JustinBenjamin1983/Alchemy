# File: server/opinion/api-2/DDList/__init__.py

import logging
import os
import json

import azure.functions as func
from shared.utils import auth_get_email
from sqlalchemy import exists, case, and_, or_
from shared.session import transactional_session
from shared.models import DueDiligence, DueDiligenceMember, Folder, Document

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('working')

    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)
    
    try:

        filter_type = req.params.get("filter_type")
        email, err = auth_get_email(req)
        if err:
            return err
        
        logging.info(f"{filter_type=} {email=}")
        
        with transactional_session() as session:

            results = []
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
            match filter_type:
                case "involves_me":
                    results = (
                        session.query(DueDiligence, has_in_progress_docs)
                        .outerjoin(DueDiligence.members)
                        .filter(
                            or_(
                                DueDiligence.owned_by == email,
                                DueDiligenceMember.member_email == email
                            )
                        )
                        .order_by(DueDiligence.created_at.desc())
                        .all()
                    )
                case "doesnt_involve_me":
                    results = (
                        session.query(DueDiligence, has_in_progress_docs)
                        .outerjoin(DueDiligence.members)
                        .filter(
                            and_(
                                DueDiligence.owned_by != email,
                                or_(
                                    DueDiligenceMember.member_email != email,
                                    DueDiligenceMember.member_email.is_(None)
                                )
                            )
                        )
                        .order_by(DueDiligence.created_at.desc())
                        .all()
                    )
                case "im_a_member":
                    results = (
                        session.query(DueDiligence)
                        .outerjoin(DueDiligence.members)
                        .filter(DueDiligenceMember.member_email == email)
                        .order_by(DueDiligence.created_at.desc())
                        .all()
                    )
                case "im_not_a_member":
                    results = (
                        session.query(DueDiligence, has_in_progress_docs)
                        .outerjoin(DueDiligence.members)
                        .filter(
                            or_(
                                DueDiligenceMember.member_email != email,
                                DueDiligenceMember.member_email.is_(None)
                            )
                        )
                        .order_by(DueDiligence.created_at.desc())
                        .all()
                    )
                case "owned_by_me":
                    results = (
                        session.query(DueDiligence, has_in_progress_docs)
                        .outerjoin(DueDiligence.members)
                        .filter(DueDiligence.owned_by == email)
                        .order_by(DueDiligence.created_at.desc())
                        .all()
                    )
                case _:
                    return "Unknown"

            projected_results = [
                {
                    **{k: v for k, v in dd.to_dict().items() if k in ["id", "name", "created_at"]},
                    "has_in_progress_docs": has_progress
                }
                for dd, has_progress in results
            ]


        return func.HttpResponse(json.dumps({"due_diligences":projected_results}), mimetype="application/json", status_code=200)

    except Exception as e:
        logging.info(e)
        logging.error(str(e))
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
