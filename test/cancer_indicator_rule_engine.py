from __future__ import annotations
from datetime import date, datetime
from typing import Any

Record = dict[str, Any]
RuleConfig = dict[str, Any]

INVALID_DATE_VALUES = {"", "00000000", None}

def to_int(value: Any) -> int | None:
    """安全轉換整數，例如 '040' 轉成 40。"""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def parse_date(value: Any) -> date | None:
    """將 YYYYMMDD 轉成日期；空值、00000000 或錯誤日期回傳 None。"""
    if value is None:
        return None
    text = str(value).strip()
    if text in INVALID_DATE_VALUES:
        return None
    try:
        return datetime.strptime(text, "%Y%m%d").date()
    except ValueError:
        return None


def normalize_text(value: Any) -> str | None:
    """統一文字格式，供 A、B、C、2E 等英數代碼比較使用。"""
    if value is None:
        return None
    text = str(value).strip().upper()
    return text or None


# ---------------------------------------------------------------------------
# 規則設定：欄位名稱可以依實際資料庫或 Excel 欄名調整
# ---------------------------------------------------------------------------

ORAL_CANCER_RULES: dict[int, dict[str, Any]] = {
    1: {
        "name": "口腔癌病人手術後6週內開始輔助治療的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "between", "field": "surgery_code", "min": 30, "max": 90},
                {"op": "valid_date", "field": "surgery_date"},
                # 依目前表格的新增條件：放射治療開始日期不得為 00000000。
                {"op": "valid_date", "field": "radiation_date"},
                {
                    "op": "any",
                    "rules": [
                        {
                            "op": "date_after",
                            "start_field": "surgery_date",
                            "end_field": "radiation_date",
                        },
                        {
                            "op": "date_after",
                            "start_field": "surgery_date",
                            "end_field": "chemotherapy_date",
                        },
                    ],
                },
            ],
        },
        "numerator": {
            "op": "earliest_after_within",
            "reference_field": "surgery_date",
            "candidate_fields": ["radiation_date", "chemotherapy_date"],
            "min_days": 1,
            "max_days": 42,
        },
    },
    2: {
        "name": "口腔癌病人手術後30天內死亡的比率",
        "type": "negative",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "between", "field": "surgery_code", "min": 30, "max": 90},
                {"op": "equals", "field": "palliative_care", "value": 0},
                {"op": "valid_date", "field": "surgery_date"},
            ],
        },
        "numerator": {
            "op": "all",
            "rules": [
                {"op": "equals", "field": "survival_status", "value": 0},
                {
                    "op": "date_interval",
                    "start_field": "surgery_date",
                    "end_field": "last_contact_date",
                    "min_days": 0,
                    "max_days": 30,
                },
            ],
        },
    },
    3: {
        "name": "口腔癌病人接受放射治療（不含化療）後90天內死亡的比率",
        "type": "negative",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "valid_date", "field": "radiation_date"},
                {"op": "greater_than", "field": "radiation_dose", "value": 0},
                {"op": "equals", "field": "chemotherapy_code", "value": 0},
                {"op": "equals", "field": "palliative_care", "value": 0},
            ],
        },
        "numerator": {
            "op": "all",
            "rules": [
                {"op": "equals", "field": "survival_status", "value": 0},
                {
                    "op": "date_interval",
                    "start_field": "radiation_date",
                    "end_field": "last_contact_date",
                    "min_days": 0,
                    "max_days": 90,
                },
            ],
        },
    },
    4: {
        "name": "口腔癌病人同步化學及放射治療後90天內死亡的比率",
        "type": "negative",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "valid_date", "field": "radiation_date"},
                {"op": "greater_than", "field": "radiation_dose", "value": 0},
                {"op": "greater_than", "field": "chemotherapy_code", "value": 0},
                {
                    "op": "not_in",
                    "field": "chemotherapy_code",
                    "values": [82, 83, 85, 86, 87, 88, 99],
                },
                {"op": "valid_date", "field": "chemotherapy_date"},
                {"op": "equals", "field": "palliative_care", "value": 0},
            ],
        },
        "numerator": {
            "op": "all",
            "rules": [
                {"op": "equals", "field": "survival_status", "value": 0},
                {
                    "op": "earliest_date_interval",
                    "start_fields": ["radiation_date", "chemotherapy_date"],
                    "end_field": "last_contact_date",
                    "min_days": 0,
                    "max_days": 90,
                },
            ],
        },
    },
    5: {
        "name": "第一個口腔癌淋巴結病理檢查15顆以上的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "equals", "field": "sequence_number", "value": 1},
                {"op": "between", "field": "surgery_code", "min": 30, "max": 80},
            ],
        },
        "numerator": {
            "op": "between",
            "field": "lymph_nodes_examined",
            "min": 15,
            "max": 90,
        },
    },
    6: {
        "name": "口腔癌根除性手術病理切緣小於4mm的比率",
        "type": "negative",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "between", "field": "histology", "min": 8050, "max": 8086},
                {"op": "between", "field": "surgery_code", "min": 30, "max": 90},
                {"op": "not_in", "field": "margin_distance", "values": [991, 999]},
            ],
        },
        "numerator": {
            "op": "any",
            "rules": [
                {"op": "between", "field": "margin_distance", "min": 0, "max": 39},
                {"op": "equals", "field": "margin_distance", "value": 987},
            ],
        },
    },
}


