# File: server/opinion/api-2/shared/pipeline_stages.py
"""
DD Pipeline Stage Definitions

Defines all pipeline stages in the correct execution order.
Used for progress tracking, resume functionality, and UI display.
"""

from enum import Enum
from typing import List, Dict, Any

class PipelinePhase(str, Enum):
    """High-level pipeline phases."""
    PRE_PROCESSING = "pre_processing"
    PROCESSING = "processing"
    POST_PROCESSING = "post_processing"


class PipelineStage(str, Enum):
    """
    All pipeline stages in execution order.

    PRE-PROCESSING PHASE:
    1. Wizard → 2. Classification → 3. Checkpoint A → 4. Readability → 5. Entity Mapping → 6. Checkpoint B

    PROCESSING PHASE:
    7. Materiality → 8. Pass 1 (Extract) → 9. Pass 2 (Analyze) → 10. Checkpoint C →
    11. Pass 3 (Calculate) → 12. Pass 4 (Cross-Doc) → 13. Pass 5 (Aggregate) →
    14. Pass 6 (Synthesize) → 15. Pass 7 (Verify)

    POST-PROCESSING PHASE:
    16. Store & Display → 17. Refinement Loop
    """
    # PRE-PROCESSING PHASE
    WIZARD = "wizard"
    CLASSIFICATION = "classification"
    CHECKPOINT_A_MISSING_DOCS = "checkpoint_a_missing_docs"
    READABILITY_CHECK = "readability_check"
    ENTITY_MAPPING = "entity_mapping"
    CHECKPOINT_B_ENTITY_CONFIRM = "checkpoint_b_entity_confirm"

    # PROCESSING PHASE
    MATERIALITY_THRESHOLDS = "materiality_thresholds"
    PASS_1_EXTRACT = "pass_1_extract"
    PASS_2_ANALYZE = "pass_2_analyze"
    CHECKPOINT_C_VALIDATION = "checkpoint_c_validation"
    PASS_3_CALCULATE = "pass_3_calculate"
    PASS_4_CROSS_DOC = "pass_4_cross_doc"
    PASS_5_AGGREGATE = "pass_5_aggregate"
    PASS_6_SYNTHESIZE = "pass_6_synthesize"
    PASS_7_VERIFY = "pass_7_verify"

    # POST-PROCESSING PHASE
    STORE_DISPLAY = "store_display"
    REFINEMENT_LOOP = "refinement_loop"

    # Terminal states
    COMPLETED = "completed"
    FAILED = "failed"


# Stage execution order (index = order)
STAGE_ORDER: List[PipelineStage] = [
    PipelineStage.WIZARD,
    PipelineStage.CLASSIFICATION,
    PipelineStage.CHECKPOINT_A_MISSING_DOCS,
    PipelineStage.READABILITY_CHECK,
    PipelineStage.ENTITY_MAPPING,
    PipelineStage.CHECKPOINT_B_ENTITY_CONFIRM,
    PipelineStage.MATERIALITY_THRESHOLDS,
    PipelineStage.PASS_1_EXTRACT,
    PipelineStage.PASS_2_ANALYZE,
    PipelineStage.CHECKPOINT_C_VALIDATION,
    PipelineStage.PASS_3_CALCULATE,
    PipelineStage.PASS_4_CROSS_DOC,
    PipelineStage.PASS_5_AGGREGATE,
    PipelineStage.PASS_6_SYNTHESIZE,
    PipelineStage.PASS_7_VERIFY,
    PipelineStage.STORE_DISPLAY,
    PipelineStage.REFINEMENT_LOOP,
]


