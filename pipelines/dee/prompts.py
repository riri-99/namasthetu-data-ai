"""
Versioned Extraction Prompts for DEE (Document Extraction Engine)
Spec Reference: HYC-SCO-2026-3841 (§12.2, §12.4)
Prompt Version: 1.0.0
Prompts are versioned as code to support regional adaptations, A/B testing, and continuous learning (§12.3).
"""

from __future__ import annotations
from typing import Dict, Tuple
from dee.models import DocumentType


PROMPT_VERSION = "1.1.0"

SYSTEM_PROMPT = """You are the Senior Legal Property Auditor & Document Extraction Engine (DEE) for Namasthetu, India's sovereign real-estate intelligence platform.
Your task is to analyze raw OCR text from legal property title documents (Sale Deeds, Encumbrance Certificates, Allotment Letters, Gift Deeds, Khata Certificates) across Indian states and languages and extract accurate, structured JSON adhering strictly to the schema provided.

NON-NEGOTIABLE OPERATIONAL RULES:
1. DATA FIDELITY: Never hallucinate or infer absent legal identifiers. If a survey number, boundary, or registration volume is unreadable or not present, output null.
2. PII PROTECTION: Never output unmasked 12-digit Aadhaar or PAN numbers. Mask them (e.g. XXXX-XXXX-1234, ABCDE****F).
3. MULTILINGUAL & REGIONAL SCRIPTS (O-07 COMPLIANCE):
   Documents are frequently written in regional Indian languages (Kannada, Marathi, Hindi, Telugu, Tamil, Gujarati, Bengali) or bilingual combinations (English + Regional).
   - If the document is in a regional script, set `is_regional_script: true` and specify `regional_language: '<Language>'` (e.g. "Kannada", "Marathi", "Hindi", "Telugu", "Tamil").
   - Extract and translate/normalize legal attributes into the standard English JSON keys, while preserving verbatim party names (or standard roman transliterations) and property names.
   - Core Indian Legal Equivalents:
     * Kannada: ಕ್ರಯಪತ್ರ / ಖರೀದಿ ಪತ್ರ (Sale Deed), ಋಣಭಾರ ಪ್ರಮಾಣ ಪತ್ರ (Encumbrance Certificate), ಖಾತಾ (Khata), ಸರ್ವೆ ನಂ (Survey No), ಚಕ್ಕುಬಂದಿ (Boundaries), ವಿಸ್ತೀರ್ಣ (Area), ಮಾರಾಟಗಾರ (Vendor), ಖರೀದಿದಾರ / ಕೊಳ್ಳುವವನು (Purchaser), ಕ್ರಯದ ಮೊತ್ತ (Consideration).
     * Marathi: खरेदीखत (Sale Deed), भारमुक्त प्रमाणपत्र (EC), मिळकत (Property), सर्व्हे क्र. / गट क्र. (Survey No), चतुःसीमा (Boundaries), क्षेत्रफळ (Area), देणार (Vendor), घेणार (Purchaser), दस्त क्रमांक (Doc No), मोबदला (Consideration).
     * Telugu: విక్రయ దస్తావేజు (Sale Deed), భార రహిత ధృవీకరణ పత్రం (EC), సర్వే నెం (Survey No), హద్దులు (Boundaries), విస్తీర్ణం (Area), అమ్మకందారు (Vendor), కొనుగోలుదారు (Purchaser).
     * Tamil: கிரய பத்திரம் (Sale Deed), வில்லங்க சான்றிதழ் (EC), சர்வே எண் (Survey No), எல்லைகள் (Boundaries), பரப்பளவு (Area), விற்பனையாளர் (Vendor), வாங்குபவர் (Purchaser).
     * Hindi: विक्रय विलेख / बैनामा (Sale Deed), भारमुक्त प्रमाण पत्र (EC), खसरा / सर्वे क्रमांक (Survey No), चौहद्दी (Boundaries), क्षेत्रफल (Area), विक्रेता (Vendor), क्रेता (Purchaser).
4. 3-PARAGRAPH PLAIN ENGLISH SUMMARY: You must provide a human-readable 3-paragraph summary in English:
   - Paragraph 1: Legal instrument definition, full names and roles of executing parties, property identity and address.
   - Paragraph 2: Monetary consideration, carpet/super built-up area, stamp duty, and registration details (SRO, book, volume).
   - Paragraph 3: Encumbrances, mortgage charges, easements, liabilities, and overall title clarity.
5. CONFIDENCE SELF-AUDIT: Provide a 0.0 to 1.0 confidence score for each field (owner, survey_no, area, dates, encumbrances). If any crucial field is obscured, specify an actionable `suggested_resolution` for manual human ops triage.
6. STRICT JSON OUTPUT: Return ONLY valid, parseable JSON without commentary, preambles, or postscripts.
"""


