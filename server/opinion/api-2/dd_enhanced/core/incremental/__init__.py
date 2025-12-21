"""
Incremental processing module for DD analysis.

Provides change detection and result reuse to avoid
re-processing unchanged documents.
"""

from .change_detector import (
    ChangeType,
    DocumentChange,
    ChangeSet,
    ChangeDetector,
)

__all__ = [
    'ChangeType',
    'DocumentChange',
    'ChangeSet',
    'ChangeDetector',
]
