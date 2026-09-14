"""Run configured indicators indicators against an uploaded registry dataset."""
from __future__ import annotations

import pandas as pd

from modules.blueprint.indicators.indicator_definitions import get_indicator_definitions
from modules.blueprint.indicators.exclusion_rules import _date_key, _find_column, apply_global_indicators_exclusions
from modules.blueprint.indicators.record_mapping import indicator_records
from modules.blueprint.indicators.rule import calculate_indicator_summary, is_cancer_candidate


def _year_mask(frame, year_start, year_end):
    diagnosis_col = _find_column(frame.columns, "2.5", ("最初診斷日期", "didiag", "診斷日期"))
    if not diagnosis_col:
        return pd.Series(False, index=frame.index), "找不到最初診斷日期(2.5)，無法依診斷年度篩選。"
    years = frame[diagnosis_col].map(_date_key).map(lambda value: value.year if value != pd.Timestamp.max else None)
    return years.between(int(year_start), int(year_end), inclusive="both").fillna(False), ""


def run_indicators_analysis(frame, cancers, year_start, year_end):
    """Return report-ready counts for every configured selected indicator."""
    year_mask, error = _year_mask(frame, year_start, year_end)
    if error:
        return {"ok": False, "error": error}

    selected = [str(key) for key in (cancers or []) if str(key).strip()]
    reports = []
    year_cases = frame.loc[year_mask].copy()
    year_records = indicator_records(year_cases)
    for cancer_key in selected:
        definitions = get_indicator_definitions(cancer_key)
        if not definitions:
            reports.append({"cancer_key": cancer_key, "input_count": 0, "indicators": [], "message": "此癌別尚未設定監測指標定義。"})
            continue

        # 個案分類 0、3 必須進入共用排除稽核，才能在摘要中呈現排除件數。
        cancer_mask = [is_cancer_candidate(record, cancer_key) for record in year_records]
        cancer_cases = year_cases.loc[cancer_mask].copy()

        included_cases, _audit_cases, global_summary = apply_global_indicators_exclusions(
            cancer_cases, is_hospital_self_reported=True
        )
        summary = calculate_indicator_summary(indicator_records(included_cases), cancer_key)
        definitions_by_id = {int(definition["id"]): definition for definition in definitions}
        indicators = []
        for indicator_number, counts in summary.items():
            definition = definitions_by_id[indicator_number]
            indicators.append({
                "id": definition["id"],
                "direction": definition["direction"],
                "name": definition["name"],
                "selection_reason": definition.get("selection_reason", ""),
                "numerator_definition": definition["numerator_definition"],
                "denominator_definition": definition["denominator_definition"],
                "numerator": counts["numerator_count"],
                "denominator": counts["denominator_count"],
                "percentage": counts["rate"],
            })
        reports.append({
            "cancer_key": cancer_key,
            "input_count": int(len(cancer_cases)),
            "included_count": int(len(included_cases)),
            "global_exclusions": global_summary,
            "indicators": indicators,
            "message": "",
        })

    return {"ok": True, "reports": reports}