# ---------------------------------------------------------------------------
# 食道癌品質指標
# 注意：surgical_margin 等欄位包含英文字母，因此使用文字型運算子。
# ---------------------------------------------------------------------------

ESOPHAGEAL_CANCER_RULES: dict[int, dict[str, Any]] = {
    1: {
        "name": "食道癌手術切除標本切除端無殘餘侵襲性癌細胞（R0切除）的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "between", "field": "surgery_code", "min": 30, "max": 90},
                # 2E、2M 無法轉成整數，本來就不會符合 between；保留此規則以對應規格。
                {"op": "text_not_in", "field": "surgery_code", "values": ["2E", "2M"]},
                {"op": "first_char_in", "field": "clinical_m", "values": ["0"]},
            ],
        },
        "numerator": {
            "op": "text_in",
            "field": "surgical_margin",
            "values": ["0", "C", "D", "E"],
        },
    },
    2: {
        "name": "食道切除標本淋巴結病理檢查15顆以上的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "between", "field": "surgery_code", "min": 30, "max": 90},
                {"op": "text_in", "field": "case_classification", "values": ["1", "2"]},
                {
                    "op": "text_not_in",
                    "field": "surgical_margin",
                    "values": ["2", "3", "4", "A", "B"],
                },
            ],
        },
        "numerator": {
            "op": "between",
            "field": "lymph_nodes_examined",
            "min": 15,
            "max": 90,
        },
    },
    3: {
        "name": "接受食道切除手術後30天內死亡的比率",
        "type": "negative",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "between", "field": "surgery_code", "min": 30, "max": 90},
                {"op": "equals", "field": "palliative_care", "value": 0},
                {"op": "valid_date", "field": "surgery_date"},
            ],
        },
        "numerator": {
            "op": "all",
            "rules": [
                {"op": "equals", "field": "survival_status", "value": 0},
                {
                    "op": "date_interval",
                    "start_field": "surgery_date",
                    "end_field": "last_contact_date",
                    "min_days": 0,
                    "max_days": 30,
                },
            ],
        },
    },
    4: {
        "name": "指定臨床分期接受食道切除手術前引導性化學及放射治療的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "between", "field": "surgery_code", "min": 30, "max": 80},
                {"op": "text_equals", "field": "sequence_number", "value": "01"},
                {
                    "op": "any",
                    "rules": [
                        # A：cT4N0M0。
                        {
                            "op": "all",
                            "rules": [
                                {"op": "first_char_in", "field": "clinical_t", "values": ["4"]},
                                {"op": "first_char_in", "field": "clinical_n", "values": ["0"]},
                                {"op": "first_char_in", "field": "clinical_m", "values": ["0"]},
                            ],
                        },
                        # B：cTanyN1-3M0。
                        {
                            "op": "all",
                            "rules": [
                                {"op": "first_char_in", "field": "clinical_n", "values": ["1", "2", "3"]},
                                {"op": "first_char_in", "field": "clinical_m", "values": ["0"]},
                            ],
                        },
                    ],
                },
            ],
        },
        # 分子：放射治療與化學治療日期皆有效，且皆早於手術日期。
        "numerator": {
            "op": "all",
            "rules": [
                {"op": "valid_date", "field": "surgery_date"},
                {"op": "valid_date", "field": "radiation_date"},
                {"op": "valid_date", "field": "chemotherapy_date"},
                {
                    "op": "date_after",
                    "start_field": "radiation_date",
                    "end_field": "surgery_date",
                },
                {
                    "op": "date_after",
                    "start_field": "chemotherapy_date",
                    "end_field": "surgery_date",
                },
            ],
        },
    },
}


# 癌別代碼是程式內部使用的穩定識別值；顯示名稱可另外修改。
INDICATOR_RULES: dict[str, dict[int, dict[str, Any]]] = {
    "oral_cancer": ORAL_CANCER_RULES,
    "esophageal_cancer": ESOPHAGEAL_CANCER_RULES,
}


# ---------------------------------------------------------------------------
# 通用規則引擎：一般新增指標不需要修改這一段
# ---------------------------------------------------------------------------

