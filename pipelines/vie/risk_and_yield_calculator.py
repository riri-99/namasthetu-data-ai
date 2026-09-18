"""
VIE (Valuation Intelligence Engine) — Risk, Yield, and Forecast Calculator.

Implements:
- Gross rental yield & monthly rental estimate calculation (§3 & schema.prisma lines 1195-1196)
- 12-Month Price Forecast with 90% Confidence Interval bands (model PriceForecast lines 1650-1668)
- 5-Year appreciation projection & primary infrastructure driver (schema.prisma lines 1197-1198)
- Multi-axis investment risk score (Overall, Legal from DEE, Market, Climate, Mortgage LTV) (lines 1178-1182)
- Market position badge classification (BELOW_MARKET, ALIGNED, ABOVE_MARKET)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from vie.models import (
    DemandSignal,
    InvestmentRiskScores,
    MarketPosition,
    MonthlyForecastPoint,
    VieFeatureVector,
)


class RiskAndYieldCalculator:
    """
    Computes derived intelligence metrics: rental yields, risk decompositions, and price time-series forecasts.
    """

    MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Micro-market typical rental yield profiles (annual gross yield %)
    LOCALITY_YIELD_PROFILES: Dict[str, float] = {
        "indiranagar": 4.1,
        "whitefield": 4.8,
        "koramangala": 4.3,
        "hsr_layout": 4.6,
        "hebbal": 4.4,
        "bandra_west": 3.1,
        "powai": 3.8,
        "worli": 3.2,
        "andheri_west": 3.5,
        "golf_course_road": 4.0,
        "cyber_city": 4.5,
        "gachibowli": 5.2,
        "hitec_city": 5.0,
        "jubilee_hills": 3.6,
        "koregaon_park": 4.2,
        "baner": 4.5,
    }

    # Primary growth drivers per micro-market
    GROWTH_DRIVERS: Dict[str, str] = {
        "indiranagar": "Established retail luxury hub and central metro interchange",
        "whitefield": "Metro Purple Line operationalization & tech park expansion",
        "koramangala": "High-density startup ecosystem and limited new land supply",
        "hsr_layout": "Direct arterial link between Outer Ring Road and Electronics City",
        "hebbal": "Airport Expressway corridor and upcoming suburban rail hub",
        "bandra_west": "Coastal Road integration & prime coastal redevelopment",
        "powai": "IIT Bombay innovation corridor and JVLR connectivity",
        "worli": "Coastal Road entry node and ultra-luxury commercial headquarters",
        "andheri_west": "Metro Line 2A & 7 connectivity and commercial density",
        "golf_course_road": "Rapid Metro connectivity and multinational institutional tenancy",
        "cyber_city": "Direct transit connectivity and grade-A commercial leases",
        "gachibowli": "Financial District tech SEZ expansion and ORR connectivity",
        "hitec_city": "Core IT corridor transit hub with resilient corporate leasing",
        "jubilee_hills": "High-net-worth land value appreciation and low density",
        "koregaon_park": "Prime lifestyle quarter with resilient expatriate rental demand",
        "baner": "Balewadi High Street commercial expansion and Mumbai-Pune highway access",
    }

    @classmethod
    def compute_rental_yield(
        cls,
        estimate_paise: int,
        locality: str,
        features: VieFeatureVector,
    ) -> Tuple[float, int]:
        """
        Calculates gross rental yield percentage and monthly rental estimate in paise.
        
        Returns:
            (gross_yield_percentage, monthly_rental_estimate_minor)
        """
        norm_loc = locality.strip().lower().replace(" ", "_").replace("-", "_")
        base_yield = cls.LOCALITY_YIELD_PROFILES.get(norm_loc, 4.2)

        # Furnishing bonus for rentals (+0.3% yield for semi, +0.7% for fully furnished)
        furnishing_yield_bonus = features.furnishing_status * 0.35
        # Condition bonus (+0.2% if high condition score >= 90)
        condition_bonus = 0.2 if features.condition_score_overall >= 90 else (
            -0.3 if features.condition_score_overall < 70 else 0.0
        )

        effective_yield_pct = round(max(2.5, min(7.5, base_yield + furnishing_yield_bonus + condition_bonus)), 2)

        # Annual rent in paise
        annual_rent_paise = estimate_paise * (effective_yield_pct / 100.0)
        monthly_rent_paise = int(round(annual_rent_paise / 12.0))

        return effective_yield_pct, monthly_rent_paise

    @classmethod
    def generate_12m_forecast(
        cls,
        estimate_paise: int,
        features: VieFeatureVector,
        start_date: Optional[datetime] = None,
    ) -> List[MonthlyForecastPoint]:
        """
        Generates 12-month forward price forecast time series with 90% CI bands (§3 & model PriceForecast).
        """
        now = start_date or datetime.now(timezone.utc)
        current_month = now.month
        current_year = now.year

        # Annual projected growth rate derived from neighbourhood growth & demand
        annual_growth_rate = 0.05 + (features.neighbourhood_growth_score / 100.0) * 0.06
        monthly_rate = annual_growth_rate / 12.0

        forecast: List[MonthlyForecastPoint] = []
        for m in range(1, 13):
            # Target month name
            target_m_idx = (current_month - 1 + m) % 12
            target_year = current_year + ((current_month - 1 + m) // 12)
            m_name = f"{cls.MONTH_NAMES[target_m_idx]} {target_year}"

            # Trend projection
            projected_val = estimate_paise * ((1.0 + monthly_rate) ** m)
            projected_minor = int(round(projected_val))

            # 90% Confidence band widens over time (±5% at month 1 to ±10% at month 12)
            ci_spread = 0.05 + (0.05 * (m / 12.0))
            low_minor = int(round(projected_minor * (1.0 - ci_spread)))
            high_minor = int(round(projected_minor * (1.0 + ci_spread)))

            forecast.append(
                MonthlyForecastPoint(
                    month=m,
                    month_name=m_name,
                    estimate_minor=projected_minor,
                    low_minor=low_minor,
                    high_minor=high_minor,
                )
            )

        return forecast

    @classmethod
    def compute_5yr_appreciation(
        cls,
        locality: str,
        features: VieFeatureVector,
    ) -> Tuple[float, str]:
        """
        Computes 5-year projected capital appreciation percentage and primary driver.
        """
        norm_loc = locality.strip().lower().replace(" ", "_").replace("-", "_")
        driver = cls.GROWTH_DRIVERS.get(
            norm_loc,
            "Transit infrastructure enhancement and regional commercial development",
        )

        # Baseline 5-yr compounded appreciation: 35% to 55% for Tier-1 micro-markets
        base_5yr = 36.0 + (features.neighbourhood_growth_score * 0.20)
        if features.transaction_velocity_score > 70:
            base_5yr += 4.5

        return round(base_5yr, 1), driver

    @classmethod
    def compute_investment_risk(
        cls,
        features: VieFeatureVector,
        dee_legal_encumbrance_flag: Optional[bool] = None,
        dee_title_confidence: Optional[float] = None,
        climate_risk_override: Optional[int] = None,
        asking_price_paise: Optional[int] = None,
        estimate_paise: Optional[int] = None,
    ) -> InvestmentRiskScores:
        """
        Computes multi-axis investment risk breakdown (0 to 100, lower is better).
        Integrates legal title risk from DEE cross-pipeline (§4 & §6.5).
        """
        # 1. Legal Risk (from DEE / Title Verification)
        legal_risk = 10
        if dee_legal_encumbrance_flag is True:
            legal_risk = 75  # Active lien or dispute found by DEE
        elif dee_title_confidence is not None:
            # Low OCR/DEE confidence indicates ambiguous deed provenance
            legal_risk = max(10, int(round((1.0 - dee_title_confidence) * 60)))

        # 2. Market Risk (from MIE signals)
        # Low velocity or low inquiry density indicates liquidity risk
        market_risk = int(
            round(
                max(
                    5,
                    50 - (features.transaction_velocity_score * 0.3) - (features.inquiry_density_score * 0.2),
                )
            )
        )

        # 3. Climate & Physical Risk
        # Seepage from PAM and old age increase structural and climate risk
        climate_risk = climate_risk_override if climate_risk_override is not None else 15
        if features.seepage_detected == 1:
            climate_risk += 15
        if features.age_years > 20:
            climate_risk += 10
        climate_risk = min(100, climate_risk)

        # 4. Mortgage LTV Risk for Lenders (Lender Persona §4)
        mortgage_ltv = None
        if asking_price_paise and estimate_paise and estimate_paise > 0:
            # Standard 80% loan on asking price vs verified valuation
            mortgage_ltv = round((asking_price_paise * 0.80) / estimate_paise, 2)

        # Composite Overall Risk (Weighted: 35% Legal, 30% Market, 25% Climate, 10% Condition)
        condition_risk = int(round(100 - features.condition_score_overall))
        overall_risk = int(
            round(
                (legal_risk * 0.35)
                + (market_risk * 0.30)
                + (climate_risk * 0.25)
                + (condition_risk * 0.10)
            )
        )

        return InvestmentRiskScores(
            overall=min(100, max(0, overall_risk)),
            legal=min(100, max(0, legal_risk)),
            market=min(100, max(0, market_risk)),
            climate=min(100, max(0, climate_risk)),
            mortgage_ltv=mortgage_ltv,
        )

    @classmethod
    def evaluate_market_position(
        cls,
        estimate_paise: int,
        listed_price_paise: Optional[int],
    ) -> Tuple[MarketPosition, Optional[float]]:
        """
        Computes difference percentage: (listed - estimate) / estimate * 100.
        Classifies into BELOW_MARKET, ALIGNED, or ABOVE_MARKET.
        """
        if not listed_price_paise or estimate_paise <= 0:
            return MarketPosition.ALIGNED, None

        diff_pct = ((listed_price_paise - estimate_paise) / float(estimate_paise)) * 100.0
        diff_pct_rounded = round(diff_pct, 2)

        if diff_pct < -2.0:
            return MarketPosition.BELOW_MARKET, diff_pct_rounded
        elif diff_pct > 2.0:
            return MarketPosition.ABOVE_MARKET, diff_pct_rounded
        else:
            return MarketPosition.ALIGNED, diff_pct_rounded

    @classmethod
    def evaluate_demand_signal(cls, features: VieFeatureVector) -> DemandSignal:
        """Determines COLD, WARM, or HOT demand signal from MIE inquiry & velocity."""
        composite = (features.inquiry_density_score * 0.6) + (features.transaction_velocity_score * 0.4)
        if composite < 40.0:
            return DemandSignal.COLD
        elif composite > 70.0:
            return DemandSignal.HOT
        else:
            return DemandSignal.WARM
