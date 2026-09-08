"""通用規則引擎。

這個檔案只放「規則怎麼被解讀與計算」的通用邏輯。
新增癌別或指標時，一般不需要修改這個檔案，
只需要在 indicators/ 底下新增或修改對應的指標檔即可。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from indicators import INDICATOR_RULES

Record = dict[str, Any]
RuleConfig = dict[str, Any]

INVALID_DATE_VALUES = {"", "00000000", None}


# ---------------------------------------------------------------------------
# 共用轉換工具
# ---------------------------------------------------------------------------

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