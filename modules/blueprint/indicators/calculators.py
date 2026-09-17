"""
指標計算輔助函式庫 (Indicator Calculation Utilities)

提供指標規則計算所需之常見資料清理與比對函式：
- 數值與代碼轉換標準化
- 癌症登記日期解析與無效代碼過濾
- 代碼數值區間比對與事件間隔天數計算
- 分子與分母布林遮罩之防呆子集保證
"""

from __future__ import annotations
import re
import pandas as pd
from modules.blueprint.indicators.exclusion_rules import _clean_code


# ---------------------------------------------------------------------------
# 數值與代碼清洗標準化
# ---------------------------------------------------------------------------
def number_value(frame, column):
    """Return a numeric series, with missing or special values as NaN."""
    if not column:
        return pd.Series(float("nan"), index=frame.index)
    return pd.to_numeric(frame[column].map(_clean_code), errors="coerce")


def code_value(frame, column):
    """Return normalized registry codes as strings."""
    if not column:
        return pd.Series("", index=frame.index, dtype="object")
    return frame[column].map(_clean_code)


# ---------------------------------------------------------------------------
# 癌症登記日期解析與驗證
# ---------------------------------------------------------------------------
def date_value(frame, column):
    """Return valid registry dates; 00000000 and blank values become NaT."""
    if not column:
        return pd.Series(pd.NaT, index=frame.index)

    def parse(value):
        text = _clean_code(value)
        if not text or text in {"00000000", "88888888", "99999999"}:
            return pd.NaT
        digits = re.sub(r"\D", "", text)
        if len(digits) >= 8:
            if digits[6:8] == "99":
                digits = f"{digits[:6]}01{digits[8:]}"
            return pd.to_datetime(digits[:8], format="%Y%m%d", errors="coerce")
        return pd.to_datetime(text, errors="coerce")

    return frame[column].map(parse)


# ---------------------------------------------------------------------------
# 範圍比對與天數間隔判定
# ---------------------------------------------------------------------------
def code_in_range(series, start, end):
    """Return rows whose numeric registry code is inclusively within a range."""
    return series.between(start, end, inclusive="both")


def event_within_days(start_date, event_date, days):
    """Return rows where an event occurs from day 0 through the given limit."""
    delta = (event_date - start_date).dt.days
    return start_date.notna() & event_date.notna() & delta.between(0, days, inclusive="both")


# ---------------------------------------------------------------------------
# 分子分母遮罩防呆保證
# ---------------------------------------------------------------------------
def result_masks(denominator, numerator):
    """Ensure numerator rows are always a subset of denominator rows."""
    denominator = denominator.fillna(False).astype(bool)
    numerator = numerator.fillna(False).astype(bool) & denominator
    return {"denominator_mask": denominator, "numerator_mask": numerator}
