import os
import pandas as pd
import logging
from functools import lru_cache
from modules.blueprint.dashboard.definition.cancer_grouping import classify_cancer_group
from modules.blueprint.dashboard.definition.cancer_group_rules import CANCER_GROUP_RULES
from modules.blueprint.dashboard.definition.histology_code_mapping import (
    blood_or_lymphoid_name,
    get_histology_code_rules,
    is_blood_or_lymphoid,
    resolve_histology_code,
    should_append_in_situ,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DASHBOARD_DATA = f"{BASE_DIR}/tasks/data"

def _safe_dashboard_path(filename):
    relative_path = str(filename or "")
    fpath = os.path.abspath(os.path.join(DASHBOARD_DATA, relative_path))
    data_dir = os.path.abspath(DASHBOARD_DATA)
    if (not relative_path or os.path.commonpath([data_dir, fpath]) != data_dir
            or not os.path.isfile(fpath)):
        raise FileNotFoundError("找不到指定的 Excel 檔案")
    return fpath


@lru_cache(maxsize=8)
def _read_dashboard_excel_cached(fpath, modified_ns, file_size):
    """Reuse parsed workbooks until the source file changes."""
    return pd.read_excel(fpath)


def _read_dashboard_excel(filename):
    fpath = _safe_dashboard_path(filename)
    stat = os.stat(fpath)
    return _read_dashboard_excel_cached(fpath, stat.st_mtime_ns, stat.st_size)

def _find_column(df, candidates):
    for col in df.columns:
        col_text = str(col).lower()
        if any(candidate.lower() in col_text for candidate in candidates):
            return col
    return None

def _column_by_index(df, index):
    if len(df.columns) > index:
        return df.columns[index]
    return None

def get_column_names(df):
    return {
        "gender_col": _find_column(df, ["sex", "性別"]),
        "age_col": _find_column(df, ["age", "診斷年齡", "年齡"]),
        "site_col": _find_column(df, ["site", "原發部位"]),
        "hist_col": _find_column(df, ["hist", "組織型態"]),
        "year_col": _find_column(df, ["didiag", "最初診斷日", "診斷日期"]),
        "behavior_col": _find_column(df, ["behavior", "性態碼"]),
        "ajcc_ed_col": _find_column(df, ["ajcc_ed", "ajcc edition", "ajcc版本"]),
        "class_col": _find_column(df, ["class", "診斷等級", "診斷方式", "個案分類"]) or _column_by_index(df, 9),
        "confirm_col": _find_column(df, ["confirm", "確診方式", "確診"]) or _column_by_index(df, 20),
        "diag_status_col": _find_column(df, ["診斷狀態分類", "診斷狀態"]),
        "treat_status_col": _find_column(df, ["治療狀態分類", "治療狀態"]),
        "patient_id_col": _find_column(df, ["病歷號碼", "user", "id"]),
        "last_contact_col": _find_column(df, ["最後聯絡或死亡日期", "最後聯絡日期", "last contact"]),
        "vital_status_col": _find_column(df, ["生存狀態", "vital status"]),
        "clinical_stage_col": _find_column(df, ["臨床期別組合", "clinical stage"]),
        "pathological_stage_col": _find_column(df, ["病理期別組合", "pathological stage"]),
        "clinical_m_col": _find_column(df, ["臨床M", "clinical m"]),
        "pathological_m_col": _find_column(df, ["病理M", "pathological m"]),
    }

# 性別年齡分布圖

def _empty_dashboard_response(message="查無符合條件資料！", histology_reason=""):
    labels = ['≦19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49', '50-54', '55-59', '60-64', '65-69', '70-74', '75-79', '80-84', '≧85']
    return {
        "noDataWarning": message,
        "genderAgeData": {
            "categories": labels,
            "male": [0] * len(labels),
            "female": [0] * len(labels),
            "total": [0] * len(labels)
        },
        "ageMedianData": [],
        "analyzableConfirmedData": [],
        "histologyData": [],
        "histologyWarnings": [],
        "histologyNoDataReason": histology_reason or message,
        "diagnosisClassificationData": [],
        "stageFirstCourseData": [],
        "stageSurgeryData": [],
        "survivalData": {
            "rows": [],
            "no_data_reason": message,
        },
    }


def _diagnosis_years(df, year_col):
    if not year_col or year_col not in df.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(df[year_col].astype(str).str[:4], errors="coerce").dropna()


def _query_year_range_outside_data(df, cols, year_start, year_end):
    if not (year_start and year_end):
        return False

    year_col = cols.get("year_col")
    years = _diagnosis_years(df, year_col)
    if years.empty:
        return True

    try:
        query_start = int(year_start)
        query_end = int(year_end)
    except (TypeError, ValueError):
        return True

    data_start = int(years.min())
    data_end = int(years.max())
    return query_start < data_start or query_end > data_end

def filter_dashboard_data(df, cols, cancers=[], year_start="", year_end="", behavior=""):
    df = df.copy()

    # --- 年份篩選 ---
    year_col = cols["year_col"]
    if year_start and year_end and year_col:
        df['extracted_year'] = df[year_col].astype(str).str[:4]
        df['extracted_year'] = pd.to_numeric(df['extracted_year'], errors='coerce')
        df = df[(df['extracted_year'] >= int(year_start)) & (df['extracted_year'] <= int(year_end))]
        
    # --- 性態碼篩選 ---
    behavior_col = cols["behavior_col"]
    if behavior and behavior_col and behavior != 'all':
        df[behavior_col] = df[behavior_col].astype(str)
        df = df[df[behavior_col].str.startswith(str(behavior))]
        
    # --- 癌別篩選 ---
    site_col = cols["site_col"]
    hist_col = cols["hist_col"]
    if cancers and "All_Cancers" not in cancers and site_col and hist_col:
        def is_selected_cancer(row):
            behavior_col = cols.get("behavior_col")
            year_col = cols.get("year_col")
            ajcc_ed_col = cols.get("ajcc_ed_col")
            gender_col = cols.get("gender_col")
            res = classify_cancer_group(
                str(row[site_col]),
                str(row[hist_col]),
                CANCER_GROUP_RULES,
                behavior=str(row[behavior_col]) if behavior_col else None,
                didiag=str(row[year_col]) if year_col else None,
                ajcc_ed=str(row[ajcc_ed_col]) if ajcc_ed_col else None,
                sex=str(row[gender_col]) if gender_col else None,
            )
            if not res:
                return False
            matched_keys = {res["group_key"], res["subgroup_key"], *res.get("ancestor_subgroup_keys", [])}
            return bool(matched_keys.intersection(cancers))
        df = df[df.apply(is_selected_cancer, axis=1)]
        
    return df

# 性別年齡分布(表,圖)
def calculate_gender_age_distribution(df, cols):
    labels = ['<=19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49', '50-54', '55-59', '60-64', '65-69', '70-74', '75-79', '80-84', '>=85']
    gender_age_data = {
        "categories": labels,
        "male": [0] * len(labels),
        "female": [0] * len(labels),
        "total": [0] * len(labels)
    }
    
    gender_col = cols["gender_col"]
    age_col = cols["age_col"]
    
    if gender_col in df.columns and age_col in df.columns:
        df_ga = df[[gender_col, age_col]].dropna()
        df_ga[age_col] = pd.to_numeric(df_ga[age_col], errors='coerce')
        df_ga = df_ga.dropna(subset=[age_col])
        df_ga[gender_col] = df_ga[gender_col].astype(str)
        
        bins = [0, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 150]
        df_ga['AgeGroup'] = pd.cut(df_ga[age_col], bins=bins, labels=labels, right=False)
        
        for idx, label in enumerate(labels):
            m_count = len(df_ga[(df_ga['AgeGroup'] == label) & (df_ga[gender_col].isin(['1', '1.0', '男']))])
            f_count = len(df_ga[(df_ga['AgeGroup'] == label) & (df_ga[gender_col].isin(['2', '2.0', '女']))])
            gender_age_data["male"][idx] = m_count
            gender_age_data["female"][idx] = f_count
            gender_age_data["total"][idx] = m_count + f_count
            
    return gender_age_data

# 年齡中位數(表)
def calculate_age_median(df, cols):
    age_median_data = {
        "male": 0, "female": 0, "total": 0,
        "male_count": 0, "female_count": 0, "total_count": 0, "male_ratio": "0.00", "female_ratio": "0.00"
    }
    
    gender_col = cols["gender_col"]
    age_col = cols["age_col"]
    
    if gender_col in df.columns and age_col in df.columns:
        df_ga = df[[gender_col, age_col]].dropna()
        df_ga[age_col] = pd.to_numeric(df_ga[age_col], errors='coerce')
        df_ga = df_ga.dropna(subset=[age_col])
        df_ga[gender_col] = df_ga[gender_col].astype(str)
        
        m_df = df_ga[df_ga[gender_col].isin(['1', '1.0', '男'])]
        f_df = df_ga[df_ga[gender_col].isin(['2', '2.0', '女'])]
        
        age_median_data["male"] = round(m_df[age_col].median(), 1) if not m_df.empty else 0
        age_median_data["female"] = round(f_df[age_col].median(), 1) if not f_df.empty else 0
        age_median_data["total"] = round(df_ga[age_col].median(), 1) if not df_ga.empty else 0
        
        m_count = len(m_df)
        f_count = len(f_df)
        age_median_data["male_count"] = m_count
        age_median_data["female_count"] = f_count
        age_median_data["total_count"] = m_count + f_count
        
        if f_count > 0:
            age_median_data["male_ratio"] = f"{round(m_count / f_count, 2):.2f}"
            age_median_data["female_ratio"] = "1.00"
        elif m_count > 0:
            age_median_data["male_ratio"] = "女性為 0，無法計算"
            age_median_data["female_ratio"] = "0.00"
        else:
            age_median_data["male_ratio"] = "0.00"
            age_median_data["female_ratio"] = "0.00"
            
    return age_median_data


def extract_year_display(value):
    text = display_value(value)
    return text[:4] if len(text) >= 4 and text[:4].isdigit() else text


def clean_warning_sentence(text):
    return str(text or "").replace("。", "").strip()


def build_histology_raw_data_message(warning_type, mismatch_fields, didiag_value, site_value):
    if warning_type != "condition_mismatch":
        return ""

    fields = mismatch_fields or []
    details = []
    year = extract_year_display(didiag_value)
    if "year" in fields and year:
        details.append(f"診斷年度 {year}")
    if "site" in fields and site_value:
        details.append(f"原發部位 {site_value}")

    if not details:
        return ""
    return f"（原始資料：{'、'.join(details)}）"

# 可分析個案與確診個案表
def normalize_case_code(value):
    if pd.isna(value):
        return ""

    text = str(value).strip()
    try:
        return str(int(float(text)))
    except (ValueError, TypeError):
        return text


def filter_stage_analysis_cases(df, cols):
    class_col = cols.get("class_col")
    if not class_col or class_col not in df.columns:
        return df.iloc[0:0].copy()
    return df.loc[df[class_col].apply(normalize_case_code).isin(["1", "2"])].copy()


def display_value(value):
    if pd.isna(value):
        return ""

    text = str(value).strip()
    try:
        numeric = float(text)
        if numeric.is_integer():
            return str(int(numeric))
    except (ValueError, TypeError):
        pass

    return text

# 可分析個案與確診個案(表)
def calculate_analyzable_confirmed_cases(df, cols):
    analyzable_confirmed_data = {
        "total_count": 0,
        "analyzable_count": 0,
        "analyzable_percent": "0.0%",
        "confirmed_count": 0,
        "confirmed_percent": "0.0%"
    }

    class_col = cols["class_col"]
    confirm_col = cols["confirm_col"]

    total_count = len(df)
    analyzable_confirmed_data["total_count"] = total_count

    if class_col in df.columns and confirm_col in df.columns:
        df_case = df[[class_col, confirm_col]].copy()
        df_case[class_col] = df_case[class_col].apply(normalize_case_code)
        df_case[confirm_col] = df_case[confirm_col].apply(normalize_case_code)

        analyzable_df = df_case[df_case[class_col].isin(["1", "2"])]
        confirmed_df = analyzable_df[analyzable_df[confirm_col].isin(["1", "2", "3", "4"])]

        analyzable_count = len(analyzable_df)
        confirmed_count = len(confirmed_df)

        analyzable_confirmed_data["analyzable_count"] = analyzable_count
        analyzable_confirmed_data["confirmed_count"] = confirmed_count

        if total_count > 0:
            analyzable_confirmed_data["analyzable_percent"] = f"{round(analyzable_count / total_count * 100, 1):.1f}%"

        if analyzable_count > 0:
            analyzable_confirmed_data["confirmed_percent"] = f"{round(confirmed_count / analyzable_count * 100, 1):.1f}%"

    return analyzable_confirmed_data

# 組織型態(表,圖)
def calculate_histology_distribution(df, cols, cancers=None, year_start="", year_end="", return_warnings=False):
    hist_dist_data = []
    histology_warnings = []
    unknown_name = "Unknown / 未對應組織型態"

    class_col = cols["class_col"]
    hist_col = cols["hist_col"]
    behavior_col = cols["behavior_col"]
    site_col = cols["site_col"]
    year_col = cols["year_col"]
    patient_id_col = cols.get("patient_id_col")

    if class_col in df.columns and hist_col in df.columns and behavior_col in df.columns:
        df_filtered = df.dropna(subset=[class_col])
        df_filtered = df_filtered[df_filtered[class_col].apply(normalize_case_code).isin(["1", "2"])]

        total_valid_cases = len(df_filtered)
        if total_valid_cases > 0:
            rules = get_histology_code_rules()
            hist_counts = {}
            for _, row in df_filtered.iterrows():
                case_row = {
                    "hist": row[hist_col] if hist_col in df.columns else "",
                    "behavior": row[behavior_col] if behavior_col in df.columns else "",
                    "site": row[site_col] if site_col in df.columns else "",
                    "didiag": row[year_col] if year_col in df.columns else "",
                }
                cancer = classify_cancer_group(
                    case_row["site"], case_row["hist"], CANCER_GROUP_RULES,
                    behavior=case_row["behavior"], didiag=case_row["didiag"],
                )
                if is_blood_or_lymphoid(cancer):
                    name_zh, name_en = blood_or_lymphoid_name(cancer)
                    res = {
                        "status": "matched", "icdo_code": f"{normalize_case_code(case_row['hist'])}/{normalize_case_code(case_row['behavior'])}",
                        "name_zh": name_zh, "name_en": name_en,
                    }
                else:
                    res = resolve_histology_code(case_row, cancer, rules, year_start, year_end)
                icdo_code = res.get("icdo_code", "")
                report_name_zh = res.get("name_zh", unknown_name)
                report_name_en = res.get("name_en", unknown_name)
                if res.get("status") == "matched" and should_append_in_situ(
                    case_row, cancer, case_row["hist"], case_row["behavior"]
                ):
                    report_name_zh = f"{report_name_zh}(原位癌)"
                    report_name_en = f"{report_name_en}(in situ)"
                key = (icdo_code, report_name_zh, report_name_en)
                hist_counts[key] = hist_counts.get(key, 0) + 1

                if res.get("status") != "matched":
                    user_id = display_value(row[patient_id_col]) if patient_id_col in df.columns else ""
                    site_value = display_value(row[site_col]) if site_col in df.columns else ""
                    hist_value = display_value(row[hist_col]) if hist_col in df.columns else ""
                    behavior_value = display_value(row[behavior_col]) if behavior_col in df.columns else ""
                    didiag_value = display_value(row[year_col]) if year_col in df.columns else ""
                    warning_type = "ambiguous_mapping" if res.get("status") == "ambiguous" else "not_in_mapping"
                    mismatch_fields = []
                    default_message = f"{icdo_code} 未納入組織代碼表。"
                    message = clean_warning_sentence(
                        f"{icdo_code} 在組織代碼表中有重複且名稱不一致的資料，請確認。"
                        if warning_type == "ambiguous_mapping" else default_message
                    )
                    detail_message = clean_warning_sentence(
                        "請補充原發部位適用條件或確認此代碼的最終組織型態名稱。"
                        if warning_type == "ambiguous_mapping"
                        else "請確認常見癌別、組織型態代碼與性態碼是否已匯入組織代碼表。"
                    )
                    raw_data_message = build_histology_raw_data_message(
                        warning_type,
                        mismatch_fields,
                        didiag_value,
                        site_value,
                    )
                    histology_warnings.append({
                        "user": user_id or "未知個案",
                        "site": site_value,
                        "hist": hist_value,
                        "behavior": behavior_value,
                        "didiag": didiag_value,
                        "icdo_code": icdo_code,
                        "warning_type": warning_type,
                        "mismatch_fields": mismatch_fields,
                        "raw_data_message": raw_data_message,
                        "message": message,
                        "detail_message": detail_message
                    })

            for (icdo_code, report_name_zh, report_name_en), count in hist_counts.items():
                pct = (count / total_valid_cases) * 100
                hist_dist_data.append({
                    "code": icdo_code,
                    "name": report_name_zh,
                    "name_zh": report_name_zh,
                    "name_en": report_name_en,
                    "count": count,
                    "percentage": f"{pct:.1f}%",
                    "pct_val": pct})

            hist_dist_data.sort(key=lambda x: x["pct_val"], reverse=True)
            for item in hist_dist_data:
                item.pop("pct_val", None)

    if return_warnings:
        return hist_dist_data, histology_warnings

    return hist_dist_data

def get_histology_no_data_reason(df, cols, histology_data, histology_warnings):
    valid_histology = [
        item for item in histology_data
        if item.get("name") != "Unknown / 未對應組織型態"
    ]
    if valid_histology:
        return ""

    required_columns = {
        "個案分類": cols.get("class_col"),
        "組織型態": cols.get("hist_col"),
        "性態碼": cols.get("behavior_col"),
    }
    missing = [name for name, column in required_columns.items() if not column or column not in df.columns]
    if missing:
        return f"缺少{'、'.join(missing)}欄位，無法產生組織型態統計。"

    class_col = cols.get("class_col")
    eligible_count = int(df[class_col].apply(normalize_case_code).isin(["1", "2"]).sum())
    if eligible_count == 0:
        return "個案分類不符合分析條件；組織型態僅納入 Class1 與 Class2 個案。"
    if histology_warnings:
        return "符合個案分類的資料皆未通過組織型態規則，可能與組織代碼、診斷年度或原發部位條件不符。"
    return "符合篩選條件的個案沒有可統計的組織型態資料。"

def calculate_diagnosis_classification(df, cols):
    data = {
        "class0_total": 0, "0_1_0": 0, "0_1_2": 0,
        "class1_total": 0, "1_1_1": 0, "1_1_3": 0, "1_1_4": 0,
        "class2_total": 0, "2_2_1": 0, "2_2_3": 0,
        "class3_total": 0, "3_2_0": 0, "3_3_2": 0,
        "total_count": 0}
    class_col = cols.get("class_col")
    diag_status_col = cols.get("diag_status_col")
    treat_status_col = cols.get("treat_status_col")
    
    if class_col in df.columns:
        df_class = df.copy()
        df_class[class_col] = df_class[class_col].apply(normalize_case_code)
        
        has_diag = bool(diag_status_col and diag_status_col in df.columns)
        has_treat = bool(treat_status_col and treat_status_col in df.columns)
        
        if has_diag: df_class[diag_status_col] = df_class[diag_status_col].apply(normalize_case_code)
        if has_treat: df_class[treat_status_col] = df_class[treat_status_col].apply(normalize_case_code)
        
        data["total_count"] = len(df_class)
        
        for idx, row in df_class.iterrows():
            c = str(row[class_col])
            d = str(row[diag_status_col]) if has_diag else ""
            t = str(row[treat_status_col]) if has_treat else ""
            
            if c == "0":
                data["class0_total"] += 1
                if d == "1" and t == "0": data["0_1_0"] += 1
                if d == "1" and t == "2": data["0_1_2"] += 1
            elif c == "1":
                data["class1_total"] += 1
                if d == "1" and t == "1": data["1_1_1"] += 1
                if d == "1" and t == "3": data["1_1_3"] += 1
                if d == "1" and t == "4": data["1_1_4"] += 1
            elif c == "2":
                data["class2_total"] += 1
                if d == "2" and t == "1": data["2_2_1"] += 1
                if d == "2" and t == "3": data["2_2_3"] += 1
            elif c == "3":
                data["class3_total"] += 1
                if d == "2" and t == "0": data["3_2_0"] += 1
                if d == "3" and t == "2": data["3_3_2"] += 1
    return data

# 存活率（Kaplan–Meier）
def _parse_registry_date(series):
    text = series.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    text = text.where(text.str.match(r"^\d{4}/\d{1,2}/\d{1,2}$"))
    return pd.to_datetime(text, format="%Y/%m/%d", errors="coerce")


def _normalize_stage(value):
    text = str(value or "").upper().replace("STAGE", "").strip()
    if not text or text in {"NAN", "NONE", "999", "888", "BBB"}:
        return ""
    compact = text.replace(" ", "").replace(".", "")
    if compact.startswith("0"):
        return "Stage 0"
    if compact.startswith("1") or compact.startswith("I") and not compact.startswith(("II", "IV")):
        return "Stage I"
    if compact.startswith("2") or compact.startswith("II") and not compact.startswith("III"):
        return "Stage II"
    if compact.startswith("3") or compact.startswith("III"):
        return "Stage III"
    if compact.startswith("4") or compact.startswith("IV"):
        return "Stage IV"
    return ""


def calculate_survival_table(df, cols):
    required = [cols.get("year_col"), cols.get("last_contact_col"), cols.get("vital_status_col")]
    if not all(required):
        return {"rows": [], "no_data_reason": "檔案缺少診斷日期、最後聯絡或死亡日期或生存狀態欄位。"}

    data = df.copy()
    source_count = int(len(data))
    exclusion_summary = {
        "source_count": source_count,
        "class0": 0,
        "class3": 0,
        "other_class": 0,
        "invalid_diagnosis_date": 0,
        "invalid_last_contact_date": 0,
        "invalid_vital_status": 0,
        "last_contact_before_diagnosis": 0,
        "stage0": 0,
        "no_usable_stage": 0,
        "stage4_missing_m": 0,
        "included_count": 0,
        "excluded_count": 0,
    }
    class_col = cols.get("class_col")
    if class_col:
        case_class = data[class_col].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
        exclusion_summary["class0"] = int((case_class == "0").sum())
        exclusion_summary["class3"] = int((case_class == "3").sum())
        exclusion_summary["other_class"] = int((~case_class.isin(["0", "1", "2", "3"])).sum())
        data = data.loc[case_class.isin(["1", "2"])].copy()
    if data.empty:
        exclusion_summary["excluded_count"] = source_count
        return {"rows": [], "no_data_reason": "所選資料沒有 Class1 或 Class2 可分析個案。", "exclusion_summary": exclusion_summary}

    diagnosis_date = _parse_registry_date(data[cols["year_col"]])
    last_contact_date = _parse_registry_date(data[cols["last_contact_col"]])
    vital_status = pd.to_numeric(data[cols["vital_status_col"]], errors="coerce")
    invalid_diagnosis = diagnosis_date.isna()
    invalid_last_contact = ~invalid_diagnosis & last_contact_date.isna()
    invalid_status = ~invalid_diagnosis & ~invalid_last_contact & ~vital_status.isin([0, 1])
    reversed_dates = ~invalid_diagnosis & ~invalid_last_contact & ~invalid_status & (last_contact_date < diagnosis_date)
    exclusion_summary["invalid_diagnosis_date"] = int(invalid_diagnosis.sum())
    exclusion_summary["invalid_last_contact_date"] = int(invalid_last_contact.sum())
    exclusion_summary["invalid_vital_status"] = int(invalid_status.sum())
    exclusion_summary["last_contact_before_diagnosis"] = int(reversed_dates.sum())
    valid = ~(invalid_diagnosis | invalid_last_contact | invalid_status | reversed_dates)
    data = data.loc[valid].copy()
    if data.empty:
        exclusion_summary["excluded_count"] = source_count
        return {"rows": [], "no_data_reason": "沒有同時具備有效診斷日期、追蹤日期與生存狀態的個案。", "exclusion_summary": exclusion_summary}

    data["_survival_months"] = (last_contact_date.loc[valid] - diagnosis_date.loc[valid]).dt.days / 30.4375
    data["_survival_event"] = (vital_status.loc[valid] == 0).astype(int)
    pathological = cols.get("pathological_stage_col")
    clinical = cols.get("clinical_stage_col")
    pathological_stage = data[pathological].map(_normalize_stage) if pathological else pd.Series("", index=data.index)
    clinical_stage = data[clinical].map(_normalize_stage) if clinical else pd.Series("", index=data.index)
    data["_survival_stage"] = pathological_stage.where(pathological_stage != "", clinical_stage)

    def normalize_m(value):
        text = str(value or "").upper().replace("M", "").replace(".", "").strip()
        if text == "0":
            return "M0"
        if text.startswith("1"):
            return "M1"
        return ""

    pathological_m_col = cols.get("pathological_m_col")
    clinical_m_col = cols.get("clinical_m_col")
    pathological_m = data[pathological_m_col].map(normalize_m) if pathological_m_col else pd.Series("", index=data.index)
    clinical_m = data[clinical_m_col].map(normalize_m) if clinical_m_col else pd.Series("", index=data.index)
    data["_survival_m"] = pathological_m.where(pathological_m != "", clinical_m)
    stage_iv = data["_survival_stage"] == "Stage IV"
    data.loc[stage_iv & (data["_survival_m"] == "M0"), "_survival_stage"] = "Stage IV(M0)"
    data.loc[stage_iv & (data["_survival_m"] == "M1"), "_survival_stage"] = "Stage IV(M1)"
    exclusion_summary["stage0"] = int((data["_survival_stage"] == "Stage 0").sum())
    exclusion_summary["no_usable_stage"] = int((data["_survival_stage"] == "").sum())
    exclusion_summary["stage4_missing_m"] = int((data["_survival_stage"] == "Stage IV").sum())

    def row_for(label, group):
        total = int(len(group))
        event_count = int(group["_survival_event"].sum())
        return {
            "stage": label,
            "total": total,
            "events": event_count,
            "censored": total - event_count,
            "percentage": round((total - event_count) / total * 100, 1) if total else 0.0,
        }

    def curve_for(label, group):
        survival = 1.0
        curve = [[0.0, 1.0]]
        censored = []
        for time_value in sorted(group["_survival_months"].unique()):
            at_risk = int((group["_survival_months"] >= time_value).sum())
            deaths = int(((group["_survival_months"] == time_value) & (group["_survival_event"] == 1)).sum())
            if deaths and at_risk:
                survival *= 1 - deaths / at_risk
                curve.append([round(float(time_value), 2), round(survival, 6)])
            censored_count = int(((group["_survival_months"] == time_value) & (group["_survival_event"] == 0)).sum())
            if censored_count:
                censored.append({
                    "value": [round(float(time_value), 2), round(survival, 6)],
                    "count": censored_count,
                })
        max_months = round(float(group["_survival_months"].max()), 2)
        if curve[-1][0] < max_months:
            curve.append([max_months, round(survival, 6)])
        return {"stage": label, "count": int(len(group)), "curve": curve, "censored": censored}

    rows = []
    chart_series = []
    report_stages = ["Stage I", "Stage II", "Stage III", "Stage IV(M0)", "Stage IV(M1)"]
    for stage in report_stages:
        stage_data = data.loc[data["_survival_stage"] == stage]
        if not stage_data.empty:
            rows.append(row_for(stage, stage_data))
            chart_series.append(curve_for(stage, stage_data))
    report_data = data.loc[data["_survival_stage"].isin(report_stages)]
    exclusion_summary["included_count"] = int(len(report_data))
    exclusion_summary["excluded_count"] = source_count - exclusion_summary["included_count"]
    if not report_data.empty:
        rows.append(row_for("Overall", report_data))
    return {
        "rows": rows,
        "chart_series": chart_series,
        "exclusion_summary": exclusion_summary,
        "no_data_reason": "" if rows else "沒有符合 AJCC Stage I–IV(M0/M1) 的有效存活資料。",
    }


# 個案分類(表,圖)
def analyze_dashboard_file(filename, cancers=[], year_start="", year_end="", behavior="",
                           analysis_items=None, source_df=None, cols=None, filtered_df=None, stage_options=None):
    try:
        source_df = source_df if source_df is not None else _read_dashboard_excel(filename)
        cols = cols or get_column_names(source_df)

        if _query_year_range_outside_data(source_df, cols, year_start, year_end):
            return _empty_dashboard_response(
                histology_reason="所選年度區間不在檔案的診斷年度範圍內。"
            )

        year_filtered_df = filter_dashboard_data(source_df, cols, [], year_start, year_end, "")
        if year_filtered_df.empty:
            return _empty_dashboard_response(histology_reason="所選年度內沒有可分析個案。")
        behavior_filtered_df = filter_dashboard_data(source_df, cols, [], year_start, year_end, behavior)
        if behavior_filtered_df.empty:
            return _empty_dashboard_response(histology_reason="所選年度內沒有符合性態碼條件的個案。")
        df = filtered_df if filtered_df is not None else filter_dashboard_data(
            source_df, cols, cancers, year_start, year_end, behavior
        )
        if df.empty:
            return _empty_dashboard_response(histology_reason="沒有同時符合所選年度、性態碼與癌別條件的個案。")
        
        selected = set(analysis_items or [])
        calculate_all = not selected
        incidence_selected = calculate_all or bool(
            selected.intersection({"性別年齡分佈", "年齡中位數"})
        )
        diagnosis_selected = calculate_all or bool(
            selected.intersection({"可分析個案與確診個案", "組織型態", "個案分類"})
        )
        stage_selected = calculate_all or bool(stage_options) or bool(
            selected.intersection({"分期呈現最細碼", "分期不呈現最細碼"})
        )
        treatment_selected = calculate_all or "期別與首次療程" in selected
        surgery_selected = calculate_all or "期別與手術術式" in selected
        result = _empty_dashboard_response()
        result.pop("noDataWarning", None)
        result["histologyNoDataReason"] = ""

        if incidence_selected:
            result["genderAgeData"] = calculate_gender_age_distribution(df, cols)
            result["ageMedianData"] = calculate_age_median(df, cols)
        if diagnosis_selected:
            result["analyzableConfirmedData"] = calculate_analyzable_confirmed_cases(df, cols)
        if diagnosis_selected:
            histology_data, histology_warnings = calculate_histology_distribution(
                df, cols, cancers=cancers, year_start=year_start, year_end=year_end, return_warnings=True
            )
            result["histologyData"] = histology_data
            result["histologyWarnings"] = histology_warnings
            result["histologyNoDataReason"] = get_histology_no_data_reason(
                df, cols, histology_data, histology_warnings
            )
        if diagnosis_selected:
            result["diagnosisClassificationData"] = calculate_diagnosis_classification(df, cols)
        if stage_selected:
            stage_df = filter_stage_analysis_cases(df, cols)
            result["stageAnalysisData"] = {
                "source_count": int(len(df)),
                "class_1_2_count": int(len(stage_df)),
            }
            if stage_options:
                from modules.blueprint.clean.field_mapping import field_mapping
                from modules.blueprint.dashboard.period_rule import (
                    calculate_stage_first_course_distribution,
                    calculate_stage_surgery_distribution,
                    calculate_stage_reports,
                )

                aliases, _ = field_mapping("中文欄位名稱")
                chinese_df = df.rename(columns={
                    column: aliases.get(str(column).strip(), str(column).strip())
                    for column in df.columns
                })
                treatment_aliases, _ = field_mapping("雲醫癌AI模組")
                for column in list(chinese_df.columns):
                    treatment_key = treatment_aliases.get(str(column).strip())
                    if treatment_key and treatment_key not in chinese_df.columns:
                        chinese_df[treatment_key] = chinese_df[column]
                stage_reports = calculate_stage_reports(chinese_df, stage_options)
                result["stageReports"] = stage_reports
                result["stageTotals"] = [
                    {"option": report["option"], "total_count": report["analyzable_count"]}
                    for report in stage_reports
                ]
                if treatment_selected:
                    result["stageFirstCourseData"] = calculate_stage_first_course_distribution(
                        chinese_df, stage_options
                    )
                if surgery_selected:
                    result["stageSurgeryData"] = calculate_stage_surgery_distribution(
                        chinese_df, stage_options,
                        manual_keys=cancers,
                    )
        if calculate_all or "存活率" in selected:
            result["survivalData"] = calculate_survival_table(df, cols)

        return result
    except Exception as e:
        logging.error(f"error {filename}: {str(e)}")
        raise e

def get_dashboard_file_years(filename, source_df=None, cols=None):
    df = source_df if source_df is not None else _read_dashboard_excel(filename)
    cols = cols or get_column_names(df)
    years = _diagnosis_years(df, cols.get("year_col"))
    years = years[(years >= 1900) & (years <= 2100)]
    return sorted(years.astype(int).unique().tolist())

def get_dashboard_file_preview(filename, limit=10, year_start="", year_end="", source_df=None, cols=None):
    df = source_df if source_df is not None else _read_dashboard_excel(filename)
    if year_start:
        cols = cols or get_column_names(df)
        year_col = cols.get("year_col")
        if year_col:
            try:
                start = int(year_start)
                end = int(year_end or year_start)
                year_values = pd.to_numeric(
                    df[year_col].astype(str).str[:4], errors="coerce"
                )
                df = df.loc[year_values.between(start, end)]
            except (TypeError, ValueError):
                df = df.iloc[0:0]
    df = df.head(limit)
    df = df.where(pd.notnull(df), "")
    return {
        "columns": [str(col) for col in df.columns],
        "rows": df.astype(str).values.tolist(),
    }

def summarize_dashboard_file(filename, behavior="", cancers=None, year_start="", year_end="",
                             source_df=None, cols=None, filtered_df=None):
    df = source_df if source_df is not None else _read_dashboard_excel(filename)
    cols = cols or get_column_names(df)
    years = get_dashboard_file_years(filename, df, cols)
    year_start = str(year_start or years[0]) if years else ""
    year_end = str(year_end or year_start) if years else ""
    filtered_df = filtered_df if filtered_df is not None else filter_dashboard_data(
        df, cols, cancers or [], year_start, year_end, behavior
    )
    age_data = calculate_age_median(filtered_df, cols)
    case_data = calculate_analyzable_confirmed_cases(filtered_df, cols)
    filtered_years = _diagnosis_years(filtered_df, cols.get("year_col"))
    yearly_counts = {
        str(int(year)): int(count)
        for year, count in filtered_years.dropna().astype(int).value_counts().sort_index().items()
    }
    period_years = [year for year in years if int(year_start) <= year <= int(year_end)] if year_start and year_end else []
    year_label = year_start if year_start == year_end else f"{year_start}–{year_end}"
    year_count = len(period_years)

    return {
        "filename": os.path.basename(filename or ""),
        "years": years,
        "year_label": year_label or "無法偵測",
        "year_start": year_start,
        "year_end": year_end,
        "year_count": year_count,
        "total_count": int(len(filtered_df)),
        "annual_average": round(len(filtered_df) / year_count, 1) if year_count else 0,
        "yearly_counts": yearly_counts,
        "male_count": int(age_data["male_count"]),
        "female_count": int(age_data["female_count"]),
        "median_age": age_data["total"],
        "analyzable_count": int(case_data["analyzable_count"]),
        "confirmed_count": int(case_data["confirmed_count"]),
        "confirmed_percent": case_data["confirmed_percent"],
    }

def compare_dashboard_files(main_filename, target_filename, behavior="", cancers=None, compare_items=None,
                            main_year="", target_year="", main_year_end="", target_year_end="",
                            compare_mode="single", stage_options=None):
    main_end = main_year if compare_mode == "single" else (main_year_end or main_year)
    target_end = target_year if compare_mode == "single" else (target_year_end or target_year)
    main_source = _read_dashboard_excel(main_filename)
    target_source = _read_dashboard_excel(target_filename)
    main_cols = get_column_names(main_source)
    target_cols = get_column_names(target_source)
    main_filtered = filter_dashboard_data(
        main_source, main_cols, cancers or [], main_year, main_end, behavior
    )
    target_filtered = filter_dashboard_data(
        target_source, target_cols, cancers or [], target_year, target_end, behavior
    )
    main_data = summarize_dashboard_file(
        main_filename, behavior, cancers, main_year, main_end,
        main_source, main_cols, main_filtered
    )
    target_data = summarize_dashboard_file(
        target_filename, behavior, cancers, target_year, target_end,
        target_source, target_cols, target_filtered
    )

    diff = target_data["total_count"] - main_data["total_count"]
    diff_percent = ""
    if main_data["total_count"] > 0:
        diff_percent = f"{round(diff / main_data['total_count'] * 100, 1):.1f}%"
    annual_average_diff = round(target_data["annual_average"] - main_data["annual_average"], 1)

    return {
        "main": main_data,
        "target": target_data,
        "analysis_data": {
            "main": analyze_dashboard_file(
                main_filename, cancers or [], main_year, main_end, behavior,
                compare_items, main_source, main_cols, main_filtered, stage_options
            ),
            "target": analyze_dashboard_file(
                target_filename, cancers or [], target_year, target_end, behavior,
                compare_items, target_source, target_cols, target_filtered, stage_options
            ),
            "items": compare_items or [],
        },
        "compare_mode": compare_mode,
        "diff": {
            "total_count": diff,
            "total_percent": diff_percent,
            "annual_average": annual_average_diff,
        }
    }
