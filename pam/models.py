"""
PAM (Photo Analysis Module) — Domain Models & Schema Contracts.

Strictly aligned with:
- Namasthetu Database Schema: src/db/schema.prisma (models InspectionPhoto, Inspection, enums RoomCategory, DefectSeverity, InspectionStatus)
- Digital Twin Viewer: digital_twin/DynamicThreeTwinViewer.tsx (InspectionDefectPin)
- PIP (Property Intelligence Profile) read-model: HYC-SCO-2026-3841 §12
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# 1. Enums strictly matching src/db/schema.prisma
# ============================================================================

class RoomCategory(str, Enum):
    """10-State Room Category enum matching src/db/schema.prisma lines 194-205."""
    LIVING_ROOM = "LIVING_ROOM"
    MASTER_BEDROOM = "MASTER_BEDROOM"
    GUEST_BEDROOM = "GUEST_BEDROOM"
    KITCHEN = "KITCHEN"
    BATHROOM = "BATHROOM"
    BALCONY = "BALCONY"
    UTILITY_AREA = "UTILITY_AREA"
    ENTRANCE_LOBBY = "ENTRANCE_LOBBY"
    PARKING = "PARKING"
    FACADE_EXTERIOR = "FACADE_EXTERIOR"


class DefectSeverity(str, Enum):
    """4-State Defect Severity enum matching src/db/schema.prisma lines 215-220."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class InspectionStatus(str, Enum):
    """7-State Field Inspection Lifecycle enum matching src/db/schema.prisma lines 83-91."""
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    QA_PENDING = "QA_PENDING"
    QA_PASSED = "QA_PASSED"
    QA_FAILED = "QA_FAILED"
    CANCELLED = "CANCELLED"


class DefectCategory(str, Enum):
    """Categories aligning condition score categories across inspection checklist."""
    STRUCTURAL = "STRUCTURAL"
    PLUMBING = "PLUMBING"
    ELECTRICAL = "ELECTRICAL"
    FINISHES = "FINISHES"
    EXTERIOR = "EXTERIOR"


# ============================================================================
# 2. Defect, Bounding Box & Fixture Entities
# ============================================================================

class BoundingBox(BaseModel):
    """Normalized bounding box coordinates (0.0 to 1.0)."""
    model_config = ConfigDict(extra="ignore")

    ymin: float = Field(..., ge=0.0, le=1.0, description="Top coordinate normalized")
    xmin: float = Field(..., ge=0.0, le=1.0, description="Left coordinate normalized")
    ymax: float = Field(..., ge=0.0, le=1.0, description="Bottom coordinate normalized")
    xmax: float = Field(..., ge=0.0, le=1.0, description="Right coordinate normalized")
    label: Optional[str] = Field(default=None, description="Optional class label for box")

    def to_dict(self) -> Dict[str, float]:
        return {
            "ymin": round(self.ymin, 4),
            "xmin": round(self.xmin, 4),
            "ymax": round(self.ymax, 4),
            "xmax": round(self.xmax, 4),
        }


class DetectedDefect(BaseModel):
    """Candidate defect identified by PAM vision models."""
    model_config = ConfigDict(extra="ignore")

    defect_id: Optional[str] = Field(default=None, description="Unique identifier for the defect")
    category: DefectCategory = Field(..., description="Checklist condition category")
    severity: DefectSeverity = Field(..., description="Severity level")
    defect_type: str = Field(..., description="E.g. seepage, wall_crack, hollow_tile, paint_peeling, exposed_wiring")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Vision model detection certainty")
    bounding_box: Optional[BoundingBox] = Field(default=None, description="Normalized defect localization")
    notes: Optional[str] = Field(default=None, description="Observed description / evidence summary")


class DetectedFixture(BaseModel):
    """Detected fixtures and appliances for digital twin and property features."""
    model_config = ConfigDict(extra="ignore")

    fixture_type: str = Field(..., description="E.g. AC_UNIT, MODULAR_KITCHEN, GEYSER, SANITARY_WARE, CHANDELIER")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    bounding_box: Optional[BoundingBox] = Field(default=None)
    condition: Optional[str] = Field(default="GOOD", description="EXCELLENT, GOOD, FAIR, POOR")


class ConditionScores(BaseModel):
    """Category condition sub-scores (0 to 100)."""
    model_config = ConfigDict(extra="ignore")

    structural: int = Field(default=100, ge=0, le=100)
    plumbing: int = Field(default=100, ge=0, le=100)
    electrical: int = Field(default=100, ge=0, le=100)
    finishes: int = Field(default=100, ge=0, le=100)
    exterior: int = Field(default=100, ge=0, le=100)
    overall: int = Field(default=100, ge=0, le=100)


# ============================================================================
# 3. Photo Analysis Output (1:1 Mapping to Model InspectionPhoto)
# ============================================================================

