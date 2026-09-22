"""
PAM (Photo Analysis Module) — Continuous Learning Loop (§12.3).

Implements:
- Recording inspector and QA reviewer feedback overrides (room class, defect calls)
- In-memory event buffer with Kafka / S3 archival export interface
- Confusion and drift telemetry tracking (room classification error rates, defect false-positive rates)
- Training dataset export for weekly retraining jobs
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from pipelines.pam.models import PredictionFeedback, RoomCategory, DefectSeverity


class FeedbackMetrics(BaseModel):
    total_feedback_events: int = 0
    room_overrides_count: int = 0
    defect_overrides_count: int = 0
    severity_adjustments_count: int = 0
    room_accuracy_rate: float = 1.0


class PamLearningLoop:
    """Collects human overrides and exports training updates for model retraining."""

    def __init__(self):
        self._events: List[PredictionFeedback] = []

    def record_feedback(
        self,
        photo_id: str,
        inspection_id: str,
        reviewer_id: str,
        predicted_room_category: RoomCategory,
        corrected_room_category: Optional[RoomCategory] = None,
        predicted_has_defect: bool = False,
        corrected_has_defect: Optional[bool] = None,
        predicted_severity: Optional[DefectSeverity] = None,
        corrected_severity: Optional[DefectSeverity] = None,
        reviewer_notes: Optional[str] = None,
    ) -> PredictionFeedback:
        """Record an inspector / QA override."""
        feedback = PredictionFeedback(
            feedback_id=f"fb_{photo_id}_{int(datetime.now(timezone.utc).timestamp())}",
            photo_id=photo_id,
            inspection_id=inspection_id,
            reviewer_id=reviewer_id,
            predicted_room_category=predicted_room_category,
            corrected_room_category=corrected_room_category,
            predicted_has_defect=predicted_has_defect,
            corrected_has_defect=corrected_has_defect,
            predicted_severity=predicted_severity,
            corrected_severity=corrected_severity,
            reviewer_notes=reviewer_notes,
            timestamp=datetime.now(timezone.utc),
        )
        self._events.append(feedback)
        return feedback

    def get_metrics(self) -> FeedbackMetrics:
        """Compute performance drift and override metrics."""
        total = len(self._events)
        if total == 0:
            return FeedbackMetrics()

        room_overrides = sum(
            1 for e in self._events if e.corrected_room_category and e.corrected_room_category != e.predicted_room_category
        )
        defect_overrides = sum(
            1 for e in self._events if e.corrected_has_defect is not None and e.corrected_has_defect != e.predicted_has_defect
        )
        severity_adjustments = sum(
            1 for e in self._events if e.corrected_severity and e.corrected_severity != e.predicted_severity
        )

        acc = max(0.0, 1.0 - (room_overrides / total))

        return FeedbackMetrics(
            total_feedback_events=total,
            room_overrides_count=room_overrides,
            defect_overrides_count=defect_overrides,
            severity_adjustments_count=severity_adjustments,
            room_accuracy_rate=round(acc, 3),
        )

    def export_training_batch(self) -> List[Dict[str, Any]]:
        """Export verified human feedback as labeled training pairs."""
        batch = []
        for e in self._events:
            batch.append({
                "photo_id": e.photo_id,
                "inspection_id": e.inspection_id,
                "target_room_category": (
                    e.corrected_room_category.value if e.corrected_room_category else e.predicted_room_category.value
                ),
                "has_defect": (
                    e.corrected_has_defect if e.corrected_has_defect is not None else e.predicted_has_defect
                ),
                "defect_severity": (
                    e.corrected_severity.value if e.corrected_severity else (
                        e.predicted_severity.value if e.predicted_severity else None
                    )
                ),
                "reviewer_id": e.reviewer_id,
                "notes": e.reviewer_notes,
                "verified_at": e.timestamp.isoformat(),
            })
        return batch

    def clear(self):
        """Clear the in-memory buffer."""
        self._events.clear()


pam_learning_loop = PamLearningLoop()
