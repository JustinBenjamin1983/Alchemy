"""
Change detection for incremental document processing.

Detects new, modified, and deleted documents to avoid full re-processing.
Change detection is based on:
- Document content hash (extracted_text)
- Folder category changes
- AI classification changes

This approach catches both content changes AND changes that affect
which questions are asked during analysis.
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
import logging

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    NEW = "new"
    MODIFIED = "modified"
    DELETED = "deleted"
    UNCHANGED = "unchanged"


@dataclass
class DocumentChange:
    """Represents a change to a single document."""
    document_id: str
    document_name: str
    change_type: ChangeType
    previous_hash: Optional[str] = None
    current_hash: Optional[str] = None
    content_changed: bool = False
    folder_changed: bool = False
    classification_changed: bool = False
    change_details: Optional[str] = None

    @property
    def requires_reprocessing(self) -> bool:
        """Whether this document needs to be re-processed."""
        return self.change_type in [ChangeType.NEW, ChangeType.MODIFIED]


@dataclass
class ChangeSet:
    """Set of changes detected between runs."""
    dd_id: str
    run_id: str
    previous_run_id: Optional[str]
    detected_at: datetime = field(default_factory=datetime.utcnow)
    new_documents: List[DocumentChange] = field(default_factory=list)
    modified_documents: List[DocumentChange] = field(default_factory=list)
    deleted_documents: List[DocumentChange] = field(default_factory=list)
    unchanged_documents: List[DocumentChange] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        """Whether any changes were detected."""
        return bool(self.new_documents or self.modified_documents or self.deleted_documents)

    @property
    def documents_to_process(self) -> List[str]:
        """Get IDs of documents that need processing."""
        return (
            [d.document_id for d in self.new_documents] +
            [d.document_id for d in self.modified_documents]
        )

    @property
    def total_documents(self) -> int:
        """Total documents in current state."""
        return (
            len(self.new_documents) +
            len(self.modified_documents) +
            len(self.unchanged_documents)
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of changes."""
        return {
            'dd_id': self.dd_id,
            'run_id': self.run_id,
            'previous_run_id': self.previous_run_id,
            'has_changes': self.has_changes,
            'new_count': len(self.new_documents),
            'modified_count': len(self.modified_documents),
            'deleted_count': len(self.deleted_documents),
            'unchanged_count': len(self.unchanged_documents),
            'to_process_count': len(self.documents_to_process),
            'total_current': self.total_documents
        }


