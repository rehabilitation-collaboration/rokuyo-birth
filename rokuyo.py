"""Rokuyo (六曜) calculation from Gregorian dates via Japanese lunar calendar.

Uses qreki (旧暦計算) for accurate Japanese lunisolar calendar conversion.
lunardate (Chinese lunisolar) is used only for cross-checking.
"""

import datetime

from qreki import Kyureki

from definitions import ROKUYO_NAMES, ROKUYO_NAMES_JA

# qreki returns Japanese rokuyo names; map to our index
_QREKI_TO_INDEX = {
    "大安": 0, "赤口": 1, "先勝": 2, "友引": 3, "先負": 4, "仏滅": 5,
}


def calc_rokuyo_index(date: datetime.date) -> int:
    """Calculate rokuyo index for a given Gregorian date.

    Uses qreki for accurate Japanese lunar calendar conversion.
    0=Taian, 1=Shakku, 2=Sensho, 3=Tomobiki, 4=Senbu, 5=Butsumetsu
    """
    k = Kyureki.from_ymd(date.year, date.month, date.day)
    return _QREKI_TO_INDEX[k.rokuyou]


def calc_rokuyo(date: datetime.date) -> str:
    """Return the English rokuyo name for a given date."""
    return ROKUYO_NAMES[calc_rokuyo_index(date)]


def calc_rokuyo_ja(date: datetime.date) -> str:
    """Return the Japanese rokuyo name for a given date."""
    return ROKUYO_NAMES_JA[calc_rokuyo_index(date)]


def get_lunar_date(date: datetime.date) -> tuple[int, int, bool]:
    """Return (lunar_month, lunar_day, is_leap_month) from qreki.

    Leap months are represented as "閏N" in qreki output.
    """
    k = Kyureki.from_ymd(date.year, date.month, date.day)
    s = str(k)  # e.g. "2024年11月20日" or "2020年閏4月15日"
    parts = s.replace("年", "/").replace("月", "/").replace("日", "").split("/")
    month_str = parts[1]
    is_leap = month_str.startswith("閏")
    month = int(month_str.replace("閏", ""))
    day = int(parts[2])
    return month, day, is_leap


def cross_check_with_lunardate(
    start: datetime.date, end: datetime.date
) -> list[dict]:
    """Compare qreki vs lunardate for a date range. Returns mismatches.

    Useful for documenting divergence between Chinese and Japanese
    lunisolar calendars in the Methods section.
    """
    from lunardate import LunarDate

    mismatches = []
    current = start
    while current <= end:
        # qreki (Japanese)
        qreki_idx = calc_rokuyo_index(current)

        # lunardate (Chinese)
        ld = LunarDate.fromSolarDate(current.year, current.month, current.day)
        lunardate_idx = (ld.month + ld.day) % 6

        if qreki_idx != lunardate_idx:
            mismatches.append({
                "date": current,
                "qreki_rokuyo": ROKUYO_NAMES_JA[qreki_idx],
                "lunardate_rokuyo": ROKUYO_NAMES_JA[lunardate_idx],
                "qreki_lunar": get_lunar_date(current)[:2],
                "lunardate_lunar": (ld.month, ld.day),
            })
        current += datetime.timedelta(days=1)
    return mismatches
