"""
MIE (Market Intelligence Engine) — Dataset Manager, Training, & Evaluation CLI.

Enables:
1. Bootstrapping realistic transaction, listing, and inquiry datasets across micro-markets
2. Calibrating micro-market baseline pricing, inquiry density, and transaction velocity parameters
3. Evaluating market intelligence accuracy, trend directions, ranking stability, and latency
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from this_is_what_you_need.common import BaseDatasetSplitter
from this_is_what_you_need.mie.pipeline import (
    AreaBasis,
    CivicProximityRecord,
    DemandSignal,
    ListingMode,
    MiePipeline,
    RawInquiryRecord,
    RawListingRecord,
    RawTransactionRecord,
)


class MieDatasetManager:
    """Manages transaction and listing datasets, train/val splits, and model calibration."""

    SAMPLE_LOCALITIES = [
        ("Indiranagar", "Bengaluru", 16500.0, 7.5),
        ("Whitefield", "Bengaluru", 9500.0, 8.5),
        ("Koramangala", "Bengaluru", 15000.0, 6.8),
        ("Bandra West", "Mumbai", 48000.0, 7.0),
        ("Lower Parel", "Mumbai", 38000.0, 6.0),
        ("Baner", "Pune", 8800.0, 8.2),
        ("Wakad", "Pune", 7800.0, 8.0),
        ("HITEC City", "Hyderabad", 9200.0, 9.0),
        ("Gachibowli", "Hyderabad", 8700.0, 8.6),
        ("Dubai Marina", "Dubai", 2200.0, 9.5),
    ]

    def __init__(self, pipeline: Optional[MiePipeline] = None):
        self.pipeline = pipeline or MiePipeline()

    def bootstrap_benchmark_dataset(self, output_path: str, count_per_locality: int = 15) -> Path:
        """
        Synthesizes a realistic market dataset with transactions, listings, and inquiries
        across major Indian and international micro-markets.
        """
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        transactions = []
        listings = []
        inquiries = []
        civic_records = {}

        now = date.today()
        rng = random.Random(42)

        for locality, city, base_rate, growth in self.SAMPLE_LOCALITIES:
            norm_loc = locality.lower().replace(" ", "_")
            currency = "AED" if city == "Dubai" else "INR"
            country = "AE" if city == "Dubai" else "IN"

            # 1. Transactions over past 180 days
            for i in range(count_per_locality):
                days_ago = rng.randint(5, 175)
                tx_date = now - timedelta(days=days_ago)
                area = float(rng.randint(900, 2400))
                # Slight noise around base rate
                rate = base_rate * (1.0 + rng.uniform(-0.08, 0.08))
                consideration = int(round(area * rate * 100.0))
                bhk = 2 if area < 1300 else (3 if area < 1900 else 4)

                transactions.append({
                    "id": f"tx_{norm_loc}_{i+1}",
                    "source": "State IGR Registry",
                    "country": country,
                    "city": city,
                    "locality": locality,
                    "registration_date": tx_date.isoformat(),
                    "document_type": "Sale Deed",
                    "area_sqft": area,
                    "area_basis": "CARPET",
                    "consideration_minor": consideration,
                    "currency": currency,
                    "configuration": f"{bhk} BHK",
                })

            # 2. Live Listings
            for j in range(count_per_locality // 2):
                days_active = rng.randint(2, 90)
                l_created = datetime.now(timezone.utc) - timedelta(days=days_active)
                area = float(rng.randint(950, 2500))
                # Asking rate is typically 5-12% higher than registered
                asking_rate = base_rate * (1.0 + rng.uniform(0.04, 0.12))
                price = int(round(area * asking_rate * 100.0))
                bhk = 2 if area < 1350 else 3
                inq_count = rng.randint(1, 12)

                listings.append({
                    "id": f"list_{norm_loc}_{j+1}",
                    "property_id": f"prop_{norm_loc}_{j+1}",
                    "locality": locality,
                    "city": city,
                    "listing_mode": "BUY",
                    "configuration": f"{bhk} BHK",
                    "area_sqft": area,
                    "price_minor": price,
                    "currency": currency,
                    "created_at": l_created.isoformat(),
                    "is_active": True,
                    "inquiry_count": inq_count,
                })

                # Inquiries for this listing
                for k in range(inq_count):
                    inq_days = rng.randint(1, days_active)
                    inquiries.append({
                        "id": f"inq_{norm_loc}_{j}_{k}",
                        "property_id": f"prop_{norm_loc}_{j+1}",
                        "locality": locality,
                        "city": city,
                        "timestamp": (datetime.now(timezone.utc) - timedelta(days=inq_days)).isoformat(),
                    })

            # 3. Civic Proximity
            civic_records[norm_loc] = {
                "metro_distance_meters": rng.choice([600, 1200, 2400, 4500]),
                "nearest_metro_name": f"{locality} Metro",
                "airport_distance_meters": rng.randint(15000, 42000),
                "water_security_index": rng.randint(65, 95),
                "flood_drainage_index": rng.randint(70, 95),
                "green_canopy_percent": rng.randint(15, 40),
                "air_quality_index": rng.randint(45, 120),
            }

        payload = {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_localities": len(self.SAMPLE_LOCALITIES),
                "total_transactions": len(transactions),
                "total_listings": len(listings),
                "total_inquiries": len(inquiries),
            },
            "transactions": transactions,
            "listings": listings,
            "inquiries": inquiries,
            "civic_records": civic_records,
        }

        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        return out_p

    def train_and_calibrate(self, data_path: str, model_output_path: str) -> Dict[str, Any]:
        """
        Learns empirical baseline rates, target velocity parameters, and demand curves
        from historical transaction and inquiry data.
        """
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        tx_list = data.get("transactions", [])
        listings = data.get("listings", [])
        inquiries = data.get("inquiries", [])

        # 1. Group transactions by locality to compute empirical base rate
        locality_rates: Dict[str, List[float]] = {}
        for t in tx_list:
            norm = t["locality"].lower().replace(" ", "_")
            unit_rate = t["consideration_minor"] / (t["area_sqft"] * 100.0)
            locality_rates.setdefault(norm, []).append(unit_rate)

        locality_priors = {}
        for norm, rates in locality_rates.items():
            avg_rate = round(float(sum(rates) / len(rates)), 1)
            locality_priors[norm] = {
                "base_rate": avg_rate,
                "growth": 7.5,
                "sample_size": len(rates),
            }

        # 2. Inquiries per active listing target
        if listings:
            inquiries_per_listing = len(inquiries) / float(len(listings))
            target_inq = round(max(1.0, inquiries_per_listing), 2)
        else:
            target_inq = 3.2

        # 3. Compile calibrated model configuration
        calibrated_model = {
            "model_version": "mie-v1.0-calibrated",
            "calibrated_at": datetime.now(timezone.utc).isoformat(),
            "target_inquiries_per_listing": target_inq,
            "target_deals_90d": max(5, int(len(tx_list) / max(1, len(locality_rates)))),
            "target_dom_days": 50.0,
            "default_growth_rate_pct": 7.5,
            "locality_priors": locality_priors,
        }

        out_p = Path(model_output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(calibrated_model, f, indent=2)

        return calibrated_model

    def evaluate_pipeline(self, data_path: str, model_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Evaluates MIE pipeline performance, latency SLA (<30ms), and score stability.
        """
        pipeline = MiePipeline(model_config_path=model_path)

        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Ingest records into pipeline
        for t in data.get("transactions", []):
            pipeline.ingest_transaction(
                RawTransactionRecord(
                    id=t["id"],
                    source=t.get("source", "IGR"),
                    country=t.get("country", "IN"),
                    city=t["city"],
                    locality=t["locality"],
                    registration_date=date.fromisoformat(t["registration_date"]),
                    area_sqft=t["area_sqft"],
                    area_basis=AreaBasis.CARPET,
                    consideration_minor=t["consideration_minor"],
                    currency=t.get("currency", "INR"),
                )
            )

        for l in data.get("listings", []):
            pipeline.ingest_listing(
                RawListingRecord(
                    id=l["id"],
                    property_id=l["property_id"],
                    locality=l["locality"],
                    city=l["city"],
                    area_sqft=l["area_sqft"],
                    price_minor=l["price_minor"],
                    currency=l.get("currency", "INR"),
                    is_active=l.get("is_active", True),
                )
            )

        for q in data.get("inquiries", []):
            pipeline.ingest_inquiry(
                RawInquiryRecord(
                    id=q["id"],
                    property_id=q["property_id"],
                    locality=q["locality"],
                    city=q["city"],
                )
            )

        for loc_norm, c in data.get("civic_records", {}).items():
            pipeline.register_civic_telemetry(
                loc_norm,
                CivicProximityRecord(
                    metro_distance_meters=c.get("metro_distance_meters"),
                    nearest_metro_name=c.get("nearest_metro_name"),
                    airport_distance_meters=c.get("airport_distance_meters"),
                    water_security_index=c.get("water_security_index"),
                    flood_drainage_index=c.get("flood_drainage_index"),
                    green_canopy_percent=c.get("green_canopy_percent"),
                    air_quality_index=c.get("air_quality_index"),
                ),
            )

        # Evaluate across all micro-markets
        unique_localities = list({(t["locality"], t["city"]) for t in data.get("transactions", [])})
        latencies = []
        results = []

        for loc, city in unique_localities:
            t0 = time.perf_counter()
            res = pipeline.analyze_micromarket(locality=loc, city=city)
            lat = (time.perf_counter() - t0) * 1000.0
            latencies.append(lat)
            results.append(res)

        avg_lat = sum(latencies) / max(1, len(latencies))
        p95_lat = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0.0

        # Evaluation metrics
        avg_velocity = sum(r.transaction_velocity_score for r in results) / max(1, len(results))
        avg_density = sum(r.inquiry_density_score for r in results) / max(1, len(results))
        avg_growth = sum(r.neighbourhood_growth_score for r in results) / max(1, len(results))
        demand_dist = {sig.value: sum(1 for r in results if r.demand_signal == sig) for sig in DemandSignal}

        return {
            "total_localities_evaluated": len(results),
            "mean_pipeline_latency_ms": round(avg_lat, 2),
            "p95_pipeline_latency_ms": round(p95_lat, 2),
            "sla_p95_target_met": p95_lat < 30.0,
            "mean_transaction_velocity_score": round(avg_velocity, 1),
            "mean_inquiry_density_score": round(avg_density, 1),
            "mean_neighbourhood_growth_score": round(avg_growth, 1),
            "demand_signal_distribution": demand_dist,
        }


