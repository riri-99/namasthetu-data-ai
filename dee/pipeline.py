"""
DEE Pipeline Orchestrator (Document Extraction Engine)
Spec Reference: HYC-SCO-2026-3841 (§12.1–§12.4, §03.M02, §07.5)
Coordinates:
  1. Document ingestion and OCR preprocessing.
  2. PII masking and AI Gateway entity extraction.
  3. Confidence calculation & manual ops review routing (Threshold: 0.85).
  4. Real-time SSE status streaming events.
  5. Downstream DeedHistoryEvent timeline construction.
"""

from __future__ import annotations
import os
import time
import uuid
from typing import Dict, Any, Optional, List, Callable
from dee.models import (
    DocumentType,
    DocumentStatus,
    ExtractedEntitiesJson,
    DeeExtractionResult,
    DeePipelineEvent,
    DeePipelineStage,
    FieldConfidenceBreakdown,
    DeeSqsMessagePayload,
)
from dee.ocr import DeeOcrProcessor, dee_ocr
from dee.gateway import AiGatewayClient, dee_gateway
from dee.prompts import get_prompt_for_document_type
from dee.ownership_chain import OwnershipChainBuilder, ownership_chain_builder
from dee.learning_loop import dee_learning_collector


DEFAULT_CONFIDENCE_THRESHOLD = float(os.environ.get("DEE_CONFIDENCE_THRESHOLD", "0.85"))


