import os
import pandas as pd
import logging
from modules.blueprint.dashboard.definition.cancer_grouping import classify_cancer_group

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DASHBOARD_DATA = os.path.join(BASE_DIR, 'tasks', 'data')

# --- 1.1 性別年齡分佈 ---
SEX_AGE_GROUPS = [
    {"label": "≤19", "min": 0, "max": 19},
    {"label": "20-24", "min": 20, "max": 24},
    {"label": "25-29", "min": 25, "max": 29},
    {"label": "30-34", "min": 30, "max": 34},
    {"label": "35-39", "min": 35, "max": 39},
    {"label": "40-44", "min": 40, "max": 44},
    {"label": "45-49", "min": 45, "max": 49},
    {"label": "50-54", "min": 50, "max": 54},
    {"label": "55-59", "min": 55, "max": 59},
    {"label": "60-64", "min": 60, "max": 64},
    {"label": "65-69", "min": 65, "max": 69},
    {"label": "70-74", "min": 70, "max": 74},
    {"label": "75-79", "min": 75, "max": 79},
    {"label": "80-84", "min": 80, "max": 84},
    {"label": "≥85", "min": 85, "max": None},
]

SEX_LABELS = {
    "1": "男性",
    "2": "女性",
}

SEX_AGE_CHART_COLORS = {
    "male": "#8ecae6",
    "female": "#f8b4c4",
    "total": "#f5b642",
}

CANCER_ID_RULE_MAP = {
    "Colorectal": {"group_key": "colon_and_rectum"},
    "Colon": {"group_key": "colon_and_rectum", "subgroup_key": "colon"},
    "Rectum": {"group_key": "colon_and_rectum", "subgroup_key": "rectum"},
    "lung_group": {"group_key": "lung_and_bronchus"},
    "Trachea": {"group_key": "lung_and_bronchus", "subgroup_key": "trachea"},
    "Lung": {"group_key": "lung_and_bronchus", "exclude_subgroup_keys": ["trachea"]},
    "small_cell_carcinoma": {"group_key": "lung_and_bronchus", "subgroup_key": "small_cell_carcinoma"},
    "adenocarcinoma": {"group_key": "lung_and_bronchus", "subgroup_key": "adenocarcinoma"},
    "squamous_cell_carcinoma": {"group_key": "lung_and_bronchus", "subgroup_key": "squamous_cell_carcinoma"},
}

def _match_sex_age_group(age):
    for group in SEX_AGE_GROUPS:
        min_age = group["min"]
        max_age = group["max"]

        if max_age is None and age >= min_age:
            return group["label"]

        if max_age is not None and min_age <= age <= max_age:
            return group["label"]

    return None

def _build_empty_sex_age_table(age_labels):
    zero_values = [0 for _ in age_labels]
    return [
        {"label": "男性", "values": zero_values.copy(), "total": 0},
        {"label": "女性", "values": zero_values.copy(), "total": 0},
        {"label": "總數", "values": zero_values.copy(), "total": 0},
        {"label": "百分比", "values": ["0.0%" for _ in age_labels], "total": "0.0%"},
    ]

def _format_number(value):
    if value is None or pd.isna(value):
        return "0"
    value = float(value)
    if value.is_integer():
        return str(int(value))
    return f"{value:.1f}"

