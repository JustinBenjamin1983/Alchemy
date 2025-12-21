"""
Knowledge Graph module for Phase 5.

Provides entity extraction, graph building, and query capabilities
for DD document analysis at scale (300+ documents).
"""

from .entity_transformer import (
    EntityTransformer,
    GraphEntity,
    PartyEntity,
    AgreementEntity,
    ObligationEntity,
    TriggerEntity,
    AmountEntity,
    DateEntity,
)

from .graph_builder import KnowledgeGraphBuilder, GraphStats

from .graph_queries import GraphQueryEngine, QueryResult

from .relationship_enricher import RelationshipEnricher

__all__ = [
    # Transformer
    'EntityTransformer',
    'GraphEntity',
    'PartyEntity',
    'AgreementEntity',
    'ObligationEntity',
    'TriggerEntity',
    'AmountEntity',
    'DateEntity',
    # Builder
    'KnowledgeGraphBuilder',
    'GraphStats',
    # Queries
    'GraphQueryEngine',
    'QueryResult',
    # Enricher
    'RelationshipEnricher',
]
