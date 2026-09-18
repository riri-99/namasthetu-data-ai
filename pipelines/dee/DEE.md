# Document Extraction Engine (DEE)

**Namasthetu · Embedded AI Service #1 · Owner: AI/ML Track**  
**Spec Reference:** Namasthetu Scope v1.0 FINAL (§12.1–§12.4, §03.M02, §07.5, §16.2)  
**Implementation Plan:** [`DOCS/DEE_Implementation_Plan.md`](../DOCS/DEE_Implementation_Plan.md)  
**Database Schema Adherence:** Compliant with [`src/db/schema.prisma`](../src/db/schema.prisma).

---

## 1. Overview & Architectural Role

The **Document Extraction Engine (DEE)** is the foundational AI service powering **Identity & Ownership Verification (§03.M02)** and the **Property Intelligence Profile (PIP)**. It extracts structured, queryable legal entities from deeds and certificates:

- **Transacting Parties & Owners:** Full legal names, relationship identifiers (S/o, D/o, W/o), masked PAN, masked Aadhaar tokens.
- **Survey & Geo Boundaries:** Revenue survey numbers, hissa, katha/PID, flat/unit numbers, village, hobli, taluk, district, schedule boundaries (N/S/E/W).
- **Physical & Carpet Area:** Carpet area, super built-up area, plot area, and units.
- **Dates & SRO Registration:** Execution dates, registration dates, sub-registrar document number, book, volume, and SRO name.
- **Encumbrances & Liabilities:** Active bank mortgages, loan amounts, charge holders, release deeds, and discharge statuses.
- **3-Paragraph Plain English Summary:** Human-readable legal summary written to `LegalDocument.aiSummaryPlainEnglish`.
- **Downstream Title Chain Events:** Builds `DeedHistoryEvent` payloads directly to power the 3-transaction ownership timeline.

---

## 2. Database Schema Alignment (`src/db/schema.prisma`)

DEE strictly updates and populates the existing models in `src/db/schema.prisma` without modifying a single line of the schema:

### Model `LegalDocument` (Lines 997–1031)

| Column | Type | DEE Field Mapping |
| :--- | :--- | :--- |
| `status` | `DocumentStatus` | `EXTRACTED` (if confidence $\ge 0.85$) or `REVIEWING` (if confidence $< 0.85$). |
| `aiExtractedDataJson` | `Json?` | Full Pydantic `ExtractedEntitiesJson` payload containing owners, survey, area, dates, encumbrances, and suggested resolution. |
| `aiConfidenceScore` | `Float?` | Composite confidence score ($0.0 - 1.0$) balancing OCR quality and LLM field certainty. |
| `aiSummaryPlainEnglish` | `String?` | 3-paragraph plain-English summary of context, financials, and liabilities. |
| `requiresManualReview` | `Boolean` | Flag set to `true` when confidence $< 0.85$, routing document to the Ops triage queue. |

### Model `DeedHistoryEvent` (Lines 1827–1850)

DEE automatically compiles extracted deeds and Encumbrance Certificates into timeline events:
- `eventType`: `SALE`, `MORTGAGE_CREATED`, `MORTGAGE_RELEASED`, `GIFT`, `CONVEYANCE`, `KHATA_TRANSFER`.
- `status`: `VERIFIED` (if auto-approved) or `PENDING` (if routed to ops).
- `year` & `eventDate`: Extracted execution/registration year.
- `parties`: Formatted transacting parties (`"Vendor → Purchaser"` or `"Mortgagor ↔ Bank"`).
- `registrationVolume`: SRO Doc #, Book #, Volume #.

---

## 3. Core Architecture & Pipeline Components

```
Uploaded Document (PDF / Image)
            │
            ▼
┌───────────────────────────────────────┐
│         dee/ocr.py                    │
│   • Grayscale & contrast enhancement   │
│   • PyPDF / PyMuPDF / Tesseract       │
│   • Regional script detection (O-07)  │
└──────────────────┬────────────────────┘
                   │ ocr_text + ocr_confidence
                   ▼
┌───────────────────────────────────────┐
│         dee/gateway.py                │
│   • Mandatory PII masking (§12.4)     │
│     (Tokenizes Aadhaar & PAN)         │
│   • Claude 3.5 Sonnet / Mock gateway  │
│   • Response caching & cost tracking  │
└──────────────────┬────────────────────┘
                   │ structured JSON
                   ▼
┌───────────────────────────────────────┐
│         dee/pipeline.py               │
│   • Confidence threshold scoring      │
│   • ≥ 0.85: Auto-approved (EXTRACTED) │
│   • < 0.85: Ops queue (REVIEWING)     │
│   • Generates suggested resolution    │
│   • Dispatches real-time SSE events   │
└──────────────────┬────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│     dee/ownership_chain.py            │
│   • Compiles DeedHistoryEvent rows    │
│   • Feeds PIP 3-transaction timeline  │
└───────────────────────────────────────┘
```