SALE_DEED_USER_TEMPLATE = """Analyze the following OCR text extracted from an Indian Sale Deed / Conveyance Deed.
Extract all structured legal property entities into the JSON format defined below.

OCR DOCUMENT TEXT:
----------------------------------------
{{OCR_TEXT}}
----------------------------------------

REQUIRED JSON STRUCTURE:
{
  "document_type": "SALE_DEED",
  "owners": [
    {
      "name": "Full legal name of party",
      "party_type": "GRANTOR_SELLER or GRANTEE_BUYER",
      "relation_type": "S/o, D/o, W/o or null",
      "relative_name": "Father or spouse name or null",
      "pan_masked": "Masked PAN or null",
      "aadhaar_masked": "Masked Aadhaar or null",
      "address": "Address or null",
      "share_percentage": 100.0
    }
  ],
  "survey_number": {
    "survey_no": "Survey number, e.g. 142/2A",
    "hissa_no": "Hissa or null",
    "katha_no": "Khata/PID number or null",
    "plot_no": "Plot number or null",
    "flat_no": "Apartment/Flat number or null",
    "building_name": "Building/Society name or null",
    "village": "Revenue Village or null",
    "hobli": "Hobli/Firka or null",
    "taluk": "Taluk or null",
    "district": "District or null",
    "state": "State or null",
    "boundaries": {
      "North": "North boundary schedule",
      "South": "South boundary schedule",
      "East": "East boundary schedule",
      "West": "West boundary schedule"
    }
  },
  "area": {
    "carpet_area_sqft": 1950.0,
    "super_built_up_sqft": 2450.0,
    "plot_area_sqft": null,
    "raw_area_text": "Verbatim area string in deed",
    "unit": "SQFT"
  },
  "dates": [
    {
      "date_type": "EXECUTION or REGISTRATION",
      "date": "YYYY-MM-DD or null",
      "year": 2024,
      "raw_date_text": "Verbatim date text",
      "document_number": "Sub-registrar doc number",
      "book_number": "Book number",
      "volume_number": "Volume/CD number",
      "page_numbers": "Page range",
      "sub_registrar_office": "SRO name"
    }
  ],
  "encumbrances": [
    {
      "entry_id": "ENC-001",
      "encumbrance_type": "MORTGAGE, LIEN, LEASE, COURT_ATTACHMENT, or NONE",
      "amount": 0.0,
      "currency": "INR",
      "holder_name": "Bank name or null",
      "claimant_or_borrower": "Borrower name or null",
      "registration_date": "YYYY-MM-DD or null",
      "document_number": "Deed number or null",
      "is_cleared": true,
      "description": "Indemnity/covenant statement or charge details"
    }
  ],
  "sale_consideration_inr": 28500000.0,
  "market_guidance_value_inr": 24200000.0,
  "stamp_duty_paid_inr": 1881000.0,
  "registration_fee_paid_inr": 285000.0,
  "field_confidence": {
    "owner": 0.95,
    "survey_no": 0.92,
    "area": 0.94,
    "dates": 0.93,
    "encumbrances": 0.90,
    "ocr_quality": 0.95
  },
  "suggested_resolution": null,
  "is_regional_script": false,
  "regional_language": null,
  "ai_summary_plain_english": "Three thorough paragraphs summarizing: 1) legal context & parties; 2) financial consideration & dimensions; 3) encumbrances & title veracity."
}
"""

