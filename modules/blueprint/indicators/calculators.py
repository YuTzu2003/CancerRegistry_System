"""Shared calculation helpers for cancer-indicator rules.

Cancer-specific numerator and denominator calculators are added only after
that cancer's definition has been confirmed.
"""
from __future__ import annotations

import re

import pandas as pd

from modules.blueprint.indicators.rules import _clean_code


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
            return pd.to_datetime(digits[:8], format="%Y%m%d", errors="coerce")
        return pd.to_datetime(text, errors="coerce")

    return frame[column].map(parse)


def code_in_range(series, start, end):
    """Return rows whose numeric registry code is inclusively within a range."""
    return series.between(start, end, inclusive="both")


def event_within_days(start_date, event_date, days):
    """Return rows where an event occurs from day 0 through the given limit."""
    delta = (event_date - start_date).dt.days
    return start_date.notna() & event_date.notna() & delta.between(0, days, inclusive="both")


def result_masks(denominator, numerator):
    """Ensure numerator rows are always a subset of denominator rows."""
    denominator = denominator.fillna(False).astype(bool)
    numerator = numerator.fillna(False).astype(bool) & denominator
    return {"denominator_mask": denominator, "numerator_mask": numerator}