# Stage metadata for UI display
STAGE_METADATA: Dict[PipelineStage, Dict[str, Any]] = {
    PipelineStage.WIZARD: {
        "name": "Project Setup",
        "description": "Enter transaction details and upload documents",
        "phase": PipelinePhase.PRE_PROCESSING,
        "order": 1,
        "is_checkpoint": False,
        "requires_user_input": True,
        "model": None,
        "can_resume_from": True,
    },
    PipelineStage.CLASSIFICATION: {
        "name": "Document Classification",
        "description": "AI categorizes documents into folders",
        "phase": PipelinePhase.PRE_PROCESSING,
        "order": 2,
        "is_checkpoint": False,
        "requires_user_input": False,
        "model": "haiku",
        "can_resume_from": True,
    },
    PipelineStage.CHECKPOINT_A_MISSING_DOCS: {
        "name": "Checkpoint A: Missing Documents",
        "description": "Validate required documents are present",
        "phase": PipelinePhase.PRE_PROCESSING,
        "order": 3,
        "is_checkpoint": True,
        "requires_user_input": True,
        "model": None,
        "can_resume_from": True,
    },
    PipelineStage.READABILITY_CHECK: {
        "name": "Readability Check",
        "description": "Validate documents and convert formats to PDF",
        "phase": PipelinePhase.PRE_PROCESSING,
        "order": 4,
        "is_checkpoint": False,
        "requires_user_input": False,
        "model": None,
        "can_resume_from": True,
    },
    PipelineStage.ENTITY_MAPPING: {
        "name": "Entity Mapping",
        "description": "Map all entities to target, detect relationships",
        "phase": PipelinePhase.PRE_PROCESSING,
        "order": 5,
        "is_checkpoint": False,
        "requires_user_input": False,
        "model": "haiku",
        "can_resume_from": True,
    },
    PipelineStage.CHECKPOINT_B_ENTITY_CONFIRM: {
        "name": "Checkpoint B: Entity Confirmation",
        "description": "Confirm/correct entity relationships",
        "phase": PipelinePhase.PRE_PROCESSING,
        "order": 6,
        "is_checkpoint": True,
        "requires_user_input": True,
        "model": None,
        "can_resume_from": True,
    },
    PipelineStage.MATERIALITY_THRESHOLDS: {
        "name": "Materiality Thresholds",
        "description": "Set thresholds based on transaction value",
        "phase": PipelinePhase.PROCESSING,
        "order": 7,
        "is_checkpoint": False,
        "requires_user_input": False,
        "model": None,
        "can_resume_from": True,
    },
    PipelineStage.PASS_1_EXTRACT: {
        "name": "Pass 1: Extract",
        "description": "Extract structured data and document references",
        "phase": PipelinePhase.PROCESSING,
        "order": 8,
        "is_checkpoint": False,
        "requires_user_input": False,
        "model": "haiku",
        "can_resume_from": True,
    },
    PipelineStage.PASS_2_ANALYZE: {
        "name": "Pass 2: Analyze",
        "description": "Analyze risks and answer Blueprint Q&A",
        "phase": PipelinePhase.PROCESSING,
        "order": 9,
        "is_checkpoint": False,
        "requires_user_input": False,
        "model": "sonnet",
        "can_resume_from": True,
    },
    PipelineStage.CHECKPOINT_C_VALIDATION: {
        "name": "Checkpoint C: Validation",
        "description": "Validate understanding and financials",
        "phase": PipelinePhase.PROCESSING,
        "order": 10,
        "is_checkpoint": True,
        "requires_user_input": True,
        "model": None,
        "can_resume_from": True,
    },
    PipelineStage.PASS_3_CALCULATE: {
        "name": "Pass 3: Calculate",
        "description": "Compute financial exposures",
        "phase": PipelinePhase.PROCESSING,
        "order": 11,
        "is_checkpoint": False,
        "requires_user_input": False,
        "model": "python",
        "can_resume_from": True,
    },
    PipelineStage.PASS_4_CROSS_DOC: {
        "name": "Pass 4: Cross-Document",
        "description": "Detect conflicts and analyze missing documents",
        "phase": PipelinePhase.PROCESSING,
        "order": 12,
        "is_checkpoint": False,
        "requires_user_input": False,
        "model": "opus",  # ALWAYS Opus
        "can_resume_from": True,
    },
    PipelineStage.PASS_5_AGGREGATE: {
        "name": "Pass 5: Aggregate",
        "description": "Combine and summarize calculations",
        "phase": PipelinePhase.PROCESSING,
        "order": 13,
        "is_checkpoint": False,
        "requires_user_input": False,
        "model": "python",
        "can_resume_from": True,
    },
    PipelineStage.PASS_6_SYNTHESIZE: {
        "name": "Pass 6: Synthesize",
        "description": "Generate executive summary and W&I schedule",
        "phase": PipelinePhase.PROCESSING,
        "order": 14,
        "is_checkpoint": False,
        "requires_user_input": False,
        "model": "sonnet",
        "can_resume_from": True,
    },
    PipelineStage.PASS_7_VERIFY: {
        "name": "Pass 7: Verify",
        "description": "Final quality control",
        "phase": PipelinePhase.PROCESSING,
        "order": 15,
        "is_checkpoint": False,
        "requires_user_input": False,
        "model": "opus",  # ALWAYS Opus
        "can_resume_from": True,
    },
    PipelineStage.STORE_DISPLAY: {
        "name": "Store & Display",
        "description": "Save Report V1 and display in Findings Explorer",
        "phase": PipelinePhase.POST_PROCESSING,
        "order": 16,
        "is_checkpoint": False,
        "requires_user_input": False,
        "model": None,
        "can_resume_from": False,
    },
    PipelineStage.REFINEMENT_LOOP: {
        "name": "Refinement Loop",
        "description": "Refine report via Ask AI",
        "phase": PipelinePhase.POST_PROCESSING,
        "order": 17,
        "is_checkpoint": False,
        "requires_user_input": True,
        "model": "sonnet",
        "can_resume_from": False,
    },
}


