"""Shared case-exclusion rules for the indicators-indicator module.

These filters run before any cancer-specific numerator or denominator rule.
"""
from __future__ import annotations

import re
from collections import Counter

import pandas as pd

from modules.blueprint.dashboard.definition.cancer_grouping import classify_cancer_group
from modules.blueprint.dashboard.definition.cancer_group_rules import CANCER_GROUP_RULES


ELIGIBLE_CASE_CLASSES = {"1", "2"}
CROSS_HOSPITAL_VALUES = {"class": "2", "diagnosis": "2", "treatment": "3"}
INDICATOR_DEFINITION_VERSION = "115"


def _clean_code(value) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "nat"}:
        return ""
    return text[:-2] if text.endswith(".0") else text


def _find_column(columns, code=None, aliases=()):
    """Find a standardized registry column by its sequence code or name."""
    normalized = [(str(column), str(column).strip().lower()) for column in columns]
    if code:
        pattern = re.compile(rf"^{re.escape(code)}(?:$|[^0-9.])")
        for original, _ in normalized:
            if pattern.match(original.strip()):
                return original
    for alias in aliases:
        alias_text = alias.lower()
        for original, lower in normalized:
            if alias_text in lower:
                return original
    return None


def _date_key(value):
    """Return a sortable diagnosis date; missing dates are sorted last."""
    text = _clean_code(value)
    if text in {"", "00000000"}:
        return pd.Timestamp.max
    digits = re.sub(r"\D", "", text)
    if len(digits) >= 8:
        parsed = pd.to_datetime(digits[:8], format="%Y%m%d", errors="coerce")
    else:
        parsed = pd.to_datetime(text, errors="coerce")
    return parsed if not pd.isna(parsed) else pd.Timestamp.max


def _is_known_surgery_date(value) -> bool:
    return _date_key(value) != pd.Timestamp.max


def _stage_severity(value) -> int:
    """Map clinical/pathological stage to a comparable 0–4 severity rank."""
    text = _clean_code(value).upper().replace("STAGE", "").strip()
    if not text or text in {"BBB", "888", "999", "8888", "9999"}:
        return -1
    if re.search(r"(?:^|\D)(IV|4)", text):
        return 4
    if re.search(r"(?:^|\D)(III|3)", text):
        return 3
    if re.search(r"(?:^|\D)(II|2)", text):
        return 2
    if re.search(r"(?:^|\D)(I|1)", text):
        return 1
    if re.search(r"(?:^|\D)(0)", text):
        return 0
    return -1


def _occurrence_key(value) -> int:
    text = _clean_code(value)
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return 999999


def _cancer_key(row, site_col, hist_col, behavior_col):
    cancer = classify_cancer_group(
        row.get(site_col, "") if site_col else "",
        row.get(hist_col, "") if hist_col else "",
        CANCER_GROUP_RULES,
        behavior=row.get(behavior_col, "") if behavior_col else None,
    )
    if cancer:
        return cancer.get("group_key") or cancer.get("subgroup_key") or ""
    return _clean_code(row.get(site_col, "") if site_col else "")


def _duplicate_sort_key(row, columns):
    pathology_prefix = _clean_code(row.get(columns["path_prefix"], "") if columns["path_prefix"] else "")
    pathology_stage = _clean_code(row.get(columns["path_stage"], "") if columns["path_stage"] else "")
    clinical_stage = row.get(columns["clinical_stage"], "") if columns["clinical_stage"] else ""
    surgery_date = row.get(columns["surgery_date"], "") if columns["surgery_date"] else ""

    # 115-year definition: use clinical stage for pathological prefix 4/6 or BBB;
    # otherwise use pathological stage when a definite primary-site surgery date exists.
    if pathology_prefix in {"4", "6"} or pathology_stage == "BBB":
        selected_stage = clinical_stage
    elif _is_known_surgery_date(surgery_date):
        selected_stage = pathology_stage
    else:
        selected_stage = clinical_stage

    return (
        _date_key(row.get(columns["diagnosis_date"], "") if columns["diagnosis_date"] else ""),
        -_stage_severity(selected_stage),
        _occurrence_key(row.get(columns["occurrence"], "") if columns["occurrence"] else ""),
        int(row.name),
    )


