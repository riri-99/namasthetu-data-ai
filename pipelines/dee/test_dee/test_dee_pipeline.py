"""
Comprehensive Test Suite for DEE (Document Extraction Engine)
Validates:
  1. Full extraction workflow on Indian legal documents (Sale Deed, EC, Allotment).
  2. Strict adherence to `src/db/schema.prisma` (`LegalDocument` and `DeedHistoryEvent`).
  3. Non-Negotiable PII Masking (Aadhaar & PAN tokenization).
  4. Confidence Threshold Routing (< 0.85 -> REVIEWING with suggested_resolution).
  5. SSE status streaming event dispatch.
"""

import os
import sys
import unittest
from datetime import datetime

# Set up path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from pipelines.dee.models import (
    DocumentType,
    DocumentStatus,
    DeedEventType,
    DeedEventStatus,
    DeePipelineStage,
    DeeSqsMessagePayload,
)
from pipelines.dee.pipeline import dee_pipeline
from pipelines.dee.gateway import mask_pii
from pipelines.dee.learning_loop import dee_learning_collector, DeeLearningEventType
from pipelines.dee.dataset_manager import dee_dataset_manager




# Sample Synthetic Test Document OCR Texts
SALE_DEED_CLEAN_TEXT = """
BOOK 1 - REGISTERED ABSOLUTE SALE DEED
Sub-Registrar Office, Shivajinagar, Bengaluru Urban
Document No: BNG-U-BLR(S)-10492/2023-24, Stored in CD-148, Pages 1 to 24.
Execution Date: 15th day of March, 2024.

BETWEEN:
PRESTIGE ESTATES PROJECTS LTD, having its registered office at The Falcon House,
Main Guard Cross Road, Bengaluru (hereinafter called the VENDOR / GRANTOR, PAN: PQRST9981M).
AND
DR. VIKRAMADITYA R. RAO, S/o Ramachandra Rao, aged about 42 years,
residing at Indiranagar, Bengaluru (hereinafter called the PURCHASER / GRANTEE, PAN: ABCDE1234F, Aadhaar: 9812 3456 7890).

SCHEDULE PROPERTY DETAILS:
All that piece and parcel of residential apartment unit bearing Flat Unit 1402, 14th Floor, Tower-B,
constructed on converted revenue land situated in Survey No. 142/2A, Varthur Village, Varthur Hobli,
Bengaluru East Taluk, with Khata No. K-9812/4.
Measurement: Carpet Area of 1,950 sq.ft and Super Built-Up Area of 2,450 sq.ft.
Boundaries:
North by: Sy No 142/1 Private Property;
South by: 40ft BDA Access Road;
East by: Civic Amenity Park Site;
West by: Drainage buffer and Sy No 143.

FINANCIAL CONSIDERATION:
Total sale consideration of INR 2,85,00,000/- (Rupees Two Crores Eighty-Five Lakhs only) fully paid.
Stamp duty paid: INR 18,81,000/-. Registration fee: INR 2,85,000/-.

ENCUMBRANCE COVENANT:
The Vendor covenants that the Schedule Property is absolute freehold and free from all prior mortgages,
charges, liens, lis pendens, tax arrears, and court attachments.
"""

ENCUMBRANCE_CERTIFICATE_MORTGAGE_TEXT = """
GOVERNMENT OF TELANGANA - REGISTRATION AND STAMPS DEPARTMENT
FORM NO. 15 - ENCUMBRANCE CERTIFICATE ON PROPERTY
Application No: EC-2024-HYD-98124
Search Period: From 01-01-2010 to 15-05-2024
Sub-Registrar Office: SRO Serilingampally, Ranga Reddy District

Property Description:
Survey No. 88/1, Plot No. 42, Jubilee Cyber Hills, Serilingampally, Hyderabad.
Registered Owner: Dr. Vikramaditya R. Rao.

RECORDED TRANSACTIONS / CHARGES:
Entry No. 1:
Date of Registration: 10-04-2024
Nature of Deed: Registered Simple Mortgage Deed (Charge ID: MORT-4821/2024)
Executant / Mortgagor: Dr. Vikramaditya R. Rao
Claimant / Mortgagee: HDFC Bank Ltd, Gachibowli Branch
Secured Loan Amount: INR 1,50,00,000/- (Rupees One Crore Fifty Lakhs only)
Status: Active / Outstanding (No discharge receipt filed to date).
"""

