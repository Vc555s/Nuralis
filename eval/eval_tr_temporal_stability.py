import argparse
import csv
import os
import random
import statistics
from collections import defaultdict
from typing import Dict, List, Tuple

import numpy as np
from scipy.stats import spearmanr

from .utils_api import analyze, ensure_results_dir, dump_json


def year_from_date(date_str: str) -> int:
    try:
        return int(str(date_str)[:4])
    except Exception:  # noqa: BLE001
        return -1


def build_keyword_year_counts(papers: List[dict]) -> Dict[str, Dict[int, int]]:
    counts: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for p in papers or []:
        year = year_from_date(p.get("date", ""))
        if year <= 0:
            continue
        categories = p.get("categories") or []
        if isinstance(categories, list):
            for cat in categories:
                if isinstance(cat, str) and cat.strip():
                    counts[cat.strip()][year] += 1
    return counts


def bootstrap_subsample_by_year(papers: List[dict], drop_frac: float, rng: random.Random) -> List[dict]:
    buckets: Dict[int, List[dict]] = defaultdict(list)
    for p in papers:
        y = year_from_date(p.get("date", ""))
        if y > 0:
            buckets[y].append(p)
    subsampled: List[dict] = []
    for year, items in buckets.items():
        if not items:
            continue
        k = int(round(len(items) * (1 - drop_frac)))
        k = max(0, min(len(items), k))
        subsampled.extend(rng.sample(items, k))
    return subsampled


def series_from_counts(counts: Dict[int, int], years: List[int]) -> List[int]:
    return [int(counts.get(y, 0)) for y in years]


def compute_keyword_spearman(
    kw_counts_a: Dict[str, Dict[int, int]],
    kw_counts_b: Dict[str, Dict[int, int]],
    years: List[int],
) -> Dict[str, float]:
    rho_by_kw: Dict[str, float] = {}
    common_kws = set(kw_counts_a.keys()) & set(kw_counts_b.keys())
    for kw in common_kws:
        a = series_from_counts(kw_counts_a[kw], years)
        b = series_from_counts(kw_counts_b[kw], years)
        if np.sum(a) == 0 and np.sum(b) == 0:
            continue
        try:
            rho, _ = spearmanr(a, b)
            if np.isfinite(rho):
                rho_by_kw[kw] = float(rho)
        except Exception:  # noqa: BLE001
            continue
    return rho_by_kw


def ci_from_values(values: List[float], alpha: float = 0.05) -> Tuple[float, float]:
    if not values:
        return (float("nan"), float("nan"))
    lower = np.percentile(values, 100 * (alpha / 2))
    upper = np.percentile(values, 100 * (1 - alpha / 2))
    return float(lower), float(upper)


def main() -> None:
    parser = argparse.ArgumentParser(description="TR-02 Temporal Stability (subsample robustness)")
    parser.add_argument("--query", required=True)
    parser.add_argument("--year-start", type=int, required=True)
    parser.add_argument("--year-end", type=int, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--api-base", default=os.environ.get("EVAL_API_BASE_URL", "http://localhost:8010/api/"))
    args = parser.parse_args()

    rng = random.Random(args.seed)

    resp = analyze(
        args.query,
        args.year_start,
        args.year_end,
        use_llm=False,
        use_embeddings=False,
        api_base=args.api_base,
    )

    papers: List[dict] = resp.get("papers", [])
    years = list(range(int(args.year_start), int(args.year_end) + 1))

    sub1 = bootstrap_subsample_by_year(papers, drop_frac=0.30, rng=rng)
    sub2 = bootstrap_subsample_by_year(papers, drop_frac=0.30, rng=rng)

    kw_counts_1 = build_keyword_year_counts(sub1)
    kw_counts_2 = build_keyword_year_counts(sub2)

    rho_by_kw = compute_keyword_spearman(kw_counts_1, kw_counts_2, years)
    rho_values = list(rho_by_kw.values())
    mean_rho = float(statistics.fmean(rho_values)) if rho_values else float("nan")
    ci_low, ci_high = ci_from_values(rho_values)

    results_dir = ensure_results_dir("results")
    csv_path = os.path.join(results_dir, f"tr_temporal_stability_{args.query}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["keyword", "spearman_rho"])
        for kw, rho in sorted(rho_by_kw.items(), key=lambda x: x[0].lower()):
            w.writerow([kw, f"{rho:.6f}"])

    summary = {
        "query": args.query,
        "year_start": args.year_start,
        "year_end": args.year_end,
        "num_keywords": len(rho_by_kw),
        "mean_rho": mean_rho,
        "ci95": [ci_low, ci_high],
        "note": "Keywords approximated from paper categories",
    }
    dump_json(summary, os.path.join(results_dir, f"tr_temporal_stability_{args.query}.json"))

    print(f"TR-02 mean rho: {mean_rho:.4f} (95% CI [{ci_low:.4f}, {ci_high:.4f}]); keywords: {len(rho_by_kw)}")


if __name__ == "__main__":
    main()


