"""
SSE (Semantic Search Engine) Package.

Namasthetu · Embedded AI Service #4 · Discovery Bounded Context
"""

from pipelines.sse.models import (
    AutocompleteCategory,
    AutocompleteItem,
    AutocompleteResult,
    FourteenFilterCriteria,
    PipSearchDocument,
    PrismaFurnishingStatus,
    PrismaListingStatus,
    PrismaPropertyType,
    PropertyViewedEvent,
    QueryIntent,
    RerankStrategy,
    SavedSearchAlertFiredEvent,
    SearchExecutedEvent,
    SearchFeedbackSample,
    SearchResultItem,
    SsePerformanceMetrics,
    SseSearchQuery,
    SseSearchResult,
)
from pipelines.sse.embedding_engine import EmbeddingEngine, embedding_engine
from pipelines.sse.lexical_engine import LexicalEngine, lexical_engine
from pipelines.sse.reranker import EdgeReranker, edge_reranker
from pipelines.sse.autocomplete import AutocompleteEngine, autocomplete_engine
from pipelines.sse.saved_searches import SavedSearchManager, saved_search_manager
from pipelines.sse.feedback_loop import SseLearningLoop, sse_learning_loop
from pipelines.sse.dataset_manager import SseDatasetManager, sse_dataset_manager
from pipelines.sse.pipeline import SsePipeline, sse_pipeline

__all__ = [
    # Pipeline & Engines
    "sse_pipeline",
    "SsePipeline",
    "embedding_engine",
    "EmbeddingEngine",
    "lexical_engine",
    "LexicalEngine",
    "edge_reranker",
    "EdgeReranker",
    "autocomplete_engine",
    "AutocompleteEngine",
    "saved_search_manager",
    "SavedSearchManager",
    "sse_learning_loop",
    "SseLearningLoop",
    "sse_dataset_manager",
    "SseDatasetManager",
    # Enums
    "QueryIntent",
    "RerankStrategy",
    "AutocompleteCategory",
    "PrismaPropertyType",
    "PrismaFurnishingStatus",
    "PrismaListingStatus",
    # Domain Models
    "FourteenFilterCriteria",
    "PipSearchDocument",
    "SseSearchQuery",
    "SearchResultItem",
    "SseSearchResult",
    "AutocompleteItem",
    "AutocompleteResult",
    "SearchExecutedEvent",
    "SavedSearchAlertFiredEvent",
    "PropertyViewedEvent",
    "SearchFeedbackSample",
    "SsePerformanceMetrics",
]