class DeePipeline:
    """
    End-to-end Document Extraction Engine Pipeline.
    """

    def __init__(
        self,
        ocr_processor: Optional[DeeOcrProcessor] = None,
        gateway_client: Optional[AiGatewayClient] = None,
        chain_builder: Optional[OwnershipChainBuilder] = None,
        confidence_threshold: Optional[float] = None,
    ):
        self.ocr = ocr_processor or dee_ocr
        self.gateway = gateway_client or dee_gateway
        self.chain_builder = chain_builder or ownership_chain_builder
        self.threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else float(os.environ.get("DEE_CONFIDENCE_THRESHOLD", "0.85"))
        )
        self.event_subscribers: List[Callable[[DeePipelineEvent], None]] = []
        # In-memory event buffer for SSE `last-event-id` auto-reconnect (§11.3 & Phase 4)
        self.event_history: Dict[str, List[DeePipelineEvent]] = {}

    def subscribe_events(self, callback: Callable[[DeePipelineEvent], None]):
        """Subscribes an event listener (for SSE status streaming)."""
        self.event_subscribers.append(callback)

    def _emit_event(
        self,
        stage: DeePipelineStage,
        document_id: str,
        property_id: str,
        progress: int,
        message: str,
        confidence: Optional[float] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        event = DeePipelineEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            stage=stage,
            document_id=document_id,
            property_id=property_id,
            progress_percentage=progress,
            message=message,
            confidence=confidence,
            data=data,
        )
        # Store in event history for SSE last-event-id replay
        self.event_history.setdefault(document_id, []).append(event)

        for sub in self.event_subscribers:
            try:
                sub(event)
            except Exception:
                pass

    def get_events_since(
        self, document_id: str, last_event_id: Optional[str] = None
    ) -> List[DeePipelineEvent]:
        """
        Retrieves all pipeline events emitted for a document strictly after `last_event_id`.
        Implements SSE auto-reconnect support (§11.3 & DEE Plan Phase 4).
        """
        history = self.event_history.get(document_id, [])
        if not last_event_id:
            return list(history)

        idx = -1
        for i, ev in enumerate(history):
            if ev.event_id == last_event_id:
                idx = i
                break

        if idx == -1:
            # Reconnect id not found in current window; replay all events
            return list(history)

        return list(history[idx + 1:])

    def get_sse_chunks_since(
        self, document_id: str, last_event_id: Optional[str] = None
    ) -> List[str]:
        """Returns SSE wire-format message chunks for events since `last_event_id`."""
        events = self.get_events_since(document_id, last_event_id)
        return [e.to_sse_message() for e in events]


    def process_document(
        self,
        file_input: str | bytes,
        document_type: DocumentType,
        document_id: str,
        property_id: str,
        mime_type: str = "application/pdf",
    ) -> DeeExtractionResult:
        """
        Synchronous / blocking execution of the DEE pipeline.
        """
        start_time = time.perf_counter()

        # Step 1: Queued & Ingesting
        self._emit_event(
            DeePipelineStage.QUEUED,
            document_id,
            property_id,
            10,
            f"Document queued for DEE extraction: {document_type.value}",
        )

        self._emit_event(
            DeePipelineStage.OCR_IN_PROGRESS,
            document_id,
            property_id,
            25,
            "Running optical character recognition and document image normalization...",
        )

        # Step 2: OCR Extraction
        ocr_result = self.ocr.process_document(file_input, mime_type=mime_type)
        ocr_text = ocr_result["text"]
        ocr_conf = ocr_result["ocr_confidence"]

        self._emit_event(
            DeePipelineStage.OCR_COMPLETED,
            document_id,
            property_id,
            50,
            f"OCR completed ({ocr_result['page_count']} pages, conf: {ocr_conf * 100:.1f}%)",
            confidence=ocr_conf,
        )

        # Step 3: Entity Extraction via AI Gateway
        self._emit_event(
            DeePipelineStage.EXTRACTION_IN_PROGRESS,
            document_id,
            property_id,
            65,
            "Analyzing legal clauses, title conveyance, and encumbrances via Claude...",
        )

        system_prompt, user_template = get_prompt_for_document_type(document_type)
        extracted_raw = self.gateway.extract_structured_entities(
            ocr_text=ocr_text,
            system_prompt=system_prompt,
            user_prompt=user_template,
            document_type=document_type.value,
            ocr_confidence=ocr_conf,
        )

        # Step 4: Validate and construct ExtractedEntitiesJson
        extracted_raw["document_type"] = document_type.value
        extracted_raw["property_id"] = property_id
        extracted_raw["document_id"] = document_id
        
        # Inject OCR confidence into breakdown
        if "field_confidence" not in extracted_raw:
            extracted_raw["field_confidence"] = {}
        extracted_raw["field_confidence"]["ocr_quality"] = ocr_conf

        # Calculate composite confidence score dynamically based on document type
        field_confs = extracted_raw.get("field_confidence", {})
        if document_type == DocumentType.ENCUMBRANCE_CERTIFICATE:
            core_fields = ["owner", "survey_no", "dates", "encumbrances"]
        elif document_type == DocumentType.KHATA_CERTIFICATE:
            core_fields = ["owner", "survey_no", "dates"]
        else:
            core_fields = ["owner", "survey_no", "area", "dates", "encumbrances"]

        scores = [float(field_confs.get(k, 0.0)) for k in core_fields]
        scores.append(ocr_conf)
        composite_confidence = round(sum(scores) / len(scores), 3)

        # Step 5: Confidence Threshold Routing (Threshold = 0.85 default, configurable)
        requires_manual_review = composite_confidence < self.threshold
        final_status = DocumentStatus.REVIEWING if requires_manual_review else DocumentStatus.EXTRACTED

        if requires_manual_review:
            if not extracted_raw.get("suggested_resolution"):
                reasons = []
                if ocr_conf < 0.60:
                    reasons.append("Scan quality degraded or photo too dark (< 60% OCR readability); re-scan recommended")
                if not extracted_raw.get("survey_number", {}).get("survey_no"):
                    reasons.append("Survey number missing or ambiguous in schedule property")
                if ocr_result.get("is_regional_script"):
                    script = ocr_result.get("detected_script", "regional")
                    reasons.append(f"Regional script detected ({script}); route to specialized ops reviewer per O-07 mitigation")
                low_fields = [k for k, v in field_confs.items() if v < self.threshold and k in core_fields]
                if low_fields:
                    reasons.append(f"Low certainty on fields: {', '.join(low_fields)}")
                
                if not reasons:
                    reasons.append("Composite certainty below auto-approval threshold")

                extracted_raw["suggested_resolution"] = (
                    f"Manual ops triage required (Score: {composite_confidence * 100:.1f}%, Target: approval threshold ({self.threshold * 100:.0f}%)): "
                    + "; ".join(reasons) + "."
                )


        else:
            extracted_raw["suggested_resolution"] = None

        entities_payload = ExtractedEntitiesJson(**extracted_raw)
        ai_summary = extracted_raw.get("ai_summary_plain_english")
        if not ai_summary:
            ai_summary = (
                f"Paragraph 1: Legal instrument identified as {document_type.value.replace('_', ' ').title()} for property {property_id}.\n\n"
                f"Paragraph 2: Processing completed with composite confidence of {composite_confidence * 100:.1f}%.\n\n"
                f"Paragraph 3: Operational assessment: {'Approved for automated pipeline' if not requires_manual_review else 'Flagged for operational review queue'}."
            )

        # Step 6: Build DeedHistoryEvent Timeline Payloads
        timeline_events = self.chain_builder.build_events_from_extraction(
            entities_payload,
            legal_document_id=document_id,
            confidence=composite_confidence,
        )

        # Step 7: Emit Completion Event
        if requires_manual_review:
            self._emit_event(
                DeePipelineStage.ROUTED_TO_MANUAL_OPS,
                document_id,
                property_id,
                100,
                f"Flagged for manual ops triage: {entities_payload.suggested_resolution}",
                confidence=composite_confidence,
            )
        else:
            self._emit_event(
                DeePipelineStage.COMPLETED,
                document_id,
                property_id,
                100,
                f"Document successfully extracted and auto-approved (Confidence: {composite_confidence * 100:.1f}%)",
                confidence=composite_confidence,
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        ocr_engine_name = ocr_result.get("ocr_engine") or getattr(self.ocr, "engine_name", "Dynamic Normalized OCR")
        llm_model_name = getattr(self.gateway, "model_name", "Claude 3.5 Sonnet")

        result = DeeExtractionResult(
            document_id=document_id,
            property_id=property_id,
            document_type=document_type,
            status=final_status,
            aiExtractedDataJson=entities_payload,
            aiConfidenceScore=composite_confidence,
            aiSummaryPlainEnglish=ai_summary,
            requiresManualReview=requires_manual_review,
            deedHistoryEvents=timeline_events,
            processing_time_ms=round(elapsed_ms, 2),
            ocr_engine_used=ocr_engine_name,
            llm_model_used=llm_model_name,
        )

        # Step 8: Feed Continuous Learning Loop (§12.3 & DEE Plan Phase 5)
        try:
            dee_learning_collector.emit_extraction(result=result, masked_ocr_text=ocr_text)
        except Exception:
            pass

        return result

    def process_sqs_message(
        self,
        sqs_payload: DeeSqsMessagePayload | Dict[str, Any] | str,
    ) -> DeeExtractionResult:
        """
        Ingests document from S3 and triggers extraction based on SQS message.
        Spec Reference: DEE Plan Phase 0 / Phase 1 / Architecture (§2).
        """
        import json
        if isinstance(sqs_payload, str):
            payload_dict = json.loads(sqs_payload)
            sqs_msg = DeeSqsMessagePayload(**payload_dict)
        elif isinstance(sqs_payload, dict):
            sqs_msg = DeeSqsMessagePayload(**sqs_payload)
        elif isinstance(sqs_payload, DeeSqsMessagePayload):
            sqs_msg = sqs_payload
        else:
            raise ValueError(f"Invalid SQS payload type: {type(sqs_payload)}")

        # Ingest document bytes directly from S3 (or fallback)
        file_bytes = self.ocr.ingest_from_s3(sqs_msg.s3_bucket, sqs_msg.s3_key)

        doc_id = sqs_msg.document_id or sqs_msg.version_id
        return self.process_document(
            file_input=file_bytes,
            document_type=sqs_msg.document_type,
            document_id=doc_id,
            property_id=sqs_msg.property_id,
            mime_type=sqs_msg.mime_type,
        )

    async def process_document_async(
        self,
        file_input: str | bytes,
        document_type: DocumentType,
        document_id: str,
        property_id: str,
        mime_type: str = "application/pdf",
    ) -> DeeExtractionResult:
        """Asynchronous execution wrapper for FastAPI worker loops."""
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self.process_document,
            file_input,
            document_type,
            document_id,
            property_id,
            mime_type,
        )



dee_pipeline = DeePipeline()
