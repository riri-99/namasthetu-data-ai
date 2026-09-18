"""
Semantic Search Engine (SSE) — Combined & Optimized Pipeline Engine.

Embedded AI Service #4 · Namasthetu Platform (Discovery Context)
Spec Reference: HYC-SCO-2026-3841 (§12.1-§12.4, §11, §03.M04)
Database Alignment: Strictly compliant with src/db/schema.prisma (models SavedSearch, Listing, Property)
"""

from __future__ import annotations

import json
import math
import re
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field, ConfigDict

from this_is_what_you_need.common import (
    BaseEventDispatcher,
    PrismaFurnishingStatus,
    PrismaListingStatus,
    PrismaPropertyType,
    ai_gateway,
)


# ============================================================================
# 1. Domain Enums
# ============================================================================

class QueryIntent(str, Enum):
    LEXICAL_HEAVY = "LEXICAL_HEAVY"
    SEMANTIC_HEAVY = "SEMANTIC_HEAVY"
    HYBRID = "HYBRID"
    INVESTOR_YIELD = "INVESTOR_YIELD"
    CONDITION_FOCUSED = "CONDITION_FOCUSED"
    LEGAL_VERIFIED = "LEGAL_VERIFIED"


class AutocompleteCategory(str, Enum):
    LOCALITY = "LOCALITY"
    SOCIETY = "SOCIETY"
    BUILDER = "BUILDER"
    FILTER_SHORTCUT = "FILTER_SHORTCUT"


# ============================================================================
# 2. 14-Filter Set & Document Models
# ============================================================================

class FourteenFilterCriteria(BaseModel):
    model_config = ConfigDict(extra="ignore")

    min_price_minor: Optional[int] = None
    max_price_minor: Optional[int] = None
    min_area_sqft: Optional[float] = None
    max_area_sqft: Optional[float] = None
    property_types: Optional[List[PrismaPropertyType]] = None
    bhk_counts: Optional[List[int]] = None
    floor_min: Optional[int] = None
    floor_max: Optional[int] = None
    age_max_years: Optional[float] = None
    furnishing_statuses: Optional[List[PrismaFurnishingStatus]] = None
    parking_required: Optional[bool] = None
    lift_required: Optional[bool] = None
    amenities: Optional[List[str]] = None
    verified_only: Optional[bool] = None
    no_seepage_only: Optional[bool] = None
    clear_title_only: Optional[bool] = None
    locality: Optional[str] = None
    city: Optional[str] = None

    def to_prisma_filters_json(self) -> Dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class PipSearchDocument(BaseModel):
    """Materialized PIP view indexed for hybrid retrieval."""
    model_config = ConfigDict(extra="ignore")

    property_id: str
    listing_id: str
    public_id: str
    title: str
    description: str
    locality: str
    city: str
    society_name: Optional[str] = None
    builder_name: Optional[str] = None
    property_type: PrismaPropertyType = PrismaPropertyType.APARTMENT
    configuration: str = "3BHK"
    bhk_count: int = 3
    carpet_area_sqft: float
    super_built_up_area_sqft: float
    floor_number: int = 4
    total_floors: int = 14
    age_years: float = 2.0
    furnishing: PrismaFurnishingStatus = PrismaFurnishingStatus.SEMI_FURNISHED
    parking_count: int = 1
    has_lift: bool = True
    amenities: List[str] = Field(default_factory=list)
    listing_price_minor: int
    status: PrismaListingStatus = PrismaListingStatus.ACTIVE

    # Cross-pipeline PAM / DEE / VIE signals
    inspection_score_overall: Optional[int] = None
    seepage_detected: bool = False
    deed_verified: bool = True
    active_liens: bool = False
    avm_estimate_minor: Optional[int] = None
    market_position: Optional[str] = None
    avm_difference_pct: Optional[float] = None
    gross_rental_yield_pct: Optional[float] = None

    embedding: Optional[List[float]] = None

    def build_embeddable_corpus(self) -> str:
        parts = [
            f"{self.title}.",
            f"{self.bhk_count} BHK {self.property_type.value.title()} in {self.locality}, {self.city}.",
            f"Area: {self.carpet_area_sqft} sqft carpet.",
            f"Floor {self.floor_number} of {self.total_floors}. Furnishing: {self.furnishing.value}.",
        ]
        if self.society_name:
            parts.append(f"Society: {self.society_name}.")
        if self.builder_name:
            parts.append(f"Builder: {self.builder_name}.")
        if self.inspection_score_overall is not None:
            parts.append(f"Condition: {self.inspection_score_overall}/100.")
            if self.seepage_detected:
                parts.append("Dampness/seepage noted.")
            else:
                parts.append("Zero seepage.")
        if self.deed_verified and not self.active_liens:
            parts.append("Clear verified title.")
        if self.market_position:
            parts.append(f"Valuation: {self.market_position}.")
        if self.gross_rental_yield_pct:
            parts.append(f"Yield: {self.gross_rental_yield_pct:.1f}%.")
        return " ".join(parts)


