from .cancer_group_rules import CANCER_GROUP_RULES


def _normalize_code(value):
    if value is None:
        return ""
    return str(value).strip().upper().replace(".", "")

def _normalize_hist(value):
    code = _normalize_code(value)
    if code.isdigit() and len(code) < 4:
        return code.zfill(4)
    return code

def _normalize_behavior(value):
    code = _normalize_code(value)
    if code.endswith(".0"):
        code = code[:-2]
    return code[:1]

def _extract_year(value):
    text = _normalize_code(value)
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) < 4:
        return None
    try:
        return int(digits[:4])
    except ValueError:
        return None

def _range_contains(value, rule):
    value = _normalize_hist(value)
    if not value.isdigit():
        return False

    number = int(value)
    rule_text = _normalize_hist(rule)
    if "-" not in rule_text:
        return value == rule_text

    start_text, end_text = [part.strip() for part in rule_text.split("-", 1)]
    start_text = _normalize_hist(start_text)
    end_text = _normalize_hist(end_text)
    if not start_text.isdigit() or not end_text.isdigit():
        return False

    return int(start_text) <= number <= int(end_text)

def _matches_any_range(value, rules):
    return any(_range_contains(value, rule) for rule in rules or [])

def _site_matches_any(site, prefixes):
    normalized_site = _normalize_code(site)
    return any(normalized_site.startswith(_normalize_code(prefix)) for prefix in prefixes or [])

def _site_matches(site, include_prefixes=None, exclude_prefixes=None):
    if include_prefixes and not _site_matches_any(site, include_prefixes):
        return False
    if exclude_prefixes and _site_matches_any(site, exclude_prefixes):
        return False
    return True

def _value_in(value, allowed_values):
    normalized_value = _normalize_code(value)
    return any(normalized_value == _normalize_code(item) for item in allowed_values or [])

def _matches_field_equals(context, field_rules):
    for field_name, allowed_values in (field_rules or {}).items():
        if not _value_in(context.get(field_name), allowed_values):
            return False
    return True

def _matches_rule(rule, site, hist, context):
    if not _site_matches(site, rule.get("site_prefixes"), rule.get("site_exclude")):
        return False

    hist_include = rule.get("hist_include")
    if hist_include and not _matches_any_range(hist, hist_include):
        return False

    if _matches_any_range(hist, rule.get("hist_exclude")):
        return False

    behavior_include = rule.get("behavior_include")
    if behavior_include and _normalize_behavior(context.get("behavior")) not in {_normalize_behavior(v) for v in behavior_include}:
        return False

    min_year = rule.get("min_didiag_year")
    if min_year is not None:
        year = _extract_year(context.get("didiag"))
        if year is None or year < int(min_year):
            return False

    return _matches_field_equals(context, rule.get("field_equals"))

def _match_subgroup(rule, site, hist, context):
    for subgroup in rule.get("subgroups", []):
        if _matches_rule(subgroup, site, hist, context):
            return subgroup
    return None

def classify_cancer_group(site, hist, rules=None, behavior=None, didiag=None, ajcc_ed=None, **extra_fields):
    
    selected_rules = rules or CANCER_GROUP_RULES
    context = {
        "behavior": behavior,
        "didiag": didiag,
        "ajcc_ed": ajcc_ed,
        **extra_fields,
    }

    for rule in selected_rules:
        if not _matches_rule(rule, site, hist, context):
            continue

        subgroup = _match_subgroup(rule, site, hist, context)
        if rule.get("requires_subgroup_match") and not subgroup:
            continue

        result = {
            "group_key": rule["key"],
            "group_name": rule["name_zh"],
            "group_name_en": rule.get("name_en", ""),
            "subgroup_key": None,
            "subgroup_name": None,
            "subgroup_name_en": None,
        }

        if subgroup:
            result.update(
                {
                    "subgroup_key": subgroup["key"],
                    "subgroup_name": subgroup["name_zh"],
                    "subgroup_name_en": subgroup.get("name_en", ""),
                }
            )

        return result

    return None
