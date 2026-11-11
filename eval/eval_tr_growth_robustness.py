import argparse
import csv
import os
from typing import Dict, List

import numpy as np
from scipy.stats import spearmanr, kendalltau

from .utils_api import analyze, ensure_results_dir, dump_json


def compute_growth_metrics_per_keyword(trends_data: dict) -> Dict[str, dict]:
    keywords: dict = trends_data.get("keywords", {}) or {}
    out: Dict[str, dict] = {}
    for kw, year_counts in keywords.items():
        years = sorted(int(y) for y in year_counts.keys())
        if len(years) < 2:
            continue
        series = np.array([int(year_counts[str(y)]) for y in years], dtype=float)
        n = len(series)
        if n < 2:
            continue
        first_half = series[: n // 2]
        last_half = series[n // 2 :]
        heuristic = float(np.mean(last_half) - np.mean(first_half))

        x = np.array(years, dtype=float)
        slope = float(np.polyfit(x, series, deg=1)[0])

        out[str(kw)] = {
            "heuristic": heuristic,
            "slope": slope,
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="TR-03 Growth Robustness (heuristic vs regression)")
    parser.add_argument("--query", required=True)
    parser.add_argument("--year-start", type=int, required=True)
    parser.add_argument("--year-end", type=int, required=True)
    parser.add_argument("--api-base", default=os.environ.get("EVAL_API_BASE_URL", "http://localhost:8010/api/"))
    args = parser.parse_args()

    resp = analyze(
        args.query,
        args.year_start,
        args.year_end,
        use_llm=False,
        use_embeddings=False,
        api_base=args.api_base,
    )
    trends_data = resp.get("trends_data", {})

    metrics = compute_growth_metrics_per_keyword(trends_data)
    if not metrics:
        print("No keyword time series found.")
        return

    keywords = list(metrics.keys())
    heuristics = np.array([metrics[k]["heuristic"] for k in keywords])
    slopes = np.array([metrics[k]["slope"] for k in keywords])

    # Rankings
    rank_heur = heuristics.argsort().argsort()
    rank_slope = slopes.argsort().argsort()
    # Spearman/Kendall between metric vectors
    rho, _ = spearmanr(heuristics, slopes)
    tau, _ = kendalltau(heuristics, slopes)

    results_dir = ensure_results_dir("results")
    csv_path = os.path.join(results_dir, f"tr_growth_robustness_{args.query}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["keyword", "heuristic", "slope", "rank_diff"])
        for i, kw in enumerate(keywords):
            w.writerow([kw, f"{heuristics[i]:.6f}", f"{slopes[i]:.6f}", int(rank_heur[i]) - int(rank_slope[i])])

    summary = {
        "query": args.query,
        "year_start": args.year_start,
        "year_end": args.year_end,
        "num_keywords": len(keywords),
        "spearman_rho": float(rho) if np.isfinite(rho) else None,
        "kendall_tau": float(tau) if np.isfinite(tau) else None,
    }
    dump_json(summary, os.path.join(results_dir, f"tr_growth_robustness_{args.query}.json"))

    print(f"TR-03 | Spearman rho: {summary['spearman_rho']:.4f} | Kendall tau: {summary['kendall_tau']:.4f} | N={len(keywords)}")


if __name__ == "__main__":
    main()


