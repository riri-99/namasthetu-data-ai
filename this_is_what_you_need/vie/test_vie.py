"""
VIE (Valuation Intelligence Engine) — Automated Unit Tests.
"""

import unittest
from this_is_what_you_need.vie.pipeline import (
    AvmCoreEngine,
    DemandSignal,
    MarketPosition,
    VieFeatureVector,
    ViePipeline,
    vie_pipeline,
)


class TestViePipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = ViePipeline()

    def test_01_avm_prediction_and_ci(self):
        vec = VieFeatureVector(area_sqft=1500.0, locality_price_per_sqft_base=10000.0)
        pred = AvmCoreEngine.predict(vec)
        self.assertGreater(pred.estimate_paise, 0)
        self.assertEqual(pred.confidence_low_paise, int(round(pred.estimate_paise * 0.85)))
        self.assertEqual(pred.confidence_high_paise, int(round(pred.estimate_paise * 1.15)))

    def test_02_full_valuation_and_prisma_export(self):
        res = self.pipeline.valuate_property(
            property_id="prop_vie_01",
            property_title="3 BHK Flat",
            locality="Whitefield",
            city="Bengaluru",
            area_sqft=1600.0,
            bhk_count=3,
            listed_price_paise=1500000000,
            pam_condition_score=95.0,
            pam_seepage_detected=False,
            dee_legal_encumbrance_flag=False,
        )
        self.assertGreater(res.estimate_minor, 0)
        prisma_row = res.to_prisma_ai_valuation()
        self.assertIn("estimateMinor", prisma_row)
        self.assertIn("confidenceLowMinor", prisma_row)
        self.assertIn("riskScoreOverall", prisma_row)
        self.assertEqual(len(res.forecast_12m), 12)

    def test_03_consent_comparable_exclusion(self):
        res = self.pipeline.valuate_property(
            property_id="prop_vie_02",
            property_title="Flat",
            locality="Whitefield",
            city="Bengaluru",
            area_sqft=1600.0,
            bhk_count=3,
        )
        for comp in res.comparables:
            self.assertTrue(comp.consent_comparable_inclusion)
            self.assertNotEqual(comp.property_id, "tx_seed_optout")


if __name__ == "__main__":
    unittest.main()