PUNE_SALE_DEED_TEXT = """
BOOK 1 - REGISTERED ABSOLUTE CONVEYANCE DEED
Sub-Registrar Office Haveli No. 12, Pune, Maharashtra
Document No: PNE-HVL-08341/2018-19, Volume 512, Pages 10 to 32.
Execution Date: 22nd day of November, 2018.

BETWEEN:
SURESH RAMCHANDRA JOSHI, S/o Ramchandra Joshi, residing at Kothrud, Pune (hereinafter called the VENDOR / GRANTOR, PAN: AAAPJ1234K).
AND
RAJESH DATTATRAY PATIL, S/o Dattatray Patil, residing at Baner, Pune (hereinafter called the PURCHASER / GRANTEE, PAN: BCDEF5678L, Aadhaar: 3123 4567 8901).

SCHEDULE PROPERTY:
All that piece and parcel of residential flat bearing Unit 402, 4th Floor, situated in Survey No. 48/3B,
Hissa No. 2, Balewadi Village, Haveli Taluk, Pune District, Maharashtra.
Measurements: Carpet Area of 850 sq.ft and Super Built-Up Area of 1,120 sq.ft.
Boundaries:
North by: 18 Meter Wide DP Road;
South by: Survey No 48/4;
East by: Internal Access Lane;
West by: Adjoining Society Plot.

FINANCIAL CONSIDERATION:
Total sale consideration of INR 75,00,000/- (Rupees Seventy-Five Lakhs only) fully paid by the Purchaser.
Stamp duty paid: INR 4,50,000/-. Registration charges paid: INR 30,000/-.

TITLE COVENANT:
The Vendor covenants that the property is freehold and free from all encumbrances, charges, and lis pendens.
"""

DEGRADED_SCAN_TEXT = """
low_contrast dark blurry photo
sy no ... [unreadable smudged numbers]
vendor ... [ink blotched]
purchaser ... [page fold shadow across signature]
"""

KANNADA_TEST_DEED = """
ಕರ್ನಾಟಕ ಸರ್ಕಾರ - ನೋಂದಣಿ ಮತ್ತು ಮುದ್ರಾಂಕ ಇಲಾಖೆ
ಪುಸ್ತಕ 1 - ನೋಂದಾಯಿತ ಕ್ರಯಪತ್ರ (ಖರೀದಿ ಪತ್ರ)
ದಸ್ತಾವೇಜು ಸಂಖ್ಯೆ: MYS-S-04821/2022-23

ಮಾರಾಟಗಾರರಾದ:
ಶ್ರೀ ಬಸವರಾಜಪ್ಪ ಎಸ್. ಬಿ., ವಾಸ: ಜಯನಗರ, ಮೈಸೂರು (PAN: BSBPA1234K).

ಖರೀದಿದಾರರಾದ:
ಶ್ರೀ ಮಂಜುನಾಥ ಕೆ. ಗೌಡ, ವಾಸ: ಕುವೆಂಪುನಗರ, ಮೈಸೂರು (PAN: MKGPA5678L, Aadhaar: 4123 7890 1234).

ಸ್ವತ್ತು ವಿವರ:
ವಿಜಯನಗರ ಗ್ರಾಮದ ಸರ್ವೆ ನಂ 84/3, ನಿವೇಶನ ಸಂಖ್ಯೆ 24, ಖಾತಾ ನಂ 1842.
ವಿಸ್ತೀರ್ಣ: 1200 ಚದರ ಅಡಿ.
ಕ್ರಯದ ಮೊತ್ತ: ರೂ. 4800000/-.
ಮುದ್ರಾಂಕ ಶುಲ್ಕ: ರೂ. 264000/-.
"""

