import pandas as pd

def is_blank(value):
    return pd.isna(value)

def clean_value(value):
    if is_blank(value):
        return ""
    return str(value).strip()

def normalize_code(value):
    try:
        return str(int(float(clean_value(value))))
    except (ValueError, TypeError):
        return clean_value(value)

def normalize_site_for_compare(value):
    return clean_value(value).upper().replace(".", "")

def to_list(value):
    if not value:
        return []

    if isinstance(value, str):
        return [item.strip() for item in value.split(",")]

    return value

def site_match(site, pattern):
    site = normalize_site_for_compare(site)
    pattern = normalize_site_for_compare(pattern)

    # C25、C34 這種三碼，代表底下全部部位都符合
    if len(pattern) == 3:
        return site.startswith(pattern)

    # C649、C220 這種四碼，代表只符合指定部位
    return site == pattern

def site_match_any(site, patterns):
    return any(site_match(site, pattern) for pattern in to_list(patterns))

def validate_year(value, rule):
    year_text = normalize_code(value)

    if len(year_text) >= 4 and year_text[:4].isdigit():
        year = int(year_text[:4])
    else:
        return False

    # year_min：診斷年份下限，例如 2018 代表年份需 >= 2018
    if "year_min" in rule and year < int(rule["year_min"]):
        return False

    # year_max：診斷年份上限，例如 2017 代表年份需 <= 2017
    if "year_max" in rule and year > int(rule["year_max"]):
        return False

    return True

# 驗證單一組特殊條件，例如：site_include、site_exclude、year_min、year_max
def validate_single_condition(case_row, condition):

    site = case_row.get("site", "")
    didiag = case_row.get("didiag", "")

    if condition.get("site_include") and not site_match_any(site, condition["site_include"]):
        return False

    if condition.get("site_exclude") and site_match_any(site, condition["site_exclude"]):
        return False

    if ("year_min" in condition or "year_max" in condition) and not validate_year(didiag, condition):
        return False

    return True

# 如果一筆定義有 conditions，代表裡面是多組 OR 條件，只要其中一組條件符合，這筆組織型態規則就算符合
def validate_histology_rule(case_row, rule):

    conditions = rule.get("conditions")

    if conditions:
        return any(validate_single_condition(case_row, condition) for condition in conditions)

    # 沒有 conditions 時，就直接用 rule 本身的特殊設定判斷
    return validate_single_condition(case_row, rule)


def rule_specificity(rule):
    special_fields = [
        "site_include",
        "site_exclude",
        "year_min",
        "year_max"
    ]

    conditions = rule.get("conditions")

    if conditions:
        return max(
            sum(1 for field in special_fields if field in condition)
            for condition in conditions
        )

    return sum(1 for field in special_fields if field in rule)

def format_list_text(values):
    items = [str(item).strip() for item in to_list(values) if str(item).strip()]
    return "、".join(items)


def format_year_condition(condition):
    year_min = condition.get("year_min")
    year_max = condition.get("year_max")

    if year_min is not None and year_max is not None:
        if int(year_min) == int(year_max):
            return f"診斷年度為 {int(year_min)} 年"
        return f"診斷年度為 {int(year_min)} 年至 {int(year_max)} 年"
    if year_min is not None:
        return f"診斷年度為 {int(year_min)} 年以後"
    if year_max is not None:
        return f"診斷年度為 {int(year_max)} 年以前"
    return ""


def format_condition_text(condition):
    parts = []
    year_text = format_year_condition(condition)
    if year_text:
        parts.append(year_text)

    site_include = format_list_text(condition.get("site_include"))
    if site_include:
        parts.append(f"原發部位為 {site_include}")

    site_exclude = format_list_text(condition.get("site_exclude"))
    if site_exclude:
        parts.append(f"原發部位不可為 {site_exclude}")

    return "，且".join(parts)


def rule_condition_text(rule):
    conditions = rule.get("conditions") or [rule]
    texts = [format_condition_text(condition) for condition in conditions]
    texts = [text for text in texts if text]
    if not texts:
        return ""
    return "；或".join(texts)



def _condition_failed_fields(case_row, condition):
    failed = []
    site = case_row.get("site", "")
    didiag = case_row.get("didiag", "")

    site_failed = False
    if condition.get("site_include") and not site_match_any(site, condition["site_include"]):
        site_failed = True
    if condition.get("site_exclude") and site_match_any(site, condition["site_exclude"]):
        site_failed = True
    if site_failed:
        failed.append("site")

    if ("year_min" in condition or "year_max" in condition) and not validate_year(didiag, condition):
        failed.append("year")

    return failed


def mismatch_fields_for_candidate_rules(case_row, candidate_rules):
    failed_options = []
    for rule in candidate_rules or []:
        conditions = rule.get("conditions") or [rule]
        for condition in conditions:
            failed = _condition_failed_fields(case_row, condition)
            if failed:
                failed_options.append(failed)

    if not failed_options:
        return []

    best = min(failed_options, key=len)
    ordered = []
    for key in ("year", "site"):
        if key in best:
            ordered.append(key)
    return ordered

def unknown_histology_result(icdo_code, candidate_rules=None, case_row=None):
    candidate_rules = candidate_rules or []
    detail_texts = []
    for rule in candidate_rules:
        text = rule_condition_text(rule)
        if text and text not in detail_texts:
            detail_texts.append(text)

    if detail_texts:
        condition_text = "；或".join(detail_texts)
        mismatch_fields = mismatch_fields_for_candidate_rules(case_row or {}, candidate_rules)
        return {
            "mismatch_fields": mismatch_fields,
            "mismatch_fields": mismatch_fields,
            "icdo_code": icdo_code,
            "raw_name": "",
            "report_name": "Unknown / 未對應組織型態",
            "warning": "組織型態與適用年度或原發部位不符",
            "warning_type": "condition_mismatch",
            "message": f"{icdo_code} 不適用於此個案，組織型態與適用年度或原發部位不符，請再確認。",
            "detail_message": f"此組織型態有特殊適用條件，僅適用於{condition_text}的個案。"
        }

    return {
        "icdo_code": icdo_code,
        "raw_name": "",
        "report_name": "Unknown / 未對應組織型態",
        "warning": "找不到符合的 1.3 組織型態規則",
        "warning_type": "not_in_mapping",
        "message": f"{icdo_code} 未納入 1.3 組織型態規則。",
        "detail_message": "若此組織型態無特殊適用條件，則此組織代碼組合不屬於目前統計規則範圍。"
    }


def match_histology(case_row, rules):
    hist = normalize_code(case_row.get("hist", ""))
    behavior = normalize_code(case_row.get("behavior", ""))
    icdo_code = f"{hist}/{behavior}"

    matched_rules = []
    candidate_rules = []

    for rule in rules:
        rule_hist = normalize_code(rule.get("hist", ""))
        rule_behavior = normalize_code(rule.get("behavior", ""))

        if rule_hist != hist or rule_behavior != behavior:
            continue

        candidate_rules.append(rule)

        if not validate_histology_rule(case_row, rule):
            continue

        matched_rule = dict(rule)
        matched_rule["raw_name"] = rule.get("raw_name", "")
        matched_rules.append(matched_rule)

    if not matched_rules:
        return unknown_histology_result(icdo_code, candidate_rules, case_row)

    matched_rules = sorted(
        matched_rules,
        key=rule_specificity,
        reverse=True
    )

    best_rule = matched_rules[0]

    return {
        "icdo_code": icdo_code,
        "raw_name": best_rule.get("raw_name", ""),
        "report_name": best_rule.get("report_name", ""),
        "warning": ""
    }
