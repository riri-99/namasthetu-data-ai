"""
PAM (Photo Analysis Module) — Evaluation & Retraining CLI Tool.

Enables drop-in evaluation and bootstrapping over user-provided photo datasets:
- Evaluate Vision Model performance on real inspection photos
- Bootstrap pseudo-labels for unannotated room photo datasets
- Export fine-tuning pairs for CLIP / ResNet model training
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Dict

# Safe UTF-8 encoding configuration for Windows console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from pipelines.pam.dataset_manager import PamDatasetManager
from pipelines.pam.models import RoomCategory
from pipelines.pam.pipeline import PamPipeline


def run_evaluation(data_dir: str, limit: int = 100):
    print(f"\n========================================================")
    print(f"[PAM EVAL] Starting Evaluation on Dataset: {data_dir}")
    print(f"========================================================")

    mgr = PamDatasetManager(data_dir=data_dir)
    images = mgr.discover_images()

    if not images:
        print(f"[WARN] No image files found in {data_dir}")
        print("[INFO] Supported formats: .jpg, .jpeg, .png, .webp, .heic, .tiff")
        return

    eval_subset = images[:limit] if limit > 0 else images
    print(f"[INFO] Found {len(images)} total images. Evaluating sample of {len(eval_subset)}...")

    pipeline = PamPipeline()
    room_counts: Dict[str, int] = {cat.value: 0 for cat in RoomCategory}
    defects_found = 0
    total_latency = 0.0
    confidences = []

    t0 = time.time()
    for idx, img_path in enumerate(eval_subset, 1):
        # Extract folder hint if folder matches a known room
        folder_hint = img_path.parent.name if img_path.parent.name in pipeline.vision_engine.INSPECTOR_HINT_MAP else None
        
        res = pipeline.analyze_photo(
            image_input=str(img_path),
            inspection_id=f"insp_eval_{idx}",
            photo_url=str(img_path),
            photo_id=f"p_{idx}",
            room_label_hint=folder_hint,
        )

        room_counts[res.room_category.value] += 1
        confidences.append(res.room_confidence)
        total_latency += res.inference_latency_ms
        if res.has_defect:
            defects_found += len(res.defects)

        if idx % 10 == 0 or idx == len(eval_subset):
            print(f"  Processed {idx}/{len(eval_subset)} photos...")

    elapsed = time.time() - t0
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    avg_latency = total_latency / len(eval_subset) if eval_subset else 0.0

    print(f"\n--------------------------------------------------------")
    print(f"[RESULT] Evaluation Summary:")
    print(f"  • Total Photos Analyzed:      {len(eval_subset)}")
    print(f"  • Mean Room Confidence:       {avg_conf * 100:.1f}%")
    print(f"  • Mean Latency Per Photo:     {avg_latency:.1f} ms (P95 target: 200-800 ms)")
    print(f"  • Total Defects Identified:   {defects_found}")
    print(f"  • Wall Time Elapsed:          {elapsed:.2f} s")
    print(f"\n[RESULT] Room Category Distribution:")
    for room, count in room_counts.items():
        if count > 0:
            pct = (count / len(eval_subset)) * 100
            print(f"  - {room:<20}: {count:>4} ({pct:.1f}%)")
    print(f"========================================================\n")


def run_bootstrap(data_dir: str, out_dir: str, threshold: float = 0.80):
    print(f"\n========================================================")
    print(f"[PAM BOOTSTRAP] Generating Pseudo-Labels")
    print(f"  • Input Directory:  {data_dir}")
    print(f"  • Output Directory: {out_dir}")
    print(f"  • Confidence Gate:  {threshold * 100:.0f}%")
    print(f"========================================================")

    mgr = PamDatasetManager(data_dir=data_dir)
    images = mgr.discover_images()
    if not images:
        print(f"[WARN] No image files found in {data_dir}")
        return

    res = mgr.bootstrap_unlabeled_photos(
        image_paths=images,
        output_annotation_dir=out_dir,
        confidence_threshold=threshold,
    )

    print(f"[OK] Bootstrapping Complete:")
    print(f"  • Total Processed:          {res['total_images_processed']}")
    print(f"  • High-Confidence Labeled:  {res['bootstrapped_high_confidence']}")
    print(f"  • Skipped (Low Confidence): {res['skipped_low_confidence']}")
    print(f"  • Candidate Defects Found:  {res['defects_identified']}")
    print(f"  • Saved JSON Labels To:     {res['output_directory']}")
    print(f"========================================================\n")


def run_export_finetune(ann_dir: str, out_file: str):
    print(f"\n========================================================")
    print(f"[PAM EXPORT] Formatting Retraining Dataset")
    print(f"  • Annotation Directory: {ann_dir}")
    print(f"  • Target File:          {out_file}")
    print(f"========================================================")

    mgr = PamDatasetManager()
    count = mgr.export_finetuning_dataset(
        annotation_dir=ann_dir,
        output_file_path=out_file,
    )

    print(f"[OK] Exported {count} labeled training pairs to {out_file}")
    print(f"========================================================\n")


def main():
    parser = argparse.ArgumentParser(description="PAM Photo Analysis Evaluation & Retraining CLI")
    parser.add_argument("--mode", choices=["eval", "bootstrap", "export-finetune"], required=True,
                        help="Execution mode: eval, bootstrap, or export-finetune")
    parser.add_argument("--data-dir", type=str, help="Path to raw image dataset directory")
    parser.add_argument("--out-dir", type=str, default="pam_output/annotations",
                        help="Output directory for bootstrapped annotations")
    parser.add_argument("--out-file", type=str, default="pam_output/finetuning_pairs.jsonl",
                        help="Output JSONL file path for fine-tuning export")
    parser.add_argument("--confidence-threshold", type=float, default=0.80,
                        help="Minimum confidence required to bootstrap pseudo-label (default: 0.80)")
    parser.add_argument("--limit", type=int, default=100,
                        help="Maximum images to evaluate (0 for all)")

    args = parser.parse_args()

    if args.mode == "eval":
        if not args.data_dir:
            print("[ERROR] --data-dir is required for eval mode")
            sys.exit(1)
        run_evaluation(args.data_dir, limit=args.limit)

    elif args.mode == "bootstrap":
        if not args.data_dir:
            print("[ERROR] --data-dir is required for bootstrap mode")
            sys.exit(1)
        run_bootstrap(args.data_dir, args.out_dir, threshold=args.confidence_threshold)

    elif args.mode == "export-finetune":
        run_export_finetune(args.out_dir, args.out_file)


if __name__ == "__main__":
    main()
