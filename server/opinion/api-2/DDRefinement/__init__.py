# DDRefinement/__init__.py
"""
Phase 10: Report Refinement Loop

Enables iterative report improvement through AI-driven refinements
with version control.

Endpoints:
- POST /api/dd-refinement/propose - AI proposes change based on prompt
- POST /api/dd-refinement/merge - Apply proposed change, create new version
- GET /api/dd-report-versions/{run_id} - List all versions
- GET /api/dd-report-versions/{run_id}/{version} - Get specific version
"""
import logging
import os
import json
import azure.functions as func
import uuid as uuid_module

from shared.utils import auth_get_email
from shared.session import transactional_session

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def get_claude_client():
    """Import and create Claude client."""
    import sys
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)

    from dd_enhanced.core.claude_client import ClaudeClient
    return ClaudeClient()


def propose_change(run_id: str, prompt: str, user_email: str = None) -> dict:
    """
    AI proposes a change based on user's refinement prompt.

    Args:
        run_id: Analysis run ID
        prompt: User's refinement request
        user_email: User's email for tracking

    Returns:
        Proposed change with before/after preview
    """
    import sys
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)

    from dd_enhanced.core.report_versions import propose_refinement

    client = get_claude_client()

    with transactional_session() as session:
        result = propose_refinement(
            run_id=run_id,
            prompt=prompt,
            client=client,
            session=session
        )

        if "error" not in result:
            result["requested_by"] = user_email

        return result


def merge_change(
    run_id: str,
    proposal: dict,
    action: str = "merge",
    edited_text: str = None,
    user_email: str = None
) -> dict:
    """
    Apply or discard a proposed change.

    Args:
        run_id: Analysis run ID
        proposal: Proposal dict from propose_change
        action: "merge" | "discard" | "edit"
        edited_text: If action is "edit", the user's edited text
        user_email: User's email for tracking

    Returns:
        New version info if merged, or confirmation of discard
    """
    import sys
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)

    from dd_enhanced.core.report_versions import apply_refinement

    if action == "discard":
        return {
            "status": "discarded",
            "proposal_id": proposal.get("proposal_id"),
            "message": "Proposed change discarded"
        }

    if action == "edit" and edited_text:
        # Update proposal with user's edited text
        proposal["proposed_text"] = edited_text
        proposal["reasoning"] = f"User edited: {proposal.get('reasoning', '')}"

    with transactional_session() as session:
        result = apply_refinement(
            run_id=run_id,
            proposal=proposal,
            created_by=user_email,
            session=session
        )

        if "error" not in result:
            result["status"] = "merged"
            result["message"] = f"Created version {result.get('version')}"

        return result


def list_versions(run_id: str) -> dict:
    """
    List all report versions for a run.

    Args:
        run_id: Analysis run ID

    Returns:
        List of version metadata
    """
    import sys
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)

    from dd_enhanced.core.report_versions import get_report_versions

    with transactional_session() as session:
        versions = get_report_versions(run_id, session)

        return {
            "run_id": run_id,
            "total_versions": len(versions),
            "versions": versions
        }


def get_version(run_id: str, version: int = None, version_id: str = None) -> dict:
    """
    Get a specific version with full content.

    Args:
        run_id: Analysis run ID
        version: Version number (optional)
        version_id: Version UUID (optional)

    Returns:
        Full version content
    """
    import sys
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)

    from dd_enhanced.core.report_versions import get_version_content

    with transactional_session() as session:
        return get_version_content(
            run_id=run_id,
            version=version,
            version_id=version_id,
            session=session
        )