def get_stage_index(stage: PipelineStage) -> int:
    """Get the index (0-based) of a stage in the execution order."""
    try:
        return STAGE_ORDER.index(stage)
    except ValueError:
        return -1


def get_next_stage(current_stage: PipelineStage) -> PipelineStage | None:
    """Get the next stage after the current one, or None if at the end."""
    idx = get_stage_index(current_stage)
    if idx < 0 or idx >= len(STAGE_ORDER) - 1:
        return None
    return STAGE_ORDER[idx + 1]


def get_previous_stage(current_stage: PipelineStage) -> PipelineStage | None:
    """Get the previous stage before the current one, or None if at the start."""
    idx = get_stage_index(current_stage)
    if idx <= 0:
        return None
    return STAGE_ORDER[idx - 1]


def is_stage_before(stage_a: PipelineStage, stage_b: PipelineStage) -> bool:
    """Check if stage_a comes before stage_b in the execution order."""
    return get_stage_index(stage_a) < get_stage_index(stage_b)


def get_stages_in_phase(phase: PipelinePhase) -> List[PipelineStage]:
    """Get all stages that belong to a specific phase."""
    return [
        stage for stage, meta in STAGE_METADATA.items()
        if meta.get("phase") == phase
    ]


def get_checkpoint_stages() -> List[PipelineStage]:
    """Get all checkpoint stages that require user input."""
    return [
        stage for stage, meta in STAGE_METADATA.items()
        if meta.get("is_checkpoint", False)
    ]


def get_resumable_stages() -> List[PipelineStage]:
    """Get all stages that can be resumed from."""
    return [
        stage for stage, meta in STAGE_METADATA.items()
        if meta.get("can_resume_from", False)
    ]


def calculate_overall_progress(completed_stages: List[PipelineStage]) -> int:
    """
    Calculate overall pipeline progress as a percentage (0-100).
    Based on the number of completed stages out of total stages.
    """
    if not completed_stages:
        return 0

    # Exclude terminal states from total count
    total_stages = len([s for s in STAGE_ORDER if s not in (PipelineStage.COMPLETED, PipelineStage.FAILED)])
    completed_count = len([s for s in completed_stages if s in STAGE_ORDER])

    return min(100, int((completed_count / total_stages) * 100))
