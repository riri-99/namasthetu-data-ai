"""
PAM (Photo Analysis Module) — Dataset Manager & Retraining Bootstrapper.

Prepared for user drop-in photo datasets:
- Recursive discovery of image files (.jpg, .jpeg, .png, .webp, .heic, .tiff)
- Deterministic train/validation/test splitting
- Pseudo-label bootstrapping for unannotated inspection photo collections
- Export to CLIP classification JSONL and defect bounding-box detection formats
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pam.models import RoomCategory, DefectSeverity
from pam.pipeline import PamPipeline


class PamDatasetManager:
    """Manages raw photo datasets, pseudo-label generation, and retraining exports."""

    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tiff", ".tif"}

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir) if data_dir else None
        self.pipeline = PamPipeline()

    def discover_images(self, custom_dir: Optional[str] = None) -> List[Path]:
        """Recursively discover all supported image files."""
        root = Path(custom_dir) if custom_dir else self.data_dir
        if not root or not root.exists():
            return []

        images: List[Path] = []
        for ext in self.SUPPORTED_EXTENSIONS:
            images.extend(root.rglob(f"*{ext}"))
            images.extend(root.rglob(f"*{ext.upper()}"))

        return sorted(list(set(images)))

    def split_dataset(
        self,
        images: List[Path],
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        seed: int = 42,
    ) -> Dict[str, List[Path]]:
        """Deterministically split image paths into train, val, and test partitions."""
        shuffled = list(images)
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

    def bootstrap_unlabeled_photos(
        self,
        image_paths: List[Path],
        output_annotation_dir: str,
        confidence_threshold: float = 0.80,
    ) -> Dict[str, Any]:
        """
        Run inference over unannotated photos and save pseudo-label ground truth candidate JSONs.
        """
        out_dir = Path(output_annotation_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        bootstrapped_count = 0
        skipped_count = 0
        room_distribution: Dict[str, int] = {cat.value: 0 for cat in RoomCategory}
        defects_found_count = 0

        for img_path in image_paths:
            try:
                # Use parent directory name as room hint if available (e.g., photos/kitchen/01.jpg)
                hint = img_path.parent.name if img_path.parent.name in self.pipeline.vision_engine.INSPECTOR_HINT_MAP else None

                res = self.pipeline.analyze_photo(
                    image_input=str(img_path),
                    inspection_id=f"insp_bootstrap_{img_path.parent.name}",
                    photo_url=str(img_path),
                    photo_id=img_path.stem,
                    room_label_hint=hint,
                )

                if res.room_confidence >= confidence_threshold:
                    bootstrapped_count += 1
                    room_distribution[res.room_category.value] += 1
                    if res.has_defect:
                        defects_found_count += len(res.defects)

                    ann_payload = {
                        "image_file": img_path.name,
                        "image_path": str(img_path.resolve()),
                        "predicted_room_category": res.room_category.value,
                        "confidence": round(res.room_confidence, 4),
                        "has_defect": res.has_defect,
                        "primary_defect_type": res.defect_type,
                        "primary_defect_severity": res.defect_severity.value if res.defect_severity else None,
                        "defects": [d.model_dump() for d in res.defects],
                        "fixtures": [f.model_dump() for f in res.fixtures],
                        "condition_scores": res.condition_scores.model_dump(),
                    }

                    target_json = out_dir / f"{img_path.stem}_label.json"
                    with open(target_json, "w", encoding="utf-8") as f:
                        json.dump(ann_payload, f, indent=2)
                else:
                    skipped_count += 1
            except Exception:
                skipped_count += 1

        return {
            "total_images_processed": len(image_paths),
            "bootstrapped_high_confidence": bootstrapped_count,
            "skipped_low_confidence": skipped_count,
            "defects_identified": defects_found_count,
            "room_distribution": room_distribution,
            "output_directory": str(out_dir.resolve()),
        }

    def export_finetuning_dataset(
        self,
        annotation_dir: str,
        output_file_path: str,
    ) -> int:
        """
        Export bootstrapped or verified annotations into standard JSONL format
        for CLIP / ResNet fine-tuning.
        """
        ann_path = Path(annotation_dir)
        json_files = list(ann_path.glob("*_label.json"))

        out_file = Path(output_file_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        count = 0
        with open(out_file, "w", encoding="utf-8") as out:
            for jf in json_files:
                try:
                    with open(jf, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    room = data.get("predicted_room_category") or data.get("target_room_category")
                    if not room:
                        continue

                    # Generate natural language text prompt for CLIP zero-shot/contrastive alignment
                    readable_room = room.replace("_", " ").lower()
                    prompt = f"a high resolution inspection photograph of a {readable_room} in a residential property"

                    record = {
                        "image_path": data.get("image_path"),
                        "room_category": room,
                        "text_prompt": prompt,
                        "has_defect": data.get("has_defect", False),
                        "defect_type": data.get("primary_defect_type"),
                        "defect_severity": data.get("primary_defect_severity"),
                        "defects_count": len(data.get("defects", [])),
                    }
                    out.write(json.dumps(record) + "\n")
                    count += 1
                except Exception:
                    continue

        return count
