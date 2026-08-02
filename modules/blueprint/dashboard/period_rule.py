import re
import pandas as pd
from modules.services.db import get_conn
def normalize_code(value, width=0):
    if pd.isna(value):
        return ""
    try:
        return str(int(float(value))).zfill(width)
    except (TypeError, ValueError):
        return str(value).strip()


def normalize_registry_date(value):
    """將癌登日期統一為 CCYYMMDD，包含 0000/00/00 等特殊日期格式。"""
    if pd.isna(value):
        return ""
    digits = re.sub(r"\D", "", str(value).strip())
    if not digits:
        return ""
    return digits[:8].zfill(8)


# 個案篩選
def filter_class(df, target_classes=("1", "2")):
    return df[df["個案分類"].map(normalize_code).isin(target_classes)]

# AJCC分期
def ajcc_stages(cases, period_codes):
    stage_codes = period_codes[period_codes["label"].astype(str).str.strip().eq("AJCC(pstage/cstage)")]
    rows = []
    for index, case in cases.iterrows():
        pdescr = normalize_code(case["病理分期字根/字首"])
        dop_mds = normalize_registry_date(case["原發部位最確切的手術切除日期"])
        pstage = normalize_code(case["病理期別組合"]).upper()
        selected_stage = (
            case["臨床期別組合"]
            if pdescr in {"4", "6"} or dop_mds == "00000000" or pstage == "BBB"
            else case["病理期別組合"]
        )
        selected_stage = normalize_code(selected_stage)
        site = str(case["原發部位"]).strip().upper()
        row = {"row_index": index, "case": case.to_dict(), "ajcc_stage": selected_stage,
               "stage_value": None, "stage_detail": None, "stage_detail_hide": None,
               "ajcc_stage_category": None}
        if selected_stage.replace(",", "") in {"999", "9999"}:
            row["ajcc_stage_category"] = "Stage Unknown"
        elif selected_stage.replace(",", "") in {"888", "8888"}:
            row["ajcc_stage_category"] = "Stage Not Applicable"
        else:
            site_codes = stage_codes[stage_codes["site"].astype(str).str.strip().str.upper().eq(site)]
            if site_codes.empty and re.fullmatch(r"C(?:0\d|[1-7]\d|80)\d", site):
                site_codes = stage_codes[stage_codes["site"].astype(str).str.strip().str.upper().eq("C00-C80")]
            matched_stage = site_codes[site_codes["stage_value"].map(normalize_code).eq(selected_stage)]
            if not matched_stage.empty:
                row.update(matched_stage.iloc[0][["stage_value", "stage_detail", "stage_detail_hide"]])
        rows.append(row)

    unknown_count = sum(row["ajcc_stage_category"] == "Stage Unknown" for row in rows)
    not_applicable_count = sum(row["ajcc_stage_category"] == "Stage Not Applicable" for row in rows)
    return {"total_count": len(rows), "included_in_stage_statistics_count": len(rows) - unknown_count - not_applicable_count,
            "stage_unknown_count": unknown_count, "stage_not_applicable_count": not_applicable_count, "rows": rows}

# FIGO分期
def figo_stages(cases, period_codes):
    rows = []
    for index, case in cases.iterrows():
        site = str(case["原發部位"]).strip().upper()[:3]
        # 2.4 FIGO 僅呈現女性個案：C53、C54、C56 且其他分期系統為 01。
        is_female = normalize_code(case["性別"]) == "2"
        if not is_female or site not in {"C53", "C54", "C56"} or normalize_code(case["其他分期系統"], 2) != "01":
            continue
        ostagec = normalize_code(case["其他分期系統期別(臨床分期)"])
        if site == "C53":
            stage_value, label = ostagec, "FIGO(ostagec)"
        else:
            # C54、C56 原則上採病理分期；臨床分期有值且不為 0000 時改採臨床值。
            # 無論選到哪個值，皆使用該癌別的 FIGO(ostagep) 碼表進行對照。
            ostagec_padded = normalize_code(case["其他分期系統期別(臨床分期)"], 4)
            stage_value = (
                ostagec
                if ostagec_padded not in {"", "0000"}
                else normalize_code(case["其他分期系統期別(病理分期)"])
            )
            label = "FIGO(ostagep)"
        matched_stage = period_codes[(period_codes["site"].astype(str).str.strip().str.upper().eq(site))
            & period_codes["ostage"].map(lambda value: normalize_code(value, 2)).eq("01")
            & period_codes["label"].astype(str).str.strip().eq(label)
            & period_codes["stage_value"].map(normalize_code).eq(stage_value)]
        row = {"row_index": index, "case": case.to_dict(), "figo_stage": stage_value,
               "stage_value": None, "stage_detail": None, "stage_detail_hide": None}
        if not matched_stage.empty:
            row.update(matched_stage.iloc[0][["stage_value", "stage_detail", "stage_detail_hide"]])
        rows.append(row)
    return {"total_count": len(rows), "rows": rows}

