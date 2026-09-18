"""
SSE (Semantic Search Engine) — Training & Evaluation CLI.
"""

from __future__ import annotations

import argparse
from this_is_what_you_need.common import BaseDatasetSplitter
from this_is_what_you_need.sse.pipeline import SsePipeline, FourteenFilterCriteria


def main():
    parser = argparse.ArgumentParser(description="SSE Training & Latency Evaluation CLI")
    parser.add_argument("--mode", choices=["eval", "bootstrap"], default="eval")
    args = parser.parse_args()
    print(f"Running SSE evaluation in mode={args.mode}...")


if __name__ == "__main__":
    main()
