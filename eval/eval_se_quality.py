import argparse
import csv
import json
import os
import time
from typing import List, Dict

from .utils_api import semantic_search, analyze, ensure_results_dir, dump_json


def load_judgments(path: str) -> List[dict]:
    items: List[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def dcg_at_k(rel: List[int], k: int) -> float:
    score = 0.0
    for i, r in enumerate(rel[:k], start=1):
        if r > 0:
            score += (2**r - 1) / (float.__pow__(2.0, 0) + (i))  # simple log base workaround
    return score


def idcg_at_k(rel: List[int], k: int) -> float:
    sorted_rel = sorted(rel, reverse=True)
    return dcg_at_k(sorted_rel, k)


def ndcg_at_k(rel: List[int], k: int) -> float:
    denom = idcg_at_k(rel, k)
    if denom == 0:
        return 0.0
    return dcg_at_k(rel, k) / denom


def mrr_at_k(rel: List[int], k: int) -> float:
    for i, r in enumerate(rel[:k], start=1):
        if r > 0:
            return 1.0 / i
    return 0.0


def normalize_url(u: str | None) -> str:
    if not u:
        return ""
    s = u.lower().strip()
    if s.endswith("/"):
        s = s[:-1]
    s = s.replace("//arxiv.org/pdf/", "//arxiv.org/abs/")
    s = s.replace("//www.arxiv.org/pdf/", "//arxiv.org/abs/")
    s = s.replace("//www.arxiv.org/abs/", "//arxiv.org/abs/")
    s = s.replace("//www.arxiv.org/", "//arxiv.org/")
    s = s.replace("//arxiv.org/pdf/", "//arxiv.org/abs/")
    if s.endswith(".pdf"):
        s = s[:-4]
    # strip version suffix like v3
    s = s.rstrip()
    if "/abs/" in s:
        head, tail = s.split("/abs/", 1)
        tail = tail.rstrip()
        tail = tail.split("v")[0]
        s = head + "/abs/" + tail
    return s


def main() -> None:
    parser = argparse.ArgumentParser(description="SE-02 Retrieval Quality (nDCG/MRR)")
    parser.add_argument("--judgments", default="gold/judgements.jsonl")
    parser.add_argument("--api-base", default=os.environ.get("EVAL_API_BASE_URL", "http://localhost:8010/api/"))
    parser.add_argument("--year-start", type=int, default=2018)
    parser.add_argument("--year-end", type=int, default=2024)
    parser.add_argument("--max-papers", type=int, default=400)
    args = parser.parse_args()

    results_dir = ensure_results_dir("results")
    judgments = load_judgments(args.judgments)
    if not judgments:
        print("No judgments found.")
        return

    # Warm up per query corpus: build embeddings with analyze so semantic-search has a relevant index
    # Use LLM off for speed

    rows = []
    ndcgs: List[float] = []
    mrrs: List[float] = []
    latencies: List[float] = []

    for j in judgments:
        query = j.get("query", "")
        rel_urls = {normalize_url(u) for u in (j.get("relevant_urls", []) or [])}
        # Build corpus for this query
        try:
            _ = analyze(query, args.year_start, args.year_end, use_llm=False, use_embeddings=True, max_papers=args.max_papers, api_base=args.api_base)
        except Exception:
            pass
        t0 = time.perf_counter()
        results = semantic_search(query, k=10, api_base=args.api_base)
        t1 = time.perf_counter()
        latencies.append(t1 - t0)

        graded = []
        for r in results:
            md = r.get("metadata", {}) if isinstance(r, dict) else {}
            url_raw = r.get("url") or md.get("url") or ""
            url = normalize_url(url_raw)
            relevant = 1 if url in rel_urls else 0
            graded.append(relevant)

        n = ndcg_at_k(graded, 10)
        m = mrr_at_k(graded, 10)
        ndcgs.append(n)
        mrrs.append(m)
        rows.append({"query": query, "nDCG@10": f"{n:.4f}", "MRR@10": f"{m:.4f}"})

    # Save per-query
    csv_path = os.path.join(results_dir, "se_ir_metrics.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["query", "nDCG@10", "MRR@10"]) 
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "macro_nDCG@10": sum(ndcgs) / len(ndcgs),
        "macro_MRR@10": sum(mrrs) / len(mrrs),
        "latency_p50_ms": 1000.0 * sorted(latencies)[len(latencies) // 2],
        "latency_p95_ms": 1000.0 * sorted(latencies)[int(len(latencies) * 0.95) - 1],
        "num_queries": len(judgments),
    }
    dump_json(summary, os.path.join(results_dir, "se_ir_summary.json"))

    print(f"nDCG@10={summary['macro_nDCG@10']:.4f} | MRR@10={summary['macro_MRR@10']:.4f} | p50={summary['latency_p50_ms']:.1f}ms | p95={summary['latency_p95_ms']:.1f}ms")


if __name__ == "__main__":
    main()


