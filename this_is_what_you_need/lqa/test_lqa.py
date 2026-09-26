"""
LQA (Listing Quality Auditor) — Automated Unit Tests.

Embedded AI Service #5 · Namasthetu Platform
Spec Reference: HYC-SCO-2026-3841 (§12.1-§12.4, §8.8, §03.M09)
Database Alignment: Strictly compliant with src/db/schema.prisma (models Listing, LqaAudit)
"""

import unittest
from datetime import datetime
from this_is_what_you_need.lqa.pipeline import (
    ListingDraftInput,
    ListingScoredEvent,
    ListingStatus,
    LqaAuditResult,
    LqaFlagCategory,
    LqaFlagSeverity,
    LqaPipeline,
    LqaStatus,
    PhotoMetadata,
    lqa_pipeline,
)


class TestLqaPipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = LqaPipeline()

    def test_01_schema_enums(self):
        """Verify enums strictly match schema.prisma lines 72-80 & 116-123."""
        self.assertEqual(LqaStatus.QUEUED.value, "QUEUED")
        self.assertEqual(LqaStatus.SCORING.value, "SCORING")
        self.assertEqual(LqaStatus.SCORED.value, "SCORED")
        self.assertEqual(LqaStatus.APPROVED.value, "APPROVED")
        self.assertEqual(LqaStatus.REJECTED.value, "REJECTED")

        self.assertEqual(ListingStatus.DRAFT.value, "DRAFT")
        self.assertEqual(ListingStatus.PENDING_APPROVAL.value, "PENDING_APPROVAL")
        self.assertEqual(ListingStatus.ACTIVE.value, "ACTIVE")
        self.assertEqual(ListingStatus.PAUSED.value, "PAUSED")
        self.assertEqual(ListingStatus.EXPIRED.value, "EXPIRED")
        self.assertEqual(ListingStatus.CLOSED.value, "CLOSED")

    def test_02_auto_approval_high_quality(self):
        """Listing with >= 90 score auto-approves and transitions to ACTIVE without Ops queue."""
        draft = ListingDraftInput(
            listing_id="list_hq_001",
            property_id="prop_hq_001",
            title="Luxury 3BHK Apartment in Indiranagar Bengaluru",
            description=(
                "Exquisite 3BHK flat on 5th floor with panoramic city views. "
                "Features imported Italian marble flooring, modular kitchen with chimney, "
                "two reserved covered car parking slots, 100% power backup, and round-the-clock security."
            ),
            asking_price_paise=2400000000,  # 2.4 Cr
            area_sqft=1850.0,
            property_type="APARTMENT",
            photos=[
                PhotoMetadata(url=f"https://s3/p{i}.jpg", room_category=rc)
                for i, rc in enumerate(["LIVING_ROOM", "MASTER_BEDROOM", "KITCHEN", "BATHROOM", "BALCONY"])
            ],
            rera_number="PRM/KA/RERA/1251/310/PR/171015/000123",
            has_occupancy_certificate=True,
            has_encumbrance_certificate=True,
            property_tax_paid=True,
            maintenance_charges_monthly_inr=5500.0,
            dee_deed_verified=True,
            dee_active_liens_detected=False,
            vie_avm_estimate_paise=2450000000,
        )

        res = self.pipeline.audit_listing(draft)

        self.assertGreaterEqual(res.overall_score, 90)
        self.assertTrue(res.lqa_passed)
        self.assertEqual(res.status, LqaStatus.APPROVED)
        self.assertFalse(res.requires_spot_check)
        self.assertEqual(res.resulting_listing_status, ListingStatus.ACTIVE)
        self.assertEqual(res.breakdown.critical_flags_count, 0)
        self.assertIn("Listing Quality Audit Report", res.feedback_narrative)

    def test_03_spot_check_band(self):
        """Listing with 72-89 score is APPROVED but routes to Ops queue for spot-check."""
        draft = ListingDraftInput(
            listing_id="list_mq_002",
            property_id="prop_mq_002",
            title="Decent 2BHK in Whitefield",
            description=(
                "Well maintained 2BHK apartment near ITPL. East facing with good ventilation. "
                "Semi-furnished with wooden wardrobes and modular kitchen fittings."
            ),
            asking_price_paise=950000000,  # 95 Lakhs
            area_sqft=1150.0,
            property_type="APARTMENT",
            photos=["https://s3/p1.jpg", "https://s3/p2.jpg", "https://s3/p3.jpg"],
            # Deed pending verification (-15) + missing RERA (-10) + missing OC (-10)
            rera_number=None,
            has_occupancy_certificate=False,
            dee_deed_verified=False,
            dee_active_liens_detected=False,
            vie_avm_estimate_paise=1000000000,
        )

        res = self.pipeline.audit_listing(draft)

        self.assertGreaterEqual(res.overall_score, 72)
        self.assertLess(res.overall_score, 90)
        self.assertTrue(res.lqa_passed)
        self.assertEqual(res.status, LqaStatus.APPROVED)
        self.assertTrue(res.requires_spot_check)
        self.assertEqual(res.resulting_listing_status, ListingStatus.PENDING_APPROVAL)

    def test_04_rejection_low_quality(self):
        """Listing with < 72 score is REJECTED and returns to DRAFT with categorised feedback."""
        draft = ListingDraftInput(
            listing_id="list_lq_003",
            property_id="prop_lq_003",
            title="Flat for sale",
            description="Flat is good. Call me.",  # Too short, missing details
            asking_price_paise=500000000,
            area_sqft=900.0,
            property_type="APARTMENT",
            photos=[],  # Zero photos -> CRITICAL
            dee_deed_verified=False,
        )

        res = self.pipeline.audit_listing(draft)

        self.assertLess(res.overall_score, 72)
        self.assertFalse(res.lqa_passed)
        self.assertEqual(res.status, LqaStatus.REJECTED)
        self.assertFalse(res.requires_spot_check)
        self.assertEqual(res.resulting_listing_status, ListingStatus.DRAFT)
        self.assertGreater(res.breakdown.critical_flags_count, 0)
        self.assertTrue(any(f.code == "NO_PHOTOS" for f in res.breakdown.all_flags))
        self.assertTrue(any(f.code == "INSUFFICIENT_DESCRIPTION" for f in res.breakdown.all_flags))

    def test_05_price_anomaly_detection(self):
        """Asking price >30% below AVM triggers SUSPICIOUS_PRICE_DISCOUNT flag."""
        draft = ListingDraftInput(
            listing_id="list_pa_004",
            property_id="prop_pa_004",
            title="3BHK Prestige Apartment",
            description="Spacious 3BHK flat in prime location with all modern amenities.",
            asking_price_paise=1000000000,  # 1.0 Cr
            area_sqft=1600.0,
            property_type="APARTMENT",
            photos=[f"https://s3/p{i}.jpg" for i in range(4)],
            dee_deed_verified=True,
            dee_active_liens_detected=False,
            vie_avm_estimate_paise=2000000000,  # 2.0 Cr -> 50% discount!
        )

        res = self.pipeline.audit_listing(draft)

        price_flags = [f for f in res.breakdown.price.flags if f.code == "SUSPICIOUS_PRICE_DISCOUNT"]
        self.assertEqual(len(price_flags), 1)
        self.assertEqual(price_flags[0].severity, LqaFlagSeverity.CRITICAL)
        self.assertLessEqual(res.breakdown.price.score, 40)

    def test_06_deceptive_disclosure_and_fraud_escalation(self):
        """Claiming 'clear title / lien free' while DEE flagged active liens triggers fraud flag."""
        draft = ListingDraftInput(
            listing_id="list_fraud_005",
            property_id="prop_fraud_005",
            title="Clear Title Independent Villa",
            description="100% clean title and lien free property. Immediate handover.",
            asking_price_paise=1800000000,
            area_sqft=2200.0,
            property_type="VILLA",
            photos=[f"https://s3/p{i}.jpg" for i in range(4)],
            dee_deed_verified=True,
            dee_active_liens_detected=True,  # DEE found active bank mortgage!
        )

        res = self.pipeline.audit_listing(draft)

        deceptive_flags = [f for f in res.breakdown.disclosure.flags if f.code == "DECEPTIVE_TITLE_CLAIM"]
        self.assertEqual(len(deceptive_flags), 1)
        self.assertEqual(deceptive_flags[0].severity, LqaFlagSeverity.CRITICAL)
        self.assertTrue(res.fraud_flag_recommended)
        self.assertEqual(res.fraud_flag_reason, "DECEPTIVE_ENCUMBRANCE_CLAIM_WITH_ACTIVE_LIEN")

    def test_07_revision_history_side_by_side(self):
        """Side-by-side comparison highlights resolved flags and score delta on re-score."""
        # 1st Submission: Rejected due to missing photos and short text
        sub1 = ListingDraftInput(
            listing_id="list_rev_006",
            property_id="prop_rev_006",
            title="Apartment in Koramangala",
            description="Nice flat available.",
            asking_price_paise=1200000000,
            area_sqft=1200.0,
            photos=[],
            dee_deed_verified=False,
        )
        res1 = self.pipeline.audit_listing(sub1)
        self.assertEqual(res1.status, LqaStatus.REJECTED)

        # 2nd Submission: Owner uploads photos, expands description, verifies deed
        sub2 = ListingDraftInput(
            listing_id="list_rev_006",
            property_id="prop_rev_006",
            title="Premium 2BHK Apartment in Koramangala 4th Block",
            description=(
                "Immaculate 2BHK apartment in Koramangala 4th block. Features spacious hall, "
                "teak wood doors, premium sanitary fittings, modular kitchen, and dedicated covered car parking."
            ),
            asking_price_paise=1200000000,
            area_sqft=1200.0,
            photos=[f"https://s3/p{i}.jpg" for i in range(5)],
            dee_deed_verified=True,
            dee_active_liens_detected=False,
            previous_audit_id=res1.audit_id,
        )
        res2 = self.pipeline.audit_listing(sub2)

        self.assertIsNotNone(res2.revision_comparison)
        comp = res2.revision_comparison
        self.assertGreater(comp.score_delta, 0)
        self.assertIn("NO_PHOTOS", comp.resolved_flags)
        self.assertIn("INSUFFICIENT_DESCRIPTION", comp.resolved_flags)
        self.assertEqual(res2.status, LqaStatus.APPROVED)

    def test_08_prisma_audit_export(self):
        """to_prisma_audit_dict strictly matches model LqaAudit in schema.prisma."""
        draft = ListingDraftInput(
            listing_id="list_prisma_007",
            property_id="prop_prisma_007",
            title="Spacious Independent House",
            description="G+1 independent house on 30x40 site with clear title and borewell water.",
            asking_price_paise=1600000000,
            area_sqft=1800.0,
            photos=[f"https://s3/p{i}.jpg" for i in range(4)],
            dee_deed_verified=True,
        )
        res = self.pipeline.audit_listing(draft)
        prisma_dict = res.to_prisma_audit_dict()

        self.assertIn("id", prisma_dict)
        self.assertEqual(prisma_dict["propertyId"], "prop_prisma_007")
        self.assertIn("status", prisma_dict)
        self.assertIn("overallScore", prisma_dict)
        self.assertIn("breakdownJson", prisma_dict)
        self.assertIn("feedbackNarrative", prisma_dict)
        self.assertIn("requiresSpotCheck", prisma_dict)
        self.assertIn("evaluatedAt", prisma_dict)

        # Check breakdown JSON structure
        b_json = prisma_dict["breakdownJson"]
        self.assertIn("photos", b_json)
        self.assertIn("price", b_json)
        self.assertIn("disclosure", b_json)
        self.assertIn("language", b_json)
        self.assertIn("all_flags", b_json)

    def test_09_event_dispatch(self):
        """ListingScoredEvent is published to subscribers upon audit completion."""
        received_events = []

        def on_event(evt: ListingScoredEvent):
            received_events.append(evt)

        self.pipeline.event_dispatcher.subscribe(on_event)

        draft = ListingDraftInput(
            listing_id="list_evt_008",
            property_id="prop_evt_008",
            title="Test Event Property",
            description="Testing event dispatcher subscription with standard property description.",
            asking_price_paise=1500000000,
            area_sqft=1400.0,
            photos=[f"https://s3/p{i}.jpg" for i in range(3)],
            dee_deed_verified=True,
        )
        res = self.pipeline.audit_listing(draft)

        self.assertEqual(len(received_events), 1)
        evt = received_events[0]
        self.assertEqual(evt.listing_id, "list_evt_008")
        self.assertEqual(evt.property_id, "prop_evt_008")
        self.assertEqual(evt.lqa_score, res.overall_score)
        self.assertEqual(evt.status, res.status)

    def test_10_direct_contact_info_leakage(self):
        """Phone numbers in description trigger CRITICAL flag for platform disintermediation."""
        draft = ListingDraftInput(
            listing_id="list_contact_009",
            property_id="prop_contact_009",
            title="Direct Owner Contact Flat",
            description="Direct owner sale! Call me at 9876543210 or email owner@example.com for discount.",
            asking_price_paise=1100000000,
            area_sqft=1100.0,
            photos=[f"https://s3/p{i}.jpg" for i in range(4)],
        )
        res = self.pipeline.audit_listing(draft)

        contact_flags = [f for f in res.breakdown.language.flags if f.code == "CONTACT_INFO_IN_DESCRIPTION"]
        self.assertEqual(len(contact_flags), 1)
        self.assertEqual(contact_flags[0].severity, LqaFlagSeverity.CRITICAL)


if __name__ == "__main__":
    unittest.main()