def evaluate_rule(record: Record, rule: RuleConfig) -> bool:
    """遞迴解讀一個規則設定。"""
    operation = rule.get("op")

    if operation == "all":
        return all(evaluate_rule(record, item) for item in rule["rules"])

    if operation == "any":
        return any(evaluate_rule(record, item) for item in rule["rules"])

    if operation == "equals":
        return to_int(record.get(rule["field"])) == to_int(rule["value"])

    if operation == "text_equals":
        return normalize_text(record.get(rule["field"])) == normalize_text(rule["value"])

    if operation == "text_in":
        value = normalize_text(record.get(rule["field"]))
        allowed = {normalize_text(item) for item in rule["values"]}
        return value is not None and value in allowed

    if operation == "text_not_in":
        value = normalize_text(record.get(rule["field"]))
        excluded = {normalize_text(item) for item in rule["values"]}
        return value is not None and value not in excluded

    if operation == "first_char_in":
        value = normalize_text(record.get(rule["field"]))
        allowed = {normalize_text(item) for item in rule["values"]}
        return value is not None and value[0] in allowed

    if operation == "between":
        value = to_int(record.get(rule["field"]))
        return value is not None and rule["min"] <= value <= rule["max"]

    if operation == "greater_than":
        value = to_int(record.get(rule["field"]))
        return value is not None and value > rule["value"]

    if operation == "not_in":
        value = to_int(record.get(rule["field"]))
        excluded = {to_int(item) for item in rule["values"]}
        return value is not None and value not in excluded

    if operation == "valid_date":
        return parse_date(record.get(rule["field"])) is not None

    if operation == "date_after":
        start_date = parse_date(record.get(rule["start_field"]))
        end_date = parse_date(record.get(rule["end_field"]))
        return start_date is not None and end_date is not None and end_date > start_date

    if operation == "date_interval":
        start_date = parse_date(record.get(rule["start_field"]))
        end_date = parse_date(record.get(rule["end_field"]))
        if start_date is None or end_date is None:
            return False
        days = (end_date - start_date).days
        return rule["min_days"] <= days <= rule["max_days"]

    if operation == "earliest_after_within":
        reference_date = parse_date(record.get(rule["reference_field"]))
        if reference_date is None:
            return False

        candidate_dates = [
            parsed
            for field in rule["candidate_fields"]
            if (parsed := parse_date(record.get(field))) is not None
            and parsed > reference_date
        ]
        if not candidate_dates:
            return False

        days = (min(candidate_dates) - reference_date).days
        return rule["min_days"] <= days <= rule["max_days"]

    if operation == "earliest_date_interval":
        start_dates = [
            parsed
            for field in rule["start_fields"]
            if (parsed := parse_date(record.get(field))) is not None
        ]
        end_date = parse_date(record.get(rule["end_field"]))
        if not start_dates or end_date is None:
            return False

        days = (end_date - min(start_dates)).days
        return rule["min_days"] <= days <= rule["max_days"]

    raise ValueError(f"不支援的規則運算子：{operation!r}")


def evaluate_record(record: Record, cancer_type: str) -> dict[int, dict[str, Any]]:
    """依指定癌別，判斷單筆資料是否符合各指標的分母及分子。"""
    if cancer_type not in INDICATOR_RULES:
        available = ", ".join(INDICATOR_RULES)
        raise ValueError(f"不支援的癌別：{cancer_type!r}；可用癌別：{available}")

    results: dict[int, dict[str, Any]] = {}
    cancer_rules = INDICATOR_RULES[cancer_type]

    for indicator_number, indicator in cancer_rules.items():
        denominator = evaluate_rule(record, indicator["denominator"])
        numerator_rule = indicator.get("numerator")

        # None 表示目前規格尚未提供分子，不能擅自判定為 False。
        numerator = (
            None
            if numerator_rule is None
            else denominator and evaluate_rule(record, numerator_rule)
        )

        if numerator is None:
            status = "分子規則尚未定義"
        elif numerator:
            status = "符合分子"
        elif denominator:
            status = "符合分母，但不符合分子"
        else:
            status = "不符合分母"

        results[indicator_number] = {
            "indicator_number": indicator_number,
            "cancer_type": cancer_type,
            "indicator_name": indicator["name"],
            "indicator_type": indicator["type"],
            "denominator": denominator,
            "numerator": numerator,
            "status": status,
        }

    return results


def calculate_indicator_summary(records: list[Record], cancer_type: str) -> dict[int, dict[str, Any]]:
    """依癌別統計多筆資料的分子數、分母數與指標比率。"""
    if cancer_type not in INDICATOR_RULES:
        raise ValueError(f"不支援的癌別：{cancer_type!r}")

    cancer_rules = INDICATOR_RULES[cancer_type]
    summary = {
        number: {
            "indicator_number": number,
            "indicator_name": indicator["name"],
            "indicator_type": indicator["type"],
            "denominator_count": 0,
            "numerator_count": 0,
            "rate": None,
            "numerator_defined": indicator.get("numerator") is not None,
        }
        for number, indicator in cancer_rules.items()
    }

    for record in records:
        for number, result in evaluate_record(record, cancer_type).items():
            summary[number]["denominator_count"] += int(result["denominator"])
            if result["numerator"] is not None:
                summary[number]["numerator_count"] += int(result["numerator"])

    for result in summary.values():
        denominator = result["denominator_count"]
        if denominator and result["numerator_defined"]:
            result["rate"] = round(result["numerator_count"] / denominator * 100, 2)
    return summary