ENCUMBRANCE_CERTIFICATE_USER_TEMPLATE = """Analyze the following OCR text extracted from an Indian Encumbrance Certificate (Form 15 / Form 16 / Nil Encumbrance).
Extract all historical encumbrance charges, mortgages, releases, and property schedule details into the JSON structure.

OCR DOCUMENT TEXT:
----------------------------------------
{{OCR_TEXT}}
----------------------------------------

REQUIRED JSON STRUCTURE:
{
  "document_type": "ENCUMBRANCE_CERTIFICATE",
  "owners": [
    {
      "name": "Name of recorded holder or transacting party",
      "party_type": "GRANTEE_BUYER or FINANCIAL_INSTITUTION",
      "relation_type": null,
      "relative_name": null,
      "pan_masked": null,
      "aadhaar_masked": null,
      "address": null,
      "share_percentage": 100.0
    }
  ],
  "survey_number": {
    "survey_no": "Survey number in schedule",
    "hissa_no": null,
    "katha_no": "Khata number",
    "plot_no": null,
    "flat_no": null,
    "building_name": null,
    "village": "Village name",
    "hobli": "Hobli name",
    "taluk": "Taluk name",
    "district": "District",
    "state": "State",
    "boundaries": null
  },
  "area": {
    "carpet_area_sqft": null,
    "super_built_up_sqft": null,
    "plot_area_sqft": null,
    "raw_area_text": "Area as noted in certificate",
    "unit": "SQFT"
  },
  "dates": [
    {
      "date_type": "SEARCH_PERIOD",
      "date": "YYYY-MM-DD",
      "year": 2024,
      "raw_date_text": "Search period, e.g. 01-04-2004 to 31-03-2024",
      "document_number": "EC application number",
      "book_number": null,
      "volume_number": null,
      "page_numbers": null,
      "sub_registrar_office": "Issuing SRO Office"
    }
  ],
  "encumbrances": [
    {
      "entry_id": "EC-ENTRY-001",
      "encumbrance_type": "MORTGAGE, CHARGE, or NONE",
      "amount": 15000000.0,
      "currency": "INR",
      "holder_name": "Lender / Bank name",
      "claimant_or_borrower": "Mortgagor name",
      "registration_date": "YYYY-MM-DD",
      "document_number": "Registered charge doc number",
      "is_cleared": false,
      "description": "Details of registered charge or nil declaration"
    }
  ],
  "sale_consideration_inr": null,
  "market_guidance_value_inr": null,
  "stamp_duty_paid_inr": null,
  "registration_fee_paid_inr": null,
  "field_confidence": {
    "owner": 0.90,
    "survey_no": 0.94,
    "area": 0.85,
    "dates": 0.95,
    "encumbrances": 0.95,
    "ocr_quality": 0.92
  },
  "suggested_resolution": null,
  "is_regional_script": false,
  "regional_language": null,
  "ai_summary_plain_english": "Three clear paragraphs summarizing: 1) search period, issuing SRO, and registered property; 2) recorded transactions or nil encumbrance declaration; 3) active liabilities, mortgages, or bank releases."
}
"""

ALLOTMENT_LETTER_USER_TEMPLATE = """Analyze the following OCR text extracted from a Developer / Housing Board Allotment Letter.
Extract the developer, allottee, unit designation, payment schedule, and terms into structured JSON.

OCR DOCUMENT TEXT:
----------------------------------------
{{OCR_TEXT}}
----------------------------------------
(Follow identical JSON schema structure, setting document_type="ALLOTMENT_LETTER")
"""


def get_prompt_for_document_type(doc_type: DocumentType) -> Tuple[str, str]:
    """
    Returns (system_prompt, user_template) matching the specific document type.
    """
    if doc_type == DocumentType.ENCUMBRANCE_CERTIFICATE:
        return SYSTEM_PROMPT, ENCUMBRANCE_CERTIFICATE_USER_TEMPLATE
    elif doc_type == DocumentType.ALLOTMENT_LETTER:
        return SYSTEM_PROMPT, ALLOTMENT_LETTER_USER_TEMPLATE
    else:
        return SYSTEM_PROMPT, SALE_DEED_USER_TEMPLATE
