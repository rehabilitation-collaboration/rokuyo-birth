"""Phase 2 & 5: Figures for rokuyo x birth analysis."""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from analysis import extract_rokuyo_results, fit_negative_binomial
from data_loader import load_analysis_data
from definitions import ROKUYO_NAMES, ROKUYO_REFERENCE
from exploratory import DOW_ORDER, ROKUYO_ORDER, rokuyo_dow_crosstab, rokuyo_summary
from sensitivity import sensitivity_5_temporal_trend

RESULTS_DIR = Path(__file__).parent / "results"

# Use non-interactive backend for PDF compatibility
matplotlib.use("Agg")

# Consistent color palette: warm for auspicious, cool for inauspicious
ROKUYO_COLORS = {
    "Taian": "#d62728",       # red (most auspicious)
    "Tomobiki": "#ff7f0e",    # orange
    "Sensho": "#2ca02c",      # green
    "Senbu": "#1f77b4",       # blue
    "Shakku": "#9467bd",      # purple
    "Butsumetsu": "#7f7f7f",  # gray (most inauspicious)
}


def fig1_rokuyo_barplot(df: pd.DataFrame, save: bool = True) -> plt.Figure:
    """Figure 1: Mean daily births by rokuyo, with subpanels by birth place.

    4-panel plot: Total, Hospital, Clinic, Midwifery.
    """
    places = [
        ("total", "Total"),
        ("hospital", "Hospital"),
        ("clinic", "Clinic"),
        ("midwifery", "Midwifery"),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    axes = axes.flatten()

    for ax, (place, title) in zip(axes, places):
        stats = rokuyo_summary(df, place)
        colors = [ROKUYO_COLORS[r] for r in stats["rokuyo"]]

        ax.bar(
            range(len(stats)),
            stats["mean"],
            yerr=stats["std"] / np.sqrt(stats["n_days"]),  # SE
            color=colors,
            capsize=3,
            edgecolor="black",
            linewidth=0.5,
        )

        ax.set_xticks(range(len(stats)))
        ax.set_xticklabels(ROKUYO_ORDER, fontsize=8, rotation=15)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.set_ylabel("Mean daily births")

        # Highlight reference (Taian) with dashed line
        taian_mean = stats.loc[stats["rokuyo"] == "Taian", "mean"].values[0]
        ax.axhline(taian_mean, color="#d62728", linestyle="--", linewidth=0.8, alpha=0.5)

    fig.suptitle(
        "Figure 1: Mean Daily Births by Rokuyo (2015-2024)",
        fontsize=14, fontweight="bold", y=0.98,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.95])

    if save:
        RESULTS_DIR.mkdir(exist_ok=True)
        for ext in ("png", "pdf"):
            fig.savefig(RESULTS_DIR / f"fig1_rokuyo_barplot.{ext}", dpi=300, bbox_inches="tight")
        print(f"Saved Figure 1 to {RESULTS_DIR}/fig1_rokuyo_barplot.png/pdf")

    return fig


def fig2_rokuyo_dow_heatmap(df: pd.DataFrame, save: bool = True) -> plt.Figure:
    """Figure 2: Rokuyo x Day-of-Week heatmap of mean daily births."""
    ct = rokuyo_dow_crosstab(df, place="total")

    fig, ax = plt.subplots(figsize=(10, 5))

    sns.heatmap(
        ct,
        annot=True,
        fmt=".0f",
        cmap="RdYlBu_r",
        linewidths=0.5,
        ax=ax,
        cbar_kws={"label": "Mean daily births"},
    )

    ax.set_yticklabels(ROKUYO_ORDER, rotation=0)
    ax.set_xlabel("Day of Week", fontsize=11)
    ax.set_ylabel("Rokuyo", fontsize=11)
    ax.set_title(
        "Figure 2: Mean Daily Births by Rokuyo and Day of Week (2015-2024)",
        fontsize=13, fontweight="bold",
    )

    plt.tight_layout()

    if save:
        RESULTS_DIR.mkdir(exist_ok=True)
        for ext in ("png", "pdf"):
            fig.savefig(RESULTS_DIR / f"fig2_rokuyo_dow_heatmap.{ext}", dpi=300, bbox_inches="tight")
        print(f"Saved Figure 2 to {RESULTS_DIR}/fig2_rokuyo_dow_heatmap.png/pdf")

    return fig


