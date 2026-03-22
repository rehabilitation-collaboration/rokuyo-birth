"""Phase 2: Descriptive statistics for rokuyo x birth analysis."""

from pathlib import Path

import pandas as pd

from data_loader import load_analysis_data
from definitions import ROKUYO_NAMES

RESULTS_DIR = Path(__file__).parent / "results"

# Ordered rokuyo names for consistent display
ROKUYO_ORDER = [ROKUYO_NAMES[i] for i in range(6)]
DOW_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def rokuyo_summary(df: pd.DataFrame, place: str = "total") -> pd.DataFrame:
    """Mean daily births by rokuyo for a given birth place.

    Returns DataFrame with columns: rokuyo, mean, std, median, n_days.
    """
    subset = df[df["birth_place"] == place]
    stats = (
        subset.groupby("rokuyo")["births"]
        .agg(["mean", "std", "median", "count"])
        .rename(columns={"count": "n_days"})
        .reindex(ROKUYO_ORDER)
        .reset_index()
    )
    return stats


def dow_summary(df: pd.DataFrame, place: str = "total") -> pd.DataFrame:
    """Mean daily births by day of week for a given birth place."""
    subset = df[df["birth_place"] == place]
    stats = (
        subset.groupby("dow")["births"]
        .agg(["mean", "std", "median", "count"])
        .rename(columns={"count": "n_days"})
        .reindex(DOW_ORDER)
        .reset_index()
    )
    return stats


def rokuyo_by_place(df: pd.DataFrame) -> pd.DataFrame:
    """Mean daily births by rokuyo for each birth place (wide format)."""
    places = ["total", "hospital", "clinic", "midwifery"]
    rows = []
    for rokuyo in ROKUYO_ORDER:
        row = {"rokuyo": rokuyo}
        for place in places:
            subset = df[(df["birth_place"] == place) & (df["rokuyo"] == rokuyo)]
            row[f"{place}_mean"] = subset["births"].mean()
            row[f"{place}_std"] = subset["births"].std()
        rows.append(row)
    return pd.DataFrame(rows)


def rokuyo_dow_crosstab(df: pd.DataFrame, place: str = "total") -> pd.DataFrame:
    """Mean daily births cross-tabulated by rokuyo (rows) x dow (columns)."""
    subset = df[df["birth_place"] == place]
    ct = subset.pivot_table(
        values="births", index="rokuyo", columns="dow", aggfunc="mean"
    )
    ct = ct.reindex(index=ROKUYO_ORDER, columns=DOW_ORDER)
    return ct


def overall_summary(df: pd.DataFrame) -> str:
    """Generate overall descriptive statistics text."""
    total = df[df["birth_place"] == "total"]
    lines = [
        "=" * 60,
        "DESCRIPTIVE STATISTICS: Rokuyo x Birth (2015-2024)",
        "=" * 60,
        "",
        "--- Dataset Overview ---",
        f"Date range: {total['date'].min()} to {total['date'].max()}",
        f"Total days: {len(total)}",
        f"Total births: {total['births'].sum():,}",
        f"Mean daily births: {total['births'].mean():.1f} (SD {total['births'].std():.1f})",
        f"Median daily births: {total['births'].median():.0f}",
        f"Range: {total['births'].min():,} - {total['births'].max():,}",
        "",
    ]

    # Rokuyo summary (total)
    lines.append("--- Mean Daily Births by Rokuyo (Total) ---")
    rs = rokuyo_summary(total.assign(birth_place="total"), "total")
    for _, row in rs.iterrows():
        lines.append(
            f"  {row['rokuyo']:<12s}: {row['mean']:7.1f} (SD {row['std']:6.1f})  "
            f"n={int(row['n_days'])} days"
        )

    # Rokuyo ratio vs Taian
    taian_mean = rs.loc[rs["rokuyo"] == "Taian", "mean"].values[0]
    lines.append(f"\n  Reference (Taian) mean: {taian_mean:.1f}")
    for _, row in rs.iterrows():
        ratio = row["mean"] / taian_mean
        diff_pct = (ratio - 1) * 100
        lines.append(
            f"  {row['rokuyo']:<12s}: ratio={ratio:.4f} ({diff_pct:+.2f}%)"
        )

    # Day-of-week summary
    lines.append("\n--- Mean Daily Births by Day of Week (Total) ---")
    ds = dow_summary(total.assign(birth_place="total"), "total")
    for _, row in ds.iterrows():
        lines.append(
            f"  {row['dow']:<12s}: {row['mean']:7.1f} (SD {row['std']:6.1f})  "
            f"n={int(row['n_days'])} days"
        )

    # Rokuyo by place
    lines.append("\n--- Mean Daily Births by Rokuyo and Birth Place ---")
    rbp = rokuyo_by_place(df)
    header = f"  {'Rokuyo':<12s} {'Total':>10s} {'Hospital':>10s} {'Clinic':>10s} {'Midwifery':>10s}"
    lines.append(header)
    lines.append("  " + "-" * (len(header) - 2))
    for _, row in rbp.iterrows():
        lines.append(
            f"  {row['rokuyo']:<12s} {row['total_mean']:10.1f} {row['hospital_mean']:10.1f} "
            f"{row['clinic_mean']:10.1f} {row['midwifery_mean']:10.1f}"
        )

    # Rokuyo x DOW crosstab
    lines.append("\n--- Rokuyo x Day-of-Week Cross-tabulation (Mean Daily Births, Total) ---")
    ct = rokuyo_dow_crosstab(df)
    lines.append(ct.round(1).to_string())

    lines.append("")
    return "\n".join(lines)


def main():
    df = load_analysis_data()

    RESULTS_DIR.mkdir(exist_ok=True)
    output_path = RESULTS_DIR / "descriptive_stats.txt"

    report = overall_summary(df)
    output_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()
