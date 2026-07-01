from .cancer_group_rules import CANCER_GROUP_RULES


def _normalize_code(value):
    if value is None:
        return ""
    return str(value).strip().upper().replace(".", "")


def _normalize_hist(value):
    code = _normalize_code(value)
    return code.zfill(4) if code.isdigit() else code


def _range_contains(value, rule):
    value = _normalize_hist(value)
    if not value.isdigit():
        return False

    number = int(value)
    rule_text = str(rule).strip()
    if "-" not in rule_text:
        return value == _normalize_hist(rule_text)

    start_text, end_text = [part.strip() for part in rule_text.split("-", 1)]
    if not start_text.isdigit() or not end_text.isdigit():
        return False

    return int(start_text) <= number <= int(end_text)


def _matches_any_range(value, rules):
    return any(_range_contains(value, rule) for rule in rules or [])


def _site_matches(site, prefixes):
    normalized_site = _normalize_code(site)
    return any(normalized_site.startswith(prefix.upper()) for prefix in prefixes or [])


def _match_subgroup(rule, site, hist):
    for subgroup in rule.get("subgroups", []):
        if subgroup.get("site_prefixes") and _site_matches(site, subgroup["site_prefixes"]):
            return subgroup
        if subgroup.get("hist_include") and _matches_any_range(hist, subgroup["hist_include"]):
            return subgroup
    return None


def classify_cancer_group(site, hist, rules=None):
    """
    Classify annual-report cancer group by site and histology.

    Current supported groups:
    - 結直腸癌: site C18/C19/C20, excluding hist 9140 and 9590-9993.
    - 肺癌: site C34, excluding hist 9140 and 9590-9993.
    """
    selected_rules = rules or CANCER_GROUP_RULES

    for rule in selected_rules:
        if not _site_matches(site, rule.get("site_prefixes")):
            continue

        if _matches_any_range(hist, rule.get("hist_exclude")):
            continue

        subgroup = _match_subgroup(rule, site, hist)
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
