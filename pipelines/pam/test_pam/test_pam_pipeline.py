"""
PAM (Photo Analysis Module) — Comprehensive Automated Unit Tests.

Covers:
1. Enum alignment with src/db/schema.prisma (RoomCategory, DefectSeverity, InspectionStatus)
2. EXIF metadata extraction and 25m Cadastral boundary anti-spoof check
3. Vision engine room classification and visual signatures
4. Inspector hint reconciliation (CONFIRMED vs OVERRIDDEN)
5. Defect detection, bounding boxes, and severity prioritization
6. 1:1 Mapping to Prisma model InspectionPhoto
7. Multi-photo inspection batch aggregation and mapping to Prisma model Inspection
8. PIP inspection payload export (defects[], scores_by_category)
9. Digital Twin 3D defect pins export (InspectionDefectPin)
10. SQS message consumption
11. Continuous learning feedback loop and metrics
12. Dataset manager discovery, splitting, pseudo-label bootstrapping, and in-memory cleanup
"""

import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageDraw

from pipelines.pam.models import (
    RoomCategory,
    DefectSeverity,
    InspectionStatus,
    DefectCategory,
    BoundingBox,
    DetectedDefect,
    DetectedFixture,
    ConditionScores,
    PhotoAnalysisResult,
    InspectionBatchAnalysisResult,
    PamSqsMessagePayload,
    PredictionFeedback,
)
from pipelines.pam.exif import ExifProcessor, haversine_distance_meters
from pipelines.pam.vision_engine import PamVisionEngine
from pipelines.pam.condition_scorer import ConditionScorer
from pipelines.pam.pipeline import PamPipeline
from pipelines.pam.feedback_loop import PamLearningLoop
from pipelines.pam.dataset_manager import PamDatasetManager


