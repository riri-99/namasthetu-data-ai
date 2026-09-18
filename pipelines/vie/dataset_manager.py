"""
VIE (Valuation Intelligence Engine) — Dataset Manager.

Implements:
- Dataset discovery, ingestion, and deterministic splitting (train/val/test)
- Bootstrapping synthetic/benchmark datasets for Tier-1 micro-markets
- Feature normalization and LightGBM / Treelite training matrix preparation
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from vie.models import VieFeatureVector
from vie.avm_engine import AvmCoreEngine


class VieDatasetManager:
    """
    Manages valuation datasets, feature extraction, train/test splitting, and benchmarking.
    """

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir) if data_dir else None

    @staticmethod
    def split_dataset(
        records: List[Dict[str, Any]],
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        seed: int = 42,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Deterministically split records into train, validation, and test sets.
        """
        shuffled = list(records)
        rng = random.Random(seed)
        rng.shuffle(shuffled)

        n = len(shuffled)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)

        return {
            "train": shuffled[:n_train],
            "val": shuffled[n_train : n_train + n_val],
            "test": shuffled[n_train + n_val :],
        }

    @staticmethod
    def bootstrap_tier1_benchmark_dataset(count: int = 200, seed: int = 42) -> List[Dict[str, Any]]:
        """
        Generates benchmark training/evaluation samples across Tier-1 micro-markets.
        Enables testing and baseline model evaluation without external files.
        """
        rng = random.Random(seed)
        markets = [
            ("Indiranagar", "Bengaluru", 16500),
            ("Whitefield", "Bengaluru", 8500),
            ("Koramangala", "Bengaluru", 15000),
            ("HSR Layout", "Bengaluru", 11000),
            ("Bandra West", "Mumbai", 48000),
            ("Powai", "Mumbai", 23000),
            ("Worli", "Mumbai", 42000),
            ("Golf Course Road", "Gurgaon", 22000),
            ("Gachibowli", "Hyderabad", 9200),
            ("Koregaon Park", "Pune", 14500),
        ]

        samples = []
        for i in range(count):
            loc, city, base_rate = rng.choice(markets)
            area = rng.randint(800, 3200)
            bhk = 2 if area < 1300 else (3 if area < 2200 else 4)
            baths = max(1, bhk + rng.choice([-1, 0, 1]))
            floor = rng.randint(1, 20)
            total_floors = max(floor, rng.randint(4, 25))
            age = round(rng.uniform(0.5, 18.0), 1)
            furn = rng.choice([0, 1, 2])
            condition = round(rng.uniform(65.0, 98.0), 1)
            seepage = 1 if condition < 75 and rng.random() < 0.4 else 0

            vec = VieFeatureVector(
                area_sqft=float(area),
                age_years=age,
                floor_number=floor,
                total_floors=total_floors,
                bhk_count=bhk,
                bathrooms_count=baths,
                furnishing_status=furn,
                condition_score_overall=condition,
                seepage_detected=seepage,
                locality_price_per_sqft_base=float(base_rate),
                inquiry_density_score=round(rng.uniform(40.0, 85.0), 1),
                transaction_velocity_score=round(rng.uniform(40.0, 80.0), 1),
                neighbourhood_growth_score=round(rng.uniform(50.0, 90.0), 1),
            )

            # Ground truth pricing with small realistic market noise (±3%)
            market_noise = rng.uniform(0.97, 1.03)
            est_inr = area * base_rate * (1.0 + (furn * 0.04)) * (1.0 - (age * 0.008)) * market_noise
            ground_truth_paise = int(round(est_inr * 100.0))

            samples.append({
                "sample_id": f"sample_{loc.lower()}_{i+1}",
                "property_id": f"prop_bmk_{i+1}",
                "locality": loc,
                "city": city,
                "features": vec.model_dump(),
                "feature_list": vec.to_feature_list(),
                "ground_truth_paise": ground_truth_paise,
            })

        return samples


vie_dataset_manager = VieDatasetManager()
