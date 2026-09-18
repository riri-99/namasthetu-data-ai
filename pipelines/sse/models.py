"""
SSE (Semantic Search Engine) — Domain Models & Schema Contracts.

Strictly aligned with:
- Namasthetu Database Schema: src/db/schema.prisma
    - model Property (lines 740-870)
    - model Listing (lines 1034-1065)
    - model SavedSearch (lines 1495-1512)
- Spec Reference: Namasthetu × Hue Cycle Launch Scope v1.0 (HYC-SCO-2026-3841, §12.1-§12.4, §11, §03.M04)
- 14-Filter Parameter Search Set (HYC-SCO-2026-3841 §12.1)
- Discovery Bounded Context Event Contracts: SearchExecuted, SavedSearchAlertFired, PropertyViewed
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# 1. Enums matching src/db/schema.prisma & Discovery Domain
# ============================================================================

class QueryIntent(str, Enum):
    """Query-aware classification for dynamic retrieval weight balancing."""
    LEXICAL_HEAVY = "LEXICAL_HEAVY"      # Strict filters, addresses, builder/society names
    SEMANTIC_HEAVY = "SEMANTIC_HEAVY"    # Qualitative, lifestyle, natural language aspirations
    HYBRID = "HYBRID"                    # Balanced query containing both location/specs and qualitative needs
    INVESTOR_YIELD = "INVESTOR_YIELD"    # High rental yield, undervalued, ROI queries (VIE cross-input)
    CONDITION_FOCUSED = "CONDITION_FOCUSED" # Well-maintained, no seepage, pristine condition (PAM cross-input)
    LEGAL_VERIFIED = "LEGAL_VERIFIED"    # Clear title, RERA registered, no encumbrance (DEE cross-input)


class RerankStrategy(str, Enum):
    """Strategy for fusing lexical and semantic ranking legs."""
    RECIPROCAL_RANK_FUSION = "RECIPROCAL_RANK_FUSION"
    WEIGHTED_SCORE_FUSION = "WEIGHTED_SCORE_FUSION"
    QUERY_AWARE_HYBRID = "QUERY_AWARE_HYBRID"


class AutocompleteCategory(str, Enum):
    """Categories for type-ahead suggestions."""
    LOCALITY = "LOCALITY"
    SOCIETY = "SOCIETY"
    BUILDER = "BUILDER"
    ADDRESS = "ADDRESS"
    FILTER_SHORTCUT = "FILTER_SHORTCUT"
    NATURAL_QUERY = "NATURAL_QUERY"


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


class PrismaListingStatus(str, Enum):
    """Listing status matching schema.prisma lines 104-110."""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    UNDER_OFFER = "UNDER_OFFER"
    SOLD = "SOLD"
    EXPIRED = "EXPIRED"
    ARCHIVED = "ARCHIVED"


# ============================================================================
# 2. Canonical 14-Filter Parameter Set (§3 & §12.1)
# ============================================================================

class FourteenFilterCriteria(BaseModel):
    """
    Structured 14-filter parameter set matching §12.1 and schema.prisma `SavedSearch.filtersJson`:
    1. price (min/max in paise)
    2. area (min/max in sqft)
    3. property type
    4. configuration (BHK count)
    5. floor (min/max)
    6. age (max years)
    7. furnishing
    8. parking
    9. lift
    10. amenities
    11. verification status (PAM/DEE verified)
    12. inspection date (since date)
    13. listing date (since date)
    14. owner type (individual / builder)
    """
    model_config = ConfigDict(extra="ignore")

    # 1. Price range (paise)
    min_price_minor: Optional[int] = Field(default=None, ge=0)
    max_price_minor: Optional[int] = Field(default=None, ge=0)

    # 2. Area range (sqft)
    min_area_sqft: Optional[float] = Field(default=None, ge=0)
    max_area_sqft: Optional[float] = Field(default=None, ge=0)

    # 3. Property type
    property_types: Optional[List[PrismaPropertyType]] = None

    # 4. Configuration (e.g. ["2BHK", "3BHK"] or [2, 3])
    bhk_counts: Optional[List[int]] = None

    # 5. Floor range
    floor_min: Optional[int] = None
    floor_max: Optional[int] = None

    # 6. Age maximum (years)
    age_max_years: Optional[float] = None

    # 7. Furnishing
    furnishing_statuses: Optional[List[PrismaFurnishingStatus]] = None

    # 8. Parking required
    parking_required: Optional[bool] = None

    # 9. Lift required
    lift_required: Optional[bool] = None

    # 10. Required amenities (e.g. ["SWIMMING_POOL", "GYM", "CLUBHOUSE"])
    amenities: Optional[List[str]] = None

    # 11. Verification status
    verified_only: Optional[bool] = None          # DEE deed verified + PAM physical inspection
    no_seepage_only: Optional[bool] = None        # PAM cross-filter: seepageDetected == False
    clear_title_only: Optional[bool] = None       # DEE cross-filter: activeLiens == False

    # 12. Inspection date (PAM completed since)
    inspected_since: Optional[datetime] = None

    # 13. Listing date (active since)
    listed_since: Optional[datetime] = None

    # 14. Owner type
    owner_types: Optional[List[str]] = None       # ["INDIVIDUAL", "BUILDER", "INSTITUTIONAL"]

    # Geospatial anchor (optional radius filter)
    locality: Optional[str] = None
    city: Optional[str] = None
    target_coords: Optional[Tuple[float, float]] = None
    radius_km: Optional[float] = None

    def to_prisma_filters_json(self) -> Dict[str, Any]:
        """Convert into JSON dictionary stored in `SavedSearch.filtersJson` (schema.prisma line 1503)."""
        return self.model_dump(mode="json", exclude_none=True)


# ============================================================================
# 3. PIP Corpus Document (Materialized View Indexed by SSE)
# ============================================================================

class PipSearchDocument(BaseModel):
    """
    Materialized Property Intelligence Profile document consumed by SSE indexer.
    Assembled across all bounded contexts: Property + PAM + DEE + VIE + MIE (§3).
    """
    model_config = ConfigDict(extra="ignore")

    # Identifiers
    property_id: str
    listing_id: str
    public_id: str
    title: str
    description: str

    # Geospatial
    locality: str
    city: str
    state: str = "Karnataka"
    pincode: Optional[str] = None
    society_name: Optional[str] = None
    builder_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Physical Attributes
    property_type: PrismaPropertyType = PrismaPropertyType.APARTMENT
    configuration: str = "3BHK"
    bhk_count: int = 3
    bathrooms_count: int = 3
    carpet_area_sqft: float
    super_built_up_area_sqft: float
    floor_number: int = 4
    total_floors: int = 14
    age_years: float = 2.0
    furnishing: PrismaFurnishingStatus = PrismaFurnishingStatus.SEMI_FURNISHED
    facing: Optional[str] = "EAST"
    parking_count: int = 1
    has_lift: bool = True
    amenities: List[str] = Field(default_factory=list)

    # Listing Data
    status: PrismaListingStatus = PrismaListingStatus.ACTIVE
    listing_price_minor: int  # in paise
    owner_type: str = "INDIVIDUAL"
    listed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Cross-Pipeline Signals: PAM (Photo Analysis Module)
    inspection_id: Optional[str] = None
    inspection_score_overall: Optional[int] = None      # 0-100 from PAM
    inspection_score_structural: Optional[int] = None   # 0-100 from PAM
    seepage_detected: bool = False                      # PAM seepage flag
    inspected_at: Optional[datetime] = None

    # Cross-Pipeline Signals: DEE (Document Extraction Engine)
    deed_verified: bool = True                          # Title chain clear in DEE
    active_liens: bool = False                          # Liens / encumbrance in DEE
    rera_registration_number: Optional[str] = None

    # Cross-Pipeline Signals: VIE (Valuation Intelligence Engine)
    avm_estimate_minor: Optional[int] = None            # VIE LightGBM estimate
    market_position: Optional[str] = None               # BELOW_MARKET, ALIGNED, ABOVE_MARKET
    avm_difference_pct: Optional[float] = None          # (listed - estimate) / estimate %
    gross_rental_yield_pct: Optional[float] = None      # Annual yield from VIE
    demand_signal: Optional[str] = None                 # COLD, WARM, HOT from MIE

    # Embeddings Representation
    embedding: Optional[List[float]] = None
    embedding_version: str = "text-embedding-3-small"
    embedded_at: Optional[datetime] = None

    def build_embeddable_corpus(self) -> str:
        """
        Synthesizes structured & narrative property intelligence into an optimal text corpus
        for dense vector embedding and GIN full-text indexing (§3 & §6.2).
        """
        parts = [
            f"{self.title}.",
            f"{self.bhk_count} BHK {self.property_type.value.replace('_', ' ').title()} in {self.locality}, {self.city}.",
            f"Area: {self.carpet_area_sqft} sqft carpet ({self.super_built_up_area_sqft} sqft super built-up).",
            f"Floor: {self.floor_number} of {self.total_floors}. Furnishing: {self.furnishing.value.replace('_', ' ').title()}.",
            f"Age: {self.age_years:.1f} years.",
        ]
        if self.society_name:
            parts.append(f"Society: {self.society_name}.")
        if self.builder_name:
            parts.append(f"Builder / Developer: {self.builder_name}.")
        if self.amenities:
            parts.append(f"Amenities: {', '.join(self.amenities)}.")

        # Cross-pipeline PAM physical condition narrative
        if self.inspection_score_overall is not None:
            parts.append(f"Physical inspection condition: {self.inspection_score_overall}/100.")
            if self.seepage_detected:
                parts.append("Minor moisture/dampness observed in inspection.")
            else:
                parts.append("Verified zero seepage or dampness.")

        # Cross-pipeline DEE legal title status
        if self.deed_verified:
            parts.append("Verified legal ownership deed and clear title chain.")
        if self.active_liens:
            parts.append("Active financial lien/encumbrance recorded.")
        else:
            parts.append("Encumbrance-free title.")

        # Cross-pipeline VIE valuation narrative
        if self.market_position:
            parts.append(f"Valuation position: {self.market_position.replace('_', ' ').title()}.")
        if self.avm_difference_pct is not None and self.avm_difference_pct < -2.0:
            parts.append(f"Underpriced bargain deal ({abs(self.avm_difference_pct):.1f}% below fair market valuation).")
        if self.gross_rental_yield_pct is not None and self.gross_rental_yield_pct >= 4.5:
            parts.append(f"High rental yield investment ({self.gross_rental_yield_pct:.1f}% gross yield).")

        if self.description:
            parts.append(self.description)

        return " ".join(parts)


# ============================================================================
# 4. Search Query & Retrieval Result Entities (§2a)
# ============================================================================

class SseSearchQuery(BaseModel):
    """Query payload received by Discovery Service / SSE Query Handler."""
    model_config = ConfigDict(extra="ignore")

    raw_query: str = Field(default="", description="Natural language or keyword search query")
    filters: Optional[FourteenFilterCriteria] = Field(default=None, description="14-filter structured parameters")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="relevance", description="'relevance', 'price_asc', 'price_desc', 'yield_desc', 'newest'")
    user_id: Optional[str] = None
    rerank_strategy: RerankStrategy = Field(default=RerankStrategy.QUERY_AWARE_HYBRID)


class SearchResultItem(BaseModel):
    """Individual ranked property result item."""
    model_config = ConfigDict(extra="ignore")

    property_id: str
    listing_id: str
    public_id: str
    title: str
    locality: str
    city: str
    price_minor: int
    price_inr: float
    area_sqft: float
    bhk_count: int
    property_type: str
    furnishing: str

    # Ranking scores
    rank: int
    final_score: float              # Calibrated combined relevance score (0.0 to 1.0)
    lexical_score: float            # GIN text match score
    semantic_score: float           # pgvector cosine similarity (0.0 to 1.0)

    # Badges & Highlights
    match_reasons: List[str] = Field(default_factory=list)
    market_position: Optional[str] = None
    avm_difference_pct: Optional[float] = None
    rental_yield_pct: Optional[float] = None
    condition_score: Optional[int] = None
    verified_badges: List[str] = Field(default_factory=list)


class SseSearchResult(BaseModel):
    """Complete response returned by SSE hybrid retrieval and edge rerank."""
    model_config = ConfigDict(extra="ignore")

    query: str
    query_intent: QueryIntent
    total_hits: int
    page: int
    page_size: int
    items: List[SearchResultItem] = Field(default_factory=list)

    # Query-aware weighting diagnostics
    lexical_weight: float
    semantic_weight: float

    # P95 Telemetry (Strict <80ms budget §1)
    retrieval_latency_ms: float
    lexical_latency_ms: float
    semantic_latency_ms: float
    rerank_latency_ms: float
    total_latency_ms: float
    cache_hit: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# 5. Autocomplete & Type-Ahead Entities (§2a & §11.3)
# ============================================================================

class AutocompleteItem(BaseModel):
    """Single suggestion item in the debounced <80ms autocomplete stream."""
    text: str
    category: AutocompleteCategory
    score: float
    highlight: str
    filters_shortcut: Optional[Dict[str, Any]] = None


class AutocompleteResult(BaseModel):
    """Autocomplete suggestions response."""
    prefix: str
    suggestions: List[AutocompleteItem] = Field(default_factory=list)
    latency_ms: float

    def to_sse_transport_chunk(self, event_id: str) -> str:
        """
        Formats as Server-Sent Events wire format chunk (§11.3 & §0 Naming Collision).
        """
        import json
        data = json.dumps(self.model_dump(mode="json"))
        return f"id: {event_id}\nevent: autocomplete_suggestion\ndata: {data}\n\n"


# ============================================================================
# 6. Event Contracts (§2a & §2b)
# ============================================================================

class SearchExecutedEvent(BaseModel):
    """Event emitted on every search query execution in Discovery bounded context."""
    event_id: str
    user_id: Optional[str]
    raw_query: str
    query_intent: str
    hits_count: int
    top_property_ids: List[str]
    latency_ms: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SavedSearchAlertFiredEvent(BaseModel):
    """Event emitted when a newly activated/updated PIP matches a user's SavedSearch (§2a & §4)."""
    event_id: str
    saved_search_id: str
    user_id: str
    search_name: str
    matching_property_id: str
    matching_listing_id: str
    property_title: str
    price_minor: int
    locality: str
    city: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PropertyViewedEvent(BaseModel):
    """Click-through event emitted when user selects a search result."""
    event_id: str
    user_id: Optional[str]
    property_id: str
    query: str
    result_rank: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# 7. Learning Loop Feedback Models (§12.3)
# ============================================================================

class SearchFeedbackSample(BaseModel):
    """Search interaction sample for continuous Learning-to-Rank (LTR) retraining."""
    query: str
    query_intent: str
    returned_property_ids: List[str]
    clicked_property_id: Optional[str] = None
    clicked_rank: Optional[int] = None
    dwell_time_seconds: Optional[float] = None
    converted_to_inquiry: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SsePerformanceMetrics(BaseModel):
    """Aggregated search performance indicators."""
    total_searches: int = 0
    zero_hits_searches: int = 0
    click_through_rate: float = 0.0
    mean_reciprocal_rank: float = 0.0
    p95_latency_ms: float = 0.0
