import os
import pandas as pd
import logging
from modules.blueprint.dashboard.definition.cancer_grouping import classify_cancer_group
from modules.blueprint.dashboard.definition.cancer_group_rules import CANCER_GROUP_RULES

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DASHBOARD_DATA = f"{BASE_DIR}/tasks/data"

def analyze_dashboard_file(filename, cancers=[], year_start="", year_end="", behavior=""):
    fpath = f"{DASHBOARD_DATA}/{filename}"
    if not os.path.exists(fpath):
        fpath = f"{BASE_DIR}/{filename}"
        if not os.path.exists(fpath):
            raise FileNotFoundError(f"找不到檔案: {filename} (嘗試過的路徑: {DASHBOARD_DATA})")

    try:
        df = pd.read_excel(fpath)
        gender_col = next((col for col in df.columns if '性別' in col), None)
        age_col = next((col for col in df.columns if '診斷年齡' in col), None)
        site_col = next((col for col in df.columns if '原發部位' in col), None)
        hist_col = next((col for col in df.columns if '組織型態' in col or '形態學' in col), None)
        year_col = next((col for col in df.columns if '最初診斷日' in col or '診斷日' in col or '診斷年份' in col), None)
        behavior_col = next((col for col in df.columns if '性態碼' in col or '行為碼' in col), None)
        
        # --- 年份篩選 ---
        if year_start and year_end and year_col:
            df['extracted_year'] = df[year_col].astype(str).str[:4]
            df['extracted_year'] = pd.to_numeric(df['extracted_year'], errors='coerce')
            df = df[(df['extracted_year'] >= int(year_start)) & (df['extracted_year'] <= int(year_end))]
            
        # --- 性態碼篩選 ---
        if behavior and behavior_col and behavior != 'all':
            df[behavior_col] = df[behavior_col].astype(str)
            df = df[df[behavior_col].str.startswith(str(behavior))]
            
        # --- 癌別篩選 ---
        if cancers and "All_Cancers" not in cancers and site_col and hist_col:
            def is_selected_cancer(row):
                res = classify_cancer_group(str(row[site_col]), str(row[hist_col]), CANCER_GROUP_RULES)
                if not res:
                    return False
                return res["group_key"] in cancers or res["subgroup_key"] in cancers           
            df = df[df.apply(is_selected_cancer, axis=1)]
        
        labels = ['<=19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49', '50-54', '55-59', '60-64', '65-69', '70-74', '75-79', '80-84', '>=85']
        
        gender_age_data = {
            "categories": labels,
            "male": [0] * len(labels),
            "female": [0] * len(labels),
            "total": [0] * len(labels)
        }

        age_median_data = {"male": 0, "female": 0, "total": 0}
        if gender_col in df.columns and age_col in df.columns:
            df_ga = df[[gender_col, age_col]].dropna()
            df_ga[age_col] = pd.to_numeric(df_ga[age_col], errors='coerce')
            df_ga = df_ga.dropna(subset=[age_col])
            df_ga[gender_col] = df_ga[gender_col].astype(str)
            
            # Median calculation
            m_df = df_ga[df_ga[gender_col].isin(['1', '1.0', '男'])]
            f_df = df_ga[df_ga[gender_col].isin(['2', '2.0', '女'])]
            
            age_median_data["male"] = round(m_df[age_col].median(), 1) if not m_df.empty else 0
            age_median_data["female"] = round(f_df[age_col].median(), 1) if not f_df.empty else 0
            age_median_data["total"] = round(df_ga[age_col].median(), 1) if not df_ga.empty else 0
            
            bins = [0, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 150]

            df_ga['AgeGroup'] = pd.cut(df_ga[age_col], bins=bins, labels=labels, right=False)
            
            for idx, label in enumerate(labels):
                m_count = len(df_ga[(df_ga['AgeGroup'] == label) & (df_ga[gender_col].isin(['1', '1.0', '男']))])
                f_count = len(df_ga[(df_ga['AgeGroup'] == label) & (df_ga[gender_col].isin(['2', '2.0', '女']))])
                gender_age_data["male"][idx] = m_count
                gender_age_data["female"][idx] = f_count
                gender_age_data["total"][idx] = m_count + f_count

        # --- 2. 常見癌症 ---
        top_cancers = {"labels": [], "values": []}
        
        if site_col and site_col in df.columns:
            site_counts = df[site_col].value_counts().head(10)
            top_cancers["labels"] = site_counts.index.astype(str).tolist()
            top_cancers["values"] = site_counts.values.tolist()
            
        return {
            "genderAgeData": gender_age_data,
            "ageMedianData": age_median_data,
            "topCancersData": top_cancers
        }

    except Exception as e:
        logging.error(f"分析檔案失敗 {filename}: {str(e)}")
        raise e