def compare_versions(run_id: str, version1: int, version2: int) -> dict:
    """
    Compare two versions.

    Args:
        run_id: Analysis run ID
        version1: First version number
        version2: Second version number

    Returns:
        Diff between versions
    """
    import sys
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)

    from dd_enhanced.core.report_versions import get_version_diff

    with transactional_session() as session:
        return get_version_diff(
            run_id=run_id,
            version1=version1,
            version2=version2,
            session=session
        )


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Refinement loop endpoints.

    POST /api/dd-refinement/propose
    Body: {
        "run_id": "uuid",
        "prompt": "Expand on environmental risk section"
    }
    Returns: { "proposal": {...}, "current_version": 1 }

    POST /api/dd-refinement/merge
    Body: {
        "run_id": "uuid",
        "proposal": {...},
        "action": "merge|discard|edit",
        "edited_text": "..." (optional, for action=edit)
    }
    Returns: { "version": 2, "status": "merged" }

    GET /api/dd-report-versions/{run_id}
    Returns: { "versions": [...] }

    GET /api/dd-report-versions/{run_id}/{version}
    Returns: { "content": {...} }

    POST /api/dd-refinement/compare
    Body: {
        "run_id": "uuid",
        "version1": 1,
        "version2": 2
    }
    Returns: { "diffs": [...] }
    """

    # Auth check
    if not DEV_MODE and req.headers.get('function-key') != os.environ.get("FUNCTION_KEY"):
        return func.HttpResponse("", status_code=401)

    try:
        email, err = auth_get_email(req)
        if err:
            return err

        method = req.method
        action = req.route_params.get("action", "")

        # GET - List versions or get specific version
        if method == "GET":
            run_id = req.route_params.get("run_id") or req.params.get("run_id")
            version = req.route_params.get("version") or req.params.get("version")

            if not run_id:
                return func.HttpResponse(
                    json.dumps({"error": "run_id is required"}),
                    status_code=400,
                    mimetype="application/json"
                )

            if version:
                result = get_version(run_id, version=int(version))
            else:
                result = list_versions(run_id)

            return func.HttpResponse(
                json.dumps(result, default=str),
                status_code=200 if "error" not in result else 404,
                mimetype="application/json"
            )

        # POST - Propose, merge, or compare
        if method == "POST":
            try:
                req_body = req.get_json()
            except ValueError:
                return func.HttpResponse(
                    json.dumps({"error": "Invalid JSON body"}),
                    status_code=400,
                    mimetype="application/json"
                )

            post_action = req_body.get("action", action)

            if post_action == "propose":
                run_id = req_body.get("run_id")
                prompt = req_body.get("prompt")

                if not run_id or not prompt:
                    return func.HttpResponse(
                        json.dumps({"error": "run_id and prompt are required"}),
                        status_code=400,
                        mimetype="application/json"
                    )

                result = propose_change(run_id, prompt, user_email=email)

            elif post_action == "merge":
                run_id = req_body.get("run_id")
                proposal = req_body.get("proposal")
                merge_action = req_body.get("merge_action", "merge")
                edited_text = req_body.get("edited_text")

                if not run_id or not proposal:
                    return func.HttpResponse(
                        json.dumps({"error": "run_id and proposal are required"}),
                        status_code=400,
                        mimetype="application/json"
                    )

                result = merge_change(
                    run_id=run_id,
                    proposal=proposal,
                    action=merge_action,
                    edited_text=edited_text,
                    user_email=email
                )

            elif post_action == "compare":
                run_id = req_body.get("run_id")
                version1 = req_body.get("version1")
                version2 = req_body.get("version2")

                if not run_id or version1 is None or version2 is None:
                    return func.HttpResponse(
                        json.dumps({"error": "run_id, version1, and version2 are required"}),
                        status_code=400,
                        mimetype="application/json"
                    )

                result = compare_versions(run_id, version1, version2)

            else:
                return func.HttpResponse(
                    json.dumps({"error": f"Unknown action: {post_action}"}),
                    status_code=400,
                    mimetype="application/json"
                )

            status_code = 200 if "error" not in result else 400
            return func.HttpResponse(
                json.dumps(result, default=str),
                status_code=status_code,
                mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps({"error": "Method not allowed"}),
            status_code=405,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"[DDRefinement] Error: {str(e)}")
        logging.exception("Full traceback:")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
