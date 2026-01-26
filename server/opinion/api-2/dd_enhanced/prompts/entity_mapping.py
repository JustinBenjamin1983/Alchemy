"""
Phase 6: Entity Mapping Prompts

Prompts for extracting and mapping entities from documents.
This pass runs after classification and before Pass 1 extraction.

Purpose:
- Identify all companies/entities mentioned in documents
- Map relationships between entities and the target
- Flag ambiguous entities for human confirmation
"""

from typing import Dict, List, Optional, Any


ENTITY_MAPPING_SYSTEM_PROMPT = """You are an entity identification specialist analyzing M&A documents.

Your task is to:
1. Extract all company/entity names from the document
2. Identify relationships between entities and the transaction target
3. Match entities to known entities from the transaction context
4. Flag entities with unclear relationships for human confirmation

CRITICAL - ONLY EXTRACT LEGAL ENTITIES:
- Companies, trusts, partnerships, and other legal entities
- Individual persons ONLY if they have a personal stake (e.g., individual shareholder, personal guarantor)
- DO NOT extract signatories, representatives, witnesses, or employees acting on behalf of companies
- If "John Smith, CEO" signs for "ABC Bank Ltd", extract "ABC Bank Ltd" NOT "John Smith"

RELATIONSHIP TYPES:
- target: The company being acquired/invested in
- parent: Parent/holding company of the target
- subsidiary: Subsidiary of the target
- related_party: Sister company, affiliate, or related party of target
- counterparty: Contract counterparty, customer, supplier, lender
- unknown: Relationship cannot be determined from document

CONFIDENCE LEVELS:
- 0.9-1.0: Entity explicitly identified (e.g., "ABC Pty Ltd, the Target")
- 0.7-0.89: Strong inference from context (e.g., defined party in contract)
- 0.5-0.69: Reasonable inference, some ambiguity
- 0.3-0.49: Weak inference, needs confirmation
- 0.0-0.29: Cannot determine relationship

Be precise with entity names - extract the full legal name when available."""


def build_entity_mapping_prompt(
    document_text: str,
    document_name: str,
    target_entity: Dict[str, Any],
    known_entities: List[Dict[str, Any]] = None,
    expected_counterparties: List[str] = None
) -> str:
    """
    Build prompt for entity extraction and mapping.

    Args:
        document_text: Text of the document to analyze
        document_name: Name of the document
        target_entity: Dict with target entity info (name, registration_number, etc.)
        known_entities: List of already-known entities from wizard or previous docs
        expected_counterparties: List of expected counterparty names

    Returns:
        Formatted prompt for Claude
    """
    target_name = target_entity.get("name", "Unknown Target")
    target_reg = target_entity.get("registration_number", "")

    # Build known entities section
    known_section = ""
    if known_entities:
        known_lines = ["Known entities from transaction context:"]
        for entity in known_entities[:20]:  # Limit to 20
            ent_name = entity.get("entity_name", entity.get("name", ""))
            ent_rel = entity.get("relationship_to_target", entity.get("relationship", ""))
            known_lines.append(f"  - {ent_name}: {ent_rel}")
        known_section = "\n".join(known_lines)

    # Build expected counterparties section
    counterparties_section = ""
    if expected_counterparties:
        counterparties_section = f"\nExpected counterparties: {', '.join(expected_counterparties[:10])}"

    return f"""Analyze this document and extract all entities mentioned.

TRANSACTION TARGET:
Name: {target_name}
Registration Number: {target_reg if target_reg else "Not provided"}

{known_section}
{counterparties_section}

---

DOCUMENT: {document_name}

{document_text[:50000]}

---

Extract all entities (companies, trusts, partnerships) and their relationships to the target.

IMPORTANT - DO NOT EXTRACT:
- Individual signatories/representatives who sign on behalf of a company (extract the company instead)
- Witnesses to signatures
- Notaries public
- Individual employees unless they have a personal stake (e.g., individual shareholder, director with personal guarantee)

For example, if "John Smith signs as CEO of ABC Bank", extract "ABC Bank" NOT "John Smith".

Return JSON:
{{
    "entities": [
        {{
            "entity_name": "Full legal name (e.g., 'ABC Mining (Pty) Ltd')",
            "registration_number": "Company registration number if found, otherwise null",
            "relationship_to_target": "target|parent|subsidiary|related_party|counterparty|unknown",
            "relationship_detail": "Specific description of relationship (e.g., '100% subsidiary', 'major customer', 'lender')",
            "confidence": 0.0-1.0,
            "evidence": "Quote or description supporting the relationship classification",
            "appears_in_role": "party|signatory|referenced|mentioned",
            "requires_confirmation": true/false
        }}
    ],
    "target_identified": true/false,
    "target_match_confidence": 0.0-1.0,
    "document_type_context": "What type of document this appears to be based on entity relationships",
    "flags": [
        {{
            "entity_name": "Name of entity with issue",
            "flag_reason": "Why this entity needs human confirmation",
            "possible_relationships": ["relationship1", "relationship2"]
        }}
    ]
}}

IMPORTANT:
- Mark requires_confirmation=true if confidence < 0.5 or relationship is unclear
- Always extract the full legal entity name, including Pty Ltd, (Pty) Ltd, Limited, etc.
- If an entity matches a known entity, use the exact name from known_entities
- Flag entities that appear in multiple roles or with conflicting relationships"""


