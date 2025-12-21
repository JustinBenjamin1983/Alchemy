"""
Relationship Enricher for Knowledge Graph (Phase 5)

Performs lightweight Claude calls to extract relationship data
that Pass 1 doesn't capture:
- Cross-document references
- Assignment restrictions
- Security relationships
- Governing law

This is designed to be ~80% cheaper than full entity extraction
by using a focused prompt and Haiku model.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import json
import time

logger = logging.getLogger(__name__)

# Configuration
MAX_WORKERS = 5
RETRY_DELAY = 2
MAX_RETRIES = 2
INPUT_CHAR_LIMIT = 15000  # Smaller than entity extraction - focused prompt


@dataclass
class RelationshipEnrichment:
    """Additional relationship data extracted for a document."""
    document_id: str
    document_name: str

    # Cross-references to other documents
    cross_references: List[Dict[str, str]] = field(default_factory=list)
    # Each: {reference_text, likely_document_type, reference_type}

    # Agreement-level details
    governing_law: Optional[str] = None
    has_assignment_restriction: bool = False
    assignment_restriction_details: Optional[str] = None

    # Security relationships (for security documents)
    secures_obligation: Optional[str] = None  # Description of secured obligation
    security_type: Optional[str] = None  # mortgage, pledge, cession, guarantee

    # Additional triggers not captured in CoC
    additional_triggers: List[Dict[str, str]] = field(default_factory=list)
    # Each: {trigger_type, description, clause_reference}

    # Extraction error
    error: Optional[str] = None


RELATIONSHIP_EXTRACTION_PROMPT = """Analyse this document for RELATIONSHIPS and CROSS-REFERENCES only.

DOCUMENT: {document_name}
DOCUMENT TYPE: {document_type}

TEXT (first {char_limit} chars):
{document_text}

Extract ONLY the following in JSON format:

{{
    "cross_references": [
        {{
            "reference_text": "<exact text mentioning another document>",
            "likely_document_type": "<e.g., 'Shareholders Agreement', 'Loan Agreement'>",
            "reference_type": "<incorporates|amends|supplements|replaces|refers_to>"
        }}
    ],
    "governing_law": "<jurisdiction, e.g., 'South Africa', 'England and Wales'>",
    "has_assignment_restriction": <true|false>,
    "assignment_restriction_details": "<if true, describe the restriction>",
    "secures_obligation": "<if this is a security document, what does it secure?>",
    "security_type": "<mortgage|pledge|cession|guarantee|surety|null>",
    "additional_triggers": [
        {{
            "trigger_type": "<default|breach|insolvency|material_adverse_change|termination>",
            "description": "<what constitutes this trigger>",
            "clause_reference": "<clause number>"
        }}
    ]
}}

RULES:
1. For cross_references: Look for phrases like "as defined in the X Agreement", "pursuant to the Y", "in terms of the Z"
2. Only include ACTUAL references to other documents, not general terms
3. For additional_triggers: Do NOT include change of control (already extracted elsewhere)
4. Keep responses concise - this is for relationship mapping, not full extraction

Return valid JSON only.
"""


class RelationshipEnricher:
    """
    Enriches entity data with relationship information.

    Uses lightweight Claude calls to extract:
    - Cross-document references
    - Assignment restrictions
    - Security relationships
    - Governing law
    - Additional triggers (not CoC)
    """

    def __init__(self, claude_client):
        self.client = claude_client

    def enrich_document(
        self,
        document: Dict[str, Any]
    ) -> RelationshipEnrichment:
        """
        Extract relationship data from a single document.

        Args:
            document: Document dict with id, original_file_name, extracted_text

        Returns:
            RelationshipEnrichment with extracted relationships
        """
        doc_id = str(document.get('id', ''))
        doc_name = document.get('original_file_name', document.get('filename', 'Unknown'))
        doc_type = document.get('ai_document_type', document.get('doc_type', ''))
        doc_text = document.get('extracted_text', document.get('text', ''))

        prompt = RELATIONSHIP_EXTRACTION_PROMPT.format(
            document_name=doc_name,
            document_type=doc_type,
            char_limit=INPUT_CHAR_LIMIT,
            document_text=doc_text[:INPUT_CHAR_LIMIT]
        )

        system_prompt = """You are a legal document analyst extracting cross-references and relationships.
