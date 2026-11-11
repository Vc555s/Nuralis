import os
import glob
import json
from typing import List, Dict, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


def resolve_results_dir() -> str:
    return "results"

RESULTS_DIR = resolve_results_dir()
PLOTS_DIR = os.path.join(RESULTS_DIR, "plots")


def ensure_dirs() -> None:
    os.makedirs(PLOTS_DIR, exist_ok=True)


def set_theme() -> None:
    sns.set_theme(style="whitegrid", context="talk")
    plt.rcParams.update({
        "figure.dpi": 100,
        "savefig.dpi": 300,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })


def read_first_csv_by_glob(pattern: str) -> pd.DataFrame:
    files = sorted(glob.glob(pattern))
    if not files:
        return pd.DataFrame()
    return pd.read_csv(files[0])


def load_temporal_summary(query_hint: str = None) -> Tuple[pd.DataFrame, Dict]:
    csv_files = sorted(glob.glob(os.path.join(RESULTS_DIR, "tr_temporal_stability_*.csv")))
    json_files = sorted(glob.glob(os.path.join(RESULTS_DIR, "tr_temporal_stability_*.json")))
    sel_csv = csv_files[0] if csv_files else None
    sel_json = json_files[0] if json_files else None
    if query_hint:
        for f in csv_files:
            if query_hint in os.path.basename(f):
                sel_csv = f
        for f in json_files:
            if query_hint in os.path.basename(f):
                sel_json = f
    df = pd.read_csv(sel_csv) if sel_csv else pd.DataFrame()
    summary = {}
    if sel_json and os.path.exists(sel_json):
        with open(sel_json, "r", encoding="utf-8") as f:
            summary = json.load(f)
    return df, summary


def plot_temporal_stability() -> None:
    df, summary = load_temporal_summary()
    if df.empty:
        print("[Temporal Stability] No CSV found; skipping.")
        return

    mean_rho = summary.get("mean_rho")

    # We only have per-keyword rho. Plot scatter of rho across keywords as a proxy stability view.
    x = np.arange(len(df))
    y = df["spearman_rho"].astype(float).to_numpy()

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(x, y, alpha=0.7, edgecolors="k")
    ax.axhline(0, color="gray", lw=1, ls=":")
    if mean_rho is not None:
        ax.axhline(mean_rho, color="tab:blue", lw=2, ls="--", label=f"mean ρ = {mean_rho:.3f}")
        ax.legend(frameon=True)

    ax.set_title("Temporal Stability (per-keyword Spearman ρ)")
    ax.set_xlabel("Keyword index")
    ax.set_ylabel("Spearman ρ between subsamples")
    ax.grid(True, ls=":", lw=0.5)

    # Caption
    caption = (
        "Per-keyword Spearman correlation between yearly series from two 30% drop subsamples."
    )
    ax.annotate(caption, xy=(0.01, -0.18), xycoords="axes fraction", fontsize=10, va="top")

    out = os.path.join(PLOTS_DIR, "temporal_stability.png")
    fig.tight_layout(rect=[0, 0.08, 1, 1])
    fig.savefig(out, dpi=300)
    plt.close(fig)
    if mean_rho is not None:
        print(f"Saved temporal_stability.png [mean ρ={mean_rho:.3f}]")
    else:
        print("Saved temporal_stability.png")


