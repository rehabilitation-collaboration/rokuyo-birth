"""Tests for negative binomial regression analysis."""

import numpy as np
import pytest

from analysis import (
    extract_rokuyo_results,
    fit_negative_binomial,
    model_diagnostics,
    prepare_model_data,
)
from data_loader import load_analysis_data
from definitions import ROKUYO_REFERENCE


@pytest.fixture(scope="module")
def df():
    return load_analysis_data()


@pytest.fixture(scope="module")
def total_result(df):
    return fit_negative_binomial(df, "total")


@pytest.fixture(scope="module")
def midwifery_result(df):
    return fit_negative_binomial(df, "midwifery")


class TestPrepareModelData:
    def test_output_shape(self, df):
        subset, X = prepare_model_data(df, "total")
        assert len(subset) == 3653
        assert len(X) == 3653

    def test_has_rokuyo_dummies(self, df):
        _, X = prepare_model_data(df, "total")
        rok_cols = [c for c in X.columns if c.startswith("rok_")]
        assert len(rok_cols) == 5  # 6 categories - 1 reference

    def test_reference_excluded(self, df):
        _, X = prepare_model_data(df, "total")
        assert f"rok_{ROKUYO_REFERENCE}" not in X.columns

    def test_has_dow_dummies(self, df):
        _, X = prepare_model_data(df, "total")
        dow_cols = [c for c in X.columns if c.startswith("dow_")]
        assert len(dow_cols) == 6  # 7 days - 1 reference

    def test_has_month_dummies(self, df):
        _, X = prepare_model_data(df, "total")
        month_cols = [c for c in X.columns if c.startswith("m")]
        assert len(month_cols) == 11  # 12 months - 1 reference

    def test_has_constant(self, df):
        _, X = prepare_model_data(df, "total")
        assert "const" in X.columns


class TestModelFit:
    def test_converged(self, total_result):
        assert total_result.mle_retvals.get("converged", False)

    def test_reasonable_n_obs(self, total_result):
        assert total_result.nobs == 3653

    def test_alpha_positive(self, total_result):
        assert total_result.params["alpha"] > 0

    def test_alpha_small(self, total_result):
        # Overdispersion should be modest for birth count data
        assert total_result.params["alpha"] < 0.1


class TestRokuyoResults:
    def test_reference_rr_is_one(self, total_result):
        rokuyo_df = extract_rokuyo_results(total_result)
        ref = rokuyo_df[rokuyo_df["rokuyo"] == ROKUYO_REFERENCE]
        assert ref["RR"].values[0] == 1.0

    def test_all_rr_near_one(self, total_result):
        rokuyo_df = extract_rokuyo_results(total_result)
        non_ref = rokuyo_df[rokuyo_df["rokuyo"] != ROKUYO_REFERENCE]
        # All RRs should be between 0.95 and 1.05 (small effects expected)
        assert (non_ref["RR"] > 0.95).all()
        assert (non_ref["RR"] < 1.05).all()

    def test_ci_contains_rr(self, total_result):
        rokuyo_df = extract_rokuyo_results(total_result)
        non_ref = rokuyo_df[rokuyo_df["rokuyo"] != ROKUYO_REFERENCE]
        for _, row in non_ref.iterrows():
            assert row["RR_lower"] <= row["RR"] <= row["RR_upper"]

    def test_ci_width_reasonable(self, total_result):
        rokuyo_df = extract_rokuyo_results(total_result)
        non_ref = rokuyo_df[rokuyo_df["rokuyo"] != ROKUYO_REFERENCE]
        widths = non_ref["RR_upper"] - non_ref["RR_lower"]
        # CIs should be narrow (< 0.05 width) given 3653 observations
        assert (widths < 0.05).all()

    def test_holm_correction_applied(self, total_result):
        rokuyo_df = extract_rokuyo_results(total_result, apply_correction=True)
        non_ref = rokuyo_df[rokuyo_df["rokuyo"] != ROKUYO_REFERENCE]
        # Holm-corrected p-values should be >= uncorrected
        assert (non_ref["p_holm"] >= non_ref["p_value"] - 1e-10).all()

    def test_five_comparisons(self, total_result):
        rokuyo_df = extract_rokuyo_results(total_result)
        non_ref = rokuyo_df[rokuyo_df["rokuyo"] != ROKUYO_REFERENCE]
        assert len(non_ref) == 5


class TestSubgroupComparison:
    def test_midwifery_wider_ci(self, total_result, midwifery_result):
        """Midwifery CIs should be wider due to smaller sample size."""
        total_rr = extract_rokuyo_results(total_result)
        mid_rr = extract_rokuyo_results(midwifery_result)

        total_non_ref = total_rr[total_rr["rokuyo"] != ROKUYO_REFERENCE]
        mid_non_ref = mid_rr[mid_rr["rokuyo"] != ROKUYO_REFERENCE]

        total_width = (total_non_ref["RR_upper"] - total_non_ref["RR_lower"]).mean()
        mid_width = (mid_non_ref["RR_upper"] - mid_non_ref["RR_lower"]).mean()

        assert mid_width > total_width


class TestDiagnostics:
    def test_diagnostics_keys(self, total_result):
        diag = model_diagnostics(total_result)
        expected_keys = {"n_obs", "log_likelihood", "aic", "bic", "alpha", "converged"}
        assert set(diag.keys()) == expected_keys

    def test_aic_finite(self, total_result):
        diag = model_diagnostics(total_result)
        assert np.isfinite(diag["aic"])
        assert np.isfinite(diag["bic"])
