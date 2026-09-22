"""
SSE (Semantic Search Engine) — Saved Searches & Alert Engine.

Implements:
- 1:1 Schema mapping to `model SavedSearch` in `src/db/schema.prisma` lines 1495-1512
- Evaluation of incoming PIP documents against active 14-filter saved searches
- Emission of `SavedSearchAlertFiredEvent` for instant buyer notifications (§2a & §4)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from pipelines.sse.models import (
    FourteenFilterCriteria,
    PipSearchDocument,
    SavedSearchAlertFiredEvent,
)
from pipelines.sse.lexical_engine import lexical_engine


class SavedSearchManager:
    """
    Evaluates new or updated properties against stored user saved search filter combinations.
    """

    def __init__(self):
        # In-memory saved search registry: id -> record
        self._saved_searches: Dict[str, Dict[str, Any]] = {}
        self._alert_subscribers: List[Callable[[SavedSearchAlertFiredEvent], None]] = []

    def subscribe_alerts(self, callback: Callable[[SavedSearchAlertFiredEvent], None]):
        """Subscribes an event listener to the SavedSearchAlertFired stream."""
        self._alert_subscribers.append(callback)

    def register_saved_search(
        self,
        user_id: str,
        name: str,
        filters: FourteenFilterCriteria,
        alerts_enabled: bool = True,
        saved_search_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates a SavedSearch record strictly matching `model SavedSearch` in schema.prisma.
        """
        sid = saved_search_id or f"ss_{uuid.uuid4().hex[:12]}"
        record = {
            "id": sid,
            "userId": user_id,
            "name": name,
            "filtersJson": filters.to_prisma_filters_json(),
            "filters_obj": filters,
            "alertsEnabled": alerts_enabled,
            "lastAlertedAt": None,
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc),
        }
        self._saved_searches[sid] = record
        return record

    def delete_saved_search(self, saved_search_id: str) -> bool:
        """Removes a saved search."""
        if saved_search_id in self._saved_searches:
            del self._saved_searches[saved_search_id]
            return True
        return False

    def evaluate_new_listing(self, doc: PipSearchDocument) -> List[SavedSearchAlertFiredEvent]:
        """
        Evaluates a newly activated or updated PIP against all active saved searches.
        Emits SavedSearchAlertFiredEvent for matches (§2a).
        """
        now = datetime.now(timezone.utc)
        fired_alerts: List[SavedSearchAlertFiredEvent] = []

        for sid, record in self._saved_searches.items():
            if not record["alertsEnabled"]:
                continue

            filters: FourteenFilterCriteria = record["filters_obj"]

            # Evaluate 14 filters
            if lexical_engine.evaluate_14_filters(doc, filters):
                alert_event = SavedSearchAlertFiredEvent(
                    event_id=f"evt_ssa_{uuid.uuid4().hex[:12]}",
                    saved_search_id=sid,
                    user_id=record["userId"],
                    search_name=record["name"],
                    matching_property_id=doc.property_id,
                    matching_listing_id=doc.listing_id,
                    property_title=doc.title,
                    price_minor=doc.listing_price_minor,
                    locality=doc.locality,
                    city=doc.city,
                    timestamp=now,
                )
                record["lastAlertedAt"] = now
                record["updatedAt"] = now
                fired_alerts.append(alert_event)

                # Dispatch to subscribers
                for sub in self._alert_subscribers:
                    try:
                        sub(alert_event)
                    except Exception:
                        pass

        return fired_alerts

    def clear(self):
        """Clears saved search store."""
        self._saved_searches.clear()


saved_search_manager = SavedSearchManager()
