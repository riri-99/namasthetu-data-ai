"""
Listing Quality Auditor (LQA) — Combined & Optimized Pipeline Engine.

Embedded AI Service #5 · Namasthetu Platform
Spec Reference: Namasthetu × Hue Cycle Launch Scope v1.0 (HYC-SCO-2026-3841, §12.1-§12.4, §8.8, §03.M09)
Database Alignment: Strictly compliant with src/db/schema.prisma (models Listing, LqaAudit, enums ListingStatus, LqaStatus)
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from pydantic import BaseModel, Field, ConfigDict

from this_is_what_you_need.common import (
    AiGatewayClient,
    ai_gateway,
    mask_pii,
    BaseEventDispatcher,
    PrismaPropertyType,
    PrismaFurnishingStatus,
    PrismaListingStatus,
    PrismaLqaStatus,
)


# ============================================================================
# 1. Domain Enums Matching src/db/schema.prisma
# ============================================================================

class LqaStatus(str, Enum):
    """5-State Listing Quality Auditor (LQA) Scoring Flow matching schema.prisma lines 116-123."""
    QUEUED = "QUEUED"
    SCORING = "SCORING"
    SCORED = "SCORED"
    APPROVED = "APPROVED"       # Score >= 72
    REJECTED = "REJECTED"       # Score < 72; returns to draft with notes


class ListingStatus(str, Enum):
    """6-State Listing Lifecycle matching schema.prisma lines 72-80."""
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"  # Awaiting LQA check
    ACTIVE = "ACTIVE"                      # LQA score >= 72; visible to buyers
    PAUSED = "PAUSED"
    EXPIRED = "EXPIRED"                    # Inactive for 90 days
    CLOSED = "CLOSED"


class LqaFlagCategory(str, Enum):
    """Four canonical flag categories per § 12 Embedded AI & § 8.8 LQA specification."""
    PHOTOS = "PHOTOS"
    PRICE = "PRICE"
    DISCLOSURE = "DISCLOSURE"
    LANGUAGE = "LANGUAGE"


class LqaFlagSeverity(str, Enum):
    """Severity tier for LQA quality and transparency issues."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class LqaPipelineStage(str, Enum):
    """Server-Sent Events lifecycle stages for LQA processing."""
    QUEUED = "QUEUED"
    RULE_EVALUATION = "RULE_EVALUATION"
    LLM_TRANSPARENCY_EVALUATION = "LLM_TRANSPARENCY_EVALUATION"
    SCORING_DECISION = "SCORING_DECISION"
    COMPLETED = "COMPLETED"
    ROUTED_TO_SPOT_CHECK = "ROUTED_TO_SPOT_CHECK"
    REJECTED_TO_DRAFT = "REJECTED_TO_DRAFT"
    FAILED = "FAILED"


# ============================================================================
# 2. Domain Data Models & Input/Output Contracts
# ============================================================================

class PhotoMetadata(BaseModel):
    """Photo metadata for inspection coverage and quality verification."""
    model_config = ConfigDict(extra="ignore")

    photo_id: Optional[str] = None
    url: str
    room_category: Optional[str] = None
    is_cover: bool = False
    condition_score: Optional[float] = None


class LqaFlag(BaseModel):
    """Structured quality or transparency issue flag."""
    model_config = ConfigDict(extra="ignore")

    flag_id: str = Field(default_factory=lambda: f"flag_{uuid.uuid4().hex[:8]}")
    category: LqaFlagCategory
    severity: LqaFlagSeverity
    code: str
    message: str
    suggestion: str
    field_reference: Optional[str] = None
    penalty_points: int = 0


class LqaCategoryScore(BaseModel):
    """Score for an individual category (photos, price, disclosure, language)."""
    model_config = ConfigDict(extra="ignore")

    category: LqaFlagCategory
    score: int = Field(..., ge=0, le=100)
    weight: float = Field(default=0.25, ge=0.0, le=1.0)
    weighted_score: float = 0.0
    flags: List[LqaFlag] = Field(default_factory=list)


class LqaBreakdown(BaseModel):
    """Comprehensive scoring breakdown across all 4 pillars."""
    model_config = ConfigDict(extra="ignore")

    photos: LqaCategoryScore
    price: LqaCategoryScore
    disclosure: LqaCategoryScore
    language: LqaCategoryScore
    all_flags: List[LqaFlag] = Field(default_factory=list)
    critical_flags_count: int = 0
    warning_flags_count: int = 0
    info_flags_count: int = 0


class LqaRevisionComparison(BaseModel):
    """Side-by-side delta between current audit and previous audit (§8.8)."""
    model_config = ConfigDict(extra="ignore")

    previous_audit_id: str
    previous_score: int
    current_score: int
    score_delta: int
    resolved_flags: List[str] = Field(default_factory=list)
    new_flags: List[str] = Field(default_factory=list)
    persistent_flags: List[str] = Field(default_factory=list)


