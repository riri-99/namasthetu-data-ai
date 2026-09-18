"""
SSE (Semantic Search Engine) — Embedding Engine.

Implements:
- Dense vector generation for PIP corpus and search queries (1536 dimensions)
- OpenAI text-embedding-3-small / AI Gateway client integration (§12.4)
- Deterministic sub-millisecond semantic vector generator for offline/edge evaluation
- Cosine similarity, Euclidean distance, and pgvector format serialization
- In-memory embeddings cache for cost governance ("cost-driven; weighting recency" §2b)
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union


class EmbeddingEngine:
    """
    Computes and manages 1536-dimensional semantic embeddings for PIP documents and search queries.
    Supports pgvector formatting and AI Gateway cost-governance caching.
    """

    DIMENSION: int = 1536

    # Domain vocabulary anchor weights for real estate semantic mapping
    REAL_ESTATE_CONCEPTS: Dict[str, Tuple[int, float]] = {
        # Spatial / Locality concepts
        "bangalore": (10, 1.0), "bengaluru": (10, 1.0), "mumbai": (11, 1.0), "gurgaon": (12, 1.0),
        "whitefield": (20, 1.2), "indiranagar": (21, 1.2), "koramangala": (22, 1.2),
        "hsr": (23, 1.2), "hebbal": (24, 1.2), "bandra": (25, 1.2), "powai": (26, 1.2),
        # Configuration & Type
        "apartment": (50, 0.8), "flat": (50, 0.8), "villa": (51, 1.2), "penthouse": (52, 1.3),
        "1bhk": (61, 1.0), "2bhk": (62, 1.0), "3bhk": (63, 1.0), "4bhk": (64, 1.0), "5bhk": (65, 1.0),
        # Luxury & Quality (PAM condition signals)
        "luxury": (100, 1.1), "premium": (101, 1.0), "renovated": (102, 1.2),
        "pristine": (103, 1.3), "well-maintained": (104, 1.2), "flawless": (105, 1.2),
        "seepage": (110, -1.5), "dampness": (111, -1.4), "cracks": (112, -1.3), "distressed": (113, -1.2),
        # Financial & Valuation (VIE signals)
        "investment": (200, 1.1), "undervalued": (201, 1.4), "bargain": (202, 1.3),
        "yield": (203, 1.3), "rental": (204, 1.1), "roi": (205, 1.2), "below_market": (206, 1.4),
        "appreciation": (207, 1.2), "growth": (208, 1.1),
        # Legal & Trust (DEE signals)
        "clear_title": (300, 1.4), "verified": (301, 1.2), "rera": (302, 1.3),
        "encumbrance_free": (303, 1.4), "khata": (304, 1.2), "lien": (305, -1.5),
        # Lifestyle & Amenities
        "pool": (400, 0.9), "gym": (401, 0.9), "clubhouse": (402, 0.9), "park": (403, 0.9),
        "metro": (404, 1.2), "transit": (405, 1.1), "school": (406, 1.0), "quiet": (407, 1.0),
        "spacious": (408, 0.9), "gated": (409, 1.0), "facing": (410, 0.8), "east": (411, 0.8),
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "text-embedding-3-small",
        dimension: int = 1536,
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model_name = model_name
        self.dimension = dimension
        self._cache: Dict[str, List[float]] = {}
        self._openai_client = None

        if self.api_key:
            try:
                import openai
                self._openai_client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                self._openai_client = None

    def get_embedding(self, text: str) -> List[float]:
        """
        Generates a 1536-dimensional normalized embedding vector.
        Utilizes caching for cost governance (§2b).
        """
        normalized_text = text.strip().lower()
        if not normalized_text:
            return [0.0] * self.dimension

        cache_key = hashlib.md5(normalized_text.encode("utf-8")).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]

        vector: List[float]
        if self._openai_client:
            try:
                resp = self._openai_client.embeddings.create(
                    model=self.model_name,
                    input=normalized_text[:8000],
                )
                vector = resp.data[0].embedding
            except Exception:
                vector = self._generate_deterministic_embedding(normalized_text)
        else:
            vector = self._generate_deterministic_embedding(normalized_text)

        # Normalize to unit length (L2 norm)
        vector = self.normalize_vector(vector)

        # Cache vector
        self._cache[cache_key] = vector
        return vector

    def _generate_deterministic_embedding(self, text: str) -> List[float]:
        """
        Deterministic, sub-millisecond semantic projection vector.
        Maps real estate concepts to dedicated dimensional slots and projects character n-grams.
        """
        vec = [0.0] * self.dimension
        words = re.findall(r"\b\w+\b", text.lower())

        # 1. Real Estate Concept Semantic Projection
        for word in words:
            if word in self.REAL_ESTATE_CONCEPTS:
                slot, weight = self.REAL_ESTATE_CONCEPTS[word]
                # Distribute weight across 8 adjacent dimensions
                for offset in range(8):
                    idx = (slot + offset * 17) % self.dimension
                    vec[idx] += weight * (1.0 / (offset + 1.0))

        # 2. Character 3-gram hash projection for vocabulary generalization
        for i in range(len(text) - 2):
            gram = text[i : i + 3]
            h = int(hashlib.md5(gram.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            sign = 1.0 if (h % 2 == 0) else -1.0
            vec[idx] += sign * 0.15

        # 3. Add base energy across sequence
        for idx, word in enumerate(words[:50]):
            h_word = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
            slot = (h_word % 500) + 500
            vec[slot] += 0.25 / (math.sqrt(idx + 1))

        return vec

    @staticmethod
    def normalize_vector(vec: List[float]) -> List[float]:
        """L2 normalize vector to unit length."""
        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0.0:
            return vec
        return [round(x / norm, 6) for x in vec]

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Calculates cosine similarity between two vectors (range -1.0 to 1.0).
        Assuming unit vectors, cosine similarity equals dot product.
        """
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        return max(-1.0, min(1.0, dot))

    @staticmethod
    def to_pgvector_string(vec: List[float]) -> str:
        """
        Formats embedding into standard PostgreSQL pgvector literal string format:
        '[0.123456, -0.654321, ...]'
        Ready for SQL INSERT/UPDATE into `vector(1536)` columns.
        """
        return "[" + ", ".join(f"{x:.6f}" for x in vec) + "]"

    @staticmethod
    def from_pgvector_string(pg_str: str) -> List[float]:
        """Parses a pgvector string '[0.1, 0.2, ...]' into Python float list."""
        clean = pg_str.strip().lstrip("[").rstrip("]")
        if not clean:
            return []
        return [float(x.strip()) for x in clean.split(",")]

    def clear_cache(self):
        """Clears embeddings cache."""
        self._cache.clear()


embedding_engine = EmbeddingEngine()
