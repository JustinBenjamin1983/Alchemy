"""
Synthesis module for hierarchical finding aggregation.

Provides multi-level synthesis:
- Batch synthesis (within batch)
- Cluster synthesis (across batches)
- Cross-cluster synthesis (across clusters)
- Deal synthesis (executive summary)
"""

from .hierarchical_synthesizer import (
    SynthesisLevel,
    SynthesisResult,
    HierarchicalSynthesizer,
    SynthesisPipeline,
    create_synthesis_pipeline,
)

__all__ = [
    'SynthesisLevel',
    'SynthesisResult',
    'HierarchicalSynthesizer',
    'SynthesisPipeline',
    'create_synthesis_pipeline',
]
