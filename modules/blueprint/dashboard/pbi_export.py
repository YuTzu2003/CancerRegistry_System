"""Prepare a Power BI-friendly annual-report dataset from an uploaded Excel file."""

import os
import re
import uuid

from pathlib import Path

import pandas as pd

from .definition.cancer_grouping import classify_cancer_group


# The existing PBIX query expects registry names without numeric IDs.
_PBIX_HEADER_ALIASES = {
    "臨床 T": "臨床T",
    "臨床 N": "臨床N",
    "臨床 M": "臨床M",
    "病理 T": "病理T",
    "病理 N": "病理N",
    "病理 M": "病理M",
    "其他分期系統期別(臨床分期)": "其他分期系統期別(臨床分期)\n",
    "未放射治療原因/放射治療執行狀態": "放射治療執行狀態",
}

# The current PBIX template imports these registry codes as whole numbers,
# although the registry permits text codes (for example, surgical margin "D"
# and smoking status "99,99,99"). Keep the source workbook intact and make
# only the generated Power BI dataset compatible with that fixed template.
_PBIX_INTEGER_FIELDS = {
    "申報醫院原發部位手術方式",
    "原發部位手術邊緣",
    "吸菸行為",
    "嚼檳榔行為",
}


def _pbix_column_name(column):
    name = re.sub(r"^\d+(?:\.\d+)*\.?\s*", "", str(column))
    return _PBIX_HEADER_ALIASES.get(name, name)


def _coerce_template_integer_fields(frame):
    """Blank non-numeric values only in fields the existing PBIX types as Int64."""
    for column in _PBIX_INTEGER_FIELDS.intersection(frame.columns):
        numeric = pd.to_numeric(frame[column], errors="coerce")
        has_value = frame[column].notna() & frame[column].astype(str).str.strip().ne("")
        frame.loc[has_value & numeric.isna(), column] = None
    return frame


def _text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def _find_column(df, candidates):
    for column in df.columns:
        column_text = str(column).strip().lower()
        if any(candidate.lower() in column_text for candidate in candidates):
            return column
    return None


def _get_source_columns(df):
    """Recognize the same canonical and Chinese headers accepted by Dashboard."""
    return {
        "gender_col": _find_column(df, ["sex", "性別"]),
        "age_col": _find_column(df, ["age", "診斷年齡"]),
        "site_col": _find_column(df, ["site", "原發部位"]),
        "hist_col": _find_column(df, ["hist", "組織型態"]),
        "year_col": _find_column(df, ["didiag", "最初診斷日期", "診斷年度"]),
        "behavior_col": _find_column(df, ["behavior", "性態碼"]),
        "ajcc_ed_col": _find_column(df, ["ajcc_ed", "ajcc 癌症分期版本與章節"]),
    }


def _filter_selected_rows(df, columns, cancers, year_start, year_end, behavior):
    result = df.copy()
    year_col = columns.get("year_col")
    behavior_col = columns.get("behavior_col")
    site_col = columns["site_col"]
    hist_col = columns["hist_col"]
    ajcc_ed_col = columns.get("ajcc_ed_col")
    gender_col = columns.get("gender_col")

    # Keep these expressions aligned with ``filter_dashboard_data``.  In
    # particular, the dashboard takes the first four displayed characters of
    # the diagnosis date and uses a prefix match for behavior, rather than
    # normalizing the values first.
    if year_col and year_start and year_end:
        extracted_year = pd.to_numeric(
            result[year_col].astype(str).str[:4], errors="coerce"
        )
        result = result[
            (extracted_year >= int(year_start))
            & (extracted_year <= int(year_end))
        ]
    if behavior_col and behavior and behavior != "all":
        result = result.copy()
        result[behavior_col] = result[behavior_col].astype(str)
        result = result[result[behavior_col].str.startswith(str(behavior))]
    if cancers and "All_Cancers" not in cancers:
        selected = set(cancers)

        def matches_selected_cancer(row):
            cancer = classify_cancer_group(
                str(row[site_col]), str(row[hist_col]),
                behavior=str(row[behavior_col]) if behavior_col else None,
                didiag=str(row[year_col]) if year_col else None,
                ajcc_ed=str(row[ajcc_ed_col]) if ajcc_ed_col else None,
                sex=str(row[gender_col]) if gender_col else None,
            )
            if not cancer:
                return False
            matched_keys = {
                cancer["group_key"], cancer.get("subgroup_key"),
                *cancer.get("ancestor_subgroup_keys", []),
            }
            return bool(matched_keys.intersection(selected))

        result = result[result.apply(matches_selected_cancer, axis=1)]
    return result


def _diagnosis_year(value):
    digits = "".join(re.findall(r"\d", _text(value)))
    return int(digits[:4]) if len(digits) >= 4 else None


