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
    'positive', 'negative', 'neutral', 'gap', 'informational', 'conflict',
    'cascade', 'cumulative', 'information',
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

# Action Category classification for findings (Phase 1 Enhancement)
ActionCategoryEnum = ENUM(
    'terminal', 'valuation', 'indemnity', 'warranty', 'information', 'condition_precedent',
    name='action_category_enum',
    create_type=True
)

# Materiality Classification (Phase 1 Enhancement)
MaterialityClassificationEnum = ENUM(
    'material', 'potentially_material', 'likely_immaterial', 'unquantified',
    name='materiality_classification_enum',
    create_type=True
)

# Validation Checkpoint types
CheckpointTypeEnum = ENUM(
    'missing_docs', 'post_analysis', 'entity_confirmation',
    name='checkpoint_type_enum',
    create_type=True
)

# Validation Checkpoint status
CheckpointStatusEnum = ENUM(
    'pending', 'awaiting_user_input', 'completed', 'skipped',
    name='checkpoint_status_enum',
    create_type=True
)

# Entity relationship types
EntityRelationshipEnum = ENUM(
    'target', 'parent', 'subsidiary', 'related_party', 'counterparty', 'unknown',
    name='entity_relationship_enum',
    create_type=True
)

# Document reference types
ReferenceTypeEnum = ENUM(
    'agreement', 'legal_opinion', 'report', 'certificate', 'schedule', 'correspondence',
    name='reference_type_enum',
    create_type=True
)

