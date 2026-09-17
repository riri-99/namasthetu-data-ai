"""
PAM — Photo Analysis Module.

Embedded AI Service #2 for Namasthetu.
Implements:
- Room classification across 10 RoomCategory enums
- Condition scoring (structural, electrical, plumbing, finishes, exterior)
- Defect detection with bounding boxes (seepage, cracks, tiles, wiring)
- Anti-spoofing EXIF geotag 25m boundary verification
- Alignment with src/db/schema.prisma (InspectionPhoto, Inspection)
- Export to Digital Twin (InspectionDefectPin) and PIP payload
"""

from pam.models import (
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
from pam.pipeline import PamPipeline, pam_pipeline
from pam.exif import ExifProcessor, ExifMetadata, haversine_distance_meters
from pam.vision_engine import PamVisionEngine, VisionPrediction
from pam.condition_scorer import ConditionScorer
from pam.feedback_loop import PamLearningLoop, pam_learning_loop
from pam.dataset_manager import PamDatasetManager

__all__ = [
    "RoomCategory",
    "DefectSeverity",
    "InspectionStatus",
    "DefectCategory",
    "BoundingBox",
    "DetectedDefect",
    "DetectedFixture",
    "ConditionScores",
    "PhotoAnalysisResult",
    "InspectionBatchAnalysisResult",
    "PamSqsMessagePayload",
    "PredictionFeedback",
    "PamPipeline",
    "pam_pipeline",
    "ExifProcessor",
    "ExifMetadata",
    "haversine_distance_meters",
    "PamVisionEngine",
    "VisionPrediction",
    "ConditionScorer",
    "PamLearningLoop",
    "pam_learning_loop",
    "PamDatasetManager",
]
