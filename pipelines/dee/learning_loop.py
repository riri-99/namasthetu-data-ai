"""
Continuous Learning Loop Client for DEE (§12.3 & DEE Implementation Plan Phase 5)
Captures labeled events on every extraction:
  1. Initial AI extraction predictions (with PII-masked OCR text).
  2. Manual ops reviewer approvals and overrides.
  3. Ground-truth correction write-backs with field-level diffs for weekly Kubeflow/Metaflow retraining.
"""

from __future__ import annotations
import uuid
from enum import Enum
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable
from pydantic import BaseModel, Field

from pipelines.dee.models import (
    DocumentType,
    ExtractedEntitiesJson,
    DeeExtractionResult,
)


class DeeLearningEventType(str, Enum):
    EXTRACTION_INITIAL = "EXTRACTION_INITIAL"
    OPS_APPROVED = "OPS_APPROVED"
    OPS_CORRECTED = "OPS_CORRECTED"
    EXTRACTION_REJECTED = "EXTRACTION_REJECTED"


class DeeLearningSample(BaseModel):
    """
    Standard dataset unit consumed by the weekly retraining pipeline (§12.3 step 8).
    """
    sample_id: str = Field(default_factory=lambda: f"lrn_{uuid.uuid4().hex[:12]}")
    event_type: DeeLearningEventType
    document_id: str
    property_id: str
    document_type: str
    masked_ocr_text: str
    predicted_entities: ExtractedEntitiesJson
    predicted_confidence: float
    corrected_entities: Optional[ExtractedEntitiesJson] = None
    field_deltas: Optional[Dict[str, Any]] = None
    reviewer_id: Optional[str] = None
    reviewer_notes: Optional[str] = None
    pipeline_version: str = "1.0.0"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_training_jsonl(self) -> Dict[str, Any]:
        """
        Formats sample for Kubeflow/Metaflow fine-tuning and evaluation (§12.3).
        """
        ground_truth = self.corrected_entities.model_dump(mode="json") if self.corrected_entities else self.predicted_entities.model_dump(mode="json")
        return {
            "id": self.sample_id,
            "document_type": self.document_type,
            "input_ocr_prompt": self.masked_ocr_text,
            "target_ground_truth": ground_truth,
            "has_human_correction": self.event_type == DeeLearningEventType.OPS_CORRECTED,
            "field_deltas": self.field_deltas or {},
            "timestamp": self.created_at.isoformat(),
        }


class DeeLearningCollector:
    """
    In-memory and streaming collector for DEE continuous learning events.
    Supports routing to Kafka topics (`doc-extraction-events`) and S3 archive buckets.
    """

    def __init__(self):
        self._events_archive: List[DeeLearningSample] = []
        self._external_publishers: List[Callable[[DeeLearningSample], None]] = []

    def register_publisher(self, publisher: Callable[[DeeLearningSample], None]):
        """Registers external Kafka / S3 event publishing callbacks."""
        self._external_publishers.append(publisher)

    def _publish_event(self, sample: DeeLearningSample):
        self._events_archive.append(sample)
        for pub in self._external_publishers:
            try:
                pub(sample)
            except Exception:
                pass

    def emit_extraction(
        self,
        result: DeeExtractionResult,
        masked_ocr_text: str,
    ) -> DeeLearningSample:
        """
        Captures the initial model extraction event upon pipeline completion (§12.3 step 1).
        """
        sample = DeeLearningSample(
            event_type=DeeLearningEventType.EXTRACTION_INITIAL,
            document_id=result.document_id,
            property_id=result.property_id,
            document_type=result.document_type.value,
            masked_ocr_text=masked_ocr_text,
            predicted_entities=result.aiExtractedDataJson,
            predicted_confidence=result.aiConfidenceScore,
            field_deltas=None,
        )
        self._publish_event(sample)
        return sample

    def record_ops_approval(
        self,
        original_result: DeeExtractionResult,
        reviewer_id: str,
        reviewer_notes: Optional[str] = None,
    ) -> DeeLearningSample:
        """
        Records human reviewer sign-off without changes.
        """
        sample = DeeLearningSample(
            event_type=DeeLearningEventType.OPS_APPROVED,
            document_id=original_result.document_id,
            property_id=original_result.property_id,
            document_type=original_result.document_type.value,
            masked_ocr_text="",
            predicted_entities=original_result.aiExtractedDataJson,
            predicted_confidence=original_result.aiConfidenceScore,
            corrected_entities=original_result.aiExtractedDataJson,
            reviewer_id=reviewer_id,
            reviewer_notes=reviewer_notes,
        )
        self._publish_event(sample)
        return sample

    def record_ops_correction(
        self,
        original_result: DeeExtractionResult,
        corrected_entities: ExtractedEntitiesJson,
        reviewer_id: str,
        reviewer_notes: Optional[str] = None,
    ) -> DeeLearningSample:
        """
        Records human ops reviewer correction. Computes field-level deltas as ground-truth signal (§12.3 step 8).
        """
        pred_dict = original_result.aiExtractedDataJson.model_dump(mode="json")
        corr_dict = corrected_entities.model_dump(mode="json")

        deltas = {}
        for key in ["owners", "survey_number", "area", "dates", "encumbrances", "sale_consideration_inr"]:
            if pred_dict.get(key) != corr_dict.get(key):
                deltas[key] = {
                    "predicted": pred_dict.get(key),
                    "corrected": corr_dict.get(key),
                }

        sample = DeeLearningSample(
            event_type=DeeLearningEventType.OPS_CORRECTED,
            document_id=original_result.document_id,
            property_id=original_result.property_id,
            document_type=original_result.document_type.value,
            masked_ocr_text="",
            predicted_entities=original_result.aiExtractedDataJson,
            predicted_confidence=original_result.aiConfidenceScore,
            corrected_entities=corrected_entities,
            field_deltas=deltas,
            reviewer_id=reviewer_id,
            reviewer_notes=reviewer_notes,
        )
        self._publish_event(sample)
        return sample

    def get_events_for_document(self, document_id: str) -> List[DeeLearningSample]:
        """Returns all learning samples for a given document."""
        return [e for e in self._events_archive if e.document_id == document_id]

    def export_dataset(self, event_type: Optional[DeeLearningEventType] = None) -> List[Dict[str, Any]]:
        """
        Exports collected samples formatted for weekly retraining batches.
        """
        samples = self._events_archive
        if event_type:
            samples = [s for s in samples if s.event_type == event_type]
        return [s.to_training_jsonl() for s in samples]

    def clear_archive(self):
        """Clears in-memory archive (useful for test isolation)."""
        self._events_archive.clear()


dee_learning_collector = DeeLearningCollector()
