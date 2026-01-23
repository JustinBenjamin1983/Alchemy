"""
Phase 10: Report Version Management

Enables iterative report refinement through AI-driven changes
with full version history and diff tracking.

Key Functions:
- create_report_version: Create new report version
- get_report_versions: List all versions for a run
- get_version_diff: Compare two versions
- propose_refinement: AI proposes change based on user prompt
- apply_refinement: Apply proposed change and create new version
"""

from typing import List, Dict, Any, Optional
import logging
import uuid
import json
from datetime import datetime
from difflib import unified_diff

logger = logging.getLogger(__name__)


def create_report_version(
    run_id: str,
    content: Dict[str, Any],
    refinement_prompt: str = None,
    changes: List[Dict[str, Any]] = None,
    created_by: str = None,
    session: Any = None
) -> Dict[str, Any]:
    """
    Create a new report version.

    Args:
        run_id: Analysis run ID
        content: Full report content (synthesis_data structure)
        refinement_prompt: User's refinement request that led to this version
        changes: List of changes from previous version
        created_by: User email
        session: Database session

    Returns:
        Created version dict
    """
    from shared.models import DDReportVersion

    run_uuid = uuid.UUID(run_id) if isinstance(run_id, str) else run_id

    # Get the current highest version number
    existing_versions = (
        session.query(DDReportVersion)
        .filter(DDReportVersion.run_id == run_uuid)
        .order_by(DDReportVersion.version.desc())
        .all()
    )

    new_version_num = (existing_versions[0].version + 1) if existing_versions else 1

    # Mark all existing versions as not current
    for v in existing_versions:
        v.is_current = False

    # Generate change summary if changes provided
    change_summary = None
    if changes:
        change_summary = _generate_change_summary(changes)

    # Create new version
    new_version = DDReportVersion(
        id=uuid.uuid4(),
        run_id=run_uuid,
        version=new_version_num,
        content=content,
        refinement_prompt=refinement_prompt,
        changes=changes,
        is_current=True,
        change_summary=change_summary,
        created_at=datetime.utcnow(),
        created_by=created_by
    )

    session.add(new_version)
    session.commit()

    return {
        "version_id": str(new_version.id),
        "version": new_version_num,
        "is_current": True,
        "created_at": new_version.created_at.isoformat(),
        "change_summary": change_summary
    }


def get_report_versions(run_id: str, session: Any) -> List[Dict[str, Any]]:
    """
    Get all report versions for a run.

    Args:
        run_id: Analysis run ID
        session: Database session

    Returns:
        List of version dicts (without full content for efficiency)
    """
    from shared.models import DDReportVersion

    run_uuid = uuid.UUID(run_id) if isinstance(run_id, str) else run_id

    versions = (
        session.query(DDReportVersion)
        .filter(DDReportVersion.run_id == run_uuid)
        .order_by(DDReportVersion.version.desc())
        .all()
    )

    return [
        {
            "version_id": str(v.id),
            "version": v.version,
            "is_current": v.is_current,
            "refinement_prompt": v.refinement_prompt,
            "change_summary": v.change_summary,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "created_by": v.created_by
        }
        for v in versions
    ]


def get_version_content(
    run_id: str,
    version: int = None,
    version_id: str = None,
    session: Any = None
) -> Dict[str, Any]:
    """
    Get full content for a specific version.

    Args:
        run_id: Analysis run ID
        version: Version number (optional, defaults to current)
        version_id: Version UUID (alternative to version number)
        session: Database session

    Returns:
        Version dict with full content
    """
    from shared.models import DDReportVersion

    run_uuid = uuid.UUID(run_id) if isinstance(run_id, str) else run_id

    query = session.query(DDReportVersion).filter(DDReportVersion.run_id == run_uuid)

    if version_id:
        version_uuid = uuid.UUID(version_id) if isinstance(version_id, str) else version_id
        query = query.filter(DDReportVersion.id == version_uuid)
    elif version:
        query = query.filter(DDReportVersion.version == version)
    else:
        query = query.filter(DDReportVersion.is_current == True)

    db_version = query.first()

    if not db_version:
        return {"error": "Version not found"}

    return {
        "version_id": str(db_version.id),
        "version": db_version.version,
        "is_current": db_version.is_current,
        "content": db_version.content,
        "refinement_prompt": db_version.refinement_prompt,
        "changes": db_version.changes,
        "change_summary": db_version.change_summary,
        "created_at": db_version.created_at.isoformat() if db_version.created_at else None,
        "created_by": db_version.created_by
    }