# MAC分期
def mac_stages(cases, period_codes):
    stage_codes = period_codes[(period_codes["site"].astype(str).str.strip().eq("C18-C20"))
        & period_codes["ostage"].map(lambda value: normalize_code(value, 2)).eq("02")
        & period_codes["label"].astype(str).str.strip().eq("MAC(ostagep)")]
    rows = []
    for index, case in cases.iterrows():
        site = str(case["原發部位"]).strip().upper()[:3]
        if site not in {"C18", "C19", "C20"} or normalize_code(case["其他分期系統"], 2) != "02":
            continue
        stage_value = normalize_code(case["其他分期系統期別(病理分期)"])
        matched_stage = stage_codes[stage_codes["stage_value"].map(normalize_code).eq(stage_value)]
        row = {"row_index": index, "case": case.to_dict(), "mac_stage": stage_value,
               "stage_value": None, "stage_detail": None, "stage_detail_hide": None}
        if not matched_stage.empty:
            row.update(matched_stage.iloc[0][["stage_value", "stage_detail", "stage_detail_hide"]])
        rows.append(row)
    return {"total_count": len(rows), "rows": rows}


def create_stage_results(cases, stage_codes, stage_name, is_applicable, select_stage):
    rows = []
    for index, case in cases.iterrows():
        if not is_applicable(case):
            continue
        stage_value = select_stage(case)
        matched_stage = stage_codes[stage_codes["stage_value"].map(normalize_code).eq(stage_value)]
        row = {"row_index": index, "case": case.to_dict(), f"{stage_name}_stage": stage_value,
               "stage_value": None, "stage_detail": None, "stage_detail_hide": None}
        if not matched_stage.empty:
            row.update(matched_stage.iloc[0][["stage_value", "stage_detail", "stage_detail_hide"]])
        rows.append(row)
    return {"total_count": len(rows), "rows": rows}

# BCLC分期
def bclc_stages(cases, period_codes):
    codes = period_codes[(period_codes["site"].astype(str).str.strip() == "C22") & (period_codes["label"] == "BCLC(ostagec)")]
    return create_stage_results(cases, codes, "bclc",
        lambda case: str(case["原發部位"]).strip().upper()[:3] == "C22" and normalize_code(case["其他分期系統"], 2) == "06",
        lambda case: normalize_code(case["其他分期系統期別(臨床分期)"]))


# SCLC分期
def sclc_stages(cases, period_codes):
    codes = period_codes[
        (period_codes["site"].astype(str).str.strip() == "C33-C34")
        & (period_codes["label"] == "SCLC(ostagec)")
    ]
    return create_stage_results(cases, codes, "sclc",
        lambda case: str(case["原發部位"]).strip().upper()[:3] in {"C33", "C34"} and normalize_code(case["其他分期系統"], 2) == "07",
        lambda case: normalize_code(case["其他分期系統期別(臨床分期)"]).upper())

# DSS分期
def dss_stages(cases, period_codes):
    codes = period_codes[(period_codes["site"].astype(str).str.strip() == "C00-C80") & (period_codes["hist"].astype(str).str.strip() == "9731-9734") & (period_codes["label"] == "DSS(ostagec)")]
    return create_stage_results(cases, codes, "dss",
        lambda case: bool(re.fullmatch(r"C(?:0\d|[1-7]\d|80)\d", str(case["原發部位"]).strip().upper())) and normalize_code(case["組織型態"]) in {"9731", "9732", "9733", "9734"} and normalize_code(case["其他分期系統"], 2) == "09",
        lambda case: normalize_code(case["其他分期系統期別(臨床分期)"]))