def build_sex_age_distribution(df, gender_col, age_col):
    age_labels = [group["label"] for group in SEX_AGE_GROUPS]
    result = {
        "genderAgeData": [],
        "sexAgeTable": {
            "title": "性別年齡分佈",
            "ageLabels": age_labels,
            "rows": [],
            "chartSeries": [],
        }
    }

    if gender_col not in df.columns or age_col not in df.columns:
        return result

    work_df = df[[gender_col, age_col]].dropna().copy()
    work_df[gender_col] = work_df[gender_col].astype(str).str.strip()
    work_df[age_col] = pd.to_numeric(work_df[age_col], errors='coerce')
    work_df = work_df.dropna(subset=[age_col])

    if work_df.empty:
        result["sexAgeTable"]["rows"] = _build_empty_sex_age_table(age_labels)
        result["sexAgeTable"]["chartSeries"] = [
            {"name": "男性", "type": "bar", "data": [0 for _ in age_labels], "itemStyle": {"color": SEX_AGE_CHART_COLORS["male"]}},
            {"name": "女性", "type": "bar", "data": [0 for _ in age_labels], "itemStyle": {"color": SEX_AGE_CHART_COLORS["female"]}},
            {"name": "總計", "type": "line", "data": [0 for _ in age_labels], "itemStyle": {"color": SEX_AGE_CHART_COLORS["total"]}, "lineStyle": {"color": SEX_AGE_CHART_COLORS["total"]}},
        ]
        return result

    work_df["AgeGroup"] = work_df[age_col].apply(_match_sex_age_group)
    work_df = work_df.dropna(subset=["AgeGroup"])

    grouped_counts = (
        work_df.groupby([gender_col, "AgeGroup"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=age_labels, fill_value=0)
    )

    sex_counts = {}
    for sex_code, sex_label in SEX_LABELS.items():
        sex_counts[sex_label] = {
            label: int(grouped_counts.loc[sex_code, label]) if sex_code in grouped_counts.index else 0
            for label in age_labels
        }

    total_counts = {
        label: sum(sex_counts[sex_label][label] for sex_label in SEX_LABELS.values())
        for label in age_labels
    }
    grand_total = sum(total_counts.values())

    for sex_label, counts in sex_counts.items():
        for label in age_labels:
            if counts[label] > 0:
                result["genderAgeData"].append({
                    "name": f"{sex_label} {label}",
                    "value": counts[label],
                })

    result["sexAgeTable"]["rows"] = [
        {"label": "男性", "values": [sex_counts["男性"][label] for label in age_labels], "total": sum(sex_counts["男性"].values())},
        {"label": "女性", "values": [sex_counts["女性"][label] for label in age_labels], "total": sum(sex_counts["女性"].values())},
        {"label": "總數", "values": [total_counts[label] for label in age_labels], "total": grand_total},
        {
            "label": "百分比",
            "values": [
                f"{(total_counts[label] / grand_total * 100):.1f}%"
                if grand_total else "0.0%"
                for label in age_labels
            ],
            "total": "100.0%" if grand_total else "0.0%",
        },
    ]
    result["sexAgeTable"]["chartSeries"] = [
        {"name": "男性", "type": "bar", "data": [sex_counts["男性"][label] for label in age_labels], "itemStyle": {"color": SEX_AGE_CHART_COLORS["male"]}},
        {"name": "女性", "type": "bar", "data": [sex_counts["女性"][label] for label in age_labels], "itemStyle": {"color": SEX_AGE_CHART_COLORS["female"]}},
        {"name": "總計", "type": "line", "data": [total_counts[label] for label in age_labels], "itemStyle": {"color": SEX_AGE_CHART_COLORS["total"]}, "lineStyle": {"color": SEX_AGE_CHART_COLORS["total"]}},
    ]

    return result

# --- 1.2 性別年齡分佈 ---
def build_age_median_table(df, gender_col, age_col):
    result = {
        "title": "年齡中位數",
        "columns": ["男性", "女性"],
        "rows": [
            {"label": "個案數(人)", "values": [0, 0]},
            {"label": "年齡中位數", "values": ["0", "0"]},
            {"label": "性別比", "values": ["0", "0"]},
        ],
    }

    if gender_col not in df.columns or age_col not in df.columns:
        return result

    work_df = df[[gender_col, age_col]].dropna().copy()
    work_df[gender_col] = work_df[gender_col].astype(str).str.strip()
    work_df[age_col] = pd.to_numeric(work_df[age_col], errors="coerce")
    work_df = work_df.dropna(subset=[age_col])

    male_df = work_df[work_df[gender_col] == "1"]
    female_df = work_df[work_df[gender_col] == "2"]

    male_count = int(len(male_df))
    female_count = int(len(female_df))
    male_median = male_df[age_col].median() if male_count else None
    female_median = female_df[age_col].median() if female_count else None

    if female_count:
        male_ratio = round(male_count / female_count, 1)
        female_ratio = 1
    elif male_count:
        male_ratio = "NA"
        female_ratio = 0
    else:
        male_ratio = 0
        female_ratio = 0

    result["rows"] = [
        {"label": "個案數(人)", "values": [male_count, female_count]},
        {"label": "年齡中位數", "values": [_format_number(male_median), _format_number(female_median)]},
        {"label": "性別比", "values": [_format_number(male_ratio) if male_ratio != "NA" else "NA", _format_number(female_ratio)]},
    ]
    return result

def _find_column(df, candidates):
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None

def _matches_selected_cancer_group(classification, selected_rules):
    if not classification:
        return False

    for rule in selected_rules:
        if classification.get("group_key") != rule.get("group_key"):
            continue

        exclude_subgroup_keys = rule.get("exclude_subgroup_keys") or []
        if classification.get("subgroup_key") in exclude_subgroup_keys:
            continue

        subgroup_key = rule.get("subgroup_key")
        if not subgroup_key or classification.get("subgroup_key") == subgroup_key:
            return True

    return False

def _filter_by_cancer_ids(df, cancer_ids):
    cancer_ids = cancer_ids or []
    if not cancer_ids or "All_Cancers" in cancer_ids:
        return df

    selected_rules = [
        CANCER_ID_RULE_MAP[cancer_id]
        for cancer_id in cancer_ids
        if cancer_id in CANCER_ID_RULE_MAP
    ]
    if not selected_rules:
        return df.iloc[0:0].copy()

    site_col = _find_column(df, ["2.6原發部位"])
    hist_col = _find_column(df, ["2.8組織型態", "2.7組織型態", "2.7組織"])
    if not site_col or not hist_col:
        return df.iloc[0:0].copy()

    mask = df.apply(
        lambda row: _matches_selected_cancer_group(
            classify_cancer_group(row.get(site_col), row.get(hist_col)),
            selected_rules,
        ),
        axis=1,
    )
    return df[mask].copy()

def analyze_dashboard_file(filename, cancer_ids=None):
    fpath = os.path.join(DASHBOARD_DATA, filename)
    if not os.path.exists(fpath):
        fpath = os.path.join(BASE_DIR, filename)
        if not os.path.exists(fpath):
            raise FileNotFoundError(f"找不到檔案: {filename}")

    try:
        df = pd.read_excel(fpath)
        df = _filter_by_cancer_ids(df, cancer_ids)
        gender_col = '1.5性別'
        age_col = '2.1診斷年齡'
        sex_age_distribution = build_sex_age_distribution(df, gender_col, age_col)
        age_median_table = build_age_median_table(df, gender_col, age_col)

        # --- 2. 常見癌症 ---
        site_col = '2.6原發部位'
        top_cancers = {"labels": [], "values": []}
        
        if site_col in df.columns:
            site_counts = df[site_col].value_counts().head(10)
            top_cancers["labels"] = site_counts.index.astype(str).tolist()
            top_cancers["values"] = site_counts.values.tolist()
            
        return {
            "genderAgeData": sex_age_distribution["genderAgeData"],
            "sexAgeTable": sex_age_distribution["sexAgeTable"],
            "ageMedianTable": age_median_table,
            "topCancersData": top_cancers
        }

    except Exception as e:
        logging.error(f"分析檔案失敗 {filename}: {str(e)}")
        raise e
