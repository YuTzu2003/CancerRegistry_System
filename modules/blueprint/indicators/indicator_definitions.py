"""
癌症登記欄位對照與指標定義組裝器 (Indicator Definitions & Column Mapping)
負責：
1. 定義規則使用的癌症登記欄位代碼。
2. 提供指標條件評估之計算器包裝器 (_calculator_for)。
3. 從資料庫讀取指標收案條件與分子分母文字定義 (Metadata)。
4. 彙整各癌別規則與計算器供分析引擎調用。
"""

from __future__ import annotations
import re
import pandas as pd
from modules.blueprint.indicators.catalog import get_indicator_rules
from modules.blueprint.indicators.exclusion_rules import _clean_code
from modules.blueprint.indicators.rule import evaluate_rule

def _is_nsclc(value) -> bool:
    try:
        code = int(float(_clean_code(value)))
    except (TypeError, ValueError):
        return False
    return code != 8002 and not 8041 <= code <= 8045

def _record_for(row):
    record = {}
    for column, value in row.items():
        header = str(column).strip()
        match = re.match(r"^(\d+(?:\.\d+)*)(?:$|[^0-9.])", header)
        record[match.group(1) if match else header] = value
    record["is_nsclc"] = "TRUE" if _is_nsclc(record.get("2.8")) else "FALSE"
    return record

def _calculator_for(rule):
    def calculator(frame):
        denominator_values = []
        numerator_values = []
        for _, row in frame.iterrows():
            record = _record_for(row)
            denominator = bool(evaluate_rule(record, rule["denominator"]))
            numerator = denominator and bool(evaluate_rule(record, rule["numerator"]))
            denominator_values.append(denominator)
            numerator_values.append(numerator)
        return {
            "denominator_mask": pd.Series(denominator_values, index=frame.index, dtype=bool),
            "numerator_mask": pd.Series(numerator_values, index=frame.index, dtype=bool),
        }
    return calculator

# ---------------------------------------------------------------------------
# 資料庫詮釋資料查詢 (Metadata)
# ---------------------------------------------------------------------------
def _metadata_by_indicator(cancer_key):
    from modules.services.db import get_conn

    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT indicator_no, selection_reason, numerator_definition, denominator_definition, notes FROM dbo.Indicator_definition_metadata WHERE cancer_group_key = ?",(str(cancer_key or ""),),)
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
    return [
        {"id": number, **definition}
        for number, definition in sorted(_metadata_by_indicator(cancer_key).items())
    ]

# ---------------------------------------------------------------------------
# 完整指標定義取得入口
# ---------------------------------------------------------------------------
def get_indicator_definitions(cancer_key, metadata=None):
    rules = get_indicator_rules(cancer_key)
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