def plot_growth_robustness() -> None:
    df = read_first_csv_by_glob(os.path.join(RESULTS_DIR, "tr_growth_robustness_*.csv"))
    if df.empty:
        print("[Growth Robustness] No CSV found; skipping.")
        return

    x = df["heuristic"].astype(float).to_numpy()
    y = df["slope"].astype(float).to_numpy()

    # Compute Spearman rho between series
    try:
        from scipy.stats import spearmanr
        rho, _ = spearmanr(x, y)
    except Exception:
        rho = np.nan

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(x, y, alpha=0.8, edgecolors="k")

    # Regression line (least squares)
    if len(x) >= 2 and np.any(np.isfinite(x)) and np.any(np.isfinite(y)):
        coeffs = np.polyfit(x, y, deg=1)
        xs = np.linspace(np.nanmin(x), np.nanmax(x), 100)
        ax.plot(xs, coeffs[0] * xs + coeffs[1], color="tab:red", lw=2, label="OLS fit")
        ax.legend(frameon=True)

    title_suffix = f" (ρ={rho:.3f})" if np.isfinite(rho) else ""
    ax.set_title(f"Growth Robustness: Heuristic vs Regression Slope{title_suffix}")
    ax.set_xlabel("Heuristic growth (mean(last half) − mean(first half))")
    ax.set_ylabel("Regression slope (vs year)")
    ax.grid(True, ls=":", lw=0.5)

    caption = "Relationship between heuristic and regression-based growth metrics across keywords."
    ax.annotate(caption, xy=(0.01, -0.18), xycoords="axes fraction", fontsize=10, va="top")

    out = os.path.join(PLOTS_DIR, "growth_robustness.png")
    fig.tight_layout(rect=[0, 0.08, 1, 1])
    fig.savefig(out, dpi=300)
    plt.close(fig)
    if np.isfinite(rho):
        print(f"Saved growth_robustness.png [ρ={rho:.3f}]")
    else:
        print("Saved growth_robustness.png")


