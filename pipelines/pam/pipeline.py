"""
PAM (Photo Analysis Module) — Pipeline Orchestrator.

Orchestrates:
1. Ingestion: files, bytes, or S3 references
2. EXIF & Cadastral Anti-Spoofing 25m check (exif.py)
3. Vision classification & defect detection (vision_engine.py)
4. Inspector hint reconciliation (CONFIRMED vs OVERRIDDEN)
5. Condition scoring & multi-photo batch aggregation (condition_scorer.py)
6. 1:1 Schema formatting for:
   - model InspectionPhoto (src/db/schema.prisma lines 964-994)
   - model Inspection (src/db/schema.prisma lines 900-960)
   - DigitalTwin InspectionDefectPin (digital_twin/DynamicThreeTwinViewer.tsx)
   - PIP inspection.defects[] and scores_by_category payload
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from PIL import Image

from pipelines.pam.models import (
    RoomCategory,
    DefectSeverity,
    InspectionStatus,
    PhotoAnalysisResult,
    InspectionBatchAnalysisResult,
    PamSqsMessagePayload,
    DetectedDefect,
)
from pipelines.pam.exif import ExifProcessor
from pipelines.pam.vision_engine import PamVisionEngine
from pipelines.pam.condition_scorer import ConditionScorer


class PamPipeline:
    """Core Photo Analysis Module orchestrator."""

    def __init__(self, use_torch: bool = True):
        self.vision_engine = PamVisionEngine(use_torch=use_torch)

    def analyze_photo(
        self,
        image_input: Union[str, bytes, Image.Image],
        inspection_id: str,
        photo_url: str,
        photo_id: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        room_label_hint: Optional[str] = None,
        target_coords: Optional[Tuple[float, float]] = None,
        fallback_coords: Optional[Tuple[float, float]] = None,
        defect_hint: Optional[str] = None,
    ) -> PhotoAnalysisResult:
        """
        Analyze a single inspection photo.
        
        Args:
            image_input: File path, bytes, or PIL Image.
            inspection_id: Target inspection ID.
            photo_url: S3 URL or path.
            photo_id: Optional ID for the photo.
            thumbnail_url: Optional thumbnail URL.
            room_label_hint: Inspector-entered room label.
            target_coords: Optional (lat, lon) cadastral property centroid for 25m check.
            fallback_coords: Optional (lat, lon) if EXIF is stripped.
            defect_hint: Optional defect hint.
        """
        start_time = time.perf_counter()

        # Step 1: EXIF & Anti-Spoofing Geotag Verification
        exif_meta = ExifProcessor.parse_exif(
            image_input,
            target_coords=target_coords,
            fallback_coords=fallback_coords,
        )

        # Step 2: Vision Analysis (Room Classification, Defect & Fixture Detection)
        vision_pred = self.vision_engine.analyze_image(
            image_input,
            room_hint=room_label_hint,
            defect_hint=defect_hint,
        )

        # Step 3: Inspector Hint Reconciliation
        reconciliation_action = "CONFIRMED"
        if room_label_hint:
            norm_hint = room_label_hint.strip().lower().replace(" ", "_")
            hint_cat = self.vision_engine.INSPECTOR_HINT_MAP.get(norm_hint)
            if hint_cat:
                if hint_cat == vision_pred.room_category:
                    reconciliation_action = "CONFIRMED"
                elif vision_pred.room_confidence >= 0.80:
                    reconciliation_action = "OVERRIDDEN"
                else:
                    reconciliation_action = "RECONCILED"

        # Step 4: Condition Scoring
        condition_scores = ConditionScorer.compute_photo_condition(vision_pred.defects)

        # Step 5: Primary Defect Aggregation for InspectionPhoto columns
        has_defect = len(vision_pred.defects) > 0
        primary_severity: Optional[DefectSeverity] = None
        primary_type: Optional[str] = None
        primary_bbox_json: Optional[Dict[str, Any]] = None

        if has_defect:
            # Sort defects by severity (CRITICAL > HIGH > MEDIUM > LOW)
            severity_order = {
                DefectSeverity.CRITICAL: 4,
                DefectSeverity.HIGH: 3,
                DefectSeverity.MEDIUM: 2,
                DefectSeverity.LOW: 1,
            }
            sorted_defects = sorted(
                vision_pred.defects,
                key=lambda d: severity_order.get(d.severity, 0),
                reverse=True,
            )
            top_defect = sorted_defects[0]
            primary_severity = top_defect.severity
            primary_type = top_defect.defect_type
            if top_defect.bounding_box:
                primary_bbox_json = top_defect.bounding_box.to_dict()

        total_latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        return PhotoAnalysisResult(
            id=photo_id,
            inspection_id=inspection_id,
            photo_url=photo_url,
            thumbnail_url=thumbnail_url,
            room_category=vision_pred.room_category,
            room_confidence=vision_pred.room_confidence,
            inspector_room_label_hint=room_label_hint,
            reconciliation_action=reconciliation_action,
            latitude=exif_meta.latitude,
            longitude=exif_meta.longitude,
            exif_timestamp=exif_meta.timestamp,
            is_geotag_valid=exif_meta.is_geotag_valid,
            geofence_distance_meters=exif_meta.distance_meters,
            has_defect=has_defect,
            defect_severity=primary_severity,
            defect_type=primary_type,
            defect_bounding_box_json=primary_bbox_json,
            defects=vision_pred.defects,
            fixtures=vision_pred.fixtures,
            condition_scores=condition_scores,
            inference_latency_ms=total_latency_ms,
            analyzed_at=datetime.now(timezone.utc),
        )

    def analyze_inspection_batch(
        self,
        inspection_id: str,
        property_id: str,
        photos: List[Dict[str, Any]],
        inspector_id: Optional[str] = None,
        target_coords: Optional[Tuple[float, float]] = None,
        inspector_scores: Optional[Dict[str, Union[int, float]]] = None,
        verified_points_count: int = 80,
    ) -> InspectionBatchAnalysisResult:
        """
        Analyze a complete batch of photos belonging to an inspection.
        
        Args:
            inspection_id: Inspection PK.
            property_id: Property PK.
            photos: List of photo dicts with keys:
                    {'image_input', 'photo_url', 'photo_id', 'room_label_hint', 'defect_hint'}
            inspector_id: Optional inspector profile ID.
            target_coords: Optional (lat, lon) of property centroid for geotag validation.
            inspector_scores: Optional dictionary of inspector-assigned scores per category.
            verified_points_count: Verified checklist points (out of 80).
        """
        photo_results: List[PhotoAnalysisResult] = []

        for p_data in photos:
            res = self.analyze_photo(
                image_input=p_data["image_input"],
                inspection_id=inspection_id,
                photo_url=p_data.get("photo_url", f"https://s3.amazonaws.com/inspections/{inspection_id}/{p_data.get('photo_id', 'photo')}.jpg"),
                photo_id=p_data.get("photo_id"),
                thumbnail_url=p_data.get("thumbnail_url"),
                room_label_hint=p_data.get("room_label_hint"),
                target_coords=target_coords,
                fallback_coords=p_data.get("fallback_coords"),
                defect_hint=p_data.get("defect_hint"),
            )
            photo_results.append(res)

        # Aggregate batch metrics
        (
            score_overall,
            score_structural,
            score_electrical,
            score_plumbing,
            score_finishes,
            score_exterior,
            seepage_detected,
            key_findings,
            summary,
            qa_status,
            requires_manual_review,
            qa_review_reason,
        ) = ConditionScorer.aggregate_inspection_scores(photo_results, inspector_scores=inspector_scores)

        photos_with_defects = sum(1 for p in photo_results if p.has_defect)
        total_defects = sum(len(p.defects) for p in photo_results)

        return InspectionBatchAnalysisResult(
            inspection_id=inspection_id,
            property_id=property_id,
            inspector_id=inspector_id,
            total_photos=len(photo_results),
            photos_with_defects=photos_with_defects,
            total_defects_count=total_defects,
            score_overall=score_overall,
            score_structural=score_structural,
            score_electrical=score_electrical,
            score_plumbing=score_plumbing,
            score_finishes=score_finishes,
            score_locality=inspector_scores.get("locality") if inspector_scores else None,
            score_cadastral=inspector_scores.get("cadastral") if inspector_scores else None,
            seepage_detected=seepage_detected,
            verified_points_count=verified_points_count,
            summary=summary,
            key_findings=key_findings,
            qa_status=qa_status,
            requires_manual_review=requires_manual_review,
            qa_review_reason=qa_review_reason,
            photo_results=photo_results,
        )

    def process_sqs_message(
        self,
        payload: PamSqsMessagePayload,
        image_bytes: bytes,
    ) -> PhotoAnalysisResult:
        """
        Process an asynchronous message received from SQS / Kafka upload worker.
        """
        target_coords = None
        if payload.target_latitude is not None and payload.target_longitude is not None:
            target_coords = (payload.target_latitude, payload.target_longitude)

        photo_url = f"s3://{payload.s3_bucket}/{payload.s3_key}"

        return self.analyze_photo(
            image_input=image_bytes,
            inspection_id=payload.inspection_id,
            photo_url=photo_url,
            photo_id=payload.photo_id,
            room_label_hint=payload.room_label_hint,
            target_coords=target_coords,
        )


pam_pipeline = PamPipeline()
