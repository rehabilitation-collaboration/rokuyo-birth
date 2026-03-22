"""Load birth data from e-Stat API, aggregate to daily counts, and add calendar labels."""

import datetime
import json
import os
from pathlib import Path

import jpholiday
import pandas as pd
import requests
from dotenv import load_dotenv

from definitions import (
    BIRTH_PLACE,
    BIRTH_PLACE_JA_TO_EN,
    DOW_REFERENCE,
    ESTAT_API_URL,
    ESTAT_PAGE_LIMIT,
    ESTAT_STATS_DATA_ID,
    YEAR_RANGE_API,
)
from rokuyo import calc_rokuyo, calc_rokuyo_index

DATA_DIR = Path(__file__).parent / "data"
CACHE_FILE = DATA_DIR / "estat_raw.parquet"
ENV_PATH = Path(__file__).parent / ".env"

# e-Stat dimension code mappings
# Pattern: 00100=total, 00110=first item, 00120=second, ..., incrementing by 10
_HOUR_CODES = {"00100": "total"} | {
    f"{110 + i * 10:05d}": str(i) for i in range(24)
}  # 00110=0h .. 00340=23h

_DAY_CODES = {"00100": "total"} | {
    f"{110 + i * 10:05d}": str(i + 1) for i in range(31)
}  # 00110=1d .. 00410=31d

_MONTH_CODES = {"00100": "total"} | {
    f"{110 + i * 10:05d}": str(i + 1) for i in range(12)
}  # 00110=1m .. 00220=12m

_PLACE_CODES = {
    "000000": "total",
    "001100": "hospital",
    "001200": "clinic",
    "001400": "midwifery",
    "002100": "home",
    "002200": "other",
}

_YEAR_CODES = {f"{y}000000": y for y in range(2015, 2025)}


def _load_appid() -> str:
    load_dotenv(ENV_PATH)
    appid = os.getenv("ESTAT_API_APPID")
    if not appid:
        raise RuntimeError("ESTAT_API_APPID not found in .env")
    return appid


def fetch_estat_raw(use_cache: bool = True) -> pd.DataFrame:
    """Fetch all records from e-Stat API with pagination. Returns raw DataFrame.

    Caches to parquet to avoid repeated API calls.
    """
    if use_cache and CACHE_FILE.exists():
        return pd.read_parquet(CACHE_FILE)

    appid = _load_appid()
    all_records = []
    start_pos = 1

    while True:
        params = {
            "appId": appid,
            "statsDataId": ESTAT_STATS_DATA_ID,
            "limit": ESTAT_PAGE_LIMIT,
            "startPosition": start_pos,
        }
        resp = requests.get(ESTAT_API_URL, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        stat_data = data["GET_STATS_DATA"]["STATISTICAL_DATA"]
        values = stat_data["DATA_INF"]["VALUE"]
        all_records.extend(values)

        result_inf = stat_data.get("RESULT_INF", {})
        total = result_inf.get("TOTAL_NUMBER", 0)
        to_number = result_inf.get("TO_NUMBER", 0)
        next_key = result_inf.get("NEXT_KEY")

        print(f"  Fetched {to_number}/{total} records...")

        if next_key is None or to_number >= total:
            break
        start_pos = int(next_key)

    df = pd.DataFrame(all_records)
    DATA_DIR.mkdir(exist_ok=True)
    df.to_parquet(CACHE_FILE, index=False)
    print(f"  Cached {len(df)} records to {CACHE_FILE}")
    return df


def parse_estat_raw(df: pd.DataFrame) -> pd.DataFrame:
    """Parse raw e-Stat data into structured DataFrame.

    Filters out 'total' rows for hour/day/month dimensions,
    keeps all birth place categories.
    """
    records = []
    for _, row in df.iterrows():
        hour_code = row["@cat01"]
        day_code = row["@cat02"]
        month_code = row["@cat03"]
        place_code = row["@cat04"]
        year_code = row["@time"]
        value = row["$"]

        # Skip summary rows
        if hour_code == "00100" or day_code == "00100" or month_code == "00100":
            continue

        hour = _HOUR_CODES.get(hour_code)
        day = _DAY_CODES.get(day_code)
        month = _MONTH_CODES.get(month_code)
        place = _PLACE_CODES.get(place_code)
        year = _YEAR_CODES.get(year_code)

        if any(v is None for v in (hour, day, month, place, year)):
            continue

        # Skip unknown hour
        if hour == "unknown":
            continue

        births = int(value) if value not in ("-", "…", "x", "") else 0

        records.append({
            "year": year,
            "month": int(month),
            "day": int(day),
            "hour": int(hour),
            "birth_place": place,
            "births": births,
        })

    return pd.DataFrame(records)


def aggregate_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate hourly data to daily totals by birth place.

    Also filters out invalid dates (e.g., Feb 30).
    """
    daily = (
        df.groupby(["year", "month", "day", "birth_place"])["births"]
        .sum()
        .reset_index()
    )

    # Validate dates and create date column
    valid_rows = []
    for _, row in daily.iterrows():
        try:
            date = datetime.date(row["year"], row["month"], row["day"])
            valid_rows.append({**row.to_dict(), "date": date})
        except ValueError:
            # Invalid date (e.g., Feb 30, Apr 31)
            continue

    return pd.DataFrame(valid_rows)


def add_calendar_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Add rokuyo, day-of-week, holiday labels to daily data."""
    df = df.copy()

    df["rokuyo_index"] = df["date"].apply(calc_rokuyo_index)
    df["rokuyo"] = df["date"].apply(calc_rokuyo)
    df["dow"] = df["date"].apply(lambda d: d.strftime("%A"))
    df["dow_num"] = df["date"].apply(lambda d: d.weekday())  # 0=Mon
    df["is_holiday"] = df["date"].apply(
        lambda d: jpholiday.is_holiday(d) or d.weekday() == 6  # Sun or national holiday
    )
    df["is_weekend"] = df["date"].apply(lambda d: d.weekday() >= 5)

    return df


def load_analysis_data(use_cache: bool = True) -> pd.DataFrame:
    """Full pipeline: fetch → parse → aggregate daily → add labels.

    Returns:
        DataFrame with columns: year, month, day, birth_place, births,
        date, rokuyo_index, rokuyo, dow, dow_num, is_holiday, is_weekend
    """
    print("Loading e-Stat data...")
    raw = fetch_estat_raw(use_cache=use_cache)
    print(f"  Raw records: {len(raw)}")

    print("Parsing...")
    parsed = parse_estat_raw(raw)
    print(f"  Parsed records: {len(parsed)}")

    print("Aggregating to daily...")
    daily = aggregate_daily(parsed)
    print(f"  Daily records: {len(daily)}")

    print("Adding calendar labels...")
    labeled = add_calendar_labels(daily)
    print(f"  Final records: {len(labeled)}")

    return labeled


if __name__ == "__main__":
    df = load_analysis_data(use_cache=True)
    print(f"\nDataset shape: {df.shape}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"Birth places: {df['birth_place'].unique()}")
    print(f"\nSample (total, first 5 rows):")
    sample = df[df["birth_place"] == "total"].head()
    print(sample[["date", "births", "rokuyo", "dow", "is_holiday"]].to_string())
