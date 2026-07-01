import pandas as pd
from modules.blueprint.dashboard.definition.cancer_group_rules import CANCER_GROUP_RULES
from modules.blueprint.dashboard.definition.cancer_grouping import classify_cancer_group

file_path = "tasks/data/年報測試虛擬資料_Fake.xlsx"
output_path = "results.xlsx"

df = pd.read_excel(file_path)
site_col = "原發部位"
hist_col = "組織型態"

results = []

for idx, row in df.iterrows():
    site = row[site_col]
    hist = row[hist_col]
    result = classify_cancer_group(site, hist, rules=CANCER_GROUP_RULES)
    results.append({
        "原發部位": site,
        "組織型態": hist,
        "分類主群組": result["group_name"] if result else "未分類",
        "分類子群組": result["subgroup_name"] if result and result["subgroup_name"] else ""
    })

res_df = pd.DataFrame(results)
res_df.to_excel(output_path, index=False)
print(res_df.groupby(["分類主群組", "分類子群組"]).size().reset_index(name="數量"))