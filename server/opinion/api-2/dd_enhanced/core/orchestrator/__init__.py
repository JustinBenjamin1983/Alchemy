"""
Parallel processing orchestrator for DD analysis.

Provides adaptive processing that auto-switches between
sequential and parallel modes based on document count.
"""

from .parallel_orchestrator import (
    ProcessingMode,
    OrchestratorConfig,
    ProcessingResult,
    ParallelOrchestrator,
    create_orchestrator,
)

__all__ = [
    'ProcessingMode',
    'OrchestratorConfig',
    'ProcessingResult',
    'ParallelOrchestrator',
    'create_orchestrator',
]