HINDI_TEST_DEED = """
मध्य प्रदेश शासन - पंजीयन एवं मुद्रांक विभाग
पुस्तक 1 - पंजीकृत विक्रय विलेख (बैनामा)
दस्तावेज़ क्रमांक: IND-08412/2021-22

विक्रेता:
महेश कुमार शर्मा, निवासी: इंदौर (PAN: MKSPA4321F).

क्रेता:
अमित कुमार वर्मा, निवासी: इंदौर (PAN: AKVPA8765M).

संपत्ति का विवरण:
ग्राम खजराना स्थित खसरा नंबर 114/2, भूखंड क्रमांक 15.
क्षेत्रफल: 1500 वर्ग फुट.
प्रतिफल राशि: रुपये 5500000/-.
स्टाम्प शुल्क: रुपये 522500/-.
"""


class TestDeePipeline(unittest.TestCase):

    def test_01_clean_sale_deed_extraction(self):
        """Test clean sale deed extraction, confidence score, and schema fields."""
        result = dee_pipeline.process_document(
            file_input=SALE_DEED_CLEAN_TEXT,

            document_type=DocumentType.SALE_DEED,
            document_id="doc-test-001",
            property_id="prop-test-blr-01",
        )

        # 1. Assertions on LegalDocument columns
        self.assertEqual(result.status, DocumentStatus.EXTRACTED)
        self.assertFalse(result.requiresManualReview)
        self.assertGreaterEqual(result.aiConfidenceScore, 0.85)
        self.assertIn("Sale Deed", result.aiSummaryPlainEnglish)

        # 2. Assertions on structured extracted entities (aiExtractedDataJson)
        entities = result.aiExtractedDataJson
        self.assertEqual(entities.document_type, DocumentType.SALE_DEED)
        self.assertGreaterEqual(len(entities.owners), 2)
        
        buyer = next((o for o in entities.owners if o.party_type.value == "GRANTEE_BUYER"), None)
        self.assertIsNotNone(buyer)
        self.assertEqual(buyer.name, "DR. VIKRAMADITYA R. RAO")
        self.assertEqual(buyer.relation_type, "S/o")
        self.assertIn("AB***F", buyer.pan_masked)

        self.assertEqual(entities.survey_number.survey_no, "142/2A")
        self.assertEqual(entities.area.carpet_area_sqft, 1950.0)
        self.assertEqual(entities.area.super_built_up_sqft, 2450.0)

        # 3. Assertions on downstream DeedHistoryEvent payloads
        self.assertGreaterEqual(len(result.deedHistoryEvents), 1)
        deed_event = result.deedHistoryEvents[0]
        self.assertEqual(deed_event.eventType, DeedEventType.SALE_DEED)
        self.assertEqual(deed_event.status, DeedEventStatus.VERIFIED)
        self.assertEqual(deed_event.year, 2024)

    def test_02_encumbrance_certificate_mortgage(self):
        """Test Encumbrance Certificate extraction with active mortgage charge."""
        result = dee_pipeline.process_document(
            file_input=ENCUMBRANCE_CERTIFICATE_MORTGAGE_TEXT,
            document_type=DocumentType.ENCUMBRANCE_CERTIFICATE,
            document_id="doc-test-002",
            property_id="prop-test-hyd-01",
        )

        self.assertEqual(result.status, DocumentStatus.EXTRACTED)
        entities = result.aiExtractedDataJson
        self.assertEqual(entities.document_type, DocumentType.ENCUMBRANCE_CERTIFICATE)
        self.assertGreaterEqual(len(entities.encumbrances), 1)

        enc = entities.encumbrances[0]
        self.assertEqual(enc.encumbrance_type.value, "MORTGAGE")
        self.assertEqual(enc.holder_name, "HDFC Bank Ltd")
        self.assertEqual(enc.amount, 15000000.0)
        self.assertFalse(enc.is_cleared)

        # Downstream DeedHistoryEvent must record MORTGAGE_RELEASE with status PENDING
        mort_event = next((e for e in result.deedHistoryEvents if e.eventType == DeedEventType.MORTGAGE_RELEASE), None)
        self.assertIsNotNone(mort_event)
        self.assertEqual(mort_event.status, DeedEventStatus.PENDING)

    def test_03_degraded_scan_manual_ops_routing(self):
        """Test degraded scan triggers below-threshold routing to manual review queue."""
        result = dee_pipeline.process_document(
            file_input=DEGRADED_SCAN_TEXT,
            document_type=DocumentType.SALE_DEED,
            document_id="doc-test-003",
            property_id="prop-test-degraded",
        )

        # Must route to REVIEWING with requiresManualReview = True
        self.assertEqual(result.status, DocumentStatus.REVIEWING)
        self.assertTrue(result.requiresManualReview)
        self.assertLess(result.aiConfidenceScore, 0.85)
        self.assertIsNotNone(result.aiExtractedDataJson.suggested_resolution)
        self.assertIn("manual", result.aiExtractedDataJson.suggested_resolution.lower())

    def test_04_pii_masking_non_negotiable(self):
        """Verify Indian PII (Aadhaar & PAN) is strictly masked and never raw."""
        raw_text = "Seller PAN: ABCDE1234F, Aadhaar: 9812 3456 7890 sold land to Buyer PAN: PQRST5678M"
        masked_text, token_map = mask_pii(raw_text)

        # Raw values must not appear in masked text
        self.assertNotIn("9812 3456 7890", masked_text)
        self.assertNotIn("ABCDE1234F", masked_text)
        self.assertNotIn("PQRST5678M", masked_text)

        # Mask tokens must be present
        self.assertIn("XXXX-XXXX-7890", masked_text)
        self.assertIn("AB***F", masked_text)
        self.assertEqual(len(token_map), 3)

    def test_05_sse_status_streaming(self):
        """Verify real-time SSE pipeline events dispatch cleanly with progress updates."""
        events_captured = []
        dee_pipeline.subscribe_events(lambda e: events_captured.append(e))

        dee_pipeline.process_document(
            file_input=SALE_DEED_CLEAN_TEXT,
            document_type=DocumentType.SALE_DEED,
            document_id="doc-test-sse",
            property_id="prop-test-sse",
        )

        stages = [e.stage for e in events_captured]
        self.assertIn(DeePipelineStage.QUEUED, stages)
        self.assertIn(DeePipelineStage.OCR_IN_PROGRESS, stages)
        self.assertIn(DeePipelineStage.EXTRACTION_IN_PROGRESS, stages)
        self.assertIn(DeePipelineStage.COMPLETED, stages)

    def test_06_dynamic_multi_city_pune_deed(self):
        """Verify zero hardcoding on non-Bangalore document (Pune, Maharashtra 2018 deed)."""
        result = dee_pipeline.process_document(
            file_input=PUNE_SALE_DEED_TEXT,
            document_type=DocumentType.SALE_DEED,
            document_id="doc-test-pune-006",
            property_id="prop-test-pune-01",
        )

        # 1. Pipeline execution status
        self.assertEqual(result.status, DocumentStatus.EXTRACTED)
        self.assertFalse(result.requiresManualReview)
        self.assertGreaterEqual(result.aiConfidenceScore, 0.85)

        # 2. Strict entity matching - exclusively Pune data
        entities = result.aiExtractedDataJson
        buyer = next((o for o in entities.owners if o.party_type.value == "GRANTEE_BUYER"), None)
        seller = next((o for o in entities.owners if o.party_type.value == "GRANTOR_SELLER"), None)

        self.assertIsNotNone(buyer)
        self.assertEqual(buyer.name, "RAJESH DATTATRAY PATIL")
        self.assertEqual(buyer.relation_type, "S/o")
        self.assertIn("BC***L", buyer.pan_masked)

        self.assertIsNotNone(seller)
        self.assertEqual(seller.name, "SURESH RAMCHANDRA JOSHI")

        self.assertEqual(entities.survey_number.survey_no, "48/3B")
        self.assertEqual(entities.survey_number.village, "Balewadi")
        self.assertEqual(entities.survey_number.taluk, "Haveli")
        self.assertEqual(entities.survey_number.district, "Pune")
        self.assertEqual(entities.survey_number.state, "Maharashtra")

        self.assertEqual(entities.area.carpet_area_sqft, 850.0)
        self.assertEqual(entities.area.super_built_up_sqft, 1120.0)
        self.assertEqual(entities.sale_consideration_inr, 7500000.0)
        self.assertEqual(entities.stamp_duty_paid_inr, 450000.0)

        # 3. Dynamic Year and Volume (2018, NOT 2024!)
        self.assertGreaterEqual(len(result.deedHistoryEvents), 1)
        deed_event = result.deedHistoryEvents[0]
        self.assertEqual(deed_event.eventType, DeedEventType.SALE_DEED)
        self.assertEqual(deed_event.year, 2018)
        self.assertIn("PNE-HVL-08341/2018-19", deed_event.registrationVolume)

        # 4. Confirm complete absence of hardcoded Bangalore / Prestige data
        dump_str = str(result.model_dump())
        self.assertNotIn("Prestige", dump_str)
        self.assertNotIn("Bengaluru", dump_str)
        self.assertNotIn("142/2A", dump_str)
        self.assertNotIn("1402", dump_str)

    def test_07_configurable_threshold(self):
        """Verify confidence threshold is dynamically configurable."""
        from pipelines.dee.pipeline import DeePipeline
        # Set strict threshold to 0.99
        strict_pipeline = DeePipeline(confidence_threshold=0.99)
        result = strict_pipeline.process_document(
            file_input=SALE_DEED_CLEAN_TEXT,
            document_type=DocumentType.SALE_DEED,
            document_id="doc-test-strict",
            property_id="prop-test-strict",
        )

        # Even with high score (~0.95), threshold 0.99 routes to manual review
        self.assertEqual(result.status, DocumentStatus.REVIEWING)
        self.assertTrue(result.requiresManualReview)
        self.assertIn("approval threshold (99%)", result.aiExtractedDataJson.suggested_resolution)

    def test_08_phase0_sqs_message_contract_and_processing(self):
        """Phase 0 & 1: Verify SQS message contract parsing and S3 file retrieval/processing."""
        import tempfile
        # Write test document to a temporary file simulating S3 key
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False, encoding="utf-8") as tmp:
            tmp.write(SALE_DEED_CLEAN_TEXT)
            tmp_path = tmp.name

        try:
            sqs_payload = DeeSqsMessagePayload(
                s3_bucket="namasthetu-legal-docs-prod",
                s3_key=tmp_path,
                document_type=DocumentType.SALE_DEED,
                property_id="prop-sqs-blr-101",
                version_id="ver-uuid-9812-41a",
                document_id="doc-sqs-blr-101",
                mime_type="text/plain",
            )

            # Process through worker SQS interface
            result = dee_pipeline.process_sqs_message(sqs_payload)
            self.assertEqual(result.document_id, "doc-sqs-blr-101")
            self.assertEqual(result.property_id, "prop-sqs-blr-101")
            self.assertEqual(result.status, DocumentStatus.EXTRACTED)
            self.assertFalse(result.requiresManualReview)
            self.assertEqual(result.aiExtractedDataJson.survey_number.survey_no, "142/2A")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_09_phase0_lqa_and_vie_consumer_contracts(self):
        """Phase 0: Verify downstream LQA (Listing Auditor) and VIE (Valuation) contracts."""
        result = dee_pipeline.process_document(
            file_input=SALE_DEED_CLEAN_TEXT,
            document_type=DocumentType.SALE_DEED,
            document_id="doc-test-contracts",
            property_id="prop-test-blr-contracts",
        )
        entities = result.aiExtractedDataJson

        # 1. Listing Quality Auditor (LQA) Contract
        lqa_data = entities.to_lqa_contract()
        self.assertEqual(lqa_data["document_type"], "SALE_DEED")
        self.assertIn("DR. VIKRAMADITYA R. RAO", lqa_data["owner_names"])
        self.assertEqual(lqa_data["survey_no"], "142/2A")
        self.assertEqual(lqa_data["carpet_area_sqft"], 1950.0)
        self.assertEqual(lqa_data["active_encumbrances_count"], 0)

        # 2. Valuation Intelligence Engine (VIE) Contract
        vie_features = entities.to_vie_features()
        self.assertEqual(vie_features["carpet_area_sqft"], 1950.0)
        self.assertEqual(vie_features["super_built_up_sqft"], 2450.0)
        self.assertEqual(vie_features["execution_year"], 2024)
        self.assertEqual(vie_features["sale_consideration_inr"], 28500000.0)
        self.assertFalse(vie_features["has_active_encumbrance"])

    def test_10_phase4_sse_last_event_id_reconnect(self):
        """Phase 4: Verify SSE status streaming and auto-reconnect using last-event-id."""
        doc_id = "doc-test-sse-reconnect"
        dee_pipeline.process_document(
            file_input=SALE_DEED_CLEAN_TEXT,
            document_type=DocumentType.SALE_DEED,
            document_id=doc_id,
            property_id="prop-test-sse-reconnect",
        )

        all_events = dee_pipeline.get_events_since(doc_id)
        self.assertGreaterEqual(len(all_events), 4)

        # Simulate client disconnect after 2nd event
        second_event_id = all_events[1].event_id

        # Reconnect with last-event-id
        replayed_events = dee_pipeline.get_events_since(doc_id, last_event_id=second_event_id)
        self.assertEqual(len(replayed_events), len(all_events) - 2)
        self.assertEqual(replayed_events[0].event_id, all_events[2].event_id)

        # Verify wire-format chunks
        chunks = dee_pipeline.get_sse_chunks_since(doc_id, last_event_id=second_event_id)
        self.assertEqual(len(chunks), len(replayed_events))
        self.assertTrue(chunks[0].startswith(f"id: {all_events[2].event_id}\n"))
        self.assertIn("data: {", chunks[0])

    def test_11_phase5_continuous_learning_loop_and_retraining_format(self):
        """Phase 5: Verify labeled event capture and ops-reviewer correction write-back."""
        dee_learning_collector.clear_archive()

        doc_id = "doc-test-learn-loop"
        result = dee_pipeline.process_document(
            file_input=SALE_DEED_CLEAN_TEXT,
            document_type=DocumentType.SALE_DEED,
            document_id=doc_id,
            property_id="prop-test-learn-loop",
        )

        # 1. Verify initial model extraction captured automatically
        events = dee_learning_collector.get_events_for_document(doc_id)
        self.assertEqual(len(events), 1)
        initial_sample = events[0]
        self.assertEqual(initial_sample.event_type, DeeLearningEventType.EXTRACTION_INITIAL)
        self.assertEqual(initial_sample.document_id, doc_id)

        # 2. Simulate manual ops reviewer correction (§12.3 step 8)
        corrected_entities = result.aiExtractedDataJson.model_copy(deep=True)
        # Fix a slight survey number typo
        corrected_entities.survey_number.survey_no = "142/2A-Amended"

        correction_sample = dee_learning_collector.record_ops_correction(
            original_result=result,
            corrected_entities=corrected_entities,
            reviewer_id="ops_reviewer_42",
            reviewer_notes="Verified via sub-registrar index II survey amendment",
        )

        self.assertEqual(correction_sample.event_type, DeeLearningEventType.OPS_CORRECTED)
        self.assertIn("survey_number", correction_sample.field_deltas)
        self.assertEqual(
            correction_sample.field_deltas["survey_number"]["corrected"]["survey_no"],
            "142/2A-Amended",
        )

        # 3. Export batch formatted for Kubeflow/Metaflow retraining
        training_dataset = dee_learning_collector.export_dataset()
        self.assertEqual(len(training_dataset), 2)
        corrected_entry = next((e for e in training_dataset if e["has_human_correction"]), None)
        self.assertIsNotNone(corrected_entry)
        self.assertEqual(
            corrected_entry["target_ground_truth"]["survey_number"]["survey_no"],
            "142/2A-Amended",
        )

    def test_12_multilingual_kannada_and_hindi_extraction(self):
        """Verify multilingual extraction on Kannada and Hindi legal deeds."""
        # 1. Kannada Extraction
        res_kan = dee_pipeline.process_document(
            file_input=KANNADA_TEST_DEED,
            document_type=DocumentType.SALE_DEED,
            document_id="doc-test-kannada",
            property_id="prop-test-mys-01",
        )
        self.assertTrue(res_kan.aiExtractedDataJson.is_regional_script)
        self.assertEqual(res_kan.aiExtractedDataJson.regional_language, "Kannada")
        self.assertEqual(res_kan.aiExtractedDataJson.survey_number.survey_no, "84/3")
        self.assertEqual(res_kan.aiExtractedDataJson.area.carpet_area_sqft, 1200.0)
        self.assertEqual(res_kan.aiExtractedDataJson.sale_consideration_inr, 4800000.0)
        kan_buyers = [o for o in res_kan.aiExtractedDataJson.owners if o.party_type.value == "GRANTEE_BUYER"]
        self.assertGreaterEqual(len(kan_buyers), 1)
        self.assertIn("ಮಂಜುನಾಥ", kan_buyers[0].name)

        # 2. Hindi Extraction
        res_hin = dee_pipeline.process_document(
            file_input=HINDI_TEST_DEED,
            document_type=DocumentType.SALE_DEED,
            document_id="doc-test-hindi",
            property_id="prop-test-indore-01",
        )
        self.assertTrue(res_hin.aiExtractedDataJson.is_regional_script)
        self.assertIn(res_hin.aiExtractedDataJson.regional_language, ("Hindi", "Devanagari (Marathi/Hindi)"))
        self.assertEqual(res_hin.aiExtractedDataJson.survey_number.survey_no, "114/2")
        self.assertEqual(res_hin.aiExtractedDataJson.area.carpet_area_sqft, 1500.0)
        self.assertEqual(res_hin.aiExtractedDataJson.sale_consideration_inr, 5500000.0)
        hin_buyers = [o for o in res_hin.aiExtractedDataJson.owners if o.party_type.value == "GRANTEE_BUYER"]
        self.assertGreaterEqual(len(hin_buyers), 1)
        self.assertIn("अमित कुमार वर्मा", hin_buyers[0].name)

    def test_13_dataset_manager_lifecycle_and_cleanup(self):
        """Verify dataset discovery, train/test split, and fine-tuning export with complete cleanup."""
        import tempfile
        import json

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create a mock file and annotation inside temporary directory
            mock_doc = os.path.join(tmp_dir, "deed_01.txt")
            with open(mock_doc, "w", encoding="utf-8") as f:
                f.write(SALE_DEED_CLEAN_TEXT)

            mock_ann = os.path.join(tmp_dir, "ground_truth.json")
            with open(mock_ann, "w", encoding="utf-8") as f:
                json.dump([{"file_name": "deed_01.txt", "document_type": "SALE_DEED"}], f)

            items = dee_dataset_manager.load_dataset(tmp_dir)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].file_name, "deed_01.txt")

            train, val, test = dee_dataset_manager.split_dataset(items, 1.0, 0.0, 0.0)
            self.assertEqual(len(train), 1)


if __name__ == "__main__":
    unittest.main()


