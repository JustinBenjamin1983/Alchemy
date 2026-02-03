# File: server/opinion/api-2/DDEvaluationRun/__init__.py
"""
Run DD Evaluation against a rubric.

Uses Claude Opus to compare generated findings against expected rubric items.
Produces detailed scoring breakdown with performance band classification.

Performance Bands (based on score out of total_points, typically 200):
- EXCELLENT: 90%+ (180-200)
- GOOD: 75-89% (150-179)
- ADEQUATE: 60-74% (120-149)
- BELOW_EXPECTATIONS: 45-59% (90-119)
- FAILURE: <45% (<90)
"""
import logging
import os
import json
import datetime
import uuid as uuid_module
import azure.functions as func
from shared.utils import auth_get_email
from shared.models import (
    DDEvaluation, DDEvalRubric, DDAnalysisRun, DueDiligence,
    PerspectiveRiskFinding, Document, Folder
)
from shared.session import transactional_session
from dd_enhanced.core.claude_client import ClaudeClient


DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"

# Evaluation model - always use Opus for evaluation accuracy
EVALUATION_MODEL = "claude-opus-4-20250514"


def main(req: func.HttpRequest) -> func.HttpResponse:

    # Skip function-key check in dev mode
    if not DEV_MODE and req.headers.get('function-key') != os.environ.get("FUNCTION_KEY"):
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)

    try:
        data = req.get_json()
        rubric_id = data.get("rubric_id")
        run_id = data.get("run_id")

        if not rubric_id:
            return func.HttpResponse(
                json.dumps({"error": "rubric_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        if not run_id:
            return func.HttpResponse(
                json.dumps({"error": "run_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Convert to UUID objects
        try:
            rubric_uuid = uuid_module.UUID(rubric_id)
            run_uuid = uuid_module.UUID(run_id)
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid UUID format"}),
                status_code=400,
                mimetype="application/json"
            )

        email, err = auth_get_email(req)
        if err:
            return err

        with transactional_session() as session:
            # Verify rubric exists
            rubric = session.query(DDEvalRubric).filter(
                DDEvalRubric.id == rubric_uuid
            ).first()

            if not rubric:
                return func.HttpResponse(
                    json.dumps({"error": "Rubric not found"}),
                    status_code=404,
                    mimetype="application/json"
                )

            # Verify run exists and is completed
            run = session.query(DDAnalysisRun).filter(
                DDAnalysisRun.id == run_uuid
            ).first()

            if not run:
                return func.HttpResponse(
                    json.dumps({"error": "Analysis run not found"}),
                    status_code=404,
                    mimetype="application/json"
                )

            if run.status != "completed":
                return func.HttpResponse(
                    json.dumps({"error": f"Analysis run must be completed. Current status: {run.status}"}),
                    status_code=400,
                    mimetype="application/json"
                )

            # Create evaluation record
            evaluation = DDEvaluation(
                rubric_id=rubric_uuid,
                run_id=run_uuid,
                status="evaluating",
                evaluation_model=EVALUATION_MODEL,
                created_at=datetime.datetime.utcnow()
            )
            session.add(evaluation)
            session.flush()
            evaluation_id = str(evaluation.id)

            # Gather all data needed for evaluation
            findings_data = _gather_findings_data(session, run)
            synthesis_data = run.synthesis_data or {}

            logging.info(f"[DDEvaluationRun] Starting evaluation {evaluation_id}")
            logging.info(f"[DDEvaluationRun] Found {len(findings_data)} findings")

            try:
                # Run the evaluation
                scores = _run_evaluation(
                    rubric.rubric_data,
                    findings_data,
                    synthesis_data
                )

                # Calculate totals
                total_score = _calculate_total_score(scores)
                percentage = (total_score / rubric.total_points * 100) if rubric.total_points > 0 else 0
                performance_band = _get_performance_band(percentage)

                # Update evaluation with results
                evaluation.status = "completed"
                evaluation.scores = scores
                evaluation.total_score = total_score
                evaluation.percentage = round(percentage, 2)
                evaluation.performance_band = performance_band
                evaluation.completed_at = datetime.datetime.utcnow()

                session.commit()

                logging.info(f"[DDEvaluationRun] Evaluation completed: {total_score}/{rubric.total_points} ({percentage:.1f}%) - {performance_band}")

                return func.HttpResponse(
                    json.dumps({
                        "id": evaluation_id,
                        "status": "completed",
                        "scores": scores,
                        "total_score": total_score,
                        "max_score": rubric.total_points,
                        "percentage": round(percentage, 2),
                        "performance_band": performance_band
                    }),
                    status_code=200,
                    mimetype="application/json"
                )

            except Exception as eval_error:
                logging.error(f"[DDEvaluationRun] Evaluation failed: {str(eval_error)}")
                evaluation.status = "failed"
                evaluation.error_message = str(eval_error)
                session.commit()

                return func.HttpResponse(
                    json.dumps({
                        "id": evaluation_id,
                        "status": "failed",
                        "error": str(eval_error)
                    }),
                    status_code=500,
                    mimetype="application/json"
                )

    except Exception as e:
        logging.info(e)
        logging.error(str(e))
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def _gather_findings_data(session, run: DDAnalysisRun) -> list:
    """Gather all findings from the run with document info."""
    findings = session.query(PerspectiveRiskFinding).filter(
        PerspectiveRiskFinding.run_id == run.id
    ).all()

    findings_data = []
    for finding in findings:
        # Get document name
        doc_name = None
        if finding.document_id:
            doc = session.query(Document).filter(
                Document.id == finding.document_id
            ).first()
            if doc:
                doc_name = doc.original_file_name

        findings_data.append({
            "id": str(finding.id),
            "title": finding.phrase,
            "analysis": finding.direct_answer,
            "evidence": finding.evidence_quote,
            "severity": str(finding.status) if finding.status else None,
            "action_priority": str(finding.action_priority) if finding.action_priority else None,
            "deal_impact": str(finding.deal_impact) if finding.deal_impact else None,
            "financial_exposure": finding.financial_exposure_amount,
            "document_name": doc_name,
            "page_reference": finding.page_number,
            "clause_reference": finding.clause_reference,
            "is_cross_document": finding.is_cross_document,
            "cross_doc_source": finding.cross_doc_source,
            "category": finding.folder_category,
            "action_category": str(finding.action_category) if finding.action_category else None,
            "statutory_act": finding.statutory_act,
            "statutory_section": finding.statutory_section
        })

    return findings_data


def _run_evaluation(rubric_data: dict, findings_data: list, synthesis_data: dict) -> dict:
    """
    Run the Claude Opus evaluation comparing findings against rubric.
    Returns detailed scoring breakdown.
    """
    client = ClaudeClient()

    # Build the evaluation prompt
    prompt = _build_evaluation_prompt(rubric_data, findings_data, synthesis_data)

    system_prompt = """You are an expert legal due diligence evaluator. Your task is to compare DD analysis findings against a known-answer rubric and score how well the analysis detected expected issues.

Be rigorous but fair in your assessment:
- Award full points when a finding clearly addresses the rubric item
- Award partial points when a finding partially addresses the item
- Award zero points when the item was missed entirely

You must respond with valid JSON only, no additional text."""

    logging.info(f"[DDEvaluationRun] Sending evaluation prompt to {EVALUATION_MODEL}")

    response = client.complete(
        prompt=prompt,
        system=system_prompt,
        model="opus",
        max_tokens=8192,
        json_mode=True
    )

    if "error" in response:
        raise Exception(f"Evaluation API error: {response.get('error')}")

    return response


def _build_evaluation_prompt(rubric_data: dict, findings_data: list, synthesis_data: dict) -> str:
    """Build the prompt for Claude to evaluate findings against rubric."""

    # Format findings for the prompt
    findings_text = json.dumps(findings_data, indent=2)

    # Format synthesis data
    synthesis_text = json.dumps(synthesis_data, indent=2) if synthesis_data else "No synthesis data available"

    # Format rubric
    rubric_text = json.dumps(rubric_data, indent=2)

    prompt = f"""Evaluate the following DD analysis findings against the evaluation rubric.

## EVALUATION RUBRIC (Expected Findings)
{rubric_text}

## ACTUAL FINDINGS FROM DD ANALYSIS
{findings_text}

## SYNTHESIS/SUMMARY DATA
{synthesis_text}

## SCORING INSTRUCTIONS

For each category in the rubric, evaluate whether the DD analysis identified the expected items:

1. **Critical Red Flags** (typically 10 points each):
   - Full points if the exact issue was identified with correct severity
   - Half points if the issue was partially identified or severity was understated
   - Zero points if the issue was completely missed

2. **Amber Flags** (typically 5 points each):
   - Full points if identified
   - Half points if partially identified
   - Zero points if missed

3. **Cross-Document Connections** (typically 5 points each):
   - Full points if the cross-document conflict/connection was identified
   - Half points if one document's issue was found but connection wasn't made
   - Zero points if missed

4. **Intelligent Questions** (typically 15 points total):
   - Assess whether the analysis generated relevant follow-up questions
   - Score based on quality and relevance of questions in synthesis

5. **Missing Documents Flagged** (typically 1 point each):
   - Points for each expected missing document category that was flagged

6. **Overall Quality** (typically 5 points):
   - Assess the overall quality of analysis, clarity, and actionability

## REQUIRED OUTPUT FORMAT

Return a JSON object with this exact structure:
{{
  "critical_red_flags": {{
    "found": [
      {{"rubric_item": "item name", "matched_finding": "finding title or summary", "score": X, "max": Y, "notes": "explanation"}}
    ],
    "missed": [
      {{"rubric_item": "item name", "score": 0, "max": Y, "notes": "why it was missed or not found"}}
    ],
    "score": TOTAL_SCORE,
    "max": TOTAL_MAX
  }},
  "amber_flags": {{
    "found": [...],
    "missed": [...],
    "score": TOTAL_SCORE,
    "max": TOTAL_MAX
  }},
  "cross_document_connections": {{
    "found": [...],
    "missed": [...],
    "score": TOTAL_SCORE,
    "max": TOTAL_MAX
  }},
  "intelligent_questions": {{
    "assessment": "description of question quality",
    "examples": ["example question 1", "example question 2"],
    "score": X,
    "max": Y
  }},
  "missing_documents": {{
    "flagged": [{{"category": "...", "score": X, "max": Y}}],
    "not_flagged": [{{"category": "...", "score": 0, "max": Y}}],
    "score": TOTAL_SCORE,
    "max": TOTAL_MAX
  }},
  "overall_quality": {{
    "assessment": "overall quality assessment",
    "strengths": ["strength 1", "strength 2"],
    "weaknesses": ["weakness 1", "weakness 2"],
    "score": X,
    "max": Y
  }},
  "summary": {{
    "total_score": TOTAL,
    "max_score": MAX,
    "key_gaps": ["gap 1", "gap 2"],
    "key_strengths": ["strength 1", "strength 2"]
  }}
}}

Evaluate thoroughly and return the JSON response:"""

    return prompt


def _calculate_total_score(scores: dict) -> int:
    """Calculate total score from scoring breakdown."""
    total = 0

    categories = [
        "critical_red_flags",
        "amber_flags",
        "cross_document_connections",
        "intelligent_questions",
        "missing_documents",
        "overall_quality"
    ]

    for category in categories:
        if category in scores and isinstance(scores[category], dict):
            total += scores[category].get("score", 0)

    # Also check summary if provided
    if "summary" in scores and isinstance(scores["summary"], dict):
        summary_total = scores["summary"].get("total_score")
        if summary_total is not None:
            return int(summary_total)

    return int(total)


def _get_performance_band(percentage: float) -> str:
    """Get performance band based on percentage score."""
    if percentage >= 90:
        return "EXCELLENT"
    elif percentage >= 75:
        return "GOOD"
    elif percentage >= 60:
        return "ADEQUATE"
    elif percentage >= 45:
        return "BELOW_EXPECTATIONS"
    else:
        return "FAILURE"
