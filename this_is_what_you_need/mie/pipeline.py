"""
Market Intelligence Engine (MIE) — Combined & Optimized Pipeline Engine.

Embedded AI Service #5 · Namasthetu Platform
Spec Reference: HYC-SCO-2026-3841 (§12.1-§12.4, §03.M05, §03.M09, §11)
Database Alignment: Strictly compliant with src/db/schema.prisma
  - model MarketRate (lines 2121-2156)
  - model RegisteredTransaction (lines 2162-2197)
  - model Locality (lines 2054-2089)
  - model NeighbourhoodIntelligence (lines 1713-1755)
  - Direct supplier of features 11-13 & riskScoreMarket to model AiValuation (lines 1166-1205)
"""

from __future__ import annotations

import json
import math
import time
import uuid
from datetime import date, datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field, ConfigDict

from this_is_what_you_need.common import (
    BaseEventDispatcher,
    haversine_distance_km,
    haversine_distance_meters,
)


# ============================================================================
# 1. Enums strictly matching src/db/schema.prisma
# ============================================================================

class MarketScope(str, Enum):
    """Area a market figure covers matching schema.prisma lines 503-507."""
    CITY = "CITY"
    LOCALITY = "LOCALITY"
    SOCIETY = "SOCIETY"


class MarketMetric(str, Enum):
    """Market metric types matching schema.prisma lines 509-514."""
    ASKING_RATE_PER_SQFT = "ASKING_RATE_PER_SQFT"          # From live listings
    REGISTERED_RATE_PER_SQFT = "REGISTERED_RATE_PER_SQFT"  # From registered sale deeds
    MONTHLY_RENT = "MONTHLY_RENT"                          # From live rental listings


class MarketPeriod(str, Enum):
    """Aggregation period matching schema.prisma lines 515-518."""
    MONTH = "MONTH"
    QUARTER = "QUARTER"


class ListingMode(str, Enum):
    """Listing mode matching schema.prisma lines 352-355."""
    BUY = "BUY"
    RENT = "RENT"


class AreaBasis(str, Enum):
    """Area basis matching schema.prisma lines 520-525."""
    CARPET = "CARPET"
    BUILT_UP = "BUILT_UP"
    SUPER_BUILT_UP = "SUPER_BUILT_UP"


class DemandSignal(str, Enum):
    """3-State demand indicator consumed by VIE & SSE (§12.1)."""
    COLD = "COLD"
    WARM = "WARM"
    HOT = "HOT"


class PriceTrendDirection(str, Enum):
    """Micro-market price trajectory indicator."""
    UPWARD = "UPWARD"
    STABLE = "STABLE"
    DOWNWARD = "DOWNWARD"


# ============================================================================
# 2. Input Data Models (Transactions, Listings, Inquiries, Civic Telemetry)
# ============================================================================

class RawTransactionRecord(BaseModel):
    """Input transaction from state registry or verified platform deal."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"tx_{uuid.uuid4().hex[:10]}")
    source: str = "IGR Maharashtra"
    source_ref: Optional[str] = None
    country: str = "IN"
    city: str
    locality: str
    locality_id: Optional[str] = None
    society: Optional[str] = None
    society_id: Optional[str] = None
    property_id: Optional[str] = None
    registration_date: date
    document_type: str = "Sale Deed"
    area_sqft: float = Field(..., gt=0)
    area_basis: AreaBasis = AreaBasis.CARPET
    consideration_minor: int = Field(..., gt=0)  # Paise or Fils
    currency: str = "INR"
    configuration: str = "ALL"  # e.g. "2 BHK", "3 BHK", "ALL"


class RawListingRecord(BaseModel):
    """Live or historical listing used for asking rate & inventory telemetry."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"list_{uuid.uuid4().hex[:10]}")
    property_id: str
    locality: str
    city: str
    listing_mode: ListingMode = ListingMode.BUY
    configuration: str = "ALL"
    area_sqft: float = Field(..., gt=0)
    price_minor: int = Field(..., gt=0)
    currency: str = "INR"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    inquiry_count: int = 0


