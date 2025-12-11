"""
Core processing modules for DD Enhanced.
"""

from .claude_client import ClaudeClient, TokenUsage
from .document_loader import load_documents, LoadedDocument, get_reference_documents
from .pass1_extract import run_pass1_extraction
from .pass2_analyze import run_pass2_analysis
from .pass3_crossdoc import run_pass3_crossdoc_synthesis
from .pass4_synthesize import run_pass4_synthesis

__all__ = [
    "ClaudeClient",
    "TokenUsage",
    "load_documents",
    "LoadedDocument",
    "get_reference_documents",
    "run_pass1_extraction",
    "run_pass2_analysis",
    "run_pass3_crossdoc_synthesis",
    "run_pass4_synthesis",
]
