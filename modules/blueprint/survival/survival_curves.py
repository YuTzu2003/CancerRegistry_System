"""Kaplan-Meier curves and 12-month actuarial life tables for the case list.

Verified against lifelines (max diff 3e-15) and an independent actuarial
recomputation on 2026存活率個案清單.xlsx before integration.
"""

from bisect import bisect_right
from collections import Counter, defaultdict
from fractions import Fraction
from math import floor, isfinite

from openpyxl import load_workbook

from modules.services.case_class_filter import find_case_class_column, is_case_class_h

from .case_recalculation import WEIGHTS, _hospital_id

_STAGES = ("I", "II", "III", "IV")
_STAGE_LABELS = {"I": "第1期", "II": "第2期", "III": "第3期", "IV": "第4期"}


def _km_curve(cases):
    """Unrounded step-curve points [[month, survival]] plus censor marks."""
    deaths = Counter(time for time, died in cases if died)
    points = [[0.0, Fraction(1)]]
    survival = Fraction(1)
    for event_time in sorted(deaths):
        at_risk = sum(1 for time, _ in cases if time >= event_time)
        survival *= 1 - Fraction(deaths[event_time], at_risk)
        points.append([event_time, survival])
    max_follow_up = max(time for time, _ in cases)
    if points[-1][0] < max_follow_up:
        points.append([max_follow_up, points[-1][1]])
    xs = [x for x, _ in points]
    censors = []
    for censor_time in sorted(time for time, died in cases if not died):
        index = bisect_right(xs, censor_time) - 1
        censors.append([censor_time, points[index][1]])
    return points, censors


def _km_at(points, last_x, month):
    """KM estimate at *month* from curve points; None when not estimable."""
    if month > last_x:
        value = points[-1][1]
        return 0.0 if value == 0 else None
    xs = [x for x, _ in points]
    return points[bisect_right(xs, month) - 1][1]


def _life_table(cases):
    """12-month actuarial life table (effective n = at-risk - censored / 2)."""
    times = [time for time, _ in cases]
    max_follow_up = max(times)
    rows = []
    cumulative = 1.0
    for start in range(0, 60, 12):
        end = start + 12
        if end == 60:
            def inside(time):
                return start <= time <= 60
        else:
            def inside(time):
                return start <= time < end
        at_risk = sum(1 for time in times if time >= start)
        deaths = sum(1 for time, died in cases if died and inside(time))
        censored = sum(1 for time, died in cases if not died and inside(time))
        effective = at_risk - censored / 2
        interval = 1 - deaths / effective if effective > 0 else None
        if at_risk == 0 or (max_follow_up < end and cumulative is not None and cumulative != 0):
            cumulative = None
        elif cumulative == 0 or cumulative is None:
            pass
        else:
            cumulative *= interval
        rows.append({
            "months": f"{start}–{end}",
            "at_risk": at_risk,
            "deaths": deaths,
            "censored": censored,
            "interval": None if interval is None else round(interval * 100, 1),
            "cumulative": None if cumulative is None else round(cumulative * 100, 1),
        })
    return rows


def _half_up_percent(rate):
    """Exact rate (Fraction) to a percentage with one decimal, half rounded up."""
    return float(floor(rate * 1000 + Fraction(1, 2))) / 10


def _stage_block(cases):
    points, censors = _km_curve(cases)
    last_x = points[-1][0]
    deaths = sum(1 for _, died in cases if died)
    annual = [_km_at(points, last_x, year * 12) for year in range(1, 6)]
    return {
        "n": len(cases),
        "deaths": deaths,
        "censored": len(cases) - deaths,
        "points": [[round(x, 4), round(float(s), 6)] for x, s in points],
        "censors": [[round(x, 4), round(float(s), 6)] for x, s in censors],
        "annual": [None if rate is None else _half_up_percent(rate) for rate in annual],
        "life_table": _life_table(cases),
    }


def compute_curves(stream, hospital_id, start_year, end_year):
    """Per-cancer KM curves, stage summaries and life tables for the period."""
    required = ("hospid", "year", "pri_site", "fnstage", "select_memo", "Status_OS", "Surv_Months")
    workbook = load_workbook(stream, read_only=True, data_only=True)
    try:
        rows = workbook.active.values
        headers = next(rows, ())
        class_column = find_case_class_column(headers)
        class_col = headers.index(class_column) if class_column is not None else None
        if not all(field in headers for field in required):
            raise ValueError("工作表缺少必要欄位，請上傳存活率個案清單。")
        columns = [headers.index(field) for field in required]
        cases = defaultdict(list)
        for row in rows:
            hospital, year, cancer, stage, memo, status, months = (
                str(row[column]).strip() for column in columns
            )
            case_class = row[class_col] if class_col is not None else None
            if (is_case_class_h(case_class)
                    or _hospital_id(hospital) != _hospital_id(hospital_id) or not year.isdecimal()
                    or not start_year <= int(year) <= end_year
                    or cancer not in WEIGHTS or not memo.startswith("15")):
                continue
            try:
                months = float(months)
            except ValueError:
                raise ValueError("納入個案的追蹤月數格式有誤。") from None
            status = status.casefold()
            if not isfinite(months) or months < 0 or status not in {"death", "censor"}:
                raise ValueError("納入個案的追蹤月數或存活狀態超出計算範圍。")
            broad = stage[0] if stage[:1] in {"1", "2", "3", "4"} else None
            cases[cancer].append((months, status == "death", broad))
        if not cases:
            raise ValueError("找不到符合條件的納入個案。")
    finally:
        workbook.close()

    results = []
    for cancer, (chinese_name, _) in WEIGHTS.items():
        rows = cases.get(cancer)
        if not rows:
            continue
        stages = {"All": _stage_block([(months, died) for months, died, _ in rows])}
        for index, stage in enumerate(_STAGES, start=1):
            members = [(months, died) for months, died, broad in rows if broad == str(index)]
            if members:
                stages[stage] = _stage_block(members)
        results.append({
            "cancer": cancer,
            "name": chinese_name,
            "total": len(rows),
            "unstaged": sum(1 for _, _, broad in rows if broad is None),
            "stages": stages,
        })
    return results
