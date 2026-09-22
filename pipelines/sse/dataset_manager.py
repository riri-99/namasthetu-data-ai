"""
SSE (Semantic Search Engine) — Dataset Manager.

Implements:
- Benchmark corpus generator across Tier-1 micro-markets
- Multi-context PIP synthesis (Property + PAM + DEE + VIE + MIE)
- Golden query test suites for latency and relevance benchmarking
"""

from __future__ import annotations

import random
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from pipelines.sse.models import (
    PipSearchDocument,
    PrismaFurnishingStatus,
    PrismaListingStatus,
    PrismaPropertyType,
)


class SseDatasetManager:
    """
    Manages benchmark property corpora and standard evaluation query suites.
    """

    MICRO_MARKET_ANCHORS = [
        ("Indiranagar", "Bengaluru", "Prestige Boulevard", "Prestige Group", 16500),
        ("Whitefield", "Bengaluru", "Sobha Dream Acres", "Sobha Limited", 8500),
        ("Koramangala", "Bengaluru", "Raheja Residency", "K Raheja Corp", 15000),
        ("HSR Layout", "Bengaluru", "Purva Vantage", "Puravankara", 11000),
        ("Hebbal", "Bengaluru", "Godrej Woodsman Estate", "Godrej Properties", 10500),
        ("Bandra West", "Mumbai", "Rustomjee Seasons", "Rustomjee", 48000),
        ("Powai", "Mumbai", "Hiranandani Gardens", "Hiranandani", 23000),
        ("Golf Course Road", "Gurgaon", "DLF The Camellias", "DLF", 22000),
        ("Gachibowli", "Hyderabad", "My Home Bhooja", "My Home Group", 9200),
        ("Koregaon Park", "Pune", "Marvel Basilo", "Marvel Realtors", 14500),
    ]

    BENCHMARK_QUERIES = [
        # Lexical queries
        "3 BHK in Whitefield with lift and parking",
        "Luxury apartment in Indiranagar Bengaluru",
        "2 BHK near Metro station",
        # Qualitative / Semantic queries
        "Peaceful spacious penthouse with garden view for family",
        "Quiet sunny home near IT tech parks with good amenities",
        # Investor queries (Cross-Pipeline VIE)
        "Undervalued property with high rental yield for investment",
        "Best ROI apartment below market valuation",
        # Condition queries (Cross-Pipeline PAM)
        "Well-maintained pristine home with zero seepage",
        "Renovated apartment with high structural quality",
        # Legal queries (Cross-Pipeline DEE)
        "Clear title encumbrance-free RERA approved flat",
    ]

    @classmethod
    def bootstrap_benchmark_corpus(cls, count: int = 50, seed: int = 42) -> List[PipSearchDocument]:
        """
        Generates realistic synthetic PIP documents cross-linked with PAM, DEE, and VIE signals.
        """
        rng = random.Random(seed)
        now = datetime.now(timezone.utc)
        docs: List[PipSearchDocument] = []

        for i in range(count):
            loc, city, society, builder, base_rate = rng.choice(cls.MICRO_MARKET_ANCHORS)
            prop_type = rng.choice([PrismaPropertyType.APARTMENT, PrismaPropertyType.APARTMENT, PrismaPropertyType.VILLA])
            area = rng.randint(950, 3200)
            bhk = 2 if area < 1300 else (3 if area < 2300 else 4)
            baths = max(1, bhk + rng.choice([0, 1]))
            floor = rng.randint(1, 18)
            total_floors = max(floor, rng.randint(6, 22))
            furn = rng.choice([PrismaFurnishingStatus.UNFURNISHED, PrismaFurnishingStatus.SEMI_FURNISHED, PrismaFurnishingStatus.FULLY_FURNISHED])
            age = round(rng.uniform(0.5, 12.0), 1)

            # Price in paise
            rate = base_rate * rng.uniform(0.92, 1.10)
            price_inr = area * rate
            price_paise = int(round(price_inr * 100.0))

            # Cross-pipeline PAM signals
            pam_score = rng.randint(65, 98)
            seepage = True if pam_score < 75 and rng.random() < 0.35 else False

            # Cross-pipeline DEE signals
            deed_verified = True if rng.random() < 0.90 else False
            active_liens = True if not deed_verified and rng.random() < 0.30 else False

            # Cross-pipeline VIE signals
            avm_diff = round(rng.uniform(-7.5, 6.0), 1)
            market_pos = "BELOW_MARKET" if avm_diff < -2.0 else ("ABOVE_MARKET" if avm_diff > 2.0 else "ALIGNED")
            yield_pct = round(rng.uniform(3.2, 5.4), 2)

            amenities_pool = ["SWIMMING_POOL", "GYM", "CLUBHOUSE", "CHILDRENS_PLAY_AREA", "POWER_BACKUP", "SECURITY_24X7", "JOGGING_TRACK"]
            selected_amenities = rng.sample(amenities_pool, rng.randint(3, len(amenities_pool)))

            doc = PipSearchDocument(
                property_id=f"prop_sse_{i+1:03d}",
                listing_id=f"list_sse_{i+1:03d}",
                public_id=f"pip_pub_{i+1:03d}",
                title=f"{bhk} BHK {prop_type.value.title()} at {society}",
                description=f"Spacious and bright {bhk} BHK residential unit located at {society}, {loc}. Thoughtfully designed with contemporary finishes.",
                locality=loc,
                city=city,
                society_name=society,
                builder_name=builder,
                property_type=prop_type,
                configuration=f"{bhk}BHK",
                bhk_count=bhk,
                bathrooms_count=baths,
                carpet_area_sqft=float(area),
                super_built_up_area_sqft=round(area * 1.25, 1),
                floor_number=floor,
                total_floors=total_floors,
                age_years=age,
                furnishing=furn,
                parking_count=rng.choice([1, 2]),
                has_lift=True,
                amenities=selected_amenities,
                listing_price_minor=price_paise,
                owner_type="INDIVIDUAL",
                status=PrismaListingStatus.ACTIVE,
                listed_at=now - timedelta(days=rng.randint(1, 90)),
                # PAM signals
                inspection_id=f"insp_sse_{i+1:03d}",
                inspection_score_overall=pam_score,
                inspection_score_structural=min(100, pam_score + rng.randint(-3, 3)),
                seepage_detected=seepage,
                inspected_at=now - timedelta(days=rng.randint(5, 60)),
                # DEE signals
                deed_verified=deed_verified,
                active_liens=active_liens,
                rera_registration_number=f"PRM/KA/RERA/{rng.randint(1000, 9999)}",
                # VIE signals
                avm_estimate_minor=int(round(price_paise * (1.0 - (avm_diff / 100.0)))),
                market_position=market_pos,
                avm_difference_pct=avm_diff,
                gross_rental_yield_pct=yield_pct,
                demand_signal="WARM" if rng.random() < 0.6 else ("HOT" if rng.random() < 0.8 else "COLD"),
            )
            docs.append(doc)

        return docs


sse_dataset_manager = SseDatasetManager()
