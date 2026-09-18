"""
PAM (Photo Analysis Module) — Dataset Manager, Training, & Evaluation CLI.

Enables:
1. Dataset evaluation across real inspection image folders
2. Bootstrapping pseudo-labels for unannotated photos
3. Exporting fine-tuning pairs for contrastive vision models
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from this_is_what_you_need.common import BaseDatasetSplitter
from this_is_what_you_need.pam.pipeline import PamPipeline, RoomCategory


class PamDatasetManager:
    """Manages inspection photo discovery, train/val/test splits, and bootstrapping."""

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


def main():
    parser = argparse.ArgumentParser(description="PAM Training & Evaluation CLI")
    parser.add_argument("--mode", choices=["eval", "bootstrap"], default="eval")
    parser.add_argument("--data-dir", type=str, default="data/inspections")
    args = parser.parse_args()
    print(f"Running PAM in mode={args.mode} on {args.data_dir}...")


if __name__ == "__main__":
    main()
