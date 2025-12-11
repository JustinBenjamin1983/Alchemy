"""
Document Registry Module

Provides document expectations, folder structures, and auto-classification
capabilities for due diligence data rooms.

This module supplements the DD blueprints by defining:
- Expected documents for each transaction type
- Standard folder hierarchies
- Auto-classification patterns for uploaded documents
- Missing document detection
"""

from .registry import (
    DocumentPriority,
    ExpectedDocument,
    DocumentFolder,
    load_document_registry,
    list_available_registries,
    classify_document,
    get_missing_documents,
    generate_document_request_list,
)

__all__ = [
    "DocumentPriority",
    "ExpectedDocument",
    "DocumentFolder",
    "load_document_registry",
    "list_available_registries",
    "classify_document",
    "get_missing_documents",
    "generate_document_request_list",
]