---

## 4. Phased Implementation Status Matrix (Plan Alignment)

| Phase | Description | Status | Implementation Details |
| :--- | :--- | :---: | :--- |
| **Phase 0** | **Interface Lock** | ✅ **COMPLETE** | Exact `ExtractedEntitiesJson` schema with field-level types; `DeeSqsMessagePayload` contract; `to_lqa_contract()` and `to_vie_features()` export helpers; configurable confidence threshold (`DEE_CONFIDENCE_THRESHOLD`, default 0.85); structured actionable `suggested_resolution` strings. |
| **Phase 1** | **OCR Layer (Tesseract)** | ✅ **COMPLETE** | Ingests from files, bytes, or AWS S3 (`ingest_from_s3`); image normalization (EXIF deskew, grayscale, 1.8x contrast boost, autocontrast, sharpening); PDF rasterization at 200 DPI via PyMuPDF; retains raw OCR text and per-word confidence metrics; regional script detection (Kannada, Marathi/Devanagari, Telugu, Tamil) mitigating O-07. |
| **Phase 2** | **Entity Extraction (Claude)** | ✅ **COMPLETE** | Type-conditional prompts (`dee/prompts.py`) versioned in Git (`PROMPT_VERSION = "1.0.0"`); AI Gateway pattern (`dee/gateway.py`) with mandatory PII tokenization (Aadhaar/PAN), deterministic SHA-256 caching, Anthropic SDK client, and safe fallback. |
| **Phase 3** | **Confidence Scoring & Routing** | ✅ **COMPLETE** | Composite confidence combining OCR readability and field certainties; writes rows matching `LegalDocument` in `src/db/schema.prisma`; routes $< 0.85$ to Ops review queue with suggested resolutions; auto-approves $\ge 0.85$. |
| **Phase 4** | **Status Streaming** | ✅ **COMPLETE** | Dispatches real-time SSE events (`QUEUED` $\to$ `OCR_IN_PROGRESS` $\to$ `OCR_COMPLETED` $\to$ `EXTRACTION_IN_PROGRESS` $\to$ `COMPLETED` / `ROUTED_TO_MANUAL_OPS`); maintains per-document event ring buffer supporting `last-event-id` auto-reconnect and replay (`get_events_since` and `get_sse_chunks_since`). |
| **Phase 5** | **Continuous Learning Loop (§12.3)** | ✅ **COMPLETE** | `dee/learning_loop.py` captures labeled extraction events to Kafka/S3 archive; records ops-reviewer approvals and corrections with field-level diffs; exports training batches for weekly Kubeflow/Metaflow retraining jobs. |

---

## 5. Quick Start & Execution

### Run Unit Tests (13 Automated Tests Covering All Phases, Multilingual & In-Memory Cleanup)
```bash
python -m unittest dee.test_dee.test_dee_pipeline
```

### Run Interactive CLI Demo
```bash
python dee/run_dee_demo.py
```

### Drop-In Dataset Evaluation & Training CLI (`dee/train_and_eval.py`)

The pipeline includes a dedicated, dataset-agnostic CLI tool (`dee/train_and_eval.py`) and dataset manager (`dee/dataset_manager.py`). **No mock data is kept in the repository**; whenever you have your real image dataset ready, you can point directly to any local directory:

#### 1. Evaluate Pipeline Accuracy on Real Image Dataset
Recursively scans your image directory (`.png`, `.jpg`, `.jpeg`, `.tiff`, `.tif`, `.bmp`, `.webp`, `.pdf`), runs OCR + extraction, and outputs accuracy metrics (auto-approval rate, field match rate, mean confidence score):
```bash
python dee/train_and_eval.py --mode eval --data-dir "path/to/your/image_dataset"
```