class SearchResultItem(BaseModel):
    property_id: str
    listing_id: str
    title: str
    locality: str
    city: str
    price_minor: int
    price_inr: float
    area_sqft: float
    bhk_count: int
    property_type: str
    furnishing: str
    rank: int
    final_score: float
    match_reasons: List[str] = Field(default_factory=list)
    verified_badges: List[str] = Field(default_factory=list)


class SseSearchResult(BaseModel):
    query: str
    query_intent: QueryIntent
    total_hits: int
    items: List[SearchResultItem] = Field(default_factory=list)
    total_latency_ms: float
    cache_hit: bool = False


# ============================================================================
# 3. Core SSE Pipeline Orchestrator
# ============================================================================

class SsePipeline:
    """Hybrid Semantic Search Engine with <80ms P95 latency target."""

    def __init__(self):
        self._doc_corpus: Dict[str, PipSearchDocument] = {}
        self._saved_searches: Dict[str, Dict[str, Any]] = {}
        self._autocomplete_entries: Dict[str, Tuple[str, AutocompleteCategory]] = {}

    def index_pip_document(self, doc: PipSearchDocument):
        # 1. Compute Embedding
        if doc.embedding is None:
            doc.embedding = ai_gateway.get_embedding(doc.build_embeddable_corpus())
        self._doc_corpus[doc.property_id] = doc

        # 2. Autocomplete register
        self._autocomplete_entries[doc.locality.lower()] = (f"{doc.locality}, {doc.city}", AutocompleteCategory.LOCALITY)
        if doc.society_name:
            self._autocomplete_entries[doc.society_name.lower()] = (f"{doc.society_name} ({doc.locality})", AutocompleteCategory.SOCIETY)

    def evaluate_14_filters(self, doc: PipSearchDocument, f: Optional[FourteenFilterCriteria]) -> bool:
        if not f:
            return True
        if f.min_price_minor and doc.listing_price_minor < f.min_price_minor:
            return False
        if f.max_price_minor and doc.listing_price_minor > f.max_price_minor:
            return False
        if f.min_area_sqft and doc.carpet_area_sqft < f.min_area_sqft:
            return False
        if f.max_area_sqft and doc.carpet_area_sqft > f.max_area_sqft:
            return False
        if f.property_types and doc.property_type not in f.property_types:
            return False
        if f.bhk_counts and doc.bhk_count not in f.bhk_counts:
            return False
        if f.floor_min and doc.floor_number < f.floor_min:
            return False
        if f.floor_max and doc.floor_number > f.floor_max:
            return False
        if f.age_max_years and doc.age_years > f.age_max_years:
            return False
        if f.furnishing_statuses and doc.furnishing not in f.furnishing_statuses:
            return False
        if f.parking_required and doc.parking_count < 1:
            return False
        if f.lift_required and not doc.has_lift:
            return False
        if f.verified_only and not (doc.deed_verified and doc.inspection_score_overall is not None):
            return False
        if f.no_seepage_only and doc.seepage_detected:
            return False
        if f.clear_title_only and (doc.active_liens or not doc.deed_verified):
            return False
        if f.locality and f.locality.lower() not in doc.locality.lower():
            return False
        if f.city and f.city.lower() != doc.city.lower():
            return False
        return True

    def search(self, raw_query: str, filters: Optional[FourteenFilterCriteria] = None, top_k: int = 10) -> SseSearchResult:
        start_time = time.perf_counter()
        q_lower = raw_query.lower()

        # Classify intent
        intent = QueryIntent.HYBRID
        if any(w in q_lower for w in ["yield", "undervalued", "investment", "roi", "bargain"]):
            intent = QueryIntent.INVESTOR_YIELD
        elif any(w in q_lower for w in ["well-maintained", "seepage", "cracks", "condition", "pristine"]):
            intent = QueryIntent.CONDITION_FOCUSED
        elif any(w in q_lower for w in ["clear title", "rera", "verified", "encumbrance"]):
            intent = QueryIntent.LEGAL_VERIFIED

        q_vec = ai_gateway.get_embedding(raw_query) if raw_query else None
        scored_items: List[SearchResultItem] = []

        for doc in self._doc_corpus.values():
            if not self.evaluate_14_filters(doc, filters):
                continue

            # Lexical score
            words = [w for w in re.findall(r"\b\w+\b", q_lower) if len(w) > 2]
            text = f"{doc.title} {doc.description} {doc.locality} {doc.city} {doc.society_name or ''}".lower()
            lex_score = sum(1.0 for w in words if w in text) / float(max(1, len(words))) if words else 0.5

            # Semantic score
            sem_score = 0.5
            if q_vec and doc.embedding:
                sem_score = max(0.0, sum(a * b for a, b in zip(q_vec, doc.embedding)))

            # Fusion & signal amplification
            final_score = (lex_score * 0.45) + (sem_score * 0.55)
            match_reasons = []
            badges = []

            # Cross-pipeline modifiers
            if doc.market_position == "BELOW_MARKET":
                final_score += 0.05
                match_reasons.append("Below fair market valuation (VIE)")
            if doc.gross_rental_yield_pct and doc.gross_rental_yield_pct >= 4.5:
                if intent == QueryIntent.INVESTOR_YIELD:
                    final_score += 0.08
                match_reasons.append(f"High rental yield: {doc.gross_rental_yield_pct:.1f}% (VIE)")
            if doc.inspection_score_overall and doc.inspection_score_overall >= 90:
                badges.append(f"PAM Inspected: {doc.inspection_score_overall}/100")
            if doc.seepage_detected:
                final_score -= 0.08
            else:
                if intent == QueryIntent.CONDITION_FOCUSED:
                    final_score += 0.08
            if doc.deed_verified and not doc.active_liens:
                badges.append("Clear Title (DEE)")
                if intent == QueryIntent.LEGAL_VERIFIED:
                    final_score += 0.08

            item = SearchResultItem(
                property_id=doc.property_id,
                listing_id=doc.listing_id,
                title=doc.title,
                locality=doc.locality,
                city=doc.city,
                price_minor=doc.listing_price_minor,
                price_inr=round(doc.listing_price_minor / 100.0, 2),
                area_sqft=doc.carpet_area_sqft,
                bhk_count=doc.bhk_count,
                property_type=doc.property_type.value,
                furnishing=doc.furnishing.value,
                rank=1,
                final_score=round(final_score, 3),
                match_reasons=match_reasons,
                verified_badges=badges,
            )
            scored_items.append(item)

        scored_items.sort(key=lambda x: x.final_score, reverse=True)
        for i, itm in enumerate(scored_items[:top_k], 1):
            itm.rank = i

        latency = round((time.perf_counter() - start_time) * 1000.0, 2)
        return SseSearchResult(
            query=raw_query,
            query_intent=intent,
            total_hits=len(scored_items),
            items=scored_items[:top_k],
            total_latency_ms=latency,
        )

    def autocomplete(self, prefix: str) -> List[Dict[str, Any]]:
        p = prefix.lower()
        results = []
        for k, (text, cat) in self._autocomplete_entries.items():
            if p in k:
                results.append({"text": text, "category": cat.value})
        return results[:8]

    def autocomplete_stream_chunk(self, prefix: str) -> str:
        res = self.autocomplete(prefix)
        return f"id: evt_ac_{uuid.uuid4().hex[:8]}\nevent: autocomplete_suggestion\ndata: {json.dumps(res)}\n\n"


sse_pipeline = SsePipeline()
