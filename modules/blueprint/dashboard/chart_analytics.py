import os
import pandas as pd
import logging

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DASHBOARD_DATA = os.path.join(BASE_DIR, 'work', 'data')

def analyze_dashboard_file(filename):
    fpath = os.path.join(DASHBOARD_DATA, filename)
    if not os.path.exists(fpath):
        fpath = os.path.join(BASE_DIR, filename)
        if not os.path.exists(fpath):
            raise FileNotFoundError(f"找不到檔案: {filename}")

    try:
        df = pd.read_excel(fpath)
        gender_col = '1.5性別'
        age_col = '2.1診斷年齡'
        
        gender_age_data = []
        if gender_col in df.columns and age_col in df.columns:
            df_ga = df[[gender_col, age_col]].dropna()
            df_ga[age_col] = pd.to_numeric(df_ga[age_col], errors='coerce')
            df_ga = df_ga.dropna(subset=[age_col])
            bins = [0, 20, 40, 60, 80, 150]
            labels = ['0-19', '20-39', '40-59', '60-79', '80+']
            df_ga['AgeGroup'] = pd.cut(df_ga[age_col], bins=bins, labels=labels, right=False)
            counts = df_ga.groupby([gender_col, 'AgeGroup']).size().reset_index(name='Count')
            for _, row in counts.iterrows():
                if row['Count'] > 0:
                    gender_str = str(row[gender_col]).replace('1', '男').replace('2', '女')
                    name = f"{gender_str} {row['AgeGroup']}"
                    gender_age_data.append({"name": name, "value": int(row['Count'])})

        # --- 2. 常見癌症 ---
        site_col = '2.6原發部位'
        top_cancers = {"labels": [], "values": []}
        
        if site_col in df.columns:
            site_counts = df[site_col].value_counts().head(10)
            top_cancers["labels"] = site_counts.index.astype(str).tolist()
            top_cancers["values"] = site_counts.values.tolist()
            
        return {
            "genderAgeData": gender_age_data,
            "topCancersData": top_cancers
        }

    except Exception as e:
        logging.error(f"分析檔案失敗 {filename}: {str(e)}")
        raise e