"""Expose configured cancer-indicator rules and registry field mappings."""

from __future__ import annotations

import re

import pandas as pd

from modules.blueprint.indicators.cancer_indicator import (
    BLADDER_CANCER_RULES,
    BREAST_CANCER_RULES,
    CERVICAL_CANCER_RULES,
    COLON_RECTUM_CANCER_RULES,
    CORPUS_UTERI_CANCER_RULES,
    ESOPHAGEAL_CANCER_RULES,
    GASTRIC_CANCER_RULES,
    LIVER_CANCER_RULES,
    LUNG_CANCER_RULES,
    ORAL_CANCER_RULES,
    OVARY_CANCER_RULES,
    PANCREATIC_CANCER_RULES,
    PROSTATE_CANCER_RULES,
)
from modules.blueprint.indicators.exclusion_rules import _clean_code, _find_column
from modules.blueprint.indicators.rule import evaluate_rule

RULES_BY_CANCER = {
    "Oral_Cavity": ORAL_CANCER_RULES,
    "Esophagus": ESOPHAGEAL_CANCER_RULES,
    "Stomach": GASTRIC_CANCER_RULES,
    "Colon_Rectum": COLON_RECTUM_CANCER_RULES,
    "Liver": LIVER_CANCER_RULES,
    "Pancreas": PANCREATIC_CANCER_RULES,
    "Cervix_Uteri": CERVICAL_CANCER_RULES,
    "Lung": LUNG_CANCER_RULES,
    "Breast": BREAST_CANCER_RULES,
    "Ovary": OVARY_CANCER_RULES,
    "Prostate": PROSTATE_CANCER_RULES,
    "Bladder": BLADDER_CANCER_RULES,
    "Corpus_Uteri": CORPUS_UTERI_CANCER_RULES,
}

FIELD_SPECS = {
    "diagnosis_date": ("2.5", ("最初診斷日期", "didiag", "診斷日期")),
    "site": ("2.6", ("原發部位", "site")),
    "microscopic_confirmation_date": ("2.12", ("首次顯微鏡檢證實日期",)),
    "surgery_code": ("4.1.4", ("申報醫院原發部位手術方式",)),
    "surgery_date": ("4.1.2", ("原發部位最確切的手術切除日期",)),
    "radiation_date": ("4.2.1.3", ("放射治療開始日期",)),
    "radiation_dose": ("4.2.2.2.2", ("最高放射劑量臨床標靶體積劑量",)),
    "chemotherapy_code": ("4.3.3", ("申報醫院化學治療",)),
    "chemotherapy_date": ("4.3.4", ("申報醫院化學治療開始日期",)),
    "palliative_care": ("4.4", ("申報醫院緩和照護",)),
    "survival_status": ("5.4", ("生存狀態",)),
    "last_contact_date": ("5.3", ("最後聯絡或死亡日期",)),
    "lymph_nodes_examined": ("2.14", ("區域淋巴結檢查數目",)),
    "sequence_number": ("2.2", ("癌症發生順序號碼",)),
    "histology": ("2.8", ("組織型態",)),
    "margin_distance": ("4.1.5.1", ("原發部位手術切緣距離",)),
    "surgical_margin": ("4.1.5", ("原發部位手術邊緣",)),
    "clinical_t": ("3.4", ("臨床T", "臨床 T")),
    "clinical_n": ("3.5", ("臨床N", "臨床 N")),
    "clinical_m": ("3.6", ("臨床M", "臨床 M")),
    "case_classification": ("2.3", ("個案分類", "class")),
    "clinical_stage": ("3.7", ("臨床期別組合",)),
    "pathological_stage": ("3.13", ("病理期別組合",)),
    "pathology_prefix": ("3.14", ("病理分期字根", "病理分期字首")),
    "treatment_status": ("2.3.2", ("治療狀態分類",)),
    "other_staging_system": ("3.17", ("其他分期系統",)),
    "other_clinical_stage": ("3.19", ("其他分期系統期別(臨床期別)",)),
    "first_treatment_date": ("4.1", ("首次療程開始日期",)),
    "first_surgery_date": ("4.1.1", ("首次手術日期",)),
}


def _is_nsclc(value) -> bool:
    try:
        code = int(float(_clean_code(value)))
    except (TypeError, ValueError):
        return False
    return code != 8002 and not 8041 <= code <= 8045


def _column_map(frame):
    return {
        field: _find_column(frame.columns, code, aliases)
        for field, (code, aliases) in FIELD_SPECS.items()
    }


def _record_for(row, columns):
    record = {}
    for column, value in row.items():
        header = str(column).strip()
        match = re.match(r"^(\d+(?:\.\d+)*)(?:$|[^0-9.])", header)
        if match:
            record[match.group(1)] = value
    for field, column in columns.items():
        record[field] = row[column] if column else None
    record["is_nsclc"] = "TRUE" if _is_nsclc(record.get("2.8")) else "FALSE"
    return record


def _calculator_for(rule):
    def calculator(frame):
        columns = _column_map(frame)
        denominator_values = []
        numerator_values = []
        for _, row in frame.iterrows():
            record = _record_for(row, columns)
            denominator = bool(evaluate_rule(record, rule["denominator"]))
            numerator = denominator and bool(evaluate_rule(record, rule["numerator"]))
            denominator_values.append(denominator)
            numerator_values.append(numerator)
        return {
            "denominator_mask": pd.Series(denominator_values, index=frame.index, dtype=bool),
            "numerator_mask": pd.Series(numerator_values, index=frame.index, dtype=bool),
        }

    return calculator


def _metadata_by_indicator(cancer_key):
    from modules.services.db import get_conn

    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT indicator_no, selection_reason, numerator_definition,
                   denominator_definition, notes, target_value, target_operator
            FROM dbo.Indicator_definition_metadata
            WHERE cancer_group_key = ?
            """,
            (str(cancer_key or ""),),
        )
        return {
            int(row[0]): {
                "selection_reason": row[1] or "",
                "numerator_definition": row[2] or "",
                "denominator_definition": row[3] or "",
                "notes": row[4] or "",
                "target_value": float(row[5]) if row[5] is not None else None,
                "target_operator": row[6] or "",
            }
            for row in cursor.fetchall()
        }
    finally:
        conn.close()


def get_indicator_metadata(cancer_key):
    return [
        {"id": number, **definition}
        for number, definition in sorted(_metadata_by_indicator(cancer_key).items())
    ]


def get_indicator_definitions(cancer_key, metadata=None):
    rules = RULES_BY_CANCER.get(str(cancer_key or ""), {})
    if metadata is None:
        metadata = _metadata_by_indicator(cancer_key)
    elif isinstance(metadata, list):
        metadata = {
            definition["id"]: {
                key: value for key, value in definition.items() if key != "id"
            }
            for definition in metadata
        }
    return [
        {
            "id": number,
            "direction": rule["type"],
            "name": rule["name"],
            "selection_reason": metadata.get(number, {}).get("selection_reason", ""),
            "numerator_definition": metadata.get(number, {}).get("numerator_definition", "")
            or "依已設定的分子規則計算。",
            "denominator_definition": metadata.get(number, {}).get("denominator_definition", "")
            or "依已設定的分母規則計算。",
            "notes": metadata.get(number, {}).get("notes", ""),
            "target_value": metadata.get(number, {}).get("target_value"),
            "target_operator": metadata.get(number, {}).get("target_operator", "") or ("<=" if rule["type"] == "negative" else ">="),
            "calculator": _calculator_for(rule),
        }
        for number, rule in sorted(rules.items())
    ]
