"""
癌症登記欄位對照與指標定義組裝器 (Indicator Definitions & Column Mapping)

負責：
1. 定義癌症登記申報代碼與欄位別名對照表 (FIELD_SPECS)。
2. 提供指標條件評估之計算器包裝器 (_calculator_for)。
3. 從資料庫讀取指標收案條件與分子分母文字定義 (Metadata)。
4. 彙整各癌別規則與計算器供分析引擎調用。
"""

from __future__ import annotations
import pandas as pd
from modules.blueprint.indicators.catalog import get_indicator_rules
from modules.blueprint.indicators.exclusion_rules import _clean_code, _find_column
from modules.blueprint.indicators.rule import evaluate_rule

# ---------------------------------------------------------------------------
# 癌症登記欄位規格與中文別名對照表
# ---------------------------------------------------------------------------
FIELD_SPECS = {
    "case_class": ("2.3", ("個案分類", "class")),
    "diagnosis_status": ("2.3.1", ("診斷狀態分類",)),
    "treatment_status": ("2.3.2", ("治療狀態分類",)),
    "diagnosis_date": ("2.5", ("最初診斷日期", "didiag")),
    "histology": ("2.8", ("組織型態", "hist")),
    "clinical_grade": ("2.10.1", ("臨床分級",)),
    "pathological_grade": ("2.10.2", ("病理分級",)),
    "lymph_nodes_examined": ("2.14", ("區域淋巴結檢查數目",)),
    "sequence_number": ("2.2", ("癌症發生順序號碼",)),
    "external_diagnostic_surgery": ("3.2", ("外院診斷性及分期性手術處置",)),
    "hospital_diagnostic_surgery": ("3.3", ("申報醫院診斷性及分期性手術處置",)),
    "clinical_t": ("3.4", ("臨床T", "clinical t")),
    "clinical_n": ("3.5", ("臨床N", "clinical n")),
    "clinical_m": ("3.6", ("臨床M", "clinical m")),
    "clinical_stage": ("3.7", ("臨床期別組合",)),
    "pathological_m": ("3.12", ("病理M",)),
    "pathological_stage": ("3.13", ("病理期別組合", "pathological stage")),
    "other_clinical_stage": ("3.19", ("其他分期系統期別(臨床分期)", "ostagec")),
    "other_pathological_stage": ("3.21", ("其他分期系統期別(病理分期)", "ostagep")),
    "first_course_date": ("4.1", ("首次療程開始日期", "dtrt_1st")),
    "surgery_date": ("4.1.2", ("原發部位最確切的手術切除日期",)),
    "surgery_code": ("4.1.4", ("申報醫院原發部位手術方式",)),
    "margin_distance": ("4.1.5.1", ("原發部位手術切緣距離",)),
    "regional_lymph_surgery": ("4.1.7", ("申報醫院區域淋巴結手術範圍",)),
    "other_site_surgery": ("4.1.9", ("申報醫院其他部位手術方式",)),
    "radiation_summary": ("4.2.1.1", ("放射治療臨床標靶體積摘要",)),
    "radiation_instrument": ("4.2.1.2", ("放射治療儀器",)),
    "radiation_date": ("4.2.1.3", ("放射治療開始日期",)),
    "radiation_dose": ("4.2.2.2.2", ("最高放射劑量臨床標靶體積劑量",)),
    "radiation_fractions": ("4.2.2.2.3", ("最高放射劑量臨床標靶體積治療次數",)),
    "other_radiation_dose": ("4.2.3.3.2", ("較低放射劑量臨床標靶體積劑量",)),
    "other_radiation_fractions": ("4.2.3.3.3", ("較低放射劑量臨床標靶體積治療次數",)),
    "chemotherapy_code": ("4.3.3", ("申報醫院化學治療",)),
    "chemotherapy_date": ("4.3.4", ("申報醫院化學治療開始日期",)),
    "hormone_therapy": ("4.3.6", ("申報醫院荷爾蒙/類固醇治療",)),
    "immunotherapy_date": ("4.3.10", ("申報醫院免疫治療開始日期",)),
    "targeted_therapy_date": ("4.3.15", ("申報醫院標靶治療開始日期",)),
    "palliative_care": ("4.4", ("申報醫院緩和照護",)),
    "other_treatment": ("4.5.1", ("其他治療",)),
    "survival_status": ("5.4", ("生存狀態",)),
    "last_contact_date": ("5.3", ("最後聯絡或死亡日期",)),
    "ssf1": ("8.1", ("癌症部位特定因子 1", "SSF1")),
    "ssf3": ("8.3", ("癌症部位特定因子 3", "SSF3")),
    "clinical_trial_432": ("4.3.2", ("外院化學治療",)),
    "clinical_trial_433": ("4.3.3", ("申報醫院化學治療",)),
    "clinical_trial_435": ("4.3.5", ("外院荷爾蒙/類固醇治療",)),
    "clinical_trial_436": ("4.3.6", ("申報醫院荷爾蒙/類固醇治療",)),
    "clinical_trial_438": ("4.3.8", ("外院免疫治療",)),
    "clinical_trial_439": ("4.3.9", ("申報醫院免疫治療",)),
    "clinical_trial_4313": ("4.3.13", ("外院標靶治療",)),
    "clinical_trial_4314": ("4.3.14", ("申報醫院標靶治療",)),
}


