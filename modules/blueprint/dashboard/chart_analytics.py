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


def get_column_names(df):
    return {
        "gender_col": _find_column(df, ["sex", "性別"]),
        "age_col": _find_column(df, ["age", "診斷年齡", "年齡"]),
        "site_col": _find_column(df, ["site", "原發部位"]),
        "hist_col": _find_column(df, ["hist", "組織型態"]),
        "year_col": _find_column(df, ["didiag", "最初診斷日", "診斷日期"]),
        "behavior_col": _find_column(df, ["behavior", "性態碼"]),
        "ajcc_ed_col": _find_column(df, ["ajcc_ed", "ajcc edition", "ajcc版本"]),
    }

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

# 性別年齡分布
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

# 年齡中位數
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

def analyze_dashboard_file(filename, cancers=[], year_start="", year_end="", behavior=""):
    fpath = f"{DASHBOARD_DATA}/{filename}"
    try:
        df = pd.read_excel(fpath)
        cols = get_column_names(df)
        
        df = filter_dashboard_data(df, cols, cancers, year_start, year_end, behavior)
        
        gender_age_data = calculate_gender_age_distribution(df, cols)
        age_median_data = calculate_age_median(df, cols)
  
        return {
            "genderAgeData": gender_age_data,
            "ageMedianData": age_median_data
        }
    except Exception as e:
        logging.error(f"error {filename}: {str(e)}")
        raise e