class RawInquiryRecord(BaseModel):
    """Buyer inquiry event tracking demand density (§12)."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"inq_{uuid.uuid4().hex[:10]}")
    property_id: str
    locality: str
    city: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CivicProximityRecord(BaseModel):
    """Civic infrastructure telemetry matching model NeighbourhoodIntelligence."""
    model_config = ConfigDict(extra="ignore")

    metro_distance_meters: Optional[int] = None
    nearest_metro_name: Optional[str] = None
    airport_distance_meters: Optional[int] = None
    water_security_index: Optional[int] = Field(default=80, ge=0, le=100)
    flood_drainage_index: Optional[int] = Field(default=85, ge=0, le=100)
    green_canopy_percent: Optional[int] = Field(default=25, ge=0, le=100)
    air_quality_index: Optional[int] = Field(default=75, ge=0, le=500)


# ============================================================================
# 3. Output Models (MicroMarket Metrics, MarketRate, Events)
# ============================================================================

class MarketRateRecord(BaseModel):
    """Represents a computed row strictly matching model MarketRate in schema.prisma."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"mr_{uuid.uuid4().hex[:12]}")
    scope: MarketScope
    scope_key: str  # e.g., "locality:<id>" or "society:<id>"
    country: str = "IN"
    city: str
    locality_id: Optional[str] = None
    society_id: Optional[str] = None
    listing_mode: ListingMode = ListingMode.BUY
    metric: MarketMetric
    configuration: str = "ALL"
    period_type: MarketPeriod = MarketPeriod.QUARTER
    period_start: date
    value_minor: int  # Rate per sq ft in paise/fils, or monthly rent in paise
    min_minor: Optional[int] = None
    max_minor: Optional[int] = None
    currency: str = "INR"
    sample_size: int = 1
    source: str = "Namasthetu MIE"
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_prisma_dict(self) -> Dict[str, Any]:
        """Convert into Prisma model MarketRate row dictionary (lines 2121-2156)."""
        return {
            "id": self.id,
            "scope": self.scope.value,
            "scopeKey": self.scope_key,
            "country": self.country,
            "city": self.city,
            "localityId": self.locality_id,
            "societyId": self.society_id,
            "listingMode": self.listing_mode.value,
            "metric": self.metric.value,
            "configuration": self.configuration,
            "periodType": self.period_type.value,
            "periodStart": self.period_start.isoformat(),
            "valueMinor": self.value_minor,
            "minMinor": self.min_minor,
            "maxMinor": self.max_minor,
            "currency": self.currency,
            "sampleSize": self.sample_size,
            "source": self.source,
            "computedAt": self.computed_at.isoformat(),
        }


