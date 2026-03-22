"""Phase 4: Sensitivity analyses and temporal trend for rokuyo x birth."""

import datetime
from pathlib import Path

import jpholiday
import numpy as np
import pandas as pd

from analysis import extract_rokuyo_results, fit_negative_binomial, model_diagnostics
from data_loader import (
    add_calendar_labels,
    aggregate_daily,
    fetch_estat_raw,
    load_analysis_data,
    parse_estat_raw,
)
from definitions import (
    ALPHA,
    DAYTIME_HOURS,
    GOLDEN_WEEK_DATES,
    NEW_YEAR_RANGE,
    OBON_DATES,
    ROKUYO_REFERENCE,
)

RESULTS_DIR = Path(__file__).parent / "results"


# --- Exclusion filters ---

def _holiday_adjacent_dates(df: pd.DataFrame) -> set:
    """Dates that are national holidays or adjacent (1 day before/after).

    Uses jpholiday only (excludes weekends from holiday definition).
    """
    national_holidays = set()
    for d in df["date"].unique():
        if jpholiday.is_holiday(d):
            national_holidays.add(d)

    adjacent = set()
    for d in national_holidays:
        adjacent.add(d - datetime.timedelta(days=1))
        adjacent.add(d)
        adjacent.add(d + datetime.timedelta(days=1))
    return adjacent


def _special_period_dates(df: pd.DataFrame) -> set:
    """New Year (12/29-1/3), Golden Week, Obon dates."""
    dates = set()
    for d in df["date"].unique():
        m, day = d.month, d.day
        # New Year: Dec 29 - Jan 3
        ny_start_m, ny_start_d, ny_end_m, ny_end_d = NEW_YEAR_RANGE
        if (m == ny_start_m and day >= ny_start_d) or (m == ny_end_m and day <= ny_end_d):
            dates.add(d)
        if (m, day) in GOLDEN_WEEK_DATES:
            dates.add(d)
        if (m, day) in OBON_DATES:
            dates.add(d)
    return dates


# --- Sensitivity analysis runners ---

def sensitivity_1_exclude_holiday_adjacent(df: pd.DataFrame) -> dict:
    """Exclude holidays and their adjacent days (+/- 1 day)."""
    exclude = _holiday_adjacent_dates(df)
    filtered = df[~df["date"].isin(exclude)]
    return _run_and_extract(filtered, "S1: Exclude holiday-adjacent")


def sensitivity_2_exclude_special_periods(df: pd.DataFrame) -> dict:
    """Exclude New Year, Golden Week, and Obon periods."""
    exclude = _special_period_dates(df)
    filtered = df[~df["date"].isin(exclude)]
    return _run_and_extract(filtered, "S2: Exclude special periods")


def sensitivity_3_weekday_stratified(df: pd.DataFrame) -> dict:
    """Stratified by weekday vs weekend."""
    weekday = df[~df["is_weekend"]]
    weekend = df[df["is_weekend"]]
    results_wd = _run_and_extract(weekday, "S3a: Weekdays only")
    results_we = _run_and_extract(weekend, "S3b: Weekends only")
    return {"weekday": results_wd, "weekend": results_we}


def sensitivity_4_daytime_vs_night(df_hourly: pd.DataFrame) -> dict:
    """Daytime (9-17h, proxy for scheduled) vs nighttime births.

    Requires hourly-level parsed data, not the daily aggregate.
    """
    df_hourly = df_hourly.copy()
    df_hourly["is_daytime"] = df_hourly["hour"].isin(DAYTIME_HOURS)

    daytime = df_hourly[df_hourly["is_daytime"]]
    night = df_hourly[~df_hourly["is_daytime"]]

    # Aggregate each to daily totals
    day_daily = _aggregate_and_label(daytime)
    night_daily = _aggregate_and_label(night)

    results_day = _run_and_extract(day_daily, "S4a: Daytime (9-17h)")
    results_night = _run_and_extract(night_daily, "S4b: Nighttime")
    return {"daytime": results_day, "nighttime": results_night}


def sensitivity_5_temporal_trend(df: pd.DataFrame) -> dict:
    """5-year stratified analysis to detect temporal changes."""
    periods = [
        ("2015-2019", range(2015, 2020)),
        ("2020-2024", range(2020, 2025)),
    ]
    results = {}
    for label, years in periods:
        subset = df[df["year"].isin(years)]
        results[label] = _run_and_extract(subset, f"S5: {label}")
    return results


# --- Helpers ---

