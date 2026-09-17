"""Map uploaded cancer-registry columns to indicator-rule field names."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd


FIELD_ALIASES = {
    "case_classification": ("case_classification", "個案分類"),
    "site": ("site", "原發部位"),
    "histology": ("histology", "組織型態"),
    "behavior": ("behavior", "性態碼"),
    "microscopic_confirmation_date": ("microscopic_confirmation_date", "首次顯微鏡檢證實日期"),
    "palliative_care": ("palliative_care", "申報醫院緩和照護"),
    "first_treatment_date": ("first_treatment_date", "首次療程開始日期"),
    "diagnosis_date": ("diagnosis_date", "最初診斷日期"),
    "surgery_code": ("surgery_code", "申報醫院原發部位手術方式"),
    "surgery_date": ("surgery_date", "原發部位最確切的手術切除日期"),
    "surgical_margin": ("surgical_margin", "原發部位手術邊緣"),
    "margin_distance": ("margin_distance", "原發部位手術切緣距離"),
    "lymph_nodes_examined": ("lymph_nodes_examined", "區域淋巴結檢查數目"),
    "positive_lymph_nodes": ("positive_lymph_nodes", "區域淋巴結侵犯數目"),
    "chemotherapy_date": ("chemotherapy_date", "申報醫院化學治療開始日期"),
    "clinical_stage": ("clinical_stage", "臨床期別組合"),
    "clinical_t": ("clinical_t", "臨床T"),
    "clinical_n": ("clinical_n", "臨床N"),
    "clinical_m": ("clinical_m", "臨床M"),
    "figo_stage": ("figo_stage", "其他分期系統期別(臨床分期)"),
    "radiation_date": ("radiation_date", "放射治療開始日期"),
    "radiation_end_date": ("radiation_end_date", "放射治療結束日期"),
    "radiation_machine": ("radiation_machine", "放射治療儀器"),
    "regional_systemic_sequence": ("regional_systemic_sequence", "區域治療與全身性治療順序"),
    "mediastinal_nodes_sampled": ("mediastinal_nodes_sampled", "癌症部位特定因子 5"),
    "pathological_n": ("pathological_n", "病理N"),
    "regional_lymph_node_surgery_scope": ("regional_lymph_node_surgery_scope", "申報醫院區域淋巴結手術範圍"),
    "merged_stage": ("merged_stage", "SUMMARY_STAGE"),
    "radiation_status": ("radiation_status", "放射治療執行狀態"),
    "radiation_dose": ("radiation_dose", "最高放射劑量臨床標靶體積劑量"),
    "her2": ("her2", "癌症部位特定因子 7"),
    "targeted_therapy_code": ("targeted_therapy_code", "申報醫院標靶治療"),
}

DATE_FIELDS = {
    "microscopic_confirmation_date",
    "first_treatment_date",
    "diagnosis_date",
    "surgery_date",
    "chemotherapy_date",
    "radiation_date",
    "radiation_end_date",
}

PAD_WIDTHS = {
    "radiation_status": 2,
    "targeted_therapy_code": 2,
}


def _text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _registry_date(value: Any) -> str:
    if isinstance(value, (pd.Timestamp,)):
        return value.strftime("%Y%m%d")
    digits = re.sub(r"\D", "", _text(value))
    return digits[:8].zfill(8) if digits else ""


def _normalized_columns(columns) -> dict[str, Any]:
    return {str(column).strip().lower(): column for column in columns}


def _resolve_columns(columns) -> dict[str, Any | None]:
    normalized = _normalized_columns(columns)
    return {
        field: next(
            (normalized[alias.strip().lower()] for alias in aliases if alias.strip().lower() in normalized),
            None,
        )
        for field, aliases in FIELD_ALIASES.items()
    }


def _is_nsclc(histology: Any) -> bool:
    """Current indicator convention: exclude explicit small-cell codes 8002 and 8041-8045."""
    try:
        code = int(float(_text(histology)))
    except (TypeError, ValueError):
        return False
    return code != 8002 and not 8041 <= code <= 8045


def indicator_records(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
    """Return normalized records consumed by ``rule.evaluate_record``."""
    columns = _resolve_columns(dataframe.columns)
    records = []
    for _, row in dataframe.iterrows():
        record = {}
        for field, column in columns.items():
            value = row.get(column) if column is not None else None
            if field in DATE_FIELDS:
                normalized = _registry_date(value)
            else:
                normalized = _text(value)
                width = PAD_WIDTHS.get(field)
                if width and normalized.isdigit():
                    normalized = normalized.zfill(width)
            record[field] = normalized
        record["is_nsclc"] = _is_nsclc(record["histology"])
        records.append(record)
    return records
