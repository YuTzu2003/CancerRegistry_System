import argparse
import re
import pandas as pd
import app
from dotenv import load_dotenv
from modules.blueprint.clean.field_mapping import field_mapping
from modules.services.db import get_conn
load_dotenv()

def normalize_code(value, width=0):
    if pd.isna(value):
        return ""
    try:
        return str(int(float(value))).zfill(width)
    except (TypeError, ValueError):
        return str(value).strip()

# 個案篩選
def filter_class(df, target_classes=["1", "2"]):
    return df[df["個案分類"].map(normalize_code).isin(target_classes)]

# AJCC分期
def ajcc_stages(cases, period_codes):
    stage_codes = period_codes[period_codes["label"].astype(str).str.strip().eq("AJCC(pstage/cstage)")]
    rows = []
    for index, case in cases.iterrows():
        pdescr = normalize_code(case["病理分期字根/字首"])
        dop_mds = normalize_code(case["原發部位最確切的手術切除日期"], width=8)
        if pdescr in {"4", "6"} or dop_mds == "00000000":
            selected_stage = case["臨床期別組合"]
        else:
            selected_stage = case["病理期別組合"]
        selected_stage = normalize_code(selected_stage)
        site = str(case["原發部位"]).strip().upper()
        row = {
            "row_index": index,
            "case": case.to_dict(),
            "ajcc_stage": selected_stage,
            "stage_value": None,
            "stage_detail": None,
            "stage_detail_hide": None,
            "ajcc_stage_category": None,
        }
        if selected_stage.replace(",", "") in {"999", "9999"}:
            row["ajcc_stage_category"] = "Stage Unknown"
        elif selected_stage.replace(",", "") in {"888", "8888"}:
            row["ajcc_stage_category"] = "Stage Not Applicable"
        else:
            site_codes = stage_codes[stage_codes["site"].astype(str).str.strip().str.upper().eq(site)]
            if site_codes.empty and re.fullmatch(r"C(?:0\d|[1-7]\d|80)\d", site):
                site_codes = stage_codes[
                    stage_codes["site"].astype(str).str.strip().str.upper().eq("C00-C80")
                ]
            matched_stage = site_codes[
                site_codes["stage_value"].map(normalize_code).eq(selected_stage)
            ]
            if not matched_stage.empty:
                stage = matched_stage.iloc[0]
                row["stage_value"] = stage["stage_value"]
                row["stage_detail"] = stage["stage_detail"]
                row["stage_detail_hide"] = stage["stage_detail_hide"]
        rows.append(row)

    unknown_count = sum(row["ajcc_stage_category"] == "Stage Unknown" for row in rows)
    not_applicable_count = sum(row["ajcc_stage_category"] == "Stage Not Applicable" for row in rows)
    return {
        "total_count": len(rows),
        "included_in_stage_statistics_count": len(rows) - unknown_count - not_applicable_count,
        "stage_unknown_count": unknown_count,
        "stage_not_applicable_count": not_applicable_count,
        "rows": rows,}

# FIGO分期
def figo_stages(cases, period_codes):
    rows = []
    for index, case in cases.iterrows():
        site = str(case["原發部位"]).strip().upper()[:3]
        if site not in {"C53", "C54", "C56"} or normalize_code(case["其他分期系統"], 2) != "01":
            continue

        ostagec = normalize_code(case["其他分期系統期別(臨床分期)"])
        if site == "C53" or normalize_code(case["其他分期系統期別(臨床分期)"], 4) != "0000":
            stage_value = ostagec
            label = "FIGO(ostagec)"
        else:
            stage_value = normalize_code(case["其他分期系統期別(病理分期)"])
            label = "FIGO(ostagep)"

        matched_stage = period_codes[
            period_codes["site"].astype(str).str.strip().str.upper().eq(site)
            & period_codes["ostage"].map(lambda value: normalize_code(value, 2)).eq("01")
            & period_codes["label"].astype(str).str.strip().eq(label)
            & period_codes["stage_value"].map(normalize_code).eq(stage_value)
        ]
        row = {
            "row_index": index,
            "case": case.to_dict(),
            "figo_stage": stage_value,
            "stage_value": None,
            "stage_detail": None,
            "stage_detail_hide": None,
        }
        if not matched_stage.empty:
            stage = matched_stage.iloc[0]
            row["stage_value"] = stage["stage_value"]
            row["stage_detail"] = stage["stage_detail"]
            row["stage_detail_hide"] = stage["stage_detail_hide"]
        rows.append(row)
    return {"total_count": len(rows), "rows": rows}