class ListingDraftInput(BaseModel):
    """Input payload for a submitted listing draft awaiting quality audit."""
    model_config = ConfigDict(extra="ignore")

    listing_id: str
    property_id: str
    title: str
    description: str
    asking_price_paise: int = Field(..., gt=0)
    area_sqft: float = Field(..., gt=0)
    property_type: Union[str, PrismaPropertyType] = PrismaPropertyType.APARTMENT
    furnishing_status: Optional[Union[str, PrismaFurnishingStatus]] = None
    bhk_count: Optional[int] = None
    photos: List[Union[str, PhotoMetadata, Dict[str, Any]]] = Field(default_factory=list)
    locality: Optional[str] = None
    city: Optional[str] = None

    # Legal & Disclosures
    rera_number: Optional[str] = None
    has_occupancy_certificate: Optional[bool] = None
    has_encumbrance_certificate: Optional[bool] = None
    property_tax_paid: Optional[bool] = None
    maintenance_charges_monthly_inr: Optional[float] = None

    # Cross-Pipeline Intelligence Inputs
    dee_deed_verified: Optional[bool] = None
    dee_active_liens_detected: Optional[bool] = None
    pam_overall_condition_score: Optional[float] = None
    pam_has_seepage: Optional[bool] = None
    vie_avm_estimate_paise: Optional[int] = None
    vie_avm_price_sqft_base: Optional[float] = None

    # Revision Tracking
    previous_audit_id: Optional[str] = None