class PhotoAnalysisResult(BaseModel):
    """
    Complete analysis result for a single inspection photo.
    Adheres 1:1 to model InspectionPhoto in src/db/schema.prisma lines 964-994.
    """
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = Field(default=None, description="UUID primary key")
    inspection_id: str = Field(..., description="Foreign key to Inspection")
    photo_url: str = Field(..., description="S3 URL / path to high-res photo")
    thumbnail_url: Optional[str] = Field(default=None, description="S3 URL to generated thumbnail")
    
    # Classification
    room_category: RoomCategory = Field(..., description="CLIP/ResNet classified room")
    room_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence of room classification")
    inspector_room_label_hint: Optional[str] = Field(default=None, description="Inspector-provided room label hint")
    reconciliation_action: Optional[str] = Field(default="CONFIRMED", description="CONFIRMED, OVERRIDDEN, or RECONCILED")

    # Anti-Spoofing & Geotag Verification
    latitude: float = Field(..., description="EXIF GPS latitude")
    longitude: float = Field(..., description="EXIF GPS longitude")
    exif_timestamp: datetime = Field(..., description="EXIF capture timestamp")
    is_geotag_valid: bool = Field(default=False, description="Validated against Cadastral 25m boundary gate")
    geofence_distance_meters: Optional[float] = Field(default=None, description="Distance from target property in meters")

    # AI Defect Detection (InspectionPhoto columns)
    has_defect: bool = Field(default=False, description="True if any defect detected")
    defect_severity: Optional[DefectSeverity] = Field(default=None, description="Highest defect severity detected")
    defect_type: Optional[str] = Field(default=None, description="Primary defect type string, e.g. 'seepage', 'wall_crack'")
    defect_bounding_box_json: Optional[Dict[str, Any]] = Field(default=None, description="Primary bounding box JSON")

    # Detailed collections
    defects: List[DetectedDefect] = Field(default_factory=list, description="All detected defects")
    fixtures: List[DetectedFixture] = Field(default_factory=list, description="Detected room fixtures")
    condition_scores: ConditionScores = Field(default_factory=ConditionScores)

    # Telemetry
    inference_latency_ms: float = Field(default=0.0, description="Inference time in milliseconds (P95 SLA: 200-800ms)")
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_prisma_inspection_photo(self) -> Dict[str, Any]:
        """Convert into Prisma model InspectionPhoto row dictionary."""
        return {
            "id": self.id,
            "inspectionId": self.inspection_id,
            "photoUrl": self.photo_url,
            "thumbnailUrl": self.thumbnail_url,
            "roomCategory": self.room_category.value,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "exifTimestamp": self.exif_timestamp.isoformat(),
            "isGeotagValid": self.is_geotag_valid,
            "hasDefect": self.has_defect,
            "defectSeverity": self.defect_severity.value if self.defect_severity else None,
            "defectType": self.defect_type,
            "defectBoundingBoxJson": self.defect_bounding_box_json,
        }

    def to_pip_defect_items(self) -> List[Dict[str, Any]]:
        """Convert detected defects into public/authenticated PIP inspection.defects[] payload."""
        items = []
        for defect in self.defects:
            items.append({
                "category": defect.category.value,
                "severity": defect.severity.value,
                "defect_type": defect.defect_type,
                "photo_url": self.photo_url,
                "note": defect.notes or f"Detected {defect.defect_type} in {self.room_category.value}",
                "confidence": round(defect.confidence, 3),
            })
        return items

    def to_digital_twin_pins(self, room_id: Optional[str] = None, floor_level: int = 0) -> List[Dict[str, Any]]:
        """
        Export candidate InspectionDefectPin objects matching DynamicThreeTwinViewer.tsx lines 40-50.
        """
        pins = []
        color_map = {
            DefectSeverity.LOW: "#3B82F6",       # Blue
            DefectSeverity.MEDIUM: "#F59E0B",    # Amber
            DefectSeverity.HIGH: "#EF4444",      # Red
            DefectSeverity.CRITICAL: "#7F1D1D",  # Dark Crimson
        }
        for idx, defect in enumerate(self.defects):
            pin_id = defect.defect_id or f"pin_{self.id or 'photo'}_{idx}"
            # Approximate 3D position normalized to room coordinates if box is present
            pos_x = 0.0
            pos_y = 1.2
            pos_z = 0.0
            if defect.bounding_box:
                pos_x = round((defect.bounding_box.xmin + defect.bounding_box.xmax - 1.0) * 1.5, 2)
                pos_y = round((1.0 - defect.bounding_box.ymin) * 2.4, 2)
            
            pins.append({
                "id": pin_id,
                "roomId": room_id or self.room_category.value.lower(),
                "roomName": self.room_category.value.replace("_", " ").title(),
                "type": defect.defect_type,
                "severity": defect.severity.value,
                "position": [pos_x, pos_y, pos_z],
                "color": color_map.get(defect.severity, "#EF4444"),
                "description": defect.notes or f"{defect.defect_type} identified ({defect.severity.value})",
                "floorLevel": floor_level,
            })
        return pins


# ============================================================================
# 4. Inspection Batch Aggregation (1:1 Mapping to Model Inspection)
# ============================================================================