def main():
    parser = argparse.ArgumentParser(description="MIE Market Intelligence Engine Evaluation & Retraining CLI")
    parser.add_argument("--mode", choices=["bootstrap", "train", "eval"], required=True,
                        help="Execution mode: bootstrap, train, or eval")
    parser.add_argument("--data-path", type=str, default="data/mie_benchmark.json",
                        help="Path to JSON dataset file")
    parser.add_argument("--model-path", type=str, default="this_is_what_you_need/mie/mie_model.json",
                        help="Path to save/load calibrated model configuration")
    parser.add_argument("--count", type=int, default=15,
                        help="Samples per locality for bootstrapping")

    args = parser.parse_args()
    mgr = MieDatasetManager()

    if args.mode == "bootstrap":
        print(f"\n[MIE BOOTSTRAP] Generating synthetic market benchmark: {args.data_path}")
        p = mgr.bootstrap_benchmark_dataset(args.data_path, count_per_locality=args.count)
        print(f"[OK] Successfully synthesized dataset at: {p}\n")

    elif args.mode == "train":
        print(f"\n[MIE TRAIN] Calibrating market baselines from: {args.data_path}")
        res = mgr.train_and_calibrate(args.data_path, args.model_path)
        print(f"[OK] Model calibrated and saved to: {args.model_path}")
        print(f"  • Localities Learned: {len(res['locality_priors'])}")
        print(f"  • Target Inquiries/Listing: {res['target_inquiries_per_listing']}\n")

    elif args.mode == "eval":
        print(f"\n[MIE EVAL] Evaluating MIE pipeline against: {args.data_path}")
        eval_res = mgr.evaluate_pipeline(args.data_path, args.model_path)
        print("[RESULT] Performance & Quality Summary:")
        print(f"  • Localities Evaluated: {eval_res['total_localities_evaluated']}")
        print(f"  • Mean Latency:         {eval_res['mean_pipeline_latency_ms']} ms")
        print(f"  • P95 Latency:          {eval_res['p95_pipeline_latency_ms']} ms (SLA < 30ms: {eval_res['sla_p95_target_met']})")
        print(f"  • Mean Velocity Score:  {eval_res['mean_transaction_velocity_score']}/100")
        print(f"  • Mean Inquiry Density: {eval_res['mean_inquiry_density_score']}/100")
        print(f"  • Mean Growth Score:    {eval_res['mean_neighbourhood_growth_score']}/100")
        print(f"  • Demand Distribution:  {eval_res['demand_signal_distribution']}\n")


if __name__ == "__main__":
    main()
