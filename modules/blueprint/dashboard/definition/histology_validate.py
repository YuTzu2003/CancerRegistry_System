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

def unknown_histology_result(icdo_code):
    return {
        "icdo_code": icdo_code,
        "raw_name": "",
        "report_name": "Unknown / 未對應組織型態",
        "warning": "找不到符合的 1.3 組織型態規則"
    }

def match_histology(case_row, rules):
    hist = normalize_code(case_row.get("hist", ""))
    behavior = normalize_code(case_row.get("behavior", ""))
    icdo_code = f"{hist}/{behavior}"

    matched_rules = []

    for raw_name, rule in rules.items():
        rule_hist = normalize_code(rule.get("hist", ""))
        rule_behavior = normalize_code(rule.get("behavior", ""))

        if rule_hist != hist or rule_behavior != behavior:
            continue

        if not validate_histology_rule(case_row, rule):
            continue

        matched_rule = dict(rule)
        matched_rule["raw_name"] = rule.get("raw_name", raw_name)
        matched_rules.append(matched_rule)

    if not matched_rules:
        return unknown_histology_result(icdo_code)

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
