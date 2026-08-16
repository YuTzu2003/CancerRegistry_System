import os
import re
import pandas as pd

NATIONAL_AGE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),"tasks", "data", "dashboard", "癌症年齡數據.xlsx")
REQUIRED_COLUMNS = ("年度", "癌別", "年齡", "合計", "男性", "女性")
NATIONAL_CANCER_BY_KEY = {
    "All_Cancers": None,
    "Oral_group": ["口腔癌", "口咽癌", "下咽癌"],
    "Oral_Cavity": ["口腔癌"],
    "Oropharynx": ["口咽癌"],
    "oropharynx_p16_positive": ["口咽癌"],
    "oropharynx_p16_negative": ["口咽癌"],
    "Hypopharynx": ["下咽癌"],
    "Salivary_Glands": ["主唾液腺癌"],
    "Nasopharynx": ["鼻咽癌"],
    "Larynx": ["喉癌"],
    "Esophagus": ["食道癌"],
    "Stomach": ["胃癌"],
    "Colon_and_Rectum_Anus": ["結腸癌", "直腸癌"],
    "Colon": ["結腸癌"],
    "Rectum": ["直腸癌"],
    "Liver_and_Intrahepatic_Bile_Duct": ["肝癌", "肝內膽管癌"],
    "Liver_and_Intrahepatic_bile_duct": ["肝癌", "肝內膽管癌"],
    "Liver": ["肝癌"],
    "Intrahepatic_bile_duct": ["肝內膽管癌"],
    "Pancreas": ["胰臟癌"],
    "Lung_and_Bronchus": ["肺癌"],
    "Lung_and_Bronchus_Trachea": ["肺癌"],
    "Breast": ["乳癌"],
    "Breast_Female": ["乳癌"],
    "Breast_Male": ["乳癌"],
    "Breast_invasive": ["乳癌"],
    "Cervix_Uteri": ["子宮頸癌"],
    "Cervix_invasive": ["子宮頸癌"],
    "Corpus_Uteri": ["子宮體癌"],
    "Ovary": ["卵巢癌"],
    "Prostate": ["攝護腺癌"],
    "Bladder": ["膀胱癌"],
    "Bladder_invasive": ["膀胱癌"],
    "Lymphoma": ["惡性淋巴瘤"],
}


def _normalize_cancer_name(value):
    return str(value or "").strip().replace("癌", "")


def _normalize_age_group(value):
    text = str(value or "").strip().replace(" ", "")
    match = re.search(r"(\d{1,2})-(\d{1,2})", text)
    if match:
        start, end = (int(part) for part in match.groups())
        if end <= 19:
            return "<=19"
        return f"{start}-{end}"
    if "以上" in text or text.startswith("85"):
        return ">=85"
    return text


def _read_national_age_data():
    data = pd.read_excel(NATIONAL_AGE_FILE, sheet_name="年齡")
    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        raise ValueError(f"全國癌症年齡資料缺少欄位：{', '.join(missing)}")

    data = data.loc[:, REQUIRED_COLUMNS].copy()
    data["年度"] = pd.to_numeric(data["年度"], errors="coerce")
    data = data.dropna(subset=["年度", "癌別", "年齡"])
    data["年度"] = data["年度"].astype(int)
    data["癌別"] = data["癌別"].astype(str).str.strip()
    data["_癌別比對"] = data["癌別"].map(_normalize_cancer_name)
    data["年齡"] = data["年齡"].astype(str).str.strip()
    for column in ("合計", "男性", "女性"):
        data[column] = pd.to_numeric(data[column], errors="coerce").fillna(0).astype(int)
    return data

def get_national_age_options():
    data = _read_national_age_data()
    years = sorted(data["年度"].unique().tolist())
    cancers_by_year = {
        str(year): sorted(data.loc[data["年度"] == year, "癌別"].unique().tolist())
        for year in years
    }
    return {"years": years, "cancers_by_year": cancers_by_year}


def get_national_age_preview(year_start="", year_end="", limit=10):
    data = _read_national_age_data()
    if year_start:
        start = int(year_start)
        end = int(year_end or year_start)
        data = data.loc[data["年度"].between(start, end)]
    return {"columns": list(REQUIRED_COLUMNS),"rows": data.head(limit).astype(str).values.tolist(),}


def get_national_age_side(year, cancers):
    data = _read_national_age_data()
    selected_keys = [str(value) for value in cancers or []]
    if "All_Cancers" in selected_keys:
        selected_cancers = data["_癌別比對"].unique().tolist()
    else:
        selected_cancers = []
        for key in selected_keys:
            selected_cancers.extend(NATIONAL_CANCER_BY_KEY.get(key, []))
        selected_cancers = list(dict.fromkeys(
            _normalize_cancer_name(cancer) for cancer in selected_cancers
        ))
    if not selected_cancers:
        raise ValueError("所選癌別沒有可對應的全國年齡資料")
    rows = data.loc[
        (data["年度"] == int(year)) & data["_癌別比對"].isin(selected_cancers),
        ["年齡", "合計", "男性", "女性"],
    ]
    if rows.empty:
        raise ValueError(f"{year} 年沒有所選癌別的全國年齡資料")
    rows = rows.copy()
    rows["年齡分組"] = rows["年齡"].map(_normalize_age_group)
    grouped = rows.groupby("年齡分組", sort=False)[["合計", "男性", "女性"]].sum().reset_index()
    gender_age_data = {
        "categories": grouped["年齡分組"].tolist(),
        "total": grouped["合計"].astype(int).tolist(),
        "male": grouped["男性"].astype(int).tolist(),
        "female": grouped["女性"].astype(int).tolist(),
    }
    total_count = int(grouped["合計"].sum())
    return {
        "filename": "全國癌症年齡統計資料",
        "years": [int(year)],
        "year_label": str(year),
        "year_start": str(year),
        "year_end": str(year),
        "year_count": 1,
        "total_count": total_count,
        "annual_average": total_count,
        "yearly_counts": {str(year): total_count},
        "male_count": int(grouped["男性"].sum()),
        "female_count": int(grouped["女性"].sum()),
        "median_age": 0,
        "analyzable_count": total_count,
        "confirmed_count": total_count,
        "confirmed_percent": "100.0%",
        "genderAgeData": gender_age_data,
    }


def compare_national_age_data(main_year, target_year, cancers):
    main = get_national_age_side(main_year, cancers)
    target = get_national_age_side(target_year, cancers)
    diff = target["total_count"] - main["total_count"]
    return {
        "main": {key: value for key, value in main.items() if key != "genderAgeData"},
        "target": {key: value for key, value in target.items() if key != "genderAgeData"},
        "analysis_data": {
            "main": {"genderAgeData": main["genderAgeData"]},
            "target": {"genderAgeData": target["genderAgeData"]},
            "items": ["性別年齡分佈"],
        },
        "compare_mode": "single",
        "diff": {
            "total_count": diff,
            "total_percent": f"{diff / main['total_count'] * 100:.1f}%" if main["total_count"] else "",
            "annual_average": diff,
        },
    }
