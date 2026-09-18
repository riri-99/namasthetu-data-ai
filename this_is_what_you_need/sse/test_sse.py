"""
SSE (Semantic Search Engine) — Automated Unit Tests.
"""

import unittest
from this_is_what_you_need.common import PrismaFurnishingStatus, PrismaPropertyType
from this_is_what_you_need.sse.pipeline import (
    FourteenFilterCriteria,
    PipSearchDocument,
    QueryIntent,
    SsePipeline,
    sse_pipeline,
)


class TestSsePipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = SsePipeline()
        self.doc = PipSearchDocument(
            property_id="prop_01",
            listing_id="list_01",
            public_id="pip_01",
            title="3 BHK Luxury Apartment in Whitefield",
            description="Beautiful apartment near metro with clear title and zero seepage.",
            locality="Whitefield",
            city="Bengaluru",
            carpet_area_sqft=1600.0,
            super_built_up_area_sqft=2000.0,
            listing_price_minor=1500000000,
            bhk_count=3,
            property_type=PrismaPropertyType.APARTMENT,
            furnishing=PrismaFurnishingStatus.SEMI_FURNISHED,
            inspection_score_overall=94,
            seepage_detected=False,
            deed_verified=True,
            active_liens=False,
            market_position="BELOW_MARKET",
            gross_rental_yield_pct=4.8,
        )
        self.pipeline.index_pip_document(self.doc)

    def test_01_filter_evaluation(self):
        filters = FourteenFilterCriteria(locality="Whitefield", bhk_counts=[3], verified_only=True)
        self.assertTrue(self.pipeline.evaluate_14_filters(self.doc, filters))

        fail_filters = FourteenFilterCriteria(locality="Indiranagar")
        self.assertFalse(self.pipeline.evaluate_14_filters(self.doc, fail_filters))

    def test_02_hybrid_search_and_latency(self):
        res = self.pipeline.search("3 BHK luxury Whitefield")
        self.assertLess(res.total_latency_ms, 80.0)  # P95 <80ms
        self.assertEqual(res.total_hits, 1)
        self.assertEqual(res.items[0].property_id, "prop_01")
        self.assertIn("Below fair market valuation (VIE)", res.items[0].match_reasons)

    def test_03_autocomplete(self):
        sugg = self.pipeline.autocomplete("white")
        self.assertGreaterEqual(len(sugg), 1)
        self.assertEqual(sugg[0]["category"], "LOCALITY")

        chunk = self.pipeline.autocomplete_stream_chunk("white")
        self.assertIn("autocomplete_suggestion", chunk)


if __name__ == "__main__":
    unittest.main()
