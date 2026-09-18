"""年度組織型態代碼表的讀取與判定。

``histology_code_mapping`` 保留國健署各年度的原始對照資料；報表分析時，
會在分析年度起始年前兩年到結束年間，採用最新年度的對照名稱。
"""

from modules.services.db import get_conn


_COLUMN_ALIASES = {
    "code_year": ("CodeYear", "code_year", "年度"),
    "cancer_group_key": ("CancerGroupKey", "cancer_group_key"),
    "hist": ("HistCode", "hist", "組織型態(hist)"),
    "behavior": ("BehaviorCode", "behavior", "性態碼(behavior)"),
    "name_zh": ("HistologyZh", "hist_zh", "組織型態"),
    "name_en": ("HistologyEn", "hist_en", "behavior_en", "Histology"),
    "site_include": ("SiteInclude", "site_include"),
    "site_exclude": ("SiteExclude", "site_exclude"),
}


def _clean(value):
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "nat"}:
        return ""
    return text[:-2] if text.endswith(".0") else text


def normalize_code(value, width=0):
    text = _clean(value).upper()
    try:
        return str(int(float(text))).zfill(width)
    except (TypeError, ValueError):
        return text


def _available_columns(cursor):
    cursor.execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'histology_code_mapping'"
    )
    return {str(row[0]).lower(): str(row[0]) for row in cursor.fetchall()}


def _resolve_columns(columns):
    resolved = {}
    for canonical, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            found = columns.get(alias.lower())
            if found:
                resolved[canonical] = found
                break
    required = {"code_year", "cancer_group_key", "hist", "behavior", "name_zh", "name_en"}
    missing = required.difference(resolved)
    if missing:
        raise ValueError(f"histology_code_mapping 缺少必要欄位：{'、'.join(sorted(missing))}")
    return resolved


def get_histology_code_rules():
    """Read the annual code table without caching so yearly updates take effect immediately."""
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        resolved = _resolve_columns(_available_columns(cursor))
        canonical_fields = [
            "code_year", "cancer_group_key", "hist", "behavior", "name_zh", "name_en",
            "site_include", "site_exclude",
        ]
        select_fields = []
        for field in canonical_fields:
            column = resolved.get(field)
            if column:
                select_fields.append(f"[{column}] AS [{field}]")
            else:
                select_fields.append(f"NULL AS [{field}]")
        cursor.execute(f"SELECT {', '.join(select_fields)} FROM dbo.histology_code_mapping")
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as exc:
        print(f"從資料庫載入年度組織型態代碼表失敗: {exc}")
        return []
    finally:
        if conn:
            conn.close()


def _code_year_to_gregorian(value):
    try:
        year = int(float(_clean(value)))
    except (TypeError, ValueError):
        return None
    return year + 1911 if year < 1911 else year


def _site_matches(site, include, exclude):
    site = _clean(site).upper().replace(".", "")
    includes = [part.strip().upper().replace(".", "") for part in _clean(include).split(",") if part.strip()]
    excludes = [part.strip().upper().replace(".", "") for part in _clean(exclude).split(",") if part.strip()]
    if includes and not any(site.startswith(item) for item in includes):
        return False
    return not any(site.startswith(item) for item in excludes)


def _site_specificity(rule):
    return int(bool(_clean(rule.get("site_include")))) + int(bool(_clean(rule.get("site_exclude"))))


def _candidate_group_keys(cancer):
    if not cancer:
        return []
    return [
        key for key in (
            cancer.get("subgroup_key"),
            *cancer.get("ancestor_subgroup_keys", []),
            cancer.get("group_key"),
        ) if key
    ]


_SPECIAL_IN_SITU_NAMES = {
    # 附表 1.2：特殊原位癌應直接使用指定名稱，而非再加上「(原位癌)」。
    ("C50", "8500"): ("乳管原位癌", "DCIS"),
    ("C50", "8520"): ("小葉原位癌", "LCIS"),
    ("C53", "8077"): ("子宮頸上皮內高度病變", "CIN3 / HSIL"),
    ("C65-C68", "8120"): ("泌尿上皮癌原位癌", "Urothelial carcinoma, in situ"),
    ("C65-C68", "8130"): ("非侵襲性乳突狀癌", "Papillary urothelial carcinoma, non-invasive"),
    ("C44", "8081"): ("鮑恩病", "Bowen disease"),
}


def _site_in_range(site, start_prefix, end_prefix):
    """Match an ICD-O topography prefix range such as C65-C68."""
    normalized_site = _clean(site).upper().replace(".", "")
    if len(normalized_site) < 3 or not normalized_site.startswith("C"):
        return False
    prefix = normalized_site[:3]
    return start_prefix <= prefix <= end_prefix