class ChangeDetector:
    """
    Detects changes between DD runs for incremental processing.
    """

    def __init__(self, db_session):
        self.db = db_session

    def compute_document_hash(self, document: Dict[str, Any]) -> str:
        """
        Compute a hash of document for change detection.

        Hash is based on:
        - extracted_text (content)
        - folder_category (affects question selection)
        - ai_category (affects question selection)
        """
        content_parts = [
            document.get('extracted_text', document.get('text', '')),
            document.get('folder_category', ''),
            document.get('ai_category', document.get('ai_document_type', ''))
        ]

        combined = '|'.join(str(p) for p in content_parts)
        return hashlib.sha256(combined.encode()).hexdigest()[:32]

    def detect_changes(
        self,
        dd_id: str,
        current_run_id: str,
        previous_run_id: Optional[str] = None,
        current_documents: Optional[List[Dict[str, Any]]] = None
    ) -> ChangeSet:
        """
        Detect changes between current state and previous run.

        Args:
            dd_id: DD identifier
            current_run_id: Current run ID
            previous_run_id: Previous run ID to compare against
            current_documents: Optional list of current documents (if already loaded)

        Returns:
            ChangeSet with categorized document changes
        """
        # Get current documents
        if current_documents is None:
            current_documents = self._get_current_documents(dd_id)

        current_doc_map = {str(d['id']): d for d in current_documents}
        current_doc_ids = set(current_doc_map.keys())
        current_hashes = {
            doc_id: self.compute_document_hash(doc)
            for doc_id, doc in current_doc_map.items()
        }

        # Get previous run's document state
        if previous_run_id:
            previous_state = self._get_previous_state(previous_run_id)
        else:
            # No previous run - all documents are new
            previous_state = {}

        previous_doc_ids = set(previous_state.keys())

        # Categorize changes
        new_docs = []
        modified_docs = []
        deleted_docs = []
        unchanged_docs = []

        # Check for new and modified documents
        for doc_id in current_doc_ids:
            doc = current_doc_map[doc_id]
            current_hash = current_hashes[doc_id]
            doc_name = doc.get('original_file_name', doc.get('filename', 'Unknown'))

            if doc_id not in previous_doc_ids:
                # New document
                new_docs.append(DocumentChange(
                    document_id=doc_id,
                    document_name=doc_name,
                    change_type=ChangeType.NEW,
                    previous_hash=None,
                    current_hash=current_hash,
                    content_changed=True
                ))
            else:
                # Existing document - check for changes
                prev = previous_state[doc_id]
                previous_hash = prev.get('hash')

                if current_hash != previous_hash:
                    # Document modified - determine what changed
                    content_changed = self._content_changed(doc, prev)
                    folder_changed = (
                        doc.get('folder_category', '') !=
                        prev.get('folder_category', '')
                    )
                    classification_changed = (
                        doc.get('ai_category', '') !=
                        prev.get('ai_category', '')
                    )

                    change_details = []
                    if content_changed:
                        change_details.append("content")
                    if folder_changed:
                        change_details.append("folder")
                    if classification_changed:
                        change_details.append("classification")

                    modified_docs.append(DocumentChange(
                        document_id=doc_id,
                        document_name=doc_name,
                        change_type=ChangeType.MODIFIED,
                        previous_hash=previous_hash,
                        current_hash=current_hash,
                        content_changed=content_changed,
                        folder_changed=folder_changed,
                        classification_changed=classification_changed,
                        change_details=", ".join(change_details)
                    ))
                else:
                    # Unchanged
                    unchanged_docs.append(DocumentChange(
                        document_id=doc_id,
                        document_name=doc_name,
                        change_type=ChangeType.UNCHANGED,
                        previous_hash=previous_hash,
                        current_hash=current_hash
                    ))

        # Check for deleted documents
        for doc_id in previous_doc_ids - current_doc_ids:
            prev = previous_state[doc_id]
            deleted_docs.append(DocumentChange(
                document_id=doc_id,
                document_name=prev.get('name', 'Unknown'),
                change_type=ChangeType.DELETED,
                previous_hash=prev.get('hash'),
                current_hash=None
            ))

        change_set = ChangeSet(
            dd_id=dd_id,
            run_id=current_run_id,
            previous_run_id=previous_run_id,
            new_documents=new_docs,
            modified_documents=modified_docs,
            deleted_documents=deleted_docs,
            unchanged_documents=unchanged_docs
        )

        logger.info(f"Change detection complete: {change_set.get_summary()}")
        return change_set

    def _content_changed(self, current: Dict, previous: Dict) -> bool:
        """Check if document content changed."""
        current_text = current.get('extracted_text', current.get('text', ''))
        previous_hash = previous.get('content_hash')

        if previous_hash:
            current_content_hash = hashlib.sha256(current_text.encode()).hexdigest()[:16]
            return current_content_hash != previous_hash

        # Fall back to overall hash comparison
        return True

    def _get_current_documents(self, dd_id: str) -> List[Dict[str, Any]]:
        """Get current documents for a DD from database."""
        result = self.db.execute("""
            SELECT
                d.id,
                d.original_file_name,
                d.extracted_text,
                f.path as folder_path,
                d.ai_document_type as ai_category,
                d.updated_at
            FROM document d
            JOIN folder f ON d.folder_id = f.id
            WHERE f.dd_id = %(dd_id)s
            AND d.is_original = false
        """, {'dd_id': dd_id})

        documents = []
        for row in result.fetchall():
            # Extract folder_category from path
            folder_path = row.folder_path or ''
            folder_category = folder_path.split('/')[-1] if '/' in folder_path else folder_path

            documents.append({
                'id': str(row.id),
                'original_file_name': row.original_file_name,
                'extracted_text': row.extracted_text or '',
                'folder_category': folder_category,
                'ai_category': row.ai_category or '',
                'updated_at': row.updated_at
            })

        return documents

    def _get_previous_state(self, run_id: str) -> Dict[str, Dict[str, Any]]:
        """Get document state from previous run."""
        result = self.db.execute("""
            SELECT
                document_id,
                document_name,
                content_hash,
                folder_category,
                ai_category
            FROM dd_document_processing_state
            WHERE run_id = %(run_id)s
        """, {'run_id': run_id})

        state = {}
        for row in result.fetchall():
            state[str(row.document_id)] = {
                'hash': row.content_hash,
                'name': row.document_name,
                'folder_category': row.folder_category,
                'ai_category': row.ai_category
            }

        return state

    def save_state(self, run_id: str, documents: List[Dict[str, Any]]):
        """
        Save document state for future change detection.

        Should be called after successful processing.
        """
        for doc in documents:
            doc_hash = self.compute_document_hash(doc)
            content_hash = hashlib.sha256(
                doc.get('extracted_text', doc.get('text', '')).encode()
            ).hexdigest()[:16]

            self.db.execute("""
                INSERT INTO dd_document_processing_state
                (run_id, document_id, document_name, content_hash, folder_category, ai_category)
                VALUES (%(run_id)s, %(document_id)s, %(document_name)s, %(content_hash)s,
                        %(folder_category)s, %(ai_category)s)
                ON CONFLICT (run_id, document_id) DO UPDATE SET
                content_hash = EXCLUDED.content_hash,
                folder_category = EXCLUDED.folder_category,
                ai_category = EXCLUDED.ai_category,
                updated_at = NOW()
            """, {
                'run_id': run_id,
                'document_id': doc.get('id'),
                'document_name': doc.get('original_file_name', doc.get('filename')),
                'content_hash': doc_hash,
                'folder_category': doc.get('folder_category', ''),
                'ai_category': doc.get('ai_category', doc.get('ai_document_type', ''))
            })

        self.db.commit()
        logger.info(f"Saved state for {len(documents)} documents in run {run_id}")

    def get_reusable_results(
        self,
        previous_run_id: str,
        unchanged_doc_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get processing results from previous run for unchanged documents.

        This allows reusing Pass 1 and Pass 2 results without re-processing.
        """
        if not unchanged_doc_ids:
            return {}

        placeholders = ','.join(['%s'] * len(unchanged_doc_ids))
        result = self.db.execute(f"""
            SELECT
                document_id,
                pass1_result,
                pass2_findings,
                pass1_completed,
                pass2_completed
            FROM dd_document_processing_state
            WHERE run_id = %s
            AND document_id IN ({placeholders})
            AND pass1_completed = true
        """, [previous_run_id] + unchanged_doc_ids)

        reusable = {}
        for row in result.fetchall():
            doc_id = str(row.document_id)
            reusable[doc_id] = {
                'pass1_result': row.pass1_result,
                'pass2_findings': row.pass2_findings,
                'pass1_completed': row.pass1_completed,
                'pass2_completed': row.pass2_completed
            }

        logger.info(f"Found {len(reusable)} reusable results from previous run")
        return reusable

    def update_processing_state(
        self,
        run_id: str,
        document_id: str,
        pass1_result: Optional[Dict] = None,
        pass2_findings: Optional[List] = None,
        entity_extracted: bool = False,
        compressed: bool = False
    ):
        """Update processing state for a document."""
        updates = []
        params = {'run_id': run_id, 'document_id': document_id}

        if pass1_result is not None:
            updates.append("pass1_result = %(pass1_result)s, pass1_completed = true")
            params['pass1_result'] = pass1_result

        if pass2_findings is not None:
            updates.append("pass2_findings = %(pass2_findings)s, pass2_completed = true")
            params['pass2_findings'] = pass2_findings

        if entity_extracted:
            updates.append("entity_extracted = true")

        if compressed:
            updates.append("compressed = true")

        if updates:
            updates.append("updated_at = NOW()")
            self.db.execute(f"""
                UPDATE dd_document_processing_state
                SET {', '.join(updates)}
                WHERE run_id = %(run_id)s AND document_id = %(document_id)s
            """, params)
            self.db.commit()
