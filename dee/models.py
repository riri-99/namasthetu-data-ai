"""
Data Models for Document Extraction Engine (DEE)
Spec Reference: HYC-SCO-2026-3841 (§12.1–§12.4, §03.M02, §07.5)
Strictly adheres to PostgreSQL schema defined in `src/db/schema.prisma` without modifying it.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timezone
from pydantic import BaseModel, Field


# ============================================================================
# 1. PRISMA SCHEMA ENUM MIRRORS (ZERO DRIFT WITH src/db/schema.prisma)
# ============================================================================

class DocumentStatus(str, Enum):
    """Mirror of `enum DocumentStatus` in `src/db/schema.prisma`"""
    UPLOADED = "UPLOADED"
    EXTRACTING = "EXTRACTING"
    EXTRACTED = "EXTRACTED"
    VALIDATED = "VALIDATED"
    REVIEWING = "REVIEWING"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class DocumentType(str, Enum):
    """Mirror of `enum DocumentType` in `src/db/schema.prisma`"""
    SALE_DEED = "SALE_DEED"
    CONVEYANCE_DEED = "CONVEYANCE_DEED"
    GIFT_DEED = "GIFT_DEED"
    ALLOTMENT_LETTER = "ALLOTMENT_LETTER"
    KHATA_CERTIFICATE = "KHATA_CERTIFICATE"
    ENCUMBRANCE_CERTIFICATE = "ENCUMBRANCE_CERTIFICATE"
    PROPERTY_TAX_RECEIPT = "PROPERTY_TAX_RECEIPT"
    RERA_APPROVAL = "RERA_APPROVAL"
    BUILDING_PLAN_APPROVAL = "BUILDING_PLAN_APPROVAL"
    OCCUPANCY_CERTIFICATE = "OCCUPANCY_CERTIFICATE"
    ELECTRICITY_BILL = "ELECTRICITY_BILL"


class DeedEventType(str, Enum):
    """Mirror of `enum DeedEventType` in `src/db/schema.prisma`"""
    SALE_DEED = "SALE_DEED"
    GIFT_DEED = "GIFT_DEED"
    KHATA_TRANSFER = "KHATA_TRANSFER"
    ENCUMBRANCE_CLEARED = "ENCUMBRANCE_CLEARED"
    MORTGAGE_RELEASE = "MORTGAGE_RELEASE"
    ULPIN_SEEDED = "ULPIN_SEEDED"
    DLD_CONVEYANCE = "DLD_CONVEYANCE"
    RERA_REGISTRATION = "RERA_REGISTRATION"
    INSPECTION_AUDIT = "INSPECTION_AUDIT"


class DeedEventStatus(str, Enum):
    """Mirror of `enum DeedEventStatus` in `src/db/schema.prisma`"""
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    CLEARED = "CLEARED"
    REJECTED = "REJECTED"


# ============================================================================
# 2. STRUCTURED ENTITY MODELS (§12.2 / §03.M02)
# ============================================================================

class ExtractedPartyType(str, Enum):
    GRANTOR_SELLER = "GRANTOR_SELLER"
    GRANTEE_BUYER = "GRANTEE_BUYER"
    ALLOTTEE = "ALLOTTEE"
    DEVELOPER_BUILDER = "DEVELOPER_BUILDER"
    FINANCIAL_INSTITUTION = "FINANCIAL_INSTITUTION"
    WITNESS = "WITNESS"
    OTHER = "OTHER"


class ExtractedOwner(BaseModel):
    name: str = Field(..., description="Full legal name of the party")
    party_type: ExtractedPartyType = Field(default=ExtractedPartyType.GRANTEE_BUYER)
    relation_type: Optional[str] = Field(None, description="e.g. S/o, D/o, W/o")
    relative_name: Optional[str] = Field(None, description="Father/Spouse name")
    pan_masked: Optional[str] = Field(None, description="Tokenized PAN (e.g. ABCDE****F)")
    aadhaar_masked: Optional[str] = Field(None, description="Tokenized Aadhaar (e.g. XXXX-XXXX-1234)")
    address: Optional[str] = Field(None, description="Address of party as stated in deed")
    share_percentage: Optional[float] = Field(None, description="Ownership share % if multiple owners")


class ExtractedSurveyNumber(BaseModel):
    survey_no: Optional[str] = Field(None, description="Revenue survey number, e.g. '142/2A'")
    hissa_no: Optional[str] = Field(None, description="Sub-division / hissa number")
    katha_no: Optional[str] = Field(None, description="Khata / E-Khata / Property ID")
    plot_no: Optional[str] = Field(None, description="Plot / site number")
    flat_no: Optional[str] = Field(None, description="Apartment unit number")
    building_name: Optional[str] = Field(None, description="Apartment or commercial complex name")
    village: Optional[str] = Field(None, description="Revenue village / Locality")
    hobli: Optional[str] = Field(None, description="Hobli / Firka")
    taluk: Optional[str] = Field(None, description="Taluk / Tehsil")
    district: Optional[str] = Field(None, description="Revenue District")
    state: Optional[str] = Field(None, description="State (e.g. Karnataka, Telangana, Maharashtra)")
    boundaries: Optional[Dict[str, str]] = Field(
        default=None,
        description="Schedule boundaries (North, South, East, West)"
    )


class ExtractedArea(BaseModel):
    carpet_area_sqft: Optional[float] = Field(None, description="Carpet area in square feet")
    super_built_up_sqft: Optional[float] = Field(None, description="Super built-up area in square feet")
    plot_area_sqft: Optional[float] = Field(None, description="Plot / site area in square feet")
    raw_area_text: Optional[str] = Field(None, description="Verbatim area string, e.g. '1200 Sq Ft' or '2 Guntas'")
    unit: str = Field(default="SQFT", description="Unit of measurement (SQFT, SQM, ACRE, GUNTA)")


class ExtractedDateEntry(BaseModel):
    date_type: str = Field(..., description="e.g. 'EXECUTION', 'REGISTRATION', 'ALLOTMENT', 'POSSESSION'")
    date: Optional[str] = Field(None, description="ISO format date YYYY-MM-DD if parseable")
    year: Optional[int] = Field(None, description="Calendar year")
    raw_date_text: Optional[str] = Field(None, description="Verbatim date string in document")
    document_number: Optional[str] = Field(None, description="Sub-registrar registration number")
    book_number: Optional[str] = Field(None, description="Sub-registrar Book number (e.g. 'Book 1')")
    volume_number: Optional[str] = Field(None, description="Sub-registrar Volume / CD number")
    page_numbers: Optional[str] = Field(None, description="Sub-registrar Page range")
    sub_registrar_office: Optional[str] = Field(None, description="SRO Name (e.g. 'SRO Indiranagar')")


class EncumbranceType(str, Enum):
    MORTGAGE = "MORTGAGE"
    CHARGE = "CHARGE"
    LIEN = "LIEN"
    LEASE = "LEASE"
    COURT_ATTACHMENT = "COURT_ATTACHMENT"
    DEVELOPMENT_RIGHTS = "DEVELOPMENT_RIGHTS"
    EASEMENT = "EASEMENT"
    TAX_ARREARS = "TAX_ARREARS"
    NONE = "NONE"


class ExtractedEncumbranceEntry(BaseModel):
    entry_id: str = Field(..., description="Encumbrance line or serial reference")
    encumbrance_type: EncumbranceType = Field(default=EncumbranceType.MORTGAGE)
    amount: Optional[float] = Field(None, description="Monetary consideration / loan liability")
    currency: str = Field(default="INR", description="Currency code (INR, AED, USD)")
    holder_name: Optional[str] = Field(None, description="Lender bank or charge holder name")
    claimant_or_borrower: Optional[str] = Field(None, description="Name of mortgagor / debtor")
    registration_date: Optional[str] = Field(None, description="Date of encumbrance registration")
    document_number: Optional[str] = Field(None, description="Deed / mortgage charge number")
    is_cleared: bool = Field(default=False, description="Whether mortgage release / discharge is recorded")
    discharge_doc_number: Optional[str] = Field(None, description="Discharge receipt / reconveyance number")
    description: Optional[str] = Field(None, description="Verbatim description of charge")


class FieldConfidenceBreakdown(BaseModel):
    owner: float = Field(default=0.0, ge=0.0, le=1.0)
    survey_no: float = Field(default=0.0, ge=0.0, le=1.0)
    area: float = Field(default=0.0, ge=0.0, le=1.0)
    dates: float = Field(default=0.0, ge=0.0, le=1.0)
    encumbrances: float = Field(default=0.0, ge=0.0, le=1.0)
    ocr_quality: float = Field(default=0.0, ge=0.0, le=1.0)


# ============================================================================
# 3. COMPLETE DOC_EXTRACTION PAYLOAD (aiExtractedDataJson in schema.prisma)
# ============================================================================

class ExtractedEntitiesJson(BaseModel):
    """
    Schema stored inside `LegalDocument.aiExtractedDataJson` in `src/db/schema.prisma`.
    Adheres strictly to §12.1-§12.2 and §07.5.
    """
    document_type: DocumentType
    property_id: Optional[str] = None
    document_id: Optional[str] = None
    
    # Core entities required by §12.1
    owners: List[ExtractedOwner] = Field(default_factory=list)
    survey_number: ExtractedSurveyNumber = Field(default_factory=ExtractedSurveyNumber)
    area: ExtractedArea = Field(default_factory=ExtractedArea)
    dates: List[ExtractedDateEntry] = Field(default_factory=list)
    encumbrances: List[ExtractedEncumbranceEntry] = Field(default_factory=list)
    
    # Financial considerations
    sale_consideration_inr: Optional[float] = Field(None, description="Sale price / stamp value")
    market_guidance_value_inr: Optional[float] = Field(None, description="Government guidance value")
    stamp_duty_paid_inr: Optional[float] = Field(None, description="Stamp duty fee paid")
    registration_fee_paid_inr: Optional[float] = Field(None, description="Registration fee paid")
    
    # Metadata and ops routing
    field_confidence: FieldConfidenceBreakdown = Field(default_factory=FieldConfidenceBreakdown)
    suggested_resolution: Optional[str] = Field(
        None,
        description="Actionable explanation for ops review queue when confidence < 0.85"
    )
    is_regional_script: bool = Field(default=False, description="Detected non-English regional script")
    regional_language: Optional[str] = None
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_lqa_contract(self) -> Dict[str, Any]:
        """
        Exports extracted entities in the schema expected by Listing Auditor (LQA) (§12.1).
        Checks that extracted entities match the listing draft.
        """
        owner_names = [o.name for o in self.owners]
        execution_date = next((d.date for d in self.dates if d.date_type == "EXECUTION" and d.date), None)
        return {
            "document_type": self.document_type.value,
            "property_id": self.property_id,
            "owner_names": owner_names,
            "survey_no": self.survey_number.survey_no,
            "plot_no": self.survey_number.plot_no,
            "flat_no": self.survey_number.flat_no,
            "building_name": self.survey_number.building_name,
            "carpet_area_sqft": self.area.carpet_area_sqft,
            "super_built_up_sqft": self.area.super_built_up_sqft,
            "execution_date": execution_date,
            "active_encumbrances_count": len([e for e in self.encumbrances if not e.is_cleared]),
        }

    def to_vie_features(self) -> Dict[str, Any]:
        """
        Exports extracted entities in the feature dictionary expected by Valuation Engine (VIE) (§12.1).
        Uses extracted area, registration year, and encumbrance liabilities as model features.
        """
        execution_year = next((d.year for d in self.dates if d.year), None)
        total_mortgage_liability = sum(
            e.amount or 0.0 for e in self.encumbrances if not e.is_cleared and e.amount
        )
        return {
            "property_id": self.property_id,
            "document_type": self.document_type.value,
            "carpet_area_sqft": self.area.carpet_area_sqft or 0.0,
            "super_built_up_sqft": self.area.super_built_up_sqft or 0.0,
            "plot_area_sqft": self.area.plot_area_sqft or 0.0,
            "execution_year": execution_year,
            "sale_consideration_inr": self.sale_consideration_inr,
            "market_guidance_value_inr": self.market_guidance_value_inr,
            "stamp_duty_paid_inr": self.stamp_duty_paid_inr,
            "has_active_encumbrance": any(not e.is_cleared for e in self.encumbrances),
            "total_encumbrance_liability_inr": total_mortgage_liability,
        }



# ============================================================================
# 4. DOWNSTREAM DEED HISTORY EVENT PAYLOAD (For DeedHistoryEvent in schema)
# ============================================================================

class DeedHistoryEventPayload(BaseModel):
    """
    Directly populates rows in `model DeedHistoryEvent` in `src/db/schema.prisma`.
    Feeds the 3-transaction ownership chain timeline.
    """
    eventType: DeedEventType
    status: DeedEventStatus = DeedEventStatus.PENDING
    year: int
    eventDate: Optional[date] = None
    title: str
    parties: str  # e.g. "Grantor Party → Grantee Party"
    registrationVolume: Optional[str] = None
    legalDocumentId: Optional[str] = None
    sequenceOrder: int = 0


# ============================================================================
# 5. FULL PIPELINE EXTRACTION RESULT
# ============================================================================

class DeeExtractionResult(BaseModel):
    """
    The complete result emitted by DEE.
    Matches the columns of `model LegalDocument` in `src/db/schema.prisma`:
      - status: DocumentStatus
      - aiExtractedDataJson: Json
      - aiConfidenceScore: Float
      - aiSummaryPlainEnglish: String (3 paragraphs)
      - requiresManualReview: Boolean
      - validUntil: DateTime?
    """
    document_id: str
    property_id: str
    document_type: DocumentType
    status: DocumentStatus
    
    # Exact LegalDocument table columns
    aiExtractedDataJson: ExtractedEntitiesJson
    aiConfidenceScore: float = Field(..., ge=0.0, le=1.0)
    aiSummaryPlainEnglish: str
    requiresManualReview: bool = False
    validUntil: Optional[datetime] = None
    
    # Downstream timeline payloads
    deedHistoryEvents: List[DeedHistoryEventPayload] = Field(default_factory=list)
    
    # Telemetry
    processing_time_ms: float
    ocr_engine_used: str = "Tesseract"
    llm_model_used: str = "claude-3-5-sonnet-20241022"


# ============================================================================
# 6. SSE STATUS STREAMING EVENT (Matches §11.3 & §12.1)
# ============================================================================

class DeePipelineStage(str, Enum):
    QUEUED = "QUEUED"
    INGESTING = "INGESTING"
    OCR_IN_PROGRESS = "OCR_IN_PROGRESS"
    OCR_COMPLETED = "OCR_COMPLETED"
    EXTRACTION_IN_PROGRESS = "EXTRACTION_IN_PROGRESS"
    CONFIDENCE_EVALUATION = "CONFIDENCE_EVALUATION"
    COMPLETED = "COMPLETED"
    ROUTED_TO_MANUAL_OPS = "ROUTED_TO_MANUAL_OPS"
    FAILED = "FAILED"


class DeePipelineEvent(BaseModel):
    event_id: str
    stage: DeePipelineStage
    document_id: str
    property_id: str
    progress_percentage: int
    message: str
    confidence: Optional[float] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: Optional[Dict[str, Any]] = None

    def to_sse_message(self) -> str:
        """
        Formats event as standard Server-Sent Events (SSE) wire chunk (§11.3).
        Includes event ID for auto-reconnect with `last-event-id`.
        """
        import json
        payload = json.dumps(self.model_dump(mode="json"))
        return f"id: {self.event_id}\nevent: {self.stage.value}\ndata: {payload}\n\n"


# ============================================================================
# 7. SQS MESSAGE CONTRACT (§2 / Phase 0 Interface Lock)
# ============================================================================

class DeeSqsMessagePayload(BaseModel):
    """
    Contract for messages arriving via AWS SQS from upload service.
    Spec Reference: DEE Plan §4 Phase 0 / §2 Architecture
    Cross-team dependency: S3 key, document type, property_id, version_id.
    """
    s3_bucket: str = Field(..., description="S3 bucket containing the raw uploaded document")
    s3_key: str = Field(..., description="S3 object key path")
    document_type: DocumentType = Field(..., description="Document classification (e.g. SALE_DEED, ENCUMBRANCE_CERTIFICATE)")
    property_id: str = Field(..., description="Target property ID")
    version_id: str = Field(..., description="Immutable DOCUMENT_VERSION UUID in PostgreSQL")
    document_id: Optional[str] = Field(None, description="Logical DOCUMENT UUID; defaults to version_id if not provided")
    mime_type: str = Field(default="application/pdf", description="MIME type of document (PDF, image/jpeg, image/png)")
    uploaded_by_user_id: Optional[str] = Field(None, description="User ID of uploader for audit logs")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Upload timestamp")

