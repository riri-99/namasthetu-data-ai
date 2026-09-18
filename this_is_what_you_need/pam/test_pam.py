"""
PAM (Photo Analysis Module) — Comprehensive Automated Unit Tests.
"""

import io
import unittest
from PIL import Image, ImageDraw

from this_is_what_you_need.common import haversine_distance_meters
from this_is_what_you_need.pam.pipeline import (
    DefectCategory,
    DefectSeverity,
    InspectionStatus,
    PamPipeline,
    RoomCategory,
    pam_pipeline,
)


def _create_synthetic_test_image(defect_patch: bool = False) -> bytes:
    img = Image.new("RGB", (300, 300), color=(200, 200, 200))
    if defect_patch:
        draw = ImageDraw.Draw(img)
        draw.rectangle([180, 180, 280, 280], fill=(20, 20, 20))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestPamPipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = PamPipeline()

    def test_01_schema_enums(self):
        self.assertEqual(len(RoomCategory), 10)
        self.assertEqual(len(DefectSeverity), 4)
        self.assertEqual(len(InspectionStatus), 7)

    def test_02_haversine_distance(self):
        dist = haversine_distance_meters(13.342150, 77.712340, 13.342250, 77.712340)
        self.assertLessEqual(dist, 25.0)

    def test_03_clean_photo_analysis(self):
        img_bytes = _create_synthetic_test_image(defect_patch=False)
        res = self.pipeline.analyze_photo(
            image_input=img_bytes,
            inspection_id="insp_101",
            photo_url="https://s3.amazonaws.com/test.jpg",
            room_label_hint="Living Room",
        )
        self.assertEqual(res.room_category, RoomCategory.LIVING_ROOM)
        self.assertFalse(res.has_defect)
        self.assertEqual(res.condition_scores.overall, 100)

    def test_04_defect_photo_analysis(self):
        img_bytes = _create_synthetic_test_image(defect_patch=True)
        res = self.pipeline.analyze_photo(
            image_input=img_bytes,
            inspection_id="insp_102",
            photo_url="https://s3.amazonaws.com/test_defect.jpg",
            defect_hint="seepage",
        )
        self.assertTrue(res.has_defect)
        self.assertEqual(res.defect_type, "seepage")
        self.assertLess(res.condition_scores.overall, 100)

    def test_05_prisma_mapping(self):
        img_bytes = _create_synthetic_test_image(defect_patch=False)
        res = self.pipeline.analyze_photo(
            image_input=img_bytes,
            inspection_id="insp_103",
            photo_url="https://s3.amazonaws.com/test.jpg",
        )
        prisma_row = res.to_prisma_inspection_photo()
        self.assertIn("roomCategory", prisma_row)
        self.assertIn("isGeotagValid", prisma_row)

    def test_06_batch_inspection_aggregation(self):
        img1 = _create_synthetic_test_image(defect_patch=False)
        img2 = _create_synthetic_test_image(defect_patch=True)
        photos = [
            {"image_input": img1, "photo_id": "p1", "room_label_hint": "Living Room"},
            {"image_input": img2, "photo_id": "p2", "defect_hint": "seepage"},
        ]
        batch_res = self.pipeline.analyze_inspection_batch(
            inspection_id="insp_batch_01",
            property_id="prop_01",
            photos=photos,
        )
        self.assertEqual(batch_res.total_photos, 2)
        self.assertTrue(batch_res.seepage_detected)
        self.assertIn("scoreOverall", batch_res.to_prisma_inspection_update())


if __name__ == "__main__":
    unittest.main()
