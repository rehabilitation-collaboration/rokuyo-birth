"""Phase 5: Publication-ready tables for rokuyo x birth analysis."""

from pathlib import Path

import numpy as np
import pandas as pd

from analysis import extract_rokuyo_results, fit_negative_binomial, model_diagnostics
from data_loader import load_analysis_data
from definitions import ALPHA, ROKUYO_REFERENCE
from exploratory import ROKUYO_ORDER, rokuyo_by_place, rokuyo_summary
from sensitivity import (
    sensitivity_1_exclude_holiday_adjacent,
    sensitivity_2_exclude_special_periods,
    sensitivity_3_weekday_stratified,
    sensitivity_5_temporal_trend,
)

RESULTS_DIR = Path(__file__).parent / "results"


def _fmt_rr(row: pd.Series) -> str:
    """Format RR (95% CI) string."""
    if row["rokuyo"] == ROKUYO_REFERENCE:
        return "1.000 (ref)"
    return f"{row['RR']:.3f} ({row['RR_lower']:.3f}-{row['RR_upper']:.3f})"


def _fmt_p(p: float) -> str:
    """Format p-value with significance markers."""
    if pd.isna(p):
        return "-"
    if p < 0.001:
        return "<0.001***"
    if p < 0.01:
        return f"{p:.3f}**"
    if p < ALPHA:
        return f"{p:.3f}*"
    return f"{p:.3f}"


def table1_descriptive(df: pd.DataFrame) -> tuple[str, str]:
    """Table 1: Descriptive statistics by rokuyo and birth place.

    Returns (markdown, latex) strings.
    """
    rbp = rokuyo_by_place(df)
    total_stats = rokuyo_summary(df, "total")

    # Markdown
    md_lines = [
        "| Rokuyo | N days | Total | Hospital | Clinic | Midwifery |",
        "|--------|--------|-------|----------|--------|-----------|",
    ]
    for _, row in rbp.iterrows():
        rokuyo = row["rokuyo"]
        n_days = int(total_stats.loc[total_stats["rokuyo"] == rokuyo, "n_days"].values[0])
        md_lines.append(
            f"| {rokuyo} | {n_days} | "
            f"{row['total_mean']:.1f} ({row['total_std']:.1f}) | "
            f"{row['hospital_mean']:.1f} ({row['hospital_std']:.1f}) | "
            f"{row['clinic_mean']:.1f} ({row['clinic_std']:.1f}) | "
            f"{row['midwifery_mean']:.1f} ({row['midwifery_std']:.1f}) |"
        )
    md = "\n".join(md_lines)

    # LaTeX
    tex_lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Mean daily births (SD) by rokuyo and birth place, 2015--2024}",
        r"\label{tab:descriptive}",
        r"\begin{tabular}{lrcccc}",
        r"\toprule",
        r"Rokuyo & N days & Total & Hospital & Clinic & Midwifery \\",
        r"\midrule",
    ]
    for _, row in rbp.iterrows():
        rokuyo = row["rokuyo"]
        n_days = int(total_stats.loc[total_stats["rokuyo"] == rokuyo, "n_days"].values[0])
        tex_lines.append(
            f"{rokuyo} & {n_days} & "
            f"{row['total_mean']:.1f} ({row['total_std']:.1f}) & "
            f"{row['hospital_mean']:.1f} ({row['hospital_std']:.1f}) & "
            f"{row['clinic_mean']:.1f} ({row['clinic_std']:.1f}) & "
            f"{row['midwifery_mean']:.1f} ({row['midwifery_std']:.1f}) \\\\"
        )
    tex_lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    tex = "\n".join(tex_lines)

    return md, tex