def get_version_diff(
    run_id: str,
    version1: int,
    version2: int,
    session: Any
) -> Dict[str, Any]:
    """
    Compare two versions and return diff.

    Args:
        run_id: Analysis run ID
        version1: First version number
        version2: Second version number
        session: Database session

    Returns:
        Diff dict with section-by-section changes
    """
    v1 = get_version_content(run_id, version=version1, session=session)
    v2 = get_version_content(run_id, version=version2, session=session)

    if "error" in v1:
        return {"error": f"Version {version1} not found"}
    if "error" in v2:
        return {"error": f"Version {version2} not found"}

    content1 = v1.get("content", {})
    content2 = v2.get("content", {})

    diffs = []

    # Compare executive summary
    summary1 = content1.get("executive_summary", "")
    summary2 = content2.get("executive_summary", "")
    if summary1 != summary2:
        diffs.append({
            "section": "executive_summary",
            "change_type": "modified",
            "diff": _text_diff(summary1, summary2)
        })

    # Compare risk sections
    risks1 = content1.get("key_risks", [])
    risks2 = content2.get("key_risks", [])
    risk_diffs = _compare_lists(risks1, risks2, key="title")
    if risk_diffs:
        diffs.extend([{"section": "key_risks", **d} for d in risk_diffs])

    # Compare recommendations
    recs1 = content1.get("recommendations", [])
    recs2 = content2.get("recommendations", [])
    rec_diffs = _compare_lists(recs1, recs2, key="recommendation")
    if rec_diffs:
        diffs.extend([{"section": "recommendations", **d} for d in rec_diffs])

    return {
        "version1": version1,
        "version2": version2,
        "total_changes": len(diffs),
        "diffs": diffs
    }


def propose_refinement(
    run_id: str,
    prompt: str,
    client: Any,  # Claude client
    session: Any
) -> Dict[str, Any]:
    """
    AI proposes a change based on user's refinement prompt.

    Args:
        run_id: Analysis run ID
        prompt: User's refinement request
        client: Claude API client
        session: Database session

    Returns:
        Proposed change dict with before/after and reasoning
    """
    # Get current version
    current = get_version_content(run_id, session=session)
    if "error" in current:
        return current

    content = current.get("content", {})

    # Build prompt for Claude
    refinement_prompt = f"""You are helping refine a due diligence report.

CURRENT REPORT CONTENT:
{json.dumps(content, indent=2)[:30000]}

USER REFINEMENT REQUEST:
{prompt}

---

Propose a specific change to the report. You may modify:
- executive_summary
- key_risks (add/remove/modify items)
- recommendations (add/remove/modify items)
- deal_considerations
- financial_summary

Return JSON:
{{
    "section": "<which section to modify>",
    "change_type": "modify|add|remove",
    "current_text": "<current text if modifying>",
    "proposed_text": "<new text>",
    "reasoning": "<why this change addresses the user's request>",
    "affected_findings": ["<finding_ids if applicable>"]
}}

IMPORTANT:
- Make targeted changes that directly address the user's request
- Preserve the professional legal due diligence tone
- Maintain consistency with the underlying findings
- Do not invent information not supported by the findings"""

    response = client.complete(
        prompt=refinement_prompt,
        system="You are a legal due diligence expert helping refine M&A reports.",
        json_mode=True,
        max_tokens=4096,
        temperature=0.3
    )

    if "error" in response:
        return {"error": f"AI refinement failed: {response.get('error')}"}

    # Add metadata
    response["proposal_id"] = str(uuid.uuid4())
    response["run_id"] = run_id
    response["user_prompt"] = prompt
    response["proposed_at"] = datetime.utcnow().isoformat()

    return {
        "proposal": response,
        "current_version": current.get("version")
    }