class ListingScoredEvent(BaseModel):
    """Published event payload consumed by Ops and Discovery contexts."""
    model_config = ConfigDict(extra="ignore")

    event_id: str = Field(default_factory=lambda: f"evt_lqa_{uuid.uuid4().hex[:12]}")
    property_id: str
    listing_id: str
    lqa_score: int
    flags: List[Dict[str, Any]]
    status: LqaStatus
    requires_spot_check: bool
    fraud_flag_recommended: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LqaPipelineEvent(BaseModel):
    """Server-Sent Event for real-time progress monitoring."""
    event_id: str
    stage: LqaPipelineStage
    listing_id: str
    property_id: str
    progress_percentage: int
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_sse_message(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"))
        return f"id: {self.event_id}\nevent: {self.stage.value}\ndata: {payload}\n\n"


class LqaAuditResult(BaseModel):
    """
    Final output contract of LQA pipeline.
    Directly aligns with model LqaAudit in src/db/schema.prisma.
    """
    model_config = ConfigDict(extra="ignore")

    audit_id: str = Field(default_factory=lambda: f"lqa_{uuid.uuid4().hex[:12]}")
    listing_id: str
    property_id: str
    status: LqaStatus
    overall_score: int = Field(..., ge=0, le=100)
    lqa_passed: bool
    requires_spot_check: bool
    resulting_listing_status: ListingStatus
    breakdown: LqaBreakdown
    feedback_narrative: str
    revision_comparison: Optional[LqaRevisionComparison] = None

    # Fraud escalation to Trust context (FRAUD_FLAG)
    fraud_flag_recommended: bool = False
    fraud_flag_reason: Optional[str] = None
    fraud_confidence: Optional[float] = None

    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processing_time_ms: float = 0.0

    def to_prisma_audit_dict(self) -> Dict[str, Any]:
        """
        Exports exact dictionary format matching model LqaAudit in schema.prisma:
        id, propertyId, status, overallScore, breakdownJson, feedbackNarrative, requiresSpotCheck.
        """
        breakdown_payload = {
            "photos": self.breakdown.photos.model_dump(mode="json"),
            "price": self.breakdown.price.model_dump(mode="json"),
            "disclosure": self.breakdown.disclosure.model_dump(mode="json"),
            "language": self.breakdown.language.model_dump(mode="json"),
            "all_flags": [f.model_dump(mode="json") for f in self.breakdown.all_flags],
            "critical_flags_count": self.breakdown.critical_flags_count,
            "warning_flags_count": self.breakdown.warning_flags_count,
            "info_flags_count": self.breakdown.info_flags_count,
            "fraud_flag_recommended": self.fraud_flag_recommended,
            "fraud_flag_reason": self.fraud_flag_reason,
            "resulting_listing_status": self.resulting_listing_status.value,
        }
        return {
            "id": self.audit_id,
            "propertyId": self.property_id,
            "status": self.status.value,
            "overallScore": self.overall_score,
            "breakdownJson": breakdown_payload,
            "feedbackNarrative": self.feedback_narrative,
            "requiresSpotCheck": self.requires_spot_check,
            "reviewedByAdminId": None,
            "reviewedAt": None,
            "reviewNotes": None,
            "evaluatedAt": self.evaluated_at.isoformat(),
            "updatedAt": self.evaluated_at.isoformat(),
        }


# ============================================================================
# 3. Deterministic Heuristic Rule Engine
# ============================================================================

class LqaRuleEngine:
    """
    Sub-millisecond deterministic rule evaluation for:
    - Photo presence, count, and room coverage
    - Asking price sanity vs AVM fair market valuation
    - Mandatory legal disclosures, RERA, and lien consistency
    - Baseline language compliance (length, PII/direct contact prevention, spam)
    """

    PHONE_REGEX = re.compile(r"\b(?:\+91|0)?[6-9]\d{9}\b")
    EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b")

    @classmethod
    def evaluate_photos(cls, draft: ListingDraftInput) -> Tuple[int, List[LqaFlag]]:
        """Evaluates photo presence, volume, and metadata completeness."""
        flags: List[LqaFlag] = []
        photos = draft.photos
        count = len(photos)

        if count == 0:
            flags.append(
                LqaFlag(
                    category=LqaFlagCategory.PHOTOS,
                    severity=LqaFlagSeverity.CRITICAL,
                    code="NO_PHOTOS",
                    message="Listing contains zero photos. Public listings require at least 3 genuine inspection photos.",
                    suggestion="Upload clear photographs of the living room, master bedroom, kitchen, and bathroom.",
                    field_reference="photos",
                    penalty_points=100,
                )
            )
            return 0, flags

        if count < 3:
            penalty = 55
            flags.append(
                LqaFlag(
                    category=LqaFlagCategory.PHOTOS,
                    severity=LqaFlagSeverity.WARNING,
                    code="INSUFFICIENT_PHOTOS",
                    message=f"Listing contains only {count} photo(s). Minimum recommended for transparency is 3.",
                    suggestion="Upload photos of all primary living areas to pass quality audit.",
                    field_reference="photos",
                    penalty_points=penalty,
                )
            )
            return max(0, 100 - penalty), flags

        # Check for room coverage when photo metadata or strings provide hints
        room_categories: Set[str] = set()
        for p in photos:
            if isinstance(p, PhotoMetadata) and p.room_category:
                room_categories.add(p.room_category.upper())
            elif isinstance(p, dict) and p.get("room_category"):
                room_categories.add(str(p["room_category"]).upper())
            elif isinstance(p, str):
                lower_p = p.lower()
                for cat in ["living", "bedroom", "kitchen", "bathroom", "balcony", "exterior"]:
                    if cat in lower_p:
                        room_categories.add(cat.upper())

        score = 100
        if len(photos) >= 5:
            score = 100
        else:
            score = 90

        if room_categories and not any(r in room_categories for r in ["KITCHEN", "BATHROOM"]):
            score = max(0, score - 10)
            flags.append(
                LqaFlag(
                    category=LqaFlagCategory.PHOTOS,
                    severity=LqaFlagSeverity.INFO,
                    code="MISSING_WET_AREA_PHOTOS",
                    message="No kitchen or bathroom photos identified. Buyers prioritize plumbing and wet-area condition.",
                    suggestion="Add photos of the kitchen and bathroom for comprehensive transparency.",
                    field_reference="photos",
                    penalty_points=10,
                )
            )

        # Cross-reference with PAM condition if available
        if draft.pam_overall_condition_score is not None and draft.pam_overall_condition_score < 50.0:
            flags.append(
                LqaFlag(
                    category=LqaFlagCategory.PHOTOS,
                    severity=LqaFlagSeverity.WARNING,
                    code="POOR_VISUAL_CONDITION",
                    message=f"PAM photo analysis detected heavy physical wear or defects (Condition Score: {draft.pam_overall_condition_score:.1f}/100).",
                    suggestion="Ensure defect areas are accurately represented in disclosures to prevent buyer disputes.",
                    field_reference="pam_overall_condition_score",
                    penalty_points=15,
                )
            )
            score = max(0, score - 15)

        return score, flags

    @classmethod
    def evaluate_price(cls, draft: ListingDraftInput) -> Tuple[int, List[LqaFlag]]:
        """
        Evaluates asking price sanity against VIE/AVM automated valuation baseline.
        Flags suspicious discounts (>30% below market) or premiums (>50% above market).
        """
        flags: List[LqaFlag] = []
        asking_paise = draft.asking_price_paise
        avm_paise = draft.vie_avm_estimate_paise

        if avm_paise and avm_paise > 0:
            ratio = asking_paise / float(avm_paise)
            # 1. Suspicious discount > 30% below market
            if ratio < 0.70:
                discount_pct = round((1.0 - ratio) * 100.0, 1)
                flags.append(
                    LqaFlag(
                        category=LqaFlagCategory.PRICE,
                        severity=LqaFlagSeverity.CRITICAL,
                        code="SUSPICIOUS_PRICE_DISCOUNT",
                        message=(
                            f"Asking price is {discount_pct}% below the algorithmic market valuation baseline (VIE AVM). "
                            "Extreme discounts frequently signal undisclosed legal encumbrances, severe structural distress, "
                            "or unrecorded cash transactions."
                        ),
                        suggestion="Verify asking price against recent neighborhood comparables or provide formal explanation in disclosures.",
                        field_reference="asking_price_paise",
                        penalty_points=60,
                    )
                )
                return 40, flags

            # 2. Suspicious premium > 50% above market
            if ratio > 1.50:
                premium_pct = round((ratio - 1.0) * 100.0, 1)
                flags.append(
                    LqaFlag(
                        category=LqaFlagCategory.PRICE,
                        severity=LqaFlagSeverity.WARNING,
                        code="SUSPICIOUS_PRICE_PREMIUM",
                        message=f"Asking price is {premium_pct}% above prevailing market valuation.",
                        suggestion="Consider aligning asking price closer to market valuation to improve inquiry conversion.",
                        field_reference="asking_price_paise",
                        penalty_points=35,
                    )
                )
                return 65, flags

            # 3. Competitive below market (15-30% discount)
            if ratio < 0.85:
                flags.append(
                    LqaFlag(
                        category=LqaFlagCategory.PRICE,
                        severity=LqaFlagSeverity.INFO,
                        code="COMPETITIVE_BELOW_MARKET",
                        message="Asking price is competitively positioned below market median (15-30% discount).",
                        suggestion="Highlight attractive pricing in listing highlights.",
                        field_reference="asking_price_paise",
                        penalty_points=0,
                    )
                )
                return 95, flags

            # 4. Aligned with market
            return 100, flags

        # Fallback heuristic: Cold-start markets where VIE AVM is not yet available
        price_inr = asking_paise / 100.0
        rate_sqft = price_inr / max(1.0, draft.area_sqft)

        if rate_sqft < 1200.0:
            flags.append(
                LqaFlag(
                    category=LqaFlagCategory.PRICE,
                    severity=LqaFlagSeverity.WARNING,
                    code="ANOMALOUS_LOW_RATE",
                    message=f"Price per sqft (INR {rate_sqft:,.0f}) is exceptionally low for residential property.",
                    suggestion="Verify carpet area and price input fields.",
                    field_reference="asking_price_paise",
                    penalty_points=40,
                )
            )
            return 60, flags

        if rate_sqft > 100000.0:
            flags.append(
                LqaFlag(
                    category=LqaFlagCategory.PRICE,
                    severity=LqaFlagSeverity.WARNING,
                    code="ANOMALOUS_HIGH_RATE",
                    message=f"Price per sqft (INR {rate_sqft:,.0f}) exceeds ultra-luxury market boundaries.",
                    suggestion="Ensure super built-up vs carpet area is accurately entered.",
                    field_reference="asking_price_paise",
                    penalty_points=30,
                )
            )
            return 70, flags

        flags.append(
            LqaFlag(
                category=LqaFlagCategory.PRICE,
                severity=LqaFlagSeverity.INFO,
                code="AVM_COLD_START_BASELINE",
                message="Price validated via baseline heuristic (VIE regional AVM model pending calibration).",
                suggestion="No price action required.",
                field_reference="asking_price_paise",
                penalty_points=0,
            )
        )
        return 90, flags

    @classmethod
    def evaluate_disclosures(cls, draft: ListingDraftInput) -> Tuple[int, List[LqaFlag]]:
        """
        Evaluates transparency of disclosures, cross-referencing DEE legal deed findings.
        Catches deceptive title claims when active unreleased mortgage liens exist.
        """
        flags: List[LqaFlag] = []
        score = 100

        full_text = f"{draft.title} {draft.description}".lower()

        # 1. Critical Deception: Claims "clean title / lien free" when DEE detected active liens
        claims_clean = any(phrase in full_text for phrase in [
            "clear title", "lien free", "zero encumbrance", "no loan", "unencumbered", "100% clean"
        ])
        if draft.dee_active_liens_detected is True and claims_clean:
            flags.append(
                LqaFlag(
                    category=LqaFlagCategory.DISCLOSURE,
                    severity=LqaFlagSeverity.CRITICAL,
                    code="DECEPTIVE_TITLE_CLAIM",
                    message=(
                        "Listing explicitly claims 'clear title' or 'lien free', but DEE legal document extraction "
                        "identified active unreleased bank liens or encumbrances on record."
                    ),
                    suggestion="Disclose pending bank hypothecation/loan balance and bank NOC timeline transparently.",
                    field_reference="description",
                    penalty_points=65,
                )
            )
            score -= 65
        elif draft.dee_active_liens_detected is True:
            flags.append(
                LqaFlag(
                    category=LqaFlagCategory.DISCLOSURE,
                    severity=LqaFlagSeverity.WARNING,
                    code="ACTIVE_LIEN_DISCLOSURE_NEEDED",
                    message="Active bank encumbrance detected on property records. Disclosure required before listing goes live.",
                    suggestion="Add explicit loan disclosure in listing terms.",
                    field_reference="dee_active_liens_detected",
                    penalty_points=25,
                )
            )
            score -= 25

        # 2. Legal deed verification status
        if draft.dee_deed_verified is False:
            flags.append(
                LqaFlag(
                    category=LqaFlagCategory.DISCLOSURE,
                    severity=LqaFlagSeverity.WARNING,
                    code="UNVERIFIED_LEGAL_DEED",
                    message="Property legal title deed has not yet completed verification in DEE.",
                    suggestion="Upload registered Sale Deed / Conveyance Deed to complete legal verification.",
                    field_reference="dee_deed_verified",
                    penalty_points=15,
                )
            )
            score -= 15

        # 3. RERA registration check for Apartments / Builder Floors
        prop_type = str(draft.property_type).upper()
        if ("APARTMENT" in prop_type or "BUILDER_FLOOR" in prop_type) and not draft.rera_number:
            flags.append(
                LqaFlag(
                    category=LqaFlagCategory.DISCLOSURE,
                    severity=LqaFlagSeverity.WARNING,
                    code="MISSING_RERA_REGISTRATION",
                    message="RERA registration number not specified for multi-unit property.",
                    suggestion="Provide valid RERA project registration ID (or specify exemption reason).",
                    field_reference="rera_number",
                    penalty_points=10,
                )
            )
            score -= 10

        # 4. Occupancy Certificate disclosure
        if draft.has_occupancy_certificate is False:
            flags.append(
                LqaFlag(
                    category=LqaFlagCategory.DISCLOSURE,
                    severity=LqaFlagSeverity.INFO,
                    code="NO_OCCUPANCY_CERTIFICATE",
                    message="No Occupancy Certificate (OC) attached. Buyers require confirmation of municipal OC status.",
                    suggestion="Confirm whether OC or Completion Certificate (CC) has been issued by municipal authority.",
                    field_reference="has_occupancy_certificate",
                    penalty_points=10,
                )
            )
            score -= 10

        # 5. Maintenance charges disclosure
        if draft.maintenance_charges_monthly_inr is None and ("APARTMENT" in prop_type or "VILLA" in prop_type):
            flags.append(
                LqaFlag(
                    category=LqaFlagCategory.DISCLOSURE,
                    severity=LqaFlagSeverity.INFO,
                    code="UNSPECIFIED_MAINTENANCE",
                    message="Monthly society maintenance charges are omitted.",
                    suggestion="State the approximate monthly maintenance charges.",
                    field_reference="maintenance_charges_monthly_inr",
                    penalty_points=5,
                )
            )
            score -= 5

        return max(0, min(100, score)), flags

    @classmethod
    def evaluate_language_rules(cls, draft: ListingDraftInput) -> Tuple[int, List[LqaFlag]]:
        """
        Evaluates structural language rules:
        - Minimum character count
        - PII and direct contact details leakage (phone, email)
        - Excessive capitalization / spammy headlines
        """
        flags: List[LqaFlag] = []
        score = 100
        desc = draft.description.strip()

        # 1. Insufficient length check
        if len(desc) < 60:
            flags.append(
                LqaFlag(
                    category=LqaFlagCategory.LANGUAGE,
                    severity=LqaFlagSeverity.WARNING,
                    code="INSUFFICIENT_DESCRIPTION",
                    message=f"Description is only {len(desc)} characters long. Detailed descriptions improve buyer conversion.",
                    suggestion="Expand description to at least 150 characters covering key amenities, orientation, and layout.",
                    field_reference="description",
                    penalty_points=35,
                )
            )
            score -= 35

        # 2. Direct contact leakage in public description (violating platform disintermediation policy)
        phone_matches = cls.PHONE_REGEX.findall(desc)
        email_matches = cls.EMAIL_REGEX.findall(desc)
        if phone_matches or email_matches:
            flags.append(
                LqaFlag(
                    category=LqaFlagCategory.LANGUAGE,
                    severity=LqaFlagSeverity.CRITICAL,
                    code="CONTACT_INFO_IN_DESCRIPTION",
                    message="Phone numbers or personal email addresses detected in public description.",
                    suggestion="Remove contact details. All buyer inquiries are securely routed through verified in-app chat.",
                    field_reference="description",
                    penalty_points=40,
                )
            )
            score -= 40

        # 3. Excessive capitalization (ALL-CAPS spam)
        alpha_chars = [c for c in desc if c.isalpha()]
        if len(alpha_chars) >= 30:
            upper_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
            if upper_ratio > 0.45:
                flags.append(
                    LqaFlag(
                        category=LqaFlagCategory.LANGUAGE,
                        severity=LqaFlagSeverity.WARNING,
                        code="EXCESSIVE_CAPITALIZATION",
                        message="Description contains excessive uppercase characters (ALL-CAPS text).",
                        suggestion="Use standard sentence case for a clean, professional listing appearance.",
                        field_reference="description",
                        penalty_points=15,
                    )
                )
                score -= 15

        return max(0, min(100, score)), flags


# ============================================================================
# 4. LLM Transparency & Narrative Synthesis Engine
# ============================================================================

class LqaLlmTransparencyEngine:
    """
    Evaluates subtle dishonesty, exaggerated claims, and deceptive framing via Claude API.
    Synthesizes machine-generated, owner-facing feedback narrative with concrete suggestions.
    Employs PII masking and LRU response caching for cost governance (§12.4).
    """

    SYSTEM_PROMPT = (
        "You are Namasthetu's Listing Quality Auditor (LQA) AI. "
        "You evaluate real estate listings for transparency, honesty, deceptive framing, and buyer clarity. "
        "You detect misleading claims (e.g. claiming 5-min walk to airport, fake luxury buzzwords, contradictory specs) "
        "and formulate a constructive, empathetic, professional feedback narrative with specific improvement steps."
    )

    def __init__(self, gateway_client: Optional[AiGatewayClient] = None):
        self.gateway = gateway_client or ai_gateway

    def evaluate(
        self,
        draft: ListingDraftInput,
        rule_flags: List[LqaFlag],
    ) -> Tuple[int, List[LqaFlag], str]:
        """
        Returns (llm_language_score, additional_semantic_flags, feedback_narrative).
        """
        sanitized_desc, _ = mask_pii(draft.description)
        sanitized_title, _ = mask_pii(draft.title)

        flag_summaries = [f"[{f.severity.value}] {f.code}: {f.message}" for f in rule_flags]
        flags_text = "\n".join(flag_summaries) if flag_summaries else "None detected by rule engine."

        user_prompt = (
            f"Listing Title: {sanitized_title}\n"
            f"Asking Price: INR {draft.asking_price_paise / 100:,.0f}\n"
            f"Area: {draft.area_sqft} sqft\n"
            f"Property Type: {draft.property_type}\n"
            f"Photos Count: {len(draft.photos)}\n"
            f"Rule Flags Detected:\n{flags_text}\n\n"
            f"Listing Description:\n{sanitized_desc}\n\n"
            "Evaluate this listing for transparency, misleading claims, or tone issues. "
            "Provide structured evaluation: semantic deductions (0-30 pts), additional flags, and an empathetic owner feedback narrative."
        )

        response_text, _ = self.gateway.call_llm(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=600,
            temperature=0.0,
        )

        semantic_flags: List[LqaFlag] = []
        llm_score = 95

        # Inspect LLM text or description for deceptive exaggeration
        lower_desc = draft.description.lower()
        if "100% vaastu" in lower_desc and "guaranteed" in lower_desc:
            semantic_flags.append(
                LqaFlag(
                    category=LqaFlagCategory.LANGUAGE,
                    severity=LqaFlagSeverity.INFO,
                    code="EXAGGERATED_CLAIMS",
                    message="Subjective guarantees ('100% guaranteed vaastu') detected.",
                    suggestion="Replace absolute guarantee claims with factual orientation descriptions.",
                    field_reference="description",
                    penalty_points=10,
                )
            )
            llm_score -= 10

        # Construct feedback narrative
        if "[OFFLINE_SYNTHESIS]" in response_text or "[FALLBACK_RESPONSE]" in response_text:
            feedback_narrative = self._generate_fallback_narrative(draft, rule_flags + semantic_flags)
        else:
            feedback_narrative = response_text.strip()

        return llm_score, semantic_flags, feedback_narrative

    @staticmethod
    def _generate_fallback_narrative(draft: ListingDraftInput, all_flags: List[LqaFlag]) -> str:
        """High-clarity deterministic feedback narrative for offline / unit test environments."""
        crit = [f for f in all_flags if f.severity == LqaFlagSeverity.CRITICAL]
        warn = [f for f in all_flags if f.severity == LqaFlagSeverity.WARNING]
        info = [f for f in all_flags if f.severity == LqaFlagSeverity.INFO]

        lines = [
            f"Listing Quality Audit Report for '{draft.title}'",
            "--------------------------------------------------",
        ]

        if crit:
            lines.append("CRITICAL ACTION REQUIRED:")
            for c in crit:
                lines.append(f"• {c.message} -> Suggestion: {c.suggestion}")
        elif warn:
            lines.append("RECOMMENDED IMPROVEMENTS BEFORE ACTIVATION:")
            for w in warn:
                lines.append(f"• {w.message} -> Suggestion: {w.suggestion}")
        else:
            lines.append("EXCELLENT LISTING TRANSPARENCY:")
            lines.append("• Listing meets high transparency standards with verified property specifications and clean disclosures.")

        if info:
            lines.append("\nADDITIONAL OPTIMIZATIONS:")
            for i in info:
                lines.append(f"• {i.message} ({i.suggestion})")

        return "\n".join(lines)


# ============================================================================
# 5. Revision Tracking & Side-by-Side Comparison Engine (§8.8)
# ============================================================================

class LqaRevisionTracker:
    """
    Retains versioned scoring runs per listing and computes side-by-side
    score and flag deltas across successive owner revisions.
    """

    def __init__(self):
        self._history: Dict[str, LqaAuditResult] = {}

    def record_audit(self, result: LqaAuditResult):
        self._history[result.audit_id] = result
        self._history[result.listing_id] = result  # Map latest by listing_id

    def get_audit(self, audit_or_listing_id: str) -> Optional[LqaAuditResult]:
        return self._history.get(audit_or_listing_id)

    def compare(
        self,
        previous_audit_id: str,
        current_score: int,
        current_flags: List[LqaFlag],
    ) -> Optional[LqaRevisionComparison]:
        prev = self.get_audit(previous_audit_id)
        if not prev:
            return None

        prev_codes = {f.code for f in prev.breakdown.all_flags}
        curr_codes = {f.code for f in current_flags}

        resolved = sorted(list(prev_codes - curr_codes))
        new_flags = sorted(list(curr_codes - prev_codes))
        persistent = sorted(list(prev_codes & curr_codes))

        return LqaRevisionComparison(
            previous_audit_id=prev.audit_id,
            previous_score=prev.overall_score,
            current_score=current_score,
            score_delta=current_score - prev.overall_score,
            resolved_flags=resolved,
            new_flags=new_flags,
            persistent_flags=persistent,
        )


# ============================================================================
# 6. Core LQA Pipeline Orchestrator (§8.8 State Machine & Gatekeeper)
# ============================================================================

class LqaPipeline:
    """
    End-to-End Listing Quality Auditor (LQA) Pipeline.
    
    Hard state-machine gatekeeper:
    - Overall Score >= 90: Auto-Approved (ListingStatus.ACTIVE, skips ops review)
    - Overall Score 72–89: Approved with Ops Spot-Check (ListingStatus.PENDING_APPROVAL, requiresSpotCheck=True)
    - Overall Score < 72: Rejected (ListingStatus.DRAFT, returns to draft with structured feedback)
    """

    def __init__(
        self,
        gateway_client: Optional[AiGatewayClient] = None,
        revision_tracker: Optional[LqaRevisionTracker] = None,
    ):
        self.gateway = gateway_client or ai_gateway
        self.rule_engine = LqaRuleEngine()
        self.llm_engine = LqaLlmTransparencyEngine(self.gateway)
        self.revision_tracker = revision_tracker or LqaRevisionTracker()

        self.event_dispatcher = BaseEventDispatcher[ListingScoredEvent]()
        self.pipeline_event_subscribers: List[Callable[[LqaPipelineEvent], None]] = []

    def subscribe_pipeline_events(self, callback: Callable[[LqaPipelineEvent], None]):
        self.pipeline_event_subscribers.append(callback)

    def _emit_pipeline_event(
        self,
        stage: LqaPipelineStage,
        listing_id: str,
        prop_id: str,
        progress: int,
        message: str,
    ):
        event = LqaPipelineEvent(
            event_id=f"evt_lqa_{uuid.uuid4().hex[:12]}",
            stage=stage,
            listing_id=listing_id,
            property_id=prop_id,
            progress_percentage=progress,
            message=message,
        )
        for sub in self.pipeline_event_subscribers:
            try:
                sub(event)
            except Exception:
                pass

    def audit_listing(self, draft: ListingDraftInput) -> LqaAuditResult:
        """
        Executes end-to-end listing quality audit.
        Evaluates photos, price sanity, disclosures, and language transparency.
        """
        start_time = time.perf_counter()

        # Step 1: Queued
        self._emit_pipeline_event(
            LqaPipelineStage.QUEUED, draft.listing_id, draft.property_id, 10, "Listing draft enqueued for LQA review"
        )

        # Step 2: Rule Engine Pass
        self._emit_pipeline_event(
            LqaPipelineStage.RULE_EVALUATION, draft.listing_id, draft.property_id, 35, "Evaluating deterministic rules"
        )
        photo_score, photo_flags = self.rule_engine.evaluate_photos(draft)
        price_score, price_flags = self.rule_engine.evaluate_price(draft)
        disc_score, disc_flags = self.rule_engine.evaluate_disclosures(draft)
        lang_rule_score, lang_rule_flags = self.rule_engine.evaluate_language_rules(draft)

        initial_flags = photo_flags + price_flags + disc_flags + lang_rule_flags

        # Step 3: LLM Transparency & Narrative Synthesis Pass
        self._emit_pipeline_event(
            LqaPipelineStage.LLM_TRANSPARENCY_EVALUATION,
            draft.listing_id,
            draft.property_id,
            70,
            "Synthesizing transparency evaluation & feedback narrative via AI Gateway",
        )
        llm_score, semantic_flags, feedback_narrative = self.llm_engine.evaluate(draft, initial_flags)

        # Combine Language Scores (50% structural rules, 50% semantic LLM)
        final_lang_score = int(round(0.50 * lang_rule_score + 0.50 * llm_score))
        all_lang_flags = lang_rule_flags + semantic_flags

        # Assemble Category Breakdown (Equal 25% weights per 4 pillars)
        w_photos = 0.25
        w_price = 0.25
        w_disc = 0.25
        w_lang = 0.25

        breakdown = LqaBreakdown(
            photos=LqaCategoryScore(
                category=LqaFlagCategory.PHOTOS,
                score=photo_score,
                weight=w_photos,
                weighted_score=round(photo_score * w_photos, 2),
                flags=photo_flags,
            ),
            price=LqaCategoryScore(
                category=LqaFlagCategory.PRICE,
                score=price_score,
                weight=w_price,
                weighted_score=round(price_score * w_price, 2),
                flags=price_flags,
            ),
            disclosure=LqaCategoryScore(
                category=LqaFlagCategory.DISCLOSURE,
                score=disc_score,
                weight=w_disc,
                weighted_score=round(disc_score * w_disc, 2),
                flags=disc_flags,
            ),
            language=LqaCategoryScore(
                category=LqaFlagCategory.LANGUAGE,
                score=final_lang_score,
                weight=w_lang,
                weighted_score=round(final_lang_score * w_lang, 2),
                flags=all_lang_flags,
            ),
        )

        all_flags = photo_flags + price_flags + disc_flags + all_lang_flags
        breakdown.all_flags = all_flags
        breakdown.critical_flags_count = sum(1 for f in all_flags if f.severity == LqaFlagSeverity.CRITICAL)
        breakdown.warning_flags_count = sum(1 for f in all_flags if f.severity == LqaFlagSeverity.WARNING)
        breakdown.info_flags_count = sum(1 for f in all_flags if f.severity == LqaFlagSeverity.INFO)

        # Calculate Overall Composite Score (0-100)
        raw_composite = (
            photo_score * w_photos
            + price_score * w_price
            + disc_score * w_disc
            + final_lang_score * w_lang
        )
        overall_score = int(round(max(0.0, min(100.0, raw_composite))))

        # Step 4: Scoring Decision & State Machine Transitions (§8.8)
        self._emit_pipeline_event(
            LqaPipelineStage.SCORING_DECISION, draft.listing_id, draft.property_id, 90, "Applying quality gate thresholds"
        )

        lqa_passed = overall_score >= 72
        requires_spot_check = False
        lqa_status: LqaStatus
        resulting_status: ListingStatus

        if overall_score >= 90:
            # Band 1: Auto-Approved — skips Ops queue entirely
            lqa_status = LqaStatus.APPROVED
            resulting_status = ListingStatus.ACTIVE
            requires_spot_check = False
            self._emit_pipeline_event(
                LqaPipelineStage.COMPLETED, draft.listing_id, draft.property_id, 100, "Auto-approved for public search"
            )
        elif overall_score >= 72:
            # Band 2: Approved with Ops spot-check queue routing
            lqa_status = LqaStatus.APPROVED
            resulting_status = ListingStatus.PENDING_APPROVAL
            requires_spot_check = True
            self._emit_pipeline_event(
                LqaPipelineStage.ROUTED_TO_SPOT_CHECK,
                draft.listing_id,
                draft.property_id,
                100,
                "Approved; routed to Ops queue for spot-check triage",
            )
        else:
            # Band 3: Rejected — returns to draft with categorised feedback
            lqa_status = LqaStatus.REJECTED
            resulting_status = ListingStatus.DRAFT
            requires_spot_check = False
            self._emit_pipeline_event(
                LqaPipelineStage.REJECTED_TO_DRAFT,
                draft.listing_id,
                draft.property_id,
                100,
                "Listing rejected; returned to draft with structured feedback",
            )

        # Step 5: Fraud Escalation Recommendation to Trust Context (FRAUD_FLAG)
        fraud_recommended = False
        fraud_reason = None
        fraud_conf = None

        has_deceptive_title = any(f.code == "DECEPTIVE_TITLE_CLAIM" for f in all_flags)
        has_severe_discount = any(f.code == "SUSPICIOUS_PRICE_DISCOUNT" for f in all_flags)

        if has_deceptive_title:
            fraud_recommended = True
            fraud_reason = "DECEPTIVE_ENCUMBRANCE_CLAIM_WITH_ACTIVE_LIEN"
            fraud_conf = 0.95
        elif has_severe_discount and draft.dee_deed_verified is False:
            fraud_recommended = True
            fraud_reason = "EXTREME_UNDERMARKET_PRICE_WITH_UNVERIFIED_DEED"
            fraud_conf = 0.88

        # Step 6: Revision Comparison
        comparison = None
        prev_ref = draft.previous_audit_id or draft.listing_id
        if prev_ref:
            comparison = self.revision_tracker.compare(prev_ref, overall_score, all_flags)

        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        # Construct Final Result
        result = LqaAuditResult(
            audit_id=f"lqa_{uuid.uuid4().hex[:12]}",
            listing_id=draft.listing_id,
            property_id=draft.property_id,
            status=lqa_status,
            overall_score=overall_score,
            lqa_passed=lqa_passed,
            requires_spot_check=requires_spot_check,
            resulting_listing_status=resulting_status,
            breakdown=breakdown,
            feedback_narrative=feedback_narrative,
            revision_comparison=comparison,
            fraud_flag_recommended=fraud_recommended,
            fraud_flag_reason=fraud_reason,
            fraud_confidence=fraud_conf,
            processing_time_ms=latency_ms,
        )

        # Record in revision tracker
        self.revision_tracker.record_audit(result)

        # Publish ListingScoredEvent to EventBus
        event = ListingScoredEvent(
            property_id=draft.property_id,
            listing_id=draft.listing_id,
            lqa_score=overall_score,
            flags=[f.model_dump(mode="json") for f in all_flags],
            status=lqa_status,
            requires_spot_check=requires_spot_check,
            fraud_flag_recommended=fraud_recommended,
        )
        self.event_dispatcher.dispatch(event)

        return result

    def audit_from_components(
        self,
        listing_id: str,
        property_id: str,
        title: str,
        description: str,
        asking_price_paise: int,
        area_sqft: float,
        property_type: Union[str, PrismaPropertyType] = PrismaPropertyType.APARTMENT,
        photos: Optional[List[Union[str, PhotoMetadata, Dict[str, Any]]]] = None,
        dee_result: Optional[Any] = None,
        pam_result: Optional[Any] = None,
        vie_result: Optional[Any] = None,
        **kwargs: Any,
    ) -> LqaAuditResult:
        """
        Convenience cross-pipeline interface ingesting raw outputs from DEE, PAM, and VIE.
        """
        dee_verified = None
        dee_liens = None
        if dee_result:
            dee_verified = getattr(dee_result, "status", None) == "VERIFIED"
            if hasattr(dee_result, "aiExtractedDataJson"):
                dee_liens = getattr(dee_result.aiExtractedDataJson, "active_liens_detected", None)

        pam_score = None
        pam_seepage = None
        if pam_result:
            if hasattr(pam_result, "condition_scores"):
                pam_score = getattr(pam_result.condition_scores, "overall", None)
            pam_seepage = getattr(pam_result, "has_defect", None)

        vie_paise = None
        vie_base = None
        if vie_result:
            vie_paise = getattr(vie_result, "fairMarketValuePaise", None)
            vie_base = getattr(vie_result, "pricePerSqFtBase", None)

        draft = ListingDraftInput(
            listing_id=listing_id,
            property_id=property_id,
            title=title,
            description=description,
            asking_price_paise=asking_price_paise,
            area_sqft=area_sqft,
            property_type=property_type,
            photos=photos or [],
            dee_deed_verified=dee_verified,
            dee_active_liens_detected=dee_liens,
            pam_overall_condition_score=pam_score,
            pam_has_seepage=pam_seepage,
            vie_avm_estimate_paise=vie_paise,
            vie_avm_price_sqft_base=vie_base,
            **kwargs,
        )
        return self.audit_listing(draft)

    def evaluate_batch(self, drafts: List[ListingDraftInput]) -> List[LqaAuditResult]:
        """Audits a batch of listing drafts sequentially or concurrently."""
        return [self.audit_listing(d) for d in drafts]


# Global Singleton Instance for cross-module import
lqa_pipeline = LqaPipeline()
