"""Shared case-exclusion rules for the cancer-indicator module.

The rules are applied only to indicators whose data source is hospital
self-reporting.  They use the same cancer classification and AJCC selection
order as the annual-report module.
"""
from __future__ import annotations

import re
from collections import Counter

import pandas as pd

from modules.blueprint.dashboard.definition.cancer_grouping import classify_cancer_group
from modules.blueprint.dashboard.definition.cancer_group_rules import CANCER_GROUP_RULES


ELIGIBLE_CASE_CLASSES = {"1", "2"}
CROSS_HOSPITAL_VALUES = {"class": "2", "diagnosis": "2", "treatment": "3"}
INVALID_IDENTITY_VALUES = {"", "9999999999"}
INDICATOR_DEFINITION_VERSION = "115"


def _clean_code(value) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "nat"}:
        return ""
    return text[:-2] if text.endswith(".0") else text


def _find_column(columns, code=None, aliases=()):
    """Find a registry column supplied as code, name, or code-plus-name."""
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
    """Return a sortable diagnosis date; invalid values sort after valid ones."""
    text = _clean_code(value)
    if text in {"", "00000000", "88888888", "99999999"}:
        return pd.Timestamp.max
    digits = re.sub(r"\D", "", text)
    if len(digits) >= 8:
        parsed = pd.to_datetime(digits[:8], format="%Y%m%d", errors="coerce")
    else:
        parsed = pd.to_datetime(text, errors="coerce")
    return parsed if not pd.isna(parsed) else pd.Timestamp.max


def _stage_severity(value) -> int:
    """Map the annual-report AJCC stage value to an order from 0 through IV."""
    text = _clean_code(value).upper().replace("STAGE", "").strip()
    if not text or text in {"BBB", "888", "8888", "999", "9999"}:
        return -1
    if re.search(r"(?:^|\D)(IV|4)", text):
        return 4
    if re.search(r"(?:^|\D)(III|3)", text):
        return 3
    if re.search(r"(?:^|\D)(II|2)", text):
        return 2
    if re.search(r"(?:^|\D)(I|1)", text):
        return 1
    if re.search(r"(?:^|\D)0", text):
        return 0
    return -1


def _append_reason(audit, mask, reason):
    """Mark rows excluded while retaining every applicable exclusion reason."""
    mask = pd.Series(mask, index=audit.index).fillna(False).astype(bool)
    if not mask.any():
        return
    existing = audit.loc[mask, "指標模組排除原因"].fillna("").astype(str)
    audit.loc[mask, "指標模組排除原因"] = existing.map(
        lambda value: reason if not value else f"{value}；{reason}" if reason not in value.split("；") else value
    )
    audit.loc[mask, "指標模組納入統計"] = False


def _annual_ajcc_stage(row, columns):
    """Apply annual-report AJCC rules 1–3 and return the selected raw stage."""
    pathology_prefix = _clean_code(row.get(columns["path_prefix"], "") if columns["path_prefix"] else "")
    pathology_stage = _clean_code(row.get(columns["path_stage"], "")).upper() if columns["path_stage"] else ""
    clinical_stage = _clean_code(row.get(columns["clinical_stage"], "")) if columns["clinical_stage"] else ""
    surgery_date = _clean_code(row.get(columns["surgery_date"], "")) if columns["surgery_date"] else ""

    # Same selection order as dashboard.period_rule.ajcc_stages.
    if pathology_prefix in {"4", "6"} or surgery_date == "00000000" or pathology_stage == "BBB":
        return clinical_stage
    return pathology_stage


def _annual_ajcc_exclusion_reason(selected_stage):
    """Annual-report AJCC rules 4–5: unknown or not-applicable stages."""
    stage = _clean_code(selected_stage).replace(",", "")
    if stage in {"888", "8888"}:
        return "AJCC期別不適用"
    if not stage or stage in {"999", "9999"}:
        return "AJCC期別不明"
    return ""


