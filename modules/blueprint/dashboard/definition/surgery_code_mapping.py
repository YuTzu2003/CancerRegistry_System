"""讀取附錄 B 手術術式對照，並依 ``SurgeryRank`` 選擇個案的最高階術式。"""

import re

from modules.services.db import get_conn


def _clean(value):
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "nat"}:
        return ""
    return text[:-2] if text.endswith(".0") else text


def normalize_surgery_code(value):
    """Normalize numeric and alpha-numeric registry operation codes."""
    text = _clean(value).upper()
    # Do not pass alpha-numeric Appendix-B codes such as ``2E0`` through
    # ``float``: Python interprets it as scientific notation (2e0 -> 2).
    if not re.fullmatch(r"\d+(?:\.0+)?", text):
        return text
    try:
        return str(int(float(text)))
    except (TypeError, ValueError):
        return text


def surgery_code_variants(value):
    """Return every source code represented by one stored mapping value.

    Appendix-B entries may use a numeric range, alternative newer codes, or
    alpha-numeric values such as ``2M/2M0`` in one displayed row.  Preserve
    that human-readable value in the database but expand it for matching.
    """
    text = _clean(value).upper()
    if not text:
        return set()

    variants = set()
    for part in re.split(r"[|/,]+", text):
        part = part.strip()
        range_match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
        if range_match:
            start, end = (int(item) for item in range_match.groups())
            if start <= end and end - start <= 99:
                variants.update(str(code) for code in range(start, end + 1))
                continue
        code = normalize_surgery_code(part)
        if code:
            variants.add(code)
    return variants


def get_surgery_code_rules(manual_key):
    """Return all rows for one appendix-B manual, in display order."""
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT [SurgeryManualKey], [RowKey], [ParentRowKey], [CodeShort], "
            "[CodeLong], [DisplayText_en], [RowType], [DisplayOrder], [SurgeryRank], [DisplayLevel] "
            "FROM dbo.Surgery_code_mapping WHERE [SurgeryManualKey] = ? "
            "ORDER BY [DisplayOrder]",
            manual_key,
        )
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as exc:
        print(f"從資料庫載入手術術式對照表失敗: {exc}")
        return []
    finally:
        if conn:
            conn.close()


def select_highest_ranked_surgery(optype_o, optype_h, rules):
    """Match both source codes and return the row with the greatest SurgeryRank.

    A tie is deterministic: the reported-hospital code (``optype_h``) wins.
    """
    candidates = []
    for source_priority, value in enumerate((optype_o, optype_h)):
        code = normalize_surgery_code(value)
        if not code:
            continue
        for rule in rules:
            if str(rule.get("RowType") or "").lower() != "code":
                continue
            rule_codes = (
                surgery_code_variants(rule.get("CodeShort"))
                | surgery_code_variants(rule.get("CodeLong"))
            )
            if code in rule_codes:
                try:
                    rank = float(rule.get("SurgeryRank"))
                except (TypeError, ValueError):
                    continue
                candidates.append((rank, source_priority, rule))
                break
    return max(candidates, key=lambda item: (item[0], item[1]))[2] if candidates else None


def format_surgery_code(value, width):
    """Format numeric codes with their appendix-B leading zeros intact."""
    code = normalize_surgery_code(value)
    return code.zfill(width) if code.isdigit() else code


def surgery_display_name(rule):
    """Return the display name without the code prefix repeated in the table."""
    short_code = format_surgery_code(rule.get("CodeShort"), 2)
    long_code = format_surgery_code(rule.get("CodeLong"), 3)
    text = str(rule.get("DisplayText_en") or "").strip()
    code = f"{short_code}/{long_code}" if short_code and long_code else short_code or long_code
    if code:
        text = re.sub(rf"^{re.escape(code)}\s*", "", text)
    return text

# Some dashboard cancer selections are analytic subtypes that share one
# appendix-B surgical manual with their site-level parent cancer.
SURGERY_MANUAL_KEY_ALIASES = {
    "oropharynx_p16_positive": "Oropharynx",
    "oropharynx_p16_negative": "Oropharynx",
    "Small_cell_carcinoma": "Lung",
    "Adenocarcinoma": "Lung",
    "Squamous_cell_carcinoma": "Lung",
    "Lung_and_Bronchus": "Lung",
    "Cervix_cin3_in_situ": "Cervix_Uteri",
    "Cervix_invasive": "Cervix_Uteri",
    "Bladder_in_situ": "Bladder",
    "Bladder_invasive": "Bladder",
    "Breast_Female": "Breast",
    "Breast_Male": "Breast",
    "Breast_in_situ": "Breast",
    "Breast_invasive": "Breast",
}


def resolve_surgery_manual_key(cancer_key):
    """Resolve an analytic cancer subtype to its appendix-B manual key."""
    key = str(cancer_key or "").strip()
    return SURGERY_MANUAL_KEY_ALIASES.get(key, key)

SURGERY_MANUAL_LABEL_OVERRIDES = {
    "Lung": ("肺癌", "Lung"),
}

def get_surgery_manual_labels(manual_key):
    """Return the Chinese and English site label for an appendix-B manual."""
    from modules.blueprint.dashboard.definition.cancer_group_rules import CANCER_GROUP_RULES

    key = str(manual_key or "").strip()
    if key in SURGERY_MANUAL_LABEL_OVERRIDES:
        return SURGERY_MANUAL_LABEL_OVERRIDES[key]
    for rule in CANCER_GROUP_RULES:
        if rule.get("key") == key:
            return rule.get("name_zh") or key, rule.get("name_en") or key
        for subgroup in rule.get("subgroups") or []:
            if subgroup.get("key") == key:
                return subgroup.get("name_zh") or key, subgroup.get("name_en") or key
    return key, key
