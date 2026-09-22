"""
Ownership Chain Reconstruction & Deed History Event Builder
Spec Reference: HYC-SCO-2026-3841 (§03.M02, §07.5, §7.3)
Transforms DEE structured extraction results directly into `DeedHistoryEvent` payloads
to populate the property timeline in `src/db/schema.prisma`.
"""

from __future__ import annotations
from typing import List, Optional
from datetime import datetime, date
from pipelines.dee.models import (
    ExtractedEntitiesJson,
    DeedHistoryEventPayload,
    DeedEventType,
    DeedEventStatus,
    DocumentType,
    ExtractedPartyType,
)


class OwnershipChainBuilder:
    """
    Constructs `DeedHistoryEvent` timeline rows directly from DEE structured extractions.
    """

    def build_events_from_extraction(
        self,
        extracted: ExtractedEntitiesJson,
        legal_document_id: Optional[str] = None,
        confidence: float = 0.95,
    ) -> List[DeedHistoryEventPayload]:
        """
        Generates timeline records for `DeedHistoryEvent` model.
        """
        events: List[DeedHistoryEventPayload] = []
        is_verified = confidence >= 0.85
        default_status = DeedEventStatus.VERIFIED if is_verified else DeedEventStatus.PENDING

        # Resolve primary parties string (e.g. "Grantor → Grantee")
        grantors = [o.name for o in extracted.owners if o.party_type == ExtractedPartyType.GRANTOR_SELLER]
        grantees = [o.name for o in extracted.owners if o.party_type in (ExtractedPartyType.GRANTEE_BUYER, ExtractedPartyType.ALLOTTEE)]
        
        parties_str = "Unknown Parties"
        if grantors and grantees:
            parties_str = f"{', '.join(grantors)} → {', '.join(grantees)}"
        elif grantees:
            parties_str = f"In favour of {', '.join(grantees)}"
        elif grantors:
            parties_str = f"Executed by {', '.join(grantors)}"

        # Resolve primary date and registration volume
        primary_year = datetime.now().year
        primary_date: Optional[date] = None
        reg_volume: Optional[str] = None

        if extracted.dates:
            d_entry = extracted.dates[0]
            if d_entry.year:
                primary_year = d_entry.year
            if d_entry.date:
                try:
                    primary_date = datetime.strptime(d_entry.date, "%Y-%m-%d").date()
                    primary_year = primary_date.year
                except ValueError:
                    pass
            
            vol_parts = []
            if d_entry.document_number:
                vol_parts.append(f"Doc #{d_entry.document_number}")
            if d_entry.book_number:
                vol_parts.append(d_entry.book_number)
            if d_entry.volume_number:
                vol_parts.append(f"Vol {d_entry.volume_number}")
            if d_entry.sub_registrar_office:
                vol_parts.append(d_entry.sub_registrar_office)
            if vol_parts:
                reg_volume = " · ".join(vol_parts)

        # Map by DocumentType (adhering strictly to enum DeedEventType in src/db/schema.prisma)
        if extracted.document_type == DocumentType.SALE_DEED:
            events.append(
                DeedHistoryEventPayload(
                    eventType=DeedEventType.SALE_DEED,
                    status=default_status,
                    year=primary_year,
                    eventDate=primary_date,
                    title="Absolute Sale Deed (Registered Conveyance)",
                    parties=parties_str,
                    registrationVolume=reg_volume,
                    legalDocumentId=legal_document_id,
                    sequenceOrder=0,
                )
            )

        elif extracted.document_type == DocumentType.GIFT_DEED:
            events.append(
                DeedHistoryEventPayload(
                    eventType=DeedEventType.GIFT_DEED,
                    status=default_status,
                    year=primary_year,
                    eventDate=primary_date,
                    title="Gift Settlement Deed (Registered)",
                    parties=parties_str,
                    registrationVolume=reg_volume,
                    legalDocumentId=legal_document_id,
                    sequenceOrder=0,
                )
            )

        elif extracted.document_type == DocumentType.ALLOTMENT_LETTER:
            events.append(
                DeedHistoryEventPayload(
                    eventType=DeedEventType.SALE_DEED,
                    status=default_status,
                    year=primary_year,
                    eventDate=primary_date,
                    title="Developer Allotment Agreement",
                    parties=parties_str,
                    registrationVolume=reg_volume,
                    legalDocumentId=legal_document_id,
                    sequenceOrder=0,
                )
            )

        elif extracted.document_type == DocumentType.KHATA_CERTIFICATE:
            events.append(
                DeedHistoryEventPayload(
                    eventType=DeedEventType.KHATA_TRANSFER,
                    status=default_status,
                    year=primary_year,
                    eventDate=primary_date,
                    title="Municipal Revenue Khata Registration & Transfer",
                    parties=parties_str,
                    registrationVolume=f"Khata #{extracted.survey_number.katha_no or 'Verified'}",
                    legalDocumentId=legal_document_id,
                    sequenceOrder=0,
                )
            )

        elif extracted.document_type == DocumentType.ENCUMBRANCE_CERTIFICATE:
            # Process encumbrance entries into mortgage / clearance events
            for idx, enc in enumerate(extracted.encumbrances):
                if enc.encumbrance_type in ("NONE", None):
                    events.append(
                        DeedHistoryEventPayload(
                            eventType=DeedEventType.ENCUMBRANCE_CLEARED,
                            status=DeedEventStatus.CLEARED,
                            year=primary_year,
                            eventDate=primary_date,
                            title="Nil Encumbrance Certificate Verified (Clean Title)",
                            parties=parties_str,
                            registrationVolume=reg_volume,
                            legalDocumentId=legal_document_id,
                            sequenceOrder=idx + 1,
                        )
                    )
                    continue

                if enc.is_cleared:
                    e_type = DeedEventType.MORTGAGE_RELEASE
                    e_status = DeedEventStatus.CLEARED
                    title = f"Discharge & Release of Mortgage — {enc.holder_name or 'Financial Institution'}"
                else:
                    e_type = DeedEventType.MORTGAGE_RELEASE
                    e_status = DeedEventStatus.PENDING
                    title = f"Registered Mortgage Charge — {enc.holder_name or 'Financial Institution'}"

                e_date = primary_date
                e_year = primary_year
                if enc.registration_date:
                    try:
                        e_date = datetime.strptime(enc.registration_date, "%Y-%m-%d").date()
                        e_year = e_date.year
                    except ValueError:
                        pass

                amt_str = f" (INR {enc.amount:,.0f})" if enc.amount else ""
                events.append(
                    DeedHistoryEventPayload(
                        eventType=e_type,
                        status=e_status,
                        year=e_year,
                        eventDate=e_date,
                        title=f"{title}{amt_str}",
                        parties=f"{enc.claimant_or_borrower or 'Borrower'} ↔ {enc.holder_name or 'Lender Bank'}",
                        registrationVolume=enc.document_number,
                        legalDocumentId=legal_document_id,
                        sequenceOrder=idx + 1,
                    )
                )

        return events


ownership_chain_builder = OwnershipChainBuilder()
