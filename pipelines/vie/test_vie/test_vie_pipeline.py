"""
VIE (Valuation Intelligence Engine) / AVM — Comprehensive Automated Unit Tests.

Covers:
1. Schema enums & 1:1 field mapping with src/db/schema.prisma (AiValuation lines 1166-1205, PriceForecast lines 1655-1668)
2. 13-feature vector assembly and normalization
3. Core LightGBM/Treelite inference (<60ms latency, ±15% CI band)
4. Comparables engine & distance similarity ranking
5. Hard constraint: Owner consent enforcement (consent.comparable_inclusion)
6. Gross rental yield & monthly rental estimation
7. 12-Month price forecast with 90% confidence band (model PriceForecast)
8. 5-Year appreciation projection & primary infrastructure driver
9. Multi-axis investment risk score (Overall, Legal, Market, Climate, Mortgage LTV)
10. Cross-Pipeline integration with PAM (Photo Analysis Module): condition score & seepage impact
11. Cross-Pipeline integration with DEE (Document Extraction Engine): title deed encumbrance impact
12. Claude narrative overlay & AI Gateway caching
13. Event ingestion & ValuationPublished bus notification
14. Continuous learning loop, MAPE tracking, and retraining batch export
15. Public Address-to-value endpoint
16. Benchmark evaluation against ±15% Tier-1 micro-market accuracy target
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from vie.models import (
    ComparableSale,
    DemandSignal,
    InvestmentRiskScores,
    MarketPosition,
    PrismaFurnishingStatus,
    PrismaPropertyType,
    ValuationFeedback,
    ValuationPublishedEvent,
    VieFeatureVector,
    VieTriggerEvent,
    VieTriggerType,
    VieValuationResult,
)
from vie.avm_engine import AvmCoreEngine, avm_core_engine
from vie.comparables_engine import ComparablesEngine, comparables_engine
from vie.narrative_engine import NarrativeEngine, narrative_engine
from vie.risk_and_yield_calculator import RiskAndYieldCalculator
from vie.feedback_loop import VieLearningLoop, vie_learning_loop
from vie.dataset_manager import VieDatasetManager, vie_dataset_manager
from vie.pipeline import ViePipeline, vie_pipeline
from vie.train_and_eval import run_evaluation


class TestViePipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = ViePipeline()
        self.comps = comparables_engine
        self.avm = avm_core_engine

    def test_01_schema_enums_and_fields_alignment(self):
        """Verify enums and 1:1 mapping to Prisma AiValuation and PriceForecast."""
        # Enums
        self.assertEqual(MarketPosition.BELOW_MARKET.value, "BELOW_MARKET")
        self.assertEqual(MarketPosition.ALIGNED.value, "ALIGNED")
        self.assertEqual(MarketPosition.ABOVE_MARKET.value, "ABOVE_MARKET")

        self.assertEqual(DemandSignal.COLD.value, "COLD")
        self.assertEqual(DemandSignal.WARM.value, "WARM")
        self.assertEqual(DemandSignal.HOT.value, "HOT")

        # Execute a test valuation
        res = self.pipeline.valuate_property(
            property_id="prop_test_01",
            property_title="3 BHK Luxury Apartment",
            locality="Whitefield",
            city="Bengaluru",
            area_sqft=1600.0,
            bhk_count=3,
            bathrooms_count=3,
            floor_number=6,
            total_floors=14,
            furnishing=PrismaFurnishingStatus.SEMI_FURNISHED,
            age_years=2.5,
            listed_price_paise=1400000000,  # 1.40 Cr
        )

        # 1:1 Prisma AiValuation columns verification (lines 1166-1205)
        ai_val_row = res.to_prisma_ai_valuation()
        self.assertIn("id", ai_val_row)
        self.assertEqual(ai_val_row["propertyId"], "prop_test_01")
        self.assertIsInstance(ai_val_row["estimateMinor"], int)
        self.assertIsInstance(ai_val_row["confidenceLowMinor"], int)
        self.assertIsInstance(ai_val_row["confidenceHighMinor"], int)
        self.assertIn(ai_val_row["marketPosition"], ["BELOW_MARKET", "ALIGNED", "ABOVE_MARKET"])
        self.assertIn(ai_val_row["demandSignal"], ["COLD", "WARM", "HOT"])
        self.assertIsInstance(ai_val_row["riskScoreOverall"], int)
        self.assertIsInstance(ai_val_row["riskScoreLegal"], int)
        self.assertIsInstance(ai_val_row["riskScoreMarket"], int)
        self.assertIsInstance(ai_val_row["riskScoreClimate"], int)
        self.assertIsInstance(ai_val_row["comparablesJson"], list)
        self.assertIsInstance(ai_val_row["narrativeSummary"], str)
        self.assertEqual(ai_val_row["listedPriceMinor"], 1400000000)
        self.assertIsInstance(ai_val_row["differencePercentage"], float)
        self.assertIsInstance(ai_val_row["grossYieldPercentage"], float)
        self.assertIsInstance(ai_val_row["monthlyRentalEstimateMinor"], int)
        self.assertIsInstance(ai_val_row["projected5YrAppreciationPct"], float)
        self.assertIsInstance(ai_val_row["historicalTransactionsCount"], int)

        # 1:1 Prisma PriceForecast columns verification (lines 1655-1668)
        forecast_row = res.to_prisma_price_forecast()
        self.assertEqual(forecast_row["propertyId"], "prop_test_01")
        self.assertEqual(forecast_row["horizonMonths"], 12)
        self.assertEqual(len(forecast_row["forecastJson"]), 12)
        self.assertIn("modelVersion", forecast_row)

        # PIP payload check
        pip_payload = res.to_pip_insights_payload()
        self.assertIn("valuation", pip_payload)
        self.assertIn("market_position", pip_payload)
        self.assertIn("demand_signal", pip_payload)
        self.assertIn("summary_narrative", pip_payload)
        self.assertIn("risk_score", pip_payload)
        self.assertIn("comparables", pip_payload)

    def test_02_feature_vector_13_features_assembly(self):
        """Verify the 13 canonical features fed to LightGBM."""
        vec = VieFeatureVector(
            area_sqft=1800.0,
            age_years=3.0,
            floor_number=5,
            total_floors=12,
            bhk_count=3,
            bathrooms_count=3,
            furnishing_status=2,
            condition_score_overall=90.0,
            seepage_detected=0,
            locality_price_per_sqft_base=12000.0,
            inquiry_density_score=65.0,
            transaction_velocity_score=58.0,
            neighbourhood_growth_score=72.0,
        )
        feature_list = vec.to_feature_list()
        self.assertEqual(len(feature_list), 13)
        self.assertEqual(feature_list[0], 1800.0)
        self.assertEqual(feature_list[7], 90.0)
        self.assertEqual(feature_list[8], 0.0)
        self.assertEqual(feature_list[9], 12000.0)

    def test_03_core_avm_prediction_latency_and_ci_bands(self):
        """Test inference latency <60ms P95 and ±15% confidence interval bands."""
        vec = VieFeatureVector(
            area_sqft=1500.0,
            locality_price_per_sqft_base=10000.0,
        )
        pred = self.avm.predict(vec)

        # Latency check (<60ms target)
        self.assertLess(pred.inference_latency_ms, 60.0)

        # Point estimate & CI check (±15% Tier-1 band)
        est = pred.estimate_paise
        self.assertGreater(est, 0)
        expected_low = int(round(est * 0.85))
        expected_high = int(round(est * 1.15))
        self.assertEqual(pred.confidence_low_paise, expected_low)
        self.assertEqual(pred.confidence_high_paise, expected_high)

    def test_04_comparables_engine_similarity_scoring(self):
        """Test similarity score computation and ranking."""
        comps = self.comps.find_comparables(
            property_id="prop_target_1",
            locality="Indiranagar",
            city="Bengaluru",
            area_sqft=1900.0,
            bhk_count=3,
            max_results=5,
        )
        self.assertGreaterEqual(len(comps), 2)
        # Verify sorted by similarity descending
        for i in range(len(comps) - 1):
            self.assertGreaterEqual(comps[i].similarity_score, comps[i + 1].similarity_score)

    def test_05_consent_comparable_inclusion_hard_constraint(self):
        """Test that properties with consent_comparable_inclusion=False are STRICTLY excluded."""
        # 'tx_blr_ind_optout_03' has consent_comparable_inclusion = False in seed
        comps = self.comps.find_comparables(
            property_id="target_search_1",
            locality="Indiranagar",
            city="Bengaluru",
            area_sqft=3000.0,
            bhk_count=4,
            max_results=10,
        )
        returned_ids = [c.property_id for c in comps]
        self.assertNotIn("tx_blr_ind_optout_03", returned_ids)
        for c in comps:
            self.assertTrue(c.consent_comparable_inclusion)

    def test_06_rental_yield_and_monthly_rent_calculation(self):
        """Test gross rental yield % and monthly rental in paise."""
        vec = VieFeatureVector(
            area_sqft=1400.0,
            furnishing_status=2,  # Fully furnished
            condition_score_overall=92.0,
            locality_price_per_sqft_base=8500.0,
        )
        estimate_paise = 1200000000  # 1.2 Cr
        yield_pct, monthly_rent_paise = RiskAndYieldCalculator.compute_rental_yield(
            estimate_paise=estimate_paise,
            locality="Whitefield",
            features=vec,
        )
        # Indian residential yield is between 3.0% and 6.5%
        self.assertGreaterEqual(yield_pct, 3.0)
        self.assertLessEqual(yield_pct, 6.5)
        # Monthly rent should equal annual rent / 12
        annual_rent = estimate_paise * (yield_pct / 100.0)
        self.assertAlmostEqual(monthly_rent_paise, int(round(annual_rent / 12.0)), delta=5)

    def test_07_price_forecast_12m_series(self):
        """Test 12-month forward price forecast with widening 90% confidence bands."""
        vec = VieFeatureVector(
            area_sqft=1500.0,
            locality_price_per_sqft_base=9000.0,
            neighbourhood_growth_score=75.0,
        )
        est_paise = 1350000000
        forecast = RiskAndYieldCalculator.generate_12m_forecast(est_paise, vec)

        self.assertEqual(len(forecast), 12)
        # Month 1 to 12 sequence
        self.assertEqual([p.month for p in forecast], list(range(1, 13)))
        # Trend should show upward appreciation
        self.assertGreater(forecast[11].estimate_minor, forecast[0].estimate_minor)
        # Low < Estimate < High
        for p in forecast:
            self.assertLess(p.low_minor, p.estimate_minor)
            self.assertGreater(p.high_minor, p.estimate_minor)

    def test_08_5yr_appreciation_and_primary_driver(self):
        """Test 5-year capital appreciation % and growth driver string."""
        vec = VieFeatureVector(
            area_sqft=1500.0,
            locality_price_per_sqft_base=9000.0,
            neighbourhood_growth_score=80.0,
            transaction_velocity_score=75.0,
        )
        apprec_pct, driver = RiskAndYieldCalculator.compute_5yr_appreciation("Whitefield", vec)
        self.assertGreater(apprec_pct, 30.0)
        self.assertIn("Purple Line", driver)

    def test_09_multi_axis_investment_risk_scores(self):
        """Test overall, market, climate, and mortgage LTV risk scores."""
        vec = VieFeatureVector(
            area_sqft=1500.0,
            locality_price_per_sqft_base=9000.0,
            age_years=5.0,
            condition_score_overall=85.0,
            seepage_detected=0,
            transaction_velocity_score=60.0,
            inquiry_density_score=60.0,
        )
        risk = RiskAndYieldCalculator.compute_investment_risk(
            features=vec,
            asking_price_paise=1500000000,
            estimate_paise=1500000000,
        )
        self.assertGreaterEqual(risk.overall, 0)
        self.assertLessEqual(risk.overall, 100)
        self.assertEqual(risk.legal, 10)  # Default clear title
        self.assertIsNotNone(risk.mortgage_ltv)
        self.assertEqual(risk.mortgage_ltv, 0.8)

    def test_10_cross_pipeline_pam_condition_impact(self):
        """Cross-Pipeline: PAM condition score & seepage flag adjust valuation and risk."""
        # 1. High-condition pristine home without seepage
        res_pristine = self.pipeline.valuate_property(
            property_id="prop_pam_high",
            property_title="Pristine Home",
            locality="Whitefield",
            city="Bengaluru",
            area_sqft=1500.0,
            bhk_count=3,
            pam_condition_score=98.0,
            pam_seepage_detected=False,
        )

        # 2. Distressed home with low condition score and active seepage detected by PAM
        res_distressed = self.pipeline.valuate_property(
            property_id="prop_pam_low",
            property_title="Distressed Home with Dampness",
            locality="Whitefield",
            city="Bengaluru",
            area_sqft=1500.0,
            bhk_count=3,
            pam_condition_score=60.0,
            pam_seepage_detected=True,
        )

        # Pristine should have strictly higher valuation than distressed
        self.assertGreater(res_pristine.estimate_minor, res_distressed.estimate_minor)
        # Distressed should have strictly higher overall and climate risk
        self.assertGreater(res_distressed.risk_scores.overall, res_pristine.risk_scores.overall)
        self.assertGreater(res_distressed.risk_scores.climate, res_pristine.risk_scores.climate)

    def test_11_cross_pipeline_dee_legal_encumbrance_impact(self):
        """Cross-Pipeline: DEE legal encumbrance flag feeds into riskScoreLegal."""
        # Clear title deed from DEE
        res_clear = self.pipeline.valuate_property(
            property_id="prop_dee_clear",
            property_title="Clear Title Home",
            locality="Indiranagar",
            city="Bengaluru",
            area_sqft=1800.0,
            bhk_count=3,
            dee_legal_encumbrance_flag=False,
            dee_title_confidence=0.98,
        )

        # Encumbered title / active lien flagged by DEE
        res_encumbered = self.pipeline.valuate_property(
            property_id="prop_dee_lien",
            property_title="Home with Bank Lien",
            locality="Indiranagar",
            city="Bengaluru",
            area_sqft=1800.0,
            bhk_count=3,
            dee_legal_encumbrance_flag=True,
            dee_title_confidence=0.85,
        )

        self.assertEqual(res_clear.risk_scores.legal, 10)
        self.assertEqual(res_encumbered.risk_scores.legal, 75)
        self.assertGreater(res_encumbered.risk_scores.overall, res_clear.risk_scores.overall)

    def test_12_narrative_overlay_and_caching(self):
        """Test Claude narrative overlay conforms to <= 600 chars and cache works."""
        narrative_engine.clear_cache()

        res = self.pipeline.valuate_property(
            property_id="prop_narr_01",
            property_title="Skyline Penthouse",
            locality="Indiranagar",
            city="Bengaluru",
            area_sqft=2400.0,
            bhk_count=4,
            listed_price_paise=4000000000,
        )
        narrative = res.narrative_summary
        self.assertLessEqual(len(narrative), 600)
        self.assertIn("Indiranagar", narrative)

        # Re-run same inputs — should hit cache with near-zero latency
        res_cached = self.pipeline.valuate_property(
            property_id="prop_narr_01",
            property_title="Skyline Penthouse",
            locality="Indiranagar",
            city="Bengaluru",
            area_sqft=2400.0,
            bhk_count=4,
            listed_price_paise=4000000000,
        )
        self.assertLessEqual(res_cached.narrative_latency_ms, 5.0)

    def test_13_event_bus_and_trigger_lifecycle(self):
        """Test event subscription and processing triggers."""
        published_events: List[ValuationPublishedEvent] = []
        self.pipeline.subscribe_events(lambda ev: published_events.append(ev))

        # Test PropertyRegistered trigger
        trigger_reg = VieTriggerEvent(
            trigger_type=VieTriggerType.PROPERTY_REGISTERED,
            property_id="prop_trig_01",
            payload={
                "title": "New Onboarding Flat",
                "locality": "Whitefield",
                "city": "Bengaluru",
                "area_sqft": 1450.0,
                "bhk_count": 3,
            },
        )
        res = self.pipeline.process_trigger_event(trigger_reg)
        self.assertIsNotNone(res)
        self.assertGreaterEqual(len(published_events), 1)
        self.assertEqual(published_events[-1].property_id, "prop_trig_01")

        # Test TransactionCompleted trigger (adds comparable to pool)
        prior_comps_count = len(self.comps._comparable_pool)
        trigger_tx = VieTriggerEvent(
            trigger_type=VieTriggerType.TRANSACTION_COMPLETED,
            property_id="prop_tx_closed_99",
            payload={
                "title": "Closed Transaction Unit 4B",
                "locality": "Whitefield",
                "city": "Bengaluru",
                "sale_price_paise": 1250000000,
                "area_sqft": 1380.0,
                "bhk_count": 3,
                "consent_comparable_inclusion": True,
            },
        )
        self.pipeline.process_trigger_event(trigger_tx)
        self.assertEqual(len(self.comps._comparable_pool), prior_comps_count + 1)

    def test_14_continuous_learning_and_drift_tracking(self):
        """Test continuous learning feedback loop, MAPE, and retraining export."""
        loop = VieLearningLoop()
        loop.clear()

        # Record 4 accurate transactions (within 5%)
        for i in range(4):
            loop.record_actual_sale(
                property_id=f"prop_loop_{i+1}",
                predicted_estimate_paise=1000000000,
                actual_transacted_paise=1020000000,
                micro_market="Whitefield",
            )
        # Record 1 slightly shifted transaction (10% error)
        loop.record_actual_sale(
            property_id="prop_loop_5",
            predicted_estimate_paise=1000000000,
            actual_transacted_paise=1100000000,
            micro_market="Whitefield",
        )

        metrics = loop.get_metrics()
        self.assertEqual(metrics.total_events, 5)
        self.assertLess(metrics.mape_percentage, 5.0)
        self.assertEqual(metrics.within_15_pct_accuracy_ratio, 100.0)
        self.assertFalse(loop.is_drift_alert_triggered())

        # Export training batch
        batch = loop.export_training_batch()
        self.assertEqual(len(batch), 5)
        self.assertIn("ground_truth_paise", batch[0])

    def test_15_address_to_value_public_api(self):
        """Test public Address-to-value endpoint without registered property ID."""
        res = self.pipeline.address_to_value(
            locality="Koramangala",
            city="Bengaluru",
            area_sqft=1750.0,
            bhk_count=3,
            furnishing="FULLY_FURNISHED",
            age_years=1.0,
        )
        self.assertIsNotNone(res)
        self.assertGreater(res.estimate_minor, 0)
        self.assertIn("Koramangala", res.narrative_summary)

    def test_16_tier1_benchmark_accuracy_target(self):
        """Verify baseline benchmark evaluation satisfies >= 85% within ±15% accuracy target."""
        eval_result = run_evaluation(samples_count=100, seed=123)
        self.assertEqual(eval_result["status"], "PASSED")
        self.assertGreaterEqual(eval_result["within_15_ratio"], 85.0)
        self.assertLess(eval_result["p95_latency_ms"], 60.0)


if __name__ == "__main__":
    unittest.main()