def _get_rokuyo_results_by_place(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Fit NB models and extract rokuyo RR for each birth place."""
    places = ["total", "hospital", "clinic", "midwifery"]
    results = {}
    for place in places:
        print(f"  Fitting model for {place}...")
        model = fit_negative_binomial(df, place)
        results[place] = extract_rokuyo_results(model)
    return results


def fig3_forest_plot(df: pd.DataFrame, save: bool = True) -> plt.Figure:
    """Figure 3: Forest plot of rokuyo RR by birth place.

    Rows = rokuyo categories (excluding reference Taian).
    Columns/groups = Total, Hospital, Clinic, Midwifery.
    """
    place_results = _get_rokuyo_results_by_place(df)

    places = ["total", "hospital", "clinic", "midwifery"]
    place_labels = {"total": "Total", "hospital": "Hospital",
                    "clinic": "Clinic", "midwifery": "Midwifery"}
    place_markers = {"total": "D", "hospital": "o", "clinic": "s", "midwifery": "^"}
    place_colors = {"total": "#1f77b4", "hospital": "#ff7f0e",
                    "clinic": "#2ca02c", "midwifery": "#d62728"}

    # Rokuyo categories (exclude reference)
    rokuyo_cats = [r for r in ROKUYO_ORDER if r != ROKUYO_REFERENCE]
    n_rokuyo = len(rokuyo_cats)
    n_places = len(places)

    fig, ax = plt.subplots(figsize=(8, 6))

    # Vertical positions for rokuyo categories, grouped with place offsets
    group_gap = 1.2
    place_offsets = np.linspace(-0.3, 0.3, n_places)

    y_positions = []
    y_labels = []

    for i, rokuyo in enumerate(rokuyo_cats):
        y_base = i * group_gap
        y_labels.append(rokuyo)
        y_positions.append(y_base)

        for j, place in enumerate(places):
            rdf = place_results[place]
            row = rdf[rdf["rokuyo"] == rokuyo]
            if row.empty:
                continue
            row = row.iloc[0]

            y = y_base + place_offsets[j]
            rr = row["RR"]
            ci_lo = row["RR_lower"]
            ci_hi = row["RR_upper"]

            ax.errorbar(
                rr, y,
                xerr=[[rr - ci_lo], [ci_hi - rr]],
                fmt=place_markers[place],
                color=place_colors[place],
                markersize=7,
                capsize=3,
                linewidth=1.2,
                label=place_labels[place] if i == 0 else None,
            )

    # Reference line at RR=1.0
    ax.axvline(1.0, color="black", linestyle="--", linewidth=0.8, alpha=0.6)

    ax.set_yticks(y_positions)
    ax.set_yticklabels(y_labels, fontsize=10)
    ax.set_xlabel("Rate Ratio (95% CI)", fontsize=11)
    ax.set_title(
        "Figure 3: Rokuyo Effect on Daily Births by Birth Place\n"
        f"(ref: {ROKUYO_REFERENCE}, adjusted for DOW, holiday, month, year)",
        fontsize=12, fontweight="bold",
    )
    ax.legend(loc="lower right", fontsize=9)
    ax.invert_yaxis()

    plt.tight_layout()

    if save:
        RESULTS_DIR.mkdir(exist_ok=True)
        for ext in ("png", "pdf"):
            fig.savefig(RESULTS_DIR / f"fig3_forest_plot.{ext}", dpi=300, bbox_inches="tight")
        print(f"Saved Figure 3 to {RESULTS_DIR}/fig3_forest_plot.png/pdf")

    return fig


def fig4_temporal_trend(df: pd.DataFrame, save: bool = True) -> plt.Figure:
    """Figure 4: Temporal trend of rokuyo effect (5-year blocks)."""
    trend_results = sensitivity_5_temporal_trend(df)

    rokuyo_cats = [r for r in ROKUYO_ORDER if r != ROKUYO_REFERENCE]
    periods = list(trend_results.keys())  # ["2015-2019", "2020-2024"]

    fig, ax = plt.subplots(figsize=(8, 5))

    x_pos = np.arange(len(periods))

    for i, rokuyo in enumerate(rokuyo_cats):
        rrs = []
        ci_los = []
        ci_his = []

        for period in periods:
            rdf = trend_results[period]["rokuyo"]
            row = rdf[rdf["rokuyo"] == rokuyo].iloc[0]
            rrs.append(row["RR"])
            ci_los.append(row["RR"] - row["RR_lower"])
            ci_his.append(row["RR_upper"] - row["RR"])

        color = ROKUYO_COLORS[rokuyo]
        offset = (i - len(rokuyo_cats) / 2 + 0.5) * 0.08

        ax.errorbar(
            x_pos + offset, rrs,
            yerr=[ci_los, ci_his],
            fmt="o-",
            color=color,
            markersize=6,
            capsize=3,
            linewidth=1.5,
            label=rokuyo,
        )

    ax.axhline(1.0, color="black", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(periods, fontsize=11)
    ax.set_xlabel("Period", fontsize=11)
    ax.set_ylabel("Rate Ratio (95% CI)", fontsize=11)
    ax.set_title(
        "Figure 4: Temporal Trend of Rokuyo Effect on Daily Births\n"
        f"(ref: {ROKUYO_REFERENCE}, 5-year blocks)",
        fontsize=12, fontweight="bold",
    )
    ax.legend(loc="lower left", fontsize=9, ncol=2)

    plt.tight_layout()

    if save:
        RESULTS_DIR.mkdir(exist_ok=True)
        for ext in ("png", "pdf"):
            fig.savefig(RESULTS_DIR / f"fig4_temporal_trend.{ext}", dpi=300, bbox_inches="tight")
        print(f"Saved Figure 4 to {RESULTS_DIR}/fig4_temporal_trend.png/pdf")

    return fig


def main():
    df = load_analysis_data()
    print("Generating Figure 1...")
    fig1_rokuyo_barplot(df)
    print("Generating Figure 2...")
    fig2_rokuyo_dow_heatmap(df)
    print("Generating Figure 3...")
    fig3_forest_plot(df)
    print("Generating Figure 4...")
    fig4_temporal_trend(df)
    plt.close("all")
    print("All figures generated.")


if __name__ == "__main__":
    main()
