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

# 個案篩選
def filter_class(df, target_classes=("1", "2")):
    return df[df["個案分類"].map(normalize_code).isin(target_classes)]

# AJCC分期
def ajcc_stages(cases, period_codes):
    stage_codes = period_codes[period_codes["label"].astype(str).str.strip().eq("AJCC(pstage/cstage)")]
    rows = []
    for index, case in cases.iterrows():
        pdescr = normalize_code(case["病理分期字根/字首"])
        dop_mds = normalize_code(case["原發部位最確切的手術切除日期"], 8)
        selected_stage = case["臨床期別組合"] if pdescr in {"4", "6"} or dop_mds == "00000000" else case["病理期別組合"]
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
        if site not in {"C53", "C54", "C56"} or normalize_code(case["其他分期系統"], 2) != "01":
            continue
        ostagec = normalize_code(case["其他分期系統期別(臨床分期)"])
        if site == "C53" or normalize_code(case["其他分期系統期別(臨床分期)"], 4) != "0000":
            stage_value, label = ostagec, "FIGO(ostagec)"
        else:
            stage_value, label = normalize_code(case["其他分期系統期別(病理分期)"]), "FIGO(ostagep)"
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
    codes = period_codes[(period_codes["site"].astype(str).str.strip() == "C33-C34") & (period_codes["label"] == "SCLC(ostagec)")]
    return create_stage_results(cases, codes, "sclc",
        lambda case: str(case["原發部位"]).strip().upper()[:3] in {"C33", "C34"} and normalize_code(case["其他分期系統"], 2) == "07",
        lambda case: normalize_code(case["其他分期系統期別(臨床分期)"]))

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
        lambda case: str(case["原發部位"]).strip().upper() == "C619" and normalize_code(case["其他分期系統"], 2) == "11",
        lambda case: normalize_code(case["其他分期系統期別(臨床分期)"]))

# Breast Cancer Prognostic Stage分期
def breast_stages(cases, period_codes):
    codes = period_codes[(period_codes["site"].astype(str).str.strip() == "C50") & (period_codes["label"] == "Breast Cancer Prognostic Stage(ostagec/ostagec)")]
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


def load_period_codes():
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT site, hist, ostage, label, stage_value, stage_detail, stage_detail_hide FROM [Hospital_data].[dbo].[Period_Code]")
        return pd.DataFrame.from_records(cursor.fetchall(), columns=[column[0] for column in cursor.description])
    finally:
        conn.close()


# test
def calculate_stage_totals(cases, options):
    cases = filter_class(cases)
    period_codes = load_period_codes()
    return [
        {"option": option.get("option") or option["system"], "total_count": STAGE_FUNCTIONS[option["system"]](cases, period_codes)["total_count"]}
        for option in options if option.get("system") in STAGE_FUNCTIONS]


def _treatment_record(case):
    """Convert the dashboard's Chinese canonical fields to treatment-rule keys."""
    def value(*keys):
        for key in keys:
            if key in case:
                return case.get(key)
        return None

    return {
        "site": value("site", "原發部位"),
        "hist": value("hist", "組織型態"),
        "optype_o": value("optype_o", "外院原發部位手術方式"),
        "optype_h": value("optype_h", "申報醫院原發部位手術方式"),
        "drt_1st": value("drt_1st", "DRET"),
        "rtstatus": value("rtstatus", "放射治療執行狀態"),
        "chem_o": value("chem_o", "外院化學治療"),
        "chem_h": value("chem_h", "申報醫院化學治療"),
        "horm_o": value("horm_o", "外院荷爾蒙/類固醇治療"),
        "horm_h": value("horm_h", "申報醫院荷爾蒙/類固醇治療"),
        "immu_o": value("immu_o", "外院免疫治療"),
        "immu_h": value("immu_h", "申報醫院免疫治療"),
        "htep_h": value("htep_h", "申報醫院骨髓/幹細胞移植或內分泌處置"),
        "target_o": value("target_o", "外院標靶治療"),
        "target_h": value("target_h", "申報醫院標靶治療"),
        "other": value("other", "其他治療"),
        "dtrt_1st": value("dtrt_1st", "DTRT_1ST"),
    }


def _stage_sort_key(label):
    """Keep common numeric/Roman stages in their clinical display order."""
    text = str(label or "").strip()
    roman = {"0": 0, "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}
    match = re.search(r"(?:Stage\s*)?(0|IV|III|II|I|V)", text, flags=re.I)
    if match:
        return (0, roman.get(match.group(1).upper(), 99), text)
    return (1, text)


def calculate_stage_first_course_distribution(cases, options):
    """Create the dynamic stage × first-course-treatment crosstab(s).

    ``options`` accepts the selected stage systems and a ``stage_mode`` of
    ``detailed`` or ``summary``.  Unknown / not-applicable stages and records
    without a Period_Code match are not included in the crosstab; their counts
    are returned for the note under the table.
    """
    from modules.blueprint.dashboard.definition.treatment_rules import (
        classify_first_course_treatments,
    )

    cases = filter_class(cases)
    period_codes = load_period_codes()
    tables = []
    seen_systems = set()

    for option in options or []:
        system = option.get("system")
        if system not in STAGE_FUNCTIONS or system in seen_systems:
            continue
        seen_systems.add(system)
        stage_mode = option.get("stage_mode", "summary")
        stage_column = "stage_detail" if stage_mode == "detailed" else "stage_detail_hide"
        stage_result = STAGE_FUNCTIONS[system](cases, period_codes)

        counts = {}
        stage_columns = set()
        excluded_unknown = 0
        excluded_not_applicable = 0
        excluded_unmapped = 0

        for row in stage_result.get("rows", []):
            category = row.get("ajcc_stage_category")
            if category == "Stage Unknown":
                excluded_unknown += 1
                continue
            if category == "Stage Not Applicable":
                excluded_not_applicable += 1
                continue
            stage = str(row.get(stage_column) or "").strip()
            if not stage:
                excluded_unmapped += 1
                continue

            treatment = classify_first_course_treatments(_treatment_record(row["case"]))
            treatment = treatment or "未記錄治療"
            stage_columns.add(stage)
            counts.setdefault(treatment, {})[stage] = counts.setdefault(treatment, {}).get(stage, 0) + 1

        stage_columns = sorted(stage_columns, key=_stage_sort_key)
        treatment_rows = []
        for treatment, values in counts.items():
            treatment_rows.append({
                "treatment": treatment,
                "values": [int(values.get(stage, 0)) for stage in stage_columns],
                "subtotal": int(sum(values.values())),
            })
        treatment_rows.sort(key=lambda item: (-item["subtotal"], item["treatment"]))

        totals = [sum(row["values"][index] for row in treatment_rows) for index in range(len(stage_columns))]
        total_count = int(sum(totals))
        tables.append({
            "system": system,
            "stage_mode": stage_mode,
            "stage_columns": stage_columns,
            "rows": treatment_rows,
            "totals": totals,
            "total_count": total_count,
            "percentages": [round(value / total_count * 100, 1) if total_count else 0 for value in totals],
            "excluded_unknown": excluded_unknown,
            "excluded_not_applicable": excluded_not_applicable,
            "excluded_unmapped": excluded_unmapped,
        })
    return tables
