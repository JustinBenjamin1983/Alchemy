# File: server/opinion/api_2/shared/models.py

from sqlalchemy import (
    Column, String, Boolean, Text, ForeignKey, DateTime, Integer, Float, BigInteger, ForeignKeyConstraint, UniqueConstraint, JSON
)
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import relationship, declarative_base
import uuid
import datetime

Base = declarative_base()

FindingTypeEnum = ENUM(
    'positive', 'negative', 'neutral', 'gap', 'informational',
    name='finding_type_enum',
    create_type=True
)

ActionPriorityEnum = ENUM(
    'critical', 'high', 'medium', 'low', 'none',
    name='action_priority_enum',
    create_type=True
)

QuestionTypeEnum = ENUM(
    'compliance_check', 'risk_search', 'information_gathering', 'verification',
    name='question_type_enum',
    create_type=True
)

# Enhanced DD: Deal impact classification for findings
DealImpactEnum = ENUM(
    'deal_blocker', 'condition_precedent', 'price_chip', 'warranty_indemnity',
    'post_closing', 'noted', 'none',
    name='deal_impact_enum',
    create_type=True
)

class BaseModel(Base):
    __abstract__ = True

    def to_dict(self, include_relationships=True, depth=1, _visited=None):
        if _visited is None:
            _visited = set()

        if self in _visited:
            return None  # Prevent circular references
        _visited.add(self)

        result = {}

        # Include column attributes
        for column in inspect(self).mapper.column_attrs:
            val = getattr(self, column.key)
            if isinstance(val, datetime.datetime):
                result[column.key] = val.isoformat()
            elif isinstance(val, uuid.UUID):
                result[column.key] = str(val)
            else:
                result[column.key] = val

        # Include relationships if requested
        if include_relationships and depth > 0:
            for rel in inspect(self.__class__).relationships:
                related = getattr(self, rel.key)

                if related is None:
                    result[rel.key] = None
                elif rel.uselist:
                    result[rel.key] = [
                        obj.to_dict(include_relationships=True, depth=depth - 1, _visited=_visited)
                        for obj in related
                    ]
                else:
                    result[rel.key] = related.to_dict(include_relationships=True, depth=depth - 1, _visited=_visited)

        return result
    
class DueDiligence(BaseModel):
    __tablename__ = "due_diligence"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    briefing = Column(Text)
    owned_by = Column(Text, nullable=False)
    original_file_name = Column(Text)
    original_file_doc_id = Column(UUID(as_uuid=True))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    members = relationship("DueDiligenceMember", back_populates="dd", cascade="all, delete")
    folders = relationship("Folder", back_populates="dd", cascade="all, delete")
    history = relationship("DocumentHistory", back_populates="dd", cascade="all, delete")