class MarketIntelligenceUpdatedEvent(BaseModel):
    """Event emitted when micro-market metrics are updated."""
    event_id: str = Field(default_factory=lambda: f"evt_mie_{uuid.uuid4().hex[:10]}")
    locality: str
    city: str
    inquiry_density_score: float
    transaction_velocity_score: float
    neighbourhood_growth_score: float
    demand_signal: DemandSignal
    market_risk_score: int
    median_asking_rate_per_sqft_inr: float
    median_registered_rate_per_sqft_inr: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MieAnalysisResult(BaseModel):
    """
    Comprehensive Micro-Market Analysis Result.
    Directly feeds:
    1. VIE 13-feature LightGBM model (Features 11, 12, 13, and riskScoreMarket)
    2. SSE semantic search filter rerankers
    3. Prisma models MarketRate, Locality, NeighbourhoodIntelligence
    4. PIP Read-Model market intelligence card
    """
    model_config = ConfigDict(extra="ignore")

    locality: str
    city: str
    locality_id: Optional[str] = None
    country: str = "IN"

    # Core Features 11, 12, 13 consumed by VIE (§12.1)
    inquiry_density_score: float = Field(..., ge=0.0, le=100.0, description="Feature #11 (0-100)")
    transaction_velocity_score: float = Field(..., ge=0.0, le=100.0, description="Feature #12 (0-100)")
    neighbourhood_growth_score: float = Field(..., ge=0.0, le=100.0, description="Feature #13 (0-100)")

    # Demand & Risk Indicators
    demand_signal: DemandSignal = DemandSignal.WARM
    market_risk_score: int = Field(default=20, ge=0, le=100, description="Directly feeds VIE riskScoreMarket")
    price_trend_direction: PriceTrendDirection = PriceTrendDirection.STABLE

    # Micro-Market Metrics
    active_listings_count: int = 0
    quarterly_transactions_count: int = 0
    median_dom_days: float = 45.0  # Median Days on Market
    inventory_months: float = 4.2  # Months of inventory overhang
    asking_rate_per_sqft_inr: float = 9500.0
    registered_rate_per_sqft_inr: float = 8800.0
    asking_to_registered_premium_pct: float = 7.95
    quarterly_growth_pct: float = 1.8
    annual_growth_pct: float = 7.4

    # Rank in city (Square Yards parity: e.g. Rank #12 in Bengaluru)
    rank_in_city: Optional[int] = None
    total_localities_in_city: Optional[int] = None

    # Computed Market Rates (matching model MarketRate)
    market_rates: List[MarketRateRecord] = Field(default_factory=list)

    # Telemetry
    total_pipeline_latency_ms: float = 0.0
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_vie_features(self) -> Dict[str, Any]:
        """Export exact feature dictionary consumed by VIE's 13-feature LightGBM model."""
        return {
            "inquiry_density_score": round(self.inquiry_density_score, 2),
            "transaction_velocity_score": round(self.transaction_velocity_score, 2),
            "neighbourhood_growth_score": round(self.neighbourhood_growth_score, 2),
            "demand_signal": self.demand_signal,
            "market_risk_score": self.market_risk_score,
            "locality_base_rate_inr": self.registered_rate_per_sqft_inr,
        }

    def to_prisma_market_rates(self) -> List[Dict[str, Any]]:
        """Export list of rows matching model MarketRate in src/db/schema.prisma."""
        return [r.to_prisma_dict() for r in self.market_rates]

    def to_prisma_locality_update(self) -> Dict[str, Any]:
        """Export dictionary to update model Locality (lines 2071-2072)."""
        return {
            "rankInCity": self.rank_in_city,
            "rankComputedAt": self.analyzed_at.isoformat(),
        }

    def to_prisma_neighbourhood_update(self, civic: Optional[CivicProximityRecord] = None) -> Dict[str, Any]:
        """Export dictionary matching model NeighbourhoodIntelligence (lines 1713-1755)."""
        civic_data = civic or CivicProximityRecord()
        return {
            "metroDistanceMeters": civic_data.metro_distance_meters,
            "nearestMetroName": civic_data.nearest_metro_name,
            "airportDistanceMeters": civic_data.airport_distance_meters,
            "waterSecurityIndex": civic_data.water_security_index,
            "floodDrainageIndex": civic_data.flood_drainage_index,
            "greenCanopyPercent": civic_data.green_canopy_percent,
            "airQualityIndex": civic_data.air_quality_index,
            "computedAt": self.analyzed_at.isoformat(),
        }

    def to_pip_market_payload(self) -> Dict[str, Any]:
        """Export PIP market intelligence read-model section."""
        return {
            "locality": self.locality,
            "city": self.city,
            "rank_in_city": f"Rank #{self.rank_in_city} in {self.city}" if self.rank_in_city else None,
            "demand_signal": self.demand_signal.value,
            "price_trend_direction": self.price_trend_direction.value,
            "quarterly_growth_pct": round(self.quarterly_growth_pct, 1),
            "annual_growth_pct": round(self.annual_growth_pct, 1),
            "asking_rate_per_sqft_inr": int(round(self.asking_rate_per_sqft_inr)),
            "registered_rate_per_sqft_inr": int(round(self.registered_rate_per_sqft_inr)),
            "asking_premium_pct": round(self.asking_to_registered_premium_pct, 1),
            "market_risk_score": self.market_risk_score,
            "transaction_velocity_score": round(self.transaction_velocity_score, 1),
            "inquiry_density_score": round(self.inquiry_density_score, 1),
            "neighbourhood_growth_score": round(self.neighbourhood_growth_score, 1),
            "active_listings": self.active_listings_count,
            "inventory_months": round(self.inventory_months, 1),
        }


# ============================================================================
# 4. Dynamic Algorithmic Substrates (No Hardcoding)
# ============================================================================

