"""Run configured indicators indicators against an uploaded registry dataset."""
from __future__ import annotations

import re
import pandas as pd

from modules.blueprint.dashboard.definition.cancer_grouping import classify_cancer_group
from modules.blueprint.dashboard.definition.cancer_group_rules import CANCER_GROUP_RULES
from modules.blueprint.indicators.indicator_definitions import get_indicator_definitions
from modules.blueprint.indicators.exclusion_rules import _clean_code, _find_column, apply_global_indicators_exclusions


GASTRIC_ADENOCARCINOMA_HISTOLOGY = {
    "8140", "8144", "8145", "8148", "8210", "8211", "8255",
    "8260", "8263", "8480", "8481", "8490", "8550", "8576",
}

LIVER_HEPATOCELLULAR_CARCINOMA_HISTOLOGY = {str(code) for code in range(8170, 8176)}


def _cancer_mask(frame, cancer_key):
    site_col = _find_column(frame.columns, "2.6", ("原發部位", "site"))
    hist_col = _find_column(frame.columns, "2.8", ("組織型態", "hist"))
    behavior_col = _find_column(frame.columns, "2.9", ("性態碼", "behavior"))
    if not site_col or not hist_col:
        return pd.Series(False, index=frame.index)

    def matches(row):
        # 年報將 C18-C21 放在同一個大分類；指標模組的結腸、直腸癌
        # 僅收 C18-C20，因此在此依指標定義另行限定。
        if cancer_key == "Colon_Rectum":
            site_code = re.sub(r"[^A-Z0-9]", "", _clean_code(row.get(site_col, "")).upper())
            histology_digits = re.sub(r"\D", "", _clean_code(row.get(hist_col, "")))
            if len(histology_digits) < 4:
                return False
            histology = int(histology_digits[:4])
            return (
                site_code[:3] in {"C18", "C19", "C20"}
                and histology != 9140
                and not 9590 <= histology <= 9993
            )

        cancer = classify_cancer_group(
            row.get(site_col, ""), row.get(hist_col, ""), CANCER_GROUP_RULES,
            behavior=row.get(behavior_col, "") if behavior_col else None,
        )
        if not cancer:
            return False
        keys = {cancer.get("group_key"), cancer.get("subgroup_key"), *cancer.get("ancestor_subgroup_keys", [])}
        if cancer_key not in keys:
            return False
        if cancer_key == "Stomach":
            histology_digits = re.sub(r"\D", "", _clean_code(row.get(hist_col, "")))
            return histology_digits[:4] in GASTRIC_ADENOCARCINOMA_HISTOLOGY
        if cancer_key == "Liver":
            site_code = re.sub(r"[^A-Z0-9]", "", _clean_code(row.get(site_col, "")).upper())
            histology_digits = re.sub(r"\D", "", _clean_code(row.get(hist_col, "")))
            return site_code == "C220" and histology_digits[:4] in LIVER_HEPATOCELLULAR_CARCINOMA_HISTOLOGY
        return True

    return frame.apply(matches, axis=1)


def _year_mask(frame, year_start, year_end):
    diagnosis_col = _find_column(frame.columns, "2.5", ("最初診斷日期", "didiag", "診斷日期"))
    if not diagnosis_col:
        return pd.Series(False, index=frame.index), "找不到最初診斷日期(2.5)，無法依診斷年度篩選。"

    def diagnosis_year(value):
        """Extract CCYY without requiring MM/DD to be fully known."""
        text = _clean_code(value)
        digits = re.sub(r"\D", "", text)
        if len(digits) < 4 or digits[:4] in {"0000", "8888", "9999"}:
            return None
        return int(digits[:4])

    years = frame[diagnosis_col].map(diagnosis_year)
    return years.between(int(year_start), int(year_end), inclusive="both").fillna(False), ""


def run_indicators_analysis(frame, cancers, year_start, year_end):
    """Return report-ready counts for every configured selected indicator."""
    year_mask, error = _year_mask(frame, year_start, year_end)
    if error:
        return {"ok": False, "error": error}

    selected = [str(key) for key in (cancers or []) if str(key).strip()]
    reports = []
    for cancer_key in selected:
        definitions = get_indicator_definitions(cancer_key)
        cancer_cases = frame.loc[year_mask & _cancer_mask(frame, cancer_key)].copy()
        if not definitions:
            reports.append({"cancer_key": cancer_key, "input_count": int(len(cancer_cases)), "indicators": [], "message": "此癌別尚未設定監測指標定義。"})
            continue

        # Cancer-specific definitions identify whether shared exclusions apply.
        included_cases, audit_cases, global_summary = apply_global_indicators_exclusions(
            cancer_cases, is_hospital_self_reported=True
        )
        indicators = []
        for definition in definitions:
            masks = definition["calculator"](included_cases)
            denominator = int(masks["denominator_mask"].sum())
            numerator = int(masks["numerator_mask"].sum())
            indicators.append({
                "id": definition["id"],
                "direction": definition["direction"],
                "name": definition["name"],
                "numerator_definition": definition["numerator_definition"],
                "denominator_definition": definition["denominator_definition"],
                "numerator": numerator,
                "denominator": denominator,
                "percentage": round(numerator / denominator * 100, 1) if denominator else None,
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
