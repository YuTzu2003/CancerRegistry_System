import os
import pandas as pd
import logging
from modules.blueprint.dashboard.definition.cancer_grouping import classify_cancer_group
from modules.blueprint.dashboard.definition.cancer_group_rules import CANCER_GROUP_RULES

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
        "class_col": _find_column(df, ["class", "診斷等級", "診斷方式"]) or _column_by_index(df, 9),
        "confirm_col": _find_column(df, ["confirm", "確診方式", "確診"]) or _column_by_index(df, 20),
    }

# 性別年齡分布圖
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
            res = classify_cancer_group(
                str(row[site_col]),
                str(row[hist_col]),
                CANCER_GROUP_RULES,
                behavior=str(row[behavior_col]) if behavior_col else None,
                didiag=str(row[year_col]) if year_col else None,
                ajcc_ed=str(row[ajcc_ed_col]) if ajcc_ed_col else None,
            )
            if not res:
                return False
            return res["group_key"] in cancers or res["subgroup_key"] in cancers           
        df = df[df.apply(is_selected_cancer, axis=1)]
        
    return df

# 性別年齡分布表
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

# 年齡中位數表
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
            age_median_data["male_ratio"] = "無限大"
            age_median_data["female_ratio"] = "0.00"
        else:
            age_median_data["male_ratio"] = "0.00"
            age_median_data["female_ratio"] = "0.00"
            
    return age_median_data

# 可分析個案與確診個案表
def normalize_case_code(value):
    if pd.isna(value):
        return ""

    text = str(value).strip()
    try:
        return str(int(float(text)))
    except (ValueError, TypeError):
        return text


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

def calculate_histology_distribution(df, cols):
    hist_dist_data = []

    class_col = cols["class_col"]
    hist_col = cols["hist_col"]
    behavior_col = cols["behavior_col"]
    site_col = cols["site_col"]
    year_col = cols["year_col"]

    if class_col in df.columns and hist_col in df.columns and behavior_col in df.columns:
        df_filtered = df.dropna(subset=[class_col])
        df_filtered = df_filtered[df_filtered[class_col].apply(normalize_case_code).isin(["1", "2"])]

        total_valid_cases = len(df_filtered)
        if total_valid_cases > 0:
            from modules.blueprint.dashboard.definition.histology_mapping import get_histology_rules
            from modules.blueprint.dashboard.definition.histology_validate import match_histology

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
                report_name = res.get("report_name", "Unknown / 未對應組織型態")
                key = (icdo_code, report_name)
                hist_counts[key] = hist_counts.get(key, 0) + 1

            for (icdo_code, report_name), count in hist_counts.items():
                pct = (count / total_valid_cases) * 100
                hist_dist_data.append({
                    "code": icdo_code,
                    "name": report_name,
                    "count": count,
                    "percentage": f"{pct:.1f}%",
                    "pct_val": pct
                })

            hist_dist_data.sort(key=lambda x: x["pct_val"], reverse=True)

            for item in hist_dist_data:
                item.pop("pct_val", None)

    return hist_dist_data

def analyze_dashboard_file(filename, cancers=[], year_start="", year_end="", behavior=""):
    fpath = f"{DASHBOARD_DATA}/{filename}"
    try:
        df = pd.read_excel(fpath)
        cols = get_column_names(df)
        
        df = filter_dashboard_data(df, cols, cancers, year_start, year_end, behavior)
        
        gender_age_data = calculate_gender_age_distribution(df, cols)
        age_median_data = calculate_age_median(df, cols)
        analyzable_confirmed_data = calculate_analyzable_confirmed_cases(df, cols)
        histology_data = calculate_histology_distribution(df, cols)
  
        return {
            "genderAgeData": gender_age_data,
            "ageMedianData": age_median_data,
            "analyzableConfirmedData": analyzable_confirmed_data,
            "histologyData": histology_data
        }
    except Exception as e:
        logging.error(f"error {filename}: {str(e)}")
        raise e