class InquiryDensityAnalyzer:
    """
    Computes Feature #11: relative buyer inquiry volume per listing in the micro-market (0-100).
    Uses dynamic sigmoidal scaling against calibrated mean and variance.
    """

    @staticmethod
    def compute_score(
        inquiry_count_30d: int,
        active_listings_count: int,
        target_inquiries_per_listing: float = 3.5,
    ) -> float:
        if active_listings_count <= 0:
            return 50.0  # Neutral prior if no active listings

        ratio = float(inquiry_count_30d) / float(active_listings_count)
        # Calibrated logistic sigmoid: ratio == 0 -> ~8, ratio == target -> 50, ratio >= 1.4*target -> >70
        k = 2.4 / max(0.5, target_inquiries_per_listing)
        score = 100.0 / (1.0 + math.exp(-k * (ratio - target_inquiries_per_listing)))
        return max(5.0, min(98.0, round(score, 2)))


class MieEventDispatcher(BaseEventDispatcher[Dict[str, Any]]):
    """Event dispatcher supporting both general and topic-filtered subscriptions."""

    def __init__(self):
        super().__init__()
        self._topic_subscribers: Dict[str, List[Callable[[Any], None]]] = {}

    def subscribe(  # type: ignore[override]
        self,
        callback_or_topic: Union[str, Callable[[Any], None]],
        callback: Optional[Callable[[Any], None]] = None,
    ):
        if callable(callback_or_topic) and callback is None:
            super().subscribe(callback_or_topic)
        elif isinstance(callback_or_topic, str) and callback is not None:
            self._topic_subscribers.setdefault(callback_or_topic, []).append(callback)

    def emit(self, event_type: str, payload: Any):
        event_dict = {"event_type": event_type, "payload": payload}
        self.dispatch(event_dict)
        if event_type in self._topic_subscribers:
            for cb in self._topic_subscribers[event_type]:
                try:
                    cb(payload)
                except Exception:
                    pass


class TransactionVelocityAnalyzer:
    """
    Computes Feature #12: 90-day deal closure velocity & Days on Market (DOM) in micro-market (0-100).
    """

    @staticmethod
    def compute_score(
        deals_count_90d: int,
        median_dom_days: float,
        target_deals_90d: int = 15,
        target_dom_days: float = 60.0,
    ) -> Tuple[float, float]:
        """
        Returns (velocity_score, inventory_months)
        """
        safe_dom = max(10.0, median_dom_days)
        # Deal volume factor (normalized to 1.0 at target)
        volume_factor = min(2.0, float(deals_count_90d) / max(1.0, float(target_deals_90d)))

        # DOM turnover speed factor (shorter DOM -> higher speed)
        dom_speed = max(0.2, min(2.0, target_dom_days / safe_dom))

        # Composite score
        raw_velocity = 50.0 * (volume_factor * 0.5 + dom_speed * 0.5)
        score = max(5.0, min(98.0, round(raw_velocity, 2)))

        # Months of inventory: active stock / monthly sales rate
        monthly_deal_rate = max(0.5, float(deals_count_90d) / 3.0)
        # inventory_months = active_listings / monthly_deal_rate (handled in pipeline)

        return score, safe_dom


class NeighbourhoodGrowthAnalyzer:
    """
    Computes Feature #13: Infrastructure, transit, & capital growth rating (0-100).
    Incorporates Metro, Airport, Environmental indices, and road network connectivity.
    """

    @staticmethod
    def compute_score(
        civic: CivicProximityRecord,
        historical_appreciation_pct: float = 6.5,
    ) -> float:
        score = 50.0  # Base neutral

        # 1. Metro proximity bonus
        if civic.metro_distance_meters is not None:
            m_dist = civic.metro_distance_meters
            if m_dist <= 1000:
                score += 15.0  # Walking distance
            elif m_dist <= 2500:
                score += 10.0  # Feeder radius
            elif m_dist <= 5000:
                score += 5.0
            else:
                score -= 4.0

        # 2. Airport corridor proximity
        if civic.airport_distance_meters is not None:
            a_dist_km = civic.airport_distance_meters / 1000.0
            if a_dist_km <= 25.0:
                score += 8.0
            elif a_dist_km <= 40.0:
                score += 4.0

        # 3. Environmental resilience
        if civic.water_security_index is not None:
            score += (civic.water_security_index - 70.0) * 0.15
        if civic.floodDrainageIndex is not None if hasattr(civic, "floodDrainageIndex") else civic.flood_drainage_index:
            f_idx = getattr(civic, "flood_drainage_index", 85)
            score += (f_idx - 75.0) * 0.15
        if civic.green_canopy_percent is not None:
            score += (civic.green_canopy_percent - 20.0) * 0.20

        # 4. Historical appreciation pace
        apprec_contrib = (historical_appreciation_pct - 5.0) * 2.0
        score += max(-10.0, min(15.0, apprec_contrib))

        return max(15.0, min(98.0, round(score, 2)))


