"""
Document Extraction Engine (DEE) — Namasthetu Property Intelligence Operating System
Spec Reference: HYC-SCO-2026-3841 (§12.1–§12.4, §03.M02, §07.5)
Adheres strictly to `src/db/schema.prisma` without modifying the database schema.
"""

from pipelines.dee.models import (
    DocumentType,
    DocumentStatus,
    DeedEventType,
    DeedEventStatus,
    ExtractedOwner,
    ExtractedSurveyNumber,
    ExtractedArea,
    ExtractedDateEntry,
    ExtractedEncumbranceEntry,
    FieldConfidenceBreakdown,
    ExtractedEntitiesJson,
    DeeExtractionResult,
    DeedHistoryEventPayload,
    DeePipelineEvent,
    DeePipelineStage,
)
from pipelines.dee.pipeline import DeePipeline, dee_pipeline
from pipelines.dee.ocr import DeeOcrProcessor, dee_ocr
from pipelines.dee.gateway import AiGatewayClient, dee_gateway

__version__ = "1.0.0"
__all__ = [
    "DocumentType",
    "DocumentStatus",
    "DeedEventType",
    "DeedEventStatus",
    "ExtractedOwner",
    "ExtractedSurveyNumber",
    "ExtractedArea",
    "ExtractedDateEntry",
    "ExtractedEncumbranceEntry",
    "FieldConfidenceBreakdown",
    "ExtractedEntitiesJson",
    "DeeExtractionResult",
    "DeedHistoryEventPayload",
    "DeePipelineEvent",
    "DeePipelineStage",
    "DeePipeline",
    "dee_pipeline",
    "DeeOcrProcessor",
    "dee_ocr",
    "AiGatewayClient",
    "dee_gateway",
]
