"""Shared helpers for excluding registry case class H from module outputs."""

from __future__ import annotations

import re


def normalize_case_class(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "nat"}:
        return ""
    if text.endswith(".0"):
        text = text[:-2]
    return text.upper()


def is_case_class_h(value) -> bool:
    return normalize_case_class(value) == "H"


def find_case_class_column(columns, preferred=None):
    """Find registry field 2.3 or its standard English/Chinese header."""
    if preferred is not None and preferred in columns:
        return preferred
    for column in columns:
        name = str(column).strip()
        if re.match(r"^2\.3(?:$|[^0-9.])", name):
            return column
    for column in columns:
        if str(column).strip().lower() == "class":
            return column
    for column in columns:
        if "個案分類" in str(column).strip():
            return column
    return None


def exclude_case_class_h(dataframe, class_column=None):
    """Return a copy without H cases when field 2.3 is present."""
    column = find_case_class_column(dataframe.columns, class_column)
    if column is None:
        return dataframe.copy()
    keep = ~dataframe[column].map(is_case_class_h)
    return dataframe.loc[keep].copy()
