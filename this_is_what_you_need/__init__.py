"""
Namasthetu Unified Embedded AI Platform.

Exposes all four embedded AI pipelines as singletons:
1. pam_pipeline (Photo Analysis Module)
2. dee_pipeline (Document Extraction Engine)
3. vie_pipeline (Valuation Intelligence Engine)
4. sse_pipeline (Semantic Search Engine)
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
)

from this_is_what_you_need.pam.pipeline import PamPipeline, pam_pipeline
from this_is_what_you_need.dee.pipeline import DeePipeline, dee_pipeline
from this_is_what_you_need.vie.pipeline import ViePipeline, vie_pipeline
from this_is_what_you_need.sse.pipeline import SsePipeline, sse_pipeline

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
    # Common Infrastructure
    "ai_gateway",
    "AiGatewayClient",
    "mask_pii",
    "BaseDatasetSplitter",
    "BaseEventDispatcher",
    "haversine_distance_meters",
    "haversine_distance_km",
    # Shared Enums
    "PrismaPropertyType",
    "PrismaFurnishingStatus",
    "PrismaListingStatus",
]
