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

# Registry fields referenced by indicator rules. Labels come from the bundled
# CancerRegistry_FmtField mapping; keep this editor list separate from the
# aliases used by the analysis input parser.
RULE_FIELD_LABELS = {
    **{code: aliases[0] for code, aliases in FIELD_SPECS.values() if aliases},
    '2.3.1': '診斷狀態分類', '2.9': '性態碼', '2.10.1': '臨床分級／分化',
    '2.10.2': '病理分級／分化', '2.15': '區域淋巴結侵犯數目',
    '3.2': '外院診斷性及分期性手術處置', '3.3': '申報醫院診斷性及分期性手術處置',
    '3.11': '病理 N', '3.12': '病理 M', '3.21': '其他分期系統期別（病理分期）',
    '4.1.7': '申報醫院區域淋巴結手術範圍', '4.1.9': '申報醫院其他部位手術方式',
    '4.2.1.1': '放射治療臨床標靶體積摘要', '4.2.1.2': '放射治療儀器',
    '4.2.2.2.3': '最高放射劑量臨床標靶體積治療次數',
    '4.2.3.3.2': '其他放射治療臨床標靶體積劑量',
    '4.2.3.3.3': '其他放射治療臨床標靶體積治療次數',
    '4.3.2': '外院化學治療', '4.3.5': '外院荷爾蒙／類固醇治療',
    '4.3.6': '申報醫院荷爾蒙／類固醇治療', '4.3.8': '外院免疫治療',
    '4.3.9': '申報醫院免疫治療', '4.3.10': '申報醫院免疫治療開始日期',
    '4.3.13': '外院標靶治療', '4.3.14': '申報醫院標靶治療',
    '4.3.15': '申報醫院標靶治療開始日期', '4.5.1': '其他治療',
    '8.1': '癌症部位特定因子 1', '8.3': '癌症部位特定因子 3',
    '8.5': '癌症部位特定因子 5', '8.7': '癌症部位特定因子 7',
    'is_nsclc': '非小細胞肺癌（系統判斷）',
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


def _rule_column_map(frame):
    """Resolve exact registry names to rule codes, without fuzzy name matches."""
    names = {str(column).strip().casefold(): column for column in frame.columns}
    aliases_by_code = {code: aliases for code, aliases in FIELD_SPECS.values()}
    result = {}
    for code, label in RULE_FIELD_LABELS.items():
        if not re.fullmatch(r'\d+(?:\.\d+)*', code):
            continue
        for name in (label, *aliases_by_code.get(code, ())):
            if name.strip().casefold() in names:
                result[code] = names[name.strip().casefold()]
                break
    return result


def _record_for(row, columns, rule_columns=None):
    record = {}
    for column, value in row.items():
        header = str(column).strip()
        match = re.match(r"^(\d+(?:\.\d+)*)(?:$|[^0-9.])", header)
        if match:
            record[match.group(1)] = value
    for field, column in columns.items():
        record[field] = row[column] if column else None
    for code, column in (rule_columns or {}).items():
        if code not in record:
            record[code] = row[column]
    record["is_nsclc"] = "TRUE" if _is_nsclc(record.get("2.8")) else "FALSE"
    return record


def _calculator_for(rule):
    def calculator(frame):
        columns = _column_map(frame)
        rule_columns = _rule_column_map(frame)
        denominator_values = []
        numerator_values = []
        for _, row in frame.iterrows():
            record = _record_for(row, columns, rule_columns)
            denominator = bool(evaluate_rule(record, rule["denominator"]))
            numerator = denominator and bool(evaluate_rule(record, rule["numerator"]))
            denominator_values.append(denominator)
            numerator_values.append(numerator)
        return {
            "denominator_mask": pd.Series(denominator_values, index=frame.index, dtype=bool),
            "numerator_mask": pd.Series(numerator_values, index=frame.index, dtype=bool),
        }

    return calculator


def _metadata_from_rules(rules):
    """Extract metadata fields from indicator rules (already embedded in rules_json)."""
    return {
        int(number): {
            "selection_reason": rule.get("selection_reason", ""),
            "numerator_definition": rule.get("numerator_definition", ""),
            "denominator_definition": rule.get("denominator_definition", ""),
            "notes": rule.get("notes", ""),
            "target_value": rule.get("target_value"),
            "target_operator": rule.get("target_operator", ""),
        }
        for number, rule in rules.items()
    }


def get_indicator_metadata(cancer_key, rules=None):
    if rules is None:
        rules = RULES_BY_CANCER.get(str(cancer_key or ""), {})
    return [
        {"id": number, **meta}
        for number, meta in sorted(_metadata_from_rules(rules).items())
    ]


def get_indicator_definitions(cancer_key, metadata=None, oral_rules=None, rule_override=None):
    rules = RULES_BY_CANCER.get(str(cancer_key or ""), {})
    if cancer_key == 'Oral_Cavity' and oral_rules is not None:
        rules = oral_rules
    if rule_override is not None:
        rules = rule_override
    if metadata is None:
        metadata = _metadata_from_rules(rules)
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
            "selection_reason": rule.get('selection_reason', metadata.get(number, {}).get('selection_reason', '')),
            "numerator_definition": rule.get('numerator_definition', metadata.get(number, {}).get('numerator_definition', '')) or '依已設定的分子規則計算。',
            "denominator_definition": rule.get('denominator_definition', metadata.get(number, {}).get('denominator_definition', '')) or '依已設定的分母規則計算。',
            "notes": rule.get('notes', metadata.get(number, {}).get('notes', '')),
            "target_value": rule.get("target_value", metadata.get(number, {}).get("target_value")),
            "target_operator": rule.get("target_operator", metadata.get(number, {}).get("target_operator", "")) or ("<=" if rule["type"] == "negative" else ">="),
            "calculator": _calculator_for(rule),
        }
        for number, rule in sorted(rules.items())
    ]
