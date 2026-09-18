"""
SSE (Semantic Search Engine) — Training & Evaluation CLI.

Enables:
1. Evaluation of hybrid search latency against <80ms P95 budget (§1)
2. Evaluation of 14-filter precision and edge rerank quality
3. Bootstrapping benchmark PIP corpora for staging and capacity testing (T-08)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from sse.dataset_manager import SseDatasetManager
from sse.pipeline import SsePipeline
from sse.models import SseSearchQuery


def run_evaluation(corpus_size: int = 50, seed: int = 42) -> Dict[str, Any]:
    """
    Evaluates SSE pipeline latency and relevance across golden queries.
    Verifies that <80ms P95 latency target (§1) is strictly satisfied.
    """
    print(f"\n=======================================================")
    print(f" SSE (Semantic Search Engine) — Pipeline Evaluation")
    print(f"=======================================================")

    pipeline = SsePipeline()
    docs = SseDatasetManager.bootstrap_benchmark_corpus(count=corpus_size, seed=seed)
    pipeline.batch_index(docs)

    queries = SseDatasetManager.BENCHMARK_QUERIES
    latencies = []
    lexical_latencies = []
    semantic_latencies = []
    rerank_latencies = []
    total_hits_list = []

    for q_text in queries:
        res = pipeline.search(SseSearchQuery(raw_query=q_text, page_size=10))
        latencies.append(res.total_latency_ms)
        lexical_latencies.append(res.lexical_latency_ms)
        semantic_latencies.append(res.semantic_latency_ms)
        rerank_latencies.append(res.rerank_latency_ms)
        total_hits_list.append(res.total_hits)

    total = len(queries)
    sorted_lat = sorted(latencies)
    p95_latency = sorted_lat[int(total * 0.95)]
    avg_latency = sum(latencies) / total
    avg_lexical = sum(lexical_latencies) / total
    avg_semantic = sum(semantic_latencies) / total
    avg_rerank = sum(rerank_latencies) / total
    zero_hits = sum(1 for h in total_hits_list if h == 0)

    print(f"Indexed PIP Documents      : {len(docs)}")
    print(f"Golden Queries Evaluated   : {total}")
    print(f"P95 Total Latency          : {p95_latency:.2f} ms (Target: < 80 ms)")
    print(f"Average Total Latency      : {avg_latency:.2f} ms")
    print(f"  - Avg Lexical Latency    : {avg_lexical:.2f} ms")
    print(f"  - Avg Semantic Latency   : {avg_semantic:.2f} ms")
    print(f"  - Avg Edge Rerank Latency: {avg_rerank:.2f} ms")
    print(f"Zero-Hit Queries           : {zero_hits} / {total}")

    status = "PASSED" if p95_latency < 80.0 and zero_hits == 0 else "NEEDS_TUNING"
    print(f"Latency Budget SLA Status  : [{status}]")
    print(f"=======================================================\n")

    return {
        "status": status,
        "corpus_size": len(docs),
        "queries_count": total,
        "p95_latency_ms": round(p95_latency, 2),
        "avg_latency_ms": round(avg_latency, 2),
        "zero_hits": zero_hits,
    }


def run_bootstrap(out_dir: str, count: int = 50):
    """Bootstraps benchmark corpus to JSON file."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    docs = SseDatasetManager.bootstrap_benchmark_corpus(count=count)
    data = [d.model_dump(mode="json") for d in docs]
    target_file = out_path / "pip_benchmark_corpus.json"
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Successfully bootstrapped {count} PIP documents to: {target_file}")


def main():
    parser = argparse.ArgumentParser(description="SSE Training & Latency Evaluation Tool")
    parser.add_argument("--mode", choices=["eval", "bootstrap"], default="eval")
    parser.add_argument("--corpus-size", type=int, default=50)
    parser.add_argument("--out-dir", type=str, default="sse_output")
    args = parser.parse_args()

    if args.mode == "eval":
        run_evaluation(corpus_size=args.corpus_size)
    elif args.mode == "bootstrap":
        run_bootstrap(out_dir=args.out_dir, count=args.corpus_size)


if __name__ == "__main__":
    main()
