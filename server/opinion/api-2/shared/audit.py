"""
Audit logging system for compliance and traceability.
Logs all user actions, system events, and data access.

Phase 7: Enterprise Features
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import json
import logging
import uuid

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Standard audit event types."""
    # Document events
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_CLASSIFIED = "document_classified"
    DOCUMENT_MOVED = "document_moved"
    DOCUMENT_DELETED = "document_deleted"
    DOCUMENT_VIEWED = "document_viewed"

    # Analysis events
    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_COMPLETED = "analysis_completed"
    ANALYSIS_FAILED = "analysis_failed"

    # Finding events
    FINDING_CREATED = "finding_created"
    FINDING_UPDATED = "finding_updated"
    FINDING_ASSIGNED = "finding_assigned"
    FINDING_APPROVED = "finding_approved"
    FINDING_REJECTED = "finding_rejected"
    FINDING_ESCALATED = "finding_escalated"

    # Comment events
    COMMENT_ADDED = "comment_added"
    COMMENT_EDITED = "comment_edited"
    COMMENT_DELETED = "comment_deleted"

    # Workflow events
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_STAGE_COMPLETED = "workflow_stage_completed"
    WORKFLOW_APPROVED = "workflow_approved"
    WORKFLOW_REJECTED = "workflow_rejected"

    # Report events
    REPORT_GENERATED = "report_generated"
    REPORT_EXPORTED = "report_exported"
    REPORT_DOWNLOADED = "report_downloaded"
    REPORT_SHARED = "report_shared"

    # Access events
    DD_ACCESSED = "dd_accessed"
    DD_CREATED = "dd_created"
    DD_DELETED = "dd_deleted"
    GRAPH_QUERIED = "graph_queried"

    # System events
    SYSTEM_ERROR = "system_error"
    RATE_LIMIT_HIT = "rate_limit_hit"


