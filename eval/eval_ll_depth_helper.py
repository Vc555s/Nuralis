import argparse
import csv
import os
from typing import Tuple

from .utils_api import analyze, ensure_results_dir


def write_markdown(path: str, insights_text: str, query: str, year_span: Tuple[int, int]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# LL Review for query: {query}\n\n")
        f.write(f"Years: {year_span[0]}–{year_span[1]}\n\n")
        f.write("## Generated Insights\n\n")
        f.write(insights_text or "(No insights returned)\n\n")
        f.write("\n## Analytic Depth Rubric (1–5)\n\n")
        f.write("| Dimension | 1 | 3 | 5 |\n")
        f.write("|---|---|---|---|\n")
        f.write("| Novelty | Repeats obvious points | Some synthesis | Clear, original synthesis |\n")
        f.write("| Synthesis | Disconnected bullets | Basic integration | Strong theme-level synthesis |\n")
        f.write("| Strategic Value | Little actionable insight | Some guidance | Actionable, decision-grade guidance |\n\n")
        f.write("## Checklist (Scope/Limitations)\n\n")
        f.write("- Mentions data coverage and time span\n")
        f.write("- Notes limitations and uncertainty\n")
        f.write("- Distinguishes evidence vs opinion\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="LL-02 Analytical Depth (human rubric + helper)")
    parser.add_argument("--query", required=True)
    parser.add_argument("--year-start", type=int, required=True)
    parser.add_argument("--year-end", type=int, required=True)
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
    adv = resp.get("advanced_insights")
    insights = ""
    if isinstance(adv, dict):
        insights = adv.get("executive_summary") or ""
        if not insights:
            insights = str(adv)

    results_dir = ensure_results_dir("results")
    md_path = os.path.join(results_dir, f"ll_review_{args.query}.md")
    write_markdown(md_path, insights, args.query, (args.year_start, args.year_end))

    csv_path = os.path.join(results_dir, "ll_review_template.csv")
    new_file = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["reviewer_id", "query", "depth_score(1-5)", "notes"]) 
        # Provide one empty row as a template example (do not score automatically)
        w.writerow(["", args.query, "", ""])

    print(f"Wrote markdown to {md_path} and template CSV to {csv_path}")


if __name__ == "__main__":
    main()


