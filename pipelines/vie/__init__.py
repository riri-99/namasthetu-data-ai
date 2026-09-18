"""
VIE (Valuation Intelligence Engine) / AVM (Automated Valuation Model) Package.

Namasthetu · Embedded AI Service #3
"""

from vie.models import (
    AvmValuationPrediction,
    ComparableSale,
    DemandSignal,
    InvestmentRiskScores,
    MarketPosition,
    MonthlyForecastPoint,
    PrismaFurnishingStatus,
    PrismaPropertyType,
    ValuationFeedback,
    ValuationPublishedEvent,
    VieFeatureVector,
    VieFeedbackMetrics,
    VieTriggerEvent,
    VieTriggerType,
    VieValuationResult,
)
from vie.avm_engine import AvmCoreEngine, avm_core_engine
from vie.comparables_engine import ComparablesEngine, comparables_engine
from vie.narrative_engine import NarrativeEngine, narrative_engine
from vie.risk_and_yield_calculator import RiskAndYieldCalculator
from vie.feedback_loop import VieLearningLoop, vie_learning_loop
from vie.dataset_manager import VieDatasetManager, vie_dataset_manager
from vie.pipeline import ViePipeline, vie_pipeline

__all__ = [
    # Pipeline & Singletons
    "vie_pipeline",
    "ViePipeline",
    "avm_core_engine",
    "AvmCoreEngine",
    "comparables_engine",
    "ComparablesEngine",
    "narrative_engine",
    "NarrativeEngine",
    "RiskAndYieldCalculator",
    "vie_learning_loop",
    "VieLearningLoop",
    "vie_dataset_manager",
    "VieDatasetManager",
    # Enums
    "MarketPosition",
    "DemandSignal",
    "VieTriggerType",
    "PrismaPropertyType",
    "PrismaFurnishingStatus",
    # Domain Models & Results
    "VieFeatureVector",
    "AvmValuationPrediction",
    "ComparableSale",
    "MonthlyForecastPoint",
    "InvestmentRiskScores",
    "VieValuationResult",
    "ValuationPublishedEvent",
    "VieTriggerEvent",
    "ValuationFeedback",
    "VieFeedbackMetrics",
]
