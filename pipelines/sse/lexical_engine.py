"""
SSE (Semantic Search Engine) — Lexical & 14-Filter Evaluation Engine.

Implements:
- Postgres GIN full-text search simulation (BM25 / ts_rank scoring)
- Strict evaluation of the canonical 14-filter parameter set (§3 & §12.1)
- Cross-pipeline structured filtering (PAM seepage/condition & DEE legal encumbrance)
- Inverted token indexing for sub-millisecond keyword lookup (<2ms execution)
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from pipelines.sse.models import FourteenFilterCriteria, PipSearchDocument


class LexicalEngine:
    """
    Executes lexical GIN full-text matching and strict 14-filter structured validation.
    """

    STOP_WORDS: Set[str] = {
        "a", "an", "the", "in", "on", "at", "for", "to", "of", "and", "or", "is", "are",
        "with", "near", "by", "from", "it", "this", "that", "these", "those"
    }

    def __init__(self):
        # Inverted index: token -> list of (doc_id, term_frequency)
        self._inverted_index: Dict[str, List[Tuple[str, float]]] = {}
        self._doc_store: Dict[str, PipSearchDocument] = {}
        self._doc_lengths: Dict[str, int] = {}
        self._avg_doc_length: float = 50.0

    def index_document(self, doc: PipSearchDocument):
        """Indexes a PIP document into the inverted lexical index."""
        self._doc_store[doc.property_id] = doc
        text = f"{doc.title} {doc.description} {doc.locality} {doc.city} {doc.society_name or ''} {doc.builder_name or ''} {doc.configuration}"
        tokens = self.tokenize(text)
        self._doc_lengths[doc.property_id] = len(tokens)

        # Update term frequencies
        tf_map: Dict[str, int] = {}
        for tok in tokens:
            tf_map[tok] = tf_map.get(tok, 0) + 1

        for tok, count in tf_map.items():
            if tok not in self._inverted_index:
                self._inverted_index[tok] = []
            self._inverted_index[tok].append((doc.property_id, count / float(len(tokens))))

        # Update average doc length
        if self._doc_lengths:
            self._avg_doc_length = sum(self._doc_lengths.values()) / float(len(self._doc_lengths))

    def remove_document(self, property_id: str):
        """Removes a property from the lexical index."""
        if property_id in self._doc_store:
            del self._doc_store[property_id]
        if property_id in self._doc_lengths:
            del self._doc_lengths[property_id]
        # Clean inverted index
        for tok in list(self._inverted_index.keys()):
            self._inverted_index[tok] = [item for item in self._inverted_index[tok] if item[0] != property_id]
            if not self._inverted_index[tok]:
                del self._inverted_index[tok]

    def tokenize(self, text: str) -> List[str]:
        """Normalizes and tokenizes text into word tokens."""
        raw_words = re.findall(r"\b[a-zA-Z0-9_\-]+\b", text.lower())
        return [w for w in raw_words if w not in self.STOP_WORDS and len(w) > 1]

    def evaluate_14_filters(
        self,
        doc: PipSearchDocument,
        filters: Optional[FourteenFilterCriteria],
    ) -> bool:
        """
        Strict evaluation of the 14-filter parameter set (§12.1 & schema.prisma).
        Returns True if doc satisfies ALL specified criteria.
        """
        if not filters:
            return True

        # Filter 1: Price range (paise)
        if filters.min_price_minor is not None and doc.listing_price_minor < filters.min_price_minor:
            return False
        if filters.max_price_minor is not None and doc.listing_price_minor > filters.max_price_minor:
            return False

        # Filter 2: Area range (sqft)
        if filters.min_area_sqft is not None and doc.carpet_area_sqft < filters.min_area_sqft:
            return False
        if filters.max_area_sqft is not None and doc.carpet_area_sqft > filters.max_area_sqft:
            return False

        # Filter 3: Property Type
        if filters.property_types and doc.property_type not in filters.property_types:
            return False

        # Filter 4: Configuration (BHK Count)
        if filters.bhk_counts and doc.bhk_count not in filters.bhk_counts:
            return False

        # Filter 5: Floor Range
        if filters.floor_min is not None and doc.floor_number < filters.floor_min:
            return False
        if filters.floor_max is not None and doc.floor_number > filters.floor_max:
            return False

        # Filter 6: Age Maximum (years)
        if filters.age_max_years is not None and doc.age_years > filters.age_max_years:
            return False

        # Filter 7: Furnishing Status
        if filters.furnishing_statuses and doc.furnishing not in filters.furnishing_statuses:
            return False

        # Filter 8: Parking Required
        if filters.parking_required and doc.parking_count < 1:
            return False

        # Filter 9: Lift Required
        if filters.lift_required and not doc.has_lift:
            return False

        # Filter 10: Required Amenities
        if filters.amenities:
            doc_amenities_norm = {a.upper().replace(" ", "_") for a in doc.amenities}
            for req in filters.amenities:
                if req.upper().replace(" ", "_") not in doc_amenities_norm:
                    return False

        # Filter 11: Verification Status (Cross-Pipeline: PAM + DEE)
        if filters.verified_only and not (doc.deed_verified and doc.inspection_score_overall is not None):
            return False
        if filters.no_seepage_only and doc.seepage_detected:
            return False
        if filters.clear_title_only and (doc.active_liens or not doc.deed_verified):
            return False

        # Filter 12: Inspected Since (PAM Inspection Date)
        if filters.inspected_since:
            if not doc.inspected_at or doc.inspected_at < filters.inspected_since:
                return False

        # Filter 13: Listing Date (Listed Since)
        if filters.listed_since:
            if not doc.listed_at or doc.listed_at < filters.listed_since:
                return False

        # Filter 14: Owner Type
        if filters.owner_types:
            if doc.owner_type.upper() not in [o.upper() for o in filters.owner_types]:
                return False

        # Geospatial Locality & City Filter
        if filters.locality:
            if filters.locality.strip().lower() not in doc.locality.lower():
                return False
        if filters.city:
            if filters.city.strip().lower() != doc.city.strip().lower():
                return False

        return True

    def search_lexical(
        self,
        query_text: str,
        filters: Optional[FourteenFilterCriteria] = None,
        candidate_docs: Optional[List[PipSearchDocument]] = None,
    ) -> List[Tuple[PipSearchDocument, float]]:
        """
        Executes lexical matching and 14-filter structured filtering.
        Returns list of (doc, score) where score is in [0.0, 1.0].
        """
        docs = candidate_docs if candidate_docs is not None else list(self._doc_store.values())
        query_tokens = self.tokenize(query_text)
        n_total_docs = max(1, len(self._doc_store))

        # Filter candidates strictly by 14 filters first
        surviving_docs = [doc for doc in docs if self.evaluate_14_filters(doc, filters)]

        # If query is empty, all surviving docs match with base score 1.0
        if not query_tokens:
            return [(doc, 1.0) for doc in surviving_docs]

        scored_results: List[Tuple[PipSearchDocument, float]] = []

        # BM25 Parameters
        k1 = 1.5
        b = 0.75

        for doc in surviving_docs:
            doc_text = f"{doc.title} {doc.description} {doc.locality} {doc.city} {doc.society_name or ''} {doc.builder_name or ''} {doc.configuration}"
            doc_tokens = self.tokenize(doc_text)
            doc_len = len(doc_tokens)
            doc_tf_map: Dict[str, int] = {}
            for t in doc_tokens:
                doc_tf_map[t] = doc_tf_map.get(t, 0) + 1

            bm25_score = 0.0
            matched_terms = 0

            for q_tok in query_tokens:
                # Document frequency (number of docs containing token)
                df = len(self._inverted_index.get(q_tok, []))
                # IDF computation
                idf = math.log((n_total_docs - df + 0.5) / (df + 0.5) + 1.0)
                tf = doc_tf_map.get(q_tok, 0)

                if tf > 0:
                    matched_terms += 1
                    # Locality/Society exact match multiplier
                    field_multiplier = 1.0
                    if q_tok in doc.locality.lower() or (doc.society_name and q_tok in doc.society_name.lower()):
                        field_multiplier = 2.0
                    elif q_tok in doc.title.lower():
                        field_multiplier = 1.5

                    # BM25 term saturation
                    term_score = idf * ((tf * (k1 + 1.0)) / (tf + k1 * (1.0 - b + b * (doc_len / self._avg_doc_length))))
                    bm25_score += term_score * field_multiplier

            # Normalize BM25 score to [0.0, 1.0]
            coverage_ratio = matched_terms / float(len(query_tokens))
            normalized_score = min(1.0, (bm25_score / (len(query_tokens) * 3.5)) * 0.7 + (coverage_ratio * 0.3))

            # Only include if at least one token matched OR if the query is very loose
            if matched_terms > 0:
                scored_results.append((doc, round(normalized_score, 4)))

        # Sort by score descending
        scored_results.sort(key=lambda x: x[1], reverse=True)
        return scored_results


lexical_engine = LexicalEngine()
