"""
VIE (Valuation Intelligence Engine) — Training & Evaluation CLI.

Enables:
1. Evaluation of AVM accuracy against ±15% Tier-1 micro-market target
2. Bootstrapping synthetic/benchmark datasets for cold-start markets
3. Exporting retraining batches for Kubeflow/Metaflow pipeline (§12.3)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from pipelines.vie.avm_engine import AvmCoreEngine
from pipelines.vie.dataset_manager import VieDatasetManager
from pipelines.vie.feedback_loop import VieLearningLoop
from pipelines.vie.models import VieFeatureVector


def run_evaluation(samples_count: int = 200, seed: int = 42) -> Dict[str, Any]:
    """
    Evaluates core AVM model accuracy against ground-truth benchmarks.
    Verifies that ±15% accuracy target on Tier-1 micro-markets is satisfied.
    """
    print(f"\n=======================================================")
    print(f" VIE / AVM Model Evaluation — Tier-1 Micro-Markets")
    print(f"=======================================================")

    avm = AvmCoreEngine()
    samples = VieDatasetManager.bootstrap_tier1_benchmark_dataset(count=samples_count, seed=seed)

    errors = []
    latencies = []
    within_15_count = 0
    within_10_count = 0

    for s in samples:
        f_dict = s["features"]
        vec = VieFeatureVector(**f_dict)
        pred = avm.predict(vec)

        gt = s["ground_truth_paise"]
        pred_val = pred.estimate_paise

        err = abs(gt - pred_val) / float(gt) * 100.0
        errors.append(err)
        latencies.append(pred.inference_latency_ms)

        if err <= 15.0:
            within_15_count += 1
        if err <= 10.0:
            within_10_count += 1

    total = len(samples)
    mape = sum(errors) / total
    ratio_15 = (within_15_count / total) * 100.0
    ratio_10 = (within_10_count / total) * 100.0
    p95_latency = sorted(latencies)[int(total * 0.95)]
    avg_latency = sum(latencies) / total

    print(f"Total Evaluated Properties : {total}")
    print(f"Mean Absolute Pct Error   : {mape:.2f}%")
    print(f"Within ±15% Accuracy Ratio : {ratio_15:.1f}% (Target: >= 85%)")
    print(f"Within ±10% Accuracy Ratio : {ratio_10:.1f}%")
    print(f"P95 Inference Latency     : {p95_latency:.3f} ms (Target: < 60 ms)")
    print(f"Average Inference Latency : {avg_latency:.3f} ms")

    status = "PASSED" if ratio_15 >= 85.0 and p95_latency < 60.0 else "NEEDS_TUNING"
    print(f"Verification Status       : [{status}]")
    print(f"=======================================================\n")

    return {
        "status": status,
        "total_samples": total,
        "mape": round(mape, 2),
        "within_15_ratio": round(ratio_15, 2),
        "within_10_ratio": round(ratio_10, 2),
        "p95_latency_ms": round(p95_latency, 3),
        "avg_latency_ms": round(avg_latency, 3),
    }


def run_bootstrap(out_dir: str, count: int = 250):
    """Bootstraps benchmark dataset to output JSON."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    samples = VieDatasetManager.bootstrap_tier1_benchmark_dataset(count=count)
    target_file = out_path / "tier1_benchmark_dataset.json"
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=2)
    print(f"Successfully bootstrapped {count} benchmark samples to: {target_file}")


def main():
    parser = argparse.ArgumentParser(description="VIE / AVM Training & Evaluation Tool")
    parser.add_argument("--mode", choices=["eval", "bootstrap"], default="eval")
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--out-dir", type=str, default="vie_output")
    args = parser.parse_args()

    if args.mode == "eval":
        run_evaluation(samples_count=args.count)
    elif args.mode == "bootstrap":
        run_bootstrap(out_dir=args.out_dir, count=args.count)


if __name__ == "__main__":
    main()
