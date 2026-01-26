"""
Phase 6: Entity Mapping Core

Maps entities across documents to identify relationships with the target.
Runs after classification, before Pass 1 extraction.

Key Functions:
- map_entities_for_document: Extract entities from a single document
- aggregate_entity_map: Consolidate entities across all documents
- check_entity_checkpoint_trigger: Determine if human confirmation needed
- store_entity_map: Persist entity map to database
"""

from typing import List, Dict, Any, Optional
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


def map_entities_for_document(
    doc: Dict[str, Any],
    target_entity: Dict[str, Any],
    known_entities: List[Dict[str, Any]],
    client: Any,  # ClaudeClient
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Extract and map entities from a single document.

    Args:
        doc: Document dict with 'filename', 'text', 'doc_type'
        target_entity: Dict with target entity info
        known_entities: List of already-known entities
        client: Claude API client
        verbose: Print progress

    Returns:
        Dict with entities, flags, and metadata
    """
    from prompts.entity_mapping import (
        ENTITY_MAPPING_SYSTEM_PROMPT,
        build_entity_mapping_prompt
    )

    filename = doc.get("filename", "unknown")

    if verbose:
        logger.info(f"  Mapping entities in {filename}...")

    # Build prompt
    prompt = build_entity_mapping_prompt(
        document_text=doc.get("text", "")[:50000],
        document_name=filename,
        target_entity=target_entity,
        known_entities=known_entities,
        expected_counterparties=target_entity.get("expected_counterparties", [])
    )

    # Call Claude
    response = client.complete(
        prompt=prompt,
        system=ENTITY_MAPPING_SYSTEM_PROMPT,
        json_mode=True,
        max_tokens=4096,
        temperature=0.1
    )

    if "error" in response:
        logger.warning(f"Entity mapping failed for {filename}: {response.get('error')}")
        return {
            "document_name": filename,
            "entities": [],
            "flags": [],
            "error": response.get("error")
        }

    # Add document reference to each entity
    for entity in response.get("entities", []):
        entity["source_document"] = filename
        entity["source_doc_id"] = doc.get("id")

    return {
        "document_name": filename,
        "document_id": doc.get("id"),
        "entities": response.get("entities", []),
        "flags": response.get("flags", []),
        "target_identified": response.get("target_identified", False),
        "target_match_confidence": response.get("target_match_confidence", 0),
        "document_type_context": response.get("document_type_context", "")
    }


def aggregate_entity_map(
    per_doc_results: List[Dict[str, Any]],
    target_entity: Dict[str, Any],
    client: Any = None,  # Optional ClaudeClient for AI-assisted aggregation
    use_ai_aggregation: bool = False
) -> Dict[str, Any]:
    """
    Aggregate entity mapping across all documents.

    Args:
        per_doc_results: List of per-document entity mapping results
        target_entity: Dict with target entity info
        client: Optional Claude client for AI-assisted aggregation
        use_ai_aggregation: Whether to use AI for complex aggregation

    Returns:
        Aggregated entity map with consolidated entities
    """
    # Simple rule-based aggregation (default)
    entity_registry: Dict[str, Dict[str, Any]] = {}

    for doc_result in per_doc_results:
        doc_name = doc_result.get("document_name", "unknown")

        for entity in doc_result.get("entities", []):
            entity_name = entity.get("entity_name", "").strip()
            if not entity_name:
                continue

            # Normalize entity name for matching
            norm_name = _normalize_entity_name(entity_name)

            if norm_name in entity_registry:
                # Update existing entity
                existing = entity_registry[norm_name]
                _merge_entity_data(existing, entity, doc_name)
            else:
                # New entity
                entity_registry[norm_name] = {
                    "entity_name": entity_name,
                    "alternate_names": [],
                    "registration_number": entity.get("registration_number"),
                    "relationship_to_target": entity.get("relationship_to_target", "unknown"),
                    "relationship_detail": entity.get("relationship_detail", ""),
                    "confidence": entity.get("confidence", 0.5),
                    "documents_appearing_in": [doc_name],
                    "document_ids": [entity.get("source_doc_id")] if entity.get("source_doc_id") else [],
                    "evidence": entity.get("evidence", ""),
                    "requires_human_confirmation": entity.get("requires_confirmation", False),
                    "appearances": 1,
                    "relationship_votes": {entity.get("relationship_to_target", "unknown"): 1}
                }

    # Convert registry to list and finalize
    entity_map = []
    for norm_name, entity_data in entity_registry.items():
        # Calculate final relationship based on votes
        votes = entity_data.pop("relationship_votes", {})
        if votes:
            entity_data["relationship_to_target"] = max(votes, key=votes.get)

        # Determine if confirmation needed
        entity_data["requires_human_confirmation"] = _needs_confirmation(entity_data, votes)

        if entity_data["requires_human_confirmation"]:
            entity_data["confirmation_reason"] = _get_confirmation_reason(entity_data, votes)

        entity_map.append(entity_data)

    # Sort by confidence descending
    entity_map.sort(key=lambda x: x.get("confidence", 0), reverse=True)

    # Calculate summary
    summary = {
        "total_unique_entities": len(entity_map),
        "entities_needing_confirmation": sum(1 for e in entity_map if e.get("requires_human_confirmation")),
        "high_confidence_entities": sum(1 for e in entity_map if e.get("confidence", 0) >= 0.7),
        "target_subsidiaries": sum(1 for e in entity_map if e.get("relationship_to_target") == "subsidiary"),
        "counterparties": sum(1 for e in entity_map if e.get("relationship_to_target") == "counterparty"),
        "unknown_relationships": sum(1 for e in entity_map if e.get("relationship_to_target") == "unknown"),
    }

    # Determine if checkpoint should be triggered
    checkpoint_recommended = check_entity_checkpoint_trigger(entity_map)

    return {
        "entity_map": entity_map,
        "checkpoint_recommended": checkpoint_recommended,
        "checkpoint_reason": _get_checkpoint_reason(entity_map, summary) if checkpoint_recommended else None,
        "summary": summary
    }


def check_entity_checkpoint_trigger(entity_map: List[Dict[str, Any]]) -> bool:
    """
    Determine if entity confirmation checkpoint should be triggered.

    Triggers if:
    - >3 documents have entities with unknown relationships
    - Constitutional document has unrecognized entity in key role
    - Entity appears in >10 docs but relationship unclear
    - Multiple entities have conflicting classifications

    Args:
        entity_map: Aggregated entity map

    Returns:
        True if checkpoint should be triggered
    """
    # Count entities needing confirmation
    needs_confirmation = sum(
        1 for e in entity_map if e.get("requires_human_confirmation")
    )

    if needs_confirmation >= 3:
        return True

    # Check for high-frequency unknown entities
    for entity in entity_map:
        appearances = entity.get("appearances", 1)
        relationship = entity.get("relationship_to_target", "unknown")
        confidence = entity.get("confidence", 0)

        if appearances >= 5 and relationship == "unknown":
            return True

        if appearances >= 10 and confidence < 0.5:
            return True

    # Check for critical entities with low confidence
    for entity in entity_map:
        relationship = entity.get("relationship_to_target", "")
        confidence = entity.get("confidence", 0)

        # Target or parent should be high confidence
        if relationship in ["target", "parent"] and confidence < 0.7:
            return True

    return False


def _normalize_entity_name(name: str) -> str:
    """Normalize entity name for matching."""
    normalized = name.lower().strip()

    # Remove common suffixes for matching
    suffixes = [
        "(pty) ltd", "pty ltd", "(proprietary) limited",
        "proprietary limited", "limited", "ltd",
        "inc", "incorporated", "corp", "corporation",
        "llc", "l.l.c.", "plc", "p.l.c."
    ]

    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)].strip()

    # Remove punctuation
    normalized = normalized.replace(".", "").replace(",", "").replace("'", "")

    return normalized


def _merge_entity_data(existing: Dict, new_entity: Dict, doc_name: str) -> None:
    """Merge new entity data into existing entity record."""
    # Add to documents list
    if doc_name not in existing["documents_appearing_in"]:
        existing["documents_appearing_in"].append(doc_name)

    # Add document ID
    if new_entity.get("source_doc_id"):
        if "document_ids" not in existing:
            existing["document_ids"] = []
        if new_entity["source_doc_id"] not in existing["document_ids"]:
            existing["document_ids"].append(new_entity["source_doc_id"])

    # Track alternate names
    new_name = new_entity.get("entity_name", "")
    if new_name and new_name != existing["entity_name"]:
        if new_name not in existing["alternate_names"]:
            existing["alternate_names"].append(new_name)

    # Update registration number if found
    if new_entity.get("registration_number") and not existing.get("registration_number"):
        existing["registration_number"] = new_entity["registration_number"]

    # Vote on relationship
    new_relationship = new_entity.get("relationship_to_target", "unknown")
    if "relationship_votes" not in existing:
        existing["relationship_votes"] = {}
    existing["relationship_votes"][new_relationship] = (
        existing["relationship_votes"].get(new_relationship, 0) + 1
    )

    # Update confidence (average)
    existing["appearances"] = existing.get("appearances", 1) + 1
    old_conf = existing.get("confidence", 0.5)
    new_conf = new_entity.get("confidence", 0.5)
    existing["confidence"] = (old_conf + new_conf) / 2

    # Append evidence if different
    new_evidence = new_entity.get("evidence", "")
    if new_evidence and new_evidence not in existing.get("evidence", ""):
        existing["evidence"] = f"{existing.get('evidence', '')}; {new_evidence}"[:1000]

    # If any instance needs confirmation, the entity needs confirmation
    if new_entity.get("requires_confirmation"):
        existing["requires_human_confirmation"] = True


def _needs_confirmation(entity_data: Dict, votes: Dict) -> bool:
    """Determine if entity needs human confirmation."""
    # Low confidence
    if entity_data.get("confidence", 0) < 0.5:
        return True

    # Unknown relationship
    if entity_data.get("relationship_to_target") == "unknown":
        return True

    # Conflicting votes
    if len(votes) > 1:
        # Check if votes are close
        vote_values = list(votes.values())
        if max(vote_values) - min(vote_values) <= 1 and len(votes) >= 2:
            return True

    # High frequency but still uncertain
    if entity_data.get("appearances", 1) >= 5 and entity_data.get("confidence", 0) < 0.7:
        return True

    return entity_data.get("requires_human_confirmation", False)


def _get_confirmation_reason(entity_data: Dict, votes: Dict) -> str:
    """Get reason why entity needs confirmation."""
    reasons = []

    if entity_data.get("confidence", 0) < 0.5:
        reasons.append("low confidence")

    if entity_data.get("relationship_to_target") == "unknown":
        reasons.append("relationship unknown")

    if len(votes) > 1:
        rel_list = [f"{r} ({c})" for r, c in votes.items()]
        reasons.append(f"conflicting classifications: {', '.join(rel_list)}")

    if entity_data.get("appearances", 1) >= 5 and entity_data.get("confidence", 0) < 0.7:
        reasons.append(f"appears in {entity_data['appearances']} documents but uncertain")

    return "; ".join(reasons) if reasons else "confirmation requested"


def _get_checkpoint_reason(entity_map: List[Dict], summary: Dict) -> str:
    """Get reason why entity checkpoint was triggered."""
    reasons = []

    needs_conf = summary.get("entities_needing_confirmation", 0)
    if needs_conf >= 3:
        reasons.append(f"{needs_conf} entities need confirmation")

    unknown = summary.get("unknown_relationships", 0)
    if unknown >= 3:
        reasons.append(f"{unknown} entities have unknown relationships")

    # Find high-frequency uncertain entities
    for entity in entity_map:
        if entity.get("appearances", 1) >= 5 and entity.get("relationship_to_target") == "unknown":
            reasons.append(f"'{entity['entity_name']}' appears frequently but relationship unclear")
            break

    return "; ".join(reasons) if reasons else "Entity confirmation recommended"


def store_entity_map(
    dd_id: str,
    run_id: Optional[str],
    entity_map: List[Dict[str, Any]],
    session: Any  # SQLAlchemy session
) -> Dict[str, Any]:
    """
    Store entity map to database.

    Clears existing entities for this DD before storing new ones to prevent duplicates.

    Args:
        dd_id: Due diligence ID
        run_id: Analysis run ID (optional)
        entity_map: List of entity dicts
        session: Database session

    Returns:
        Dict with stored count and any errors
    """
    from shared.models import DDEntityMap

    stored_count = 0
    errors = []

    dd_uuid = uuid.UUID(dd_id) if isinstance(dd_id, str) else dd_id
    run_uuid = uuid.UUID(run_id) if run_id and isinstance(run_id, str) else run_id

    # Clear existing entities for this DD to prevent duplicates on re-run
    try:
        deleted_count = session.query(DDEntityMap).filter(
            DDEntityMap.dd_id == dd_uuid
        ).delete()
        logger.info(f"Cleared {deleted_count} existing entities for DD {dd_id}")
    except Exception as e:
        logger.warning(f"Failed to clear existing entities: {e}")
        errors.append(f"Failed to clear existing entities: {str(e)}")

    for entity in entity_map:
        try:
            db_entity = DDEntityMap(
                id=uuid.uuid4(),
                dd_id=dd_uuid,
                run_id=run_uuid,
                entity_name=entity.get("entity_name", "")[:500],
                registration_number=entity.get("registration_number"),
                relationship_to_target=entity.get("relationship_to_target", "unknown"),
                relationship_detail=entity.get("relationship_detail", "")[:2000] if entity.get("relationship_detail") else None,
                confidence=entity.get("confidence", 0.5),
                documents_appearing_in=entity.get("document_ids", []),
                evidence=entity.get("evidence", "")[:2000] if entity.get("evidence") else None,
                requires_human_confirmation=entity.get("requires_human_confirmation", False),
                human_confirmed=False,
                human_confirmation_value=None,
                created_at=datetime.utcnow()
            )
            session.add(db_entity)
            stored_count += 1

        except Exception as e:
            errors.append(f"Failed to store entity '{entity.get('entity_name')}': {str(e)}")
            logger.warning(f"Entity storage error: {e}")

    try:
        session.commit()
    except Exception as e:
        session.rollback()
        errors.append(f"Commit failed: {str(e)}")
        logger.error(f"Entity map commit failed: {e}")

    return {
        "stored_count": stored_count,
        "errors": errors
    }


def get_entity_map_for_dd(dd_id: str, session: Any) -> List[Dict[str, Any]]:
    """
    Retrieve entity map for a DD project.

    Args:
        dd_id: Due diligence ID
        session: Database session

    Returns:
        List of entity dicts
    """
    from shared.models import DDEntityMap

    dd_uuid = uuid.UUID(dd_id) if isinstance(dd_id, str) else dd_id

    entities = session.query(DDEntityMap).filter(
        DDEntityMap.dd_id == dd_uuid
    ).order_by(DDEntityMap.confidence.desc()).all()

    return [
        {
            "id": str(entity.id),
            "entity_name": entity.entity_name,
            "registration_number": entity.registration_number,
            "relationship_to_target": entity.relationship_to_target,
            "relationship_detail": entity.relationship_detail,
            "confidence": entity.confidence,
            "documents_appearing_in": entity.documents_appearing_in,
            "evidence": entity.evidence,
            "requires_human_confirmation": entity.requires_human_confirmation,
            "human_confirmed": entity.human_confirmed,
            "human_confirmation_value": entity.human_confirmation_value,
        }
        for entity in entities
    ]
