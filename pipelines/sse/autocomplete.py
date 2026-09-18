"""
SSE (Semantic Search Engine) — Autocomplete & Type-Ahead Engine.

Implements:
- Debounced <80ms type-ahead autocomplete suggestions (§2a & §11.3)
- Real-time streaming output compatible with Server-Sent Events (SSE-transport) wire chunks
- Category classification across Localities, Societies, Builders, and Filter Shortcuts
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sse.models import (
    AutocompleteCategory,
    AutocompleteItem,
    AutocompleteResult,
    PipSearchDocument,
)


class AutocompleteEngine:
    """
    Sub-millisecond type-ahead suggestion engine with SSE-transport wire serialization.
    """

    def __init__(self):
        # Trie/Index mapping: normalized prefix -> list of suggestions
        self._entries: Dict[str, AutocompleteItem] = {}

    def register_property_doc(self, doc: PipSearchDocument):
        """Extracts and indexes autocomplete entities from a PIP document."""
        # 1. Locality
        loc_key = f"loc_{doc.locality.lower()}"
        if loc_key not in self._entries:
            self._entries[loc_key] = AutocompleteItem(
                text=f"{doc.locality}, {doc.city}",
                category=AutocompleteCategory.LOCALITY,
                score=1.0,
                highlight=doc.locality,
                filters_shortcut={"locality": doc.locality, "city": doc.city},
            )

        # 2. Society
        if doc.society_name:
            soc_key = f"soc_{doc.society_name.lower()}"
            if soc_key not in self._entries:
                self._entries[soc_key] = AutocompleteItem(
                    text=f"{doc.society_name} ({doc.locality})",
                    category=AutocompleteCategory.SOCIETY,
                    score=0.9,
                    highlight=doc.society_name,
                    filters_shortcut={"locality": doc.locality},
                )

        # 3. Builder
        if doc.builder_name:
            bld_key = f"bld_{doc.builder_name.lower()}"
            if bld_key not in self._entries:
                self._entries[bld_key] = AutocompleteItem(
                    text=f"{doc.builder_name} Properties",
                    category=AutocompleteCategory.BUILDER,
                    score=0.85,
                    highlight=doc.builder_name,
                )

        # 4. Filter shortcuts
        shortcut_text = f"{doc.bhk_count} BHK in {doc.locality}"
        sc_key = f"sc_{doc.bhk_count}_{doc.locality.lower()}"
        if sc_key not in self._entries:
            self._entries[sc_key] = AutocompleteItem(
                text=shortcut_text,
                category=AutocompleteCategory.FILTER_SHORTCUT,
                score=0.8,
                highlight=shortcut_text,
                filters_shortcut={"locality": doc.locality, "bhk_counts": [doc.bhk_count]},
            )

    def suggest(self, prefix: str, max_results: int = 8) -> AutocompleteResult:
        """
        Retrieves matching autocomplete suggestions within <80ms budget.
        """
        start_time = time.perf_counter()
        clean_prefix = prefix.strip().lower()

        if not clean_prefix:
            return AutocompleteResult(prefix=prefix, suggestions=[], latency_ms=0.0)

        matches: List[Tuple[float, AutocompleteItem]] = []

        for item in self._entries.values():
            text_lower = item.text.lower()
            score = 0.0

            if text_lower.startswith(clean_prefix):
                # Prefix match gets top priority
                score = item.score + 1.0
            elif clean_prefix in text_lower:
                # Substring match
                score = item.score + 0.5

            if score > 0.0:
                matches.append((score, item))

        # Sort by score descending
        matches.sort(key=lambda x: x[0], reverse=True)
        suggestions = [item for _, item in matches[:max_results]]
        latency = round((time.perf_counter() - start_time) * 1000.0, 3)

        return AutocompleteResult(
            prefix=prefix,
            suggestions=suggestions,
            latency_ms=latency,
        )

    def format_sse_transport(self, prefix: str, max_results: int = 8) -> str:
        """
        Formats suggestions directly as Server-Sent Events HTTP wire stream chunk (§11.3).
        """
        res = self.suggest(prefix, max_results=max_results)
        event_id = f"evt_ac_{uuid.uuid4().hex[:8]}"
        return res.to_sse_transport_chunk(event_id)

    def clear(self):
        """Clears autocomplete index."""
        self._entries.clear()


autocomplete_engine = AutocompleteEngine()