def _aggregate_and_label(df_hourly: pd.DataFrame) -> pd.DataFrame:
    """Aggregate hourly data to daily and add calendar labels."""
    daily = (
        df_hourly.groupby(["year", "month", "day", "birth_place"])["births"]
        .sum()
        .reset_index()
    )
    valid_rows = []
    for _, row in daily.iterrows():
        try:
            date = datetime.date(row["year"], row["month"], row["day"])
            valid_rows.append({**row.to_dict(), "date": date})
        except ValueError:
            continue
    result = pd.DataFrame(valid_rows)
    return add_calendar_labels(result)


def _run_and_extract(df: pd.DataFrame, label: str) -> dict:
    """Fit NB model on total births and extract rokuyo results."""
    n_days = len(df[df["birth_place"] == "total"])
    print(f"  {label}: {n_days} days")
    result = fit_negative_binomial(df, "total")
    rokuyo_df = extract_rokuyo_results(result)
    diag = model_diagnostics(result)
    return {"label": label, "rokuyo": rokuyo_df, "diagnostics": diag, "n_days": n_days}


# --- Formatting ---

def _format_one(info: dict) -> str:
    """Format a single sensitivity result."""
    lines = [
        f"  [{info['label']}]",
        f"  N={info['n_days']} days, AIC={info['diagnostics']['aic']:.0f}, "
        f"converged={info['diagnostics']['converged']}",
    ]
    rokuyo_df = info["rokuyo"]
    non_ref = rokuyo_df[rokuyo_df["rokuyo"] != ROKUYO_REFERENCE]
    for _, row in non_ref.iterrows():
        sig = "*" if row["p_holm"] < ALPHA else ""
        lines.append(
            f"    {row['rokuyo']:<12s} RR={row['RR']:.4f} "
            f"({row['RR_lower']:.4f}-{row['RR_upper']:.4f}) "
            f"p(Holm)={row['p_holm']:.4f} {sig}"
        )
    return "\n".join(lines)


def format_all_results(results: dict) -> str:
    """Format all sensitivity analysis results."""
    lines = [
        "=" * 70,
        "SENSITIVITY ANALYSES: Rokuyo x Birth (2015-2024)",
        f"Reference: {ROKUYO_REFERENCE}, Model: Negative Binomial",
        "=" * 70,
        "",
    ]

    for key, val in results.items():
        if isinstance(val, dict) and "label" in val:
            lines.append(_format_one(val))
        elif isinstance(val, dict):
            for sub_key, sub_val in val.items():
                lines.append(_format_one(sub_val))
        lines.append("")

    # Summary table
    lines.append("--- SUMMARY: Any significant rokuyo effect across analyses? ---")
    lines.append(f"{'Analysis':<35s} {'Min p(Holm)':>12s} {'Significant?':>13s}")
    lines.append("-" * 62)

    for key, val in results.items():
        items = []
        if isinstance(val, dict) and "label" in val:
            items = [(val["label"], val)]
        elif isinstance(val, dict):
            items = [(v["label"], v) for v in val.values()]
        for label, info in items:
            non_ref = info["rokuyo"][info["rokuyo"]["rokuyo"] != ROKUYO_REFERENCE]
            min_p = non_ref["p_holm"].min()
            sig = "YES" if min_p < ALPHA else "No"
            lines.append(f"{label:<35s} {min_p:12.4f} {sig:>13s}")

    lines.append("")
    return "\n".join(lines)


def main():
    print("Loading data...")
    df = load_analysis_data()

    print("Loading hourly data for sensitivity 4...")
    raw = fetch_estat_raw()
    parsed = parse_estat_raw(raw)

    results = {}

    print("\nSensitivity 1: Exclude holiday-adjacent...")
    results["s1"] = sensitivity_1_exclude_holiday_adjacent(df)

    print("Sensitivity 2: Exclude special periods...")
    results["s2"] = sensitivity_2_exclude_special_periods(df)

    print("Sensitivity 3: Weekday/weekend stratification...")
    results["s3"] = sensitivity_3_weekday_stratified(df)

    print("Sensitivity 4: Daytime vs nighttime...")
    results["s4"] = sensitivity_4_daytime_vs_night(parsed)

    print("Sensitivity 5: Temporal trend (5-year blocks)...")
    results["s5"] = sensitivity_5_temporal_trend(df)

    RESULTS_DIR.mkdir(exist_ok=True)
    report = format_all_results(results)
    output_path = RESULTS_DIR / "sensitivity.txt"
    output_path.write_text(report, encoding="utf-8")
    print(f"\n{report}")
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    main()