def table2_main_analysis(df: pd.DataFrame) -> tuple[str, str]:
    """Table 2: Main analysis results (RR by birth place).

    Returns (markdown, latex) strings.
    """
    places = [
        ("total", "Total"),
        ("hospital", "Hospital"),
        ("clinic", "Clinic"),
        ("midwifery", "Midwifery"),
    ]

    place_data = {}
    for place, label in places:
        model = fit_negative_binomial(df, place)
        rdf = extract_rokuyo_results(model)
        diag = model_diagnostics(model)
        place_data[place] = {"rokuyo": rdf, "diag": diag, "label": label}

    # Markdown
    md_lines = [
        "| Rokuyo | Total | Hospital | Clinic | Midwifery |",
        "|--------|-------|----------|--------|-----------|",
    ]
    for rokuyo in ROKUYO_ORDER:
        cols = [rokuyo]
        for place, _ in places:
            rdf = place_data[place]["rokuyo"]
            row = rdf[rdf["rokuyo"] == rokuyo].iloc[0]
            if rokuyo == ROKUYO_REFERENCE:
                cols.append("1.000 (ref)")
            else:
                sig = ""
                if row["p_holm"] < 0.001:
                    sig = "***"
                elif row["p_holm"] < 0.01:
                    sig = "**"
                elif row["p_holm"] < ALPHA:
                    sig = "*"
                cols.append(
                    f"{row['RR']:.4f} ({row['RR_lower']:.4f}-{row['RR_upper']:.4f}){sig}"
                )
        md_lines.append("| " + " | ".join(cols) + " |")

    # Add N and AIC
    md_lines.append("|--------|-------|----------|--------|-----------|")
    n_row = ["N"]
    aic_row = ["AIC"]
    for place, _ in places:
        d = place_data[place]["diag"]
        n_row.append(str(d["n_obs"]))
        aic_row.append(f"{d['aic']:.0f}")
    md_lines.append("| " + " | ".join(n_row) + " |")
    md_lines.append("| " + " | ".join(aic_row) + " |")
    md = "\n".join(md_lines)

    # LaTeX
    tex_lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Rate ratios (95\% CI) of daily births by rokuyo, negative binomial regression}",
        r"\label{tab:main_analysis}",
        r"\begin{tabular}{lcccc}",
        r"\toprule",
        r"Rokuyo & Total & Hospital & Clinic & Midwifery \\",
        r"\midrule",
    ]
    for rokuyo in ROKUYO_ORDER:
        cols = [rokuyo]
        for place, _ in places:
            rdf = place_data[place]["rokuyo"]
            row = rdf[rdf["rokuyo"] == rokuyo].iloc[0]
            cols.append(_fmt_rr(row))
        tex_lines.append(" & ".join(cols) + r" \\")
    tex_lines += [
        r"\midrule",
    ]
    n_row = ["N"]
    aic_row = ["AIC"]
    for place, _ in places:
        d = place_data[place]["diag"]
        n_row.append(f"{d['n_obs']}")
        aic_row.append(f"{d['aic']:.0f}")
    tex_lines.append(" & ".join(n_row) + r" \\")
    tex_lines.append(" & ".join(aic_row) + r" \\")
    tex_lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    tex = "\n".join(tex_lines)

    return md, tex


