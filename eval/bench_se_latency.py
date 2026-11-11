import argparse
import asyncio
import csv
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List

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


def do_search(query: str, api_base: str) -> float:
    t0 = time.perf_counter()
    _ = semantic_search(query, k=10, api_base=api_base)
    t1 = time.perf_counter()
    return t1 - t0


async def run_benchmark(queries: List[str], api_base: str, repeats: int, concurrency: int, year_start: int, year_end: int) -> List[float]:
    loop = asyncio.get_event_loop()
    sem = asyncio.Semaphore(concurrency)
    timings: List[float] = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        async def task(q: str):
            async with sem:
                return await loop.run_in_executor(pool, do_search, q, api_base)

        # Warm the index for each query by running analyze (embeddings only)
        for q in queries:
            try:
                await loop.run_in_executor(pool, analyze, q, year_start, year_end, False, True, 300, api_base)
            except Exception:
                pass

        for q in queries:
            for _ in range(repeats):
                timings.append(await task(q))
    return timings


def percentile(sorted_vals: List[float], p: float) -> float:
    if not sorted_vals:
        return float("nan")
    k = max(0, min(len(sorted_vals) - 1, int(round(p * (len(sorted_vals) - 1)))))
    return sorted_vals[k]


def main() -> None:
    parser = argparse.ArgumentParser(description="SE-03 Semantic Search Latency (throughput)")
    parser.add_argument("--judgments", default="gold/judgements.jsonl")
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--api-base", default=os.environ.get("EVAL_API_BASE_URL", "http://localhost:8010/api/"))
    parser.add_argument("--year-start", type=int, default=2018)
    parser.add_argument("--year-end", type=int, default=2024)
    args = parser.parse_args()

    judgments = load_judgments(args.judgments)
    if not judgments:
        print("No judgments found.")
        return

    queries = [j["query"] for j in judgments]
    timings = asyncio.run(run_benchmark(queries, args.api_base, args.repeats, args.concurrency, args.year_start, args.year_end))

    sorted_t = sorted(timings)
    p50 = percentile(sorted_t, 0.50)
    p90 = percentile(sorted_t, 0.90)
    p95 = percentile(sorted_t, 0.95)
    mean = sum(sorted_t) / len(sorted_t)
    var = sum((x - mean) ** 2 for x in sorted_t) / max(1, len(sorted_t) - 1)
    std = var ** 0.5
    # Max QPS at fixed concurrency (rough approximation)
    max_qps = args.concurrency / p50 if p50 > 0 else float("inf")

    results_dir = ensure_results_dir("results")
    raw_csv = os.path.join(results_dir, "se_latency_raw.csv")
    with open(raw_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["latency_s"])
        for x in timings:
            w.writerow([f"{x:.6f}"])

    summary = {
        "num_requests": len(timings),
        "concurrency": args.concurrency,
        "p50_ms": p50 * 1000.0,
        "p90_ms": p90 * 1000.0,
        "p95_ms": p95 * 1000.0,
        "mean_ms": mean * 1000.0,
        "std_ms": std * 1000.0,
        "approx_max_qps": max_qps,
    }
    dump_json(summary, os.path.join(results_dir, "se_latency_summary.json"))

    print(
        f"p50={summary['p50_ms']:.1f}ms | p90={summary['p90_ms']:.1f}ms | p95={summary['p95_ms']:.1f}ms | "
        f"mean={summary['mean_ms']:.1f}ms | std={summary['std_ms']:.1f}ms | ~maxQPS={summary['approx_max_qps']:.2f}"
    )


if __name__ == "__main__":
    main()