def apply_refinement(
    run_id: str,
    proposal: Dict[str, Any],
    created_by: str = None,
    session: Any = None
) -> Dict[str, Any]:
    """
    Apply a proposed refinement and create new version.

    Args:
        run_id: Analysis run ID
        proposal: Proposal dict from propose_refinement
        created_by: User email
        session: Database session

    Returns:
        New version dict
    """
    # Get current content
    current = get_version_content(run_id, session=session)
    if "error" in current:
        return current

    content = current.get("content", {})
    new_content = json.loads(json.dumps(content))  # Deep copy

    # Apply the change
    section = proposal.get("section", "")
    change_type = proposal.get("change_type", "modify")
    proposed_text = proposal.get("proposed_text", "")

    if section == "executive_summary":
        new_content["executive_summary"] = proposed_text

    elif section == "key_risks":
        if change_type == "add":
            if "key_risks" not in new_content:
                new_content["key_risks"] = []
            new_content["key_risks"].append(
                {"title": proposed_text} if isinstance(proposed_text, str) else proposed_text
            )
        elif change_type == "remove":
            current_text = proposal.get("current_text", "")
            new_content["key_risks"] = [
                r for r in new_content.get("key_risks", [])
                if r.get("title") != current_text and r.get("description") != current_text
            ]
        elif change_type == "modify":
            current_text = proposal.get("current_text", "")
            for i, risk in enumerate(new_content.get("key_risks", [])):
                if risk.get("title") == current_text or risk.get("description") == current_text:
                    if isinstance(proposed_text, dict):
                        new_content["key_risks"][i].update(proposed_text)
                    else:
                        new_content["key_risks"][i]["description"] = proposed_text
                    break

    elif section == "recommendations":
        if change_type == "add":
            if "recommendations" not in new_content:
                new_content["recommendations"] = []
            new_content["recommendations"].append(
                {"recommendation": proposed_text} if isinstance(proposed_text, str) else proposed_text
            )
        elif change_type == "remove":
            current_text = proposal.get("current_text", "")
            new_content["recommendations"] = [
                r for r in new_content.get("recommendations", [])
                if r.get("recommendation") != current_text
            ]
        elif change_type == "modify":
            current_text = proposal.get("current_text", "")
            for i, rec in enumerate(new_content.get("recommendations", [])):
                if rec.get("recommendation") == current_text:
                    if isinstance(proposed_text, dict):
                        new_content["recommendations"][i].update(proposed_text)
                    else:
                        new_content["recommendations"][i]["recommendation"] = proposed_text
                    break

    elif section in new_content:
        new_content[section] = proposed_text

    # Create new version with the change
    changes = [{
        "section": section,
        "change_type": change_type,
        "old_text": proposal.get("current_text"),
        "new_text": proposed_text,
        "reasoning": proposal.get("reasoning")
    }]

    return create_report_version(
        run_id=run_id,
        content=new_content,
        refinement_prompt=proposal.get("user_prompt"),
        changes=changes,
        created_by=created_by,
        session=session
    )


def _generate_change_summary(changes: List[Dict]) -> str:
    """Generate human-readable summary of changes."""
    if not changes:
        return "No changes recorded"

    summaries = []
    for change in changes[:5]:
        section = change.get("section", "unknown")
        change_type = change.get("change_type", "modified")
        reasoning = change.get("reasoning", "")[:100]

        summaries.append(f"{change_type.title()} {section}: {reasoning}")

    return "; ".join(summaries)


def _text_diff(text1: str, text2: str) -> str:
    """Generate unified diff between two texts."""
    if not text1:
        text1 = ""
    if not text2:
        text2 = ""

    lines1 = text1.splitlines(keepends=True)
    lines2 = text2.splitlines(keepends=True)

    diff = list(unified_diff(lines1, lines2, lineterm=''))
    return "\n".join(diff[:50])  # Limit diff size


def _compare_lists(
    list1: List[Dict],
    list2: List[Dict],
    key: str
) -> List[Dict]:
    """Compare two lists of dicts by a key field."""
    diffs = []

    keys1 = {item.get(key): item for item in list1}
    keys2 = {item.get(key): item for item in list2}

    # Find added
    for k in keys2:
        if k not in keys1:
            diffs.append({
                "change_type": "added",
                "item": keys2[k]
            })

    # Find removed
    for k in keys1:
        if k not in keys2:
            diffs.append({
                "change_type": "removed",
                "item": keys1[k]
            })

    # Find modified
    for k in keys1:
        if k in keys2 and keys1[k] != keys2[k]:
            diffs.append({
                "change_type": "modified",
                "old_item": keys1[k],
                "new_item": keys2[k]
            })

    return diffs
