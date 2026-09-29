import logging
import os
import re
import shutil
import pandas as pd
from openpyxl import Workbook
from modules.blueprint.clean.field_mapping import get_field_map
from modules.services.db import get_conn
from modules.blueprint.clean.cleaner import FORMAT_RULES_MAP

DUPLICATE_COMPARISON_FIELDS = ( "病歷號碼", "身分證統一編號", "癌症發生順序號碼", "最初診斷日期", "原發部位",)

def get_duplicate_comparison_columns(fmt_name, headers, alias_to_target=None):
    fmt_key = f"fmt_{str(fmt_name).replace('fmt_', '')}"
    rules = FORMAT_RULES_MAP.get(fmt_key, {})
    expected = {
        field_name: f"{rules[field_name]['ID']}{field_name}"
        for field_name in DUPLICATE_COMPARISON_FIELDS
        if field_name in rules
    }
    if len(expected) != len(DUPLICATE_COMPARISON_FIELDS):
        raise ValueError("目前資料格式缺少重複資料比對欄位")

    alias_to_target = alias_to_target if alias_to_target is not None else get_field_map("field_name_zh", fmt_name)
    normalized_targets = {re.sub(r"\s+", "", str(target)): field_name for field_name, target in expected.items()}
    resolved = {}
    for header in headers:
        text = str(header).strip()
        target = alias_to_target.get(text, text)
        field_name = normalized_targets.get(re.sub(r"\s+", "", str(target)))
        if field_name and field_name not in resolved:
            resolved[field_name] = header
    missing = [field_name for field_name in DUPLICATE_COMPARISON_FIELDS if field_name not in resolved]
    if missing:
        raise ValueError(f"缺少重複資料比對欄位：{'、'.join(missing)}")
    return resolved

def normalize_duplicate_value(value):
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", "", str(value)).upper()

def get_duplicate_keys(dataframe, columns):
    keys = set()
    for _, row in dataframe.iterrows():
        key = tuple(normalize_duplicate_value(row[columns[field_name]]) for field_name in DUPLICATE_COMPARISON_FIELDS)
        if all(key):
            keys.add(key)
    return keys

def exclude_reviewed_rows(dataframe, reference_keys, columns):
    duplicate_rows = dataframe.apply(
        lambda row: all(normalize_duplicate_value(row[columns[field_name]]) for field_name in DUPLICATE_COMPARISON_FIELDS)
        and tuple(normalize_duplicate_value(row[columns[field_name]]) for field_name in DUPLICATE_COMPARISON_FIELDS) in reference_keys,
        axis=1,)
    return dataframe.loc[~duplicate_rows].copy(), int(duplicate_rows.sum())

def create_empty_cleaning_result(dataframe, output_file, report_file):
    error_mask = pd.DataFrame("", index=dataframe.index, columns=dataframe.columns)
    result_df = dataframe.copy()
    result_df["錯誤類型(A:遺漏值 B:格式不符 C:日期格式錯誤 D:邏輯錯誤)"] = ""
    result_df.to_excel(output_file, index=False, engine="openpyxl")

    report = Workbook()
    report.active.title = "資料清洗報告"
    report.active.append(["資料總件數", 0])
    report.save(report_file)
    report.close()
    return {
        "total": 0,
        "error_rows": 0,
        "completeness": 0,
        "correctness": 0,
        "consistency": 0,
        "quality_score": 0,
        "missing_cells": 0,
        "format_cells": 0,
        "logic_cells": 0,
    }, {}, result_df, error_mask


def get_review_records_logic(user_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""SELECT Job.JobID, Job.FileName, Job.TotalCount, Job.CreatedAt, DataFormat.FmtName, DataFormat.Version
                    FROM Job JOIN DataFormat ON Job.FmtID = DataFormat.FmtID
                    WHERE Job.UserID = ? AND Job.CreatedAt >= DATEADD(month, -3, GETDATE())
                    ORDER BY Job.CreatedAt DESC""",(user_id,),)
    records = [
        {
            "job_id": str(row.JobID),
            "file_name": row.FileName,
            "total_count": row.TotalCount,
            "created_at": row.CreatedAt.strftime("%Y/%m/%d %H:%M") if row.CreatedAt else "",
            "format": str(row.FmtName),
            "version": row.Version,
        }
        for row in cursor.fetchall()
    ]
    conn.close()
    return {"ok": True, "records": records}, 200

def cleanup_expired_review_records():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT JobID, [Path] FROM Job WHERE CreatedAt < DATEADD(month, -3, GETDATE())")
    expired_records = cursor.fetchall()
    if not expired_records:
        conn.close()
        return 0

    job_ids = [row.JobID for row in expired_records]
    placeholders = ", ".join("?" for job_id in job_ids)
    cursor.execute(f"DELETE FROM Job WHERE JobID IN ({placeholders})", job_ids)
    conn.commit()
    conn.close()

    jobs_root = os.path.abspath(os.path.join("tasks", "Jobs"))
    for job_id, project_path in expired_records:
        path = os.path.abspath(str(project_path or ""))
        try:
            if path and os.path.commonpath((jobs_root, path)) == jobs_root and os.path.isdir(path):
                shutil.rmtree(path)
        except OSError:
            logging.exception("Unable to delete expired review record files: %s", path)
    logging.info("Deleted %s expired review records", len(expired_records))
    return len(expired_records)


def get_selected_review_duplicate_keys(user_id, review_job_ids):
    unique_job_ids = list(dict.fromkeys(job_id for job_id in review_job_ids if job_id))
    if not unique_job_ids:
        return set()

    conn = get_conn()
    cursor = conn.cursor()
    placeholders = ", ".join("?" for job_id in unique_job_ids)
    cursor.execute(f"""SELECT Job.JobID, Job.Path, Job.FileName, DataFormat.FmtName
                    FROM Job JOIN DataFormat ON Job.FmtID = DataFormat.FmtID
                    WHERE Job.UserID = ? AND Job.CreatedAt >= DATEADD(month, -3, GETDATE())
                    AND Job.JobID IN ({placeholders})""",[user_id, *unique_job_ids],)
    review_records = cursor.fetchall()
    conn.close()
    if len(review_records) != len(unique_job_ids):
        raise ValueError("選取的資料審核紀錄不存在或已超過保存期限")

    reference_keys = set()
    for record in review_records:
        base_name = os.path.splitext(record.FileName)[0]
        cleaned_file = os.path.join(record.Path, f"fmt{record.FmtName}_{base_name}_Clean.xlsx")
        if not os.path.exists(cleaned_file):
            raise ValueError(f"找不到資料審核紀錄的清洗檔案：{record.FileName}")
        reference_df = pd.read_excel(cleaned_file, dtype=str)
        reference_columns = get_duplicate_comparison_columns(record.FmtName, reference_df.columns)
        reference_keys.update(get_duplicate_keys(reference_df, reference_columns))
    return reference_keys