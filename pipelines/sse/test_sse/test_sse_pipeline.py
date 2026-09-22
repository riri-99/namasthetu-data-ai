"""
SSE (Semantic Search Engine) — Comprehensive Automated Unit Tests.

Covers:
1. Schema & enum alignment with src/db/schema.prisma (Property, Listing, SavedSearch)
2. Strict evaluation of the canonical 14-filter parameter set (§3 & §12.1)
3. 1536-dimensional vector embedding & pgvector serialization
4. Lexical GIN full-text index simulation & BM25 ranking
5. Query intent classification (Lexical, Semantic, Investor, Condition, Legal, Hybrid)
6. Edge rerank & query-aware score fusion (<30ms edge latency)
7. Cross-Pipeline integration with PAM: condition score & seepage impact on search ranking
8. Cross-Pipeline integration with DEE: deed verification & active lien impact on search ranking
9. Cross-Pipeline integration with VIE: below-market valuation & high rental yield boost
10. Autocomplete type-ahead & Server-Sent Events wire format chunk (§11.3)
11. SavedSearch registration, 14-filter matching, and SavedSearchAlertFiredEvent emission
12. End-to-end search execution satisfying the <80ms P95 latency SLA (§1)
13. Learning loop click-through tracking, MRR, CTR, and LTR training batch export
14. Hot query caching simulation (Valkey layer §2a)
15. Incremental event-driven PIP re-indexing (PAM/DEE/VIE trigger ingestion)
16. Benchmark evaluation runner on golden queries
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone, timedelta

from pipelines.sse.models import (
    AutocompleteCategory,
    FourteenFilterCriteria,
    PipSearchDocument,
    PrismaFurnishingStatus,
    PrismaListingStatus,
    PrismaPropertyType,
    QueryIntent,
    RerankStrategy,
    SavedSearchAlertFiredEvent,
    SearchExecutedEvent,
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
from pipelines.sse.train_and_eval import run_evaluation


class TestSsePipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = SsePipeline()
        self.embedder = embedding_engine
        self.lexical = lexical_engine
        self.reranker = edge_reranker

        # Create a sample PIP document
        self.doc_1 = PipSearchDocument(
            property_id="prop_test_01",
            listing_id="list_test_01",
            public_id="pip_pub_01",
            title="3 BHK Luxury Apartment in Whitefield",
            description="East facing spacious apartment near Hope Farm metro station.",
            locality="Whitefield",
            city="Bengaluru",
            society_name="Prestige Boulevard",
            builder_name="Prestige Group",
            property_type=PrismaPropertyType.APARTMENT,
            configuration="3BHK",
            bhk_count=3,
            bathrooms_count=3,
            carpet_area_sqft=1650.0,
            super_built_up_area_sqft=2000.0,
            floor_number=6,
            total_floors=14,
            age_years=2.0,
            furnishing=PrismaFurnishingStatus.SEMI_FURNISHED,
            parking_count=2,
            has_lift=True,
            amenities=["SWIMMING_POOL", "GYM", "CLUBHOUSE"],
            listing_price_minor=1500000000,  # 1.50 Cr
            status=PrismaListingStatus.ACTIVE,
            owner_type="INDIVIDUAL",
            # PAM signals
            inspection_id="insp_test_01",
            inspection_score_overall=94,
            inspection_score_structural=96,
            seepage_detected=False,
            inspected_at=datetime.now(timezone.utc) - timedelta(days=10),
            # DEE signals
            deed_verified=True,
            active_liens=False,
            # VIE signals
            avm_estimate_minor=1580000000,
            market_position="BELOW_MARKET",
            avm_difference_pct=-5.06,
            gross_rental_yield_pct=4.8,
            demand_signal="WARM",
        )

        self.doc_2 = PipSearchDocument(
            property_id="prop_test_02",
            listing_id="list_test_02",
            public_id="pip_pub_02",
            title="2 BHK Independent Villa in Indiranagar",
            description="Centrally located heritage villa with private garden.",
            locality="Indiranagar",
            city="Bengaluru",
            society_name="Defense Colony",
            builder_name="Independent",
            property_type=PrismaPropertyType.VILLA,
            configuration="2BHK",
            bhk_count=2,
            bathrooms_count=2,
            carpet_area_sqft=1200.0,
            super_built_up_area_sqft=1450.0,
            floor_number=1,
            total_floors=2,
            age_years=15.0,
            furnishing=PrismaFurnishingStatus.UNFURNISHED,
            parking_count=1,
            has_lift=False,
            amenities=["GARDEN", "SECURITY_24X7"],
            listing_price_minor=2800000000,  # 2.80 Cr
            status=PrismaListingStatus.ACTIVE,
            owner_type="INDIVIDUAL",
            # PAM signals
            inspection_id="insp_test_02",
            inspection_score_overall=68,
            inspection_score_structural=70,
            seepage_detected=True,  # Seepage defect!
            inspected_at=datetime.now(timezone.utc) - timedelta(days=40),
            # DEE signals
            deed_verified=False,
            active_liens=True,     # Financial lien!
            # VIE signals
            avm_estimate_minor=2600000000,
            market_position="ABOVE_MARKET",
            avm_difference_pct=7.69,
            gross_rental_yield_pct=3.1,
            demand_signal="HOT",
        )

    def test_01_schema_and_models_alignment(self):
        """Test enums and models alignment with schema.prisma and Discovery specs."""
        self.assertEqual(PrismaPropertyType.APARTMENT.value, "APARTMENT")
        self.assertEqual(PrismaPropertyType.VILLA.value, "VILLA")
        self.assertEqual(PrismaFurnishingStatus.SEMI_FURNISHED.value, "SEMI_FURNISHED")
        self.assertEqual(PrismaListingStatus.ACTIVE.value, "ACTIVE")

        self.assertEqual(QueryIntent.INVESTOR_YIELD.value, "INVESTOR_YIELD")
        self.assertEqual(QueryIntent.CONDITION_FOCUSED.value, "CONDITION_FOCUSED")
        self.assertEqual(QueryIntent.LEGAL_VERIFIED.value, "LEGAL_VERIFIED")

        # Test embeddable corpus generation
        corpus = self.doc_1.build_embeddable_corpus()
        self.assertIn("Whitefield", corpus)
        self.assertIn("1650.0 sqft", corpus)
        self.assertIn("zero seepage", corpus)
        self.assertIn("clear title", corpus)

    def test_02_14_filter_criteria_complete_evaluation(self):
        """Test strict evaluation of the 14-filter parameter set (§12.1)."""
        engine = LexicalEngine()

        # Matching filters for doc_1
        match_filters = FourteenFilterCriteria(
            min_price_minor=1000000000,
            max_price_minor=2000000000,
            min_area_sqft=1400.0,
            property_types=[PrismaPropertyType.APARTMENT],
            bhk_counts=[3],
            floor_min=2,
            floor_max=10,
            age_max_years=5.0,
            furnishing_statuses=[PrismaFurnishingStatus.SEMI_FURNISHED],
            parking_required=True,
            lift_required=True,
            amenities=["SWIMMING_POOL"],
            verified_only=True,
            no_seepage_only=True,
            clear_title_only=True,
            owner_types=["INDIVIDUAL"],
            locality="Whitefield",
            city="Bengaluru",
        )
        self.assertTrue(engine.evaluate_14_filters(self.doc_1, match_filters))

        # Should fail on doc_2 due to:
        # - property_type (VILLA vs APARTMENT)
        # - lift_required (has_lift=False)
        # - no_seepage_only (seepage_detected=True)
        # - clear_title_only (active_liens=True)
        self.assertFalse(engine.evaluate_14_filters(self.doc_2, match_filters))

    def test_03_embedding_generation_and_pgvector_serialization(self):
        """Test 1536-dimensional embedding, normalization, and pgvector format."""
        vec = self.embedder.get_embedding("3 BHK Luxury Apartment in Whitefield with clear title")
        self.assertEqual(len(vec), 1536)

        # L2 norm should equal ~1.0
        norm = sum(x * x for x in vec)
        self.assertAlmostEqual(norm, 1.0, places=3)

        # pgvector formatting string
        pg_str = self.embedder.to_pgvector_string(vec)
        self.assertTrue(pg_str.startswith("["))
        self.assertTrue(pg_str.endswith("]"))

        # Reconstructed from pgvector string
        parsed_vec = self.embedder.from_pgvector_string(pg_str)
        self.assertEqual(len(parsed_vec), 1536)
        self.assertAlmostEqual(parsed_vec[0], vec[0], places=5)

    def test_04_lexical_gin_bm25_retrieval(self):
        """Test lexical inverted index, term saturation, and locality boosting."""
        engine = LexicalEngine()
        engine.index_document(self.doc_1)
        engine.index_document(self.doc_2)

        # Search for "Whitefield"
        results = engine.search_lexical("Whitefield")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0].property_id, "prop_test_01")
        self.assertGreater(results[0][1], 0.3)

        # Search for "Indiranagar villa"
        results_villa = engine.search_lexical("Indiranagar villa")
        self.assertEqual(len(results_villa), 1)
        self.assertEqual(results_villa[0][0].property_id, "prop_test_02")

    def test_05_query_intent_classification(self):
        """Test query-aware intent classification (§6.1)."""
        reranker = EdgeReranker()

        # Investor yield query (VIE signal)
        intent_inv = reranker.detect_query_intent("high rental yield undervalued flat for investment")
        self.assertEqual(intent_inv, QueryIntent.INVESTOR_YIELD)

        # Condition query (PAM signal)
        intent_pam = reranker.detect_query_intent("well-maintained apartment with zero seepage")
        self.assertEqual(intent_pam, QueryIntent.CONDITION_FOCUSED)

        # Legal query (DEE signal)
        intent_dee = reranker.detect_query_intent("clear title RERA approved encumbrance-free home")
        self.assertEqual(intent_dee, QueryIntent.LEGAL_VERIFIED)

        # Lexical heavy
        intent_lex = reranker.detect_query_intent("3 bhk in whitefield 1500 sqft")
        self.assertEqual(intent_lex, QueryIntent.LEXICAL_HEAVY)

        # Semantic heavy
        intent_sem = reranker.detect_query_intent("peaceful quiet environment for family near green parks")
        self.assertEqual(intent_sem, QueryIntent.SEMANTIC_HEAVY)

    def test_06_edge_reranking_fusion_and_latency(self):
        """Test edge score fusion and verify sub-30ms latency target."""
        reranker = EdgeReranker()
        lex_results = [(self.doc_1, 0.85), (self.doc_2, 0.40)]
        sem_results = [(self.doc_1, 0.90), (self.doc_2, 0.35)]

        ranked_items, intent, w_lex, w_sem, latency = reranker.rerank(
            query_text="3 BHK Whitefield",
            lexical_results=lex_results,
            semantic_results=sem_results,
            strategy=RerankStrategy.QUERY_AWARE_HYBRID,
        )

        self.assertLess(latency, 30.0)  # Sub-30ms edge requirement
        self.assertEqual(len(ranked_items), 2)
        self.assertEqual(ranked_items[0].property_id, "prop_test_01")
        self.assertEqual(ranked_items[0].rank, 1)
        self.assertGreater(ranked_items[0].final_score, ranked_items[1].final_score)

    def test_07_cross_pipeline_pam_inspection_impact(self):
        """Cross-Pipeline PAM: Pristine condition boosted, seepage penalized."""
        reranker = EdgeReranker()
        # Equal base scores
        lex_results = [(self.doc_1, 0.50), (self.doc_2, 0.50)]
        sem_results = [(self.doc_1, 0.50), (self.doc_2, 0.50)]

        ranked_items, _, _, _, _ = reranker.rerank(
            query_text="well-maintained home with good condition",
            lexical_results=lex_results,
            semantic_results=sem_results,
        )

        # doc_1 (PAM condition 94, no seepage) should rank above doc_2 (PAM condition 68, seepage)
        self.assertEqual(ranked_items[0].property_id, "prop_test_01")
        self.assertIn("PAM Inspected: 94/100", ranked_items[0].verified_badges)
        self.assertIn("Zero dampness or seepage verified by PAM", ranked_items[0].match_reasons)

    def test_08_cross_pipeline_dee_legal_title_impact(self):
        """Cross-Pipeline DEE: Title verification boosted, active liens penalized."""
        reranker = EdgeReranker()
        lex_results = [(self.doc_1, 0.50), (self.doc_2, 0.50)]
        sem_results = [(self.doc_1, 0.50), (self.doc_2, 0.50)]

        ranked_items, _, _, _, _ = reranker.rerank(
            query_text="clear title encumbrance-free flat",
            lexical_results=lex_results,
            semantic_results=sem_results,
        )

        # doc_1 (DEE verified deed, no liens) should rank strictly higher than doc_2 (unverified, active liens)
        self.assertEqual(ranked_items[0].property_id, "prop_test_01")
        self.assertIn("DEE Title Verified", ranked_items[0].verified_badges)
        self.assertIn("Clear Encumbrance", ranked_items[0].verified_badges)

    def test_09_cross_pipeline_vie_valuation_and_yield_impact(self):
        """Cross-Pipeline VIE: Below-market valuation & high rental yield boost."""
        reranker = EdgeReranker()
        lex_results = [(self.doc_1, 0.50), (self.doc_2, 0.50)]
        sem_results = [(self.doc_1, 0.50), (self.doc_2, 0.50)]

        ranked_items, _, _, _, _ = reranker.rerank(
            query_text="high rental yield undervalued apartment for investment",
            lexical_results=lex_results,
            semantic_results=sem_results,
        )

        # doc_1 has market_position = "BELOW_MARKET" and yield = 4.8%
        self.assertEqual(ranked_items[0].property_id, "prop_test_01")
        self.assertTrue(any("fair market valuation (VIE)" in r for r in ranked_items[0].match_reasons))
        self.assertTrue(any("High rental yield" in r for r in ranked_items[0].match_reasons))

    def test_10_autocomplete_typeahead_and_sse_transport(self):
        """Test debounced <80ms autocomplete and SSE-transport wire chunks (§11.3)."""
        ac = AutocompleteEngine()
        ac.clear()
        ac.register_property_doc(self.doc_1)
        ac.register_property_doc(self.doc_2)

        # Suggest for "white"
        res = ac.suggest("white")
        self.assertLess(res.latency_ms, 80.0)
        self.assertGreaterEqual(len(res.suggestions), 1)
        self.assertEqual(res.suggestions[0].category, AutocompleteCategory.LOCALITY)
        self.assertIn("Whitefield", res.suggestions[0].text)

        # Wire chunk format test (Server-Sent Events transport §11.3)
        wire_chunk = ac.format_sse_transport("white")
        self.assertTrue(wire_chunk.startswith("id: "))
        self.assertIn("event: autocomplete_suggestion\n", wire_chunk)
        self.assertIn("data: {", wire_chunk)

    def test_11_saved_searches_and_alert_emission(self):
        """Test SavedSearch 14-filter matching and SavedSearchAlertFiredEvent emission."""
        sm = SavedSearchManager()
        sm.clear()
        fired_alerts: List[SavedSearchAlertFiredEvent] = []
        sm.subscribe_alerts(lambda ev: fired_alerts.append(ev))

        # Register a saved search for a buyer looking for 3BHK in Whitefield under 2 Cr
        filters = FourteenFilterCriteria(
            locality="Whitefield",
            bhk_counts=[3],
            max_price_minor=2000000000,
            parking_required=True,
        )
        record = sm.register_saved_search(
            user_id="user_buyer_101",
            name="My Whitefield 3BHK Search",
            filters=filters,
            alerts_enabled=True,
        )
        self.assertEqual(record["userId"], "user_buyer_101")
        self.assertIn("filtersJson", record)

        # Evaluate against doc_1 (matches)
        alerts_1 = sm.evaluate_new_listing(self.doc_1)
        self.assertEqual(len(alerts_1), 1)
        self.assertEqual(alerts_1[0].user_id, "user_buyer_101")
        self.assertEqual(alerts_1[0].matching_property_id, "prop_test_01")
        self.assertEqual(len(fired_alerts), 1)

        # Evaluate against doc_2 (does NOT match - Indiranagar 2BHK)
        alerts_2 = sm.evaluate_new_listing(self.doc_2)
        self.assertEqual(len(alerts_2), 0)

    def test_12_search_pipeline_e2e_and_latency_budget(self):
        """Test complete hybrid search execution satisfying the <80ms P95 latency budget."""
        pipe = SsePipeline()
        pipe.index_pip_document(self.doc_1)
        pipe.index_pip_document(self.doc_2)

        executed_events: List[SearchExecutedEvent] = []
        pipe.subscribe_search_executed(lambda ev: executed_events.append(ev))

        # Run query
        res = pipe.search(SseSearchQuery(raw_query="3 BHK Whitefield luxury apartment"))
        self.assertLess(res.total_latency_ms, 80.0)  # P95 target <80ms
        self.assertGreaterEqual(res.total_hits, 1)
        self.assertEqual(res.items[0].property_id, "prop_test_01")
        self.assertEqual(len(executed_events), 1)
        self.assertEqual(executed_events[0].raw_query, "3 BHK Whitefield luxury apartment")

    def test_13_click_through_and_learning_loop(self):
        """Test user click-through event, MRR, and LTR training export."""
        loop = SseLearningLoop()
        loop.clear()

        # Record search click
        sample = loop.record_search_interaction(
            query="3 BHK Whitefield",
            query_intent="LEXICAL_HEAVY",
            returned_property_ids=["prop_test_01", "prop_test_02"],
            clicked_property_id="prop_test_01",
            clicked_rank=1,
            dwell_time_seconds=45.0,
            converted_to_inquiry=True,
        )
        self.assertEqual(sample.clicked_property_id, "prop_test_01")

        metrics = loop.get_metrics()
        self.assertEqual(metrics.total_searches, 1)
        self.assertEqual(metrics.click_through_rate, 100.0)
        self.assertEqual(metrics.mean_reciprocal_rank, 1.0)

        # Export LTR training batch
        batch = loop.export_ltr_training_batch()
        self.assertEqual(len(batch), 1)
        self.assertEqual(batch[0]["clicked_property_id"], "prop_test_01")

    def test_14_caching_and_valkey_hot_pip_layer(self):
        """Test hot query cache provides sub-1ms responses (§2a)."""
        pipe = SsePipeline()
        pipe.index_pip_document(self.doc_1)

        # First run (computes and caches)
        res1 = pipe.search("3 BHK in Whitefield")
        # Second run (cache hit)
        res2 = pipe.search("3 BHK in Whitefield")
        self.assertTrue(res2.cache_hit)
        self.assertLessEqual(res2.total_latency_ms, 2.0)

    def test_15_dynamic_event_updates(self):
        """Test event-driven PIP re-indexing from PAM, DEE, and VIE."""
        pipe = SsePipeline()
        pipe.index_pip_document(self.doc_1)

        # Ingest PAM inspection update: structural score drops and seepage detected
        pipe.handle_pam_inspection_completed(
            property_id="prop_test_01",
            inspection_id="insp_new_99",
            score_overall=65,
            score_structural=60,
            seepage_detected=True,
        )
        updated_doc = pipe._doc_corpus["prop_test_01"]
        self.assertEqual(updated_doc.inspection_score_overall, 65)
        self.assertTrue(updated_doc.seepage_detected)

        # Ingest DEE legal update: lien flagged
        pipe.handle_dee_document_verified(
            property_id="prop_test_01",
            deed_verified=False,
            active_liens=True,
        )
        self.assertTrue(pipe._doc_corpus["prop_test_01"].active_liens)

        # Ingest VIE valuation update
        pipe.handle_vie_valuation_published(
            property_id="prop_test_01",
            estimate_minor=1650000000,
            market_position="ALIGNED",
            difference_pct=0.0,
            gross_yield_pct=5.2,
            demand_signal="HOT",
        )
        self.assertEqual(pipe._doc_corpus["prop_test_01"].gross_rental_yield_pct, 5.2)

    def test_16_benchmark_evaluation_runner(self):
        """Test evaluation CLI runner on golden queries against benchmark corpus."""
        eval_res = run_evaluation(corpus_size=25, seed=99)
        self.assertEqual(eval_res["status"], "PASSED")
        self.assertLess(eval_res["p95_latency_ms"], 80.0)
        self.assertEqual(eval_res["zero_hits"], 0)


if __name__ == "__main__":
    unittest.main()
