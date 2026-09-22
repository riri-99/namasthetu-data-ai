"""
VIE (Valuation Intelligence Engine) — Dataset Manager, Model Training, & Evaluation CLI.

Enables:
1. Bootstrapping realistic Indian real-estate transaction datasets with micro-market variance
2. Training the 13-feature regularized Ridge/LightGBM AVM core model
3. Evaluating valuation accuracy: MAPE, MdAPE, PE10, PE20, and P95 latency
4. Continuous learning updates for micro-market locality rates and yield curves
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from this_is_what_you_need.common import BaseDatasetSplitter
from this_is_what_you_need.vie.pipeline import (
    AvmCoreEngine,
    DemandSignal,
    MarketPosition,
    VieFeatureVector,
    ViePipeline,
)


class VieDatasetManager:
    """Manages transaction datasets, AVM training loops, and valuation accuracy benchmarks."""

    LOCALITY_PROFILES: Dict[str, Dict[str, Any]] = {
        "Whitefield": {"base_rate": 8500.0, "growth": 72.0, "velocity": 78.0, "inquiry": 75.0},
        "Indiranagar": {"base_rate": 16500.0, "growth": 65.0, "velocity": 60.0, "inquiry": 70.0},
        "Koramangala": {"base_rate": 15000.0, "growth": 68.0, "velocity": 65.0, "inquiry": 72.0},
        "HSR Layout": {"base_rate": 11000.0, "growth": 75.0, "velocity": 80.0, "inquiry": 78.0},
        "Hebbal": {"base_rate": 10500.0, "growth": 70.0, "velocity": 70.0, "inquiry": 68.0},
        "Electronic City": {"base_rate": 6200.0, "growth": 60.0, "velocity": 65.0, "inquiry": 62.0},
    }

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = Path(data_path) if data_path else None
        self.pipeline = ViePipeline()

    def bootstrap_benchmark_dataset(self, output_file: str, count: int = 60) -> Path:
        """
        Generates realistic multi-attribute real-estate transaction records with canonical 13 features
        and ground-truth transaction sale prices.
        """
        out_p = Path(output_file)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        rng = random.Random(42)
        records: List[Dict[str, Any]] = []

        localities = list(self.LOCALITY_PROFILES.keys())

        for i in range(count):
            loc_name = localities[i % len(localities)]
            prof = self.LOCALITY_PROFILES[loc_name]

            bhk = rng.choice([1, 2, 3, 4])
            area_sqft = float(rng.randint(550, 950) if bhk == 1 else (
                rng.randint(950, 1400) if bhk == 2 else (
                    rng.randint(1400, 2200) if bhk == 3 else rng.randint(2200, 3600)
                )
            ))
            bathrooms = min(bhk + 1, rng.choice([bhk, bhk + 1]))
            total_floors = rng.randint(4, 25)
            floor_num = rng.randint(1, total_floors)
            furn_status = rng.choice([0, 1, 2])
            age_years = round(rng.uniform(0.5, 18.0), 1)
            condition_score = round(rng.uniform(70.0, 98.0), 1)
            seepage = 1 if condition_score < 75.0 and rng.random() < 0.6 else 0

            # Base valuation with realistic noise
            base_sqft = prof["base_rate"] * (1.0 + rng.uniform(-0.06, 0.06))
            inquiry_score = round(prof["inquiry"] + rng.uniform(-5.0, 5.0), 1)
            velocity_score = round(prof["velocity"] + rng.uniform(-5.0, 5.0), 1)
            growth_score = round(prof["growth"] + rng.uniform(-4.0, 4.0), 1)

            vec = VieFeatureVector(
                area_sqft=area_sqft,
                age_years=age_years,
                floor_number=floor_num,
                total_floors=total_floors,
                bhk_count=bhk,
                bathrooms_count=bathrooms,
                furnishing_status=furn_status,
                condition_score_overall=condition_score,
                seepage_detected=seepage,
                locality_price_per_sqft_base=base_sqft,
                inquiry_density_score=inquiry_score,
                transaction_velocity_score=velocity_score,
                neighbourhood_growth_score=growth_score,
            )

            # Ground truth calculation with non-linear factors
            true_price_inr = (
                area_sqft * base_sqft
                * (1.0 - (0.010 * min(age_years, 30.0)))
                * (1.0 + furn_status * 0.04)
                * (1.0 + (condition_score - 85.0) / 300.0)
                * (0.95 if seepage == 1 else 1.0)
                * (1.0 + rng.uniform(-0.03, 0.03))  # market micro-variance
            )
            true_price_paise = int(round(true_price_inr * 100.0))

            # Calculate realistic gross rental yield for bootstrap sample
            sample_yield = round(rng.uniform(3.8, 5.2), 2)

            records.append({
                "property_id": f"tx_prop_{i+1:04d}",
                "locality": loc_name,
                "city": "Bengaluru",
                "area_sqft": area_sqft,
                "bhk_count": bhk,
                "feature_vector": vec.model_dump(),
                "features_list": vec.to_feature_list(),
                "transacted_price_paise": true_price_paise,
                "transacted_price_inr": round(true_price_inr, 2),
                "rental_yield": sample_yield,
            })

        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)

        return out_p

    def train(
        self,
        dataset_path: str,
        model_save_path: Optional[str] = None,
        train_ratio: float = 0.80,
    ) -> Dict[str, Any]:
        """
        Trains AvmCoreEngine on transaction dataset, evaluating R2 score and saving weights.
        """
        data_p = Path(dataset_path)
        if not data_p.exists():
            raise FileNotFoundError(f"Dataset not found at {data_p}")

        with open(data_p, "r", encoding="utf-8") as f:
            records = json.load(f)

        splits = BaseDatasetSplitter.split(records, train_ratio=train_ratio, val_ratio=0.10, test_ratio=0.10)
        train_set = splits["train"]

        X_train = [r["features_list"] for r in train_set]
        y_train = [float(r["transacted_price_paise"]) for r in train_set]

        # Register transaction prices and yields into market registry
        for r in train_set:
            sqft_rate = (r["transacted_price_inr"] / max(1.0, r["area_sqft"]))
            self.pipeline.market_registry.register_transaction(
                r["locality"],
                sqft_rate,
                rental_yield=r.get("rental_yield"),
            )

        train_res = AvmCoreEngine.fit(X_train, y_train)

        target_model = model_save_path or str(Path(__file__).parent / "vie_model.json")
        AvmCoreEngine.save_model(target_model)
        train_res["model_saved_to"] = target_model
        train_res["val_count"] = len(splits["val"])
        train_res["test_count"] = len(splits["test"])
        return train_res

    def evaluate_dataset(
        self,
        dataset_path: str,
        model_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates valuation accuracy metrics on dataset:
        - MAPE (Mean Absolute Percentage Error)
        - MdAPE (Median Absolute Percentage Error)
        - PE10 (% within 10% error)
        - PE20 (% within 20% error)
        - RMSE (Root Mean Squared Error in INR)
        - Inference Latency (ms)
        """
        data_p = Path(dataset_path)
        if not data_p.exists():
            raise FileNotFoundError(f"Dataset not found at {data_p}")

        if model_path and Path(model_path).exists():
            AvmCoreEngine.load_model(model_path)

        with open(data_p, "r", encoding="utf-8") as f:
            records = json.load(f)

        percentage_errors = []
        squared_errors = []
        latencies_ms = []

        for r in records:
            vec = VieFeatureVector(**r["feature_vector"])
            gt_paise = float(r["transacted_price_paise"])

            start = time.perf_counter()
            pred = AvmCoreEngine.predict(vec)
            lat = (time.perf_counter() - start) * 1000.0
            latencies_ms.append(lat)

            est_paise = float(pred.estimate_paise)
            ape = abs(est_paise - gt_paise) / max(1.0, gt_paise) * 100.0
            percentage_errors.append(ape)

            diff_inr = (est_paise - gt_paise) / 100.0
            squared_errors.append(diff_inr ** 2)

        n = len(records)
        sorted_apes = sorted(percentage_errors)
        mape = round(sum(percentage_errors) / max(1, n), 2)
        mdape = round(sorted_apes[n // 2], 2) if n > 0 else 0.0
        pe10 = round(sum(1 for e in percentage_errors if e <= 10.0) / max(1, n) * 100.0, 1)
        pe20 = round(sum(1 for e in percentage_errors if e <= 20.0) / max(1, n) * 100.0, 1)
        rmse_inr = round(math.sqrt(sum(squared_errors) / max(1, n)), 2)
        avg_latency = round(sum(latencies_ms) / max(1, len(latencies_ms)), 3)

        return {
            "total_eval_samples": n,
            "mape_percentage": mape,
            "mdape_percentage": mdape,
            "pe10_percentage": pe10,
            "pe20_percentage": pe20,
            "rmse_inr": rmse_inr,
            "avg_latency_ms": avg_latency,
            "p95_latency_ms": round(sorted(latencies_ms)[int(len(latencies_ms) * 0.95)], 3) if latencies_ms else 0.0,
        }


def main():
    parser = argparse.ArgumentParser(description="VIE Training & Evaluation CLI")
    parser.add_argument("--mode", choices=["train", "eval", "bootstrap"], default="eval")
    parser.add_argument("--data-path", type=str, default="data/transactions.json")
    parser.add_argument("--model-path", type=str, default=None)
    parser.add_argument("--count", type=int, default=60)
    args = parser.parse_args()

    mgr = VieDatasetManager(args.data_path)

    if args.mode == "bootstrap":
        print(f"Bootstrapping {args.count} real-estate transaction records into {args.data_path}...")
        p = mgr.bootstrap_benchmark_dataset(args.data_path, count=args.count)
        print(f"Transactions dataset generated successfully at: {p}")

    elif args.mode == "train":
        print(f"Training AVM regression weights on {args.data_path}...")
        res = mgr.train(args.data_path, model_save_path=args.model_path)
        print(f"Training completed:\n{json.dumps(res, indent=2)}")

    elif args.mode == "eval":
        data_p = Path(args.data_path)
        if not data_p.exists():
            print(f"Dataset not found at {args.data_path}, bootstrapping benchmark dataset first...")
            mgr.bootstrap_benchmark_dataset(args.data_path, count=args.count)
        print(f"Evaluating AVM valuation accuracy on {args.data_path}...")
        metrics = mgr.evaluate_dataset(args.data_path, model_path=args.model_path)
        print(f"Valuation Accuracy Metrics:\n{json.dumps(metrics, indent=2)}")


if __name__ == "__main__":
    main()
