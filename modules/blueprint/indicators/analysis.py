"""
指標分析核心邏輯 (Indicators Analysis Engine)

負責依據使用者指定之診斷年度區間與癌別清單：
1. 篩選指定年度與癌別個案。
2. 套用全域共用排除規則（class 1/2、跨院治療、AJCC 期別不明/不適用、院內重複個案）。
3. 執行各指標之分子與分母運算。
4. 進行分子不大於分母之防呆校驗並回傳彙整報表。
"""

from __future__ import annotations
import logging
import pandas as pd
from modules.blueprint.dashboard.definition.cancer_grouping import classify_cancer_group
from modules.blueprint.dashboard.definition.cancer_group_rules import CANCER_GROUP_RULES
from modules.blueprint.indicators.indicator_definitions import (get_indicator_definitions, get_indicator_metadata)
from modules.blueprint.indicators.exclusion_rules import _clean_code, _date_key, _find_column, apply_global_indicators_exclusions

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 特定癌別收案準則（原發部位與組織型態條件）
# ---------------------------------------------------------------------------
INDICATOR_CANCER_CRITERIA = {
    "Ovary": {
        "sites": {"C569"},
        "histology_exclude": {"9140"},
        "histology_exclude_ranges": ((9590, 9993),),
    },
    "Prostate": {
        "sites": {"C619"},
        "histology_include": {"8140", "8141", "8201", "8255", "8500", "8550", "8551", "8552"},
    },
    "Bladder": {
        "sites": {"C679"},
        "histology_include": {"8020", "8031", "8082", "8120", "8122", "8130", "8131"},
    },
    "Corpus_Uteri": {
        "sites": {"C540", "C541", "C543", "C548", "C549"},
        "histology_exclude": {"9140"},
        "histology_exclude_ranges": ((9590, 9993),),
        "histology_types": {
            "type_i": {"8380", "8382", "8383", "8480", "8560", "8570", "8140"},
            "type_ii": {"8441", "8310", "8041", "8045", "8246", "8013", "8020", "8323", "8070", "8071", "8072", "8076"},
        },
    },
}


# ---------------------------------------------------------------------------
# 代碼清洗與部位/組織型態標準化輔助函式
# ---------------------------------------------------------------------------
def _normalize_site(value):
    return _clean_code(value).upper().replace(".", "")


def _normalize_histology(value):
    code = _clean_code(value)
    return code.zfill(4) if code.isdigit() and len(code) < 4 else code


# ---------------------------------------------------------------------------
# 個案篩選遮罩（癌別與診斷年度）
# ---------------------------------------------------------------------------
def _indicator_cancer_mask(frame, cancer_key):
    criteria = INDICATOR_CANCER_CRITERIA[cancer_key]
    case_class_col = _find_column(frame.columns, "2.3", ("class", "個案分類"))
    site_col = _find_column(frame.columns, "2.6", ("原發部位", "site"))
    hist_col = _find_column(frame.columns, "2.8", ("組織型態", "hist"))
    if not case_class_col or not site_col or not hist_col:
        return pd.Series(False, index=frame.index)

    histology = frame[hist_col].map(_normalize_histology)
    mask = (
        frame[case_class_col].map(_clean_code).isin({"1", "2"})
        & frame[site_col].map(_normalize_site).isin(criteria["sites"])
    )
    if "histology_include" in criteria:
        return mask & histology.isin(criteria["histology_include"])

    mask &= ~histology.isin(criteria["histology_exclude"])
    histology_number = pd.to_numeric(histology, errors="coerce")
    for start, end in criteria["histology_exclude_ranges"]:
        mask &= ~histology_number.between(start, end, inclusive="both")
    return mask.fillna(False)


def _cancer_mask(frame, cancer_key):
    if cancer_key in INDICATOR_CANCER_CRITERIA:
        return _indicator_cancer_mask(frame, cancer_key)

    site_col = _find_column(frame.columns, "2.6", ("原發部位", "site"))
    hist_col = _find_column(frame.columns, "2.8", ("組織型態", "hist"))
    behavior_col = _find_column(frame.columns, "2.9", ("性態碼", "behavior"))
    if not site_col or not hist_col:
        return pd.Series(False, index=frame.index)

    def matches(row):
        cancer = classify_cancer_group(
            row.get(site_col, ""), row.get(hist_col, ""), CANCER_GROUP_RULES,
            behavior=row.get(behavior_col, "") if behavior_col else None,
        )
        if not cancer:
            return False
        keys = {cancer.get("group_key"), cancer.get("subgroup_key"), *cancer.get("ancestor_subgroup_keys", [])}
        return cancer_key in keys

    return frame.apply(matches, axis=1)


