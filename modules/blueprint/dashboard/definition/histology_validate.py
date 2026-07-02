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

    if len(pattern) == 3:
        return site.startswith(pattern)

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

def validate_histology_rule(case_row, rule):
    # 驗證單筆個案是否符合某一條 1.3 組織型態規則

    site = case_row.get("site", "")
    didiag = case_row.get("didiag", "")

    if rule.get("site_include") and not site_match_any(site, rule["site_include"]):
        return False

    if rule.get("site_exclude") and site_match_any(site, rule["site_exclude"]):
        return False

    if ("year_min" in rule or "year_max" in rule) and not validate_year(didiag, rule):
        return False

    return True

def rule_specificity(rule):
    # 條件越多，代表規則越特殊，越優先使用
    special_fields = [
        "site_include",
        "site_exclude",
        "year_min",
        "year_max"
    ]

    return sum(1 for field in special_fields if field in rule)

def unknown_histology_result(icdo_code):
    # 找不到符合規則時，統一回傳 Unknown
    return {
        "icdo_code": icdo_code,
        "raw_name": "",
        "report_name": "Unknown / 未對應組織型態",
        "warning": "找不到符合的 1.3 組織型態規則"
    }

def match_histology(case_row, rules):
    # 根據 hist + behavior 找候選規則，再依照 site、didiag 判斷應該套用哪一條

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
        matched_rule["raw_name"] = raw_name
        matched_rules.append(matched_rule)

    if not matched_rules:
        return unknown_histology_result(icdo_code)

    # 多條符合時，選條件最明確的那條
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