# DRE分期
def dre_stages(cases, period_codes):
    codes = period_codes[(period_codes["site"].astype(str).str.strip() == "C619") & (period_codes["label"] == "DRE(ostagec)")]
    return create_stage_results(cases, codes, "dre",
        # 2.4 DRE 僅呈現男性攝護腺個案。
        lambda case: normalize_code(case["性別"]) == "1"
            and str(case["原發部位"]).strip().upper() == "C619"
            and normalize_code(case["其他分期系統"], 2) == "11",
        lambda case: normalize_code(case["其他分期系統期別(臨床分期)"]))

# Breast Cancer Prognostic Stage分期
def breast_stages(cases, period_codes):
    codes = period_codes[
        (period_codes["site"].astype(str).str.strip() == "C50")
        & (
            period_codes["label"].astype(str).str.strip()
            == "Breast Cancer Prognostic Stage(ostagep/ostagec)"
        )
    ]
    def select_stage(case):
        stage_value = normalize_code(case["其他分期系統期別(病理分期)"])
        return normalize_code(case["其他分期系統期別(臨床分期)"]) if normalize_code(stage_value, 4) == "8888" else stage_value
    return create_stage_results(cases, codes, "breast",
        lambda case: str(case["原發部位"]).strip().upper()[:3] == "C50" and normalize_code(case["其他分期系統"], 2) == "12", select_stage)

# Binet分期
def binet_stages(cases, period_codes):
    codes = period_codes[(period_codes["site"].astype(str).str.strip() == "C00-C80") & (period_codes["hist"].astype(str).str.strip() == "9823") & (period_codes["label"] == "Binet(ostagec)")]
    return create_stage_results(cases, codes, "binet",
        lambda case: bool(re.fullmatch(r"C(?:0\d|[1-7]\d|80)\d", str(case["原發部位"]).strip().upper())) and normalize_code(case["組織型態"]) == "9823" and normalize_code(case["其他分期系統"], 2) == "13",
        lambda case: normalize_code(case["其他分期系統期別(臨床分期)"]))


STAGE_FUNCTIONS = {
    "AJCC": ajcc_stages, "FIGO": figo_stages, "MAC": mac_stages, "BCLC": bclc_stages,
    "SCLC": sclc_stages, "DSS": dss_stages, "DRE": dre_stages,
    "Breast Cancer Prognostic Stage": breast_stages, "Binet": binet_stages,
}

AGE_GROUPS = [
    ("≦19", None, 19), ("20-24", 20, 24), ("25-29", 25, 29),
    ("30-34", 30, 34), ("35-39", 35, 39), ("40-44", 40, 44),
    ("45-49", 45, 49), ("50-54", 50, 54), ("55-59", 55, 59),
    ("60-64", 60, 64), ("65-69", 65, 69), ("70-74", 70, 74),
    ("75-79", 75, 79), ("80-84", 80, 84), ("≧85", 85, None),
]


def _case_value(case, *field_names):
    """從已轉為中文欄名的個案資料中取得第一個存在的欄位值。"""
    for field_name in field_names:
        if field_name in case:
            return case.get(field_name)
    return None


def _sex_label(case):
    value = normalize_code(_case_value(case, "性別", "sex")).upper()
    if value in {"1", "M", "MALE", "男性", "男"}:
        return "男性"
    if value in {"2", "F", "FEMALE", "女性", "女"}:
        return "女性"
    return ""


def _age_group_label(case):
    value = _case_value(case, "診斷年齡", "年齡", "age")
    try:
        age = int(float(value))
    except (TypeError, ValueError):
        return ""
    for label, lower, upper in AGE_GROUPS:
        if (lower is None or age >= lower) and (upper is None or age <= upper):
            return label
    return ""


def _stage_report_label(row, detailed=False):
    """依模式使用 Period_Code 的最細碼或整併期別名稱。"""
    value = row.get("stage_detail" if detailed else "stage_detail_hide")
    if pd.isna(value):
        return ""
    label = str(value).strip()
    return "" if label.lower() in {"", "nan", "none"} else re.sub(r"^Stage\s+", "", label, flags=re.I)


