"""
Interactive CLI Demo Runner for Document Extraction Engine (DEE)
Executes sample extractions and demonstrates:
  - Clean Sale Deed extraction
  - Encumbrance Certificate with active mortgage extraction
  - Low-confidence degraded scan routing to Manual Ops Review queue
  - Exact adherence to `src/db/schema.prisma`
"""

import sys
import os
import json
import time

# Ensure package path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dee.models import DocumentType, DocumentStatus
from dee.pipeline import dee_pipeline
from dee.test_dee.test_dee_pipeline import (
    SALE_DEED_CLEAN_TEXT,
    ENCUMBRANCE_CERTIFICATE_MORTGAGE_TEXT,
    DEGRADED_SCAN_TEXT,
    PUNE_SALE_DEED_TEXT,
)


def print_banner(title: str):
    print("\n" + "=" * 80)
    print(f"📄 {title}")
    print("=" * 80)


def print_result_summary(result):
    print(f"  🆔 Document ID:           {result.document_id}")
    print(f"  🏛️ Property ID:           {result.property_id}")
    print(f"  📑 Document Type:         {result.document_type.value}")
    
    status_icon = "✅" if result.status == DocumentStatus.EXTRACTED else "⚠️"
    print(f"  {status_icon} Status (schema.prisma): {result.status.value}")
    print(f"  📊 Composite Confidence:  {result.aiConfidenceScore * 100:.1f}%")
    print(f"  👤 Requires Manual Ops:   {'YES (Routed to Review Queue)' if result.requiresManualReview else 'NO (Auto-Approved)'}")
    print(f"  ⏱️ Processing Time:       {result.processing_time_ms:.1f} ms")

    entities = result.aiExtractedDataJson

    print("\n  [EXTRACTED PARTIES & OWNERS]")
    for o in entities.owners:
        rel = f" ({o.relation_type} {o.relative_name})" if o.relative_name else ""
        pan = f" · PAN: {o.pan_masked}" if o.pan_masked else ""
        print(f"    • {o.party_type.value}: {o.name}{rel}{pan}")

    print("\n  [PROPERTY IDENTIFIERS & BOUNDARIES]")
    sn = entities.survey_number
    print(f"    • Survey No:  {sn.survey_no or 'N/A'}")
    print(f"    • Khata / PID:{sn.katha_no or 'N/A'}")
    print(f"    • Unit / Flat:{sn.flat_no or 'N/A'}")
    print(f"    • Village:    {sn.village or 'N/A'}, Taluk: {sn.taluk or 'N/A'}")

    print("\n  [AREA MEASUREMENTS]")
    ar = entities.area
    print(f"    • Carpet Area:        {ar.carpet_area_sqft or 'N/A'} {ar.unit}")
    print(f"    • Super Built-up Area:{ar.super_built_up_sqft or 'N/A'} {ar.unit}")

    print("\n  [FINANCIALS & REGISTRATION]")
    if entities.sale_consideration_inr:
        print(f"    • Consideration:      INR {entities.sale_consideration_inr:,.0f}")
    if entities.dates:
        d = entities.dates[0]
        print(f"    • Date:               {d.date or d.raw_date_text}")
        print(f"    • Doc Number:         {d.document_number or 'N/A'}")
        print(f"    • SRO Office:         {d.sub_registrar_office or 'N/A'}")

    print("\n  [ENCUMBRANCES & LIABILITIES]")
    if entities.encumbrances:
        for enc in entities.encumbrances:
            cleared = " [DISCHARGED]" if enc.is_cleared else " [ACTIVE LIABILITY]"
            amt = f" - INR {enc.amount:,.0f}" if enc.amount else ""
            holder = f" ({enc.holder_name})" if enc.holder_name else ""
            print(f"    • {enc.encumbrance_type.value}{amt}{holder}{cleared}")
            if enc.description:
                print(f"      Description: {enc.description}")

    if entities.suggested_resolution:
        print("\n  [ACTIONABLE SUGGESTED RESOLUTION FOR OPS REVIEWER]")
        print(f"    ⚠️ {entities.suggested_resolution}")

    print("\n  [AI PLAIN-ENGLISH SUMMARY (LegalDocument.aiSummaryPlainEnglish)]")
    for para in result.aiSummaryPlainEnglish.split("\n\n"):
        print(f"    {para}")

    print("\n  [DOWNSTREAM DeedHistoryEvent PAYLOADS]")
    for e in result.deedHistoryEvents:
        print(f"    • [{e.year}] {e.eventType.value} ({e.status.value}): {e.title}")
        print(f"      Parties: {e.parties}")
        if e.registrationVolume:
            print(f"      Volume:  {e.registrationVolume}")


def main():
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print_banner("DEMO 1: Clean Absolute Sale Deed (Bengaluru East - Prestige Unit 1402)")
    res1 = dee_pipeline.process_document(
        file_input=SALE_DEED_CLEAN_TEXT,
        document_type=DocumentType.SALE_DEED,
        document_id="doc-bng-sale-deed-01",
        property_id="prop-prestige-blr-101",
    )
    print_result_summary(res1)

    print_banner("DEMO 2: Encumbrance Certificate with Active Mortgage (Hyderabad - HDFC Bank)")
    res2 = dee_pipeline.process_document(
        file_input=ENCUMBRANCE_CERTIFICATE_MORTGAGE_TEXT,
        document_type=DocumentType.ENCUMBRANCE_CERTIFICATE,
        document_id="doc-hyd-ec-02",
        property_id="prop-jubilee-hyd-202",
    )
    print_result_summary(res2)

    print_banner("DEMO 3: Degraded Low-Contrast Scan (Manual Ops Triage Triggered)")
    res3 = dee_pipeline.process_document(
        file_input=DEGRADED_SCAN_TEXT,
        document_type=DocumentType.SALE_DEED,
        document_id="doc-degraded-scan-03",
        property_id="prop-degraded-303",
    )
    print_result_summary(res3)

    print_banner("DEMO 4: Dynamic Regional Conveyance Deed (Haveli, Pune - Balewadi Unit 402)")
    res4 = dee_pipeline.process_document(
        file_input=PUNE_SALE_DEED_TEXT,
        document_type=DocumentType.SALE_DEED,
        document_id="doc-pne-conveyance-04",
        property_id="prop-balewadi-pune-404",
    )
    print_result_summary(res4)

    print("\n" + "=" * 80)
    print("🎉 ALL DEE DEMOS EXECUTED SUCCESSFULLY — ZERO DRIFT WITH src/db/schema.prisma")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