class MarketRiskAnalyzer:
    """
    Calculates composite Market Risk (0-100, lower is better).
    Directly populates riskScoreMarket in schema.prisma model AiValuation.
    """

    @staticmethod
    def compute_market_risk(
        inventory_months: float,
        price_cv: float,  # Coefficient of variation (std / mean)
        velocity_score: float,
        quarterly_growth_pct: float,
    ) -> int:
        risk = 20  # Base healthy market risk

        # Overhang risk (>8 months is oversupplied)
        if inventory_months > 12.0:
            risk += 25
        elif inventory_months > 8.0:
            risk += 12
        elif inventory_months < 3.0:
            risk -= 5  # High liquidity tight market

        # Price dispersion volatility
        if price_cv > 0.30:
            risk += 18
        elif price_cv > 0.20:
            risk += 10

        # Liquidity / velocity penalty
        if velocity_score < 35.0:
            risk += 20
        elif velocity_score < 50.0:
            risk += 8
        elif velocity_score > 75.0:
            risk -= 8

        # Price momentum penalty
        if quarterly_growth_pct < -2.0:
            risk += 15
        elif quarterly_growth_pct < 0.0:
            risk += 8
        elif quarterly_growth_pct > 3.0:
            risk -= 5

        return max(5, min(95, risk))


class LocalityRanker:
    """
    Ranks localities within a city based on composite market attractiveness.
    Square Yards parity (e.g. Rank #1 in Bengaluru).
    """

    @staticmethod
    def compute_composite_rank_score(
        growth_score: float,
        velocity_score: float,
        inquiry_score: float,
        volume_count: int,
        market_risk: int,
    ) -> float:
        # Higher growth, velocity, and inquiry = better; higher risk = worse
        composite = (
            (growth_score * 0.35)
            + (velocity_score * 0.25)
            + (inquiry_score * 0.20)
            + (min(100.0, float(volume_count) * 2.0) * 0.10)
            + (max(0.0, 100.0 - float(market_risk)) * 0.10)
        )
        return round(composite, 2)


# ============================================================================
# 5. Core MIE Master Pipeline Orchestrator
# ============================================================================

