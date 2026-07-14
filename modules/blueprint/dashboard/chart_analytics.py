import os
import pandas as pd
import logging
from modules.blueprint.dashboard.definition.cancer_grouping import classify_cancer_group
from modules.blueprint.dashboard.definition.cancer_group_rules import CANCER_GROUP_RULES
from modules.blueprint.dashboard.definition.histology_mapping import get_histology_rules
from modules.blueprint.dashboard.definition.histology_validate import match_histology

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DASHBOARD_DATA = f"{BASE_DIR}/tasks/data"

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
    }

# 性別年齡分布圖

def _empty_dashboard_response(message="查無符合條件資料！"):
    return {
        "noDataWarning": message,
        "genderAgeData": {"male": [], "female": [], "total": []},
        "ageMedianData": [],
        "analyzableConfirmedData": [],
        "histologyData": [],
        "histologyWarnings": [],
        "diagnosisClassificationData": []
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
def calculate_histology_distribution(df, cols, return_warnings=False):
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
            rules = get_histology_rules()
            hist_counts = {}
            for _, row in df_filtered.iterrows():
                case_row = {
                    "hist": row[hist_col] if hist_col in df.columns else "",
                    "behavior": row[behavior_col] if behavior_col in df.columns else "",
                    "site": row[site_col] if site_col in df.columns else "",
                    "didiag": row[year_col] if year_col in df.columns else "",
                }
                res = match_histology(case_row, rules)
                icdo_code = res.get("icdo_code", "")
                report_name = res.get("report_name", unknown_name)
                key = (icdo_code, report_name)
                hist_counts[key] = hist_counts.get(key, 0) + 1

                if report_name == unknown_name:
                    user_id = display_value(row[patient_id_col]) if patient_id_col in df.columns else ""
                    site_value = display_value(row[site_col]) if site_col in df.columns else ""
                    hist_value = display_value(row[hist_col]) if hist_col in df.columns else ""
                    behavior_value = display_value(row[behavior_col]) if behavior_col in df.columns else ""
                    didiag_value = display_value(row[year_col]) if year_col in df.columns else ""
                    warning_type = res.get("warning_type", "not_in_mapping")
                    mismatch_fields = res.get("mismatch_fields", [])
                    default_message = f"{icdo_code} 未納入 1.3 組織型態規則。"
                    message = clean_warning_sentence(res.get("message", default_message))
                    detail_message = clean_warning_sentence(res.get("detail_message", "若此組織型態無特殊適用條件，則此組織代碼組合不屬於目前統計規則範圍。"))
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

            for (icdo_code, report_name), count in hist_counts.items():
                pct = (count / total_valid_cases) * 100
                hist_dist_data.append({
                    "code": icdo_code,
                    "name": report_name,
                    "count": count,
                    "percentage": f"{pct:.1f}%",
                    "pct_val": pct})

            hist_dist_data.sort(key=lambda x: x["pct_val"], reverse=True)
            for item in hist_dist_data:
                item.pop("pct_val", None)

    if return_warnings:
        return hist_dist_data, histology_warnings

    return hist_dist_data

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

# 個案分類(表,圖)
def analyze_dashboard_file(filename, cancers=[], year_start="", year_end="", behavior=""):
    fpath = f"{DASHBOARD_DATA}/{filename}"
    try:
        df = pd.read_excel(fpath)
        cols = get_column_names(df)

        if _query_year_range_outside_data(df, cols, year_start, year_end):
            return _empty_dashboard_response()

        df = filter_dashboard_data(df, cols, cancers, year_start, year_end, behavior)
        if df.empty:
            return _empty_dashboard_response()
        
        gender_age_data = calculate_gender_age_distribution(df, cols)
        age_median_data = calculate_age_median(df, cols)
        analyzable_confirmed_data = calculate_analyzable_confirmed_cases(df, cols)
        histology_data, histology_warnings = calculate_histology_distribution(df, cols, return_warnings=True)
        diagnosis_classification_data = calculate_diagnosis_classification(df, cols)
  
        return {
            "genderAgeData": gender_age_data,
            "ageMedianData": age_median_data,
            "analyzableConfirmedData": analyzable_confirmed_data,
            "histologyData": histology_data,
            "histologyWarnings": histology_warnings,
            "diagnosisClassificationData": diagnosis_classification_data
        }
    except Exception as e:
        logging.error(f"error {filename}: {str(e)}")
        raise e