def build_entity_aggregation_prompt(
    per_doc_results: List[Dict[str, Any]],
    target_entity: Dict[str, Any]
) -> str:
    """
    Build prompt to aggregate entity mapping across multiple documents.

    Args:
        per_doc_results: List of entity extraction results from each document
        target_entity: Dict with target entity info

    Returns:
        Formatted prompt for Claude
    """
    target_name = target_entity.get("name", "Unknown Target")

    # Compile all entities across documents
    all_entities = []
    for doc_result in per_doc_results:
        doc_name = doc_result.get("document_name", "Unknown")
        for entity in doc_result.get("entities", []):
            entity["source_document"] = doc_name
            all_entities.append(entity)

    entities_json = "\n".join([
        f"- {e.get('entity_name')}: {e.get('relationship_to_target')} "
        f"(confidence: {e.get('confidence', 0)}, from: {e.get('source_document', 'unknown')})"
        for e in all_entities[:100]  # Limit to 100 entities
    ])

    return f"""Aggregate and reconcile entity mappings across multiple documents.

TARGET ENTITY: {target_name}

ENTITIES EXTRACTED FROM ALL DOCUMENTS:
{entities_json}

---

Reconcile these entities into a unified entity map:
1. Merge duplicate entities (same company, different name formats)
2. Resolve conflicting relationship classifications
3. Calculate overall confidence based on multiple appearances
4. Flag entities that need human confirmation

Return JSON:
{{
    "entity_map": [
        {{
            "entity_name": "Canonical/standard name for this entity",
            "alternate_names": ["Other names used in documents"],
            "registration_number": "Registration number if found",
            "relationship_to_target": "target|parent|subsidiary|related_party|counterparty|unknown",
            "relationship_detail": "Consolidated description of relationship",
            "confidence": 0.0-1.0,
            "documents_appearing_in": ["doc1.pdf", "doc2.pdf"],
            "evidence": "Best evidence supporting the classification",
            "requires_human_confirmation": true/false,
            "confirmation_reason": "Why human needs to confirm (if applicable)"
        }}
    ],
    "checkpoint_recommended": true/false,
    "checkpoint_reason": "Why entity confirmation checkpoint should trigger",
    "summary": {{
        "total_unique_entities": 0,
        "entities_needing_confirmation": 0,
        "high_confidence_entities": 0,
        "target_subsidiaries": 0,
        "counterparties": 0
    }}
}}

FLAG FOR HUMAN CONFIRMATION IF:
- Same entity has different relationships in different documents
- Entity appears in >10 documents but relationship is unclear
- Entity is in a constitutional document but relationship unknown
- Confidence is below 0.5 for an entity in a critical document"""
