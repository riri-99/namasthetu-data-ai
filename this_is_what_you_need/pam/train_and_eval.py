"""
PAM (Photo Analysis Module) — Dataset Manager, Training, & Evaluation CLI.

Enables:
1. Dataset evaluation across real inspection image folders
2. Bootstrapping synthetic/pseudo-labeled benchmark datasets
3. Training dynamic room classification centroids and defect thresholds
4. Measuring classification accuracy, defect detection F1, and inference latency
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from this_is_what_you_need.common import BaseDatasetSplitter
from this_is_what_you_need.pam.pipeline import (
    DefectCategory,
    DefectSeverity,
    PamPipeline,
    PamVisionEngine,
    RoomCategory,
)


class PamDatasetManager:
    """Manages inspection photo discovery, train/val/test splits, bootstrapping, and model fitting."""

    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tiff"}

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir) if data_dir else None
        self.pipeline = PamPipeline()

    def discover_images(self, custom_dir: Optional[str] = None) -> List[Path]:
        root = Path(custom_dir) if custom_dir else self.data_dir
        if not root or not root.exists():
            return []
        images = []
        for ext in self.SUPPORTED_EXTENSIONS:
            images.extend(root.rglob(f"*{ext}"))
            images.extend(root.rglob(f"*{ext.upper()}"))
        return sorted(list(set(images)))

    def split_dataset(self, images: List[Path]) -> Dict[str, List[Path]]:
        return BaseDatasetSplitter.split(images)

    def bootstrap_benchmark_dataset(self, output_dir: str, count: int = 30) -> Path:
        """
        Synthesizes a labeled benchmark image dataset with known room categories,
        varied lighting tones, and localized defect patches.
        """
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        samples: List[Dict[str, Any]] = []
        categories = [
            (RoomCategory.LIVING_ROOM, (170, 150, 130), False),
            (RoomCategory.BATHROOM, (220, 225, 235), False),
            (RoomCategory.KITCHEN, (140, 130, 120), False),
            (RoomCategory.BALCONY, (145, 160, 185), False),
            (RoomCategory.MASTER_BEDROOM, (180, 140, 130), False),
            (RoomCategory.PARKING, (70, 70, 75), False),
            (RoomCategory.LIVING_ROOM, (175, 155, 135), True),  # with seepage
            (RoomCategory.BATHROOM, (215, 220, 230), True),  # with seepage
        ]

        for i in range(count):
            cat, base_color, has_defect = categories[i % len(categories)]
            # Add minor pixel tone variation
            r = max(0, min(255, base_color[0] + (i % 7) * 3 - 10))
            g = max(0, min(255, base_color[1] + (i % 5) * 3 - 8))
            b = max(0, min(255, base_color[2] + (i % 3) * 4 - 6))

            img = Image.new("RGB", (320, 240), color=(r, g, b))
            draw = ImageDraw.Draw(img)

            defect_drop = 0.0
            if has_defect:
                # Draw dark dampness/seepage patch
                draw.rectangle([180, 120, 280, 210], fill=(25, 25, 25))
                defect_drop = 65.0

            img_filename = f"photo_{i:03d}_{cat.value.lower()}{'_defect' if has_defect else ''}.jpg"
            img_file_path = out_path / img_filename
            img.save(img_file_path, format="JPEG", quality=90)

            samples.append({
                "image_file": img_filename,
                "image_path": str(img_file_path),
                "room_category": cat.value,
                "has_defect": has_defect,
                "defect_type": "seepage" if has_defect else None,
                "defect_drop": defect_drop,
            })

        manifest_path = out_path / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(samples, f, indent=2)

        return out_path

    def train(self, dataset_dir: str, model_save_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Trains dynamic room centroids and defect thresholds from a labeled manifest or image directory.
        """
        ds_path = Path(dataset_dir)
        manifest_path = ds_path / "manifest.json"

        training_samples: List[Dict[str, Any]] = []

        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                raw_samples = json.load(f)
            for item in raw_samples:
                img_file = ds_path / item.get("image_file", "")
                if not img_file.exists():
                    img_file = Path(item.get("image_path", ""))
                if img_file.exists():
                    with Image.open(img_file) as img:
                        feats = PamVisionEngine.extract_pixel_features(img.convert("RGB"))
                    training_samples.append({
                        "features": feats,
                        "category": item.get("room_category"),
                        "has_defect": item.get("has_defect", False),
                        "defect_drop": item.get("defect_drop", 0.0),
                    })
        else:
            # Discover images by subdirectory name
            images = self.discover_images(dataset_dir)
            for img_p in images:
                folder_name = img_p.parent.name.upper()
                with Image.open(img_p) as img:
                    feats = PamVisionEngine.extract_pixel_features(img.convert("RGB"))
                training_samples.append({
                    "features": feats,
                    "category": folder_name,
                })

        if not training_samples:
            raise ValueError(f"No valid labeled training samples found in {dataset_dir}")

        engine = PamVisionEngine()
        train_result = engine.fit(training_samples)

        save_target = model_save_path or str(Path(__file__).parent / "pam_model.json")
        engine.save_model(save_target)
        train_result["model_saved_to"] = save_target
        return train_result

    def evaluate_dataset(self, dataset_dir: str, model_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Evaluates PAM pipeline on labeled benchmark data.
        Returns accuracy, precision, recall, and average inference latency.
        """
        ds_path = Path(dataset_dir)
        manifest_path = ds_path / "manifest.json"

        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found at {manifest_path}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            samples = json.load(f)

        engine = PamVisionEngine(model_path=model_path)

        correct_rooms = 0
        tp_defect = 0
        fp_defect = 0
        fn_defect = 0
        tn_defect = 0
        latencies_ms = []

        per_class_stats: Dict[str, Dict[str, int]] = {}

        for item in samples:
            img_p = ds_path / item["image_file"]
            if not img_p.exists():
                img_p = Path(item["image_path"])

            start = time.perf_counter()
            with Image.open(img_p) as img:
                cat, conf, defects, fixtures = engine.analyze_image(img)
            latencies_ms.append((time.perf_counter() - start) * 1000.0)

            gt_cat = item["room_category"].upper()
            pred_cat = cat.value.upper()

            if gt_cat not in per_class_stats:
                per_class_stats[gt_cat] = {"tp": 0, "total": 0}
            per_class_stats[gt_cat]["total"] += 1

            if gt_cat == pred_cat:
                correct_rooms += 1
                per_class_stats[gt_cat]["tp"] += 1

            gt_has_defect = item.get("has_defect", False)
            pred_has_defect = len(defects) > 0

            if gt_has_defect and pred_has_defect:
                tp_defect += 1
            elif not gt_has_defect and pred_has_defect:
                fp_defect += 1
            elif gt_has_defect and not pred_has_defect:
                fn_defect += 1
            else:
                tn_defect += 1

        n = len(samples)
        accuracy = round(correct_rooms / max(1, n), 4)
        defect_prec = round(tp_defect / max(1, tp_defect + fp_defect), 4)
        defect_rec = round(tp_defect / max(1, tp_defect + fn_defect), 4)
        defect_f1 = round(2 * defect_prec * defect_rec / max(0.001, defect_prec + defect_rec), 4)
        avg_latency = round(sum(latencies_ms) / max(1, len(latencies_ms)), 2)

        return {
            "total_samples": n,
            "room_classification_accuracy": accuracy,
            "defect_precision": defect_prec,
            "defect_recall": defect_rec,
            "defect_f1_score": defect_f1,
            "avg_latency_ms": avg_latency,
            "per_class_breakdown": {
                k: f"{v['tp']}/{v['total']} ({v['tp']/max(1, v['total']) * 100:.1f}%)"
                for k, v in per_class_stats.items()
            },
        }


def main():
    parser = argparse.ArgumentParser(description="PAM Training & Evaluation CLI")
    parser.add_argument("--mode", choices=["train", "eval", "bootstrap"], default="eval")
    parser.add_argument("--data-dir", type=str, default="data/inspections")
    parser.add_argument("--model-path", type=str, default=None)
    parser.add_argument("--count", type=int, default=30)
    args = parser.parse_args()

    mgr = PamDatasetManager(args.data_dir)

    if args.mode == "bootstrap":
        print(f"Bootstrapping {args.count} benchmark photos into {args.data_dir}...")
        p = mgr.bootstrap_benchmark_dataset(args.data_dir, count=args.count)
        print(f"Dataset generated successfully at: {p}")

    elif args.mode == "train":
        print(f"Training PAM dynamic model on {args.data_dir}...")
        res = mgr.train(args.data_dir, model_save_path=args.model_path)
        print(f"Training completed: {json.dumps(res, indent=2)}")

    elif args.mode == "eval":
        data_p = Path(args.data_dir)
        if not (data_p / "manifest.json").exists():
            print(f"Manifest not found in {args.data_dir}, bootstrapping benchmark dataset first...")
            mgr.bootstrap_benchmark_dataset(args.data_dir, count=args.count)
        print(f"Evaluating PAM pipeline on {args.data_dir}...")
        metrics = mgr.evaluate_dataset(args.data_dir, model_path=args.model_path)
        print(f"Evaluation Metrics:\n{json.dumps(metrics, indent=2)}")


if __name__ == "__main__":
    main()
