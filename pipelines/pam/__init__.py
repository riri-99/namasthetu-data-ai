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
from pipelines.pam.pipeline import PamPipeline, pam_pipeline
from pipelines.pam.exif import ExifProcessor, ExifMetadata, haversine_distance_meters
from pipelines.pam.vision_engine import PamVisionEngine, VisionPrediction
from pipelines.pam.condition_scorer import ConditionScorer
from pipelines.pam.feedback_loop import PamLearningLoop, pam_learning_loop
from pipelines.pam.dataset_manager import PamDatasetManager

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
