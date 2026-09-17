"""通用規則引擎。

這個檔案只放「規則怎麼被解讀與計算」的通用邏輯。
新增癌別或指標時，一般不需要修改這個檔案，
只需要在 indicators/ 底下新增或修改對應的指標檔即可。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from modules.blueprint.indicators.cancer_indicator import CANCER_BASE_RULES, INDICATOR_RULES

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
    """將 YYYYMMDD 轉成日期；日為99時按癌登規則以01計算。"""
    if value is None:
        return None
    text = str(value).strip()
    if text in INVALID_DATE_VALUES:
        return None
    if len(text) == 8 and text.isdigit() and text[6:8] == "99":
        text = f"{text[:6]}01"
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


def normalize_code(value: Any) -> str | None:
    """統一癌登代碼格式，例如 C54.1、C541 皆轉成 C541。"""
    text = normalize_text(value)
    if text is None:
        return None
    normalized = "".join(character for character in text if character.isalnum())
    return normalized or None


# ---------------------------------------------------------------------------
# 通用規則引擎：一般新增指標不需要修改這一段
# ---------------------------------------------------------------------------

def evaluate_rule(record: Record, rule: RuleConfig) -> bool:
    operation = rule.get("op")

    # 全部規則都成立，相當於「且」
    if operation == "all":
        return all(evaluate_rule(record, item) for item in rule["rules"])

    # 至少一條規則成立，相當於「或」
    if operation == "any":
        return any(evaluate_rule(record, item) for item in rule["rules"])

    # 將子規則的判定結果反轉，相當於「非」
    if operation == "not":
        return not evaluate_rule(record, rule["rule"])

    # 數字完全相等；比較前會先安全轉成整數
    if operation == "equals":
        return to_int(record.get(rule["field"])) == to_int(rule["value"])

    # 文字完全相等；忽略英文字母大小寫
    if operation == "text_equals":
        return normalize_text(record.get(rule["field"])) == normalize_text(rule["value"])

    # 文字值必須包含在指定清單中
    if operation == "text_in":
        value = normalize_text(record.get(rule["field"]))
        allowed = {normalize_text(item) for item in rule["values"]}
        return value is not None and value in allowed

    # 文字值不得包含在指定清單中
    if operation == "text_not_in":
        value = normalize_text(record.get(rule["field"]))
        excluded = {normalize_text(item) for item in rule["values"]}
        return value is not None and value not in excluded

    # 癌登代碼完全相等；會先移除小數點等非英數字元
    if operation == "code_in":
        value = normalize_code(record.get(rule["field"]))
        allowed = {normalize_code(item) for item in rule["values"]}
        return value is not None and value in allowed

    # 癌登代碼須以指定內容開頭，例如 C25 可涵蓋 C250～C259
    if operation == "code_prefix_in":
        value = normalize_code(record.get(rule["field"]))
        prefixes = [normalize_code(item) for item in rule["values"]]
        return value is not None and any(
            prefix is not None and value.startswith(prefix) for prefix in prefixes
        )

    # 比較兩個欄位的文字內容是否相同
    if operation == "fields_equal":
        left = normalize_text(record.get(rule["left_field"]))
        right = normalize_text(record.get(rule["right_field"]))
        return left is not None and right is not None and left == right

    # 比較兩個欄位解析後的日期是否相同
    if operation == "dates_equal":
        left = parse_date(record.get(rule["left_field"]))
        right = parse_date(record.get(rule["right_field"]))
        return left is not None and right is not None and left == right

    # 欄位第一個字元必須包含在指定清單中
    if operation == "first_char_in":
        value = normalize_text(record.get(rule["field"]))
        allowed = {normalize_text(item) for item in rule["values"]}
        return value is not None and value[0] in allowed

    # 數值必須介於最小值與最大值之間，包含上下限
    if operation == "between":
        value = to_int(record.get(rule["field"]))
        return value is not None and rule["min"] <= value <= rule["max"]

    # 數值必須大於指定門檻
    if operation == "greater_than":
        value = to_int(record.get(rule["field"]))
        return value is not None and value > rule["value"]

    # 數值必須大於或等於指定門檻
    if operation == "greater_than_or_equal":
        value = to_int(record.get(rule["field"]))
        return value is not None and value >= rule["value"]

    # 數值必須小於或等於指定門檻
    if operation == "less_than_or_equal":
        value = to_int(record.get(rule["field"]))
        return value is not None and value <= rule["value"]

    # 數值不得包含在指定清單中
    if operation == "not_in":
        value = to_int(record.get(rule["field"]))
        excluded = {to_int(item) for item in rule["values"]}
        return value is not None and value not in excluded

    # 欄位必須能解析成有效日期
    if operation == "valid_date":
        return parse_date(record.get(rule["field"])) is not None

    # 結束日期必須晚於開始日期，不包含同一天
    if operation == "date_after":
        start_date = parse_date(record.get(rule["start_field"]))
        end_date = parse_date(record.get(rule["end_field"]))
        return start_date is not None and end_date is not None and end_date > start_date

    # 結束日期必須等於或晚於開始日期，包含同一天
    if operation == "date_on_or_after":
        start_date = parse_date(record.get(rule["start_field"]))
        end_date = parse_date(record.get(rule["end_field"]))
        return start_date is not None and end_date is not None and end_date >= start_date

    # 日期年份必須落在指定起訖年度內
    if operation == "date_year_between":
        value = parse_date(record.get(rule["field"]))
        return value is not None and rule["min"] <= value.year <= rule["max"]

    # 開始與結束日期的間隔天數必須落在指定範圍內
    if operation == "date_interval":
        start_date = parse_date(record.get(rule["start_field"]))
        end_date = parse_date(record.get(rule["end_field"]))
        if start_date is None or end_date is None:
            return False
        days = (end_date - start_date).days
        return rule["min_days"] <= days <= rule["max_days"]

    # 從多個候選事件中選取參考日期之後最早的一天，再檢查間隔
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

    # 從多個開始日期中選最早者，再與結束日期計算間隔
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


def is_cancer_eligible(record: Record, cancer_type: str) -> bool:
    """先套用癌別層級收案規則；未設定基礎規則的既有癌別維持原行為。"""
    base_rule = CANCER_BASE_RULES.get(cancer_type)
    return base_rule is None or evaluate_rule(record, base_rule)


def is_cancer_candidate(record: Record, cancer_type: str) -> bool:
    """判斷年度內的癌別母體，個案分類留給共用排除流程統計。"""
    base_rule = CANCER_BASE_RULES.get(cancer_type)
    if base_rule is None:
        return True
    if base_rule.get("op") != "all":
        return evaluate_rule(record, base_rule)

    candidate_rule = {
        **base_rule,
        "rules": [
            rule
            for rule in base_rule.get("rules", [])
            if rule.get("field") != "case_classification"
        ],
    }
    return evaluate_rule(record, candidate_rule)


def evaluate_record(record: Record, cancer_type: str) -> dict[int, dict[str, Any]]:
    """依指定癌別，判斷單筆資料是否符合各指標的分母及分子。"""
    if cancer_type not in INDICATOR_RULES:
        available = ", ".join(INDICATOR_RULES)
        raise ValueError(f"不支援的癌別：{cancer_type!r}；可用癌別：{available}")

    results: dict[int, dict[str, Any]] = {}
    cancer_rules = INDICATOR_RULES[cancer_type]
    base_eligible = is_cancer_eligible(record, cancer_type)

    for indicator_number, indicator in cancer_rules.items():
        denominator = base_eligible and evaluate_rule(record, indicator["denominator"])
        numerator_rule = indicator.get("numerator")

        # None 表示目前規格尚未提供分子，不能擅自判定為 False。
        numerator = (
            None
            if numerator_rule is None
            else denominator and evaluate_rule(record, numerator_rule)
        )

        if not base_eligible:
            status = "不符合癌別收案條件"
        elif numerator is None:
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