# MAC分期
def mac_stages(cases, period_codes):
    rows = []
    mac_codes = period_codes[
        period_codes["site"].astype(str).str.strip().eq("C18-C20")
        & period_codes["ostage"].map(lambda value: normalize_code(value, 2)).eq("02")
        & period_codes["label"].astype(str).str.strip().eq("MAC(ostagep)")
    ]

    for index, case in cases.iterrows():
        site = str(case["原發部位"]).strip().upper()[:3]
        if site not in {"C18", "C19", "C20"} or normalize_code(case["其他分期系統"], 2) != "02":
            continue

        stage_value = normalize_code(case["其他分期系統期別(病理分期)"])
        matched_stage = mac_codes[mac_codes["stage_value"].map(normalize_code).eq(stage_value)]
        row = {
            "row_index": index,
            "case": case.to_dict(),
            "mac_stage": stage_value,
            "stage_value": None,
            "stage_detail": None,
            "stage_detail_hide": None,
        }
        if not matched_stage.empty:
            stage = matched_stage.iloc[0]
            row["stage_value"] = stage["stage_value"]
            row["stage_detail"] = stage["stage_detail"]
            row["stage_detail_hide"] = stage["stage_detail_hide"]
        rows.append(row)
    return {"total_count": len(rows), "rows": rows}


def create_stage_results(cases, stage_codes, stage_name, is_applicable, select_stage):
    rows = []
    for index, case in cases.iterrows():
        if not is_applicable(case):
            continue
        stage_value = select_stage(case)
        matched_stage = stage_codes[stage_codes["stage_value"].map(normalize_code) == stage_value]
        row = {"row_index": index, "case": case.to_dict(), f"{stage_name}_stage": stage_value, "stage_value": None, "stage_detail": None, "stage_detail_hide": None}
        if not matched_stage.empty:
            row.update(matched_stage.iloc[0][["stage_value", "stage_detail", "stage_detail_hide"]])
        rows.append(row)
    return {"total_count": len(rows), "rows": rows}

# BCLC分期
def bclc_stages(cases, period_codes):
    stage_codes = period_codes[(period_codes["site"].astype(str).str.strip() == "C22") & (period_codes["label"] == "BCLC(ostagec)")]
    return create_stage_results(
        cases, stage_codes, "bclc",
        lambda case: str(case["原發部位"]).strip().upper()[:3] == "C22" and normalize_code(case["其他分期系統"], 2) == "06",
        lambda case: normalize_code(case["其他分期系統期別(臨床分期)"]),)

# SCLC分期
def sclc_stages(cases, period_codes):
    stage_codes = period_codes[(period_codes["site"].astype(str).str.strip() == "C33-C34") & (period_codes["label"] == "SCLC(ostagec)")]
    return create_stage_results(cases, stage_codes, "sclc", lambda case: str(case["原發部位"]).strip().upper()[:3] in {"C33", "C34"} and normalize_code(case["其他分期系統"], 2) == "07", lambda case: normalize_code(case["其他分期系統期別(臨床分期)"]))

# DSS分期
def dss_stages(cases, period_codes):
    stage_codes = period_codes[(period_codes["site"].astype(str).str.strip() == "C00-C80") & (period_codes["hist"].astype(str).str.strip() == "9731-9734") & (period_codes["label"] == "DSS(ostagec)")]
    return create_stage_results(cases, stage_codes, "dss", lambda case: bool(re.fullmatch(r"C(?:0\d|[1-7]\d|80)\d", str(case["原發部位"]).strip().upper())) and normalize_code(case["組織型態"]) in {"9731", "9732", "9733", "9734"} and normalize_code(case["其他分期系統"], 2) == "09", lambda case: normalize_code(case["其他分期系統期別(臨床分期)"]))