Output valid JSON only. Be precise and concise."""

        try:
            # Use Haiku for cost efficiency
            response = self.client.complete_extraction(
                prompt=prompt,
                system=system_prompt,
                max_tokens=1500  # Smaller than full extraction
            )

            if "error" in response:
                return RelationshipEnrichment(
                    document_id=doc_id,
                    document_name=doc_name,
                    error=response.get('error')
                )

            # Parse response
            return self._parse_response(response, doc_id, doc_name)

        except Exception as e:
            logger.warning(f"Relationship enrichment failed for {doc_name}: {e}")
            return RelationshipEnrichment(
                document_id=doc_id,
                document_name=doc_name,
                error=str(e)
            )

    def _parse_response(
        self,
        response: Any,
        doc_id: str,
        doc_name: str
    ) -> RelationshipEnrichment:
        """Parse the Claude response into RelationshipEnrichment."""
        # Handle if response is already parsed dict
        if isinstance(response, dict):
            data = response
        else:
            # Try to parse as JSON
            try:
                text = str(response)
                if '```json' in text:
                    text = text.split('```json')[1].split('```')[0]
                elif '```' in text:
                    text = text.split('```')[1].split('```')[0]
                data = json.loads(text.strip())
            except json.JSONDecodeError:
                return RelationshipEnrichment(
                    document_id=doc_id,
                    document_name=doc_name,
                    error="Failed to parse JSON response"
                )

        return RelationshipEnrichment(
            document_id=doc_id,
            document_name=doc_name,
            cross_references=data.get('cross_references', []),
            governing_law=data.get('governing_law'),
            has_assignment_restriction=data.get('has_assignment_restriction', False),
            assignment_restriction_details=data.get('assignment_restriction_details'),
            secures_obligation=data.get('secures_obligation'),
            security_type=data.get('security_type'),
            additional_triggers=data.get('additional_triggers', [])
        )

    def enrich_all_documents(
        self,
        documents: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None,
        max_workers: int = MAX_WORKERS
    ) -> List[RelationshipEnrichment]:
        """
        Enrich all documents with relationship data in parallel.

        Args:
            documents: List of document dicts
            progress_callback: Optional callback(current, total, message)
            max_workers: Number of parallel workers

        Returns:
            List of RelationshipEnrichment for all documents
        """
        total = len(documents)
        results: List[RelationshipEnrichment] = []
        completed = 0

        logger.info(f"Enriching relationships for {total} documents with {max_workers} workers")

        def enrich_one(doc: Dict[str, Any]) -> RelationshipEnrichment:
            return self._enrich_with_retry(doc)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_doc = {
                executor.submit(enrich_one, doc): doc
                for doc in documents
            }

            for future in as_completed(future_to_doc):
                doc = future_to_doc[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Enrichment failed for {doc.get('original_file_name')}: {e}")
                    results.append(RelationshipEnrichment(
                        document_id=str(doc.get('id', '')),
                        document_name=doc.get('original_file_name', 'Unknown'),
                        error=str(e)
                    ))

                completed += 1
                if progress_callback:
                    progress_callback(
                        completed,
                        total,
                        f"Enriched: {doc.get('original_file_name', 'Unknown')}"
                    )

        # Sort by document order (as_completed returns in completion order)
        doc_id_order = {str(doc.get('id', '')): i for i, doc in enumerate(documents)}
        results.sort(key=lambda r: doc_id_order.get(r.document_id, 999))

        # Log summary
        errors = [r for r in results if r.error]
        refs_found = sum(len(r.cross_references) for r in results)
        logger.info(f"Enrichment complete: {refs_found} cross-references found, {len(errors)} errors")

        return results

    def _enrich_with_retry(
        self,
        document: Dict[str, Any],
        max_retries: int = MAX_RETRIES
    ) -> RelationshipEnrichment:
        """Enrich with retry logic for rate limits."""
        last_error = None

        for attempt in range(max_retries):
            try:
                return self.enrich_document(document)
            except Exception as e:
                last_error = str(e)
                if 'rate' in last_error.lower() or '429' in last_error:
                    wait_time = RETRY_DELAY * (attempt + 1)
                    logger.warning(f"Rate limit hit, waiting {wait_time}s before retry")
                    time.sleep(wait_time)
                else:
                    break

        return RelationshipEnrichment(
            document_id=str(document.get('id', '')),
            document_name=document.get('original_file_name', 'Unknown'),
            error=last_error or 'Unknown error'
        )


def merge_enrichments(
    document_entities: 'DocumentEntities',
    enrichment: RelationshipEnrichment
) -> 'DocumentEntities':
    """
    Merge relationship enrichment data into document entities.

    Args:
        document_entities: Existing entities from Pass 1 transformation
        enrichment: Relationship enrichment from Claude call

    Returns:
        Updated DocumentEntities with enrichment data merged
    """
    from .entity_transformer import TriggerEntity

    # Add cross-references
    document_entities.cross_references = [
        ref.get('reference_text', '') for ref in enrichment.cross_references
    ]

    # Update agreement with enrichment data
    if document_entities.agreements:
        agreement = document_entities.agreements[0]
        if enrichment.governing_law:
            agreement.governing_law = enrichment.governing_law
        if enrichment.has_assignment_restriction:
            agreement.has_assignment_restriction = True

    # Add additional triggers
    for trigger_data in enrichment.additional_triggers:
        document_entities.triggers.append(TriggerEntity(
            source_document_id=document_entities.document_id,
            source_document_name=document_entities.document_name,
            trigger_type=trigger_data.get('trigger_type', 'other'),
            description=trigger_data.get('description', ''),
            clause_reference=trigger_data.get('clause_reference')
        ))

    return document_entities