def log_audit_event(
    session,
    event_type: str,
    entity_type: str,
    entity_id: str,
    user_id: Optional[str] = None,
    dd_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> Optional[str]:
    """
    Log an audit event to the database.

    Args:
        session: SQLAlchemy database session
        event_type: Type of event (from AuditEventType or string)
        entity_type: Type of entity affected (dd, document, finding, report)
        entity_id: ID of the affected entity
        user_id: ID of user who triggered the event (null for system events)
        dd_id: Optional DD project ID for filtering
        details: Additional event details (JSON)
        ip_address: Client IP address
        user_agent: Client user agent string

    Returns:
        Audit event ID if successful, None otherwise
    """
    from sqlalchemy import text

    try:
        audit_id = str(uuid.uuid4())

        # Handle enum values
        if isinstance(event_type, AuditEventType):
            event_type = event_type.value

        # Serialize details to JSON
        details_json = json.dumps(details) if details else None

        session.execute(
            text("""
                INSERT INTO dd_audit_log
                (id, event_type, user_id, entity_type, entity_id, dd_id, details,
                 ip_address, user_agent, created_at)
                VALUES (:id, :event_type, :user_id, :entity_type, :entity_id, :dd_id,
                        :details::jsonb, :ip_address, :user_agent, :created_at)
            """),
            {
                'id': audit_id,
                'event_type': event_type,
                'user_id': user_id,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'dd_id': dd_id,
                'details': details_json,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'created_at': datetime.utcnow()
            }
        )

        return audit_id

    except Exception as e:
        # Don't fail the main operation if audit logging fails
        logger.error(f"Failed to log audit event: {e}")
        return None


def log_audit_event_safe(
    event_type: str,
    entity_type: str,
    entity_id: str,
    user_id: Optional[str] = None,
    dd_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> Optional[str]:
    """
    Log an audit event using a fresh session (safe for use outside transactions).

    Args:
        Same as log_audit_event
    """
    from shared.session import transactional_session

    try:
        with transactional_session() as session:
            audit_id = log_audit_event(
                session=session,
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user_id,
                dd_id=dd_id,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent
            )
            session.commit()
            return audit_id
    except Exception as e:
        logger.error(f"Failed to log audit event (safe): {e}")
        return None


def get_audit_trail(
    session,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    dd_id: Optional[str] = None,
    user_id: Optional[str] = None,
    event_types: Optional[List[str]] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict]:
    """
    Query audit trail with filters.

    Args:
        session: Database session
        entity_type: Filter by entity type
        entity_id: Filter by specific entity
        dd_id: Filter by DD project
        user_id: Filter by user
        event_types: Filter by event types (list)
        start_date: Start of date range
        end_date: End of date range
        limit: Max results (default 100)
        offset: Skip results for pagination
    """
    from sqlalchemy import text

    query = """
        SELECT
            a.id,
            a.event_type,
            a.user_id,
            a.entity_type,
            a.entity_id,
            a.dd_id,
            a.details,
            a.ip_address,
            a.created_at,
            u.name as user_name,
            u.email as user_email
        FROM dd_audit_log a
        LEFT JOIN users u ON a.user_id = u.id
        WHERE 1=1
    """
    params = {}

    if entity_type:
        query += " AND a.entity_type = :entity_type"
        params['entity_type'] = entity_type

    if entity_id:
        query += " AND a.entity_id = :entity_id"
        params['entity_id'] = entity_id

    if dd_id:
        query += " AND a.dd_id = :dd_id"
        params['dd_id'] = dd_id

    if user_id:
        query += " AND a.user_id = :user_id"
        params['user_id'] = user_id

    if event_types:
        query += " AND a.event_type = ANY(:event_types)"
        params['event_types'] = event_types

    if start_date:
        query += " AND a.created_at >= :start_date"
        params['start_date'] = start_date

    if end_date:
        query += " AND a.created_at <= :end_date"
        params['end_date'] = end_date

    query += " ORDER BY a.created_at DESC LIMIT :limit OFFSET :offset"
    params['limit'] = limit
    params['offset'] = offset

    result = session.execute(text(query), params)
    rows = result.fetchall()

    return [
        {
            'id': str(row.id),
            'event_type': row.event_type,
            'user_id': str(row.user_id) if row.user_id else None,
            'entity_type': row.entity_type,
            'entity_id': str(row.entity_id),
            'dd_id': str(row.dd_id) if row.dd_id else None,
            'details': row.details,
            'ip_address': row.ip_address,
            'created_at': row.created_at.isoformat() if row.created_at else None,
            'user_name': row.user_name,
            'user_email': row.user_email
        }
        for row in rows
    ]


def get_audit_summary(session, dd_id: str) -> Dict[str, Any]:
    """
    Get audit summary for a DD project.

    Returns event counts, unique users, and activity timeline.
    """
    from sqlalchemy import text

    # Get event counts by type
    event_counts_result = session.execute(
        text("""
            SELECT event_type, COUNT(*) as count
            FROM dd_audit_log
            WHERE dd_id = :dd_id
            GROUP BY event_type
            ORDER BY count DESC
        """),
        {'dd_id': dd_id}
    )
    event_counts = {row.event_type: row.count for row in event_counts_result.fetchall()}

    # Get unique users
    unique_users_result = session.execute(
        text("""
            SELECT DISTINCT a.user_id, u.name, u.email
            FROM dd_audit_log a
            JOIN users u ON a.user_id = u.id
            WHERE a.dd_id = :dd_id
            AND a.user_id IS NOT NULL
        """),
        {'dd_id': dd_id}
    )
    unique_users = [
        {'user_id': str(row.user_id), 'name': row.name, 'email': row.email}
        for row in unique_users_result.fetchall()
    ]

    # Get timeline (events per day for last 30 days)
    timeline_result = session.execute(
        text("""
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM dd_audit_log
            WHERE dd_id = :dd_id
            AND created_at >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(created_at)
            ORDER BY date
        """),
        {'dd_id': dd_id}
    )
    timeline = [
        {'date': row.date.isoformat() if row.date else None, 'count': row.count}
        for row in timeline_result.fetchall()
    ]

    # Get total count
    total_result = session.execute(
        text("SELECT COUNT(*) as total FROM dd_audit_log WHERE dd_id = :dd_id"),
        {'dd_id': dd_id}
    )
    total_events = total_result.fetchone().total

    return {
        'dd_id': dd_id,
        'event_counts': event_counts,
        'unique_users': unique_users,
        'timeline': timeline,
        'total_events': total_events
    }


def get_entity_audit_trail(session, entity_type: str, entity_id: str, limit: int = 50) -> List[Dict]:
    """
    Get audit trail for a specific entity (document, finding, etc.).
    """
    return get_audit_trail(
        session=session,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit
    )


# Notification placeholder (stub for Q6)
def notify_user(user_id: str, notification_type: str, entity_id: str, details: Dict = None):
    """
    Placeholder for user notifications.

    In production, this would integrate with email/Slack.
    Currently just logs the notification.
    """
    logger.info(
        f"[NOTIFICATION STUB] User: {user_id}, Type: {notification_type}, "
        f"Entity: {entity_id}, Details: {details}"
    )
