"""
Document Selector Utility

Provides smart document selection for DD processing pipeline.
Ensures only the "best version" of each document is processed:
- If original has a successful conversion → use converted PDF
- If no conversion exists → use original
- Never process both original AND its converted version

This prevents duplicate processing and ensures findings link correctly.
"""

import logging
from typing import List, Dict, Set
from sqlalchemy.orm import Session
from shared.models import Document


def get_processable_documents(session: Session, folder_ids: List[str]) -> List[Document]:
    """
    Get the best version of each document for processing.

    Logic:
    1. For documents with successful conversion (converted_doc_id set):
       → Return the converted PDF (found via converted_from_id)
    2. For documents without conversion:
       → Return the original document
    3. Never return both original AND its converted version

    Args:
        session: SQLAlchemy session
        folder_ids: List of folder UUIDs to get documents from

    Returns:
        List of Document objects to process (deduplicated, best versions)
    """
    # Get all documents in the specified folders
    all_docs = session.query(Document).filter(
        Document.folder_id.in_(folder_ids)
    ).all()

    # Build lookup structures
    docs_by_id: Dict[str, Document] = {str(doc.id): doc for doc in all_docs}
    originals_with_conversion: Set[str] = set()  # Original doc IDs that have conversions
    converted_docs: List[Document] = []  # Converted PDFs to include

    # First pass: identify converted documents and their originals
    for doc in all_docs:
        if doc.converted_from_id:
            # This IS a converted document - mark its original as "handled"
            originals_with_conversion.add(str(doc.converted_from_id))
            converted_docs.append(doc)

    # Second pass: collect processable documents
    processable: List[Document] = []
    seen_originals: Set[str] = set()

    # Add converted documents (prefer these over originals)
    for doc in converted_docs:
        original_id = str(doc.converted_from_id)
        if original_id not in seen_originals:
            processable.append(doc)
            seen_originals.add(original_id)

    # Add originals that don't have conversions
    for doc in all_docs:
        doc_id = str(doc.id)

        # Skip if this is a converted doc (already added above)
        if doc.converted_from_id:
            continue

        # Skip if this original has a conversion (converted version added above)
        if doc_id in originals_with_conversion:
            continue

        # Skip ZIP files and other non-processable originals
        if doc.is_original and doc.type in ('zip', 'rar', '7z'):
            continue

        # Add this document (original without conversion)
        if doc_id not in seen_originals:
            processable.append(doc)
            seen_originals.add(doc_id)

    logging.info(
        f"Document selection: {len(all_docs)} total → {len(processable)} processable "
        f"({len(converted_docs)} converted, {len(originals_with_conversion)} originals replaced)"
    )

    return processable


def get_original_document_id(doc: Document) -> str:
    """
    Get the original document ID for linking findings.

    If the document is a converted version, returns the ID of the original.
    Otherwise returns the document's own ID.

    This ensures findings are always linked to the user's uploaded file,
    not the converted version.

    Args:
        doc: Document object (may be original or converted)

    Returns:
        UUID string of the original document
    """
    if doc.converted_from_id:
        return str(doc.converted_from_id)
    return str(doc.id)


def get_processable_document_count(session: Session, dd_id: str) -> int:
    """
    Get count of processable documents for a DD (for progress display).

    Args:
        session: SQLAlchemy session
        dd_id: Due diligence UUID

    Returns:
        Count of documents that will actually be processed
    """
    from shared.models import Folder

    # Get all folders for this DD
    folders = session.query(Folder).filter(Folder.dd_id == dd_id).all()
    folder_ids = [str(f.id) for f in folders]

    if not folder_ids:
        return 0

    # Use the same logic as get_processable_documents
    processable = get_processable_documents(session, folder_ids)
    return len(processable)
