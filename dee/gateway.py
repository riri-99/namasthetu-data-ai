"""
AI Gateway Client for DEE
Spec Reference: HYC-SCO-2026-3841 (§12.4, §5 Non-Negotiables)
Provides:
  1. Mandatory PII masking (Aadhaar & PAN tokenization) before sending to LLM.
  2. Claude 3.5 Sonnet integration via official Anthropic SDK.
  3. Response caching and cost governance.
  4. Fully dynamic entity extraction engine for zero-cost offline testing, CI/CD, and local execution.
"""

from __future__ import annotations
import os
import re
import json
import uuid
import hashlib
import time
from typing import Dict, Any, Optional, Tuple, List


# Regex patterns for Indian legal PII redaction (§5 Non-Negotiable)
AADHAAR_REGEX = re.compile(r"\b([2-9]\d{3})[ -]?(\d{4})[ -]?(\d{4})\b")
PAN_REGEX = re.compile(r"\b([A-Z]{5})(\d{4})([A-Z])\b")

MONTH_MAP = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "october": 10, "oct": 10,
    "november": 11, "nov": 11, "december": 12, "dec": 12,
}


def mask_pii(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Redacts raw Indian PII (Aadhaar and PAN) before passing text to external LLMs.
    Returns (masked_text, token_map) so tokens can be re-associated internally.
    """
    token_map: Dict[str, str] = {}
    counter = 1

    def aadhaar_sub(match: re.Match) -> str:
        nonlocal counter
        raw = match.group(0)
        token = f"[MASKED_AADHAAR_{counter}: XXXX-XXXX-{match.group(3)}]"
        token_map[token] = raw
        counter += 1
        return token

    def pan_sub(match: re.Match) -> str:
        nonlocal counter
        raw = match.group(0)
        token = f"[MASKED_PAN_{counter}: {match.group(1)[:2]}***{match.group(3)}]"
        token_map[token] = raw
        counter += 1
        return token

    masked = AADHAAR_REGEX.sub(aadhaar_sub, text)
    masked = PAN_REGEX.sub(pan_sub, masked)
    return masked, token_map


class AiGatewayClient:
    """
    Client for LLM Entity Extraction satisfying the AI Gateway requirement (§12.4).
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model_name = model
        self.cache: Dict[str, str] = {}
        self.client = None

        if self.api_key:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                pass

    def extract_structured_entities(
        self,
        ocr_text: str,
        system_prompt: str,
        user_prompt: str,
        document_type: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.0,
        ocr_confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Executes entity extraction through the gateway with PII protection.
        Returns parsed JSON dict from LLM response or dynamic heuristic fallback.
        """
        target_model = model or self.model_name

        # 1. PII Redaction
        sanitized_ocr, token_map = mask_pii(ocr_text)
        sanitized_user_prompt = user_prompt.replace("{{OCR_TEXT}}", sanitized_ocr)

        # 2. Check Gateway Cache
        cache_key = hashlib.sha256(
            f"{target_model}:{system_prompt}:{sanitized_user_prompt}".encode("utf-8")
        ).hexdigest()

        if cache_key in self.cache:
            raw_json = self.cache[cache_key]
            return json.loads(raw_json)

        # 3. Call Live Claude API if configured
        if self.client:
            response = self.client.messages.create(
                model=target_model,
                max_tokens=4096,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": sanitized_user_prompt}],
            )
            raw_text = response.content[0].text
            cleaned_json = self._clean_json_text(raw_text)
            self.cache[cache_key] = cleaned_json
            return json.loads(cleaned_json)

        # 4. Fallback: 100% Dynamic In-Memory Entity Extraction
        parsed_payload = self._dynamic_entity_extraction(
            sanitized_ocr,
            document_type=document_type,
            ocr_confidence=ocr_confidence,
        )
        self.cache[cache_key] = json.dumps(parsed_payload)
        return parsed_payload

    def _clean_json_text(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def _dynamic_entity_extraction(
        self,
        ocr_text: str,
        document_type: Optional[str] = None,
        ocr_confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Fully dynamic entity extraction engine.
        Extracts exclusively from input text using robust patterns. Zero hardcoded entities.
        """
        text = ocr_text
        lower = text.lower()

        # 1. Resolve Document Type dynamically (English + Regional Indian Languages)
        resolved_doc_type = document_type
        if not resolved_doc_type:
            if any(k in lower for k in (
                "encumbrance certificate", "form no. 15", "form 15", "form 16",
                "ಋಣಭಾರ ಪ್ರಮಾಣ ಪತ್ರ", "भारमुक्त प्रमाणपत्र", "भारमुक्त प्रमाण पत्र",
                "భార రహిత ధృవీకరణ పత్రం", "வில்லங்க சான்றிதழ்"
            )):
                resolved_doc_type = "ENCUMBRANCE_CERTIFICATE"
            elif any(k in lower for k in ("allotment letter", "allotment agreement", "ಹಂಚಿಕೆ ಪತ್ರ", "वाटप पत्र", "आवंटन पत्र")):
                resolved_doc_type = "ALLOTMENT_LETTER"
            elif any(k in lower for k in ("gift deed", "settlement deed", "ದಾನ ಪತ್ರ", "बक्षीसपत्र")):
                resolved_doc_type = "GIFT_DEED"
            elif any(k in lower for k in ("khata", "katha certificate", "ಖಾತಾ", "खाते प्रमाणपत्र", "ನಮೂನೆ 9", "ನಮೂನೆ 11")):
                resolved_doc_type = "KHATA_CERTIFICATE"
            else:
                resolved_doc_type = "SALE_DEED"

        # 2. Extract Transacting Parties (Owners) dynamically (Multilingual)
        owners: List[Dict[str, Any]] = []

        grantor_name = None
        grantee_name = None

        if resolved_doc_type == "ENCUMBRANCE_CERTIFICATE":
            ec_owner_m = re.search(
                r"(?:Registered Owner|Owner Name|Executant|Mortgagor|In favour of|ಸ್ವತ್ತುದಾರರು|भोगवटादार|खातेदार|పట్టాదారు)\s*[:\-\s,]+([^\n,:;]+?)(?:,|\n|\(|\bresiding\b|ವಾಸ|राहणार|$)",
                text,
                re.IGNORECASE,
            )
            if ec_owner_m:
                grantee_name = ec_owner_m.group(1).strip().rstrip(",. ")
        else:
            grantor_patterns = [
                r"(?:\bBETWEEN\b\s*[:\n\s]*)([^\n,:;]+?)(?:,|\n|\(|\bresiding\b|\bhereinafter\b|\bAND\b|PAN|Aadhaar|$)",
                r"(?:ಮಾರಾಟಗಾರ(?:ರು)?|ಬರೆದುಕೊಟ್ಟವರು|ಮೊದಲನೇ\s*ಪಾರ್ಟಿ|ಮಾರಾಟಗಾರರಾದ)\s*[:\-\s,]+([^\n,:;]+?)(?:,|\n|\(|\bವಾಸ\b|PAN|Aadhaar|ಇವರು|$)",
                r"(?:देणार|विक्री\s*करणारे|पहिले\s*पक्षकार|लिहून\s*देणार)\s*[:\-\s,]+([^\n,:;]+?)(?:,|\n|\(|\bराहणार\b|PAN|Aadhaar|यांसी|यांनी|$)",
                r"(?:विक्रेता|प्रथम\s*पक्ष)\s*[:\-\s,]+([^\n,:;]+?)(?:,|\n|\(|\bनिवासी\b|PAN|Aadhaar|आत्मज|$)",
                r"(?:అమ్మకందారు|మొదటి\s*పక్షం)\s*[:\-\s,]+([^\n,:;]+?)(?:,|\n|\(|\bనివాసి\b|PAN|Aadhaar|$)",
                r"(?:விற்பனையாளர்|முதல்\s*தரப்பினர்)\s*[:\-\s,]+([^\n,:;]+?)(?:,|\n|\(|\bவசிப்பவர்\b|PAN|Aadhaar|$)",
                r"(?<!called the\s)(?:vendor|seller|grantor|transferor|lessor|first\s*party)\s*[:\-\s,]+([^\n,:;]+?)(?:,|\n|\(|\bresiding\b|\bhereinafter\b|\bS/o\b|\bD/o\b|\bW/o\b|PAN|Aadhaar|$)",
            ]
            for pat in grantor_patterns:
                m = re.search(pat, text, re.IGNORECASE)
                if m and len(m.group(1).strip()) > 2:
                    candidate = m.group(1).strip().strip("/,. ")
                    if candidate.lower() not in (
                        "the vendor", "the seller", "the grantor", "between",
                        "grantor", "vendor", "seller", "first party",
                    ):
                        grantor_name = candidate
                        break

            grantee_patterns = [
                r"(?:\bAND\b\s*[:\n\s]*)([^\n,:;]+?)(?:,|\n|\(|\bresiding\b|\bhereinafter\b|PAN|Aadhaar|$)",
                r"(?:ಖರೀದಿದಾರ(?:ರು)?|ಕೊಳ್ಳುವವರು|ಬರೆಸಿಕೊಂಡವರು|ಎರಡನೇ\s*ಪಾರ್ಟಿ|ಖರೀದಿದಾರರಾದ)\s*[:\-\s,]+([^\n,:;]+?)(?:,|\n|\(|\bವಾಸ\b|PAN|Aadhaar|ಇವರಿಗೆ|$)",
                r"(?:घेणार|खरेदीदार|दुसरे\s*पक्षकार|लिहून\s*घेणार)\s*[:\-\s,]+([^\n,:;]+?)(?:,|\n|\(|\bराहणार\b|PAN|Aadhaar|यांस|यांना|$)",
                r"(?:(?<![\u0900-\u097F])क्रेता|द्वितीय\s*पक्ष)\s*[:\-\s,]+([^\n,:;]+?)(?:,|\n|\(|\bनिवासी\b|PAN|Aadhaar|आत्मज|$)",
                r"(?:కొనుగోలుదారు|రెండవ\s*పక్షం)\s*[:\-\s,]+([^\n,:;]+?)(?:,|\n|\(|\bనివాసి\b|PAN|Aadhaar|$)",
                r"(?:வாங்குபவர்|இரண்டாம்\s*தரப்பினர்)\s*[:\-\s,]+([^\n,:;]+?)(?:,|\n|\(|\bவசிப்பவர்\b|PAN|Aadhaar|$)",
                r"(?:Registered Owner|Owner Name|In favour of)\s*[:\-\s,]+([^\n,:;]+?)(?:,|\n|\(|\bresiding\b|$)",
                r"(?<!called the\s)(?:purchaser|buyer|grantee|transferee|lessee|allottee|second\s*party)\s*[:\-\s,]+([^\n,:;]+?)(?:,|\n|\(|\bresiding\b|\bhereinafter\b|\bS/o\b|\bD/o\b|\bW/o\b|PAN|Aadhaar|$)",
            ]
            for pat in grantee_patterns:
                m = re.search(pat, text, re.IGNORECASE)
                if m and len(m.group(1).strip()) > 2:
                    candidate = m.group(1).strip().strip("/,. ")
                    if candidate.lower() not in (
                        "the purchaser", "the vendor", "the company", "the buyer",
                        "the grantee", "stamps department", "grantee", "purchaser",
                        "buyer", "second party",
                    ):
                        grantee_name = candidate
                        break



        # Relationship parsing scoped specifically to each party
        def find_relation_for_party(name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
            if not name:
                return None, None
            idx = text.find(name)
            if idx != -1:
                chunk = text[idx:idx + 180]
                m = re.search(
                    r"\b(S/o|D/o|W/o|Son of|Daughter of|Wife of)\s+([A-Za-z\s\.]+?)(?:,|\n|\(|\bresiding\b|\baged\b|PAN|Aadhaar|$)",
                    chunk,
                    re.IGNORECASE,
                )
                if m:
                    return m.group(1).strip(), m.group(2).strip().rstrip(",. ")
            return None, None

        grantee_rel_type, grantee_rel_name = find_relation_for_party(grantee_name)
        grantor_rel_type, grantor_rel_name = find_relation_for_party(grantor_name)

        # Masked PAN & Aadhaar detection specific to party scope
        pan_pattern = re.compile(r"(\[MASKED_PAN[^\]]+\]|[A-Z]{5}\d{4}[A-Z])")
        aadhaar_pattern = re.compile(r"(\[MASKED_AADHAAR[^\]]+\]|\b\d{4}\s*\d{4}\s*\d{4}\b)")

        def find_id_for_party(name: Optional[str], pat: re.Pattern) -> Optional[str]:
            if not name:
                return None
            idx = text.find(name)
            if idx != -1:
                chunk = text[idx:idx + 300]
                m = pat.search(chunk)
                if m:
                    return m.group(1)
            # Global fallback
            all_m = pat.findall(text)
            return all_m[0] if all_m else None

        if grantee_name:
            owners.append({
                "name": grantee_name,
                "party_type": "ALLOTTEE" if resolved_doc_type == "ALLOTMENT_LETTER" else "GRANTEE_BUYER",
                "relation_type": grantee_rel_type,
                "relative_name": grantee_rel_name,
                "pan_masked": find_id_for_party(grantee_name, pan_pattern),
                "aadhaar_masked": find_id_for_party(grantee_name, aadhaar_pattern),
                "address": None,
                "share_percentage": 100.0,
            })

        if grantor_name and resolved_doc_type not in ("ENCUMBRANCE_CERTIFICATE", "ALLOTMENT_LETTER"):
            owners.append({
                "name": grantor_name,
                "party_type": "GRANTOR_SELLER",
                "relation_type": grantor_rel_type,
                "relative_name": grantor_rel_name,
                "pan_masked": find_id_for_party(grantor_name, pan_pattern),
                "aadhaar_masked": find_id_for_party(grantor_name, aadhaar_pattern),
                "address": None,
                "share_percentage": 100.0,
            })

        # 3. Extract Survey & Schedule Identifiers dynamically (Multilingual)
        survey_m = re.search(
            r"(?:survey|sy\.?|s\.?no\.?|ಸರ್ವೆ\s*(?:ನಂಬರ್|ನಂ)|ಸರ್ವೇ\s*ನಂ|सर्व्हे\s*(?:नंबर|क्र\.)|गट\s*(?:नंबर|क्र\.)|सी\.टी\.एस\.\s*क्र\.|खसरा\s*(?:नंबर|क्र\.)|सर्वे\s*क्रमांक|సర్వే\s*(?:నంబరు|నెం)|சர்வே\s*எண்)\s*(?:no\.?|number|#|cr\.?)?\s*[:\-\s#]*([0-9]+[\w/\-]*)",
            text,
            re.IGNORECASE,
        )
        survey_no = survey_m.group(1).strip() if survey_m else None

        hissa_m = re.search(r"(?:hissa|sub[\-\s]*div(?:ision)?|ಹಿಸ್ಸಾ|हिस्सा)\s*(?:no\.?|#)?\s*[:\-\s]*([0-9]+[A-Za-z0-9/\-]*)", text, re.IGNORECASE)
        hissa_no = hissa_m.group(1).strip() if hissa_m else None

        katha_m = re.search(r"(?:katha|khata|pid|property\s*id|e[\-\s]*khata|ಖಾತಾ\s*(?:ನಂ|ಸಂಖ್ಯೆ)?|ಕಥಾ|खाते\s*क्र\.|पट्टा\s*నం)\s*(?:no\.?|#)?\s*[:\-\s]*([A-Za-z0-9/\-]+)", text, re.IGNORECASE)
        katha_no = katha_m.group(1).strip() if katha_m else None

        plot_m = re.search(r"(?:plot|site|ನಿವೇಶನ|भूखंड|प्लॉट)\s*(?:no\.?|#)?\s*[:\-\s]*([A-Za-z0-9/\-]+)", text, re.IGNORECASE)
        plot_no = plot_m.group(1).strip() if plot_m else None

        flat_m = re.search(r"(?:flat|unit|apartment|ಫ್ಲ್ಯಾಟ್|सदनिका|फ्लैट)\s*(?:no\.?|#|bearing)?\s*(?:unit|flat|no\.?)?\s*[:\-\s]*([0-9]+[A-Za-z0-9\-]*)", text, re.IGNORECASE)
        flat_no = flat_m.group(1).strip() if flat_m else None

        village_m = re.search(r"([A-Za-z\s]+?)\s+(?:village|grama|mouza|ಗ್ರಾಮ|गाव|ग्राम)", text, re.IGNORECASE) or re.search(r"(?:village|ಗ್ರಾಮ|गाव)\s*[:\-\s]*([A-Za-z\s]+?)(?:,|\n|hobli|taluk|$)", text, re.IGNORECASE)
        village = village_m.group(1).strip().rstrip(",. ") if village_m else None

        hobli_m = re.search(r"([A-Za-z\s]+?)\s+hobli", text, re.IGNORECASE) or re.search(r"hobli\s*[:\-\s]*([A-Za-z\s]+?)(?:,|\n|taluk|district|$)", text, re.IGNORECASE)
        hobli = hobli_m.group(1).strip().rstrip(",. ") if hobli_m else None

        taluk_m = re.search(r"([A-Za-z\s]+?)\s+taluk", text, re.IGNORECASE) or re.search(r"(?:taluk|ತಾಲೂಕು|तालुका)\s*[:\-\s]*([A-Za-z\s]+?)(?:,|\n|district|$)", text, re.IGNORECASE)
        taluk = taluk_m.group(1).strip().rstrip(",. ") if taluk_m else None

        district_m = re.search(r"([A-Za-z\s]+?)\s+district", text, re.IGNORECASE) or re.search(r"(?:district|ಜಿಲ್ಲೆ|जिल्हा|ज़िला)\s*[:\-\s]*([A-Za-z\s]+?)(?:,|\n|state|$)", text, re.IGNORECASE)
        district = district_m.group(1).strip().rstrip(",. ") if district_m else None

        state = None
        for s in ("Karnataka", "Telangana", "Maharashtra", "Tamil Nadu", "Delhi", "Haryana", "Uttar Pradesh", "Gujarat", "Andhra Pradesh", "Kerala", "Madhya Pradesh"):
            if s.lower() in lower or (s == "Karnataka" and "ಕರ್ನಾಟಕ" in text) or (s == "Maharashtra" and "महाराष्ट्र" in text) or (s == "Telangana" and "తెలంగాణ" in text):
                state = s
                break

        # Schedule Boundaries (Multilingual: North, South, East, West in English/Kannada/Marathi/Hindi/Telugu/Tamil)
        north_m = re.search(r"(?:North|ಉತ್ತರ(?:ಕ್ಕೆ)?|उत्तरेस|उत्तर|ఉత్తరం|வடக்கு)\s*(?:by|:)?[:\s]*([^\n;\.]+)", text, re.IGNORECASE)
        south_m = re.search(r"(?:South|ದಕ್ಷಿಣ(?:ಕ್ಕೆ)?|दक्षिणेस|दक्षिण|దక్షిణం|தெற்கு)\s*(?:by|:)?[:\s]*([^\n;\.]+)", text, re.IGNORECASE)
        east_m = re.search(r"(?:East|ಪೂರ್ವ(?:ಕ್ಕೆ)?|पूर्वेस|पूरब|पूर्व|తూర్పు|கிழக்கு)\s*(?:by|:)?[:\s]*([^\n;\.]+)", text, re.IGNORECASE)
        west_m = re.search(r"(?:West|ಪಶ್ಚಿಮ(?:ಕ್ಕೆ)?|पश्चिमेस|पश्चिम|పడమర|மேற்கு)\s*(?:by|:)?[:\s]*([^\n;\.]+)", text, re.IGNORECASE)

        boundaries = None
        if north_m or south_m or east_m or west_m:
            boundaries = {}
            if north_m: boundaries["North"] = north_m.group(1).strip().rstrip(";,. ")
            if south_m: boundaries["South"] = south_m.group(1).strip().rstrip(";,. ")
            if east_m: boundaries["East"] = east_m.group(1).strip().rstrip(";,. ")
            if west_m: boundaries["West"] = west_m.group(1).strip().rstrip(";,. ")

        # 4. Extract Area Measurements dynamically (Multilingual)
        carpet_m = re.search(
            r"(?:carpet\s*area|ವಿಸ್ತೀರ್ಣ|क्षेत्रफळ|क्षेत्रफल|విస్తీರ್ణం|பரப்பளவு)\s*(?:of|is|:)?\s*([0-9,]+(?:\.[0-9]+)?)\s*(sq(?:uare)?\.?\s*(?:ft|feet|meters?|m|yards?)|ಚದರ\s*ಅಡಿ|चौ\.?\s*फूट|चौरस\s*फूट|वर्ग\s*फुट|చదరపు\s*అడుగులు|guntas?|ಗುಂಟೆ|गुंठे|cents?)?",
            text,
            re.IGNORECASE,
        )
        super_m = re.search(r"(?:super\s*built[\-\s]*up|built[\-\s]*up|sba)\s*area\s*(?:of|is|:)?\s*([0-9,]+(?:\.[0-9]+)?)\s*(sq(?:uare)?\.?\s*(?:ft|feet|meters?|m|yards?)|guntas?|cents?)?", text, re.IGNORECASE)
        plot_m = re.search(r"(?:plot|site|land)\s*area\s*(?:of|is|:)?\s*([0-9,]+(?:\.[0-9]+)?)\s*(sq(?:uare)?\.?\s*(?:ft|feet|meters?|m|yards?)|guntas?|cents?)?", text, re.IGNORECASE)
        generic_area_m = re.search(r"([0-9,]+(?:\.[0-9]+)?)\s*(sq(?:uare)?\.?\s*(?:ft|feet|meters?|yards?)|ಚದರ\s*ಅಡಿ|चौ\.?\s*फूट|वर्ग\s*फुट|guntas?|cents?)", text, re.IGNORECASE)

        carpet_sqft = float(carpet_m.group(1).replace(",", "")) if carpet_m else None
        super_sqft = float(super_m.group(1).replace(",", "")) if super_m else None
        plot_sqft = float(plot_m.group(1).replace(",", "")) if plot_m else None
        raw_area_text = carpet_m or super_m or plot_m or generic_area_m
        raw_area_str = raw_area_text.group(0).strip() if raw_area_text else None

        # 5. Extract Financial Consideration dynamically (Multilingual)
        consideration_m = re.search(
            r"(?:consideration|sale\s*price|value\s*of\s*property|sum\s*of|ಕ್ರಯದ\s*ಮೊತ್ತ|ಮೊತ್ತ\s*ರೂ\.?|मोबदला|रक्कम\s*रु\.?|प्रतिफल\s*(?:राशि)?|विక్రయ\s*ప్రతిఫలం)\s*(?:of|is|:)?\s*(?:inr|rs\.?|rupees|ರೂ\.?|रु\.?|रुपये|రూ\.?)?\s*([0-9,]+(?:\.[0-9]+)?)",
            text,
            re.IGNORECASE,
        )
        sale_consideration = float(consideration_m.group(1).replace(",", "")) if consideration_m else None

        stamp_m = re.search(r"(?:stamp\s*duty|ಮುದ್ರಾಂಕ\s*ಶುಲ್ಕ|मुद्रांक\s*शुल्क|स्टाम्प\s*शुल्क)\s*(?:paid|amount)?\s*[:\s]*(?:inr|rs\.?|rupees|ರೂ\.?|रु\.?|रुपये|రూ\.?)?\s*([0-9,]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
        stamp_duty = float(stamp_m.group(1).replace(",", "")) if stamp_m else None

        reg_fee_m = re.search(r"(?:registration\s*(?:fee|charges)|ನೋಂದಣಿ\s*ಶುಲ್ಕ|नोंदणी\s*फी|पंजीयन\s*शुल्क)\s*(?:paid)?\s*[:\s]*(?:inr|rs\.?|rupees|ರೂ\.?|रु\.?|रुपये|రూ\.?)?\s*([0-9,]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
        reg_fee = float(reg_fee_m.group(1).replace(",", "")) if reg_fee_m else None


        # 6. Extract Dates & SRO Registration dynamically
        date_iso = None
        date_year = None
        date_raw_str = None

        date_words_m = re.search(r"([0-9]{1,2})(?:st|nd|rd|th)?\s+(?:day\s+of\s+)?([A-Za-z]+),?\s+([0-9]{4})", text)
        date_slash_m = re.search(r"([0-9]{1,2})[\-\/\.]([0-9]{1,2})[\-\/\.]([0-9]{4})", text)
        date_iso_m = re.search(r"([0-9]{4})[\-\/\.]([0-9]{1,2})[\-\/\.]([0-9]{1,2})", text)

        if date_words_m:
            d_val = int(date_words_m.group(1))
            m_str = date_words_m.group(2).lower()
            y_val = int(date_words_m.group(3))
            m_val = MONTH_MAP.get(m_str, 1)
            date_iso = f"{y_val:04d}-{m_val:02d}-{d_val:02d}"
            date_year = y_val
            date_raw_str = date_words_m.group(0).strip()
        elif date_slash_m:
            d_val = int(date_slash_m.group(1))
            m_val = int(date_slash_m.group(2))
            y_val = int(date_slash_m.group(3))
            if m_val <= 12 and d_val <= 31:
                date_iso = f"{y_val:04d}-{m_val:02d}-{d_val:02d}"
                date_year = y_val
                date_raw_str = date_slash_m.group(0).strip()
        elif date_iso_m:
            y_val = int(date_iso_m.group(1))
            m_val = int(date_iso_m.group(2))
            d_val = int(date_iso_m.group(3))
            date_iso = f"{y_val:04d}-{m_val:02d}-{d_val:02d}"
            date_year = y_val
            date_raw_str = date_iso_m.group(0).strip()

        doc_num_m = re.search(r"(?:document|doc|charge\s*id|application)\s*(?:no\.?|number|#)\s*[:\-\s]*([A-Za-z0-9\-\(\)/]+)", text, re.IGNORECASE)
        doc_number = doc_num_m.group(1).strip().rstrip(",. ") if doc_num_m else None

        sro_m = re.search(r"(?:sub[\-\s]*registrar\s*(?:office)?|sro)\s*[:\-\s,]*([A-Za-z0-9\s,\.\(\)\-]+?)(?:,|\n|document|stored|book|search|district|$)", text, re.IGNORECASE)
        sro_office = sro_m.group(1).strip().rstrip(",. ") if sro_m else None

        book_m = re.search(r"book\s*([0-9IVX]+)", text, re.IGNORECASE)
        book_no = f"Book {book_m.group(1).strip()}" if book_m else None

        vol_m = re.search(r"(?:volume|vol\.?|cd)\s*[:\-\s]*([A-Za-z0-9\-]+)", text, re.IGNORECASE)
        volume_no = vol_m.group(1).strip() if vol_m else None

        dates: List[Dict[str, Any]] = []
        if date_iso or doc_number or sro_office:
            dates.append({
                "date_type": "REGISTRATION" if doc_number else "EXECUTION",
                "date": date_iso,
                "year": date_year,
                "raw_date_text": date_raw_str,
                "document_number": doc_number,
                "book_number": book_no,
                "volume_number": volume_no,
                "page_numbers": None,
                "sub_registrar_office": sro_office,
            })

        # 7. Extract Encumbrances dynamically
        encumbrances: List[Dict[str, Any]] = []
        is_active_charge = (
            ("charge id" in lower or "mortgagee" in lower or "secured loan" in lower or "loan amount" in lower or "registered simple mortgage" in lower) and
            not ("free from all" in lower or "free from any" in lower)
        )

        if is_active_charge or (("mortgage" in lower or "charge" in lower or "loan" in lower) and not ("free from" in lower or "clear title" in lower or "covenant" in lower)):
            bank_m = re.search(r"([A-Za-z\s]+(?:Bank|Finance|Financial|Corporation|Housing)[A-Za-z\s]*)", text, re.IGNORECASE)
            bank_name = bank_m.group(1).strip().rstrip(",. ") if bank_m else None

            loan_amt_m = re.search(r"(?:loan|mortgage|charge|secured|amount)\s*(?:of|amount)?\s*[:\-\s]*(?:inr|rs\.?|rupees)?\s*([0-9,]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
            loan_amt = float(loan_amt_m.group(1).replace(",", "")) if loan_amt_m else None

            is_uncleared = "no discharge" in lower or "not discharged" in lower or "active" in lower or "outstanding" in lower
            is_cleared = ("discharge" in lower or "released" in lower or "cancelled" in lower or "satisfied" in lower) and not is_uncleared

            encumbrances.append({
                "entry_id": f"ENC-{uuid.uuid4().hex[:6].upper()}",
                "encumbrance_type": "MORTGAGE",
                "amount": loan_amt,
                "currency": "INR",
                "holder_name": bank_name,
                "claimant_or_borrower": grantee_name,
                "registration_date": date_iso,
                "document_number": doc_number,
                "is_cleared": is_cleared,
                "description": f"Registered mortgage charge in favour of {bank_name or 'financial institution'} for loan facility",
            })
        elif "covenant" in lower or "free from" in lower or "clear title" in lower or "clean title" in lower:
            encumbrances.append({
                "entry_id": f"DECL-{uuid.uuid4().hex[:6].upper()}",
                "encumbrance_type": "NONE",
                "amount": 0.0,
                "currency": "INR",
                "holder_name": None,
                "claimant_or_borrower": None,
                "registration_date": date_iso,
                "document_number": None,
                "is_cleared": True,
                "description": "Vendor covenants property is free from all prior charges, liens, lis pendens, and encumbrances",
            })
        elif resolved_doc_type == "ENCUMBRANCE_CERTIFICATE" and ("nil" in lower or "no encumbrance" in lower):
            encumbrances.append({
                "entry_id": f"EC-NIL-{uuid.uuid4().hex[:6].upper()}",
                "encumbrance_type": "NONE",
                "amount": 0.0,
                "currency": "INR",
                "holder_name": None,
                "claimant_or_borrower": None,
                "registration_date": date_iso,
                "document_number": None,
                "is_cleared": True,
                "description": "Nil encumbrance certified for search period",
            })

        # 8. Dynamic Confidence Assessment & Degradation Detection
        is_degraded = (
            (ocr_confidence is not None and ocr_confidence < 0.75) or
            "blurry" in lower or "dark" in lower or "low_contrast" in lower or "unreadable" in lower or
            len(text.strip()) < 120 or (not survey_no and not owners)
        )

        # Dynamic Owner Confidence
        if len(owners) >= 2 and all(o.get("name") for o in owners):
            owner_conf = 0.96 if all(len(o["name"].split()) >= 2 for o in owners) else 0.85
        elif len(owners) == 1 and owners[0].get("name"):
            if resolved_doc_type in ("ENCUMBRANCE_CERTIFICATE", "ALLOTMENT_LETTER", "KHATA_CERTIFICATE"):
                owner_conf = 0.95 if len(owners[0]["name"].split()) >= 2 else 0.80
            else:
                owner_conf = 0.75 if len(owners[0]["name"].split()) >= 2 else 0.50
        else:
            owner_conf = 0.0

        # Dynamic Survey & Location Confidence
        survey_conf = 0.0
        if survey_no:
            survey_conf += 0.60
        if village or taluk or district:
            survey_conf += 0.20
        if boundaries:
            survey_conf += 0.15
        if flat_no or plot_no:
            survey_conf = max(survey_conf, 0.70)
        survey_conf = min(0.98, survey_conf)

        # Dynamic Area Confidence
        area_conf = 0.0
        if carpet_sqft and super_sqft:
            area_conf = 0.96
        elif carpet_sqft or super_sqft or plot_sqft:
            area_conf = 0.90
        elif raw_area_str:
            area_conf = 0.70

        # Dynamic Date & Registration Confidence
        date_conf = 0.0
        if date_iso and doc_number:
            date_conf = 0.96
        elif date_iso or doc_number:
            date_conf = 0.70
        elif date_raw_str:
            date_conf = 0.50

        # Dynamic Encumbrance Confidence
        enc_conf = 0.95 if encumbrances else 0.40

        if is_degraded:
            scale = max(0.2, ocr_confidence) if ocr_confidence is not None else 0.60
            owner_conf = min(owner_conf * scale, 0.65)
            survey_conf = min(survey_conf * scale, 0.60)
            area_conf = min(area_conf * scale, 0.60)
            date_conf = min(date_conf * scale, 0.65)
            enc_conf = min(enc_conf * scale, 0.60)

        # Dynamic Suggested Resolution
        missing_fields = []
        if owner_conf < 0.7: missing_fields.append("transacting parties/owners")
        if survey_conf < 0.7: missing_fields.append("survey/schedule number")
        if area_conf < 0.7 and resolved_doc_type not in ("ENCUMBRANCE_CERTIFICATE", "KHATA_CERTIFICATE"):
            missing_fields.append("area measurements")
        if date_conf < 0.7: missing_fields.append("registration dates/SRO details")

        suggested_resolution = None
        if is_degraded or missing_fields:
            suggested_resolution = (
                f"Document exhibited degradation or missing fields ({', '.join(missing_fields) if missing_fields else 'low visual contrast'}). "
                f"Manual ops verification required against physical deed records."
            )

        # 9. Dynamic 3-Paragraph Plain English Summary
        # Paragraph 1: Legal context, parties, location
        parties_desc = ""
        if len(owners) >= 2:
            parties_desc = f"executed between {owners[1]['name']} (Vendor/Grantor) and {owners[0]['name']} (Purchaser/Grantee)"
        elif len(owners) == 1:
            parties_desc = f"in favour of {owners[0]['name']}"
        else:
            parties_desc = "with parties unspecified or illegible in the scan"

        location_desc = []
        if flat_no: location_desc.append(f"Unit/Flat {flat_no}")
        if survey_no: location_desc.append(f"Survey No. {survey_no}")
        if village: location_desc.append(f"{village} Village")
        if taluk: location_desc.append(f"{taluk} Taluk")
        loc_str = ", ".join(location_desc) if location_desc else "location unrecorded in available text"

        p1 = (
            f"Paragraph 1: This legal instrument is a registered {resolved_doc_type.replace('_', ' ').title()} "
            f"{parties_desc}. The schedule property identifies as {loc_str}."
        )

        # Paragraph 2: Financials & dimensions
        fin_parts = []
        if sale_consideration: fin_parts.append(f"consideration of INR {sale_consideration:,.0f}")
        if stamp_duty: fin_parts.append(f"stamp duty of INR {stamp_duty:,.0f}")
        if carpet_sqft: fin_parts.append(f"carpet area of {carpet_sqft:,.0f} sq.ft")
        if super_sqft: fin_parts.append(f"super built-up area of {super_sqft:,.0f} sq.ft")
        if doc_number: fin_parts.append(f"registered under document #{doc_number}")
        if sro_office: fin_parts.append(f"at {sro_office}")
        fin_str = ", accompanied by ".join(fin_parts) if fin_parts else "financial and area metrics not specified in the extracted text"

        p2 = f"Paragraph 2: The conveyance records {fin_str}."

        # Paragraph 3: Encumbrances & title
        has_active_enc = any(e.get("encumbrance_type") not in ("NONE", None) and not e.get("is_cleared") for e in encumbrances)
        if has_active_enc:
            active_encs = [f"{e['holder_name'] or 'lender'} (INR {e['amount']:,.0f})" for e in encumbrances if e.get('amount')]
            p3 = f"Paragraph 3: Encumbrance audit identifies active recorded charges: {', '.join(active_encs) if active_encs else 'unspecified charge amount'}. Title clearance verification advised."
        else:
            p3 = "Paragraph 3: The instrument covenants clear title with zero prior liens, adverse charges, or outstanding encumbrances declared."

        ai_summary = f"{p1}\n\n{p2}\n\n{p3}"

        # Detect regional Indic script & language
        kannada_count = len(re.findall(r"[\u0C80-\u0CFF]", text))
        devanagari_count = len(re.findall(r"[\u0900-\u097F]", text))
        telugu_count = len(re.findall(r"[\u0C00-\u0C7F]", text))
        tamil_count = len(re.findall(r"[\u0B80-\u0BFF]", text))

        is_reg = False
        reg_lang = None
        if kannada_count > 5:
            is_reg = True
            reg_lang = "Kannada"
        elif devanagari_count > 5:
            is_reg = True
            reg_lang = "Marathi" if ("खरेदीखत" in text or "दस्तऐवज" in text or "गट नंबर" in text or "गट क्र" in text or "महाराष्ट्र" in text or "पुणे" in text or "हवेली" in text) else "Hindi"

        elif telugu_count > 5:
            is_reg = True
            reg_lang = "Telugu"
        elif tamil_count > 5:
            is_reg = True
            reg_lang = "Tamil"

        return {
            "document_type": resolved_doc_type,
            "owners": owners,
            "survey_number": {
                "survey_no": survey_no,
                "hissa_no": hissa_no,
                "katha_no": katha_no,
                "plot_no": plot_no,
                "flat_no": flat_no,
                "building_name": None,
                "village": village,
                "hobli": hobli,
                "taluk": taluk,
                "district": district,
                "state": state,
                "boundaries": boundaries,
            },
            "area": {
                "carpet_area_sqft": carpet_sqft,
                "super_built_up_sqft": super_sqft,
                "plot_area_sqft": plot_sqft,
                "raw_area_text": raw_area_str,
                "unit": "SQFT",
            },
            "dates": dates,
            "encumbrances": encumbrances,
            "sale_consideration_inr": sale_consideration,
            "market_guidance_value_inr": None,
            "stamp_duty_paid_inr": stamp_duty,
            "registration_fee_paid_inr": reg_fee,
            "field_confidence": {
                "owner": round(owner_conf, 2),
                "survey_no": round(survey_conf, 2),
                "area": round(area_conf, 2),
                "dates": round(date_conf, 2),
                "encumbrances": round(enc_conf, 2),
                "ocr_quality": round(ocr_confidence, 2) if ocr_confidence is not None else (0.55 if is_degraded else 0.95),
            },
            "suggested_resolution": suggested_resolution,
            "is_regional_script": is_reg,
            "regional_language": reg_lang,
            "ai_summary_plain_english": ai_summary,
        }


dee_gateway = AiGatewayClient()

