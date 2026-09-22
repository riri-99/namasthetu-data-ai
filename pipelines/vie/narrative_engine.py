"""
VIE (Valuation Intelligence Engine) — Narrative Engine.

Implements:
- Claude API narrative overlay routed via AI Gateway pattern (§12.4 & §1)
- Explainable natural language valuation summary (max 600 chars)
- In-memory response caching with hash key for cost governance (up to 60% savings §12.4)
- High-fidelity contextual fallback generator when offline or API key is absent
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from pipelines.vie.models import (
    DemandSignal,
    InvestmentRiskScores,
    MarketPosition,
    VieFeatureVector,
)


class NarrativeEngine:
    """
    Generates plain-English narrative summaries alongside numeric AVM estimates.
    Satisfies §12.1 Claude narrative layer and AI Gateway caching requirement (§12.4).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        gateway_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.gateway_url = gateway_url or os.environ.get("AI_GATEWAY_URL")
        self._cache: Dict[str, str] = {}
        self._client = None

        if self.api_key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                self._client = None

    def generate_narrative(
        self,
        property_title: str,
        locality: str,
        city: str,
        estimate_paise: int,
        confidence_low_paise: int,
        confidence_high_paise: int,
        market_position: MarketPosition,
        difference_pct: Optional[float],
        demand_signal: DemandSignal,
        risk_scores: InvestmentRiskScores,
        features: VieFeatureVector,
        comparables_count: int,
    ) -> Tuple[str, float]:
        """
        Generates a concise, high-value valuation narrative (max 600 chars).
        
        Returns:
            (narrative_text, latency_ms)
        """
        start_time = time.perf_counter()

        # Build cache key to satisfy §12.4 AI Gateway cost governance
        cache_key = self._compute_cache_key(
            locality=locality,
            estimate_paise=estimate_paise,
            market_position=market_position.value,
            difference_pct=difference_pct,
            condition_score=features.condition_score_overall,
            seepage=features.seepage_detected,
            legal_risk=risk_scores.legal,
        )

        if cache_key in self._cache:
            latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            return self._cache[cache_key], latency_ms

        narrative: str
        # 1. Attempt LLM invocation if client configured
        if self._client:
            try:
                narrative = self._call_claude_llm(
                    property_title=property_title,
                    locality=locality,
                    city=city,
                    estimate_paise=estimate_paise,
                    confidence_low_paise=confidence_low_paise,
                    confidence_high_paise=confidence_high_paise,
                    market_position=market_position,
                    difference_pct=difference_pct,
                    demand_signal=demand_signal,
                    risk_scores=risk_scores,
                    features=features,
                    comparables_count=comparables_count,
                )
            except Exception:
                narrative = self._generate_contextual_fallback(
                    property_title=property_title,
                    locality=locality,
                    city=city,
                    estimate_paise=estimate_paise,
                    market_position=market_position,
                    difference_pct=difference_pct,
                    demand_signal=demand_signal,
                    risk_scores=risk_scores,
                    features=features,
                    comparables_count=comparables_count,
                )
        else:
            narrative = self._generate_contextual_fallback(
                property_title=property_title,
                locality=locality,
                city=city,
                estimate_paise=estimate_paise,
                market_position=market_position,
                difference_pct=difference_pct,
                demand_signal=demand_signal,
                risk_scores=risk_scores,
                features=features,
                comparables_count=comparables_count,
            )

        # Enforce max 600 characters constraint
        if len(narrative) > 600:
            narrative = narrative[:597] + "..."

        self._cache[cache_key] = narrative
        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        return narrative, latency_ms

    def _call_claude_llm(
        self,
        property_title: str,
        locality: str,
        city: str,
        estimate_paise: int,
        confidence_low_paise: int,
        confidence_high_paise: int,
        market_position: MarketPosition,
        difference_pct: Optional[float],
        demand_signal: DemandSignal,
        risk_scores: InvestmentRiskScores,
        features: VieFeatureVector,
        comparables_count: int,
    ) -> str:
        """Call Claude API through Gateway client."""
        est_cr = round((estimate_paise / 100.0) / 10000000.0, 2)
        low_cr = round((confidence_low_paise / 100.0) / 10000000.0, 2)
        high_cr = round((confidence_high_paise / 100.0) / 10000000.0, 2)

        system_prompt = (
            "You are the Valuation Intelligence Engine (VIE) for Namasthetu. "
            "Write a concise, professional valuation summary under 550 characters. "
            "Highlight the predicted price band, market alignment, physical condition impact, "
            "and legal title status."
        )

        user_content = (
            f"Property: {property_title} in {locality}, {city}\n"
            f"AVM Estimate: INR {est_cr} Cr (Band: {low_cr} - {high_cr} Cr)\n"
            f"Market Position: {market_position.value} ({difference_pct}% difference)\n"
            f"Demand Signal: {demand_signal.value}\n"
            f"Physical Condition Score: {features.condition_score_overall}/100\n"
            f"Seepage Detected: {'Yes' if features.seepage_detected else 'No'}\n"
            f"Legal Risk Score: {risk_scores.legal}/100\n"
            f"Verified Comparables: {comparables_count}\n"
        )

        resp = self._client.messages.create(
            model=self.model,
            max_tokens=250,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        return resp.content[0].text.strip()

    def _generate_contextual_fallback(
        self,
        property_title: str,
        locality: str,
        city: str,
        estimate_paise: int,
        market_position: MarketPosition,
        difference_pct: Optional[float],
        demand_signal: DemandSignal,
        risk_scores: InvestmentRiskScores,
        features: VieFeatureVector,
        comparables_count: int,
    ) -> str:
        """
        Deterministic, context-rich narrative generator conforming to the 600-char budget.
        """
        est_cr = round((estimate_paise / 100.0) / 10000000.0, 2)
        est_lakh = round((estimate_paise / 100.0) / 100000.0, 2)
        price_str = f"INR {est_cr} Cr" if est_cr >= 1.0 else f"INR {est_lakh} L"

        pos_str = "aligned with current market transactions"
        if market_position == MarketPosition.BELOW_MARKET and difference_pct is not None:
            pos_str = f"listed {abs(difference_pct):.1f}% below fair market value"
        elif market_position == MarketPosition.ABOVE_MARKET and difference_pct is not None:
            pos_str = f"commanding a {difference_pct:.1f}% premium over benchmark"

        condition_str = f"physical condition rated {features.condition_score_overall:.0f}/100"
        if features.seepage_detected == 1:
            condition_str += " with dampness remediation factored"

        legal_str = "clear verified ownership title"
        if risk_scores.legal > 40:
            legal_str = "elevated title/encumbrance flags noted"

        narrative = (
            f"Automated valuation estimates fair market value at {price_str} based on {comparables_count} "
            f"verified comparable transactions in {locality}. The property is {pos_str} with {demand_signal.value.lower()} "
            f"neighborhood demand. Features include {condition_str} and {legal_str} (overall risk score: {risk_scores.overall}/100)."
        )

        return narrative

    @staticmethod
    def _compute_cache_key(**kwargs) -> str:
        """Deterministic MD5 cache key generator."""
        payload = json.dumps(kwargs, sort_keys=True)
        return hashlib.md5(payload.encode("utf-8")).hexdigest()

    def clear_cache(self):
        """Clears in-memory narrative cache."""
        self._cache.clear()


narrative_engine = NarrativeEngine()
