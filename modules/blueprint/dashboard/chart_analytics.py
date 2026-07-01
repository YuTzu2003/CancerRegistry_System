import os
import pandas as pd
import logging

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DASHBOARD_DATA = os.path.join(BASE_DIR, 'tasks', 'data')
ANNUAL_AGE_LABELS = ['≤19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49', '50-54', '55-59', '60-64', '65-69', '70-74', '75-79', '80-84', '≥85']
ANNUAL_AGE_BINS = [0, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 150]

def _build_sex_age_table(df, gender_col, age_col):
    result = {
        "title": "性別年齡分佈",
        "ageLabels": ANNUAL_AGE_LABELS,
        "rows": [],
        "chartSeries": [],
    }

    if gender_col not in df.columns or age_col not in df.columns:
        return result

    df_ga = df[[gender_col, age_col]].dropna().copy()
    df_ga[age_col] = pd.to_numeric(df_ga[age_col], errors='coerce')
    df_ga = df_ga.dropna(subset=[age_col])
    if df_ga.empty:
        return result

    df_ga['AgeGroup'] = pd.cut(
        df_ga[age_col],
        bins=ANNUAL_AGE_BINS,
        labels=ANNUAL_AGE_LABELS,
        right=False,
        include_lowest=True,
    )

    df_ga['GenderCode'] = df_ga[gender_col].astype(str).str.strip()
    grouped_counts = (
        df_ga.groupby(['GenderCode', 'AgeGroup'], observed=False)
        .size()
        .unstack(fill_value=0)
        .reindex(columns=ANNUAL_AGE_LABELS, fill_value=0)
    )

    male_counts = {label: int(grouped_counts.loc['1', label]) if '1' in grouped_counts.index else 0 for label in ANNUAL_AGE_LABELS}
    female_counts = {label: int(grouped_counts.loc['2', label]) if '2' in grouped_counts.index else 0 for label in ANNUAL_AGE_LABELS}
    total_counts = {
        label: male_counts.get(label, 0) + female_counts.get(label, 0)
        for label in ANNUAL_AGE_LABELS
    }
    grand_total = sum(total_counts.values())
    percent_counts = {
        label: f"{(total_counts[label] / grand_total * 100):.1f}%" if grand_total else "0.0%"
        for label in ANNUAL_AGE_LABELS
    }

    result["rows"] = [
        {"label": "男性", "values": [male_counts[label] for label in ANNUAL_AGE_LABELS], "total": sum(male_counts.values())},
        {"label": "女性", "values": [female_counts[label] for label in ANNUAL_AGE_LABELS], "total": sum(female_counts.values())},
        {"label": "總數", "values": [total_counts[label] for label in ANNUAL_AGE_LABELS], "total": grand_total},
        {"label": "百分比", "values": [percent_counts[label] for label in ANNUAL_AGE_LABELS], "total": "100.0%" if grand_total else "0.0%"},
    ]
    result["chartSeries"] = [
        {"name": "男性", "type": "bar", "data": [male_counts[label] for label in ANNUAL_AGE_LABELS]},
        {"name": "女性", "type": "bar", "data": [female_counts[label] for label in ANNUAL_AGE_LABELS]},
        {"name": "總計", "type": "line", "data": [total_counts[label] for label in ANNUAL_AGE_LABELS]},
    ]
    return result

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
        sex_age_table = _build_sex_age_table(df, gender_col, age_col)

        # --- 2. 常見癌症 ---
        site_col = '2.6原發部位'
        top_cancers = {"labels": [], "values": []}
        
        if site_col in df.columns:
            site_counts = df[site_col].value_counts().head(10)
            top_cancers["labels"] = site_counts.index.astype(str).tolist()
            top_cancers["values"] = site_counts.values.tolist()
            
        return {
            "genderAgeData": gender_age_data,
            "sexAgeTable": sex_age_table,
            "topCancersData": top_cancers
        }

    except Exception as e:
        logging.error(f"分析檔案失敗 {filename}: {str(e)}")
        raise e