# Document reference criticality
ReferenceCriticalityEnum = ENUM(
    'critical', 'important', 'minor',
    name='reference_criticality_enum',
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

    # Full wizard project setup data (JSON)
    project_setup = Column(JSON, nullable=True)

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

    # Phase 2: Blueprint Folder Organisation fields
    folder_category = Column(String(50), nullable=True)  # e.g., "01_Corporate", "02_Commercial"
    is_blueprint_folder = Column(Boolean, default=False)  # TRUE for auto-created blueprint folders
    expected_doc_types = Column(JSON, default=list)  # Expected document types for this folder
    sort_order = Column(Integer, default=99)  # Numeric sort order (01, 02, 03...)
    relevance = Column(String(20), nullable=True)  # critical, high, medium, low, n/a
    document_count = Column(Integer, default=0)  # Cached count for display

    dd = relationship("DueDiligence", back_populates="folders")
    documents = relationship("Document", back_populates="folder", cascade="all, delete", foreign_keys="[Document.folder_id]")


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

    # Readability check status (for pre-processing validation)
    readability_status = Column(Text, default="pending")  # pending, checking, ready, failed
    readability_error = Column(Text, nullable=True)  # Error message if readability check failed

    # PPTX-to-PDF conversion fields
    converted_doc_id = Column(UUID(as_uuid=True), nullable=True)  # Reference to converted PDF document
    conversion_status = Column(String(20), nullable=True)  # pending, converting, converted, failed
    converted_from_id = Column(UUID(as_uuid=True), nullable=True)  # For converted docs, reference to original

    # AI Classification fields (Phase 1: Document Organisation)
    ai_category = Column(String(50), nullable=True)  # e.g., "01_Corporate", "02_Commercial"
    ai_subcategory = Column(String(100), nullable=True)  # e.g., "Constitutional", "Supply Agreements"
    ai_document_type = Column(String(100), nullable=True)  # e.g., "Shareholders Agreement", "Mining Right"
    ai_confidence = Column(Float, nullable=True)  # 0-100 confidence score
    category_source = Column(String(20), default="pending")  # pending, ai, manual, zip_structure
    ai_key_parties = Column(JSON, default=list)  # List of party names extracted from document
    classification_status = Column(String(20), default="pending")  # pending, classifying, classified, failed
    ai_classification_reasoning = Column(Text, nullable=True)  # AI's explanation for classification
    classification_error = Column(Text, nullable=True)  # Error message if classification failed
    classified_at = Column(DateTime, nullable=True)  # When classification completed

    # Phase 2: Folder Organisation fields
    original_folder_id = Column(UUID(as_uuid=True), ForeignKey("folder.id", ondelete="SET NULL"), nullable=True)
    folder_assignment_source = Column(String(20), default="original_zip")  # original_zip, ai, manual

    # Page-aware content (for source referencing in findings)
    extracted_text_with_pages = Column(Text, nullable=True)  # Text with [PAGE X] markers
    total_pages = Column(Integer, nullable=True)  # Total number of pages in document

    folder = relationship("Folder", back_populates="documents", foreign_keys="[Document.folder_id]")
    original_folder = relationship("Folder", foreign_keys="[Document.original_folder_id]")
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
    document_id = Column(UUID(as_uuid=True), ForeignKey("document.id", ondelete="CASCADE"), nullable=True)
    phrase = Column(Text, nullable=False)
    page_number = Column(Text, nullable=False)  # Clause reference (e.g., "Clause 15.2")
    actual_page_number = Column(Integer, nullable=True)  # Actual page number in document (1-indexed)
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

    # Run tracking - links finding to specific analysis run
    run_id = Column(UUID(as_uuid=True), ForeignKey("dd_analysis_run.id", ondelete="CASCADE"), nullable=True)

    # Phase 3: Folder-aware processing fields
    folder_category = Column(String(50), nullable=True)  # e.g., "01_Corporate", "02_Commercial"
    question_id = Column(Text, nullable=True)  # Links to blueprint question that generated this finding
    is_cross_document = Column(Boolean, default=False)  # True for cross-document findings
    related_document_ids = Column(Text, nullable=True)  # JSON array of doc IDs for cross-doc findings
    source_cluster = Column(String(50), nullable=True)  # Pass 3 cluster: "corporate_governance", "financial", etc.

    # Chain of Thought reasoning - JSON object with reasoning steps
    # Format: {"step_1_identification": "...", "step_2_context": "...", "step_3_transaction_impact": "...", ...}
    reasoning = Column(Text, nullable=True)

    # ===== PHASE 1 ENHANCEMENTS =====

    # Action Category (Task 4) - How to resolve this finding
    action_category = Column(String(50), nullable=True)  # terminal|valuation|indemnity|warranty|information|condition_precedent
    resolution_mechanism = Column(String(100), nullable=True)  # suspensive_condition|price_adjustment|indemnity|warranty|disclosure|walk_away
    resolution_responsible_party = Column(String(50), nullable=True)  # seller|buyer|both|third_party
    resolution_timeline = Column(String(50), nullable=True)  # before_signing|between_sign_and_close|post_closing|ongoing
    resolution_cost = Column(Float, nullable=True)
    resolution_cost_confidence = Column(Float, nullable=True)
    resolution_description = Column(Text, nullable=True)  # Detailed resolution recommendation

    # Materiality (Task 3) - Relative importance based on deal value
    materiality_classification = Column(String(50), nullable=True)  # material|potentially_material|likely_immaterial|unquantified
    materiality_ratio = Column(Float, nullable=True)  # Ratio to transaction value (e.g., 0.05 = 5%)
    materiality_threshold = Column(String(200), nullable=True)  # Threshold description applied
    materiality_qualitative_override = Column(String(200), nullable=True)  # Qualitative factors overriding quantitative

    # Confidence Calibration (Task 6) - Granular confidence scores
    confidence_finding_exists = Column(Float, nullable=True)  # 0.0-1.0: Confidence the issue exists
    confidence_severity = Column(Float, nullable=True)  # 0.0-1.0: Confidence severity is correct
    confidence_amount = Column(Float, nullable=True)  # 0.0-1.0: Confidence financial amount is correct
    confidence_basis = Column(Text, nullable=True)  # Explanation of confidence assessment

    # Statutory Reference (Task 2) - Legal citation framework
    statutory_act = Column(String(200), nullable=True)  # E.g., "Mineral and Petroleum Resources Development Act 28 of 2002"
    statutory_section = Column(String(100), nullable=True)  # E.g., "Section 11"
    statutory_consequence = Column(Text, nullable=True)  # What happens if provision violated
    regulatory_body = Column(String(200), nullable=True)  # E.g., "Department of Mineral Resources and Energy"

    # Relationships
    perspective_risk = relationship("PerspectiveRisk", backref="findings")
    document = relationship("Document", backref="doc_findings")
    run = relationship("DDAnalysisRun", back_populates="findings")

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
    client_name = Column(Text)
    target_entity_name = Column(Text)
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
    key_persons = Column(Text)  # JSON array stored as text (keyIndividuals)
    key_suppliers = Column(Text)  # JSON array stored as text (keySuppliers)
    counterparties = Column(Text)  # JSON array stored as text (keyCustomers)
    key_contractors = Column(Text)  # JSON array stored as text (keyContractors)
    key_lenders = Column(Text)  # JSON array stored as text
    key_regulators = Column(Text)  # JSON array stored as text
    key_other = Column(Text)  # JSON array stored as text (keyOther)
    shareholder_entity_name = Column(Text)
    shareholders = Column(Text)  # JSON array stored as text

    # Phase 1 Enhancement: Entity Mapping Context
    target_registration_number = Column(Text)  # Company registration number for entity matching
    known_subsidiaries = Column(Text)  # JSON array: [{name, relationship}]
    holding_company = Column(Text)  # JSON object: {name, percentage}
    expected_counterparties = Column(Text)  # JSON array of counterparty names to watch for

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
    dd_id = Column(UUID(as_uuid=True), ForeignKey("due_diligence.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey("dd_analysis_run.id", ondelete="CASCADE"), nullable=True)

    # Current processing state
    current_pass = Column(Integer, default=1)  # 1-4 for the pipeline passes
    current_stage = Column(String(100))  # e.g., "pass3_financial_cluster"
    status = Column(ProcessingStatusEnum, default="pending")

    # Pass 1 outputs (stored for reuse in later passes)
    pass1_extractions = Column(JSON)  # {doc_id: extraction_data}

    # Pass 2 outputs (for resume capability)
    pass2_findings = Column(JSON)  # List of findings from Pass 2
    processed_doc_ids = Column(JSON)  # List of document IDs already processed

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

    # Phase 5: Knowledge Graph stats
    graph_vertices = Column(Integer, default=0)
    graph_edges = Column(Integer, default=0)

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


# Analysis Run status enum (reuses ProcessingStatusEnum)
class DDAnalysisRun(BaseModel):
    """
    Represents a single DD analysis run.
    Each run processes a selected subset of documents and stores its findings separately.
    """
    __tablename__ = "dd_analysis_run"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dd_id = Column(UUID(as_uuid=True), ForeignKey("due_diligence.id", ondelete="CASCADE"), nullable=False)

    # Run identification
    run_number = Column(Integer, nullable=False)  # Sequential per DD (1, 2, 3...)
    name = Column(Text, nullable=False)  # Default: "Run {n} - {timestamp}", editable

    # Status
    status = Column(ProcessingStatusEnum, default="pending")

    # Document selection (JSON array of document UUIDs)
    selected_document_ids = Column(JSON, nullable=False, default=list)

    # Progress tracking
    documents_processed = Column(Integer, default=0)
    total_documents = Column(Integer, default=0)

    # Finding summary counts
    findings_total = Column(Integer, default=0)
    findings_critical = Column(Integer, default=0)
    findings_high = Column(Integer, default=0)
    findings_medium = Column(Integer, default=0)
    findings_low = Column(Integer, default=0)

    # Synthesis data (Pass 4 output)
    # Contains: executive_summary, deal_assessment, financial_exposure_summary,
    # deal_blockers, conditions_precedent, key_recommendations, next_steps
    synthesis_data = Column(JSON, nullable=True, default=None)

    # Cost tracking
    estimated_cost_usd = Column(Float, default=0.0)

    # Model tier configuration (cost_optimized, balanced, high_accuracy, maximum_accuracy)
    model_tier = Column(Text, default="balanced")

    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Error handling
    last_error = Column(Text, nullable=True)

    # Relationships
    dd = relationship("DueDiligence", backref="analysis_runs")
    findings = relationship("PerspectiveRiskFinding", back_populates="run", cascade="all, delete-orphan")


# Organisation status enum for Phase 1 document classification
OrganisationStatusEnum = ENUM(
    'pending', 'classifying', 'organising', 'completed', 'failed',
    name='organisation_status_enum',
    create_type=True
)


class DDOrganisationStatus(BaseModel):
    """
    Tracks the document organisation/classification progress for a DD project.
    Created when ZIP is uploaded, updated as documents are classified.
    """
    __tablename__ = "dd_organisation_status"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dd_id = Column(UUID(as_uuid=True), ForeignKey("due_diligence.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Status tracking
    status = Column(String(20), default="pending")  # pending, classifying, organising, completed, failed

    # Progress counters
    total_documents = Column(Integer, default=0)
    classified_count = Column(Integer, default=0)
    low_confidence_count = Column(Integer, default=0)  # Count of docs with confidence < 70
    failed_count = Column(Integer, default=0)

    # Category distribution (JSON object with counts per category)
    category_counts = Column(JSON, default=dict)  # {"01_Corporate": 5, "02_Commercial": 3, ...}

    # Error handling
    error_message = Column(Text, nullable=True)

    # Phase 2: Organisation tracking
    organised_count = Column(Integer, default=0)  # Documents moved to blueprint folders
    needs_review_count = Column(Integer, default=0)  # Documents in 99_Needs_Review

    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    organised_at = Column(DateTime, nullable=True)  # When organisation completed
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    dd = relationship("DueDiligence", backref="organisation_status")


# ============================================================================
# PHASE 1 ENHANCEMENTS: New Tables for Human-in-the-Loop Features
# ============================================================================

class DDValidationCheckpoint(BaseModel):
    """
    Human-in-the-loop validation checkpoints.

    Checkpoint Types:
    - 'missing_docs': After classification, validates required documents are present
    - 'post_analysis': After Pass 2, combined validation wizard (4 steps)
    - 'entity_confirmation': Confirms entity relationships when ambiguous
    """
    __tablename__ = "dd_validation_checkpoint"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dd_id = Column(UUID(as_uuid=True), ForeignKey("due_diligence.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey("dd_analysis_run.id", ondelete="CASCADE"), nullable=True)

    checkpoint_type = Column(String(50), nullable=False)  # 'missing_docs' | 'post_analysis' | 'entity_confirmation'
    status = Column(String(50), default="pending")  # 'pending' | 'awaiting_user_input' | 'completed' | 'skipped'

    # AI-generated content for validation
    preliminary_summary = Column(Text, nullable=True)  # AI-generated summary of findings/understanding
    questions = Column(JSON, nullable=True)  # [{question, context, options, user_answer, correction}]
    missing_docs = Column(JSON, nullable=True)  # [{doc_type, importance, reason, user_response}]
    financial_confirmations = Column(JSON, nullable=True)  # [{metric, extracted_value, confirmed_value, source}]

    # User responses
    user_responses = Column(JSON, nullable=True)  # Freeform user responses
    uploaded_doc_ids = Column(JSON, nullable=True)  # Document IDs uploaded during checkpoint
    manual_data_inputs = Column(JSON, nullable=True)  # Manual data entered by user (e.g., EBITDA)

    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    dd = relationship("DueDiligence", backref="validation_checkpoints")
    run = relationship("DDAnalysisRun", backref="validation_checkpoints")


class DDReportVersion(BaseModel):
    """
    Report versioning for refinement loop.

    Enables iterative report improvement through AI-driven refinements
    with full version history and diff tracking.
    """
    __tablename__ = "dd_report_version"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("dd_analysis_run.id", ondelete="CASCADE"), nullable=False)

    version = Column(Integer, nullable=False)  # Sequential version number (1, 2, 3...)
    content = Column(JSON, nullable=False)  # Full report content (synthesis_data structure)
    refinement_prompt = Column(Text, nullable=True)  # User's refinement request that led to this version
    changes = Column(JSON, nullable=True)  # [{section, change_type, old_text, new_text, reasoning}]

    # Version metadata
    is_current = Column(Boolean, default=True)  # Is this the current/active version
    change_summary = Column(Text, nullable=True)  # AI-generated summary of changes from previous version

    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    created_by = Column(String(200), nullable=True)  # User email who triggered refinement

    # Relationships
    run = relationship("DDAnalysisRun", backref="report_versions")


class DDEntityMap(BaseModel):
    """
    Entity mapping for transaction parties.

    Maps all entities mentioned in documents to their relationship
    with the target entity. Supports entity confirmation checkpoint
    when relationships are ambiguous.
    """
    __tablename__ = "dd_entity_map"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dd_id = Column(UUID(as_uuid=True), ForeignKey("due_diligence.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey("dd_analysis_run.id", ondelete="CASCADE"), nullable=True)

    # Entity identification
    entity_name = Column(String(500), nullable=False)  # Full legal name of entity
    registration_number = Column(String(100), nullable=True)  # Company registration number if found

    # Relationship classification
    relationship_to_target = Column(String(50), nullable=False)  # target|parent|subsidiary|related_party|counterparty|unknown
    relationship_detail = Column(Text, nullable=True)  # Detailed description of relationship

    # Confidence and evidence
    confidence = Column(Float, default=0.5)  # 0.0-1.0 confidence in classification
    documents_appearing_in = Column(JSON, nullable=True)  # Array of document IDs where entity appears
    evidence = Column(Text, nullable=True)  # Evidence supporting the relationship classification

    # Human confirmation
    requires_human_confirmation = Column(Boolean, default=False)  # Flag for checkpoint trigger
    human_confirmed = Column(Boolean, default=False)  # Whether human has confirmed
    human_confirmation_value = Column(String(50), nullable=True)  # Human-provided relationship if different

    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    dd = relationship("DueDiligence", backref="entity_maps")
    run = relationship("DDAnalysisRun", backref="entity_maps")


class DDDocumentReference(BaseModel):
    """
    References to other documents extracted during Pass 1.

    Tracks documents mentioned in analyzed documents that may or may not
    be present in the data room. Enables gap analysis for missing critical docs.
    """
    __tablename__ = "dd_document_reference"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("dd_analysis_run.id", ondelete="CASCADE"), nullable=False)
    source_document_id = Column(UUID(as_uuid=True), ForeignKey("document.id", ondelete="CASCADE"), nullable=False)

    # Reference details
    referenced_document_name = Column(String(500), nullable=False)  # Name/description of referenced document
    reference_context = Column(Text, nullable=True)  # Why/how the document is referenced
    reference_type = Column(String(50), nullable=True)  # agreement|legal_opinion|report|certificate|schedule|correspondence
    criticality = Column(String(20), nullable=True)  # critical|important|minor
    clause_reference = Column(String(200), nullable=True)  # Where in source document the reference appears
    quote = Column(Text, nullable=True)  # Exact quote mentioning the reference

    # Matching status
    found_in_data_room = Column(Boolean, nullable=True)  # Whether referenced doc is in data room
    matched_document_id = Column(UUID(as_uuid=True), ForeignKey("document.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    run = relationship("DDAnalysisRun", backref="document_references")
    source_document = relationship("Document", foreign_keys=[source_document_id], backref="outgoing_references")
    matched_document = relationship("Document", foreign_keys=[matched_document_id], backref="incoming_references")