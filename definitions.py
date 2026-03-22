"""Rokuyo and birth data definitions and constants."""

# Rokuyo (六曜) definitions
# Derived from lunar calendar: (lunar_month + lunar_day) % 6
ROKUYO_NAMES = {
    0: "Taian",      # 大安 (Great Safety)
    1: "Shakku",     # 赤口 (Red Mouth)
    2: "Sensho",     # 先勝 (First Win)
    3: "Tomobiki",   # 友引 (Friend Pull)
    4: "Senbu",      # 先負 (First Loss)
    5: "Butsumetsu",  # 仏滅 (Buddha's Death)
}

ROKUYO_NAMES_JA = {
    0: "大安",
    1: "赤口",
    2: "先勝",
    3: "友引",
    4: "先負",
    5: "仏滅",
}

ROKUYO_INDEX = {name: idx for idx, name in ROKUYO_NAMES.items()}

# Reference category for regression (most auspicious day)
ROKUYO_REFERENCE = "Taian"

# Birth place categories in e-Stat data
BIRTH_PLACE = {
    "total": "総数",
    "hospital": "病院",
    "clinic": "診療所",
    "midwifery": "助産所",
    "home": "自宅",
    "other": "その他",
}

BIRTH_PLACE_JA_TO_EN = {v: k for k, v in BIRTH_PLACE.items()}

# e-Stat API configuration
ESTAT_API_URL = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
ESTAT_STATS_DATA_ID = "0003411915"
ESTAT_PAGE_LIMIT = 100_000

# Analysis period
YEAR_RANGE_API = (2015, 2024)
YEAR_RANGE_CSV = (1980, 2014)

# Day-of-week reference category for regression
DOW_REFERENCE = "Monday"

# Special periods to exclude in sensitivity analysis
NEW_YEAR_RANGE = (12, 29, 1, 3)  # Dec 29 - Jan 3
OBON_DATES = [(8, 13), (8, 14), (8, 15), (8, 16)]
GOLDEN_WEEK_DATES = [(4, 29), (4, 30), (5, 1), (5, 2), (5, 3), (5, 4), (5, 5)]

# Daytime hours for sensitivity analysis (proxy for scheduled deliveries)
DAYTIME_HOURS = range(9, 17)  # 9:00-16:59

# Statistical constants
ALPHA = 0.05