# DRE分期
def dre_stages(cases, period_codes):
    stage_codes = period_codes[(period_codes["site"].astype(str).str.strip() == "C619") & (period_codes["label"] == "DRE(ostagec)")]
    return create_stage_results(cases, stage_codes, "dre", lambda case: str(case["原發部位"]).strip().upper() == "C619" and normalize_code(case["其他分期系統"], 2) == "11", lambda case: normalize_code(case["其他分期系統期別(臨床分期)"]))

# Breast Cancer Prognostic Stage分期
def breast_stages(cases, period_codes):
    stage_codes = period_codes[(period_codes["site"].astype(str).str.strip() == "C50") & (period_codes["label"] == "Breast Cancer Prognostic Stage(ostagec/ostagec)")]
    def select_stage(case):
        stage_value = normalize_code(case["其他分期系統期別(病理分期)"])
        return normalize_code(case["其他分期系統期別(臨床分期)"]) if normalize_code(stage_value, 4) == "8888" else stage_value
    return create_stage_results(cases, stage_codes, "breast", lambda case: str(case["原發部位"]).strip().upper()[:3] == "C50" and normalize_code(case["其他分期系統"], 2) == "12", select_stage)

# Binet分期
def binet_stages(cases, period_codes):
    stage_codes = period_codes[(period_codes["site"].astype(str).str.strip() == "C00-C80") & (period_codes["hist"].astype(str).str.strip() == "9823") & (period_codes["label"] == "Binet(ostagec)")]
    return create_stage_results(cases, stage_codes, "binet", lambda case: bool(re.fullmatch(r"C(?:0\d|[1-7]\d|80)\d", str(case["原發部位"]).strip().upper())) and normalize_code(case["組織型態"]) == "9823" and normalize_code(case["其他分期系統"], 2) == "13", lambda case: normalize_code(case["其他分期系統期別(臨床分期)"]))


def main():
    parser = argparse.ArgumentParser(description="篩選個案分類後輸出分期")
    parser.add_argument("input_file")
    parser.add_argument("--stage-type", choices=["ajcc", "figo", "mac", "bclc", "sclc", "dss", "dre", "breast", "binet"], required=True)
    parser.add_argument("--sheet")
    parser.add_argument("--output")
    args = parser.parse_args()

    
    cases = filter_class(to_chinese_columns(pd.read_excel(args.input_file, sheet_name=args.sheet)))
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT site, hist, ostage, label, stage_value, stage_detail, stage_detail_hide "
            "FROM [Hospital_data].[dbo].[Period_Code]"
        )
        period_codes = pd.DataFrame.from_records(
            cursor.fetchall(), columns=[column[0] for column in cursor.description]
        )
    finally:
        conn.close()

    stage_function = {
        "ajcc": ajcc_stages, "figo": figo_stages, "mac": mac_stages,
        "bclc": bclc_stages, "sclc": sclc_stages, "dss": dss_stages,
        "dre": dre_stages, "breast": breast_stages, "binet": binet_stages,
    }[args.stage_type]
    result = stage_function(cases, period_codes)
    output = cases.iloc[0:0].copy()
    if result["rows"]:
        stage_result = pd.DataFrame(result["rows"]).set_index("row_index")
        output = cases.loc[stage_result.index].copy()
        output[f"{args.stage_type}_stage"] = stage_result[f"{args.stage_type}_stage"]
        output["stage_value"] = stage_result["stage_value"]
        output["stage_detail"] = stage_result["stage_detail"]
        output["stage_detail_hide"] = stage_result["stage_detail_hide"]
        if args.stage_type == "ajcc":
            output["ajcc_stage_category"] = stage_result["ajcc_stage_category"]
    else:
        output[f"{args.stage_type}_stage"] = None
        output["stage_value"] = None
        output["stage_detail"] = None
        output["stage_detail_hide"] = None

    output_path = args.output or f"{args.stage_type}_stages.xlsx"
    output.to_excel(output_path, index=False)
    print(f"{args.stage_type.upper()} COUNT：{result['total_count']}")

if __name__ == "__main__":
    main()