"""
API endpoint for collaboration features.
Handles finding assignments, comments, and review workflows.

Phase 7: Enterprise Features
"""

import azure.functions as func
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
from sqlalchemy import text

from shared.session import transactional_session
from shared.audit import log_audit_event, AuditEventType, notify_user

logger = logging.getLogger(__name__)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Collaboration API endpoint.

    Routes:
        GET /dd-collaboration?dd_id=X&action=get_assignments
        GET /dd-collaboration?dd_id=X&action=get_comments&finding_id=Y
        GET /dd-collaboration?dd_id=X&action=get_workflow_status
        POST /dd-collaboration (action in body: assign_finding, add_comment, update_workflow)
    """
    try:
        if req.method == 'OPTIONS':
            return func.HttpResponse(status_code=200)

        if req.method == 'GET':
            return handle_get(req)
        elif req.method == 'POST':
            return handle_post(req)
        else:
            return func.HttpResponse(
                json.dumps({"error": f"Method {req.method} not allowed"}),
                status_code=405,
                mimetype="application/json"
            )

    except Exception as e:
        logger.error(f"Error in collaboration endpoint: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def handle_get(req: func.HttpRequest) -> func.HttpResponse:
    """Handle GET requests for collaboration data."""
    dd_id = req.params.get('dd_id')
    action = req.params.get('action')

    if not dd_id:
        return func.HttpResponse(
            json.dumps({"error": "dd_id is required"}),
            status_code=400,
            mimetype="application/json"
        )

    if not action:
        return func.HttpResponse(
            json.dumps({"error": "action is required"}),
            status_code=400,
            mimetype="application/json"
        )

    with transactional_session() as session:
        if action == 'get_assignments':
            finding_id = req.params.get('finding_id')
            user_id = req.params.get('user_id')
            data = get_assignments(session, dd_id, finding_id, user_id)

        elif action == 'get_comments':
            finding_id = req.params.get('finding_id')
            if not finding_id:
                return func.HttpResponse(
                    json.dumps({"error": "finding_id is required for get_comments"}),
                    status_code=400,
                    mimetype="application/json"
                )
            data = get_comments(session, finding_id)

        elif action == 'get_workflow_status':
            run_id = req.params.get('run_id')
            data = get_workflow_status(session, dd_id, run_id)

        elif action == 'get_users':
            data = get_users(session)

        else:
            return func.HttpResponse(
                json.dumps({"error": f"Unknown action: {action}"}),
                status_code=400,
                mimetype="application/json"
            )

    return func.HttpResponse(
        json.dumps(data, default=str),
        status_code=200,
        mimetype="application/json"
    )


def handle_post(req: func.HttpRequest) -> func.HttpResponse:
    """Handle POST requests for collaboration actions."""
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body"}),
            status_code=400,
            mimetype="application/json"
        )

    action = body.get('action')
    dd_id = body.get('dd_id')

    if not action:
        return func.HttpResponse(
            json.dumps({"error": "action is required in body"}),
            status_code=400,
            mimetype="application/json"
        )

    with transactional_session() as session:
        if action == 'assign_finding':
            result = assign_finding(session, body)
        elif action == 'unassign_finding':
            result = unassign_finding(session, body)
        elif action == 'add_comment':
            result = add_comment(session, body)
        elif action == 'edit_comment':
            result = edit_comment(session, body)
        elif action == 'delete_comment':
            result = delete_comment(session, body)
        elif action == 'update_workflow':
            result = update_workflow(session, body)
        elif action == 'start_workflow':
            result = start_workflow(session, body)
        elif action == 'approve_stage':
            result = approve_stage(session, body)
        elif action == 'reject_stage':
            result = reject_stage(session, body)
        else:
            return func.HttpResponse(
                json.dumps({"error": f"Unknown action: {action}"}),
                status_code=400,
                mimetype="application/json"
            )

        session.commit()

    return func.HttpResponse(
        json.dumps(result, default=str),
        status_code=200,
        mimetype="application/json"
    )


# ============================================================================
# Assignment Functions
# ============================================================================

def assign_finding(session, body: Dict) -> Dict:
    """
    Assign a finding to a user.

    Body:
        finding_id: Finding to assign
        assignee_id: User to assign to
        assigned_by: User making the assignment
        due_date: Optional due date
        notes: Optional assignment notes
    """
    finding_id = body.get('finding_id')
    assignee_id = body.get('assignee_id')
    assigned_by = body.get('assigned_by')
    due_date = body.get('due_date')
    notes = body.get('notes')
    dd_id = body.get('dd_id')

    if not finding_id or not assignee_id:
        return {"error": "finding_id and assignee_id are required"}

    assignment_id = str(uuid.uuid4())

    # Check if already assigned to this user
    existing = session.execute(
        text("""
            SELECT id FROM dd_finding_assignment
            WHERE finding_id = :finding_id AND assignee_id = :assignee_id
        """),
        {'finding_id': finding_id, 'assignee_id': assignee_id}
    ).fetchone()

    if existing:
        return {"error": "Finding already assigned to this user", "assignment_id": str(existing.id)}

    session.execute(
        text("""
            INSERT INTO dd_finding_assignment
            (id, finding_id, assignee_id, assigned_by, assigned_at, due_date, status, notes)
            VALUES (:id, :finding_id, :assignee_id, :assigned_by, :assigned_at, :due_date, :status, :notes)
        """),
        {
            'id': assignment_id,
            'finding_id': finding_id,
            'assignee_id': assignee_id,
            'assigned_by': assigned_by,
            'assigned_at': datetime.utcnow(),
            'due_date': due_date,
            'status': 'pending',
            'notes': notes
        }
    )

    # Log audit event
    log_audit_event(
        session=session,
        event_type=AuditEventType.FINDING_ASSIGNED.value,
        entity_type='finding',
        entity_id=finding_id,
        user_id=assigned_by,
        dd_id=dd_id,
        details={'assignee_id': assignee_id, 'due_date': due_date}
    )

    # Send notification (stub)
    notify_user(
        user_id=assignee_id,
        notification_type='finding_assigned',
        entity_id=finding_id,
        details={'assigned_by': assigned_by, 'due_date': due_date}
    )

    return {
        "success": True,
        "assignment_id": assignment_id,
        "message": "Finding assigned successfully"
    }


def unassign_finding(session, body: Dict) -> Dict:
    """Remove an assignment."""
    assignment_id = body.get('assignment_id')
    user_id = body.get('user_id')
    dd_id = body.get('dd_id')

    if not assignment_id:
        return {"error": "assignment_id is required"}

    # Get finding_id for audit
    result = session.execute(
        text("SELECT finding_id FROM dd_finding_assignment WHERE id = :id"),
        {'id': assignment_id}
    ).fetchone()

    if not result:
        return {"error": "Assignment not found"}

    session.execute(
        text("DELETE FROM dd_finding_assignment WHERE id = :id"),
        {'id': assignment_id}
    )

    log_audit_event(
        session=session,
        event_type=AuditEventType.FINDING_UPDATED.value,
        entity_type='finding',
        entity_id=str(result.finding_id),
        user_id=user_id,
        dd_id=dd_id,
        details={'action': 'unassigned', 'assignment_id': assignment_id}
    )

    return {"success": True, "message": "Assignment removed"}


def get_assignments(
    session,
    dd_id: str,
    finding_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> Dict:
    """
    Get assignments, optionally filtered by finding or user.
    """
    query = """
        SELECT
            a.id,
            a.finding_id,
            a.assignee_id,
            a.assigned_by,
            a.assigned_at,
            a.due_date,
            a.status,
            a.notes,
            a.completed_at,
            u1.name as assignee_name,
            u1.email as assignee_email,
            u2.name as assigned_by_name,
            f.phrase as finding_description,
            f.action_priority as finding_severity,
            f.folder_category
        FROM dd_finding_assignment a
        JOIN perspective_risk_finding f ON a.finding_id = f.id
        JOIN dd_analysis_run r ON f.run_id = r.id
        LEFT JOIN users u1 ON a.assignee_id = u1.id
        LEFT JOIN users u2 ON a.assigned_by = u2.id
        WHERE r.dd_id = :dd_id
    """
    params = {'dd_id': dd_id}

    if finding_id:
        query += " AND a.finding_id = :finding_id"
        params['finding_id'] = finding_id

    if user_id:
        query += " AND a.assignee_id = :user_id"
        params['user_id'] = user_id

    query += " ORDER BY a.assigned_at DESC"

    result = session.execute(text(query), params)
    rows = result.fetchall()

    assignments = [
        {
            'id': str(row.id),
            'finding_id': str(row.finding_id),
            'assignee': {
                'id': str(row.assignee_id) if row.assignee_id else None,
                'name': row.assignee_name,
                'email': row.assignee_email
            },
            'assigned_by': {
                'id': str(row.assigned_by) if row.assigned_by else None,
                'name': row.assigned_by_name
            },
            'assigned_at': row.assigned_at.isoformat() if row.assigned_at else None,
            'due_date': row.due_date.isoformat() if row.due_date else None,
            'status': row.status,
            'notes': row.notes,
            'completed_at': row.completed_at.isoformat() if row.completed_at else None,
            'finding': {
                'description': row.finding_description[:200] if row.finding_description else None,
                'severity': row.finding_severity,
                'folder_category': row.folder_category
            }
        }
        for row in rows
    ]

    # Summary stats
    stats = {
        'total': len(assignments),
        'pending': len([a for a in assignments if a['status'] == 'pending']),
        'in_progress': len([a for a in assignments if a['status'] == 'in_progress']),
        'completed': len([a for a in assignments if a['status'] == 'completed']),
        'overdue': len([a for a in assignments if a['due_date'] and a['status'] != 'completed'
                        and datetime.fromisoformat(a['due_date']) < datetime.utcnow()])
    }

    return {
        'assignments': assignments,
        'stats': stats
    }


# ============================================================================
# Comment Functions
# ============================================================================

def add_comment(session, body: Dict) -> Dict:
    """
    Add a comment to a finding.

    Body:
        finding_id: Finding to comment on
        user_id: User making the comment
        content: Comment text
        parent_id: Optional parent comment ID for threading
        mentioned_user_ids: Optional list of mentioned user IDs
    """
    finding_id = body.get('finding_id')
    user_id = body.get('user_id')
    content = body.get('content')
    parent_id = body.get('parent_id')
    mentioned_user_ids = body.get('mentioned_user_ids', [])
    dd_id = body.get('dd_id')

    if not finding_id or not content:
        return {"error": "finding_id and content are required"}

    comment_id = str(uuid.uuid4())

    session.execute(
        text("""
            INSERT INTO dd_finding_comment
            (id, finding_id, user_id, content, parent_id, mentioned_user_ids, created_at)
            VALUES (:id, :finding_id, :user_id, :content, :parent_id, :mentioned_user_ids, :created_at)
        """),
        {
            'id': comment_id,
            'finding_id': finding_id,
            'user_id': user_id,
            'content': content,
            'parent_id': parent_id,
            'mentioned_user_ids': mentioned_user_ids,
            'created_at': datetime.utcnow()
        }
    )

    log_audit_event(
        session=session,
        event_type=AuditEventType.COMMENT_ADDED.value,
        entity_type='finding',
        entity_id=finding_id,
        user_id=user_id,
        dd_id=dd_id,
        details={'comment_id': comment_id, 'has_parent': bool(parent_id)}
    )

    # Notify mentioned users
    for mentioned_id in mentioned_user_ids:
        notify_user(
            user_id=mentioned_id,
            notification_type='mentioned_in_comment',
            entity_id=finding_id,
            details={'comment_id': comment_id, 'mentioned_by': user_id}
        )

    return {
        "success": True,
        "comment_id": comment_id,
        "message": "Comment added successfully"
    }


def edit_comment(session, body: Dict) -> Dict:
    """Edit an existing comment."""
    comment_id = body.get('comment_id')
    content = body.get('content')
    user_id = body.get('user_id')
    dd_id = body.get('dd_id')

    if not comment_id or not content:
        return {"error": "comment_id and content are required"}

    # Verify ownership
    existing = session.execute(
        text("SELECT user_id, finding_id FROM dd_finding_comment WHERE id = :id"),
        {'id': comment_id}
    ).fetchone()

    if not existing:
        return {"error": "Comment not found"}

    if str(existing.user_id) != user_id:
        return {"error": "Cannot edit another user's comment"}

    session.execute(
        text("""
            UPDATE dd_finding_comment
            SET content = :content, updated_at = :updated_at
            WHERE id = :id
        """),
        {
            'id': comment_id,
            'content': content,
            'updated_at': datetime.utcnow()
        }
    )

    log_audit_event(
        session=session,
        event_type=AuditEventType.COMMENT_EDITED.value,
        entity_type='finding',
        entity_id=str(existing.finding_id),
        user_id=user_id,
        dd_id=dd_id,
        details={'comment_id': comment_id}
    )

    return {"success": True, "message": "Comment updated"}


def delete_comment(session, body: Dict) -> Dict:
    """Delete a comment (soft delete by clearing content)."""
    comment_id = body.get('comment_id')
    user_id = body.get('user_id')
    dd_id = body.get('dd_id')

    if not comment_id:
        return {"error": "comment_id is required"}

    # Verify ownership
    existing = session.execute(
        text("SELECT user_id, finding_id FROM dd_finding_comment WHERE id = :id"),
        {'id': comment_id}
    ).fetchone()

    if not existing:
        return {"error": "Comment not found"}

    if str(existing.user_id) != user_id:
        return {"error": "Cannot delete another user's comment"}

    session.execute(
        text("""
            UPDATE dd_finding_comment
            SET content = '[Deleted]', deleted_at = :deleted_at
            WHERE id = :id
        """),
        {
            'id': comment_id,
            'deleted_at': datetime.utcnow()
        }
    )

    log_audit_event(
        session=session,
        event_type=AuditEventType.COMMENT_DELETED.value,
        entity_type='finding',
        entity_id=str(existing.finding_id),
        user_id=user_id,
        dd_id=dd_id,
        details={'comment_id': comment_id}
    )

    return {"success": True, "message": "Comment deleted"}


def get_comments(session, finding_id: str) -> Dict:
    """Get all comments for a finding, threaded."""
    result = session.execute(
        text("""
            SELECT
                c.id,
                c.finding_id,
                c.user_id,
                c.content,
                c.parent_id,
                c.mentioned_user_ids,
                c.created_at,
                c.updated_at,
                c.deleted_at,
                u.name as user_name,
                u.email as user_email
            FROM dd_finding_comment c
            LEFT JOIN users u ON c.user_id = u.id
            WHERE c.finding_id = :finding_id
            ORDER BY c.created_at ASC
        """),
        {'finding_id': finding_id}
    )
    rows = result.fetchall()

    # Build threaded structure
    comments_by_id = {}
    root_comments = []

    for row in rows:
        comment = {
            'id': str(row.id),
            'finding_id': str(row.finding_id),
            'user': {
                'id': str(row.user_id) if row.user_id else None,
                'name': row.user_name,
                'email': row.user_email
            },
            'content': row.content,
            'parent_id': str(row.parent_id) if row.parent_id else None,
            'mentioned_user_ids': row.mentioned_user_ids or [],
            'created_at': row.created_at.isoformat() if row.created_at else None,
            'updated_at': row.updated_at.isoformat() if row.updated_at else None,
            'is_deleted': row.deleted_at is not None,
            'replies': []
        }
        comments_by_id[comment['id']] = comment

        if not row.parent_id:
            root_comments.append(comment)

    # Thread replies
    for comment in comments_by_id.values():
        if comment['parent_id'] and comment['parent_id'] in comments_by_id:
            comments_by_id[comment['parent_id']]['replies'].append(comment)

    return {
        'finding_id': finding_id,
        'comments': root_comments,
        'total_count': len(rows)
    }


# ============================================================================
# Workflow Functions
# ============================================================================

def start_workflow(session, body: Dict) -> Dict:
    """
    Start a review workflow for a DD analysis run.

    Body:
        dd_id: DD project ID
        run_id: Analysis run ID
        created_by: User starting the workflow
        stages: List of stages (e.g., ['initial_review', 'partner_review', 'final_approval'])
        workflow_type: Type of workflow (e.g., 'standard', 'expedited')
    """
    dd_id = body.get('dd_id')
    run_id = body.get('run_id')
    created_by = body.get('created_by')
    stages = body.get('stages', ['initial_review', 'partner_review', 'final_approval'])
    workflow_type = body.get('workflow_type', 'standard')

    if not dd_id or not run_id:
        return {"error": "dd_id and run_id are required"}

    workflow_id = str(uuid.uuid4())

    session.execute(
        text("""
            INSERT INTO dd_review_workflow
            (id, dd_id, run_id, workflow_type, current_stage, stages, status, created_by, created_at)
            VALUES (:id, :dd_id, :run_id, :workflow_type, :current_stage, :stages, :status, :created_by, :created_at)
        """),
        {
            'id': workflow_id,
            'dd_id': dd_id,
            'run_id': run_id,
            'workflow_type': workflow_type,
            'current_stage': stages[0] if stages else 'review',
            'stages': stages,
            'status': 'in_progress',
            'created_by': created_by,
            'created_at': datetime.utcnow()
        }
    )

    log_audit_event(
        session=session,
        event_type=AuditEventType.WORKFLOW_STARTED.value,
        entity_type='dd',
        entity_id=dd_id,
        user_id=created_by,
        dd_id=dd_id,
        details={'workflow_id': workflow_id, 'run_id': run_id, 'workflow_type': workflow_type}
    )

    return {
        "success": True,
        "workflow_id": workflow_id,
        "current_stage": stages[0] if stages else 'review',
        "message": "Workflow started successfully"
    }


def approve_stage(session, body: Dict) -> Dict:
    """
    Approve the current workflow stage.

    Body:
        workflow_id: Workflow to approve
        user_id: User approving
        comments: Optional approval comments
    """
    workflow_id = body.get('workflow_id')
    user_id = body.get('user_id')
    comments = body.get('comments')
    dd_id = body.get('dd_id')

    if not workflow_id:
        return {"error": "workflow_id is required"}

    # Get current workflow state
    workflow = session.execute(
        text("""
            SELECT id, dd_id, current_stage, stages, status
            FROM dd_review_workflow
            WHERE id = :workflow_id
        """),
        {'workflow_id': workflow_id}
    ).fetchone()

    if not workflow:
        return {"error": "Workflow not found"}

    if workflow.status != 'in_progress':
        return {"error": f"Workflow is {workflow.status}, cannot approve"}

    stages = workflow.stages or []
    current_idx = stages.index(workflow.current_stage) if workflow.current_stage in stages else -1

    # Record approval
    approval_id = str(uuid.uuid4())
    session.execute(
        text("""
            INSERT INTO dd_workflow_approval
            (id, workflow_id, stage, approved_by, approved_at, status, comments)
            VALUES (:id, :workflow_id, :stage, :approved_by, :approved_at, :status, :comments)
        """),
        {
            'id': approval_id,
            'workflow_id': workflow_id,
            'stage': workflow.current_stage,
            'approved_by': user_id,
            'approved_at': datetime.utcnow(),
            'status': 'approved',
            'comments': comments
        }
    )

    # Move to next stage or complete
    if current_idx < len(stages) - 1:
        next_stage = stages[current_idx + 1]
        session.execute(
            text("""
                UPDATE dd_review_workflow
                SET current_stage = :next_stage
                WHERE id = :workflow_id
            """),
            {'workflow_id': workflow_id, 'next_stage': next_stage}
        )
        message = f"Stage '{workflow.current_stage}' approved. Moved to '{next_stage}'."
    else:
        # Final stage approved - complete workflow
        session.execute(
            text("""
                UPDATE dd_review_workflow
                SET status = 'completed', completed_at = :completed_at
                WHERE id = :workflow_id
            """),
            {'workflow_id': workflow_id, 'completed_at': datetime.utcnow()}
        )
        message = "Workflow completed successfully."

    log_audit_event(
        session=session,
        event_type=AuditEventType.WORKFLOW_APPROVED.value,
        entity_type='dd',
        entity_id=str(workflow.dd_id),
        user_id=user_id,
        dd_id=dd_id or str(workflow.dd_id),
        details={
            'workflow_id': workflow_id,
            'stage': workflow.current_stage,
            'approval_id': approval_id
        }
    )

    return {
        "success": True,
        "approval_id": approval_id,
        "message": message
    }


def reject_stage(session, body: Dict) -> Dict:
    """
    Reject the current workflow stage.

    Body:
        workflow_id: Workflow to reject
        user_id: User rejecting
        comments: Required rejection reason
    """
    workflow_id = body.get('workflow_id')
    user_id = body.get('user_id')
    comments = body.get('comments')
    dd_id = body.get('dd_id')

    if not workflow_id:
        return {"error": "workflow_id is required"}

    if not comments:
        return {"error": "comments (rejection reason) is required"}

    # Get current workflow state
    workflow = session.execute(
        text("""
            SELECT id, dd_id, current_stage, status
            FROM dd_review_workflow
            WHERE id = :workflow_id
        """),
        {'workflow_id': workflow_id}
    ).fetchone()

    if not workflow:
        return {"error": "Workflow not found"}

    if workflow.status != 'in_progress':
        return {"error": f"Workflow is {workflow.status}, cannot reject"}

    # Record rejection
    approval_id = str(uuid.uuid4())
    session.execute(
        text("""
            INSERT INTO dd_workflow_approval
            (id, workflow_id, stage, approved_by, approved_at, status, comments)
            VALUES (:id, :workflow_id, :stage, :approved_by, :approved_at, :status, :comments)
        """),
        {
            'id': approval_id,
            'workflow_id': workflow_id,
            'stage': workflow.current_stage,
            'approved_by': user_id,
            'approved_at': datetime.utcnow(),
            'status': 'rejected',
            'comments': comments
        }
    )

    # Update workflow status
    session.execute(
        text("""
            UPDATE dd_review_workflow
            SET status = 'rejected'
            WHERE id = :workflow_id
        """),
        {'workflow_id': workflow_id}
    )

    log_audit_event(
        session=session,
        event_type=AuditEventType.WORKFLOW_REJECTED.value,
        entity_type='dd',
        entity_id=str(workflow.dd_id),
        user_id=user_id,
        dd_id=dd_id or str(workflow.dd_id),
        details={
            'workflow_id': workflow_id,
            'stage': workflow.current_stage,
            'reason': comments
        }
    )

    return {
        "success": True,
        "message": f"Stage '{workflow.current_stage}' rejected."
    }


def update_workflow(session, body: Dict) -> Dict:
    """
    Update workflow status or stage.

    Body:
        workflow_id: Workflow to update
        status: New status (optional)
        current_stage: New current stage (optional)
    """
    workflow_id = body.get('workflow_id')
    status = body.get('status')
    current_stage = body.get('current_stage')
    user_id = body.get('user_id')
    dd_id = body.get('dd_id')

    if not workflow_id:
        return {"error": "workflow_id is required"}

    updates = []
    params = {'workflow_id': workflow_id}

    if status:
        updates.append("status = :status")
        params['status'] = status
        if status == 'completed':
            updates.append("completed_at = :completed_at")
            params['completed_at'] = datetime.utcnow()

    if current_stage:
        updates.append("current_stage = :current_stage")
        params['current_stage'] = current_stage

    if not updates:
        return {"error": "No updates provided"}

    session.execute(
        text(f"UPDATE dd_review_workflow SET {', '.join(updates)} WHERE id = :workflow_id"),
        params
    )

    log_audit_event(
        session=session,
        event_type=AuditEventType.WORKFLOW_STAGE_COMPLETED.value,
        entity_type='workflow',
        entity_id=workflow_id,
        user_id=user_id,
        dd_id=dd_id,
        details={'status': status, 'current_stage': current_stage}
    )

    return {"success": True, "message": "Workflow updated"}


def get_workflow_status(session, dd_id: str, run_id: Optional[str] = None) -> Dict:
    """Get workflow status for a DD project."""
    query = """
        SELECT
            w.id,
            w.dd_id,
            w.run_id,
            w.workflow_type,
            w.current_stage,
            w.stages,
            w.status,
            w.created_by,
            w.created_at,
            w.completed_at,
            u.name as created_by_name
        FROM dd_review_workflow w
        LEFT JOIN users u ON w.created_by = u.id
        WHERE w.dd_id = :dd_id
    """
    params = {'dd_id': dd_id}

    if run_id:
        query += " AND w.run_id = :run_id"
        params['run_id'] = run_id

    query += " ORDER BY w.created_at DESC"

    result = session.execute(text(query), params)
    workflows = []

    for row in result.fetchall():
        # Get approvals for this workflow
        approvals = session.execute(
            text("""
                SELECT
                    a.id,
                    a.stage,
                    a.status,
                    a.approved_by,
                    a.approved_at,
                    a.comments,
                    u.name as approver_name
                FROM dd_workflow_approval a
                LEFT JOIN users u ON a.approved_by = u.id
                WHERE a.workflow_id = :workflow_id
                ORDER BY a.approved_at
            """),
            {'workflow_id': row.id}
        ).fetchall()

        stages = row.stages or []
        current_idx = stages.index(row.current_stage) if row.current_stage in stages else 0

        workflows.append({
            'id': str(row.id),
            'dd_id': str(row.dd_id),
            'run_id': str(row.run_id) if row.run_id else None,
            'workflow_type': row.workflow_type,
            'current_stage': row.current_stage,
            'stages': stages,
            'stage_progress': {
                'current': current_idx + 1,
                'total': len(stages)
            },
            'status': row.status,
            'created_by': {
                'id': str(row.created_by) if row.created_by else None,
                'name': row.created_by_name
            },
            'created_at': row.created_at.isoformat() if row.created_at else None,
            'completed_at': row.completed_at.isoformat() if row.completed_at else None,
            'approvals': [
                {
                    'id': str(a.id),
                    'stage': a.stage,
                    'status': a.status,
                    'approver': {
                        'id': str(a.approved_by) if a.approved_by else None,
                        'name': a.approver_name
                    },
                    'approved_at': a.approved_at.isoformat() if a.approved_at else None,
                    'comments': a.comments
                }
                for a in approvals
            ]
        })

    return {
        'dd_id': dd_id,
        'workflows': workflows,
        'active_workflow': workflows[0] if workflows and workflows[0]['status'] == 'in_progress' else None
    }


# ============================================================================
# User Functions
# ============================================================================

def get_users(session) -> Dict:
    """Get list of users for assignment dropdowns."""
    result = session.execute(
        text("""
            SELECT id, name, email, role, created_at
            FROM users
            ORDER BY name
        """)
    )

    users = [
        {
            'id': str(row.id),
            'name': row.name,
            'email': row.email,
            'role': row.role
        }
        for row in result.fetchall()
    ]

    return {'users': users}