def _raw_stage_code(row):
    for key, value in row.items():
        if key.endswith("_stage") and key not in {"stage_value", "stage_detail", "stage_detail_hide"}:
            return normalize_code(value).replace(",", "")
    return ""


def _stage_sort_key(label):
    order = {
        "0": 0, "I": 10, "II": 20, "III": 30, "IV": 40,
        "A": 50, "B": 60, "C": 70, "D": 80,
        "LIMITED": 90, "EXTENSIVE": 100,
    }
    text = str(label).strip()
    upper = text.upper()
    stage_match = re.match(r"^(0|IV|III|II|I|4|3|2|1)(.*)$", upper)
    if stage_match:
        stage_order = {
            "0": 0, "I": 10, "1": 10, "II": 20, "2": 20,
            "III": 30, "3": 30, "IV": 40, "4": 40,
        }
        return (stage_order[stage_match.group(1)], stage_match.group(2), text)
    dre_match = re.match(r"^T(X|0|1|2|3|4)(.*)$", upper)
    if dre_match:
        dre_order = {"X": 0, "0": 1, "1": 2, "2": 3, "3": 4, "4": 5}
        return (110 + dre_order[dre_match.group(1)], dre_match.group(2), text)
    if upper.startswith("LIMITED"):
        return (90, upper, text)
    if upper.startswith("EXTENSIVE"):
        return (100, upper, text)
    return (order.get(upper, 999), "", text)


def build_stage_report(stage_result, option):
    """把 2.4 分期結果整理成前端三種表圖共用的資料契約。"""
    rows = stage_result.get("rows", [])
    option_name = option.get("option") or option["system"]
    if "年齡層期別" in option_name:
        view = "age"
    elif "性別期別" in option_name:
        view = "sex"
    else:
        view = "stage"
    detailed = bool(option.get("detailed"))
    included_rows = []
    unknown_count = 0
    not_applicable_count = 0

    for row in rows:
        raw_code = _raw_stage_code(row)
        category = row.get("ajcc_stage_category")
        label = _stage_report_label(row, detailed)
        if category == "Stage Not Applicable" or raw_code in {"888", "8888"}:
            not_applicable_count += 1
        elif category == "Stage Unknown" or raw_code in {"999", "9999"} or not label:
            unknown_count += 1
        else:
            included_rows.append((row, label))

    stage_labels = sorted({label for _, label in included_rows}, key=_stage_sort_key)
    stage_index = {label: index for index, label in enumerate(stage_labels)}
    stage_totals = [0] * len(stage_labels)
    sex_values = {"男性": [0] * len(stage_labels), "女性": [0] * len(stage_labels)}
    age_values = {label: [0] * len(stage_labels) for label, _, _ in AGE_GROUPS}

    for row, label in included_rows:
        index = stage_index[label]
        stage_totals[index] += 1
        case = row.get("case") or {}
        sex = _sex_label(case)
        age_group = _age_group_label(case)
        if sex in sex_values:
            sex_values[sex][index] += 1
        if age_group in age_values:
            age_values[age_group][index] += 1

    chart_stage_labels = stage_labels
    chart_age_values = age_values
    if view == "age" and detailed:
        # 2.4 規定年齡層「圖」固定使用整併期別；表格仍依最細碼模式呈現。
        chart_rows = []
        for row in rows:
            raw_code = _raw_stage_code(row)
            category = row.get("ajcc_stage_category")
            label = _stage_report_label(row, detailed=False)
            if category in {"Stage Unknown", "Stage Not Applicable"}:
                continue
            if raw_code in {"888", "8888", "999", "9999"} or not label:
                continue
            chart_rows.append((row, label))
        chart_stage_labels = sorted({label for _, label in chart_rows}, key=_stage_sort_key)
        chart_stage_index = {label: index for index, label in enumerate(chart_stage_labels)}
        chart_age_values = {label: [0] * len(chart_stage_labels) for label, _, _ in AGE_GROUPS}
        for row, label in chart_rows:
            age_group = _age_group_label(row.get("case") or {})
            if age_group in chart_age_values:
                chart_age_values[age_group][chart_stage_index[label]] += 1

    return {
        "option": option_name,
        "view": view,
        "staging_system": option["system"],
        "detailed": detailed,
        "stage_labels": stage_labels,
        "stage_totals": stage_totals,
        # 2.4 性別期別規則：只呈現實際有個案的性別，總數為 0 的性別不列入表圖。
        "sex_rows": [
            {"sex": label, "values": values}
            for label, values in sex_values.items()
            if sum(values) > 0
        ],
        "age_rows": [{"age": label, "values": age_values[label]} for label, _, _ in AGE_GROUPS],
        "chart_stage_labels": chart_stage_labels,
        "chart_age_rows": [
            {"age": label, "values": chart_age_values[label]}
            for label, _, _ in AGE_GROUPS
        ],
        "analyzable_count": int(stage_result.get("total_count", len(rows))),
        "unknown_count": unknown_count,
        "not_applicable_count": not_applicable_count,
        "included_count": len(included_rows),
        "is_preview": False,
    }


