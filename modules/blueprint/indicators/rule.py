"""
通用規則引擎 (Universal Rule Engine)

本模組提供指標運算之規則解讀與評估邏輯：
1. 基礎欄位型別轉換（整數、日期、字串、期別代碼）。
2. 支援複合條件（all, any, not）與各類運算子（數值、文字、日期、放射治療 BED 等）。
3. 單筆資料與整批資料之分子/分母命中判定。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

Record = dict[str, Any]
RuleConfig = dict[str, Any]

INVALID_DATE_VALUES = {"", "00000000", "88888888", None}


# ---------------------------------------------------------------------------
# 共用轉換工具
# ---------------------------------------------------------------------------
def to_int(value: Any) -> int | None:
    """安全轉換整數，例如 '040' 或 Excel 的 40.0 都轉成 40。"""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        number = float(text)
        return int(number) if number.is_integer() else None
    except (TypeError, ValueError):
        return None


def parse_date(value: Any) -> date | None:
    """接受 YYYYMMDD、YYYY/MM/DD、YYYY-MM-DD 及 Excel 日期物件。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    digits = "".join(character for character in text if character.isdigit())
    if digits in INVALID_DATE_VALUES or len(digits) != 8:
        return None
    # 登錄日期的月碼或日碼為 99 時，仍可納入指標判定；以一日代替。
    if digits[4:6] == "99":
        digits = f"{digits[:4]}01{digits[6:]}"
    if digits[6:8] == "99":
        digits = f"{digits[:6]}01"
    try:
        return datetime.strptime(digits, "%Y%m%d").date()
    except ValueError:
        return None


def normalize_text(value: Any) -> str | None:
    """統一文字格式，供 A、B、C、2E 等英數代碼比較使用。"""
    if value is None:
        return None
    text = str(value).strip().upper()
    return None if text in {"", "NAN", "NONE", "NAT"} else text


def normalize_stage(value: Any) -> str | None:
    """標準化期別字串，去除前綴 STAGE、空白與逗號，並將羅馬數字轉為阿拉伯數字。"""
    text = normalize_text(value)
    if text is None:
        return None
    text = text.replace("STAGE", "").replace(" ", "").replace(",", "")
    for roman, number in (("IV", "4"), ("III", "3"), ("II", "2"), ("I", "1")):
        if text.startswith(roman):
            return number + text[len(roman):]
    return text


def normalize_code(value: Any) -> str | None:
    text = normalize_text(value)
    if text is None:
        return None
    normalized = "".join(character for character in text if character.isalnum())
    return normalized or None