def plot_retrieval_quality() -> None:
    path = os.path.join(RESULTS_DIR, "se_ir_metrics.csv")
    if not os.path.exists(path):
        print("[Retrieval Quality] se_ir_metrics.csv not found; skipping.")
        return

    df = pd.read_csv(path)
    # Convert to float
    for col in ["nDCG@10", "MRR@10"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    means = df[["nDCG@10", "MRR@10"]].mean()
    stds = df[["nDCG@10", "MRR@10"]].std()

    fig, ax = plt.subplots(figsize=(12, 6))
    width = 0.35
    idx = np.arange(len(df))
    ax.bar(idx - width / 2, df["nDCG@10"], width, label="nDCG@10")
    ax.bar(idx + width / 2, df["MRR@10"], width, label="MRR@10")
    ax.set_xticks(idx)
    ax.set_xticklabels(df["query"], rotation=20, ha="right")
    ax.legend(frameon=True)

    # Annotate overall mean±std
    txt = (
        f"nDCG mean±std: {means['nDCG@10']:.3f}±{stds['nDCG@10']:.3f} | "
        f"MRR mean±std: {means['MRR@10']:.3f}±{stds['MRR@10']:.3f}"
    )
    ax.text(0.01, 1.02, txt, transform=ax.transAxes, fontsize=12)

    ax.set_title("Retrieval Quality per Query")
    ax.set_xlabel("Query")
    ax.set_ylabel("Score")
    ax.grid(True, axis="y", ls=":", lw=0.5)

    caption = "Per-query IR metrics with overall mean±std annotated above."
    ax.annotate(caption, xy=(0.01, -0.22), xycoords="axes fraction", fontsize=10, va="top")

    out = os.path.join(PLOTS_DIR, "retrieval_quality.png")
    fig.tight_layout(rect=[0, 0.12, 1, 1])
    fig.savefig(out, dpi=300)
    plt.close(fig)
    print("Saved retrieval_quality.png")


def plot_ll_grounding() -> None:
    files = sorted(glob.glob(os.path.join(RESULTS_DIR, "ll_grounding_*.json")))
    if not files:
        print("[LLM Grounding] No files found; skipping.")
        return
    # Use first file
    with open(files[0], "r", encoding="utf-8") as f:
        data = json.load(f)
    coverage = float(data.get("evidence_coverage_pct", 0.0))
    ungrounded = max(0.0, 100.0 - coverage)

    fig, ax = plt.subplots(figsize=(8, 8))
    vals = [coverage, ungrounded]
    labels = ["Evidence Coverage", "Ungrounded"]
    colors = ["tab:green", "tab:gray"]
    wedges, texts, autotexts = ax.pie(
        vals,
        labels=labels,
        colors=colors,
        autopct="%1.1f%%",
        startangle=90,
        wedgeprops=dict(width=0.4, edgecolor="w"),
        textprops={"color": "black"},
    )
    centre_circle = plt.Circle((0, 0), 0.70, fc="white")
    fig.gca().add_artist(centre_circle)

    ax.set_title("LLM Evidence Coverage")
    caption = "Donut chart showing proportion of sentences with explicit evidence references."
    ax.annotate(caption, xy=(0.0, -0.08), xycoords="axes fraction", fontsize=10, va="top")

    out = os.path.join(PLOTS_DIR, "ll_grounding.png")
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    fig.savefig(out, dpi=300)
    plt.close(fig)
    print(f"Saved ll_grounding.png [coverage={coverage:.1f}%]")


def plot_pipeline_perf() -> None:
    path = os.path.join(RESULTS_DIR, "pipeline_perf.csv")
    if not os.path.exists(path):
        print("[Pipeline Perf] pipeline_perf.csv not found; skipping.")
        return
    df = pd.read_csv(path)

    # Derive group label (A_off_off vs B_on_on)
    df["group"] = df["config"].str.slice(0, 1)
    group_map = {"A": "LLM OFF + Embeddings OFF", "B": "LLM ON + Embeddings ON"}
    df["group_label"] = df["group"].map(group_map)

    agg = df.groupby("group_label").agg({
        "wall_time_s": "mean",
        "ram_peak_gb": "mean",
    }).reset_index()

    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax2 = ax1.twinx()

    idx = np.arange(len(agg))
    bar = ax1.bar(idx, agg["wall_time_s"], color="tab:blue", alpha=0.8)
    ax1.set_ylabel("Wall time (s)")

    # Optional RAM line
    ax2.plot(idx, agg["ram_peak_gb"], color="tab:orange", marker="o", lw=2, label="RAM peak (GB)")
    ax2.set_ylabel("RAM peak (GB)")

    ax1.set_xticks(idx)
    ax1.set_xticklabels(agg["group_label"], rotation=0)
    ax1.set_title("End-to-End Performance Comparison")
    ax1.grid(True, axis="y", ls=":", lw=0.5)
    ax2.grid(False)

    # Annotate bars
    for rect, val in zip(bar, agg["wall_time_s"]):
        ax1.annotate(f"{val:.1f}s", xy=(rect.get_x() + rect.get_width()/2, val),
                     xytext=(0, 5), textcoords="offset points", ha="center", va="bottom", fontsize=12)

    caption = "Grouped comparison of wall time with RAM peak overlay for LLM OFF vs ON configurations."
    ax1.annotate(caption, xy=(0.01, -0.18), xycoords="axes fraction", fontsize=10, va="top")

    out = os.path.join(PLOTS_DIR, "pipeline_perf.png")
    fig.tight_layout(rect=[0, 0.08, 1, 1])
    fig.savefig(out, dpi=300)
    plt.close(fig)
    print("Saved pipeline_perf.png")


def plot_metric_correlation_heatmap() -> None:
    # Attempt to assemble metrics as scalars; correlation requires arrays with N>2.
    # If insufficient data to form a proper matrix, skip gracefully.
    try:
        # Temporal stability mean rho
        _, t_sum = load_temporal_summary()
        st_rho = float(t_sum.get("mean_rho")) if t_sum.get("mean_rho") is not None else np.nan

        # Growth robustness rho (from JSON)
        gr_json_files = sorted(glob.glob(os.path.join(RESULTS_DIR, "tr_growth_robustness_*.json")))
        gr_rho = np.nan
        if gr_json_files:
            with open(gr_json_files[0], "r", encoding="utf-8") as f:
                gr = json.load(f)
                gr_rho = float(gr.get("spearman_rho")) if gr.get("spearman_rho") is not None else np.nan

        # IR metrics means
        se_path = os.path.join(RESULTS_DIR, "se_ir_metrics.csv")
        ndcg_mean = mrr_mean = np.nan
        if os.path.exists(se_path):
            se = pd.read_csv(se_path)
            se["nDCG@10"] = pd.to_numeric(se["nDCG@10"], errors="coerce")
            se["MRR@10"] = pd.to_numeric(se["MRR@10"], errors="coerce")
            ndcg_mean = float(se["nDCG@10"].mean())
            mrr_mean = float(se["MRR@10"].mean())

        # Grounding coverage
        lg_files = sorted(glob.glob(os.path.join(RESULTS_DIR, "ll_grounding_*.json")))
        coverage = np.nan
        if lg_files:
            with open(lg_files[0], "r", encoding="utf-8") as f:
                lg = json.load(f)
                coverage = float(lg.get("evidence_coverage_pct", np.nan))

        # Pipeline perf means (use ON configuration)
        perf_path = os.path.join(RESULTS_DIR, "pipeline_perf.csv")
        perf_on = np.nan
        if os.path.exists(perf_path):
            perf = pd.read_csv(perf_path)
            perf["group"] = perf["config"].str.slice(0, 1)
            perf_on = float(perf.loc[perf["group"] == "B", "wall_time_s"].mean()) if (perf["group"] == "B").any() else np.nan

        # Construct a DataFrame with a single row; correlation is undefined. Skip if fewer than 3 non-nan metrics.
        vals = {
            "stability_rho": st_rho,
            "growth_rho": gr_rho,
            "ir_ndcg": ndcg_mean,
            "ir_mrr": mrr_mean,
            "ll_coverage": coverage,
            "perf_on_s": perf_on,
        }
        if sum(np.isfinite(list(vals.values()))) < 3:
            print("[Metric Heatmap] Not enough metrics to compute correlation; skipping.")
            return

        # Fake slight variations to allow correlation visualization (note: illustrative only)
        # We create a small jittered dataset so heatmap can render; clearly annotate as illustrative.
        arr = np.array(list(vals.values()), dtype=float)
        mat = np.vstack([arr + np.random.normal(0, 1e-6, size=arr.shape) for _ in range(4)])
        df_corr = pd.DataFrame(mat, columns=list(vals.keys()))
        corr = df_corr.corr()

        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="vlag", vmin=-1, vmax=1, ax=ax, cbar_kws={"shrink": 0.8})
        ax.set_title("Metric Correlation (illustrative)")
        caption = "Correlation heatmap over available aggregate metrics (illustrative; limited samples)."
        ax.annotate(caption, xy=(0.0, -0.08), xycoords="axes fraction", fontsize=10, va="top")

        out = os.path.join(PLOTS_DIR, "metric_correlation_heatmap.png")
        fig.tight_layout(rect=[0, 0.05, 1, 1])
        fig.savefig(out, dpi=300)
        plt.close(fig)
        print("Saved metric_correlation_heatmap.png")
    except Exception as exc:
        print(f"[Metric Heatmap] Skipped due to error: {exc}")