def _cancer_key(row, site_col, hist_col, behavior_col, diagnosis_col, ajcc_ed_col):
    """Return the most specific annual-report cancer key for duplicate grouping."""
    cancer = classify_cancer_group(
        row.get(site_col, "") if site_col else "",
        row.get(hist_col, "") if hist_col else "",
        CANCER_GROUP_RULES,
        behavior=row.get(behavior_col, "") if behavior_col else None,
        didiag=row.get(diagnosis_col, "") if diagnosis_col else None,
        ajcc_ed=row.get(ajcc_ed_col, "") if ajcc_ed_col else None,
    )
    if not cancer:
        return ""
    return cancer.get("subgroup_key") or cancer.get("group_key") or ""


def _column_map(frame):
    return {
        "case_class": _find_column(frame.columns, "2.3", ("class", "個案分類")),
        "diagnosis_status": _find_column(frame.columns, "2.3.1", ("診斷狀態分類",)),
        "treatment_status": _find_column(frame.columns, "2.3.2", ("治療狀態分類",)),
        "hospital": _find_column(frame.columns, "1.1", ("申報醫院代碼", "醫院代碼", "hospital code")),
        "identity": _find_column(frame.columns, "1.4", ("身分證統一編號", "身分證", "identity")),
        "diagnosis_date": _find_column(frame.columns, "2.5", ("最初診斷日期", "didiag")),
        "occurrence": _find_column(frame.columns, "2.2", ("癌症發生順序",)),
        "site": _find_column(frame.columns, "2.6", ("原發部位", "site")),
        "hist": _find_column(frame.columns, "2.8", ("組織型態", "hist")),
        "behavior": _find_column(frame.columns, "2.9", ("性態碼", "behavior")),
        "clinical_stage": _find_column(frame.columns, "3.7", ("臨床期別組合",)),
        "path_stage": _find_column(frame.columns, "3.13", ("病理期別組合",)),
        "path_prefix": _find_column(frame.columns, "3.14", ("病理分期字根", "病理分期字首")),
        "ajcc_ed": _find_column(frame.columns, "3.16", ("AJCC 癌症分期版本與章節", "ajcc_ed")),
        "surgery_date": _find_column(frame.columns, "4.1.2", ("最確切的手術切除日期",)),
    }


def _apply_duplicate_exclusion(audit, columns, warnings):
    """Keep one eligible case for each hospital + cancer + identity group.

    Retention order follows the confirmed definition: earliest diagnosis date,
    then more severe annual-report AJCC stage.  Cancer occurrence number is
    used only when diagnosis, clinical stage, and pathological stage are all
    identical.  Unresolved ties remain included and are reported as warnings.
    """
    required = ("hospital", "identity", "diagnosis_date", "site", "hist")
    missing = [name for name in required if not columns[name]]
    if missing:
        warnings.append("缺少院內重複個案判定欄位，未套用院內重複個案排除：" + "、".join(missing))
        return

    eligible_indices = audit.index[audit["指標模組納入統計"]].tolist()
    groups = {}
    for index in eligible_indices:
        row = audit.loc[index]
        hospital = _clean_code(row.get(columns["hospital"], ""))
        identity = _clean_code(row.get(columns["identity"], ""))
        cancer = _cancer_key(
            row, columns["site"], columns["hist"], columns["behavior"],
            columns["diagnosis_date"], columns["ajcc_ed"],
        )
        if not hospital or not cancer or identity in INVALID_IDENTITY_VALUES:
            continue
        groups.setdefault((hospital, cancer, identity), []).append(index)

    for _, indexes in groups.items():
        if len(indexes) < 2:
            continue
        group = audit.loc[indexes].copy()
        group["_diagnosis_sort"] = group[columns["diagnosis_date"]].map(_date_key)
        earliest_date = group["_diagnosis_sort"].min()
        candidates = group.loc[group["_diagnosis_sort"].eq(earliest_date)].copy()

        if len(candidates) > 1:
            candidates["_ajcc_stage"] = candidates.apply(
                lambda row: _annual_ajcc_stage(row, columns), axis=1
            )
            candidates["_stage_severity"] = candidates["_ajcc_stage"].map(_stage_severity)
            highest_severity = candidates["_stage_severity"].max()
            candidates = candidates.loc[candidates["_stage_severity"].eq(highest_severity)].copy()

        if len(candidates) > 1:
            clinical_values = candidates[columns["clinical_stage"]].map(_clean_code) if columns["clinical_stage"] else pd.Series("", index=candidates.index)
            pathology_values = candidates[columns["path_stage"]].map(_clean_code) if columns["path_stage"] else pd.Series("", index=candidates.index)
            same_raw_stages = clinical_values.nunique(dropna=False) == 1 and pathology_values.nunique(dropna=False) == 1
            if same_raw_stages and columns["occurrence"]:
                occurrence_values = pd.to_numeric(candidates[columns["occurrence"]].map(_clean_code), errors="coerce")
                lowest_occurrence = occurrence_values.min()
                candidates = candidates.loc[occurrence_values.eq(lowest_occurrence)].copy()
            else:
                warnings.append("發現無法依既定規則裁決的院內重複個案，已暫時全部保留。")
                continue

        if len(candidates) == 1:
            retained_index = candidates.index[0]
            duplicate_indexes = [index for index in indexes if index != retained_index]
            _append_reason(audit, audit.index.isin(duplicate_indexes), "院內重複個案排除")
        else:
            warnings.append("發現癌症發生順序號碼相同的院內重複個案，已暫時全部保留。")


