"""
DEE (Document Extraction Engine) — Training & Evaluation CLI.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

from this_is_what_you_need.common import BaseDatasetSplitter
from this_is_what_you_need.dee.pipeline import DeePipeline, DocumentType


def main():
    parser = argparse.ArgumentParser(description="DEE Training & Evaluation CLI")
    parser.add_argument("--mode", choices=["eval", "bootstrap"], default="eval")
    parser.add_argument("--data-dir", type=str, default="data/deeds")
    args = parser.parse_args()
    print(f"Running DEE in mode={args.mode} on {args.data_dir}...")


if __name__ == "__main__":
    main()