def _special_in_situ_name(case, hist, behavior):
    if normalize_code(behavior) != "2":
        return None

    site = _clean(case.get("site")).upper().replace(".", "")
    hist_code = normalize_code(hist, 4)
    direct_name = _SPECIAL_IN_SITU_NAMES.get((site[:3], hist_code))
    if direct_name:
        return direct_name

    urinary_name = _SPECIAL_IN_SITU_NAMES.get(("C65-C68", hist_code))
    if urinary_name and _site_in_range(site, "C65", "C68"):
        return urinary_name

    # C44 的黑色素瘤原位癌為 8720 至 8790 的連續組織型態代碼。
    try:
        hist_number = int(hist_code)
    except ValueError:
        return None
    if site.startswith("C44") and 8720 <= hist_number <= 8790:
        return ("黑色素瘤原位癌", "Melanoma in situ")
    return None


def resolve_histology_code(case, cancer, rules, year_start="", year_end="", *, _allow_in_situ_fallback=True):
    """Return the display names selected from the annual code table.

    The latest available table year within the requested range (start year minus
    two years through end year) wins.  Same-year, same-condition conflicting
    names are returned as ambiguous rather than selected arbitrarily.
    """
    hist = normalize_code(case.get("hist"), 4)
    behavior = normalize_code(case.get("behavior"))
    # 附表 1.2 的特殊原位癌名稱，不依賴年度代碼表是否另列 /2 資料。
    special_name = _special_in_situ_name(case, hist, behavior)
    if special_name:
        return {
            "status": "matched",
            "icdo_code": f"{hist}/{behavior}",
            "name_zh": special_name[0],
            "name_en": special_name[1],
        }

    group_keys = _candidate_group_keys(cancer)
    if not group_keys:
        return {"status": "not_found", "icdo_code": f"{hist}/{behavior}"}

    try:
        start = int(year_start) - 2 if year_start else None
        end = int(year_end) if year_end else None
    except (TypeError, ValueError):
        start = end = None

    matches = []
    for rule in rules:
        if normalize_code(rule.get("hist"), 4) != hist or normalize_code(rule.get("behavior")) != behavior:
            continue
        rule_key = _clean(rule.get("cancer_group_key"))
        if rule_key not in group_keys:
            continue
        table_year = _code_year_to_gregorian(rule.get("code_year"))
        if table_year is None or (start is not None and table_year < start) or (end is not None and table_year > end):
            continue
        if not _site_matches(case.get("site"), rule.get("site_include"), rule.get("site_exclude")):
            continue
        matches.append((table_year, group_keys.index(rule_key), _site_specificity(rule), rule))

    if not matches and behavior == "2" and _allow_in_situ_fallback:
        # 多數代碼表只列惡性 /3 名稱；原位癌 /2 沿用相同 hist 的基礎名稱，
        # 再由呼叫端加上「(原位癌)」/ "(in situ)"，但維持 /2 為獨立統計項目。
        base_case = dict(case)
        base_case["behavior"] = "3"
        base_result = resolve_histology_code(
            base_case, cancer, rules, year_start, year_end,
            _allow_in_situ_fallback=False,
        )
        if base_result.get("status") == "matched":
            base_result["icdo_code"] = f"{hist}/{behavior}"
            base_result["used_in_situ_base_name"] = True
            return base_result

    if not matches:
        return {"status": "not_found", "icdo_code": f"{hist}/{behavior}"}

    latest_year = max(item[0] for item in matches)
    matches = [item for item in matches if item[0] == latest_year]
    best_group_rank = min(item[1] for item in matches)
    matches = [item for item in matches if item[1] == best_group_rank]
    best_specificity = max(item[2] for item in matches)
    matches = [item for item in matches if item[2] == best_specificity]

    names = {(_clean(item[3].get("name_zh")), _clean(item[3].get("name_en"))) for item in matches}
    if len(names) != 1:
        return {
            "status": "ambiguous",
            "icdo_code": f"{hist}/{behavior}",
            "code_year": latest_year - 1911 if latest_year >= 1911 else latest_year,
        }

    name_zh, name_en = names.pop()
    return {
        "status": "matched",
        "icdo_code": f"{hist}/{behavior}",
        "name_zh": name_zh,
        "name_en": name_en,
        "code_year": latest_year - 1911 if latest_year >= 1911 else latest_year,
    }


def is_blood_or_lymphoid(cancer):
    return bool(cancer and cancer.get("group_key") in {"Lymphoma", "Leukemia_and_myeloid_neoplasm"})


def blood_or_lymphoid_name(cancer):
    if not cancer:
        return "", ""
    return (
        cancer.get("subgroup_name") or cancer.get("group_name") or "",
        cancer.get("subgroup_name_en") or cancer.get("group_name_en") or "",
    )


def is_special_in_situ(case, hist, behavior):
    """Special names from appendix 1.2 that must not receive an in-situ suffix."""
    return _special_in_situ_name(case, hist, behavior) is not None


def should_append_in_situ(case, cancer, hist, behavior):
    if normalize_code(behavior) != "2" or is_blood_or_lymphoid(cancer):
        return False
    hist_number = normalize_code(hist, 4)
    try:
        numeric_hist = int(hist_number)
    except ValueError:
        return False
    return numeric_hist != 9140 and not 9590 <= numeric_hist <= 9993 and not is_special_in_situ(case, hist, behavior)
