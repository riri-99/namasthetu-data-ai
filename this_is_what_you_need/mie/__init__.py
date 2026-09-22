"""
Market Intelligence Engine (MIE) — Embedded AI Service #5.

Namasthetu Platform · Launch Scope HYC-SCO-2026-3841
Prisma Alignment: Strictly compliant with src/db/schema.prisma (models MarketRate, Locality, NeighbourhoodIntelligence)
"""

from this_is_what_you_need.mie.pipeline import (
    MarketScope,
    MarketMetric,
    MarketPeriod,
    ListingMode,
    AreaBasis,
    DemandSignal,
    PriceTrendDirection,
    RawTransactionRecord,
    RawListingRecord,
    RawInquiryRecord,
    CivicProximityRecord,
    MarketRateRecord,
    MarketIntelligenceUpdatedEvent,
    MieAnalysisResult,
    InquiryDensityAnalyzer,
    TransactionVelocityAnalyzer,
    NeighbourhoodGrowthAnalyzer,
    MarketRiskAnalyzer,
    LocalityRanker,
    MiePipeline,
    mie_pipeline,
)

__all__ = [
    "MarketScope",
    "MarketMetric",
    "MarketPeriod",
    "ListingMode",
    "AreaBasis",
    "DemandSignal",
    "PriceTrendDirection",
    "RawTransactionRecord",
    "RawListingRecord",
    "RawInquiryRecord",
    "CivicProximityRecord",
    "MarketRateRecord",
    "MarketIntelligenceUpdatedEvent",
    "MieAnalysisResult",
    "InquiryDensityAnalyzer",
    "TransactionVelocityAnalyzer",
    "NeighbourhoodGrowthAnalyzer",
    "MarketRiskAnalyzer",
    "LocalityRanker",
    "MiePipeline",
    "mie_pipeline",
]
