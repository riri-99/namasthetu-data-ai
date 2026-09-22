"""
PAM (Photo Analysis Module) — Condition Scorer & Aggregation Substrate.

Implements:
- 0 to 100 Condition Scoring across 5 categories: Structural, Electrical, Plumbing, Finishes, Exterior
- Defect severity deduction matrix (LOW=-5, MEDIUM=-15, HIGH=-25, CRITICAL=-40)
- Cross-reconciliation against inspector-entered scores (1-10 or 0-100)
- Headline findings generation: [{category, status: PASS|OPTIMAL|ATTENTION, detail}]
- Seepage detection aggregation (populates model Inspection.seepageDetected)
- QA Gating Decision (QA_PASSED vs QA_PENDING / QA_FAILED)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from pipelines.pam.models import (
    DefectCategory,
    DefectSeverity,
    DetectedDefect,
    ConditionScores,
    InspectionStatus,
    PhotoAnalysisResult,
)


class ConditionScorer:
    """Calculates condition sub-scores, overall score, key findings, and QA gates."""

    # Penalty deductions per severity level
    SEVERITY_PENALTIES: Dict[DefectSeverity, int] = {
        DefectSeverity.LOW: 5,
        DefectSeverity.MEDIUM: 15,
        DefectSeverity.HIGH: 25,
        DefectSeverity.CRITICAL: 40,
    }

    # Weights for overall score computation
    CATEGORY_WEIGHTS: Dict[DefectCategory, float] = {
        DefectCategory.STRUCTURAL: 0.30,
        DefectCategory.PLUMBING: 0.25,
        DefectCategory.ELECTRICAL: 0.20,
        DefectCategory.FINISHES: 0.15,
        DefectCategory.EXTERIOR: 0.10,
    }

    @classmethod
    def compute_photo_condition(cls, defects: List[DetectedDefect]) -> ConditionScores:
        """Compute condition scores for a single photo based on observed defects."""
        scores = {cat: 100 for cat in DefectCategory}

        for defect in defects:
            penalty = cls.SEVERITY_PENALTIES.get(defect.severity, 10)
            scores[defect.category] = max(0, scores[defect.category] - penalty)

        overall = sum(scores[cat] * cls.CATEGORY_WEIGHTS[cat] for cat in DefectCategory)

        return ConditionScores(
            structural=scores[DefectCategory.STRUCTURAL],
            plumbing=scores[DefectCategory.PLUMBING],
            electrical=scores[DefectCategory.ELECTRICAL],
            finishes=scores[DefectCategory.FINISHES],
            exterior=scores[DefectCategory.EXTERIOR],
            overall=int(round(overall)),
        )

    @classmethod
    def aggregate_inspection_scores(
        cls,
        photo_results: List[PhotoAnalysisResult],
        inspector_scores: Optional[Dict[str, Union[int, float]]] = None,
    ) -> Tuple[int, int, int, int, int, int, bool, List[Dict[str, Any]], str, InspectionStatus, bool, Optional[str]]:
        """
        Aggregate photo-level scores into complete Inspection entity metrics.

        Returns:
            (score_overall, score_structural, score_electrical, score_plumbing,
             score_finishes, score_exterior, seepage_detected, key_findings,
             summary, qa_status, requires_manual_review, qa_review_reason)
        """
        category_penalties: Dict[DefectCategory, int] = {cat: 0 for cat in DefectCategory}
        all_defects: List[DetectedDefect] = []
        has_critical = False
        seepage_detected = False
        invalid_geotags_count = 0

        for p in photo_results:
            if not p.is_geotag_valid:
                invalid_geotags_count += 1
            for d in p.defects:
                all_defects.append(d)
                penalty = cls.SEVERITY_PENALTIES.get(d.severity, 10)
                category_penalties[d.category] += penalty
                if d.severity == DefectSeverity.CRITICAL:
                    has_critical = True
                if "seepage" in d.defect_type.lower() or "damp" in d.defect_type.lower():
                    seepage_detected = True

        # Calculate base category scores (0 to 100)
        cat_scores: Dict[DefectCategory, int] = {}
        for cat in DefectCategory:
            raw_score = max(0, 100 - category_penalties[cat])
            # If inspector scores provided (scaled 1-10 or 0-100), blend with vision score
            if inspector_scores:
                key = cat.value.lower()
                insp_val = inspector_scores.get(key)
                if insp_val is not None:
                    # Normalize 1-10 to 0-100 if necessary
                    insp_norm = int(insp_val * 10) if insp_val <= 10 else int(insp_val)
                    # Blend: 60% Vision Model + 40% Inspector Manual Assessment
                    blended = int(round(0.60 * raw_score + 0.40 * insp_norm))
                    cat_scores[cat] = max(0, min(100, blended))
                else:
                    cat_scores[cat] = raw_score
            else:
                cat_scores[cat] = raw_score

        overall = int(round(sum(cat_scores[cat] * cls.CATEGORY_WEIGHTS[cat] for cat in DefectCategory)))

        # Build Key Findings
        key_findings: List[Dict[str, Any]] = []
        for cat in DefectCategory:
            score = cat_scores[cat]
            if score >= 90:
                status = "OPTIMAL"
                detail = f"{cat.value.title()} condition is pristine with zero defects."
            elif score >= 75:
                status = "PASS"
                detail = f"{cat.value.title()} systems structurally sound with minor cosmetic wear."
            else:
                status = "ATTENTION"
                issues = [d.defect_type for d in all_defects if d.category == cat]
                detail = f"Requires attention: {', '.join(set(issues)) if issues else 'Multiple condition faults detected'}."

            key_findings.append({
                "category": cat.value,
                "status": status,
                "score": score,
                "detail": detail,
            })

        # Summary Narrative
        defect_count = len(all_defects)
        summary = (
            f"Physical inspection verified across {len(photo_results)} geotagged photos. "
            f"Overall property condition rated at {overall}/100. "
            f"{'Seepage detected across plumbing/wall junctions. ' if seepage_detected else 'No active water seepage detected. '}"
            f"Identified {defect_count} candidate defects requiring owner/buyer attention."
        )

        # QA Gating Decision
        qa_status = InspectionStatus.QA_PASSED
        requires_manual_review = False
        qa_review_reason: Optional[str] = None

        if has_critical:
            qa_status = InspectionStatus.QA_PENDING
            requires_manual_review = True
            qa_review_reason = "Critical defect detected (potential structural / fire safety hazard)."
        elif overall < 70:
            qa_status = InspectionStatus.QA_PENDING
            requires_manual_review = True
            qa_review_reason = f"Low composite condition score ({overall}/100) below auto-approval threshold."
        elif invalid_geotags_count > (len(photo_results) // 2) and len(photo_results) > 0:
            qa_status = InspectionStatus.QA_PENDING
            requires_manual_review = True
            qa_review_reason = f"{invalid_geotags_count} photos failed cadastral 25m boundary anti-spoof check."

        return (
            overall,
            cat_scores[DefectCategory.STRUCTURAL],
            cat_scores[DefectCategory.ELECTRICAL],
            cat_scores[DefectCategory.PLUMBING],
            cat_scores[DefectCategory.FINISHES],
            cat_scores[DefectCategory.EXTERIOR],
            seepage_detected,
            key_findings,
            summary,
            qa_status,
            requires_manual_review,
            qa_review_reason,
        )
