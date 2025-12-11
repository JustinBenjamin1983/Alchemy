"""
Prompt templates for each pass of the DD analysis.
"""

from .extraction import EXTRACTION_SYSTEM_PROMPT, build_extraction_prompt
from .analysis import ANALYSIS_SYSTEM_PROMPT, build_analysis_prompt
from .crossdoc import (
    CROSSDOC_SYSTEM_PROMPT,
    build_conflict_detection_prompt,
    build_cascade_mapping_prompt,
    build_authorization_check_prompt,
    build_consent_matrix_prompt,
)
from .synthesis import SYNTHESIS_SYSTEM_PROMPT, build_synthesis_prompt

__all__ = [
    "EXTRACTION_SYSTEM_PROMPT",
    "build_extraction_prompt",
    "ANALYSIS_SYSTEM_PROMPT",
    "build_analysis_prompt",
    "CROSSDOC_SYSTEM_PROMPT",
    "build_conflict_detection_prompt",
    "build_cascade_mapping_prompt",
    "build_authorization_check_prompt",
    "build_consent_matrix_prompt",
    "SYNTHESIS_SYSTEM_PROMPT",
    "build_synthesis_prompt",
]