def load_period_codes():
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT site, hist, ostage, label, stage_value, stage_detail, stage_detail_hide FROM [Hospital_data].[dbo].[Period_Code]")
        return pd.DataFrame.from_records(cursor.fetchall(), columns=[column[0] for column in cursor.description])
    finally:
        conn.close()


def calculate_stage_reports(cases, options, period_codes=None):
    """依勾選選項計算期別、性別期別及年齡層期別報表資料。"""
    cases = filter_class(cases)
    period_codes = load_period_codes() if period_codes is None else period_codes
    results_by_system = {}
    reports = []
    for option in options:
        system = option.get("system")
        if system not in STAGE_FUNCTIONS:
            continue
        if system not in results_by_system:
            results_by_system[system] = STAGE_FUNCTIONS[system](cases, period_codes)
        reports.append(build_stage_report(results_by_system[system], option))
    return reports


def calculate_stage_totals(cases, options, period_codes=None):
    reports = calculate_stage_reports(cases, options, period_codes)
    return [{"option": report["option"], "total_count": report["analyzable_count"]} for report in reports]


def _treatment_record(case):
    """Return treatment fields after CancerRegistry_FieldMap standardization.

    The dashboard prepares these canonical keys from the ``雲醫癌AI模組``
    mapping before stage/treatment analysis.  The Chinese registry headers
    remain a compatibility fallback for a directly uploaded registry file.
    In particular, ``DRET`` is never a fallback for ``drt_1st``.
    """
    def value(canonical_key, registry_header):
        if canonical_key in case:
            return case.get(canonical_key)
        return case.get(registry_header)

    return {
        "site": value("site", "原發部位"),
        "hist": value("hist", "組織型態"),
        "optype_o": value("optype_o", "外院原發部位手術方式"),
        "optype_h": value("optype_h", "申報醫院原發部位手術方式"),
        "drt_1st": value("drt_1st", "放射治療開始日期"),
        "rtstatus": value("rtstatus", "放射治療執行狀態"),
        "chem_o": value("chem_o", "外院化學治療"),
        "chem_h": value("chem_h", "申報醫院化學治療"),
        "horm_o": value("horm_o", "外院荷爾蒙/類固醇治療"),
        "horm_h": value("horm_h", "申報醫院荷爾蒙/類固醇治療"),
        "immu_o": value("immu_o", "外院免疫治療"),
        "immu_h": value("immu_h", "申報醫院免疫治療"),
        "htep_h": value("htep_h", "骨髓/幹細胞移植或內分泌處置"),
        "target_o": value("target_o", "外院標靶治療"),
        "target_h": value("target_h", "申報醫院標靶治療"),
        "other": value("other", "其他治療"),
        "dtrt_1st": value("dtrt_1st", "首次療程開始日期"),
    }


