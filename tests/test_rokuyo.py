"""Tests for rokuyo calculation accuracy.

Ground truth data sourced from:
- himekuricalendar.com (2024 Jan, Jul; 2020 Feb)
- zexy.net rokki calendar (2024)
- rokuyou.net (individual date lookups)
- Cross-validated against multiple Japanese calendar sites

Uses qreki (Japanese lunisolar calendar) as primary calculation engine.
"""

import datetime
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from definitions import ROKUYO_NAMES, ROKUYO_NAMES_JA
from rokuyo import calc_rokuyo, calc_rokuyo_index, calc_rokuyo_ja, get_lunar_date


# Ground truth: (date, expected_rokuyo_ja)
# Verified against himekuricalendar.com, zexy.net, rokuyou.net
KNOWN_ROKUYO = [
    # 2024 January (full month verified 31/31)
    (datetime.date(2024, 1, 1), "赤口"),
    (datetime.date(2024, 1, 6), "大安"),
    (datetime.date(2024, 1, 11), "赤口"),  # lunar month boundary
    (datetime.date(2024, 1, 15), "仏滅"),
    (datetime.date(2024, 1, 22), "大安"),
    (datetime.date(2024, 1, 28), "大安"),
    (datetime.date(2024, 1, 31), "友引"),
    # 2024 July (full month verified 31/31)
    (datetime.date(2024, 7, 1), "赤口"),
    (datetime.date(2024, 7, 6), "赤口"),  # lunar month boundary
    (datetime.date(2024, 7, 11), "大安"),
    (datetime.date(2024, 7, 17), "大安"),
    (datetime.date(2024, 7, 23), "大安"),
    (datetime.date(2024, 7, 29), "大安"),
    (datetime.date(2024, 7, 31), "先勝"),
    # 2020 February — lunardate diverges here (Chinese vs Japanese lunar)
    (datetime.date(2020, 2, 23), "赤口"),  # lunardate gives 友引 (wrong)
    (datetime.date(2020, 2, 29), "先勝"),  # leap day; lunardate gives 友引 (wrong)
    # Edge cases: year boundaries
    (datetime.date(2023, 12, 31), "大安"),
    (datetime.date(2015, 1, 1), "先負"),
]


@pytest.mark.parametrize("date, expected_ja", KNOWN_ROKUYO)
def test_rokuyo_against_ground_truth(date, expected_ja):
    """Verify rokuyo calculation matches published calendar data."""
    assert calc_rokuyo_ja(date) == expected_ja


def test_rokuyo_index_range():
    """Rokuyo index must be 0-5 for any date."""
    start = datetime.date(2015, 1, 1)
    for i in range(365 * 3):
        d = start + datetime.timedelta(days=i)
        idx = calc_rokuyo_index(d)
        assert 0 <= idx <= 5, f"Index out of range for {d}: {idx}"


def test_rokuyo_names_mapping():
    """All 6 rokuyo names must be defined."""
    assert len(ROKUYO_NAMES) == 6
    assert len(ROKUYO_NAMES_JA) == 6
    for i in range(6):
        assert i in ROKUYO_NAMES
        assert i in ROKUYO_NAMES_JA


def test_get_lunar_date_returns_valid():
    """Lunar month must be 1-12, day 1-30."""
    d = datetime.date(2024, 6, 15)
    month, day, is_leap = get_lunar_date(d)
    assert 1 <= month <= 12
    assert 1 <= day <= 30
    assert isinstance(is_leap, bool)


def test_calc_rokuyo_english():
    """English name must be one of the defined names."""
    name = calc_rokuyo(datetime.date(2024, 1, 1))
    assert name in ROKUYO_NAMES.values()


def test_lunar_month_boundary_resets_rokuyo():
    """At lunar month boundaries, rokuyo resets (day=1 → index = (month+1)%6)."""
    # Lunar new year 2024: Feb 10 → lunar 1/1 → (1+1)%6 = 2 (先勝)
    d = datetime.date(2024, 2, 10)
    month, day, _ = get_lunar_date(d)
    assert month == 1 and day == 1, f"Expected lunar 1/1, got {month}/{day}"
    assert calc_rokuyo_index(d) == 2  # (1+1)%6 = 先勝


def test_full_january_2024():
    """Full validation of January 2024 (31 days)."""
    expected = [
        "赤口", "先勝", "友引", "先負", "仏滅", "大安",
        "赤口", "先勝", "友引", "先負", "赤口", "先勝",
        "友引", "先負", "仏滅", "大安", "赤口", "先勝",
        "友引", "先負", "仏滅", "大安", "赤口", "先勝",
        "友引", "先負", "仏滅", "大安", "赤口", "先勝",
        "友引",
    ]
    for day_idx, exp in enumerate(expected):
        d = datetime.date(2024, 1, day_idx + 1)
        assert calc_rokuyo_ja(d) == exp, f"Mismatch on {d}"


def test_full_july_2024():
    """Full validation of July 2024 (31 days)."""
    expected = [
        "赤口", "先勝", "友引", "先負", "仏滅", "赤口",
        "先勝", "友引", "先負", "仏滅", "大安", "赤口",
        "先勝", "友引", "先負", "仏滅", "大安", "赤口",
        "先勝", "友引", "先負", "仏滅", "大安", "赤口",
        "先勝", "友引", "先負", "仏滅", "大安", "赤口",
        "先勝",
    ]
    for day_idx, exp in enumerate(expected):
        d = datetime.date(2024, 7, day_idx + 1)
        assert calc_rokuyo_ja(d) == exp, f"Mismatch on {d}"
