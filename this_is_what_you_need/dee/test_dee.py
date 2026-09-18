"""
DEE (Document Extraction Engine) — Automated Unit Tests.
"""

import unittest
from this_is_what_you_need.dee.pipeline import (
    DeePipeline,
    DocumentStatus,
    DocumentType,
    dee_pipeline,
)


class TestDeePipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = DeePipeline()

    def test_01_document_enums(self):
        self.assertEqual(DocumentType.SALE_DEED.value, "SALE_DEED")
        self.assertEqual(DocumentStatus.VERIFIED.value, "VERIFIED")

    def test_02_extract_sale_deed(self):
        res = self.pipeline.process_document(
            file_input=b"%PDF-1.4 Simulated sale deed text for testing",
            document_type=DocumentType.SALE_DEED,
            document_id="doc_101",
            property_id="prop_101",
        )
        self.assertEqual(res.document_id, "doc_101")
        self.assertEqual(res.status, DocumentStatus.VERIFIED)
        self.assertEqual(res.aiExtractedDataJson.survey_number, "42/1")
        self.assertEqual(res.aiExtractedDataJson.consideration_amount_paise, 1500000000)
        self.assertFalse(res.aiExtractedDataJson.active_liens_detected)


if __name__ == "__main__":
    unittest.main()
