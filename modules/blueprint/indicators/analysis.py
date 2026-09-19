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
from modules.blueprint.indicators.catalog import cancer_case_mask
from modules.blueprint.indicators.indicator_definitions import (get_indicator_definitions, get_indicator_metadata)
from modules.blueprint.indicators.exclusion_rules import _clean_code, _date_key, _find_column, apply_global_indicators_exclusions

logger = logging.getLogger(__name__)

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
        cancer_cases = frame.loc[year_mask & cancer_case_mask(frame, cancer_key)]
        included_cases, audit_cases, global_summary = apply_global_indicators_exclusions(
            cancer_cases,
            is_hospital_self_reported=True,
        )
        if not definitions:
            reports.append({
                "cancer_key": cancer_key,
                "input_count": int(len(cancer_cases)),
                "included_count": int(len(included_cases)),
                "global_exclusions": global_summary,
                "indicator_definition_metadata": metadata,
                "indicators": [
                    {
                        "id": definition["id"],
                        "direction": "unknown",
                        "name": f"指標 {definition['id']}",
                        "numerator_definition": definition["numerator_definition"],
                        "denominator_definition": definition["denominator_definition"],
                        "numerator": None,
                        "denominator": None,
                        "percentage": None,
                        "calculation_available": False,
                    }
                    for definition in metadata
                ],
                "message": "此癌別尚未建立可執行的指標計算規則。",
            })
            continue

        prostate_indicator_1_2_cases = included_cases
        if cancer_key == "Prostate":
            # Only prostate indicators 1 and 2 ignore the case-class exclusion.
            prostate_indicator_1_2_cases, _, _ = apply_global_indicators_exclusions(
                cancer_cases,
                is_hospital_self_reported=True,
                exclude_case_class=False,
            )
        indicators = []
        for definition in definitions:
            denominator_cases = (
                prostate_indicator_1_2_cases
                if cancer_key == "Prostate" and definition["id"] in {1, 2}
                else included_cases
            )
            numerator_masks = definition["calculator"](included_cases)
            denominator_masks = (
                numerator_masks
                if denominator_cases is included_cases
                else definition["calculator"](denominator_cases)
            )
            denominator = _unique_case_count(denominator_cases, denominator_masks["denominator_mask"])
            numerator = _unique_case_count(included_cases, numerator_masks["numerator_mask"])
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