def table3_sensitivity(df: pd.DataFrame) -> tuple[str, str]:
    """Table 3: Sensitivity analysis summary.

    Returns (markdown, latex) strings.
    """
    print("Running sensitivity analyses for Table 3...")
    analyses = {}

    print("  S1: Exclude holiday-adjacent...")
    analyses["S1"] = sensitivity_1_exclude_holiday_adjacent(df)
    print("  S2: Exclude special periods...")
    analyses["S2"] = sensitivity_2_exclude_special_periods(df)
    print("  S3: Weekday/weekend stratification...")
    s3 = sensitivity_3_weekday_stratified(df)
    analyses["S3a"] = s3["weekday"]
    analyses["S3b"] = s3["weekend"]
    print("  S5: Temporal trend...")
    s5 = sensitivity_5_temporal_trend(df)
    for period_label, period_data in s5.items():
        analyses[f"S5:{period_label}"] = period_data

    labels = {
        "S1": "Excl. holiday-adjacent",
        "S2": "Excl. special periods",
        "S3a": "Weekdays only",
        "S3b": "Weekends only",
        "S5:2015-2019": "2015-2019",
        "S5:2020-2024": "2020-2024",
    }

    # Markdown: rows = analyses, columns = rokuyo RR + min p
    rokuyo_cats = [r for r in ROKUYO_ORDER if r != ROKUYO_REFERENCE]
    header = "| Analysis | N | " + " | ".join(rokuyo_cats) + " | Min p(Holm) |"
    sep = "|" + "|".join(["--------"] * (len(rokuyo_cats) + 3)) + "|"
    md_lines = [header, sep]

    for key, info in analyses.items():
        rdf = info["rokuyo"]
        non_ref = rdf[rdf["rokuyo"] != ROKUYO_REFERENCE]
        min_p = non_ref["p_holm"].min()
        cols = [labels[key], str(info["n_days"])]
        for rokuyo in rokuyo_cats:
            row = rdf[rdf["rokuyo"] == rokuyo]
            if row.empty:
                cols.append("-")
            else:
                row = row.iloc[0]
                sig = "*" if row["p_holm"] < ALPHA else ""
                cols.append(f"{row['RR']:.3f}{sig}")
        cols.append(_fmt_p(min_p))
        md_lines.append("| " + " | ".join(cols) + " |")
    md = "\n".join(md_lines)

    # LaTeX
    n_cols = len(rokuyo_cats)
    col_spec = "l r " + "c " * n_cols + "c"
    tex_lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Sensitivity analyses: rate ratios by rokuyo (ref: Taian)}",
        r"\label{tab:sensitivity}",
        f"\\begin{{tabular}}{{{col_spec}}}",
        r"\toprule",
        "Analysis & N & " + " & ".join(rokuyo_cats) + r" & Min $p_\mathrm{Holm}$ \\",
        r"\midrule",
    ]
    for key, info in analyses.items():
        rdf = info["rokuyo"]
        non_ref = rdf[rdf["rokuyo"] != ROKUYO_REFERENCE]
        min_p = non_ref["p_holm"].min()
        cols = [labels[key], str(info["n_days"])]
        for rokuyo in rokuyo_cats:
            row = rdf[rdf["rokuyo"] == rokuyo]
            if row.empty:
                cols.append("--")
            else:
                row = row.iloc[0]
                sig = "*" if row["p_holm"] < ALPHA else ""
                cols.append(f"{row['RR']:.3f}{sig}")
        if min_p < 0.001:
            cols.append("$<$0.001")
        else:
            cols.append(f"{min_p:.3f}")
        tex_lines.append(" & ".join(cols) + r" \\")
    tex_lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    tex = "\n".join(tex_lines)

    return md, tex


def main():
    df = load_analysis_data()
    RESULTS_DIR.mkdir(exist_ok=True)

    print("Generating Table 1: Descriptive statistics...")
    md1, tex1 = table1_descriptive(df)

    print("Generating Table 2: Main analysis...")
    md2, tex2 = table2_main_analysis(df)

    print("Generating Table 3: Sensitivity analyses...")
    md3, tex3 = table3_sensitivity(df)

    # Save Markdown
    md_path = RESULTS_DIR / "tables.md"
    md_content = "\n\n".join([
        "# Tables for Rokuyo x Birth Analysis\n",
        "## Table 1: Descriptive Statistics\n", md1,
        "\n## Table 2: Main Analysis (Negative Binomial Regression)\n", md2,
        "\n## Table 3: Sensitivity Analyses\n", md3,
    ])
    md_path.write_text(md_content, encoding="utf-8")
    print(f"Saved Markdown tables to {md_path}")

    # Save LaTeX
    tex_path = RESULTS_DIR / "tables.tex"
    tex_content = "\n\n".join([
        "% Tables for Rokuyo x Birth Analysis",
        "% Table 1: Descriptive Statistics", tex1,
        "% Table 2: Main Analysis", tex2,
        "% Table 3: Sensitivity Analyses", tex3,
    ])
    tex_path.write_text(tex_content, encoding="utf-8")
    print(f"Saved LaTeX tables to {tex_path}")


if __name__ == "__main__":
    main()
