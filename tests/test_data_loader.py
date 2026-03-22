"""Tests for data loading pipeline."""

import datetime
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from data_loader import (
    _DAY_CODES,
    _HOUR_CODES,
    _MONTH_CODES,
    _PLACE_CODES,
    _YEAR_CODES,
    aggregate_daily,
    load_analysis_data,
    parse_estat_raw,
)


class TestCodeMappings:
    def test_hour_codes_count(self):
        # 24 hours + total = 25
        assert len(_HOUR_CODES) == 25

    def test_day_codes_count(self):
        # 31 days + total = 32
        assert len(_DAY_CODES) == 32

    def test_month_codes_count(self):
        # 12 months + total = 13
        assert len(_MONTH_CODES) == 13

    def test_place_codes_count(self):
        assert len(_PLACE_CODES) == 6

    def test_year_codes_count(self):
        assert len(_YEAR_CODES) == 10

    def test_hour_codes_values(self):
        assert _HOUR_CODES["00100"] == "total"
        assert _HOUR_CODES["00110"] == "0"
        assert _HOUR_CODES["00340"] == "23"

    def test_day_codes_values(self):
        assert _DAY_CODES["00100"] == "total"
        assert _DAY_CODES["00110"] == "1"
        assert _DAY_CODES["00410"] == "31"

    def test_month_codes_values(self):
        assert _MONTH_CODES["00100"] == "total"
        assert _MONTH_CODES["00110"] == "1"
        assert _MONTH_CODES["00220"] == "12"


class TestFullPipeline:
    """Tests that require cached data (skip if not available)."""

    @pytest.fixture(scope="class")
    def daily_data(self):
        cache = Path(__file__).parent.parent / "data" / "estat_raw.parquet"
        if not cache.exists():
            pytest.skip("Cached data not available")
        return load_analysis_data(use_cache=True)

    def test_date_range(self, daily_data):
        assert daily_data["date"].min() == datetime.date(2015, 1, 1)
        assert daily_data["date"].max() == datetime.date(2024, 12, 31)

    def test_expected_row_count(self, daily_data):
        # 6 birth places * ~3653 days
        assert len(daily_data) > 20_000

    def test_unique_dates(self, daily_data):
        total = daily_data[daily_data["birth_place"] == "total"]
        assert total["date"].nunique() == 3653

    def test_birth_places(self, daily_data):
        places = set(daily_data["birth_place"].unique())
        assert places == {"total", "hospital", "clinic", "midwifery", "home", "other"}

    def test_no_negative_births(self, daily_data):
        assert (daily_data["births"] >= 0).all()

    def test_rokuyo_columns_present(self, daily_data):
        for col in ["rokuyo_index", "rokuyo", "dow", "dow_num", "is_holiday", "is_weekend"]:
            assert col in daily_data.columns

    def test_rokuyo_index_range(self, daily_data):
        assert daily_data["rokuyo_index"].min() >= 0
        assert daily_data["rokuyo_index"].max() <= 5

    def test_place_sum_equals_total(self, daily_data):
        """Sum of place-specific births should equal total for each date."""
        sample_dates = daily_data["date"].unique()[:10]
        for d in sample_dates:
            day_data = daily_data[daily_data["date"] == d]
            total_val = day_data[day_data["birth_place"] == "total"]["births"].values[0]
            place_sum = day_data[day_data["birth_place"] != "total"]["births"].sum()
            assert place_sum == total_val, f"Mismatch on {d}: {place_sum} != {total_val}"

    def test_no_missing_dates(self, daily_data):
        """Total should have an entry for every date in the range."""
        total = daily_data[daily_data["birth_place"] == "total"]
        dates = pd.to_datetime(total["date"])
        expected = pd.date_range("2015-01-01", "2024-12-31")
        missing = expected.difference(dates)
        assert len(missing) == 0, f"Missing dates: {missing[:5]}"
