"""
SSE (Semantic Search Engine) — Dataset Manager, Ranking Optimization, & Evaluation CLI.

Enables:
1. Bootstrapping realistic property catalog documents and multi-intent query benchmarks
2. Tuning hybrid BM25 + dense semantic ranking weights via Mean Reciprocal Rank (MRR)
3. Evaluating Recall@k, NDCG@10, and verifying <80ms P95 latency SLA
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

from this_is_what_you_need.common import (
    BaseDatasetSplitter,
    PrismaFurnishingStatus,
    PrismaListingStatus,
    PrismaPropertyType,
)
from this_is_what_you_need.sse.pipeline import (
    FourteenFilterCriteria,
    PipSearchDocument,
    QueryIntent,
    SearchRankingWeights,
    SsePipeline,
)


class SseDatasetManager:
    """Manages search catalog datasets, multi-intent queries, ranking tuning, and latency benchmarking."""

    LOCALITIES = ["Whitefield", "Indiranagar", "Koramangala", "HSR Layout", "Hebbal", "Sarjapur Road"]
    SOCIETIES = ["Prestige Shantiniketan", "Sobha Dream Acres", "Brigade Gateway", "Godrej Woodsman", "Total Environment"]

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = Path(data_path) if data_path else None
        self.pipeline = SsePipeline()

    def bootstrap_benchmark_dataset(
        self,
        output_file: str,
        doc_count: int = 50,
        query_count: int = 20,
    ) -> Path:
        """
        Synthesizes catalog documents and multi-intent benchmark queries with ground-truth relevant document IDs.
        """
        out_p = Path(output_file)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        rng = random.Random(42)
        documents: List[Dict[str, Any]] = []

        for i in range(doc_count):
            loc = rng.choice(self.LOCALITIES)
            soc = rng.choice(self.SOCIETIES)
            bhk = rng.choice([1, 2, 3, 4])
            prop_type = PrismaPropertyType.APARTMENT if rng.random() > 0.15 else PrismaPropertyType.VILLA
            furn = rng.choice([PrismaFurnishingStatus.SEMI_FURNISHED, PrismaFurnishingStatus.FULLY_FURNISHED, PrismaFurnishingStatus.UNFURNISHED])
            area = float(rng.randint(600, 3200))
            price_paise = int(area * rng.randint(7000, 15000) * 100)
            score = rng.randint(72, 98)
            seepage = score < 78 and rng.random() < 0.5
            deed_ok = rng.random() > 0.10
            liens = not deed_ok and rng.random() > 0.5
            market_pos = rng.choice(["BELOW_MARKET", "ALIGNED", "ABOVE_MARKET"])
            yield_pct = round(rng.uniform(3.8, 5.8), 2)

            title = f"{bhk} BHK {prop_type.value.title()} in {soc}, {loc}"
            desc = f"Spacious {bhk} BHK property located at {loc}. Condition rated {score}/100. {'Zero seepage.' if not seepage else 'Minor seepage patch.'}"

            doc = PipSearchDocument(
                property_id=f"prop_{i+1:04d}",
                listing_id=f"list_{i+1:04d}",
                public_id=f"pip_{i+1:04d}",
                title=title,
                description=desc,
                locality=loc,
                city="Bengaluru",
                society_name=soc,
                property_type=prop_type,
                bhk_count=bhk,
                carpet_area_sqft=area,
                super_built_up_area_sqft=round(area * 1.25, 1),
                floor_number=rng.randint(1, 15),
                total_floors=18,
                furnishing=furn,
                parking_count=1,
                has_lift=True,
                listing_price_minor=price_paise,
                inspection_score_overall=score,
                seepage_detected=seepage,
                deed_verified=deed_ok,
                active_liens=liens,
                market_position=market_pos,
                gross_rental_yield_pct=yield_pct,
            )
            documents.append(doc.model_dump())

        # Generate multi-intent queries
        queries: List[Dict[str, Any]] = [
            {"query": "3 BHK luxury in Whitefield", "intent": "HYBRID", "must_match": {"locality": "Whitefield", "bhk_count": 3}},
            {"query": "High rental yield investment in HSR Layout", "intent": "INVESTOR_YIELD", "must_match": {"locality": "HSR Layout"}},
            {"query": "Pristine well-maintained 2 BHK without seepage", "intent": "CONDITION_FOCUSED", "must_match": {"bhk_count": 2, "no_seepage": True}},
            {"query": "Clear verified title apartment in Indiranagar", "intent": "LEGAL_VERIFIED", "must_match": {"locality": "Indiranagar", "clear_title": True}},
            {"query": "Sobha Dream Acres apartment", "intent": "LEXICAL_HEAVY", "must_match": {"society": "Sobha Dream Acres"}},
            {"query": "Affordable 1 BHK flat in Koramangala", "intent": "HYBRID", "must_match": {"locality": "Koramangala", "bhk_count": 1}},
            {"query": "Bargain undervalued properties below market price", "intent": "INVESTOR_YIELD", "must_match": {"market_pos": "BELOW_MARKET"}},
            {"query": "Spacious 4 BHK villa with clear rera title", "intent": "LEGAL_VERIFIED", "must_match": {"bhk_count": 4}},
        ]

        # Compute ground truth relevant doc IDs for each query
        for q in queries:
            conds = q["must_match"]
            rel_ids = []
            for d in documents:
                match = True
                if "locality" in conds and conds["locality"].lower() not in d["locality"].lower():
                    match = False
                if "bhk_count" in conds and conds["bhk_count"] != d["bhk_count"]:
                    match = False
                if "society" in conds and conds["society"].lower() not in (d.get("society_name") or "").lower():
                    match = False
                if "no_seepage" in conds and d.get("seepage_detected"):
                    match = False
                if "clear_title" in conds and (not d.get("deed_verified") or d.get("active_liens")):
                    match = False
                if "market_pos" in conds and d.get("market_position") != conds["market_pos"]:
                    match = False
                if match:
                    rel_ids.append(d["property_id"])
            q["relevant_doc_ids"] = rel_ids

        payload = {"documents": documents, "queries": queries}
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        return out_p

    def train_ranking_weights(
        self,
        dataset_path: str,
        weights_save_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Tunes ranking weights (lexical, semantic, cross-pipeline bonuses) on queries to optimize Mean Reciprocal Rank (MRR).
        """
        data_p = Path(dataset_path)
        with open(data_p, "r", encoding="utf-8") as f:
            data = json.load(f)

        pipe = SsePipeline()
        for doc_dict in data["documents"]:
            pipe.index_pip_document(PipSearchDocument(**doc_dict))

        queries = data["queries"]
        train_queries = queries[: max(1, int(len(queries) * 0.7))]

        # Coordinate grid tuning
        best_mrr = -1.0
        best_weights = pipe.ranking_weights.model_copy()

        candidates = [
            (0.35, 0.65), (0.45, 0.55), (0.50, 0.50), (0.60, 0.40)
        ]

        for w_lex, w_sem in candidates:
            pipe.ranking_weights.w_lexical = w_lex
            pipe.ranking_weights.w_semantic = w_sem

            mrr_sum = 0.0
            valid_q = 0
            for q in train_queries:
                target_ids = set(q.get("relevant_doc_ids", []))
                if not target_ids:
                    continue
                res = pipe.search(q["query"], top_k=10)
                rr = 0.0
                for item in res.items:
                    if item.property_id in target_ids:
                        rr = 1.0 / item.rank
                        break
                mrr_sum += rr
                valid_q += 1

            current_mrr = mrr_sum / max(1, valid_q)
            if current_mrr > best_mrr:
                best_mrr = current_mrr
                best_weights = pipe.ranking_weights.model_copy()

        pipe.ranking_weights = best_weights
        save_target = weights_save_path or str(Path(__file__).parent / "sse_weights.json")
        pipe.save_weights(save_target)

        return {
            "tuned_weights": best_weights.model_dump(),
            "best_train_mrr": round(best_mrr, 4),
            "weights_saved_to": save_target,
            "train_queries_count": len(train_queries),
        }

    def evaluate_dataset(
        self,
        dataset_path: str,
        weights_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates retrieval metrics: Recall@5, Recall@10, MRR, Mean NDCG@10, and latency statistics.
        """
        data_p = Path(dataset_path)
        with open(data_p, "r", encoding="utf-8") as f:
            data = json.load(f)

        pipe = SsePipeline(weights_path=weights_path)
        for doc_dict in data["documents"]:
            pipe.index_pip_document(PipSearchDocument(**doc_dict))

        queries = data["queries"]

        recall_5_list = []
        recall_10_list = []
        mrr_list = []
        ndcg_list = []
        latencies_ms = []

        for q in queries:
            target_ids = set(q.get("relevant_doc_ids", []))
            if not target_ids:
                continue

            start = time.perf_counter()
            res = pipe.search(q["query"], top_k=10)
            lat = (time.perf_counter() - start) * 1000.0
            latencies_ms.append(lat)

            retrieved_ids = [itm.property_id for itm in res.items]

            # Recall@5 and Recall@10
            hits_5 = sum(1 for pid in retrieved_ids[:5] if pid in target_ids)
            hits_10 = sum(1 for pid in retrieved_ids[:10] if pid in target_ids)
            recall_5_list.append(hits_5 / max(1, min(5, len(target_ids))))
            recall_10_list.append(hits_10 / max(1, min(10, len(target_ids))))

            # Reciprocal Rank
            rr = 0.0
            for rank, pid in enumerate(retrieved_ids, 1):
                if pid in target_ids:
                    rr = 1.0 / rank
                    break
            mrr_list.append(rr)

            # NDCG@10
            dcg = 0.0
            for rank, pid in enumerate(retrieved_ids[:10], 1):
                rel = 1.0 if pid in target_ids else 0.0
                dcg += rel / math.log2(rank + 1)
            idcg = sum(1.0 / math.log2(r + 1) for r in range(1, min(10, len(target_ids)) + 1)) or 1.0
            ndcg_list.append(dcg / idcg)

        n_q = len(recall_5_list)
        avg_lat = round(sum(latencies_ms) / max(1, len(latencies_ms)), 2)
        sorted_lats = sorted(latencies_ms)
        p95_lat = round(sorted_lats[int(len(sorted_lats) * 0.95)], 2) if sorted_lats else 0.0

        return {
            "total_queries_evaluated": n_q,
            "mean_recall_at_5": round(sum(recall_5_list) / max(1, n_q), 4),
            "mean_recall_at_10": round(sum(recall_10_list) / max(1, n_q), 4),
            "mean_reciprocal_rank": round(sum(mrr_list) / max(1, n_q), 4),
            "mean_ndcg_at_10": round(sum(ndcg_list) / max(1, n_q), 4),
            "avg_latency_ms": avg_lat,
            "p95_latency_ms": p95_lat,
            "sla_80ms_passed": p95_lat < 80.0,
        }


def main():
    parser = argparse.ArgumentParser(description="SSE Training & Latency Evaluation CLI")
    parser.add_argument("--mode", choices=["train", "eval", "bootstrap"], default="eval")
    parser.add_argument("--data-path", type=str, default="data/search_benchmark.json")
    parser.add_argument("--weights-path", type=str, default=None)
    parser.add_argument("--doc-count", type=int, default=50)
    args = parser.parse_args()

    mgr = SseDatasetManager(args.data_path)

    if args.mode == "bootstrap":
        print(f"Bootstrapping {args.doc_count} search documents and benchmark queries into {args.data_path}...")
        p = mgr.bootstrap_benchmark_dataset(args.data_path, doc_count=args.doc_count)
        print(f"Benchmark dataset generated successfully at: {p}")

    elif args.mode == "train":
        print(f"Tuning hybrid search ranking weights on {args.data_path}...")
        res = mgr.train_ranking_weights(args.data_path, weights_save_path=args.weights_path)
        print(f"Tuning completed:\n{json.dumps(res, indent=2)}")

    elif args.mode == "eval":
        data_p = Path(args.data_path)
        if not data_p.exists():
            print(f"Benchmark dataset not found at {args.data_path}, bootstrapping benchmark first...")
            mgr.bootstrap_benchmark_dataset(args.data_path, doc_count=args.doc_count)
        print(f"Evaluating retrieval quality and latency SLA on {args.data_path}...")
        metrics = mgr.evaluate_dataset(args.data_path, weights_path=args.weights_path)
        print(f"Retrieval Quality & Latency Metrics:\n{json.dumps(metrics, indent=2)}")


if __name__ == "__main__":
    main()
