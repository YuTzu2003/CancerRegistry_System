"""Executable numerator and denominator rules for indicators indicators."""
from __future__ import annotations

import re

import pandas as pd

from modules.blueprint.indicators.rules import _clean_code, _find_column


def _columns(frame):
    return {
        "surgery_code": _find_column(frame.columns, "4.1.4", ("申報醫院原發部位手術方式",)),
        "surgery_date": _find_column(frame.columns, "4.1.2", ("最確切的手術切除日期",)),
        "radiation_date": _find_column(frame.columns, "4.2.1.3", ("放射治療開始日期",)),
        "radiation_dose": _find_column(frame.columns, "4.2.2.2.2", ("最高放射劑量臨床標靶體積劑量",)),
        "chemotherapy": _find_column(frame.columns, "4.3.3", ("申報醫院化學治療",)),
        "chemotherapy_date": _find_column(frame.columns, "4.3.4", ("申報醫院化學治療開始日期",)),
        "palliative": _find_column(frame.columns, "4.4", ("申報醫院緩和照護",)),
        "survival": _find_column(frame.columns, "5.4", ("生存狀態",)),
        "death_date": _find_column(frame.columns, "5.3", ("最後聯絡或死亡日期",)),
        "node_examined": _find_column(frame.columns, "2.14", ("區域淋巴結檢查數目",)),
        "occurrence": _find_column(frame.columns, "2.2", ("癌症發生順序",)),
        "histology": _find_column(frame.columns, "2.8", ("組織型態",)),
        "margin": _find_column(frame.columns, "4.1.5.1", ("原發部位手術切緣距離",)),
    }


def _number(frame, column):
    if not column:
        return pd.Series(float("nan"), index=frame.index)
    return pd.to_numeric(frame[column].map(_clean_code), errors="coerce")


def _code(frame, column):
    if not column:
        return pd.Series("", index=frame.index, dtype="object")
    return frame[column].map(_clean_code)


def _date(frame, column):
    if not column:
        return pd.Series(pd.NaT, index=frame.index)

    def parse(value):
        text = _clean_code(value)
        if not text or text == "00000000":
            return pd.NaT
        digits = re.sub(r"\D", "", text)
        if len(digits) >= 8:
            return pd.to_datetime(digits[:8], format="%Y%m%d", errors="coerce")
        return pd.to_datetime(text, errors="coerce")

    return frame[column].map(parse)


def _in_range(series, start, end):
    return series.between(start, end, inclusive="both")


def _after_within_days(anchor, event, days):
    delta = (event - anchor).dt.days
    return anchor.notna() & event.notna() & delta.between(0, days, inclusive="both")


def _base_result(denominator, numerator):
    denominator = denominator.fillna(False).astype(bool)
    numerator = (numerator.fillna(False).astype(bool) & denominator)
    return {"denominator_mask": denominator, "numerator_mask": numerator}


def calculate_oral_indicator_1(frame):
    """Post-operative adjuvant RT/CCRT started within six weeks."""
    col = _columns(frame)
    surgery_code = _number(frame, col["surgery_code"])
    surgery_date = _date(frame, col["surgery_date"])
    radiation_date = _date(frame, col["radiation_date"])
    chemotherapy_date = _date(frame, col["chemotherapy_date"])

    eligible_surgery = _in_range(surgery_code, 30, 90) & surgery_date.notna()
    radiation_after_surgery = radiation_date.notna() & (radiation_date > surgery_date)
    # The definition's option B requires post-operative chemotherapy and a
    # recorded radiation start date, representing concurrent chemoradiation.
    ccrt_after_surgery = (
        chemotherapy_date.notna()
        & (chemotherapy_date > surgery_date)
        & radiation_date.notna()
    )
    denominator = eligible_surgery & (radiation_after_surgery | ccrt_after_surgery)
    earliest_treatment = pd.concat([radiation_date, chemotherapy_date], axis=1).min(axis=1)
    numerator = _after_within_days(surgery_date, earliest_treatment, 42)
    return _base_result(denominator, numerator)


def calculate_oral_indicator_2(frame):
    """Death within 30 days after oral-cancer surgery."""
    col = _columns(frame)
    denominator = (
        _in_range(_number(frame, col["surgery_code"]), 30, 90)
        & _code(frame, col["palliative"]).eq("0")
        & _date(frame, col["surgery_date"]).notna()
    )
    numerator = (
        _code(frame, col["survival"]).eq("0")
        & _after_within_days(_date(frame, col["surgery_date"]), _date(frame, col["death_date"]), 30)
    )
    return _base_result(denominator, numerator)


def calculate_oral_indicator_3(frame):
    """Death within 90 days after radiotherapy without chemotherapy."""
    col = _columns(frame)
    radiation_date = _date(frame, col["radiation_date"])
    denominator = (
        radiation_date.notna()
        & (_number(frame, col["radiation_dose"]) > 0)
        & _code(frame, col["chemotherapy"]).eq("0")
        & _code(frame, col["palliative"]).eq("0")
    )
    numerator = (
        _code(frame, col["survival"]).eq("0")
        & _after_within_days(radiation_date, _date(frame, col["death_date"]), 90)
    )
    return _base_result(denominator, numerator)


def calculate_oral_indicator_4(frame):
    """Death within 90 days after concurrent chemoradiation."""
    col = _columns(frame)
    radiation_date = _date(frame, col["radiation_date"])
    chemotherapy_date = _date(frame, col["chemotherapy_date"])
    chemotherapy_code = _number(frame, col["chemotherapy"])
    excluded_chemotherapy_codes = {82, 83, 85, 86, 87, 88, 99}
    denominator = (
        radiation_date.notna()
        & (_number(frame, col["radiation_dose"]) > 0)
        & (chemotherapy_code > 0)
        & ~chemotherapy_code.isin(excluded_chemotherapy_codes)
        & chemotherapy_date.notna()
        & _code(frame, col["palliative"]).eq("0")
    )
    treatment_start = pd.concat([radiation_date, chemotherapy_date], axis=1).min(axis=1)
    numerator = (
        _code(frame, col["survival"]).eq("0")
        & _after_within_days(treatment_start, _date(frame, col["death_date"]), 90)
    )
    return _base_result(denominator, numerator)


def calculate_oral_indicator_5(frame):
    """At least 15 regional lymph nodes examined for the first oral cancer."""
    col = _columns(frame)
    denominator = (
        _number(frame, col["occurrence"]).eq(1)
        & _in_range(_number(frame, col["surgery_code"]), 30, 80)
    )
    numerator = _in_range(_number(frame, col["node_examined"]), 15, 90)
    return _base_result(denominator, numerator)


def calculate_oral_indicator_6(frame):
    """Close (<4 mm) or positive pathological margin after radical surgery."""
    col = _columns(frame)
    margin_code = _code(frame, col["margin"])
    margin_number = _number(frame, col["margin"])
    denominator = (
        _in_range(_number(frame, col["histology"]), 8050, 8086)
        & _in_range(_number(frame, col["surgery_code"]), 30, 90)
        & margin_code.ne("")
        & ~margin_code.isin({"991", "999"})
    )
    numerator = (margin_number < 40) | margin_code.eq("987")
    return _base_result(denominator, numerator)