def apply_global_indicators_exclusions(dataframe: pd.DataFrame, *, is_hospital_self_reported: bool = True):
    """Apply the version-115 shared exclusions and return an auditable result.

    Hard exclusions are applied first: class not 1/2, cross-hospital treatment,
    and annual-report AJCC stage unknown/not-applicable.  Duplicate selection
    runs only across the remaining eligible rows.
    """
    audit = dataframe.copy()
    audit["指標模組納入統計"] = True
    audit["指標模組排除原因"] = ""

    if not is_hospital_self_reported:
        return audit.copy(), audit, {
            "input_count": int(len(audit)),
            "included_count": int(len(audit)),
            "excluded_count": 0,
            "excluded_by_reason": {},
            "warnings": ["此指標非醫院自行申報資料來源，未套用共用排除規則。"],
        }

    columns = _column_map(audit)
    warnings = []

    class_col = columns["case_class"]
    if class_col:
        eligible_class = audit[class_col].map(_clean_code).isin(ELIGIBLE_CASE_CLASSES)
        _append_reason(audit, ~eligible_class, "個案分類非 class 1、2")
    else:
        warnings.append("找不到個案分類(2.3)欄位，未套用 class=1、2 排除規則。")

    diagnosis_col = columns["diagnosis_status"]
    treatment_col = columns["treatment_status"]
    if class_col and diagnosis_col and treatment_col:
        cross_hospital = (
            audit[class_col].map(_clean_code).eq(CROSS_HOSPITAL_VALUES["class"])
            & audit[diagnosis_col].map(_clean_code).eq(CROSS_HOSPITAL_VALUES["diagnosis"])
            & audit[treatment_col].map(_clean_code).eq(CROSS_HOSPITAL_VALUES["treatment"])
        )
        _append_reason(audit, cross_hospital, "跨院治療個案")
    else:
        warnings.append("缺少跨院治療判定欄位，未套用跨院治療排除規則。")

    stage_required = ("clinical_stage", "path_stage", "path_prefix", "surgery_date")
    missing_stage = [name for name in stage_required if not columns[name]]
    if missing_stage:
        warnings.append("缺少 AJCC 期別判定欄位，未套用 AJCC期別不明／不適用排除：" + "、".join(missing_stage))
    else:
        selected_stages = audit.apply(lambda row: _annual_ajcc_stage(row, columns), axis=1)
        stage_reasons = selected_stages.map(_annual_ajcc_exclusion_reason)
        _append_reason(audit, stage_reasons.eq("AJCC期別不明"), "AJCC期別不明")
        _append_reason(audit, stage_reasons.eq("AJCC期別不適用"), "AJCC期別不適用")

    _apply_duplicate_exclusion(audit, columns, warnings)

    included = audit.loc[audit["指標模組納入統計"]].copy()
    reason_counts = Counter()
    for value in audit.loc[~audit["指標模組納入統計"], "指標模組排除原因"]:
        for reason in str(value).split("；"):
            if reason:
                reason_counts[reason] += 1
    summary = {
        "input_count": int(len(audit)),
        "included_count": int(len(included)),
        "excluded_count": int(len(audit) - len(included)),
        "excluded_by_reason": dict(reason_counts),
        "warnings": warnings,
    }
    return included, audit, summary