# ---------------------------------------------------------------------------
# 欄位對照與計算器包裝
# ---------------------------------------------------------------------------
FIELD_SPECS.update({
    "site": ("2.6", ("原發部位", "site")),
    "microscopic_confirmation_date": ("2.12", ("首次顯微鏡檢證實日期",)),
    "surgical_margin": ("4.1.5", ("原發部位手術邊緣",)),
    "pathology_prefix": ("3.14", ("病理分期字根", "病理分期字首")),
    "other_staging_system": ("3.17", ("其他分期系統",)),
    "first_treatment_date": ("4.1", ("首次療程開始日期", "dtrt_1st")),
    "first_surgery_date": ("4.1.1", ("首次手術日期",)),
    "case_classification": ("2.3", ("個案分類", "class")),
    "behavior": ("2.9", ("性態碼", "behavior")),
    "figo_stage": ("3.19", ("其他分期系統期別(臨床分期)", "figo_stage")),
    "radiation_end_date": (None, ("放射治療結束日期", "radiation_end_date")),
    "radiation_machine": ("4.2.1.2", ("放射治療儀器", "radiation_machine")),
    "regional_systemic_sequence": (None, ("區域治療與全身性治療順序", "regional_systemic_sequence")),
    "mediastinal_nodes_sampled": (None, ("癌症部位特定因子 5", "mediastinal_nodes_sampled")),
    "pathological_n": ("3.11", ("病理N", "pathological_n")),
    "regional_lymph_node_surgery_scope": ("4.1.7", ("申報醫院區域淋巴結手術範圍", "regional_lymph_node_surgery_scope")),
    "merged_stage": (None, ("SUMMARY_STAGE", "merged_stage")),
    "radiation_status": (None, ("放射治療執行狀態", "radiation_status")),
    "her2": (None, ("癌症部位特定因子 7", "her2")),
    "targeted_therapy_code": (None, ("申報醫院標靶治療", "targeted_therapy_code")),
    "positive_lymph_nodes": (None, ("區域淋巴結侵犯數目", "positive_lymph_nodes")),
})


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


def _calculator_for(rule):
    def calculator(frame):
        columns = _column_map(frame)
        denominator_values = []
        numerator_values = []
        for _, row in frame.iterrows():
            record = {field: row[column] if column else None for field, column in columns.items()}
            record["is_nsclc"] = "TRUE" if _is_nsclc(record["histology"]) else "FALSE"
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
DB_CANCER_KEY_ALIASES = {"Cervix_Uteri": ("Cervix_Uteri", "Cervix Uteri"),}


def _metadata_by_indicator(cancer_key):
    from modules.services.db import get_conn

    database_keys = DB_CANCER_KEY_ALIASES.get(str(cancer_key or ""), (str(cancer_key or ""),))
    placeholders = ", ".join("?" for _ in database_keys)
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""SELECT indicator_no, selection_reason, numerator_definition,
                       denominator_definition, notes
                FROM dbo.indicator_definition_metadata
                WHERE cancer_group_key IN ({placeholders})""",
            database_keys,
        )
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