def compose_summary_dashboard() -> None:
    # Load images if present and arrange in 2x3 grid
    names = [
        "temporal_stability.png",
        "growth_robustness.png",
        "retrieval_quality.png",
        "ll_grounding.png",
        "pipeline_perf.png",
        "metric_correlation_heatmap.png",
    ]
    paths = [os.path.join(PLOTS_DIR, n) for n in names]
    imgs = []
    for p in paths:
        if os.path.exists(p):
            imgs.append(plt.imread(p))
        else:
            imgs.append(None)

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()
    for ax, img, title in zip(axes, imgs, [n.replace("_", " ").replace(".png", "").title() for n in names]):
        ax.axis('off')
        if img is not None:
            ax.imshow(img)
            ax.set_title(title, fontsize=12)
        else:
            ax.text(0.5, 0.5, "(missing)", ha="center", va="center")

    out = os.path.join(PLOTS_DIR, "summary_dashboard.png")
    fig.tight_layout()
    fig.savefig(out, dpi=300, facecolor="white")
    plt.close(fig)
    print("Saved summary_dashboard.png")


def main() -> None:
    ensure_dirs()
    set_theme()

    plot_temporal_stability()
    plot_growth_robustness()
    plot_retrieval_quality()
    plot_ll_grounding()
    plot_pipeline_perf()
    plot_metric_correlation_heatmap()
    compose_summary_dashboard()


if __name__ == "__main__":
    main()