def _behavior_code(value):
    text = _text(value)
    return text[:1] if text else ""


def _sex_label(value):
    text = _text(value)
    if text in {"1", "1.0"}:
        return "男"
    if text in {"2", "2.0"}:
        return "女"
    return "未知"


def _age_group(value):
    age = pd.to_numeric(value, errors="coerce")
    if pd.isna(age):
        return "未知", 999
    age = int(age)
    if age <= 19:
        return "≤19", 0
    if age >= 85:
        return "≥85", 85
    start = (age // 5) * 5
    return f"{start:02d}-{start + 4:02d}", start


def export_pbi_dataset(source_path, output_path, cancers=None, year_start="", year_end="", behavior=""):
    """Export source Excel with reusable Power BI helper columns.

    The original Excel remains unchanged. Cancer grouping is calculated with the
    same ``cancer_group_rules.py`` logic used by the Flask dashboard.
    """
    source = Path(source_path).resolve()
    output = Path(output_path).resolve()
    if source == output:
        raise ValueError("PBI 輸出檔不可覆蓋原始年報檔案。")
    if not source.is_file():
        raise FileNotFoundError(f"找不到原始年報檔案：{source}")

    df = pd.read_excel(source)
    columns = _get_source_columns(df)
    required = {"site_col": "site／原發部位", "hist_col": "hist／組織型態"}
    missing = [label for key, label in required.items() if not columns.get(key)]
    if missing:
        raise ValueError(f"缺少必要欄位：{'、'.join(missing)}")

    cancers = list(cancers or ["All_Cancers"])
    df = _filter_selected_rows(df, columns, cancers, year_start, year_end, behavior)
    if df.empty:
        raise ValueError("目前篩選條件沒有符合資料，未更新 Power BI 發布檔。")

    site_col = columns["site_col"]
    hist_col = columns["hist_col"]
    behavior_col = columns.get("behavior_col")
    year_col = columns.get("year_col")
    ajcc_ed_col = columns.get("ajcc_ed_col")
    gender_col = columns.get("gender_col")
    age_col = columns.get("age_col")

    derived_rows = []
    for _, row in df.iterrows():
        cancer = classify_cancer_group(
            row[site_col],
            row[hist_col],
            behavior=row[behavior_col] if behavior_col else None,
            didiag=row[year_col] if year_col else None,
            ajcc_ed=row[ajcc_ed_col] if ajcc_ed_col else None,
            sex=row[gender_col] if gender_col else None,
        )
        age_group, age_group_sort = _age_group(row[age_col]) if age_col else ("未知", 999)
        derived_rows.append({
            "CancerGroupKey": cancer.get("subgroup_key") or cancer.get("group_key") if cancer else "",
            "CancerGroupName": cancer.get("subgroup_name") or cancer.get("group_name") if cancer else "未分類",
            "CancerParentGroupKey": cancer.get("group_key") if cancer else "",
            "CancerParentGroupName": cancer.get("group_name") if cancer else "未分類",
            "DiagnosisYear": _diagnosis_year(row[year_col]) if year_col else None,
            "BehaviorCode": _behavior_code(row[behavior_col]) if behavior_col else "",
            "SexLabel": _sex_label(row[gender_col]) if gender_col else "未知",
            "AgeGroup": age_group,
            "AgeGroupSort": age_group_sort,
        })

    derived_columns = [
        "CancerGroupKey", "CancerGroupName", "CancerParentGroupKey", "CancerParentGroupName",
        "DiagnosisYear", "BehaviorCode", "SexLabel", "AgeGroup", "AgeGroupSort",
    ]
    result = pd.concat(
        [df.reset_index(drop=True), pd.DataFrame(derived_rows, columns=derived_columns)],
        axis=1,
    )
    translated = [_pbix_column_name(column) for column in result.columns]
    if len(translated) != len(set(translated)):
        raise ValueError("年報欄位轉換後出現重複名稱，無法提供給 Power BI 公版。")
    result.columns = translated
    result = _coerce_template_integer_fields(result)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.stem}.{uuid.uuid4().hex}.tmp.xlsx")
    try:
        with pd.ExcelWriter(temporary, engine="openpyxl") as writer:
            # Match the existing source workbook's main sheet name so the
            # published PBIX only needs a path change, not query remapping.
            result.to_excel(writer, sheet_name="Sheet1", index=False)
            pd.DataFrame([{
                "YearStart": year_start,
                "YearEnd": year_end,
                "BehaviorCode": behavior,
                "CancerKeys": ",".join(cancers),
                "PublishedAt": pd.Timestamp.now(),
            }]).to_excel(writer, sheet_name="ReportMeta", index=False)
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()

    return {
        "source": str(source),
        "output": str(output),
        "rows": len(result),
        "classified_rows": int((result["CancerGroupKey"] != "").sum()),
    }
