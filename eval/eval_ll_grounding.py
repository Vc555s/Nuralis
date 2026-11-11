import argparse
import json
import os
import re
from typing import List

from .utils_api import analyze, ensure_results_dir, dump_json


SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text: str) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    # simple regex-based sentence split
    parts = SENT_SPLIT_RE.split(text)
    return [s.strip() for s in parts if s.strip()]


def has_citation(s: str) -> bool:
    s = s or ""
    if re.search(r"\[[0-9]+\]", s):
        return True
    if re.search(r"https?://", s, re.IGNORECASE):
        return True
    if re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", s, re.IGNORECASE):  # DOI
        return True
    return False


def normalize_sentence(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().strip())


def main() -> None:
    parser = argparse.ArgumentParser(description="LL-03 Grounding & Evidence Coverage")
    parser.add_argument("--query", required=True)
    parser.add_argument("--year-start", type=int, required=True)
    parser.add_argument("--year-end", type=int, required=True)
    parser.add_argument("--top-n-refs", type=int, default=10)
    parser.add_argument("--api-base", default=os.environ.get("EVAL_API_BASE_URL", "http://localhost:8010/api/"))
    args = parser.parse_args()

    resp = analyze(
        args.query,
        args.year_start,
        args.year_end,
        use_llm=True,
        use_embeddings=True,
        api_base=args.api_base,
    )

    insights_block = None
    adv = resp.get("advanced_insights")
    if isinstance(adv, dict):
        insights_block = adv.get("executive_summary") or json.dumps(adv)
    if not insights_block:
        insights_block = ""

    # Build reference URL list from top N papers
    papers = resp.get("papers", [])[: args.top_n_refs]
    ref_urls = [p.get("url") for p in papers if isinstance(p, dict) and p.get("url")]

    sentences = split_sentences(insights_block)
    total = max(1, len(sentences))
    coverage_hits = 0
    for s in sentences:
        if has_citation(s):
            coverage_hits += 1
        else:
            # count hit if we explicitly see any referenced url
            if any(u in s for u in ref_urls):
                coverage_hits += 1

    coverage = 100.0 * (coverage_hits / total)

    # Redundancy: percentage duplicate sentences
    normed = [normalize_sentence(s) for s in sentences]
    unique = len(set(normed))
    redundancy = 100.0 * (1 - (unique / max(1, len(normed))))

    results_dir = ensure_results_dir("results")
    out = {
        "query": args.query,
        "year_start": args.year_start,
        "year_end": args.year_end,
        "num_sentences": len(sentences),
        "evidence_coverage_pct": coverage,
        "redundancy_pct": redundancy,
        "sample_sentences": sentences[:10],
        "ref_urls_sample": ref_urls[:5],
    }
    dump_json(out, os.path.join(results_dir, f"ll_grounding_{args.query}.json"))
    print(f"Coverage={coverage:.1f}% | Redundancy={redundancy:.1f}% | sentences={len(sentences)}")


if __name__ == "__main__":
    main()


