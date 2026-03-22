"""Phase 3: Negative binomial regression for rokuyo x birth analysis."""

from pathlib import Path

import jpholiday
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

from data_loader import load_analysis_data
from definitions import ALPHA, ROKUYO_NAMES, ROKUYO_REFERENCE

RESULTS_DIR = Path(__file__).parent / "results"

ROKUYO_DUMMIES = [name for name in ROKUYO_NAMES.values() if name != ROKUYO_REFERENCE]


def prepare_model_data(df: pd.DataFrame, place: str = "total") -> pd.DataFrame:
    """Prepare design matrix for negative binomial regression.

    Filters to a single birth place and creates dummy variables.
    """
    subset = df[df["birth_place"] == place].copy()

    # Rokuyo dummies (ref: Taian)
    rokuyo_dummies = pd.get_dummies(subset["rokuyo"], prefix="rok", dtype=float)
    ref_col = f"rok_{ROKUYO_REFERENCE}"
    if ref_col in rokuyo_dummies.columns:
        rokuyo_dummies = rokuyo_dummies.drop(columns=[ref_col])

    # Day-of-week dummies (ref: first available, preferring Monday)
    dow_dummies = pd.get_dummies(subset["dow"], prefix="dow", dtype=float)
    dow_ref = "dow_Monday" if "dow_Monday" in dow_dummies.columns else dow_dummies.columns[0]
    dow_dummies = dow_dummies.drop(columns=[dow_ref])

    # Month dummies (ref: first available, preferring January)
    subset["month_str"] = subset["month"].apply(lambda m: f"m{m:02d}")
    month_dummies = pd.get_dummies(subset["month_str"], prefix="", prefix_sep="", dtype=float)
    month_ref = "m01" if "m01" in month_dummies.columns else month_dummies.columns[0]
    month_dummies = month_dummies.drop(columns=[month_ref])

    # Year (linear trend, centered)
    subset["year_c"] = subset["year"] - subset["year"].median()

    # Holiday indicator: national holidays only (weekends already captured by DOW dummies)
    subset["holiday"] = subset["date"].apply(
        lambda d: float(jpholiday.is_holiday(d))
    )

    # Combine
    X = pd.concat([rokuyo_dummies, dow_dummies, month_dummies, subset[["year_c", "holiday"]]], axis=1)

    # Drop zero-variance columns (can occur in filtered subsets)
    zero_var = X.columns[X.std() == 0]
    if len(zero_var) > 0:
        X = X.drop(columns=zero_var)

    X = sm.add_constant(X)

    return subset, X


def fit_negative_binomial(df: pd.DataFrame, place: str = "total") -> sm.GenericLikelihoodModelResults:
    """Fit negative binomial regression model."""
    subset, X = prepare_model_data(df, place)
    y = subset["births"]

    model = sm.NegativeBinomial(y, X, loglike_method="nb2")
    try:
        result = model.fit(disp=False, maxiter=200)
    except np.linalg.LinAlgError:
        # Fallback to BFGS for near-singular design matrices (e.g., filtered subsets)
        result = model.fit(disp=False, maxiter=500, method="bfgs")
    return result


def extract_rokuyo_results(result, apply_correction: bool = True) -> pd.DataFrame:
    """Extract rokuyo coefficients as Rate Ratios with CIs and p-values."""
    params = result.params
    conf = result.conf_int()
    pvalues = result.pvalues

    rows = []
    rokuyo_cols = [c for c in params.index if c.startswith("rok_")]

    for col in rokuyo_cols:
        rokuyo_name = col.replace("rok_", "")
        coef = params[col]
        ci_low, ci_high = conf.loc[col]
        p = pvalues[col]

        rows.append({
            "rokuyo": rokuyo_name,
            "coef": coef,
            "RR": np.exp(coef),
            "RR_lower": np.exp(ci_low),
            "RR_upper": np.exp(ci_high),
            "p_value": p,
        })

    df_results = pd.DataFrame(rows)

    # Holm correction for multiple comparisons
    if apply_correction and len(df_results) > 0:
        _, p_corrected, _, _ = multipletests(df_results["p_value"], method="holm")
        df_results["p_holm"] = p_corrected

    # Add reference category
    ref_row = pd.DataFrame([{
        "rokuyo": ROKUYO_REFERENCE,
        "coef": 0.0,
        "RR": 1.0,
        "RR_lower": np.nan,
        "RR_upper": np.nan,
        "p_value": np.nan,
        "p_holm": np.nan,
    }])
    df_results = pd.concat([ref_row, df_results], ignore_index=True)

    return df_results