# ---------------------------------------------------------------------------
# 通用規則運算子解讀引擎
# ---------------------------------------------------------------------------
def evaluate_rule(record: Record, rule: RuleConfig) -> bool:
    """遞迴解讀並計算單一規則設定。"""
    operation = rule.get("op")

    # 邏輯運算子
    if operation == "all":
        return all(evaluate_rule(record, item) for item in rule["rules"])

    if operation == "any":
        return any(evaluate_rule(record, item) for item in rule["rules"])

    if operation == "not":
        return not evaluate_rule(record, rule["rule"])

    # 數值與文字比對運算子
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

    if operation == "code_in":
        value = normalize_code(record.get(rule["field"]))
        allowed = {normalize_code(item) for item in rule["values"]}
        return value is not None and value in allowed

    if operation == "code_prefix_in":
        value = normalize_code(record.get(rule["field"]))
        prefixes = [normalize_code(item) for item in rule["values"]]
        return value is not None and any(prefix is not None and value.startswith(prefix) for prefix in prefixes)

    if operation == "text_starts_with":
        value = normalize_text(record.get(rule["field"]))
        prefixes = tuple(normalize_text(item) for item in rule["values"])
        return value is not None and value.startswith(prefixes)

    if operation == "text_not_equals":
        value = normalize_text(record.get(rule["field"]))
        return value is not None and value != normalize_text(rule["value"])

    if operation == "text_in_without_prefix":
        value = normalize_text(record.get(rule["field"]))
        prefix = normalize_text(rule["prefix"])
        if value is None:
            return False
        if prefix and value.startswith(prefix):
            value = value[len(prefix):]
        return value in {normalize_text(item) for item in rule["values"]}

    if operation == "zero_fill_text_in":
        value = normalize_text(record.get(rule["field"]))
        return value is not None and value.zfill(rule["width"]) in {
            normalize_text(item) for item in rule["values"]
        }

    if operation == "all_fields_not_in":
        excluded = {normalize_text(item) for item in rule["values"]}
        return all(normalize_text(record.get(field)) not in excluded for field in rule["fields"])

    if operation == "concatenated_text_in":
        value = "".join(normalize_text(record.get(field)) or "" for field in rule["fields"])
        return value in {normalize_text(item) for item in rule["values"]}

    if operation == "present":
        return normalize_text(record.get(rule["field"])) is not None

    # 期別專用比對運算子
    if operation == "stage_first_char_in":
        value = normalize_stage(record.get(rule["field"]))
        return value is not None and value[0] in set(rule["values"])

    if operation == "stage_in":
        value = normalize_stage(record.get(rule["field"]))
        return value is not None and value in set(rule["values"])

    if operation == "preferred_stage_in":
        preferred = normalize_stage(record.get(rule["preferred_field"]))
        if preferred in set(rule["invalid_values"]):
            preferred = normalize_stage(record.get(rule["fallback_field"]))
        return preferred is not None and preferred in set(rule["values"])

    if operation == "stage_matches":
        import re

        value = normalize_stage(record.get(rule["field"]))
        return value is not None and re.fullmatch(rule["pattern"], value) is not None

    if operation == "first_char_in":
        value = normalize_text(record.get(rule["field"]))
        allowed = {normalize_text(item) for item in rule["values"]}
        return value is not None and value[0] in allowed

    # 數值範圍與大小運算子
    if operation == "between":
        value = to_int(record.get(rule["field"]))
        return value is not None and rule["min"] <= value <= rule["max"]

    if operation == "greater_than":
        value = to_int(record.get(rule["field"]))
        return value is not None and value > rule["value"]

    if operation == "greater_than_or_equal":
        value = to_int(record.get(rule["field"]))
        return value is not None and value >= rule["value"]

    if operation == "not_in":
        value = to_int(record.get(rule["field"]))
        excluded = {to_int(item) for item in rule["values"]}
        return value is not None and value not in excluded

    if operation == "in":
        value = to_int(record.get(rule["field"]))
        return value is not None and value in {to_int(item) for item in rule["values"]}

    # 日期與時間區間運算子
    if operation == "valid_date":
        return parse_date(record.get(rule["field"])) is not None

    if operation == "date_year_between":
        value = parse_date(record.get(rule["field"]))
        return value is not None and rule["min"] <= value.year <= rule["max"]

    if operation == "date_after":
        start_date = parse_date(record.get(rule["start_field"]))
        end_date = parse_date(record.get(rule["end_field"]))
        return start_date is not None and end_date is not None and end_date > start_date

    if operation == "date_on_or_after":
        start_date = parse_date(record.get(rule["start_field"]))
        end_date = parse_date(record.get(rule["end_field"]))
        return start_date is not None and end_date is not None and end_date >= start_date

    if operation == "dates_equal":
        left = parse_date(record.get(rule["left_field"]))
        right = parse_date(record.get(rule["right_field"]))
        return left is not None and right is not None and left == right

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

    if operation == "any_date_on_or_after":
        reference_date = parse_date(record.get(rule["reference_field"]))
        return reference_date is not None and any(
            (candidate := parse_date(record.get(field))) is not None and candidate >= reference_date
            for field in rule["candidate_fields"]
        )

    if operation == "earliest_on_or_after_within":
        reference_date = parse_date(record.get(rule["reference_field"]))
        if reference_date is None:
            return False
        candidates = [
            candidate for field in rule["candidate_fields"]
            if (candidate := parse_date(record.get(field))) is not None and candidate >= reference_date
        ]
        if not candidates:
            return False
        days = (min(candidates) - reference_date).days
        return rule["min_days"] <= days <= rule["max_days"]

    # 放射治療 BED (Biological Effective Dose) 門檻運算子
    if operation == "bed_at_least":
        alpha_beta = rule.get("alpha_beta", 1.8)

        def bed(dose_field: str, fractions_field: str) -> float | None:
            dose = to_int(record.get(dose_field))
            fractions = to_int(record.get(fractions_field))
            if dose is None or fractions is None or fractions <= 0:
                return None
            total_gy = dose / 100
            return total_gy * (1 + total_gy / fractions / alpha_beta)

        values = [bed(item["dose_field"], item["fractions_field"]) for item in rule["courses"]]
        doses = [to_int(record.get(item["dose_field"])) or 0 for item in rule["courses"]]
        fractions = [to_int(record.get(item["fractions_field"])) or 0 for item in rule["courses"]]
        total_gy = sum(doses) / 100
        fraction_dose = sum(
            dose / 100 / fraction
            for dose, fraction in zip(doses, fractions)
            if fraction > 0
        )
        values.append(total_gy * (1 + fraction_dose / alpha_beta))
        return max((value for value in values if value is not None), default=float("-inf")) >= rule["value"]

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


# ---------------------------------------------------------------------------
# 單筆紀錄規則判定與多筆資料指標統計
# ---------------------------------------------------------------------------
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