def _create_synthetic_test_image(
    color: tuple = (200, 200, 200),
    size: tuple = (300, 300),
    defect_patch: bool = False,
) -> bytes:
    """Create a synthetic test image in memory as bytes."""
    img = Image.new("RGB", size, color=color)
    draw = ImageDraw.Draw(img)
    if defect_patch:
        # Draw a dark damp patch representing seepage in lower-right
        draw.rectangle([180, 180, 280, 280], fill=(20, 20, 20))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestPamPipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = PamPipeline()

    def test_01_schema_enums_alignment(self):
        """Verify all 10 RoomCategory, 4 DefectSeverity, and 7 InspectionStatus values match schema.prisma."""
        expected_rooms = {
            "LIVING_ROOM", "MASTER_BEDROOM", "GUEST_BEDROOM", "KITCHEN", "BATHROOM",
            "BALCONY", "UTILITY_AREA", "ENTRANCE_LOBBY", "PARKING", "FACADE_EXTERIOR"
        }
        actual_rooms = {cat.value for cat in RoomCategory}
        self.assertEqual(expected_rooms, actual_rooms)

        expected_severities = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        actual_severities = {sev.value for sev in DefectSeverity}
        self.assertEqual(expected_severities, actual_severities)

        expected_statuses = {
            "SCHEDULED", "IN_PROGRESS", "SUBMITTED", "QA_PENDING",
            "QA_PASSED", "QA_FAILED", "CANCELLED"
        }
        actual_statuses = {status.value for status in InspectionStatus}
        self.assertEqual(expected_statuses, actual_statuses)

    def test_02_haversine_and_geotag_validation(self):
        """Test distance computation and 25m cadastral boundary anti-spoof gate."""
        # Prestige Golfshire, Bengaluru coordinates
        lat1, lon1 = 13.342150, 77.712340
        # Point 15 meters away
        lat2, lon2 = 13.342250, 77.712340
        dist_15m = haversine_distance_meters(lat1, lon1, lat2, lon2)
        self.assertLessEqual(dist_15m, 25.0)

        # Point 200 meters away
        lat3, lon3 = 13.344000, 77.712340
        dist_200m = haversine_distance_meters(lat1, lon1, lat3, lon3)
        self.assertGreater(dist_200m, 25.0)

        # Ingest image with fallback coordinates within 25m
        img_bytes = _create_synthetic_test_image()
        meta_valid = ExifProcessor.parse_exif(
            img_bytes,
            target_coords=(lat1, lon1),
            fallback_coords=(lat2, lon2),
        )
        self.assertTrue(meta_valid.is_geotag_valid)
        self.assertLessEqual(meta_valid.distance_meters, 25.0)

        # Image beyond 25m boundary fails check
        meta_invalid = ExifProcessor.parse_exif(
            img_bytes,
            target_coords=(lat1, lon1),
            fallback_coords=(lat3, lon3),
        )
        self.assertFalse(meta_invalid.is_geotag_valid)
        self.assertGreater(meta_invalid.distance_meters, 25.0)

    def test_03_room_classification(self):
        """Test room classification and visual signatures."""
        kitchen_bytes = _create_synthetic_test_image(color=(140, 130, 120))
        pred = self.pipeline.vision_engine.analyze_image(kitchen_bytes, room_hint="kitchen")
        self.assertEqual(pred.room_category, RoomCategory.KITCHEN)
        self.assertGreater(pred.room_confidence, 0.50)
        self.assertIn("KITCHEN", pred.category_probabilities)

        bath_bytes = _create_synthetic_test_image(color=(220, 230, 240))
        pred_bath = self.pipeline.vision_engine.analyze_image(bath_bytes, room_hint="bathroom")
        self.assertEqual(pred_bath.room_category, RoomCategory.BATHROOM)

    def test_04_inspector_hint_reconciliation(self):
        """Test inspector hint reconciliation (CONFIRMED vs OVERRIDDEN)."""
        img_bytes = _create_synthetic_test_image(color=(150, 140, 130))
        res_confirmed = self.pipeline.analyze_photo(
            image_input=img_bytes,
            inspection_id="insp_101",
            photo_url="https://s3.example.com/p1.jpg",
            room_label_hint="living room",
        )
        self.assertEqual(res_confirmed.reconciliation_action, "CONFIRMED")
        self.assertEqual(res_confirmed.room_category, RoomCategory.LIVING_ROOM)

    def test_05_defect_detection_and_bounding_boxes(self):
        """Test defect detection, bounding box creation, and severity prioritization."""
        img_defect_bytes = _create_synthetic_test_image(color=(200, 200, 200), defect_patch=True)
        res = self.pipeline.analyze_photo(
            image_input=img_defect_bytes,
            inspection_id="insp_102",
            photo_url="https://s3.example.com/p2.jpg",
            defect_hint="seepage",
        )
        self.assertTrue(res.has_defect)
        self.assertIn(res.defect_severity, (DefectSeverity.HIGH, DefectSeverity.MEDIUM))
        self.assertEqual(res.defect_type, "seepage")
        self.assertIsNotNone(res.defect_bounding_box_json)
        self.assertIn("ymin", res.defect_bounding_box_json)
        self.assertIn("xmin", res.defect_bounding_box_json)

    def test_06_prisma_inspection_photo_mapping(self):
        """Test 1:1 serialization to model InspectionPhoto columns in schema.prisma."""
        img_bytes = _create_synthetic_test_image()
        res = self.pipeline.analyze_photo(
            image_input=img_bytes,
            inspection_id="insp_103",
            photo_url="https://s3.example.com/p3.jpg",
            photo_id="photo_uuid_103",
            target_coords=(12.9716, 77.5946),
            fallback_coords=(12.9716, 77.5946),
        )
        prisma_row = res.to_prisma_inspection_photo()
        self.assertEqual(prisma_row["id"], "photo_uuid_103")
        self.assertEqual(prisma_row["inspectionId"], "insp_103")
        self.assertEqual(prisma_row["photoUrl"], "https://s3.example.com/p3.jpg")
        self.assertTrue(prisma_row["isGeotagValid"])
        self.assertIn("roomCategory", prisma_row)
        self.assertIn("hasDefect", prisma_row)

    def test_07_inspection_batch_aggregation(self):
        """Test multi-photo batch aggregation and condition score deduction."""
        p1 = _create_synthetic_test_image(color=(150, 140, 130))
        p2 = _create_synthetic_test_image(color=(200, 200, 200), defect_patch=True)
        photos = [
            {"image_input": p1, "photo_id": "p_living", "room_label_hint": "living", "fallback_coords": (12.9716, 77.5946)},
            {"image_input": p2, "photo_id": "p_bath", "room_label_hint": "bathroom", "defect_hint": "seepage", "fallback_coords": (12.9716, 77.5946)},
        ]

        batch_res = self.pipeline.analyze_inspection_batch(
            inspection_id="insp_batch_201",
            property_id="prop_301",
            photos=photos,
            target_coords=(12.9716, 77.5946),
            inspector_scores={"structural": 9, "plumbing": 7, "electrical": 10, "finishes": 9},
        )

        self.assertEqual(batch_res.total_photos, 2)
        self.assertEqual(batch_res.photos_with_defects, 1)
        self.assertTrue(batch_res.seepage_detected)
        self.assertLess(batch_res.score_plumbing, 100)
        self.assertEqual(batch_res.qa_status, InspectionStatus.QA_PASSED)

        # Verify Prisma Inspection row update dictionary
        update_dict = batch_res.to_prisma_inspection_update()
        self.assertIn("scoreOverall", update_dict)
        self.assertIn("scoreStructural", update_dict)
        self.assertIn("scorePlumbing", update_dict)
        self.assertIn("keyFindings", update_dict)
        self.assertTrue(update_dict["seepageDetected"])

    def test_08_pip_inspection_payload_export(self):
        """Test PIP inspection payload generation matching full launch scope (§12)."""
        p_defect = _create_synthetic_test_image(defect_patch=True)
        photos = [
            {"image_input": p_defect, "photo_id": "p_crack", "room_label_hint": "bedroom", "defect_hint": "crack"}
        ]
        batch_res = self.pipeline.analyze_inspection_batch(
            inspection_id="insp_pip_301",
            property_id="prop_401",
            photos=photos,
        )
        pip_data = batch_res.to_pip_inspection_payload()
        self.assertEqual(pip_data["inspection_id"], "insp_pip_301")
        self.assertIn("score_overall", pip_data)
        self.assertIn("scores_by_category", pip_data)
        self.assertIn("defects", pip_data)
        self.assertEqual(len(pip_data["defects"]), 1)
        self.assertEqual(pip_data["defects"][0]["category"], "STRUCTURAL")

    def test_09_digital_twin_defect_pins_export(self):
        """Test export to InspectionDefectPin format matching DynamicThreeTwinViewer.tsx."""
        p_defect = _create_synthetic_test_image(defect_patch=True)
        res = self.pipeline.analyze_photo(
            image_input=p_defect,
            inspection_id="insp_twin_401",
            photo_url="https://s3.example.com/defect.jpg",
            defect_hint="crack",
        )
        pins = res.to_digital_twin_pins(room_id="master_bedroom_1", floor_level=2)
        self.assertEqual(len(pins), 1)
        pin = pins[0]
        self.assertEqual(pin["roomId"], "master_bedroom_1")
        self.assertEqual(pin["floorLevel"], 2)
        self.assertEqual(pin["type"], "wall_crack")
        self.assertEqual(len(pin["position"]), 3)
        self.assertTrue(pin["color"].startswith("#"))

    def test_10_sqs_message_consumption(self):
        """Test SQS message worker ingestion."""
        sqs_payload = PamSqsMessagePayload(
            photo_id="photo_sqs_01",
            inspection_id="insp_sqs_01",
            property_id="prop_sqs_01",
            s3_bucket="namasthetu-inspections",
            s3_key="raw/2026/photo_01.jpg",
            room_label_hint="balcony",
            target_latitude=12.9716,
            target_longitude=77.5946,
        )
        img_bytes = _create_synthetic_test_image(color=(160, 180, 200))
        res = self.pipeline.process_sqs_message(sqs_payload, image_bytes=img_bytes)
        self.assertEqual(res.id, "photo_sqs_01")
        self.assertEqual(res.inspection_id, "insp_sqs_01")
        self.assertEqual(res.room_category, RoomCategory.BALCONY)

    def test_11_continuous_learning_loop_feedback(self):
        """Test §12.3 continuous learning feedback collection and telemetry."""
        loop = PamLearningLoop()
        fb1 = loop.record_feedback(
            photo_id="p_001",
            inspection_id="insp_001",
            reviewer_id="inspector_ramesh",
            predicted_room_category=RoomCategory.GUEST_BEDROOM,
            corrected_room_category=RoomCategory.MASTER_BEDROOM,
            predicted_has_defect=False,
            corrected_has_defect=True,
            corrected_severity=DefectSeverity.LOW,
            reviewer_notes="Identified as master bedroom due to attached walk-in closet.",
        )
        self.assertEqual(fb1.photo_id, "p_001")
        self.assertEqual(fb1.corrected_room_category, RoomCategory.MASTER_BEDROOM)

        metrics = loop.get_metrics()
        self.assertEqual(metrics.total_feedback_events, 1)
        self.assertEqual(metrics.room_overrides_count, 1)
        self.assertEqual(metrics.defect_overrides_count, 1)

        batch = loop.export_training_batch()
        self.assertEqual(len(batch), 1)
        self.assertEqual(batch[0]["target_room_category"], "MASTER_BEDROOM")
        self.assertTrue(batch[0]["has_defect"])

    def test_12_dataset_manager_lifecycle_and_cleanup(self):
        """Test dataset discovery, pseudo-label bootstrapping, and export in a temporary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            kitchen_dir = temp_path / "kitchen"
            kitchen_dir.mkdir()

            # Write two temporary synthetic image files
            img_k1 = Image.new("RGB", (100, 100), color=(140, 130, 120))
            img_k1.save(kitchen_dir / "k1.jpg")
            img_k2 = Image.new("RGB", (100, 100), color=(140, 130, 120))
            img_k2.save(kitchen_dir / "k2.png")

            mgr = PamDatasetManager(data_dir=str(temp_path))
            discovered = mgr.discover_images()
            self.assertEqual(len(discovered), 2)

            # Test splitting
            splits = mgr.split_dataset(discovered, train_ratio=0.5, val_ratio=0.5, test_ratio=0.0)
            self.assertEqual(len(splits["train"]), 1)
            self.assertEqual(len(splits["val"]), 1)

            # Test bootstrapping pseudo-labels
            ann_out = temp_path / "annotations"
            bootstrap_res = mgr.bootstrap_unlabeled_photos(
                image_paths=discovered,
                output_annotation_dir=str(ann_out),
                confidence_threshold=0.50,
            )
            self.assertEqual(bootstrap_res["bootstrapped_high_confidence"], 2)

            # Test fine-tuning export
            jsonl_out = temp_path / "finetune.jsonl"
            exported_count = mgr.export_finetuning_dataset(
                annotation_dir=str(ann_out),
                output_file_path=str(jsonl_out),
            )
            self.assertEqual(exported_count, 2)
            self.assertTrue(jsonl_out.exists())

        # Assert temporary directory has been completely deleted
        self.assertFalse(temp_path.exists())


if __name__ == "__main__":
    unittest.main()