class InspectionBatchAnalysisResult(BaseModel):
    """
    Aggregated analysis result for an entire inspection (all rooms/photos).
    Maps 1:1 to model Inspection in src/db/schema.prisma lines 900-960.
    """
    model_config = ConfigDict(extra="ignore")

    inspection_id: str = Field(..., description="Inspection ID")
    property_id: str = Field(..., description="Property ID")
    inspector_id: Optional[str] = Field(default=None)

    total_photos: int = Field(default=0)
    photos_with_defects: int = Field(default=0)
    total_defects_count: int = Field(default=0)

    # Inspection Model Scores (0-100)
    score_overall: int = Field(default=100, ge=0, le=100)
    score_structural: int = Field(default=100, ge=0, le=100)
    score_electrical: int = Field(default=100, ge=0, le=100)
    score_plumbing: int = Field(default=100, ge=0, le=100)
    score_finishes: int = Field(default=100, ge=0, le=100)
    score_locality: Optional[int] = Field(default=None)
    score_cadastral: Optional[int] = Field(default=None)

    # Model Inspection flags
    seepage_detected: bool = Field(default=False, description="True if any plumbing or structural seepage detected")
    active_liens: Optional[bool] = Field(default=None)
    verified_points_count: int = Field(default=0, ge=0, le=80)
    
    # Summaries & Key Findings (jsonb)
    summary: str = Field(default="", description="High level condition summary")
    key_findings: List[Dict[str, Any]] = Field(default_factory=list, description="List of [{category, status, detail}]")

    # QA Gating Decision
    qa_status: InspectionStatus = Field(default=InspectionStatus.QA_PASSED)
    requires_manual_review: bool = Field(default=False)
    qa_review_reason: Optional[str] = Field(default=None)

    # Photos breakdown
    photo_results: List[PhotoAnalysisResult] = Field(default_factory=list)

    def to_prisma_inspection_update(self) -> Dict[str, Any]:
        """Convert into Prisma model Inspection update dictionary."""
        return {
            "scoreOverall": self.score_overall,
            "scoreStructural": self.score_structural,
            "scoreElectrical": self.score_electrical,
            "scorePlumbing": self.score_plumbing,
            "scoreFinishes": self.score_finishes,
            "scoreLocality": self.score_locality,
            "scoreCadastral": self.score_cadastral,
            "seepageDetected": self.seepage_detected,
            "verifiedPointsCount": self.verified_points_count,
            "summary": self.summary,
            "keyFindings": self.key_findings,
            "status": self.qa_status.value,
        }

    def to_pip_inspection_payload(self) -> Dict[str, Any]:
        """Generate PIP inspection read-model section."""
        all_defects = []
        for p in self.photo_results:
            all_defects.extend(p.to_pip_defect_items())

        return {
            "inspection_id": self.inspection_id,
            "score_overall": self.score_overall,
            "scores_by_category": {
                "structural": self.score_structural,
                "plumbing": self.score_plumbing,
                "electrical": self.score_electrical,
                "finishes": self.score_finishes,
            },
            "seepage_detected": self.seepage_detected,
            "photos_count": self.total_photos,
            "defects_count": len(all_defects),
            "defects": all_defects,
            "key_findings": self.key_findings,
            "summary": self.summary,
            "qa_status": self.qa_status.value,
        }


# ============================================================================
# 5. SQS & Event Ingestion Payloads
# ============================================================================

class PamSqsMessagePayload(BaseModel):
    """
    Message contract received from Inspection Service upload queue.
    KEDA-scaled queue worker consumption.
    """
    model_config = ConfigDict(extra="ignore")

    photo_id: str = Field(..., description="INSPECTION_PHOTO PK")
    inspection_id: str = Field(..., description="Report / Inspection PK")
    property_id: str = Field(..., description="Property PK")
    s3_bucket: str = Field(..., description="S3 bucket storing original inspection photo")
    s3_key: str = Field(..., description="Encrypted S3 object key")
    room_label_hint: Optional[str] = Field(default=None, description="Inspector-entered room label hint")
    target_latitude: Optional[float] = Field(default=None, description="Expected property cadastral centroid lat")
    target_longitude: Optional[float] = Field(default=None, description="Expected property cadastral centroid lng")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# 6. Continuous Learning Feedback Contract (§12.3)
# ============================================================================

class PredictionFeedback(BaseModel):
    """Human QA / Inspector override event feeding back into training loops."""
    model_config = ConfigDict(extra="ignore")

    feedback_id: str = Field(..., description="Unique feedback event id")
    photo_id: str = Field(..., description="Target photo ID")
    inspection_id: str = Field(..., description="Inspection ID")
    reviewer_id: str = Field(..., description="Inspector or QA Admin user id")
    
    # Overrides
    predicted_room_category: RoomCategory
    corrected_room_category: Optional[RoomCategory] = None
    predicted_has_defect: bool
    corrected_has_defect: Optional[bool] = None
    predicted_severity: Optional[DefectSeverity] = None
    corrected_severity: Optional[DefectSeverity] = None

    reviewer_notes: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
