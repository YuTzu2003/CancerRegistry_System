from __future__ import annotations
import pandas as pd
from modules.blueprint.indicators.cancer_indicator import ORAL_CANCER_RULES
from modules.blueprint.indicators.exclusion_rules import _find_column
from modules.blueprint.indicators.rule import evaluate_rule

RULES_BY_CANCER = {"Oral_Cavity": ORAL_CANCER_RULES}

FIELD_SPECS = {
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
}


def _column_map(frame):
    return {
        field: _find_column(frame.columns, code, aliases)
        for field, (code, aliases) in FIELD_SPECS.items()
    }


def _calculator_for(rule):
    def calculator(frame):
        columns = _column_map(frame)
        denominator_values = []
        numerator_values = []
        for _, row in frame.iterrows():
            record = {field: row[column] if column else None for field, column in columns.items()}
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
        cursor.execute( """SELECT indicator_no, selection_reason, numerator_definition,denominator_definition, notes FROM dbo.indicator_definition_metadata WHERE cancer_group_key = ?""",(str(cancer_key or ""),),)
        return {
            int(row[0]): {
                "selection_reason": row[1] or "",
                "numerator_definition": row[2] or "",
                "denominator_definition": row[3] or "",
                "notes": row[4] or "",
            }
            for row in cursor.fetchall()
        }
    finally:
        conn.close()


def get_indicator_metadata(cancer_key):
    """Return editable indicator definitions for display, even without a calculator."""
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
            definition["id"]: {key: value for key, value in definition.items() if key != "id"}
            for definition in metadata
        }
    return [
        {
            "id": number,
            "direction": rule["type"],
            "name": rule["name"],
            "selection_reason": metadata.get(number, {}).get("selection_reason", ""),
            "numerator_definition": metadata.get(number, {}).get("numerator_definition", "") or "依已設定的分子規則計算。",
            "denominator_definition": metadata.get(number, {}).get("denominator_definition", "") or "依已設定的分母規則計算。",
            "notes": metadata.get(number, {}).get("notes", ""),
            "calculator": _calculator_for(rule),
        }
        for number, rule in sorted(rules.items())
    ]