def _available_stage_labels(system, detailed, period_codes):
    """Return reportable Period_Code labels for an empty stage-treatment table."""
    label = period_codes["label"].astype(str).str.strip()
    label_matches = {
        "AJCC": label.eq("AJCC(pstage/cstage)"),
        "FIGO": label.str.startswith("FIGO("),
        "MAC": label.eq("MAC(ostagep)"),
        "BCLC": label.eq("BCLC(ostagec)"),
        "SCLC": label.eq("SCLC(ostagec)"),
        "DSS": label.eq("DSS(ostagec)"),
        "DRE": label.eq("DRE(ostagec)"),
        "Breast Cancer Prognostic Stage": label.str.startswith("Breast Cancer Prognostic Stage("),
        "Binet": label.eq("Binet(ostagec)"),
    }
    codes = period_codes.loc[label_matches.get(system, pd.Series(False, index=period_codes.index))]
    stage_column = "stage_detail" if detailed else "stage_detail_hide"
    labels = []
    for _, code in codes.iterrows():
        if normalize_code(code.get("stage_value")).replace(",", "") in {"888", "8888", "999", "9999"}:
            continue
        value = str(code.get(stage_column) or "").strip()
        if value:
            labels.append(value)
    return sorted(set(labels), key=_stage_sort_key)


def calculate_stage_first_course_distribution(cases, options, period_codes=None):
    """Create first-course-treatment crosstabs for the selected stage systems."""
    from modules.blueprint.dashboard.definition.treatment_rules import (
        classify_first_course_treatments,
    )

    cases = filter_class(cases)
    period_codes = load_period_codes() if period_codes is None else period_codes
    tables = []
    seen_systems = set()
    for option in options or []:
        system = option.get("system")
        if system not in STAGE_FUNCTIONS or system in seen_systems:
            continue
        seen_systems.add(system)
        detailed = option.get("detailed", False)
        stage_column = "stage_detail" if detailed else "stage_detail_hide"
        stage_result = STAGE_FUNCTIONS[system](cases, period_codes)
        counts = {}
        stage_columns = set()
        excluded_unknown = excluded_not_applicable = excluded_unmapped = 0
        excluded_unclassified_treatment = 0
        for row in stage_result.get("rows", []):
            raw_code = _raw_stage_code(row)
            category = row.get("ajcc_stage_category")
            if category == "Stage Not Applicable" or raw_code in {"888", "8888"}:
                excluded_not_applicable += 1
                continue
            stage = str(row.get(stage_column) or "").strip()
            if category == "Stage Unknown" or raw_code in {"999", "9999"} or not stage:
                # Keep the same convention as the stage distribution tables:
                # a blank Period_Code mapping is counted as an unknown stage.
                excluded_unknown += 1
                continue
            treatment = classify_first_course_treatments(_treatment_record(row["case"]))
            if not treatment:
                # A real first-course date without a recognized treatment code
                # is a data-quality exception, not a treatment category.
                excluded_unclassified_treatment += 1
                continue
            stage_columns.add(stage)
            counts.setdefault(treatment, {})[stage] = counts.setdefault(treatment, {}).get(stage, 0) + 1

        stage_columns = sorted(stage_columns, key=_stage_sort_key)
        if not stage_columns:
            stage_columns = _available_stage_labels(system, detailed, period_codes)
        treatment_rows = [
            {
                "treatment": treatment,
                "values": [int(values.get(stage, 0)) for stage in stage_columns],
                "subtotal": int(sum(values.values())),
            }
            for treatment, values in counts.items()
        ]
        treatment_rows.sort(key=lambda item: (-item["subtotal"], item["treatment"]))
        totals = [sum(row["values"][index] for row in treatment_rows) for index in range(len(stage_columns))]
        total_count = int(sum(totals))
        tables.append({
            "system": system,
            "stage_mode": "detailed" if detailed else "summary",
            "stage_columns": stage_columns,
            "rows": treatment_rows,
            "totals": totals,
            "total_count": total_count,
            "percentages": [round(value / total_count * 100, 1) if total_count else 0 for value in totals],
            "analyzable_count": int(stage_result.get("total_count", len(stage_result.get("rows", [])))),
            "included_count": total_count,
            "excluded_unknown": excluded_unknown,
            "excluded_not_applicable": excluded_not_applicable,
            "excluded_unmapped": excluded_unmapped,
            "excluded_unclassified_treatment": excluded_unclassified_treatment,
        })
    return tables
