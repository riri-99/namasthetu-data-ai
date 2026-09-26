"""
Namasthetu Unified Embedded AI Platform.

Exposes all embedded AI pipelines as singletons:
Exposes all five embedded AI pipelines as singletons:
1. pam_pipeline (Photo Analysis Module)
2. dee_pipeline (Document Extraction Engine)
3. vie_pipeline (Valuation Intelligence Engine)
4. sse_pipeline (Semantic Search Engine)
5. lqa_pipeline (Listing Quality Auditor)
5. mie_pipeline (Market Intelligence Engine)
"""

from this_is_what_you_need.common import (
    AiGatewayClient,
    ai_gateway,
    mask_pii,
    BaseDatasetSplitter,
    BaseEventDispatcher,
    haversine_distance_meters,
    haversine_distance_km,
    PrismaPropertyType,
    PrismaFurnishingStatus,
    PrismaListingStatus,
    PrismaLqaStatus,
    PrismaLqaStatus,
)

from this_is_what_you_need.pam.pipeline import PamPipeline, pam_pipeline
from this_is_what_you_need.dee.pipeline import DeePipeline, dee_pipeline
from this_is_what_you_need.vie.pipeline import ViePipeline, vie_pipeline
from this_is_what_you_need.sse.pipeline import SsePipeline, sse_pipeline
from this_is_what_you_need.lqa.pipeline import LqaPipeline, lqa_pipeline, LqaStatus, LqaAuditResult, ListingDraftInput
from this_is_what_you_need.mie.pipeline import (
    MiePipeline,
    mie_pipeline,
    MarketScope,
    MarketMetric,
    MarketPeriod,
    DemandSignal,
)

__all__ = [
    # Pipelines
    "pam_pipeline",
    "PamPipeline",
    "dee_pipeline",
    "DeePipeline",
    "vie_pipeline",
    "ViePipeline",
    "sse_pipeline",
    "SsePipeline",
    "lqa_pipeline",
    "LqaPipeline",
    "mie_pipeline",
    "MiePipeline",
    # MIE Domain Enums
    "MarketScope",
    "MarketMetric",
    "MarketPeriod",
    "DemandSignal",
    # Common Infrastructure
    "ai_gateway",
    "AiGatewayClient",
    "mask_pii",
    "BaseDatasetSplitter",
    "BaseEventDispatcher",
    "haversine_distance_meters",
    "haversine_distance_km",
    # Shared Enums & Models
    # Shared Enums & Models
    "PrismaPropertyType",
    "PrismaFurnishingStatus",
    "PrismaListingStatus",
    "PrismaLqaStatus",
    "LqaStatus",
    "LqaAuditResult",
    "ListingDraftInput",
    "PrismaLqaStatus",
    "LqaStatus",
    "LqaAuditResult",
    "ListingDraftInput",
]
