"""
SSE (Semantic Search Engine) — Edge Rerank & Query-Aware Fusion Engine.

Implements:
- Sub-30ms Edge Reranking (Cloudflare Workers / ONNX pattern §2a)
- Query-Aware Ranking: Intent classification and dynamic weight balancing (§6.1)
- Hybrid Fusion: Reciprocal Rank Fusion (RRF) & Weighted Blended Scoring
- Cross-Pipeline Signal Amplification:
    - VIE Valuation: boosts undervalued properties & high rental yields
    - PAM Inspection: condition score weighting & seepage penalty
    - DEE Legal: clear title verification boost & active lien penalty
- Match reasons & verification badge attribution
"""

from __future__ import annotations

import math
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from sse.models import (
    PipSearchDocument,
    QueryIntent,
    RerankStrategy,
    SearchResultItem,
)


class EdgeReranker:
    """
    Combines lexical and semantic retrieval legs using query-aware ranking and edge reranking.
    """

    # Keyword intent mapping
    INVESTOR_KEYWORDS = {"yield", "undervalued", "investment", "roi", "bargain", "below market", "appreciation", "investor"}
    CONDITION_KEYWORDS = {"well-maintained", "seepage", "damp", "cracks", "renovated", "condition", "pristine", "structural"}
    LEGAL_KEYWORDS = {"clear title", "rera", "verified deed", "encumbrance", "khata", "legal", "lien"}
    LEXICAL_KEYWORDS = {"bhk", "floor", "sqft", "road", "main", "sector", "phase", "layout", "nagar", "cross"}

    def __init__(self, rrf_k: int = 60):
        self.rrf_k = rrf_k

    def detect_query_intent(self, query_text: str) -> QueryIntent:
        """
        Classifies user query intent for dynamic weight balancing (§6.1).
        """
        q = query_text.lower()
        words = set(re.findall(r"\b\w+\b", q))

        # Check investor signals (VIE)
        if any(kw in q for kw in self.INVESTOR_KEYWORDS):
            return QueryIntent.INVESTOR_YIELD

        # Check physical condition signals (PAM)
        if any(kw in q for kw in self.CONDITION_KEYWORDS):
            return QueryIntent.CONDITION_FOCUSED

        # Check legal signals (DEE)
        if any(kw in q for kw in self.LEGAL_KEYWORDS):
            return QueryIntent.LEGAL_VERIFIED

        # Check strict lexical specifications
        lex_matches = sum(1 for kw in self.LEXICAL_KEYWORDS if kw in q or kw in words)
        if lex_matches >= 2 or re.search(r"\d+\s*bhk", q) or re.search(r"\d+\s*(cr|lakh|sqft)", q):
            return QueryIntent.LEXICAL_HEAVY

        # Check qualitative semantic queries
        if len(words) >= 4 and not re.search(r"\d", q):
            return QueryIntent.SEMANTIC_HEAVY

        return QueryIntent.HYBRID

    def get_query_weights(self, intent: QueryIntent) -> Tuple[float, float]:
        """
        Returns (lexical_weight, semantic_weight) tailored to the query intent.
        """
        if intent == QueryIntent.LEXICAL_HEAVY:
            return 0.70, 0.30
        elif intent == QueryIntent.SEMANTIC_HEAVY:
            return 0.25, 0.75
        elif intent == QueryIntent.INVESTOR_YIELD:
            return 0.40, 0.60
        elif intent == QueryIntent.CONDITION_FOCUSED:
            return 0.45, 0.55
        elif intent == QueryIntent.LEGAL_VERIFIED:
            return 0.50, 0.50
        else:  # HYBRID
            return 0.50, 0.50

    def rerank(
        self,
        query_text: str,
        lexical_results: List[Tuple[PipSearchDocument, float]],
        semantic_results: List[Tuple[PipSearchDocument, float]],
        strategy: RerankStrategy = RerankStrategy.QUERY_AWARE_HYBRID,
        top_k: int = 20,
    ) -> Tuple[List[SearchResultItem], QueryIntent, float, float, float]:
        """
        Executes query-aware fusion and edge reranking.
        
        Returns:
            (ranked_items, query_intent, lexical_weight, semantic_weight, latency_ms)
        """
        start_time = time.perf_counter()
        intent = self.detect_query_intent(query_text)
        w_lex, w_sem = self.get_query_weights(intent)

        # Build candidate map
        candidates: Dict[str, Dict[str, Any]] = {}

        # 1. Process lexical leg
        for rank, (doc, score) in enumerate(lexical_results, 1):
            candidates[doc.property_id] = {
                "doc": doc,
                "lexical_score": score,
                "lexical_rank": rank,
                "semantic_score": 0.0,
                "semantic_rank": 999,
            }

        # 2. Process semantic leg
        for rank, (doc, score) in enumerate(semantic_results, 1):
            if doc.property_id not in candidates:
                candidates[doc.property_id] = {
                    "doc": doc,
                    "lexical_score": 0.0,
                    "lexical_rank": 999,
                    "semantic_score": score,
                    "semantic_rank": rank,
                }
            else:
                candidates[doc.property_id]["semantic_score"] = score
                candidates[doc.property_id]["semantic_rank"] = rank

        # 3. Compute hybrid scores
        scored_items: List[SearchResultItem] = []

        for prop_id, c in candidates.items():
            doc: PipSearchDocument = c["doc"]
            s_lex = c["lexical_score"]
            s_sem = c["semantic_score"]
            r_lex = c["lexical_rank"]
            r_sem = c["semantic_rank"]

            # Strategy Selection
            if strategy == RerankStrategy.RECIPROCAL_RANK_FUSION:
                # Standard RRF formula: 1 / (k + rank)
                base_score = (1.0 / (self.rrf_k + r_lex)) + (1.0 / (self.rrf_k + r_sem))
                # Scale to [0, 1] approximately
                final_score = min(1.0, base_score * 30.0)
            else:
                # Query-Aware Weighted Blended Score
                final_score = (w_lex * s_lex) + (w_sem * s_sem)

            # 4. Cross-Pipeline Intelligence Modifiers (§4)
            match_reasons: List[str] = []
            verified_badges: List[str] = []

            # A. Cross-Pipeline: VIE Valuation Intelligence Signals
            if doc.market_position == "BELOW_MARKET" and doc.avm_difference_pct is not None:
                if doc.avm_difference_pct < -3.0:
                    final_score += 0.05  # Bonus for high value bargain
                    match_reasons.append(f"Listed {abs(doc.avm_difference_pct):.1f}% below fair market valuation (VIE)")
            if doc.gross_rental_yield_pct is not None and doc.gross_rental_yield_pct >= 4.5:
                if intent == QueryIntent.INVESTOR_YIELD:
                    final_score += 0.08  # High yield alignment
                match_reasons.append(f"High rental yield: {doc.gross_rental_yield_pct:.1f}% gross (VIE)")

            # B. Cross-Pipeline: PAM Inspection Signals
            if doc.inspection_score_overall is not None:
                verified_badges.append(f"PAM Inspected: {doc.inspection_score_overall}/100")
                if doc.inspection_score_overall >= 90:
                    final_score += 0.03
                    match_reasons.append("Pristine physical condition score (PAM)")
            if doc.seepage_detected:
                final_score -= 0.06  # Penalty for moisture/seepage defect
                if intent == QueryIntent.CONDITION_FOCUSED:
                    final_score -= 0.15
            else:
                if intent == QueryIntent.CONDITION_FOCUSED:
                    final_score += 0.08
                    match_reasons.append("Zero dampness or seepage verified by PAM")

            # C. Cross-Pipeline: DEE Title Deed Signals
            if doc.deed_verified:
                verified_badges.append("DEE Title Verified")
                if not doc.active_liens:
                    verified_badges.append("Clear Encumbrance")
                    if intent == QueryIntent.LEGAL_VERIFIED:
                        final_score += 0.08
                        match_reasons.append("Verified clear title & encumbrance-free deed (DEE)")
            if doc.active_liens:
                final_score -= 0.08  # Penalty for financial encumbrance
                if intent == QueryIntent.LEGAL_VERIFIED:
                    final_score -= 0.20

            # Semantic match attribution
            if s_sem >= 0.70:
                match_reasons.append("High semantic intent match")

            final_score = max(0.0, min(1.0, round(final_score, 4)))

            item = SearchResultItem(
                property_id=doc.property_id,
                listing_id=doc.listing_id,
                public_id=doc.public_id,
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
                final_score=final_score,
                lexical_score=round(s_lex, 3),
                semantic_score=round(s_sem, 3),
                match_reasons=match_reasons,
                market_position=doc.market_position,
                avm_difference_pct=doc.avm_difference_pct,
                rental_yield_pct=doc.gross_rental_yield_pct,
                condition_score=doc.inspection_score_overall,
                verified_badges=verified_badges,
            )
            scored_items.append(item)

        # 5. Sort by final score descending
        scored_items.sort(key=lambda x: x.final_score, reverse=True)

        # Assign final sequential ranks
        for idx, itm in enumerate(scored_items[:top_k], 1):
            itm.rank = idx

        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 3)
        return scored_items[:top_k], intent, w_lex, w_sem, latency_ms


edge_reranker = EdgeReranker()
