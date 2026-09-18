"""
SSE (Semantic Search Engine) — Core Pipeline Orchestrator.

Orchestrates:
1. Serving Path (Query time, <80ms P95 latency target §1):
   - Query Handler (CQRS read path §2a)
   - Parallel Hybrid Retrieval (Lexical GIN leg + Semantic pgvector leg)
   - Edge Rerank (Cloudflare Workers / ONNX pattern, sub-30ms)
   - Event emission (SearchExecuted, PropertyViewed)
2. Autocomplete Type-Ahead Path (<80ms debounced, delivered via SSE-transport §11.3)
3. Indexing Path (Nightly batch & incremental PIP updates §2b):
   - Dense embeddings computation (OpenAI text-embedding-3-small via AI Gateway)
   - GIN inverted index refresh
   - SavedSearch re-evaluation & alert dispatch (SavedSearchAlertFired)
4. Cross-Pipeline Ingestion:
   - PAM: condition scores & seepage flag updates
   - DEE: deed verification & active lien flags
   - VIE: valuation estimates, market position, and rental yields
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from sse.models import (
    AutocompleteResult,
    FourteenFilterCriteria,
    PipSearchDocument,
    PropertyViewedEvent,
    QueryIntent,
    RerankStrategy,
    SavedSearchAlertFiredEvent,
    SearchExecutedEvent,
    SearchResultItem,
    SseSearchQuery,
    SseSearchResult,
)
from sse.embedding_engine import EmbeddingEngine, embedding_engine
from sse.lexical_engine import LexicalEngine, lexical_engine
from sse.reranker import EdgeReranker, edge_reranker
from sse.autocomplete import AutocompleteEngine, autocomplete_engine
from sse.saved_searches import SavedSearchManager, saved_search_manager


class SsePipeline:
    """End-to-end Semantic Search Engine Orchestrator."""

    def __init__(
        self,
        embedder: Optional[EmbeddingEngine] = None,
        lexical: Optional[LexicalEngine] = None,
        rerank_engine: Optional[EdgeReranker] = None,
        autocomplete: Optional[AutocompleteEngine] = None,
        saved_searches: Optional[SavedSearchManager] = None,
    ):
        self.embedder = embedder or embedding_engine
        self.lexical = lexical or lexical_engine
        self.reranker = rerank_engine or edge_reranker
        self.autocomplete_engine = autocomplete or autocomplete_engine
        self.saved_searches = saved_searches or saved_search_manager

        # In-memory primary document repository (simulating Postgres Aurora projection)
        self._doc_corpus: Dict[str, PipSearchDocument] = {}
        # Hot PIP cache (simulating Valkey cache §2a)
        self._hot_query_cache: Dict[str, SseSearchResult] = {}

        # Event Bus Listeners
        self.search_executed_subscribers: List[Callable[[SearchExecutedEvent], None]] = []
        self.property_viewed_subscribers: List[Callable[[PropertyViewedEvent], None]] = []

    def subscribe_search_executed(self, callback: Callable[[SearchExecutedEvent], None]):
        """Subscribes an event listener to the SearchExecuted stream."""
        self.search_executed_subscribers.append(callback)

    def subscribe_property_viewed(self, callback: Callable[[PropertyViewedEvent], None]):
        """Subscribes an event listener to the PropertyViewed stream."""
        self.property_viewed_subscribers.append(callback)

    def search(self, query: Union[str, SseSearchQuery]) -> SseSearchResult:
        """
        Executes hybrid search query with strict <80ms P95 latency target.
        """
        total_start = time.perf_counter()

        # Normalize query model
        q_obj: SseSearchQuery
        if isinstance(query, str):
            q_obj = SseSearchQuery(raw_query=query)
        else:
            q_obj = query

        raw_q = q_obj.raw_query.strip()

        # Cache check for hot queries (Valkey layer §2a)
        cache_key = f"{raw_q}_{q_obj.filters.model_dump_json() if q_obj.filters else ''}_{q_obj.sort_by}_{q_obj.page}"
        if cache_key in self._hot_query_cache:
            cached = self._hot_query_cache[cache_key].model_copy(
                update={"cache_hit": True, "total_latency_ms": 0.5}
            )
            return cached

        # 1. Lexical Retrieval Leg (GIN full-text + 14-filter structured matching)
        lex_start = time.perf_counter()
        lexical_candidates = self.lexical.search_lexical(
            query_text=raw_q,
            filters=q_obj.filters,
            candidate_docs=list(self._doc_corpus.values()),
        )
        lex_latency = round((time.perf_counter() - lex_start) * 1000.0, 3)

        # 2. Semantic Retrieval Leg (pgvector cosine similarity)
        sem_start = time.perf_counter()
        semantic_candidates: List[Tuple[PipSearchDocument, float]] = []

        if raw_q:
            q_vec = self.embedder.get_embedding(raw_q)
            # Evaluate semantic similarity on candidates that pass the 14 filters
            surviving_docs = [
                doc for doc in self._doc_corpus.values()
                if self.lexical.evaluate_14_filters(doc, q_obj.filters)
            ]
            for doc in surviving_docs:
                if doc.embedding is None:
                    # Compute on demand if not pre-embedded
                    doc.embedding = self.embedder.get_embedding(doc.build_embeddable_corpus())
                sim = self.embedder.cosine_similarity(q_vec, doc.embedding)
                # Filter out negative or negligible similarities
                if sim > 0.05:
                    semantic_candidates.append((doc, round(sim, 4)))

            semantic_candidates.sort(key=lambda x: x[1], reverse=True)

        sem_latency = round((time.perf_counter() - sem_start) * 1000.0, 3)

        # 3. Edge Rerank & Score Fusion (<30ms Edge pass)
        rerank_start = time.perf_counter()
        ranked_items, intent, w_lex, w_sem, rerank_latency = self.reranker.rerank(
            query_text=raw_q,
            lexical_results=lexical_candidates,
            semantic_results=semantic_candidates,
            strategy=q_obj.rerank_strategy,
            top_k=q_obj.page_size * q_obj.page,
        )

        # 4. Sorting Overrides
        if q_obj.sort_by == "price_asc":
            ranked_items.sort(key=lambda x: x.price_minor)
        elif q_obj.sort_by == "price_desc":
            ranked_items.sort(key=lambda x: x.price_minor, reverse=True)
        elif q_obj.sort_by == "yield_desc":
            ranked_items.sort(key=lambda x: x.rental_yield_pct or 0.0, reverse=True)

        # Pagination
        start_idx = (q_obj.page - 1) * q_obj.page_size
        end_idx = start_idx + q_obj.page_size
        paginated_items = ranked_items[start_idx:end_idx]

        total_latency = round((time.perf_counter() - total_start) * 1000.0, 2)

        result = SseSearchResult(
            query=raw_q,
            query_intent=intent,
            total_hits=len(ranked_items),
            page=q_obj.page,
            page_size=q_obj.page_size,
            items=paginated_items,
            lexical_weight=w_lex,
            semantic_weight=w_sem,
            retrieval_latency_ms=round(lex_latency + sem_latency, 2),
            lexical_latency_ms=lex_latency,
            semantic_latency_ms=sem_latency,
            rerank_latency_ms=rerank_latency,
            total_latency_ms=total_latency,
            cache_hit=False,
            timestamp=datetime.now(timezone.utc),
        )

        # Store in hot query cache
        if len(self._hot_query_cache) < 500:
            self._hot_query_cache[cache_key] = result

        # 5. Emit SearchExecuted Event
        self._emit_search_executed(result, user_id=q_obj.user_id)

        return result

    def autocomplete(self, prefix: str, max_results: int = 8) -> AutocompleteResult:
        """Type-ahead autocomplete debounced under <80ms (§2a)."""
        return self.autocomplete_engine.suggest(prefix, max_results=max_results)

    def autocomplete_stream_chunk(self, prefix: str, max_results: int = 8) -> str:
        """Autocomplete result formatted as Server-Sent Events HTTP wire format chunk (§11.3)."""
        return self.autocomplete_engine.format_sse_transport(prefix, max_results=max_results)

    def index_pip_document(self, doc: PipSearchDocument):
        """
        Indexes or updates a PIP document across all search representations:
        1. Compute 1536-d embedding vector
        2. Index in lexical GIN engine
        3. Extract autocomplete entities
        4. Evaluate against active saved searches -> emit SavedSearchAlertFiredEvent
        """
        # 1. Embeddings lifecycle (§2b)
        corpus_text = doc.build_embeddable_corpus()
        doc.embedding = self.embedder.get_embedding(corpus_text)
        doc.embedded_at = datetime.now(timezone.utc)

        # 2. Store in primary corpus
        self._doc_corpus[doc.property_id] = doc

        # 3. Lexical index
        self.lexical.index_document(doc)

        # 4. Autocomplete index
        self.autocomplete_engine.register_property_doc(doc)

        # 5. Saved search matching & alert dispatch (§2a & §4)
        self.saved_searches.evaluate_new_listing(doc)

        # Invalidate query cache
        self._hot_query_cache.clear()

    def batch_index(self, docs: List[PipSearchDocument]):
        """Batch index for nightly scheduled embeddings refresh or cold-start indexing."""
        for d in docs:
            self.index_pip_document(d)

    def record_property_view(self, property_id: str, query: str, rank: int, user_id: Optional[str] = None):
        """Emits PropertyViewed event upon buyer click-through."""
        event = PropertyViewedEvent(
            event_id=f"evt_pv_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            property_id=property_id,
            query=query,
            result_rank=rank,
            timestamp=datetime.now(timezone.utc),
        )
        for sub in self.property_viewed_subscribers:
            try:
                sub(event)
            except Exception:
                pass

    # ========================================================================
    # Cross-Pipeline Event Ingestion (PAM, DEE, VIE)
    # ========================================================================

    def handle_pam_inspection_completed(
        self,
        property_id: str,
        inspection_id: str,
        score_overall: int,
        score_structural: int,
        seepage_detected: bool,
    ):
        """
        Cross-Pipeline Trigger: PAM Inspection Completed.
        Updates physical condition scores and seepage flag, refreshing embeddings and search rank.
        """
        if property_id in self._doc_corpus:
            doc = self._doc_corpus[property_id]
            doc.inspection_id = inspection_id
            doc.inspection_score_overall = score_overall
            doc.inspection_score_structural = score_structural
            doc.seepage_detected = seepage_detected
            doc.inspected_at = datetime.now(timezone.utc)
            # Re-index to refresh embedding with new condition signal
            self.index_pip_document(doc)

    def handle_dee_document_verified(
        self,
        property_id: str,
        deed_verified: bool,
        active_liens: bool,
        rera_number: Optional[str] = None,
    ):
        """
        Cross-Pipeline Trigger: DEE Title Deed Verified.
        Updates legal encumbrance and title verification badges.
        """
        if property_id in self._doc_corpus:
            doc = self._doc_corpus[property_id]
            doc.deed_verified = deed_verified
            doc.active_liens = active_liens
            doc.rera_registration_number = rera_number
            # Re-index to refresh embedding with legal trust signals
            self.index_pip_document(doc)

    def handle_vie_valuation_published(
        self,
        property_id: str,
        estimate_minor: int,
        market_position: str,
        difference_pct: Optional[float],
        gross_yield_pct: Optional[float],
        demand_signal: Optional[str],
    ):
        """
        Cross-Pipeline Trigger: VIE Valuation Published.
        Incorporates valuation positioning and rental yield metrics for investor queries.
        """
        if property_id in self._doc_corpus:
            doc = self._doc_corpus[property_id]
            doc.avm_estimate_minor = estimate_minor
            doc.market_position = market_position
            doc.avm_difference_pct = difference_pct
            doc.gross_rental_yield_pct = gross_yield_pct
            doc.demand_signal = demand_signal
            # Re-index with new valuation data
            self.index_pip_document(doc)

    def _emit_search_executed(self, res: SseSearchResult, user_id: Optional[str]):
        """Dispatches SearchExecuted event to subscribers."""
        event = SearchExecutedEvent(
            event_id=f"evt_se_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            raw_query=res.query,
            query_intent=res.query_intent.value,
            hits_count=res.total_hits,
            top_property_ids=[item.property_id for item in res.items[:5]],
            latency_ms=res.total_latency_ms,
            timestamp=res.timestamp,
        )
        for sub in self.search_executed_subscribers:
            try:
                sub(event)
            except Exception:
                pass


sse_pipeline = SsePipeline()
