"""
VIE (Valuation Intelligence Engine) — Core Pipeline Orchestrator.

Orchestrates:
1. Input Assembly: Property physical + address + PAM condition scores + DEE legal title + MIE demand signals
2. Core AVM Valuation: LightGBM / compiled Treelite inference (<60ms P95 latency)
3. Comparables Engine: Radius retrieval & similarity scoring with consent.comparable_inclusion enforcement
4. Risk & Rental Yield: Gross yield, 12-month forward forecast, 5-yr appreciation, composite risk breakdown
5. Narrative Overlay: Claude API via AI Gateway pattern (max 600 chars, response cached)
6. 1:1 Schema Formatting:
   - model AiValuation (src/db/schema.prisma lines 1166-1205)
   - model PriceForecast (src/db/schema.prisma lines 1655-1668)
   - PIP ai_insights.valuation object (HYC-SCO-2026-3841 §12)
7. Event Ingestion & Bus: Triggers on PropertyRegistered, PriceUpdated, InspectionCompleted, TransactionCompleted
8. Public API: Address-to-value endpoint
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from vie.avm_engine import AvmCoreEngine, avm_core_engine
from vie.comparables_engine import ComparablesEngine, comparables_engine
from vie.narrative_engine import NarrativeEngine, narrative_engine
from vie.risk_and_yield_calculator import RiskAndYieldCalculator
from vie.models import (
    ComparableSale,
    DemandSignal,
    InvestmentRiskScores,
    MarketPosition,
    PrismaFurnishingStatus,
    ValuationPublishedEvent,
    VieFeatureVector,
    VieTriggerEvent,
    VieTriggerType,
    VieValuationResult,
)


class ViePipeline:
    """End-to-end Valuation Intelligence Engine Orchestrator."""

    def __init__(
        self,
        avm_engine_instance: Optional[AvmCoreEngine] = None,
        comparables_engine_instance: Optional[ComparablesEngine] = None,
        narrative_engine_instance: Optional[NarrativeEngine] = None,
    ):
        self.avm = avm_engine_instance or avm_core_engine
        self.comps = comparables_engine_instance or comparables_engine
        self.narrative = narrative_engine_instance or narrative_engine
        self.event_subscribers: List[Callable[[ValuationPublishedEvent], None]] = []

    def subscribe_events(self, callback: Callable[[ValuationPublishedEvent], None]):
        """Subscribes an event listener to the ValuationPublished stream."""
        self.event_subscribers.append(callback)

    def _emit_published_event(self, result: VieValuationResult) -> ValuationPublishedEvent:
        """Publishes ValuationPublished event to internal event bus."""
        event = ValuationPublishedEvent(
            event_id=f"evt_val_{uuid.uuid4().hex[:12]}",
            property_id=result.property_id,
            valuation_id=result.id,
            estimate_paise=result.estimate_minor,
            confidence_interval_low_paise=result.confidence_low_minor,
            confidence_interval_high_paise=result.confidence_high_minor,
            market_position=result.market_position.value,
            demand_signal=result.demand_signal.value,
            model_version=result.model_version,
            timestamp=datetime.now(timezone.utc),
        )
        for sub in self.event_subscribers:
            try:
                sub(event)
            except Exception:
                pass
        return event

    def valuate_property(
        self,
        property_id: str,
        property_title: str,
        locality: str,
        city: str,
        area_sqft: float,
        bhk_count: int,
        bathrooms_count: int = 2,
        floor_number: int = 1,
        total_floors: int = 1,
        furnishing: Union[str, PrismaFurnishingStatus] = PrismaFurnishingStatus.SEMI_FURNISHED,
        age_years: float = 0.0,
        listed_price_paise: Optional[int] = None,
        coordinates: Optional[Tuple[float, float]] = None,
        # Cross-Pipeline PAM Inputs (Inspection Service)
        pam_condition_score: Optional[float] = None,
        pam_seepage_detected: Optional[bool] = None,
        # Cross-Pipeline DEE Inputs (Legal Document Engine)
        dee_legal_encumbrance_flag: Optional[bool] = None,
        dee_title_confidence: Optional[float] = None,
        # MIE Market Signals
        mie_inquiry_density: Optional[float] = None,
        mie_transaction_velocity: Optional[float] = None,
        mie_neighbourhood_growth: Optional[float] = None,
        locality_base_rate_inr: Optional[float] = None,
    ) -> VieValuationResult:
        """
        Executes end-to-end property valuation.
        """
        pipeline_start = time.perf_counter()
        norm_loc = locality.strip().lower().replace(" ", "_").replace("-", "_")

        # 1. Resolve Micro-Market Base Rate
        base_rate = locality_base_rate_inr
        if not base_rate:
            meta = self.comps.TIER1_MICROMARKETS.get(norm_loc)
            base_rate = meta["base_rate_inr"] if meta else 9500.0

        # 2. Encode Furnishing Status
        furn_val = furnishing.value if isinstance(furnishing, PrismaFurnishingStatus) else str(furnishing)
        furn_encoded = 1
        if "unfurnished" in furn_val.lower():
            furn_encoded = 0
        elif "fully" in furn_val.lower():
            furn_encoded = 2

        # 3. Assemble 13-Feature Vector (HYC-SCO-2026-3841 §12)
        condition_val = pam_condition_score if pam_condition_score is not None else 85.0
        seepage_val = 1 if pam_seepage_detected is True else 0

        features = VieFeatureVector(
            area_sqft=area_sqft,
            age_years=age_years,
            floor_number=floor_number,
            total_floors=total_floors,
            bhk_count=bhk_count,
            bathrooms_count=bathrooms_count,
            furnishing_status=furn_encoded,
            condition_score_overall=condition_val,
            seepage_detected=seepage_val,
            locality_price_per_sqft_base=base_rate,
            inquiry_density_score=mie_inquiry_density if mie_inquiry_density is not None else 55.0,
            transaction_velocity_score=mie_transaction_velocity if mie_transaction_velocity is not None else 50.0,
            neighbourhood_growth_score=mie_neighbourhood_growth if mie_neighbourhood_growth is not None else 65.0,
        )

        # 4. Core LightGBM Valuation (<60ms P95 latency)
        avm_pred = self.avm.predict(features)
        estimate_paise = avm_pred.estimate_paise
        ci_low_paise = avm_pred.confidence_low_paise
        ci_high_paise = avm_pred.confidence_high_paise

        # 5. Comparables Engine (respecting consent.comparable_inclusion)
        comparables = self.comps.find_comparables(
            property_id=property_id,
            locality=locality,
            city=city,
            area_sqft=area_sqft,
            bhk_count=bhk_count,
            age_years=age_years,
            coordinates=coordinates,
            max_results=6,
        )

        # 6. Risk, Yield, and 12-Month Forecast
        market_pos, diff_pct = RiskAndYieldCalculator.evaluate_market_position(
            estimate_paise=estimate_paise,
            listed_price_paise=listed_price_paise,
        )
        demand_sig = RiskAndYieldCalculator.evaluate_demand_signal(features)
        gross_yield_pct, monthly_rent_paise = RiskAndYieldCalculator.compute_rental_yield(
            estimate_paise=estimate_paise,
            locality=locality,
            features=features,
        )
        forecast_12m = RiskAndYieldCalculator.generate_12m_forecast(
            estimate_paise=estimate_paise,
            features=features,
        )
        apprec_5yr, apprec_driver = RiskAndYieldCalculator.compute_5yr_appreciation(
            locality=locality,
            features=features,
        )
        risk_scores = RiskAndYieldCalculator.compute_investment_risk(
            features=features,
            dee_legal_encumbrance_flag=dee_legal_encumbrance_flag,
            dee_title_confidence=dee_title_confidence,
            asking_price_paise=listed_price_paise,
            estimate_paise=estimate_paise,
        )

        # 7. Narrative Overlay (Claude via AI Gateway)
        narrative, narrative_latency = self.narrative.generate_narrative(
            property_title=property_title,
            locality=locality,
            city=city,
            estimate_paise=estimate_paise,
            confidence_low_paise=ci_low_paise,
            confidence_high_paise=ci_high_paise,
            market_position=market_pos,
            difference_pct=diff_pct,
            demand_signal=demand_sig,
            risk_scores=risk_scores,
            features=features,
            comparables_count=len(comparables),
        )

        total_latency = round((time.perf_counter() - pipeline_start) * 1000.0, 2)

        # 8. Create Valuation Result (1:1 with Prisma AiValuation & PriceForecast)
        result = VieValuationResult(
            id=f"val_{uuid.uuid4().hex[:12]}",
            property_id=property_id,
            model_version=avm_pred.model_version,
            estimate_minor=estimate_paise,
            confidence_low_minor=ci_low_paise,
            confidence_high_minor=ci_high_paise,
            market_position=market_pos,
            demand_signal=demand_sig,
            risk_scores=risk_scores,
            comparables=comparables,
            narrative_summary=narrative,
            listed_price_minor=listed_price_paise,
            difference_percentage=diff_pct,
            gross_yield_percentage=gross_yield_pct,
            monthly_rental_estimate_minor=monthly_rent_paise,
            projected_5yr_appreciation_pct=apprec_5yr,
            appreciation_driver=apprec_driver,
            historical_transactions_count=len(comparables),
            forecast_12m=forecast_12m,
            feature_vector=features,
            core_inference_latency_ms=avm_pred.inference_latency_ms,
            narrative_latency_ms=narrative_latency,
            total_pipeline_latency_ms=total_latency,
        )

        # Publish Event
        self._emit_published_event(result)

        return result

    def address_to_value(
        self,
        locality: str,
        city: str,
        area_sqft: float,
        bhk_count: int,
        furnishing: str = "SEMI_FURNISHED",
        age_years: float = 0.0,
    ) -> VieValuationResult:
        """
        Public Address-to-value API (§12.1 feature table).
        Enables public consumer instantaneous valuation before property onboarding.
        """
        temp_prop_id = f"pub_query_{uuid.uuid4().hex[:8]}"
        title = f"{bhk_count} BHK Residence, {locality.title()}"
        return self.valuate_property(
            property_id=temp_prop_id,
            property_title=title,
            locality=locality,
            city=city,
            area_sqft=area_sqft,
            bhk_count=bhk_count,
            furnishing=furnishing,
            age_years=age_years,
        )

    def process_trigger_event(self, trigger: VieTriggerEvent) -> Optional[VieValuationResult]:
        """
        Processes asynchronous trigger events from system message bus (§2).
        
        Triggers:
        - PROPERTY_REGISTERED: New property onboarding
        - PRICE_UPDATED: Asking price revised by owner
        - INSPECTION_COMPLETED: Inspection condition & seepage data now available from PAM
        - TRANSACTION_COMPLETED: New closed deal becomes fresh comparable
        """
        t_type = trigger.trigger_type
        payload = trigger.payload
        prop_id = trigger.property_id

        if t_type == VieTriggerType.TRANSACTION_COMPLETED:
            # Add transaction to comparables pool
            comp = ComparableSale(
                property_id=prop_id,
                title=payload.get("title", f"Sale at {payload.get('locality', 'Bengaluru')}"),
                locality=payload.get("locality", "Whitefield"),
                city=payload.get("city", "Bengaluru"),
                sale_price_paise=payload.get("sale_price_paise", 1000000000),
                area_sqft=payload.get("area_sqft", 1200.0),
                bhk_count=payload.get("bhk_count", 2),
                transacted_at=datetime.now(timezone.utc),
                similarity_score=1.0,
                distance_meters=payload.get("distance_meters", 300.0),
                consent_comparable_inclusion=payload.get("consent_comparable_inclusion", True),
            )
            self.comps.add_transaction(comp)
            return None

        # Valuation triggers: re-run valuation with updated features
        return self.valuate_property(
            property_id=prop_id,
            property_title=payload.get("title", "Property Valuation"),
            locality=payload.get("locality", "Whitefield"),
            city=payload.get("city", "Bengaluru"),
            area_sqft=payload.get("area_sqft", 1400.0),
            bhk_count=payload.get("bhk_count", 3),
            bathrooms_count=payload.get("bathrooms_count", 2),
            floor_number=payload.get("floor_number", 4),
            total_floors=payload.get("total_floors", 12),
            furnishing=payload.get("furnishing", "SEMI_FURNISHED"),
            age_years=payload.get("age_years", 2.0),
            listed_price_paise=payload.get("listed_price_paise"),
            pam_condition_score=payload.get("pam_condition_score"),
            pam_seepage_detected=payload.get("pam_seepage_detected"),
            dee_legal_encumbrance_flag=payload.get("dee_legal_encumbrance_flag"),
            dee_title_confidence=payload.get("dee_title_confidence"),
            mie_inquiry_density=payload.get("mie_inquiry_density"),
            mie_transaction_velocity=payload.get("mie_transaction_velocity"),
            mie_neighbourhood_growth=payload.get("mie_neighbourhood_growth"),
        )


vie_pipeline = ViePipeline()