#### 2. Bootstrap Pseudo-Labels for Unannotated Images
If your dropped dataset does not have pre-existing annotations, this command runs high-confidence extraction and saves ground-truth candidate JSONs alongside each document for review:
```bash
python dee/train_and_eval.py --mode bootstrap --data-dir "path/to/your/image_dataset" --confidence-threshold 0.85
```

#### 3. Export Fine-Tuning JSONL (Chat / Vision Format)
Formats high-confidence documents into standard fine-tuning pairs ready for Claude / LLM retraining:
```bash
python dee/train_and_eval.py --mode export-finetune --data-dir "path/to/your/image_dataset" --out-dir "path/to/finetuning_export"
```

### Python API Usage

#### Standard File Ingestion:
```python
from dee import dee_pipeline, DocumentType

result = dee_pipeline.process_document(
    file_input="path/to/sale_deed.pdf", # or raw bytes
    document_type=DocumentType.SALE_DEED,
    document_id="doc-101",
    property_id="prop-202",
)

print(result.status)                # DocumentStatus.EXTRACTED or REVIEWING
print(result.aiConfidenceScore)     # e.g. 0.942
print(result.aiSummaryPlainEnglish) # 3-paragraph plain-English summary
print(result.requiresManualReview)  # False (auto-approved) or True (ops queue)
```

#### SQS Message Worker Ingestion (Phase 0/1):
```python
from dee.models import DeeSqsMessagePayload
from dee.pipeline import dee_pipeline

sqs_payload = DeeSqsMessagePayload(
    s3_bucket="namasthetu-legal-docs",
    s3_key="uploads/deed-101.pdf",
    document_type=DocumentType.SALE_DEED,
    property_id="prop-202",
    version_id="ver-uuid-101",
)
result = dee_pipeline.process_sqs_message(sqs_payload)
```

#### SSE Reconnect Support (Phase 4):
```python
# Replay missed events after client network disconnect:
events = dee_pipeline.get_events_since(document_id="doc-101", last_event_id="evt_abc123")
sse_chunks = dee_pipeline.get_sse_chunks_since(document_id="doc-101", last_event_id="evt_abc123")
```

#### Continuous Learning & Retraining Export (Phase 5):
```python
from dee.learning_loop import dee_learning_collector

# Human ops reviewer corrections recorded with field deltas:
dee_learning_collector.record_ops_correction(
    original_result=result,
    corrected_entities=corrected_entities,
    reviewer_id="reviewer_88",
    reviewer_notes="Survey number updated after physical inspection",
)

# Export labeled pairs for weekly Kubeflow/Metaflow training pipeline:
dataset = dee_learning_collector.export_dataset()
```

---

## 6. Non-Negotiables & Risk Mitigations Carried Out

1. **Mandatory PII Masking (§5 Non-Negotiable):**  
   Raw Aadhaar (12-digit) and PAN numbers are tokenized *before* prompt ingestion (`mask_pii()`), preventing any PII leaks into logs or external LLM providers.
2. **Confidence-Driven Ops Routing (§03.M02):**  
   Documents below the $0.85$ threshold are automatically flagged (`requiresManualReview = True`) and supplied with an actionable `suggested_resolution` string for human reviewers.
3. **Regional Script Awareness & Native Multilingual Support (O-07):**  
   `dee/ocr.py` dynamically identifies regional scripts (Kannada, Marathi, Hindi/Devanagari, Telugu, Tamil, Gujarati, Bengali) and configures Tesseract multi-language models (`eng+kan+hin+mar+tel+tam`). Prompts (`dee/prompts.py` v1.1.0) and gateways normalize vernacular legal conventions (e.g., ಕ್ರಯಪತ್ರ, विकसन करार, बैनामा, పట్టాదారు, விற்பனையாளர்) into canonical JSON schema keys while faithfully preserving native party names and schedule descriptions.
4. **Zero-Drift Database Contract:**  
   Outputs cleanly populate `model LegalDocument` and `model DeedHistoryEvent` in `src/db/schema.prisma`.
5. **Drop-In Dataset & Retraining Architecture:**  
   The pipeline core is completely decoupled from sample data. Zero mock datasets are persisted in the repository. As soon as real image batches are available, they can be directly dropped and processed via `dee/train_and_eval.py` for evaluation, pseudo-labeling, and fine-tune dataset generation.

