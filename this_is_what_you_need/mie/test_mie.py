"""
MIE (Market Intelligence Engine) — Automated Unit Tests.

Covers:
1. Prisma schema enum compliance (MarketScope, MarketMetric, MarketPeriod, ListingMode, AreaBasis, DemandSignal)
2. Inquiry density scoring & sigmoidal normalization
3. Transaction velocity & DOM turnover speed
4. Neighbourhood growth & civic infrastructure scoring
5. Demand signal (HOT/WARM/COLD) and market risk index
6. 1:1 Serialization to Prisma model MarketRate
7. Direct integration with VIE 13-feature LightGBM model
8. Locality ranking in city (Square Yards parity)
9. Event bus pub-sub dispatching
10. In-memory dataset lifecycle & calibration cleanup
"""

import os
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Ensure repo root is on sys.path
repo_root = str(Path(__file__).resolve().parent.parent.parent)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from this_is_what_you_need.mie.pipeline import (
    AreaBasis,
    CivicProximityRecord,
    DemandSignal,
    InquiryDensityAnalyzer,
    ListingMode,
    LocalityRanker,
    MarketMetric,
    MarketPeriod,
    MarketRiskAnalyzer,
    MarketScope,
    MiePipeline,
    NeighbourhoodGrowthAnalyzer,
    PriceTrendDirection,
    RawInquiryRecord,
    RawListingRecord,
    RawTransactionRecord,
    TransactionVelocityAnalyzer,
    mie_pipeline,
)
from this_is_what_you_need.mie.train_and_eval import MieDatasetManager
from this_is_what_you_need.vie.pipeline import vie_pipeline


class TestMiePipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = MiePipeline()

    def test_01_prisma_enums_alignment(self):
        """Verify all MarketScope, MarketMetric, MarketPeriod, ListingMode, AreaBasis match schema.prisma."""
        # MarketScope (lines 503-507)
        self.assertEqual({"CITY", "LOCALITY", "SOCIETY"}, {e.value for e in MarketScope})
        # MarketMetric (lines 509-514)
        self.assertEqual(
            {"ASKING_RATE_PER_SQFT", "REGISTERED_RATE_PER_SQFT", "MONTHLY_RENT"},
            {e.value for e in MarketMetric},
        )
        # MarketPeriod (lines 515-518)
        self.assertEqual({"MONTH", "QUARTER"}, {e.value for e in MarketPeriod})
        # ListingMode (lines 352-355)
        self.assertEqual({"BUY", "RENT"}, {e.value for e in ListingMode})
        # AreaBasis (lines 520-525)
        self.assertEqual({"CARPET", "BUILT_UP", "SUPER_BUILT_UP"}, {e.value for e in AreaBasis})
        # DemandSignal (VIE & SSE alignment)
        self.assertEqual({"COLD", "WARM", "HOT"}, {e.value for e in DemandSignal})

    def test_02_inquiry_density_and_velocity_scoring(self):
        """Test inquiry density and transaction velocity formulas."""
        # 10 inquiries on 2 active listings (5.0 inq/listing vs 3.5 target) -> high density > 70
        high_density = InquiryDensityAnalyzer.compute_score(
            inquiry_count_30d=10,
            active_listings_count=2,
            target_inquiries_per_listing=3.5,
        )
        self.assertGreater(high_density, 70.0)

        # 1 inquiry on 10 active listings (0.1 inq/listing) -> low density < 30
        low_density = InquiryDensityAnalyzer.compute_score(
            inquiry_count_30d=1,
            active_listings_count=10,
            target_inquiries_per_listing=3.5,
        )
        self.assertLess(low_density, 30.0)

        # High transaction volume with fast turnover (DOM=25 days vs 60 days target) -> velocity > 75
        high_vel, _ = TransactionVelocityAnalyzer.compute_score(
            deals_count_90d=24,
            median_dom_days=25.0,
            target_deals_90d=15,
            target_dom_days=60.0,
        )
        self.assertGreater(high_vel, 75.0)

    def test_03_neighbourhood_growth_scoring(self):
        """Test transit proximity and environmental scoring for Feature #13."""
        civic_high = CivicProximityRecord(
            metro_distance_meters=800,  # Walking distance
            airport_distance_meters=22000,
            water_security_index=90,
            flood_drainage_index=90,
            green_canopy_percent=35,
        )
        growth_high = NeighbourhoodGrowthAnalyzer.compute_score(civic_high, historical_appreciation_pct=8.5)
        self.assertGreater(growth_high, 75.0)

        civic_low = CivicProximityRecord(
            metro_distance_meters=7500,  # Distant metro
            airport_distance_meters=55000,
            water_security_index=55,
            flood_drainage_index=60,
            green_canopy_percent=10,
        )
        growth_low = NeighbourhoodGrowthAnalyzer.compute_score(civic_low, historical_appreciation_pct=4.0)
        self.assertLess(growth_low, 55.0)

    def test_04_demand_signal_and_market_risk(self):
        """Test HOT/COLD demand signals and market risk computation."""
        # Low inventory, high velocity, stable prices -> low market risk (<30)
        healthy_risk = MarketRiskAnalyzer.compute_market_risk(
            inventory_months=2.5,
            price_cv=0.12,
            velocity_score=85.0,
            quarterly_growth_pct=2.1,
        )
        self.assertLess(healthy_risk, 30)

        # High inventory overhang, sluggish velocity, price drops -> high market risk (>60)
        stagnant_risk = MarketRiskAnalyzer.compute_market_risk(
            inventory_months=14.5,
            price_cv=0.35,
            velocity_score=25.0,
            quarterly_growth_pct=-2.5,
        )
        self.assertGreater(stagnant_risk, 60)

    def test_05_prisma_market_rates_export(self):
        """Test strict 1:1 mapping to model MarketRate in schema.prisma."""
        # Ingest a transaction
        tx = RawTransactionRecord(
            locality="Whitefield",
            city="Bengaluru",
            registration_date=date(2026, 4, 15),
            area_sqft=1500.0,
            consideration_minor=1425000000,  # Rs 1.425 Cr (9500 / sqft)
        )
        rate_rec = self.pipeline.ingest_transaction(tx)
        prisma_row = rate_rec.to_prisma_dict()

        self.assertEqual(prisma_row["scope"], "LOCALITY")
        self.assertIn("whitefield", prisma_row["scopeKey"].lower())
        self.assertEqual(prisma_row["city"], "Bengaluru")
        self.assertEqual(prisma_row["listingMode"], "BUY")
        self.assertEqual(prisma_row["metric"], "REGISTERED_RATE_PER_SQFT")
        self.assertEqual(prisma_row["periodType"], "QUARTER")
        self.assertEqual(prisma_row["currency"], "INR")
        self.assertGreater(prisma_row["valueMinor"], 0)

        # Full analysis output mapping
        res = self.pipeline.analyze_micromarket("Whitefield", "Bengaluru")
        rates = res.to_prisma_market_rates()
        self.assertGreaterEqual(len(rates), 2)
        metrics = {r["metric"] for r in rates}
        self.assertIn("REGISTERED_RATE_PER_SQFT", metrics)
        self.assertIn("ASKING_RATE_PER_SQFT", metrics)

    def test_06_vie_cross_pipeline_compatibility(self):
        """Verify that MIE features directly plug into VIE 13-feature LightGBM model."""
        res = self.pipeline.analyze_micromarket("Whitefield", "Bengaluru")
        vie_feats = res.to_vie_features()

        self.assertIn("inquiry_density_score", vie_feats)
        self.assertIn("transaction_velocity_score", vie_feats)
        self.assertIn("neighbourhood_growth_score", vie_feats)
        self.assertIn("demand_signal", vie_feats)
        self.assertIn("market_risk_score", vie_feats)

        # Execute VIE valuation using MIE features
        val_res = vie_pipeline.valuate_property(
            property_id="prop_vie_test_mie",
            property_title="3 BHK Prestige Lakeview",
            locality="Whitefield",
            city="Bengaluru",
            area_sqft=1650.0,
            bhk_count=3,
            listed_price_paise=1500000000,
            mie_inquiry_density=vie_feats["inquiry_density_score"],
            mie_transaction_velocity=vie_feats["transaction_velocity_score"],
            mie_neighbourhood_growth=vie_feats["neighbourhood_growth_score"],
            locality_base_rate_inr=vie_feats["locality_base_rate_inr"],
        )
        self.assertGreater(val_res.estimate_minor, 0)
        self.assertIsNotNone(val_res.risk_scores)

    def test_07_event_bus_dispatching(self):
        """Test event emission when new transactions, listings, or inquiries arrive."""
        events_received = []

        def on_event(payload):
            events_received.append(payload)

        self.pipeline.dispatcher.subscribe("TRANSACTION_RECORDED", on_event)
        self.pipeline.dispatcher.subscribe("MARKET_INTELLIGENCE_UPDATED", on_event)

        self.pipeline.ingest_transaction(
            RawTransactionRecord(
                locality="Indiranagar",
                city="Bengaluru",
                registration_date=date(2026, 5, 10),
                area_sqft=1400.0,
                consideration_minor=2310000000,
            )
        )
        self.pipeline.analyze_micromarket("Indiranagar", "Bengaluru")

        self.assertGreaterEqual(len(events_received), 2)

    def test_08_locality_ranking(self):
        """Test Square Yards parity locality ranking in city."""
        city = "Bengaluru"
        locs = ["Indiranagar", "Whitefield", "Koramangala"]
        rankings = self.pipeline.rank_localities_in_city(city, locs)

        self.assertEqual(len(rankings), 3)
        ranks = list(rankings.values())
        self.assertEqual(sorted(ranks), [1, 2, 3])

    def test_09_dataset_manager_lifecycle_and_cleanup(self):
        """Test synthetic dataset bootstrap, calibration, and evaluation in temporary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            data_file = temp_path / "mie_data.json"
            model_file = temp_path / "mie_model.json"

            mgr = MieDatasetManager()
            # 1. Bootstrap
            p = mgr.bootstrap_benchmark_dataset(str(data_file), count_per_locality=5)
            self.assertTrue(p.exists())

            # 2. Calibrate
            calib = mgr.train_and_calibrate(str(data_file), str(model_file))
            self.assertTrue(model_file.exists())
            self.assertIn("locality_priors", calib)

            # 3. Evaluate
            eval_metrics = mgr.evaluate_pipeline(str(data_file), str(model_file))
            self.assertGreater(eval_metrics["total_localities_evaluated"], 0)
            self.assertLess(eval_metrics["mean_pipeline_latency_ms"], 50.0)

        # Temporary files cleaned up
        self.assertFalse(data_file.exists())
        self.assertFalse(model_file.exists())


if __name__ == "__main__":
    unittest.main()