class DueDiligenceMember(BaseModel):
    __tablename__ = "due_diligence_member"
    __table_args__ = (
        UniqueConstraint("dd_id", "member_email", name="uq_dd_member"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dd_id = Column(UUID(as_uuid=True), ForeignKey("due_diligence.id", ondelete="CASCADE"), nullable=False)
    member_email = Column(Text, nullable=False)

    dd = relationship("DueDiligence", back_populates="members")
    perspectives = relationship("Perspective", back_populates="member", cascade="all, delete-orphan")

class Folder(BaseModel):
    __tablename__ = "folder"

    id = Column(UUID(as_uuid=True), primary_key=True)
    dd_id = Column(UUID(as_uuid=True), ForeignKey("due_diligence.id", ondelete="CASCADE"))
    folder_name = Column(Text, nullable=False)
    is_root = Column(Boolean, default=False)
    path = Column(Text, nullable=False)
    hierarchy = Column(Text, nullable=False)
    description = Column(Text)

    dd = relationship("DueDiligence", back_populates="folders")
    documents = relationship("Document", back_populates="folder", cascade="all, delete")


class Document(BaseModel):
    __tablename__ = "document"

    id = Column(UUID(as_uuid=True), primary_key=True)
    folder_id = Column(UUID(as_uuid=True), ForeignKey("folder.id", ondelete="CASCADE"), nullable=False)
    type = Column(Text, nullable=False)
    original_file_name = Column(Text, nullable=False) # TODO consider changing to file_name
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
    processing_status = Column(Text, nullable=False)
    is_original = Column(Boolean, default=False)
    size_in_bytes = Column(BigInteger)
    description = Column(Text)

    folder = relationship("Folder", back_populates="documents")
    history = relationship("DocumentHistory", back_populates="document", cascade="all, delete")
    


DocumentActionEnum = ENUM(
    'ZIP uploaded', 'Added', 'Moved', 'Deleted', 'File Renamed',
    name='document_action',
    create_type=True
)

class DocumentHistory(BaseModel):
    __tablename__ = "document_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(UUID(as_uuid=True), ForeignKey("document.id", ondelete="CASCADE"), nullable=False)
    dd_id = Column(UUID(as_uuid=True), ForeignKey("due_diligence.id", ondelete="CASCADE"), nullable=False)
    original_file_name = Column(Text, nullable=False) # TODO consider changing to file_name
    previous_folder = Column(Text)
    current_folder = Column(Text)
    action = Column(DocumentActionEnum, nullable=False)
    by_user = Column(Text)
    action_at = Column(DateTime, default=datetime.datetime.utcnow)

    document = relationship("Document", back_populates="history")
    dd = relationship("DueDiligence", backref="document_history")


class Perspective(BaseModel):
    __tablename__ = "perspective"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id = Column(UUID(as_uuid=True), ForeignKey("due_diligence_member.id", ondelete="CASCADE"), nullable=False)
    lens = Column(Text, nullable=False)

    member = relationship("DueDiligenceMember", back_populates="perspectives")
    risks = relationship("PerspectiveRisk", back_populates="perspective", cascade="all, delete-orphan")

class PerspectiveRisk(BaseModel):
    __tablename__ = "perspective_risk"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    perspective_id = Column(UUID(as_uuid=True), ForeignKey("perspective.id", ondelete="CASCADE"), nullable=False)
    category = Column(Text, nullable=False)
    detail = Column(Text, nullable=False)
    folder_scope = Column(Text, default="All Folders")
    is_processed = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    search_strategy = Column(Text)
    question_type = Column(QuestionTypeEnum, default="risk_search")
    expected_answer_type = Column(Text, default="risk_identification")
    perspective = relationship("Perspective", back_populates="risks")

# Update PerspectiveRiskFinding model with new fields
PerspectiveRiskFindingStatusEnum = ENUM(
    'New', 'Red', 'Amber', 'Green', 'Info', 'Deleted',
    name='perspective_risk_finding_status',
    create_type=True
)


class PerspectiveRiskFinding(BaseModel):
    __tablename__ = "perspective_risk_finding"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    perspective_risk_id = Column(UUID(as_uuid=True), ForeignKey("perspective_risk.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("document.id", ondelete="CASCADE"), nullable=False)
    phrase = Column(Text, nullable=False)
    page_number = Column(Text, nullable=False)
    status = Column(PerspectiveRiskFindingStatusEnum, nullable=False)
    is_reviewed = Column(Boolean, default=False)
    reviewed_by = Column(Text, nullable=True)
    
    # New fields for enhanced findings model
    finding_type = Column(FindingTypeEnum, default="negative")
    confidence_score = Column(Float, default=0.5)
    requires_action = Column(Boolean, default=False)
    action_priority = Column(ActionPriorityEnum, default="none")
    direct_answer = Column(Text)
    evidence_quote = Column(Text)
    missing_documents = Column(Text)
    action_items = Column(Text)

    # Enhanced DD fields for deal impact and financial exposure
    deal_impact = Column(DealImpactEnum, default="none")
    financial_exposure_amount = Column(Float, nullable=True)
    financial_exposure_currency = Column(String(10), default="ZAR")
    financial_exposure_calculation = Column(Text, nullable=True)  # "Show your working"
    clause_reference = Column(Text, nullable=True)  # e.g., "Clause 15.2.1"
    cross_doc_source = Column(Text, nullable=True)  # For cross-doc findings: "MOI vs Board Resolution"
    analysis_pass = Column(Integer, default=2)  # Which pass generated this: 2=per-doc, 3=cross-doc

    # Relationships
    perspective_risk = relationship("PerspectiveRisk", backref="findings")
    document = relationship("Document", backref="doc_findings")

class DDQuestion(BaseModel):
    __tablename__ = "dd_question"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dd_id = Column(UUID(as_uuid=True), ForeignKey("due_diligence.id", ondelete="CASCADE"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text)
    asked_by = Column(Text, nullable=False)  # email of the user who asked
    folder_id = Column(UUID(as_uuid=True), ForeignKey("folder.id", ondelete="SET NULL"), nullable=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("document.id", ondelete="SET NULL"), nullable=True)
    folder_name = Column(Text)  # Store folder name in case folder is deleted
    document_name = Column(Text)  # Store document name in case document is deleted
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    dd = relationship("DueDiligence", backref="questions")
    folder = relationship("Folder")
    document = relationship("Document")
    referenced_documents = relationship("DDQuestionReferencedDoc", back_populates="question", cascade="all, delete-orphan")


class DDQuestionReferencedDoc(BaseModel):
    __tablename__ = "dd_question_referenced_doc"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id = Column(UUID(as_uuid=True), ForeignKey("dd_question.id", ondelete="CASCADE"), nullable=False)
    doc_id = Column(UUID(as_uuid=True), nullable=False)  # Document ID that was referenced
    filename = Column(Text, nullable=False)
    page_number = Column(Text)
    folder_path = Column(Text)

    # Relationships
    question = relationship("DDQuestion", back_populates="referenced_documents")


class DDWizardDraft(BaseModel):
    """Stores in-progress DD wizard configurations that users can resume later."""
    __tablename__ = "dd_wizard_draft"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owned_by = Column(Text, nullable=False)  # email of the user who created the draft
    current_step = Column(Integer, default=1)  # 1-5 for the wizard steps

    # Step 1: Transaction Basics
    transaction_type = Column(Text)
    transaction_name = Column(Text)
    client_role = Column(Text)
    deal_structure = Column(Text)
    estimated_value = Column(Float)
    target_closing_date = Column(DateTime)

    # Step 2: Deal Context
    deal_rationale = Column(Text)
    known_concerns = Column(Text)  # JSON array stored as text

    # Step 3: Focus Areas
    critical_priorities = Column(Text)  # JSON array stored as text
    known_deal_breakers = Column(Text)  # JSON array stored as text
    deprioritized_areas = Column(Text)  # JSON array stored as text

    # Step 4: Key Parties
    target_company_name = Column(Text)
    key_persons = Column(Text)  # JSON array stored as text
    counterparties = Column(Text)  # JSON array stored as text
    key_lenders = Column(Text)  # JSON array stored as text
    key_regulators = Column(Text)  # JSON array stored as text

    # Metadata
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


# Processing checkpoint status enum
ProcessingStatusEnum = ENUM(
    'pending', 'processing', 'completed', 'failed', 'paused',
    name='processing_status_enum',
    create_type=True
)


class DDProcessingCheckpoint(BaseModel):
    """
    Tracks progress of enhanced DD processing pipeline.
    Enables resume capability if processing is interrupted.
    """
    __tablename__ = "dd_processing_checkpoint"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dd_id = Column(UUID(as_uuid=True), ForeignKey("due_diligence.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Current processing state
    current_pass = Column(Integer, default=1)  # 1-4 for the pipeline passes
    current_stage = Column(String(100))  # e.g., "pass3_financial_cluster"
    status = Column(ProcessingStatusEnum, default="pending")

    # Pass 1 outputs (stored for reuse in later passes)
    pass1_extractions = Column(JSON)  # {doc_id: extraction_data}

    # Progress tracking
    documents_processed = Column(Integer, default=0)
    total_documents = Column(Integer)
    clusters_processed = Column(JSON)  # ["corporate_governance", "financial", ...]
    questions_processed = Column(Integer, default=0)
    total_questions = Column(Integer)

    # Granular pass progress (0-100)
    pass1_progress = Column(Integer, default=0)
    pass2_progress = Column(Integer, default=0)
    pass3_progress = Column(Integer, default=0)
    pass4_progress = Column(Integer, default=0)

    # Current item being processed (for UI display)
    current_document_id = Column(UUID(as_uuid=True), nullable=True)
    current_document_name = Column(Text, nullable=True)
    current_question = Column(Text, nullable=True)

    # Finding counts (updated as findings are created)
    findings_total = Column(Integer, default=0)
    findings_critical = Column(Integer, default=0)
    findings_high = Column(Integer, default=0)
    findings_medium = Column(Integer, default=0)
    findings_low = Column(Integer, default=0)
    findings_deal_blockers = Column(Integer, default=0)
    findings_cps = Column(Integer, default=0)

    # Cluster info
    clusters_total = Column(Integer, default=0)

    # Cost tracking (accumulated across all passes)
    total_input_tokens = Column(Integer, default=0)
    total_output_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)
    cost_by_model = Column(JSON)  # {"haiku": {input: X, output: Y}, "sonnet": {...}}

    # Timestamps
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Error handling
    last_error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # Relationships
    dd = relationship("DueDiligence", backref="processing_checkpoints")