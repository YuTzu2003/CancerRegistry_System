"""Create a portable Power BI project from the annual report PBIP template."""

import base64
import json
import os
import shutil
import textwrap
import zipfile
from pathlib import Path

from .pbi_export import export_pbi_dataset


TOPIC_PAGES = {
    "性別年齡分佈": "性別年齡分布表&圖",
    "年齡中位數": "年齡中位數表",
    "可分析個案與確診個案": "可分析個案與確診個案\u200b表",
}


class PbipExportError(RuntimeError):
    pass


def _copy_project(template, project_dir, selected_pages):
    root = template.parent
    manifest = json.loads(template.read_text(encoding="utf-8-sig"))
    artifacts = manifest.get("artifacts") or []
    if len(artifacts) != 1:
        raise PbipExportError("PBIP 公版的報表設定不符合預期。")
    report_name = artifacts[0].get("report", {}).get("path")
    if not isinstance(report_name, str) or Path(report_name).name != report_name:
        raise PbipExportError("PBIP 公版的報表路徑不符合預期。")
    report_source = root / report_name
    reference = json.loads((report_source / "definition.pbir").read_text(encoding="utf-8-sig"))
    model_reference = reference.get("datasetReference", {}).get("byPath", {}).get("path")
    model_name = Path(model_reference or "").name
    if not model_name.endswith(".SemanticModel") or model_reference != f"../{model_name}":
        raise PbipExportError("PBIP 公版須使用同一資料夾內的語意模型。")
    model_source = root / model_name
    pages_source = report_source / "definition" / "pages"
    metadata = json.loads((pages_source / "pages.json").read_text(encoding="utf-8-sig"))
    page_order = metadata.get("pageOrder")
    if not isinstance(page_order, list) or not page_order:
        raise PbipExportError("PBIP 公版沒有可用的報表頁面。")
    page_names = {}
    for page_id in page_order:
        if not isinstance(page_id, str) or Path(page_id).name != page_id:
            raise PbipExportError("PBIP 公版的頁面識別碼不符合預期。")
        page = json.loads((pages_source / page_id / "page.json").read_text(encoding="utf-8-sig"))
        page_names[page_id] = page["displayName"]
    missing = selected_pages.difference(page_names.values())
    if missing:
        raise PbipExportError("PBIP 公版缺少分析頁面：" + "、".join(sorted(missing)))
    kept_ids = [page_id for page_id in page_order if page_names[page_id] in selected_pages]

    report_target = project_dir / report_name
    model_target = project_dir / model_name

    def ignore_local_state(path, names):
        ignored = set(names).intersection({"cache.abf", "localSettings.json"})
        if Path(path).resolve() == (report_source / "definition").resolve():
            ignored.add("pages")
        return ignored

    shutil.copytree(report_source, report_target, ignore=ignore_local_state)
    shutil.copytree(model_source, model_target, ignore=ignore_local_state)
    target_pages = report_target / "definition" / "pages"
    target_pages.mkdir()
    for page_id in kept_ids:
        shutil.copytree(pages_source / page_id, target_pages / page_id, ignore=ignore_local_state)
    metadata["pageOrder"] = kept_ids
    if metadata.get("activePageName") not in kept_ids:
        metadata["activePageName"] = kept_ids[0]
    (target_pages / "pages.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    shutil.copy2(template, project_dir / template.name)
    return model_target, kept_ids


def _embed_dataset(model_dir, excel_path):
    """Use an embedded Excel binary so the copied project has no machine path."""
    table_path = model_dir / "definition" / "tables" / "工作表1.tmdl"
    original = table_path.read_text(encoding="utf-8-sig")
    old_source = "Excel.Workbook(File.Contents(DataFilePath), null, true)"
    if original.count(old_source) != 1:
        raise PbipExportError("PBIP 公版的工作表1資料來源已變更，請重新確認公版。")
    encoded = base64.b64encode(excel_path.read_bytes()).decode("ascii")
    chunks = textwrap.wrap(encoded, 12000)
    value = (" &\n\t\t\t\t        ").join(f'"{chunk}"' for chunk in chunks)
    replacement = f"Excel.Workbook(Binary.FromText({value}, BinaryEncoding.Base64), null, true)"
    table_path.write_text(original.replace(old_source, replacement), encoding="utf-8")
    # The former path parameter remains part of the template's query metadata.
    # Clear its machine-specific value even though the data table no longer uses it.
    parameter_path = model_dir / "definition" / "expressions.tmdl"
    if parameter_path.is_file():
        parameter = parameter_path.read_text(encoding="utf-8-sig")
        lines = parameter.splitlines(keepends=True)
        for index, line in enumerate(lines):
            if line.startswith("expression DataFilePath = "):
                suffix = line[line.find(" meta ["):]
                lines[index] = 'expression DataFilePath = "內嵌資料"' + suffix
                break
        parameter_path.write_text("".join(lines), encoding="utf-8")


def create_filtered_pbip(source_path, output_dir, *, cancers, year_start, year_end, behavior, topics):
    unknown = set(topics).difference(TOPIC_PAGES)
    if not topics or unknown:
        raise PbipExportError("目前 PBIP 公版只支援：" + "、".join(TOPIC_PAGES))
    selected_pages = {TOPIC_PAGES[topic] for topic in topics}
    template = Path(os.getenv("PBI_PROJECT_TEMPLATE_PATH"))
    if not template.is_file():
        raise PbipExportError(f"找不到 PBIP 公版：{template}")

    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    project_dir = output_dir / "cancer_annual_report"
    project_dir.mkdir()
    excel_path = project_dir / "powerbi_dataset.xlsx"
    result = export_pbi_dataset(
        source_path, excel_path, cancers=cancers, year_start=year_start,
        year_end=year_end, behavior=behavior,
    )
    model_dir, kept_ids = _copy_project(template, project_dir, selected_pages)
    _embed_dataset(model_dir, excel_path)
    instructions = (
        "癌症年報 Power BI 專案\n\n"
        "1. 解壓縮整個檔案，資料夾內的檔案與子資料夾請一起保留。\n"
        f"2. 開啟 {template.name}。\n"
        "3. 在 Power BI Desktop 按『重新整理』，確認圖表顯示這次篩選的資料。\n"
        "4. 用『檔案 → 另存新檔』選擇 PBIX 格式，再自行上傳至 Report Server。\n\n"
        f"篩選資料：{result['rows']} 筆；保留圖表頁面：{len(kept_ids)} 頁。\n"
        "powerbi_dataset.xlsx 是本次篩選資料的獨立副本，可供核對。\n"
    )
    (project_dir / "使用說明.txt").write_text(instructions, encoding="utf-8-sig")
    archive_path = output_dir / "cancer_annual_report_pbip.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(project_dir.rglob("*")):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(output_dir))
    return {**result, "archive": str(archive_path), "pages": len(kept_ids)}