def apply_global_indicators_exclusions(dataframe: pd.DataFrame, *, is_hospital_self_reported: bool = True):
    """Apply 115-year shared exclusions and preserve a row-level audit trail.

    These exclusions apply only to hospital self-reported indicator sources.

    Returns `(included_cases, audit_cases, summary)`.  `audit_cases` keeps
    all original rows and adds ``監測模組納入統計`` and ``監測模組排除原因``.
    """
    audit = dataframe.copy()
    audit["監測模組納入統計"] = True
    audit["監測模組排除原因"] = ""

    if not is_hospital_self_reported:
        return audit.copy(), audit, {
            "input_count": int(len(audit)),
            "included_count": int(len(audit)),
            "excluded_count": 0,
            "excluded_by_reason": {},
            "warnings": ["此指標非醫院自行申報資料來源，未套用共用排除規則。"],
        }

    columns = {
        "case_class": _find_column(audit.columns, "2.3", ("class", "個案分類")),
        "diagnosis_status": _find_column(audit.columns, "2.3.1", ("診斷狀態分類",)),
        "treatment_status": _find_column(audit.columns, "2.3.2", ("治療狀態分類",)),
        "hospital": _find_column(audit.columns, None, ("醫院代碼", "hospital code")),
        "identity": _find_column(audit.columns, "1.4", ("身分證", "身分證字號", "identity")),
        "medical_record": _find_column(audit.columns, "1.2", ("病歷號", "medical record")),
        "diagnosis_date": _find_column(audit.columns, "2.5", ("最初診斷日期", "didiag")),
        "occurrence": _find_column(audit.columns, "2.2", ("癌症發生順序",)),
        "site": _find_column(audit.columns, "2.6", ("原發部位", "site")),
        "hist": _find_column(audit.columns, "2.8", ("組織型態", "hist")),
        "behavior": _find_column(audit.columns, "2.9", ("性態碼", "behavior")),
        "clinical_stage": _find_column(audit.columns, "3.7", ("臨床期別組合",)),
        "path_stage": _find_column(audit.columns, "3.13", ("病理期別組合",)),
        "path_prefix": _find_column(audit.columns, "3.14", ("病理分期字根",)),
        "surgery_date": _find_column(audit.columns, "4.1.2", ("最確切的手術切除日期",)),
    }
    warnings = []
    class_col = columns["case_class"]
    if not class_col:
        warnings.append("找不到個案分類(2.3)欄位，無法套用 class=1、2 的前置納入規則。")
    else:
        eligible = audit[class_col].map(_clean_code).isin(ELIGIBLE_CASE_CLASSES)
        audit.loc[~eligible, "監測模組納入統計"] = False
        audit.loc[~eligible, "監測模組排除原因"] = "個案分類非 class 1、2"

    # Cross-hospital treatment exclusions are applied after class filtering.
    diagnosis_col = columns["diagnosis_status"]
    treatment_col = columns["treatment_status"]
    if class_col and diagnosis_col and treatment_col:
        cross_hospital = (
            audit["監測模組納入統計"]
            & audit[class_col].map(_clean_code).eq(CROSS_HOSPITAL_VALUES["class"])
            & audit[diagnosis_col].map(_clean_code).eq(CROSS_HOSPITAL_VALUES["diagnosis"])
            & audit[treatment_col].map(_clean_code).eq(CROSS_HOSPITAL_VALUES["treatment"])
        )
        audit.loc[cross_hospital, "監測模組納入統計"] = False
        audit.loc[cross_hospital, "監測模組排除原因"] = "跨院治療個案"
    else:
        warnings.append("缺少跨院治療判定欄位，未套用跨院治療排除。")

    included = audit.loc[audit["監測模組納入統計"]].copy()
    excluded_counts = Counter(audit.loc[~audit["監測模組納入統計"], "監測模組排除原因"])
    summary = {
        "input_count": int(len(audit)),
        "included_count": int(len(included)),
        "excluded_count": int(len(audit) - len(included)),
        "excluded_by_reason": dict(excluded_counts),
        "warnings": warnings,
    }
    return included, audit, summary