def _year_mask(frame, year_start, year_end):
    diagnosis_col = _find_column(frame.columns, "2.5", ("最初診斷日期", "didiag", "診斷日期"))
    if not diagnosis_col:
        return pd.Series(False, index=frame.index), "找不到最初診斷日期(2.5)，無法依診斷年度篩選。"
    years = frame[diagnosis_col].map(_date_key).map(lambda value: value.year if value != pd.Timestamp.max else None)
    return years.between(int(year_start), int(year_end), inclusive="both").fillna(False), ""


# ---------------------------------------------------------------------------
# 唯一個案計數計算
# ---------------------------------------------------------------------------
def _unique_case_count(frame, mask):
    selected = frame.loc[pd.Series(mask, index=frame.index).fillna(False).astype(bool)]
    if selected.empty:
        return 0

    explicit_id = _find_column(
        selected.columns,
        aliases=("案件識別值", "個案識別值", "case_id", "record_id", "資料編號"),
    )
    if explicit_id:
        values = selected[explicit_id].map(_clean_code)
        return int(values[values.ne("")].nunique() + values.eq("").sum())

    key_specs = (
        ("1.1", ("申報醫院代碼", "醫院代碼")),
        ("1.4", ("身分證統一編號", "身分證")),
        ("2.6", ("原發部位", "site")),
        ("2.5", ("最初診斷日期", "didiag")),
        ("2.2", ("癌症發生順序號碼",)),
    )
    key_columns = [_find_column(selected.columns, code, aliases) for code, aliases in key_specs]
    if not all(key_columns):
        return int(len(selected))

    keys = selected[key_columns].map(_clean_code)
    complete = keys.ne("").all(axis=1)
    return int(keys.loc[complete].drop_duplicates().shape[0] + (~complete).sum())


# ---------------------------------------------------------------------------
# 指標分析主流程
# ---------------------------------------------------------------------------
def run_indicators_analysis(frame, cancers, year_start, year_end):
    year_mask, error = _year_mask(frame, year_start, year_end)
    if error:
        return {"ok": False, "error": error}

    selected = [str(key) for key in (cancers or []) if str(key).strip()]
    reports = []
    for cancer_key in selected:
        metadata = get_indicator_metadata(cancer_key)
        definitions = get_indicator_definitions(cancer_key, metadata)
        cancer_cases = frame.loc[year_mask & _cancer_mask(frame, cancer_key)].copy()
        if not definitions:
            reports.append({
                "cancer_key": cancer_key,
                "input_count": int(len(cancer_cases)),
                "indicator_definition_metadata": metadata,
                "indicators": [],
                "message": "此癌別尚未設定監測指標定義。",
            })
            continue

        # Cancer-specific definitions identify whether shared exclusions apply.
        included_cases, audit_cases, global_summary = apply_global_indicators_exclusions(
            cancer_cases, is_hospital_self_reported=True
        )
        indicators = []
        for definition in definitions:
            masks = definition["calculator"](included_cases)
            denominator = _unique_case_count(included_cases, masks["denominator_mask"])
            numerator = _unique_case_count(included_cases, masks["numerator_mask"])
            calculation_error = ""
            if numerator > denominator:
                calculation_error = "分子件數大於分母件數，已停止顯示監測結果。"
                logger.error(
                    "Indicator numerator exceeds denominator: cancer=%s indicator=%s numerator=%s denominator=%s",
                    cancer_key,
                    definition["id"],
                    numerator,
                    denominator,
                )
            indicators.append({
                "id": definition["id"],
                "direction": definition["direction"],
                "name": definition["name"],
                "numerator_definition": definition["numerator_definition"],
                "denominator_definition": definition["denominator_definition"],
                "numerator": numerator,
                "denominator": denominator,
                "percentage": (
                    round(numerator / denominator * 100, 1)
                    if denominator and not calculation_error
                    else None
                ),
                "calculation_error": calculation_error,
            })
        reports.append({
            "cancer_key": cancer_key,
            "input_count": int(len(cancer_cases)),
            "included_count": int(len(included_cases)),
            "global_exclusions": global_summary,
            "indicator_definition_metadata": metadata,
            "indicators": indicators,
            "message": "",
        })

    return {"ok": True, "reports": reports}
