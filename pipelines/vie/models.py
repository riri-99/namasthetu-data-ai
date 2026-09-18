"""
VIE (Valuation Intelligence Engine) / AVM (Automated Valuation Model)
Domain Models & Schema Contracts.

Strictly aligned with:
- Namasthetu Database Schema: src/db/schema.prisma
    - model AiValuation (lines 1166-1205)
    - model PriceForecast (lines 1655-1668)
    - model Property (lines 740-870)
- Spec Reference: Namasthetu × Hue Cycle Launch Scope v1.0 (HYC-SCO-2026-3841, §12.1-§12.4, §03.M05, §03.M09)
- PIP (Property Intelligence Profile) read-model: ai_insights.valuation
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# 1. Enums strictly matching src/db/schema.prisma & Domain Specifications
# ============================================================================

class MarketPosition(str, Enum):
    """3-State Market Position relative to current asking price."""
    BELOW_MARKET = "BELOW_MARKET"
    ALIGNED = "ALIGNED"
    ABOVE_MARKET = "ABOVE_MARKET"


class DemandSignal(str, Enum):
    """3-State Demand Intensity indicator from MIE (Market Intelligence Engine)."""
    COLD = "COLD"
    WARM = "WARM"
    HOT = "HOT"


class VieTriggerType(str, Enum):
    """Supported pipeline trigger events (§2)."""
    PROPERTY_REGISTERED = "PROPERTY_REGISTERED"
    PRICE_UPDATED = "PRICE_UPDATED"
    INSPECTION_COMPLETED = "INSPECTION_COMPLETED"
    TRANSACTION_COMPLETED = "TRANSACTION_COMPLETED"
    ADDRESS_TO_VALUE_QUERY = "ADDRESS_TO_VALUE_QUERY"


class PrismaPropertyType(str, Enum):
    """Property types matching schema.prisma lines 177-184."""
    APARTMENT = "APARTMENT"
    INDEPENDENT_HOUSE = "INDEPENDENT_HOUSE"
    VILLA = "VILLA"
    PLOT_LAND = "PLOT_LAND"
    PENTHOUSE = "PENTHOUSE"
    BUILDER_FLOOR = "BUILDER_FLOOR"


class PrismaFurnishingStatus(str, Enum):
    """Furnishing status matching schema.prisma lines 208-212."""
    UNFURNISHED = "UNFURNISHED"
    SEMI_FURNISHED = "SEMI_FURNISHED"
    FULLY_FURNISHED = "FULLY_FURNISHED"


# ============================================================================
# 2. 13-Feature Vector for LightGBM Core Valuation (§12.1 & Spec §1)
# ============================================================================

class VieFeatureVector(BaseModel):
    """
    Standard 13-feature vector fed into the LightGBM/Treelite AVM core model.
    Budgeted for <60ms P95 latency at the edge.
    """
    model_config = ConfigDict(extra="ignore")

    # 1. Physical features
    area_sqft: float = Field(..., gt=0, description="Carpet or super built-up area in sqft")
    age_years: float = Field(default=0.0, ge=0, description="Building age in years")
    floor_number: int = Field(default=1, ge=0, description="Unit floor level")
    total_floors: int = Field(default=1, ge=1, description="Total floors in building")
    bhk_count: int = Field(default=2, ge=1, le=10, description="Number of bedrooms")
    bathrooms_count: int = Field(default=2, ge=1, le=10, description="Number of bathrooms")
    furnishing_status: int = Field(
        default=1,
        ge=0,
        le=2,
        description="Furnishing: 0=Unfurnished, 1=Semi-Furnished, 2=Fully-Furnished",
    )

    # 2. Condition features (cross-pipeline from PAM / Inspection Service)
    condition_score_overall: float = Field(
        default=85.0,
        ge=0.0,
        le=100.0,
        description="Overall physical condition score (0-100) from PAM",
    )
    seepage_detected: int = Field(
        default=0,
        ge=0,
        le=1,
        description="1 if seepage/dampness detected in any inspection photo by PAM, else 0",
    )

    # 3. Micro-market & Geospatial Base (Transaction / MIE features)
    locality_price_per_sqft_base: float = Field(
        ...,
        gt=0,
        description="Baseline transaction rate (INR/sqft) for the micro-market",
    )

    # 4. Market & Demand Signals (from MIE)
    inquiry_density_score: float = Field(
        default=50.0,
        ge=0.0,
        le=100.0,
        description="Relative buyer inquiry volume per active listing (0-100)",
    )
    transaction_velocity_score: float = Field(
        default=50.0,
        ge=0.0,
        le=100.0,
        description="Velocity of deal closures in locality over past 90 days (0-100)",
    )
    neighbourhood_growth_score: float = Field(
        default=60.0,
        ge=0.0,
        le=100.0,
        description="Infrastructure, transit, and capital appreciation score (0-100)",
    )

    def to_feature_list(self) -> List[float]:
        """Convert into canonical ordered 13-feature array for LightGBM inference."""
        return [
            float(self.area_sqft),
            float(self.age_years),
            float(self.floor_number),
            float(self.total_floors),
            float(self.bhk_count),
            float(self.bathrooms_count),
            float(self.furnishing_status),
            float(self.condition_score_overall),
            float(self.seepage_detected),
            float(self.locality_price_per_sqft_base),
            float(self.inquiry_density_score),
            float(self.transaction_velocity_score),
            float(self.neighbourhood_growth_score),
        ]


# ============================================================================
# 3. Comparables Engine Models (§3 & Doc 03 M05)
# ============================================================================

class ComparableSale(BaseModel):
    """
    A single verified comparable transaction within the neighborhood radius.
    Enforces owner consent constraint: consent.comparable_inclusion (§3).
    """
    model_config = ConfigDict(extra="ignore")

    property_id: str = Field(..., description="Property unique ID")
    title: Optional[str] = Field(default=None, description="Property title or unit description")
    locality: str = Field(..., description="Micro-market or locality name")
    city: str = Field(..., description="City name")
    sale_price_paise: int = Field(..., gt=0, description="Actual closed transaction price in paise")
    area_sqft: float = Field(..., gt=0, description="Property area in square feet")
    bhk_count: int = Field(default=2, ge=1, description="BHK count")
    transacted_at: datetime = Field(..., description="Timestamp of transaction closure")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Composite similarity (0.0 - 1.0)")
    distance_meters: float = Field(default=0.0, ge=0.0, description="Distance from target property")
    consent_comparable_inclusion: bool = Field(
        default=True,
        description="Explicit owner consent flag. If False, MUST BE EXCLUDED from results.",
    )

    def to_pip_dict(self) -> Dict[str, Any]:
        """Format for PIP ai_insights.comparables list."""
        return {
            "property_id": self.property_id,
            "title": self.title,
            "locality": self.locality,
            "city": self.city,
            "similarity_score": round(self.similarity_score, 3),
            "sale_price_paise": self.sale_price_paise,
            "sale_price_inr": round(self.sale_price_paise / 100.0, 2),
            "area_sqft": self.area_sqft,
            "rate_per_sqft_inr": round((self.sale_price_paise / 100.0) / self.area_sqft, 2) if self.area_sqft > 0 else 0,
            "transacted_at": self.transacted_at.isoformat(),
            "distance_meters": round(self.distance_meters, 1),
        }


# ============================================================================
# 4. Derived / Adjacent Valuation Products (Doc 03 M09 & §3)
# ============================================================================

class MonthlyForecastPoint(BaseModel):
    """Single monthly interval point in the 12-Month Price Forecast."""
    month: int = Field(..., ge=1, le=12, description="Forecast month sequence (1 to 12)")
    month_name: str = Field(..., description="E.g. 'Oct 2026'")
    estimate_minor: int = Field(..., description="Projected central estimate in paise")
    low_minor: int = Field(..., description="90% CI band lower bound in paise")
    high_minor: int = Field(..., description="90% CI band upper bound in paise")


class InvestmentRiskScores(BaseModel):
    """
    Composite 0-100 risk scores (lower is better) matching schema.prisma lines 1178-1182.
    Integrates legal title risk from DEE, climate risk, and market risk.
    """
    model_config = ConfigDict(extra="ignore")

    overall: int = Field(default=15, ge=0, le=100, description="Composite weighted risk score")
    legal: int = Field(default=10, ge=0, le=100, description="Title & encumbrance risk from DEE")
    market: int = Field(default=20, ge=0, le=100, description="Market liquidity & volatility risk")
    climate: int = Field(default=15, ge=0, le=100, description="Flooding, heat, & structural climate risk")
    mortgage_ltv: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.5,
        description="LTV mispricing risk ratio for lender persona (§4)",
    )


class AvmValuationPrediction(BaseModel):
    """Core numerical prediction output from LightGBM model."""
    model_config = ConfigDict(extra="ignore")

    estimate_paise: int = Field(..., description="Point estimate in paise")
    confidence_low_paise: int = Field(..., description="-15% lower confidence band in paise")
    confidence_high_paise: int = Field(..., description="+15% upper confidence band in paise")
    feature_importance: Dict[str, float] = Field(default_factory=dict)
    inference_latency_ms: float = Field(default=0.0)
    model_version: str = Field(default="lightgbm-avm-v1.4-treelite")


# ============================================================================
# 5. Full Pipeline Output (1:1 with Prisma AiValuation & PriceForecast)
# ============================================================================

class VieValuationResult(BaseModel):
    """
    Complete output generated by the Valuation Intelligence Engine.
    Strictly aligns 1:1 with `model AiValuation` and `model PriceForecast` in schema.prisma.
    """
    model_config = ConfigDict(extra="ignore")

    # Identifiers
    id: str = Field(..., description="Unique valuation ID")
    property_id: str = Field(..., description="Property FK")
    model_version: str = Field(default="lightgbm-avm-v1.4-treelite")

    # Core Estimates (in minor units / paise)
    estimate_minor: int = Field(..., description="LightGBM predicted valuation in paise")
    confidence_low_minor: int = Field(..., description="-15% band in paise")
    confidence_high_minor: int = Field(..., description="+15% band in paise")

    # Market & Demand Classifications
    market_position: MarketPosition = Field(default=MarketPosition.ALIGNED)
    demand_signal: DemandSignal = Field(default=DemandSignal.WARM)

    # Composite Risk Breakdown (0 to 100, lower is better)
    risk_scores: InvestmentRiskScores = Field(default_factory=InvestmentRiskScores)

    # Comparables (Doc 03 M05: last 5-10 verified sales)
    comparables: List[ComparableSale] = Field(default_factory=list)

    # Narrative Summary (Claude LLM generated via AI Gateway)
    narrative_summary: str = Field(
        ...,
        max_length=600,
        description="Plain-English summary generated by Claude, max 600 chars",
    )

    # Ownership Lens (PIP valuation card)
    listed_price_minor: Optional[int] = Field(
        default=None,
        description="Asking price against which valuation is compared",
    )
    difference_percentage: Optional[float] = Field(
        default=None,
        description="(listed - estimate) / estimate; -3.2 = 3.2% below",
    )
    gross_yield_percentage: Optional[float] = Field(
        default=None,
        description="Annual rental yield %, e.g. 4.25",
    )
    monthly_rental_estimate_minor: Optional[int] = Field(
        default=None,
        description="Estimated monthly rental in paise",
    )
    projected_5yr_appreciation_pct: Optional[float] = Field(
        default=None,
        description="5-year projected appreciation %, e.g. 42.5",
    )
    appreciation_driver: Optional[str] = Field(
        default=None,
        description="Primary growth driver, e.g. 'Metro Line 4 extension & IT Corridor'",
    )
    historical_transactions_count: int = Field(
        default=0,
        ge=0,
        description="Count of registered sales behind the estimate",
    )

    # 12-Month Price Forecast (model PriceForecast)
    forecast_12m: List[MonthlyForecastPoint] = Field(default_factory=list)

    # Metadata & Telemetry
    feature_vector: Optional[VieFeatureVector] = None
    core_inference_latency_ms: float = Field(default=0.0)
    narrative_latency_ms: float = Field(default=0.0)
    total_pipeline_latency_ms: float = Field(default=0.0)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_prisma_ai_valuation(self) -> Dict[str, Any]:
        """
        Export dictionary strictly matching `model AiValuation` in `src/db/schema.prisma` lines 1166-1205.
        """
        return {
            "id": self.id,
            "propertyId": self.property_id,
            "estimateMinor": self.estimate_minor,
            "confidenceLowMinor": self.confidence_low_minor,
            "confidenceHighMinor": self.confidence_high_minor,
            "marketPosition": self.market_position.value,
            "demandSignal": self.demand_signal.value,
            "riskScoreOverall": self.risk_scores.overall,
            "riskScoreLegal": self.risk_scores.legal,
            "riskScoreMarket": self.risk_scores.market,
            "riskScoreClimate": self.risk_scores.climate,
            "comparablesJson": [c.to_pip_dict() for c in self.comparables],
            "narrativeSummary": self.narrative_summary,
            "listedPriceMinor": self.listed_price_minor,
            "differencePercentage": round(self.difference_percentage, 2) if self.difference_percentage is not None else None,
            "grossYieldPercentage": round(self.gross_yield_percentage, 2) if self.gross_yield_percentage is not None else None,
            "monthlyRentalEstimateMinor": self.monthly_rental_estimate_minor,
            "projected5YrAppreciationPct": round(self.projected_5yr_appreciation_pct, 2) if self.projected_5yr_appreciation_pct is not None else None,
            "appreciationDriver": self.appreciation_driver,
            "historicalTransactionsCount": self.historical_transactions_count,
            "generatedAt": self.generated_at,
        }

    def to_prisma_price_forecast(self) -> Dict[str, Any]:
        """
        Export dictionary strictly matching `model PriceForecast` in `src/db/schema.prisma` lines 1655-1668.
        """
        forecast_json = [
            {
                "month": p.month,
                "monthName": p.month_name,
                "estimateMinor": p.estimate_minor,
                "lowMinor": p.low_minor,
                "highMinor": p.high_minor,
            }
            for p in self.forecast_12m
        ]
        return {
            "propertyId": self.property_id,
            "horizonMonths": 12,
            "forecastJson": forecast_json,
            "modelVersion": self.model_version,
            "generatedAt": self.generated_at,
        }

    def to_pip_insights_payload(self) -> Dict[str, Any]:
        """
        Export public/authenticated PIP ai_insights.valuation object (§3).
        """
        return {
            "valuation": {
                "estimate_paise": self.estimate_minor,
                "estimate_inr": round(self.estimate_minor / 100.0, 2),
                "confidence_interval_low_paise": self.confidence_low_minor,
                "confidence_interval_high_paise": self.confidence_high_minor,
                "confidence_interval_inr": [
                    round(self.confidence_low_minor / 100.0, 2),
                    round(self.confidence_high_minor / 100.0, 2),
                ],
                "model_version": self.model_version,
                "computed_at": self.generated_at.isoformat(),
            },
            "market_position": {
                "position": self.market_position.value.lower(),
                "difference_pct": round(self.difference_percentage, 2) if self.difference_percentage is not None else 0.0,
            },
            "demand_signal": self.demand_signal.value.lower(),
            "summary_narrative": self.narrative_summary,
            "rental_intelligence": {
                "gross_yield_pct": round(self.gross_yield_percentage, 2) if self.gross_yield_percentage is not None else None,
                "monthly_rental_estimate_paise": self.monthly_rental_estimate_minor,
                "monthly_rental_estimate_inr": round(self.monthly_rental_estimate_minor / 100.0, 2) if self.monthly_rental_estimate_minor else None,
            },
            "growth_intelligence": {
                "projected_5yr_appreciation_pct": round(self.projected_5yr_appreciation_pct, 2) if self.projected_5yr_appreciation_pct is not None else None,
                "primary_driver": self.appreciation_driver,
            },
            "risk_score": {
                "overall": self.risk_scores.overall,
                "legal": self.risk_scores.legal,
                "market": self.risk_scores.market,
                "climate": self.risk_scores.climate,
                "mortgage_ltv": self.risk_scores.mortgage_ltv,
            },
            "comparables": [c.to_pip_dict() for c in self.comparables],
            "price_forecast_12m": [
                {
                    "month": p.month,
                    "month_name": p.month_name,
                    "estimate_inr": round(p.estimate_minor / 100.0, 2),
                    "low_inr": round(p.low_minor / 100.0, 2),
                    "high_inr": round(p.high_minor / 100.0, 2),
                }
                for p in self.forecast_12m
            ],
        }


# ============================================================================
# 6. Event Contracts & Ingestion Payloads (§2)
# ============================================================================

class ValuationPublishedEvent(BaseModel):
    """Event emitted when a valuation is published to the system event bus."""
    event_id: str
    property_id: str
    valuation_id: str
    estimate_paise: int
    confidence_interval_low_paise: int
    confidence_interval_high_paise: int
    market_position: str
    demand_signal: str
    model_version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VieTriggerEvent(BaseModel):
    """Generic trigger payload for event-driven re-valuation (§2)."""
    trigger_type: VieTriggerType
    property_id: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# 7. Continuous Learning Feedback Contract (§12.3)
# ============================================================================

class ValuationFeedback(BaseModel):
    """Feedback sample capturing ground-truth actual sales vs predicted valuation."""
    model_config = ConfigDict(extra="ignore")

    feedback_id: str
    property_id: str
    predicted_estimate_paise: int
    actual_transacted_paise: Optional[int] = None
    user_or_appraiser_override_paise: Optional[int] = None
    percentage_error: Optional[float] = None
    micro_market: str
    source_event: str = "TransactionCompleted"
    notes: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VieFeedbackMetrics(BaseModel):
    """Performance drift metrics computed over time."""
    total_events: int = 0
    mape_percentage: float = 0.0  # Mean Absolute Percentage Error
    within_15_pct_accuracy_ratio: float = 0.0
    overvalued_count: int = 0
    undervalued_count: int = 0
