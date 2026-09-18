"""
VIE (Valuation Intelligence Engine) — Continuous Learning & MLOps Feedback Loop.

Implements:
- Continuous learning loop (§12.3 & §4) capturing ground-truth actual sale prices vs predictions
- Drift & accuracy tracking: MAPE (Mean Absolute Percentage Error) & ±15% Tier-1 accuracy ratio
- Automated drift alerts when accuracy falls below target threshold (T-04 risk mitigation)
- Export of labeled training pairs for Kubeflow/Metaflow weekly retraining pipeline (§12.3)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from vie.models import ValuationFeedback, VieFeedbackMetrics


class VieLearningLoop:
    """
    Collects ground-truth deal closures and human overrides for model monitoring and weekly retraining.
    """

    def __init__(self, accuracy_threshold_pct: float = 85.0):
        self._events: List[ValuationFeedback] = []
        self.accuracy_threshold_pct = accuracy_threshold_pct

    def record_actual_sale(
        self,
        property_id: str,
        predicted_estimate_paise: int,
        actual_transacted_paise: int,
        micro_market: str,
        notes: Optional[str] = None,
    ) -> ValuationFeedback:
        """
        Record actual closed transaction price from TransactionCompleted event.
        """
        err_pct = (
            abs(actual_transacted_paise - predicted_estimate_paise)
            / float(actual_transacted_paise)
        ) * 100.0

        feedback = ValuationFeedback(
            feedback_id=f"fb_val_{property_id}_{int(datetime.now(timezone.utc).timestamp())}",
            property_id=property_id,
            predicted_estimate_paise=predicted_estimate_paise,
            actual_transacted_paise=actual_transacted_paise,
            percentage_error=round(err_pct, 2),
            micro_market=micro_market,
            source_event="TransactionCompleted",
            notes=notes,
            timestamp=datetime.now(timezone.utc),
        )
        self._events.append(feedback)
        return feedback

    def record_override(
        self,
        property_id: str,
        predicted_estimate_paise: int,
        override_paise: int,
        micro_market: str,
        reviewer_id: str,
        notes: Optional[str] = None,
    ) -> ValuationFeedback:
        """
        Record an expert appraiser or ops manual override.
        """
        err_pct = (
            abs(override_paise - predicted_estimate_paise)
            / float(override_paise)
        ) * 100.0

        feedback = ValuationFeedback(
            feedback_id=f"fb_ovr_{property_id}_{int(datetime.now(timezone.utc).timestamp())}",
            property_id=property_id,
            predicted_estimate_paise=predicted_estimate_paise,
            user_or_appraiser_override_paise=override_paise,
            percentage_error=round(err_pct, 2),
            micro_market=micro_market,
            source_event=f"AppraiserOverride:{reviewer_id}",
            notes=notes,
            timestamp=datetime.now(timezone.utc),
        )
        self._events.append(feedback)
        return feedback

    def get_metrics(self) -> VieFeedbackMetrics:
        """
        Computes model performance metrics: MAPE, within ±15% ratio, and bias.
        """
        total = len(self._events)
        if total == 0:
            return VieFeedbackMetrics()

        total_err = 0.0
        within_15_count = 0
        overvalued = 0
        undervalued = 0

        for e in self._events:
            ground_truth = e.actual_transacted_paise or e.user_or_appraiser_override_paise
            if not ground_truth:
                continue

            err = abs(ground_truth - e.predicted_estimate_paise) / float(ground_truth) * 100.0
            total_err += err

            if err <= 15.0:
                within_15_count += 1

            if e.predicted_estimate_paise > ground_truth:
                overvalued += 1
            elif e.predicted_estimate_paise < ground_truth:
                undervalued += 1

        mape = round(total_err / total, 2)
        ratio_15 = round((within_15_count / float(total)) * 100.0, 1)

        return VieFeedbackMetrics(
            total_events=total,
            mape_percentage=mape,
            within_15_pct_accuracy_ratio=ratio_15,
            overvalued_count=overvalued,
            undervalued_count=undervalued,
        )

    def is_drift_alert_triggered(self) -> bool:
        """Checks if accuracy within ±15% drops below the SLA threshold (e.g. 85%)."""
        metrics = self.get_metrics()
        if metrics.total_events < 5:
            return False
        return metrics.within_15_pct_accuracy_ratio < self.accuracy_threshold_pct

    def export_training_batch(self) -> List[Dict[str, Any]]:
        """
        Exports feedback samples formatted for weekly Kubeflow/Metaflow retraining (§12.3).
        """
        batch = []
        for e in self._events:
            ground_truth = e.actual_transacted_paise or e.user_or_appraiser_override_paise
            if not ground_truth:
                continue
            batch.append({
                "feedback_id": e.feedback_id,
                "property_id": e.property_id,
                "predicted_estimate_paise": e.predicted_estimate_paise,
                "ground_truth_paise": ground_truth,
                "percentage_error": e.percentage_error,
                "micro_market": e.micro_market,
                "source": e.source_event,
                "notes": e.notes,
                "timestamp": e.timestamp.isoformat(),
            })
        return batch

    def clear(self):
        """Clears in-memory feedback buffer."""
        self._events.clear()


vie_learning_loop = VieLearningLoop()