def model_diagnostics(result) -> dict:
    """Extract model diagnostic statistics."""
    return {
        "n_obs": int(result.nobs),
        "log_likelihood": result.llf,
        "aic": result.aic,
        "bic": result.bic,
        "alpha": result.params.get("alpha", np.nan),
        "converged": result.mle_retvals.get("converged", False),
    }


def format_results_table(rokuyo_df: pd.DataFrame, diag: dict, place: str) -> str:
    """Format results as readable text."""
    lines = [
        f"--- {place.upper()} ---",
        f"N observations: {diag['n_obs']}",
        f"Log-likelihood: {diag['log_likelihood']:.1f}",
        f"AIC: {diag['aic']:.1f}  BIC: {diag['bic']:.1f}",
        f"Alpha (overdispersion): {diag['alpha']:.4f}",
        f"Converged: {diag['converged']}",
        "",
        f"{'Rokuyo':<12s} {'RR':>6s} {'95% CI':>16s} {'p-value':>10s} {'p(Holm)':>10s} {'Sig':>4s}",
        "-" * 62,
    ]

    for _, row in rokuyo_df.iterrows():
        if row["rokuyo"] == ROKUYO_REFERENCE:
            lines.append(f"{row['rokuyo']:<12s} {'1.000':>6s} {'(reference)':>16s}")
        else:
            sig = ""
            p_holm = row["p_holm"]
            if p_holm < 0.001:
                sig = "***"
            elif p_holm < 0.01:
                sig = "**"
            elif p_holm < ALPHA:
                sig = "*"
            lines.append(
                f"{row['rokuyo']:<12s} {row['RR']:6.4f} "
                f"({row['RR_lower']:.4f}-{row['RR_upper']:.4f}) "
                f"{row['p_value']:10.4f} {p_holm:10.4f} {sig:>4s}"
            )

    return "\n".join(lines)


def run_main_analysis(df: pd.DataFrame) -> str:
    """Run full analysis pipeline: total + subgroups."""
    lines = [
        "=" * 70,
        "MAIN ANALYSIS: Negative Binomial Regression",
        "Rokuyo effect on daily births (2015-2024)",
        f"Reference category: {ROKUYO_REFERENCE} (most auspicious day)",
        "Covariates: day-of-week, holiday, month, year (linear trend)",
        "=" * 70,
        "",
    ]

    all_results = {}
    places = [
        ("total", "All birth places combined"),
        ("hospital", "Hospital births only"),
        ("clinic", "Clinic births only"),
        ("midwifery", "Midwifery births only (negative control: no C-sections)"),
    ]

    for place, desc in places:
        print(f"Fitting model for {place}...")
        result = fit_negative_binomial(df, place)
        rokuyo_df = extract_rokuyo_results(result)
        diag = model_diagnostics(result)

        lines.append(f"[{desc}]")
        lines.append(format_results_table(rokuyo_df, diag, place))
        lines.append("")

        all_results[place] = {
            "model": result,
            "rokuyo": rokuyo_df,
            "diagnostics": diag,
        }

    # Day-of-week effects (total model only)
    total_result = all_results["total"]["model"]
    lines.append("--- DAY-OF-WEEK EFFECTS (Total, for comparison) ---")
    dow_cols = [c for c in total_result.params.index if c.startswith("dow_")]
    lines.append(f"{'Day':<12s} {'RR':>6s} {'95% CI':>16s} {'p-value':>10s}")
    lines.append("-" * 48)
    lines.append(f"{'Monday':<12s} {'1.000':>6s} {'(reference)':>16s}")
    conf = total_result.conf_int()
    for col in dow_cols:
        day = col.replace("dow_", "")
        rr = np.exp(total_result.params[col])
        ci_lo = np.exp(conf.loc[col, 0])
        ci_hi = np.exp(conf.loc[col, 1])
        p = total_result.pvalues[col]
        lines.append(f"{day:<12s} {rr:6.4f} ({ci_lo:.4f}-{ci_hi:.4f}) {p:10.4f}")

    # Holiday effect
    lines.append("")
    hol_rr = np.exp(total_result.params["holiday"])
    hol_ci = np.exp(conf.loc["holiday"])
    hol_p = total_result.pvalues["holiday"]
    lines.append(f"Holiday effect: RR={hol_rr:.4f} ({hol_ci[0]:.4f}-{hol_ci[1]:.4f}), p={hol_p:.4f}")

    lines.append("")
    return "\n".join(lines), all_results


def main():
    df = load_analysis_data()

    RESULTS_DIR.mkdir(exist_ok=True)
    output_path = RESULTS_DIR / "main_analysis.txt"

    report, results = run_main_analysis(df)
    output_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()