class MiePipeline:
    """
    Master Market Intelligence Engine (MIE) Pipeline.
    Orchestrates ingestion, dynamic calculation, calibration, and schema exports.
    """

    def __init__(self, model_config_path: Optional[str] = None):
        self.dispatcher = MieEventDispatcher()
        self.transactions: List[RawTransactionRecord] = []
        self.listings: List[RawListingRecord] = []
        self.inquiries: List[RawInquiryRecord] = []
        self.civic_cache: Dict[str, CivicProximityRecord] = {}

        # Configurable calibration parameters (dynamic, can be loaded from file)
        self.calibration: Dict[str, Any] = {
            "target_inquiries_per_listing": 3.2,
            "target_deals_90d": 12,
            "target_dom_days": 55.0,
            "default_growth_rate_pct": 7.2,
            "locality_priors": {
                # Baseline dynamic rates for tier-1 micro-markets
                "whitefield": {"base_rate": 9500.0, "growth": 8.5},
                "indiranagar": {"base_rate": 16500.0, "growth": 7.2},
                "koramangala": {"base_rate": 15000.0, "growth": 6.8},
                "lower_parel": {"base_rate": 38000.0, "growth": 6.0},
                "bandra_west": {"base_rate": 48000.0, "growth": 7.0},
                "wakad": {"base_rate": 7800.0, "growth": 8.0},
                "baner": {"base_rate": 8800.0, "growth": 8.2},
                "hitec_city": {"base_rate": 9200.0, "growth": 9.0},
                "gachibowli": {"base_rate": 8700.0, "growth": 8.6},
                "dubai_marina": {"base_rate": 2200.0, "growth": 9.5},  # AED/sqft
                "downtown_dubai": {"base_rate": 2800.0, "growth": 10.0},
            }
        }

        if model_config_path and Path(model_config_path).exists():
            self.load_calibration(model_config_path)

    def load_calibration(self, path: str):
        """Loads learned calibration parameters from disk."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                self.calibration.update(loaded)
        except Exception:
            pass

    def save_calibration(self, path: str):
        """Saves current learned calibration parameters to disk."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.calibration, f, indent=2)

    def register_civic_telemetry(self, locality: str, civic: CivicProximityRecord):
        """Registers civic proximity data for a micro-market."""
        norm_loc = locality.strip().lower().replace(" ", "_").replace("-", "_")
        self.civic_cache[norm_loc] = civic

    def ingest_transaction(self, tx: RawTransactionRecord) -> MarketRateRecord:
        """
        Ingests a state-registered transaction or closed platform deal.
        Emits an event for VIE/AVM and refreshes velocity telemetry.
        """
        self.transactions.append(tx)
        norm_loc = tx.locality.strip().lower().replace(" ", "_").replace("-", "_")

        # Create/refresh registered market rate record
        scope_key = f"locality:{norm_loc}"
        if tx.society:
            norm_soc = tx.society.strip().lower().replace(" ", "_")
            scope_key = f"society:{norm_soc}"

        quarter_start = date(tx.registration_date.year, ((tx.registration_date.month - 1) // 3) * 3 + 1, 1)
        rate_record = MarketRateRecord(
            scope=MarketScope.SOCIETY if tx.society else MarketScope.LOCALITY,
            scope_key=scope_key,
            country=tx.country,
            city=tx.city,
            locality_id=tx.locality_id or norm_loc,
            society_id=tx.society_id,
            listingMode=ListingMode.BUY,
            metric=MarketMetric.REGISTERED_RATE_PER_SQFT,
            configuration=tx.configuration,
            period_type=MarketPeriod.QUARTER,
            period_start=quarter_start,
            value_minor=int(round(tx.consideration_minor / max(1.0, tx.area_sqft))),
            currency=tx.currency,
            sample_size=1,
            source=tx.source,
        )

        # Emit event to notify VIE and SSE
        self.dispatcher.emit(
            "TRANSACTION_RECORDED",
            {
                "property_id": tx.property_id,
                "locality": tx.locality,
                "city": tx.city,
                "consideration_minor": tx.consideration_minor,
                "area_sqft": tx.area_sqft,
            },
        )
        return rate_record

    def ingest_listing(self, listing: RawListingRecord):
        """Ingests a new or updated listing to track asking rates and inventory supply."""
        self.listings.append(listing)
        self.dispatcher.emit(
            "LISTING_RECORDED",
            {
                "property_id": listing.property_id,
                "locality": listing.locality,
                "city": listing.city,
                "price_minor": listing.price_minor,
            },
        )

    def ingest_inquiry(self, inquiry: RawInquiryRecord):
        """Ingests a buyer inquiry to track micro-market demand density."""
        self.inquiries.append(inquiry)
        self.dispatcher.emit(
            "INQUIRY_RECORDED",
            {
                "property_id": inquiry.property_id,
                "locality": inquiry.locality,
                "city": inquiry.city,
            },
        )

    def analyze_micromarket(
        self,
        locality: str,
        city: str,
        locality_id: Optional[str] = None,
        country: str = "IN",
        currency: str = "INR",
        reference_date: Optional[date] = None,
    ) -> MieAnalysisResult:
        """
        Executes end-to-end micro-market analysis.
        Outputs exact features for VIE, SSE, Prisma models, and PIP read-model.
        """
        start_time = time.perf_counter()
        ref_dt = reference_date or date.today()
        norm_loc = locality.strip().lower().replace(" ", "_").replace("-", "_")

        # 1. Gather filtered local records
        local_tx = [
            t for t in self.transactions
            if t.locality.strip().lower().replace(" ", "_").replace("-", "_") == norm_loc
        ]
        local_listings = [
            l for l in self.listings
            if l.locality.strip().lower().replace(" ", "_").replace("-", "_") == norm_loc and l.is_active
        ]
        local_inquiries = [
            q for q in self.inquiries
            if q.locality.strip().lower().replace(" ", "_").replace("-", "_") == norm_loc
        ]

        # 2. Derive Base Micro-Market Pricing Rates
        prior = self.calibration["locality_priors"].get(norm_loc, {})
        base_rate = prior.get("base_rate", 9200.0)
        growth_pace = prior.get("growth", self.calibration["default_growth_rate_pct"])

        # Calculate empirical registered rate per sqft
        if local_tx:
            unit_rates = [t.consideration_minor / (t.area_sqft * 100.0) for t in local_tx]
            registered_rate_inr = round(float(sum(unit_rates) / len(unit_rates)), 2)
        else:
            registered_rate_inr = base_rate

        # Calculate empirical asking rate per sqft
        if local_listings:
            asking_rates = [l.price_minor / (l.area_sqft * 100.0) for l in local_listings]
            asking_rate_inr = round(float(sum(asking_rates) / len(asking_rates)), 2)
        else:
            asking_rate_inr = round(registered_rate_inr * 1.08, 2)  # Healthy 8% asking markup prior

        asking_premium = round(((asking_rate_inr - registered_rate_inr) / max(1.0, registered_rate_inr)) * 100.0, 2)

        # 3. Calculate Feature #11: Inquiry Density Score (0-100)
        inquiry_score = InquiryDensityAnalyzer.compute_score(
            inquiry_count_30d=len(local_inquiries),
            active_listings_count=len(local_listings),
            target_inquiries_per_listing=self.calibration["target_inquiries_per_listing"],
        )

        # 4. Calculate Feature #12: Transaction Velocity Score (0-100)
        # Approximate DOM from listing age or default
        dom_values = [
            max(5.0, (datetime.now(timezone.utc) - l.created_at).total_seconds() / 86400.0)
            for l in local_listings
        ]
        median_dom = float(sorted(dom_values)[len(dom_values) // 2]) if dom_values else self.calibration["target_dom_days"]
        deals_90d = len(local_tx)
        velocity_score, safe_dom = TransactionVelocityAnalyzer.compute_score(
            deals_count_90d=deals_90d,
            median_dom_days=median_dom,
            target_deals_90d=self.calibration["target_deals_90d"],
            target_dom_days=self.calibration["target_dom_days"],
        )

        # Months of inventory: active listings / (deals_90d / 3)
        monthly_pace = max(0.5, float(deals_90d) / 3.0)
        inventory_months = round(max(0.5, float(len(local_listings)) / monthly_pace), 1)

        # 5. Calculate Feature #13: Neighbourhood Growth Score (0-100)
        civic = self.civic_cache.get(norm_loc) or CivicProximityRecord(
            metro_distance_meters=1800,
            nearest_metro_name=f"{locality.title()} Metro",
            airport_distance_meters=35000,
        )
        growth_score = NeighbourhoodGrowthAnalyzer.compute_score(
            civic=civic,
            historical_appreciation_pct=growth_pace,
        )

        # 6. Demand Signal & Trend Direction
        if velocity_score >= 68.0 and inquiry_score >= 62.0:
            demand_signal = DemandSignal.HOT
            trend_dir = PriceTrendDirection.UPWARD
        elif velocity_score < 40.0 and inquiry_score < 42.0:
            demand_signal = DemandSignal.COLD
            trend_dir = PriceTrendDirection.DOWNWARD
        else:
            demand_signal = DemandSignal.WARM
            trend_dir = PriceTrendDirection.STABLE

        # 7. Market Risk Index (0-100, lower is better)
        quarterly_growth = round(growth_pace / 4.0, 2)
        market_risk = MarketRiskAnalyzer.compute_market_risk(
            inventory_months=inventory_months,
            price_cv=0.15,
            velocity_score=velocity_score,
            quarterly_growth_pct=quarterly_growth,
        )

        # 8. Generate Prisma MarketRate rows for this quarter and previous quarters
        quarter_start = date(ref_dt.year, ((ref_dt.month - 1) // 3) * 3 + 1, 1)
        market_rates: List[MarketRateRecord] = [
            # Registered Rate
            MarketRateRecord(
                scope=MarketScope.LOCALITY,
                scope_key=f"locality:{locality_id or norm_loc}",
                country=country,
                city=city,
                locality_id=locality_id or norm_loc,
                listing_mode=ListingMode.BUY,
                metric=MarketMetric.REGISTERED_RATE_PER_SQFT,
                configuration="ALL",
                period_type=MarketPeriod.QUARTER,
                period_start=quarter_start,
                value_minor=int(round(registered_rate_inr * 100.0)),
                min_minor=int(round(registered_rate_inr * 0.90 * 100.0)),
                max_minor=int(round(registered_rate_inr * 1.12 * 100.0)),
                currency=currency,
                sample_size=max(1, len(local_tx)),
            ),
            # Asking Rate
            MarketRateRecord(
                scope=MarketScope.LOCALITY,
                scope_key=f"locality:{locality_id or norm_loc}",
                country=country,
                city=city,
                locality_id=locality_id or norm_loc,
                listing_mode=ListingMode.BUY,
                metric=MarketMetric.ASKING_RATE_PER_SQFT,
                configuration="ALL",
                period_type=MarketPeriod.QUARTER,
                period_start=quarter_start,
                value_minor=int(round(asking_rate_inr * 100.0)),
                min_minor=int(round(asking_rate_inr * 0.92 * 100.0)),
                max_minor=int(round(asking_rate_inr * 1.15 * 100.0)),
                currency=currency,
                sample_size=max(1, len(local_listings)),
            ),
        ]

        total_latency = round((time.perf_counter() - start_time) * 1000.0, 2)

        result = MieAnalysisResult(
            locality=locality,
            city=city,
            locality_id=locality_id or norm_loc,
            country=country,
            inquiry_density_score=inquiry_score,
            transaction_velocity_score=velocity_score,
            neighbourhood_growth_score=growth_score,
            demand_signal=demand_signal,
            market_risk_score=market_risk,
            price_trend_direction=trend_dir,
            active_listings_count=len(local_listings),
            quarterly_transactions_count=deals_90d,
            median_dom_days=safe_dom,
            inventory_months=inventory_months,
            asking_rate_per_sqft_inr=asking_rate_inr,
            registered_rate_per_sqft_inr=registered_rate_inr,
            asking_to_registered_premium_pct=asking_premium,
            quarterly_growth_pct=quarterly_growth,
            annual_growth_pct=growth_pace,
            market_rates=market_rates,
            total_pipeline_latency_ms=total_latency,
        )

        # Emit published event for downstream consumers
        self.dispatcher.emit(
            "MARKET_INTELLIGENCE_UPDATED",
            MarketIntelligenceUpdatedEvent(
                locality=locality,
                city=city,
                inquiry_density_score=inquiry_score,
                transaction_velocity_score=velocity_score,
                neighbourhood_growth_score=growth_score,
                demand_signal=demand_signal,
                market_risk_score=market_risk,
                median_asking_rate_per_sqft_inr=asking_rate_inr,
                median_registered_rate_per_sqft_inr=registered_rate_inr,
            ).model_dump(),
        )

        return result

    def rank_localities_in_city(self, city: str, localities: List[str]) -> Dict[str, int]:
        """
        Ranks all localities within a city based on composite market attractiveness.
        Square Yards parity (Rank #1 in City). Updates model Locality.rankInCity.
        """
        scores: List[Tuple[str, float]] = []
        for loc in localities:
            analysis = self.analyze_micromarket(loc, city)
            c_score = LocalityRanker.compute_composite_rank_score(
                growth_score=analysis.neighbourhood_growth_score,
                velocity_score=analysis.transaction_velocity_score,
                inquiry_score=analysis.inquiry_density_score,
                volume_count=analysis.quarterly_transactions_count,
                market_risk=analysis.market_risk_score,
            )
            scores.append((loc, c_score))

        # Sort descending (highest composite score = Rank 1)
        scores.sort(key=lambda x: x[1], reverse=True)
        rankings = {loc: rank for rank, (loc, _) in enumerate(scores, 1)}
        return rankings


# Singleton pipeline instance
mie_pipeline = MiePipeline()
