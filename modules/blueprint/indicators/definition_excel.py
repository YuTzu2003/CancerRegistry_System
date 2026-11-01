"""Plain Excel template and import validation for indicator definitions.

Executable rules are stored in hidden columns on the same worksheet so users
can work in one simple table without losing the system's structured rules.
"""
from __future__ import annotations

from copy import deepcopy
from io import BytesIO
import json

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Side, Font
from openpyxl.utils import get_column_letter

from modules.blueprint.indicators.catalog import CANCER_SPECS, get_cancer_label
from modules.blueprint.indicators.indicator_definitions import get_indicator_metadata


DISPLAY_SHEET = "指標定義"
RULE_SHEET = "系統計算規則"
INFO_SHEET = "填寫說明"
DISPLAY_HEADERS = (
    "癌別", "指標編號", "指標屬性", "指標名稱", "選取理由",
    "分子定義", "分母定義", "癌登資料選用欄位（分子）", "癌登資料選用欄位（分母）", "備註",
)
RULE_HEADERS = ("癌別代碼", "指標編號", "分子規則 JSON", "分母規則 JSON")
INTERNAL_HEADERS = ("系統癌別代碼", "系統分子規則 JSON", "系統分母規則 JSON")


def _text(value):
    return str(value or "").strip()


def _metadata(cancer_key):
    return {item["id"]: item for item in get_indicator_metadata(cancer_key)}


def _rule_summary(rule):
    """Keep the reader-facing sheet useful without pretending it is executable."""
    fields = []

    def walk(node):
        if not isinstance(node, dict):
            return
        if node.get("field"):
            fields.append(str(node["field"]))
        for child in node.get("rules", []):
            walk(child)
        walk(node.get("rule"))

    walk(rule)
    return "、".join(dict.fromkeys(fields)) or "依系統規則設定"


def build_definition_workbook(definition, *, version_name, version_description=""):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = DISPLAY_SHEET
    sheet.freeze_panes = "A2"
    sheet.sheet_view.showGridLines = True
    sheet.append(DISPLAY_HEADERS)
    for index, header in enumerate(INTERNAL_HEADERS, len(DISPLAY_HEADERS) + 1):
        sheet.cell(row=1, column=index, value=header)
    # Keep the workbook visually plain: black text, white cells and ordinary
    # black cell borders. The implementation columns are hidden from users.
    edge = Side(style="thin", color="000000")
    plain_border = Border(left=edge, right=edge, top=edge, bottom=edge)

    sample = next(
        (
            (cancer_key, number, rule)
            for cancer_key in CANCER_SPECS
            for number, rule in sorted(definition.get(cancer_key, {}).items())
        ),
        None,
    )
    if sample:
        cancer_key, number, rule = sample
        item = _metadata(cancer_key).get(number, {})
        sheet.append((
            get_cancer_label(cancer_key),
            number,
            {"positive": "正向指標", "negative": "負向指標", "observation": "觀察指標"}.get(rule.get("type"), rule.get("type", "")),
            rule.get("name", ""),
            rule.get("selection_reason", item.get("selection_reason", "")),
            rule.get("numerator_definition", item.get("numerator_definition", "")),
            rule.get("denominator_definition", item.get("denominator_definition", "")),
            _rule_summary(rule.get("numerator")),
            _rule_summary(rule.get("denominator")),
            rule.get("notes", item.get("notes", "")),
        ))

    for row in sheet.iter_rows():
        for cell in row:
            cell.font = Font(name="Arial", color="000000", bold=cell.row == 1)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = plain_border
    widths = (20, 12, 16, 42, 34, 48, 48, 34, 34, 42)
    for index, width in enumerate(widths, 1):
        sheet.column_dimensions[get_column_letter(index)].width = width

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer


def _header_map(sheet):
    headers = {_text(cell.value): index for index, cell in enumerate(next(sheet.iter_rows(min_row=1, max_row=1), ()), 0)}
    required = ("指標編號", "指標名稱", "分子定義", "分母定義")
    missing = [header for header in required if header not in headers]
    if "癌別代碼" not in headers and "系統癌別代碼" not in headers and "癌別" not in headers:
        missing.append("癌別")
    if missing:
        raise ValueError("指標定義工作表缺少欄位：" + "、".join(missing) + "。")
    return headers


def _read_json_rule(value, label):
    try:
        rule = json.loads(_text(value))
    except json.JSONDecodeError as error:
        raise ValueError(f"{label} 不是有效的系統計算規則。請使用系統下載的 Excel 範本。") from error
    if not isinstance(rule, dict):
        raise ValueError(f"{label} 格式不正確。")
    return rule


def read_definition_workbook(uploaded_file, base_definition):
    """Return a full definition updated by a system-generated Excel template."""
    try:
        workbook = load_workbook(uploaded_file, read_only=True, data_only=True)
    except Exception as error:  # openpyxl normalizes several invalid-file errors.
        raise ValueError("無法讀取 Excel 檔案，請使用系統下載的 .xlsx 範本。") from error
    if DISPLAY_SHEET not in workbook.sheetnames:
        raise ValueError("Excel 檔案需包含「指標定義」工作表。")

    definition = deepcopy(base_definition)
    sheet = workbook[DISPLAY_SHEET]
    headers = _header_map(sheet)
    seen = set()
    for values in sheet.iter_rows(min_row=2, values_only=True):
        if not any(value not in (None, "") for value in values):
            continue
        cancer_code_header = "系統癌別代碼" if "系統癌別代碼" in headers else "癌別代碼"
        cancer_key = _text(values[headers[cancer_code_header]]) if cancer_code_header in headers else ""
        cancer_label = _text(values[headers["癌別"]]) if "癌別" in headers else ""
        if not cancer_key:
            cancer_key = next((key for key in CANCER_SPECS if get_cancer_label(key) == cancer_label), "")
        try:
            number = int(values[headers["指標編號"]])
        except (TypeError, ValueError):
            raise ValueError("指標編號必須是整數。") from None
        if cancer_key not in CANCER_SPECS or number not in definition.get(cancer_key, {}):
            raise ValueError(f"找不到 {cancer_key} 指標 {number}，請勿新增或變更範本中的癌別代碼與指標編號。")
        key = (cancer_key, number)
        if key in seen:
            raise ValueError(f"{get_cancer_label(cancer_key)} 指標 {number} 重複。")
        seen.add(key)
        rule = definition[cancer_key][number]
        for column, field in (("指標名稱", "name"), ("選取理由", "selection_reason"), ("分子定義", "numerator_definition"), ("分母定義", "denominator_definition"), ("備註", "notes")):
            if column not in headers:
                continue
            value = _text(values[headers[column]])
            if field in ("name", "numerator_definition", "denominator_definition") and not value:
                raise ValueError(f"{get_cancer_label(cancer_key)} 指標 {number} 的「{column}」不可空白。")
            if len(value) > 3000:
                raise ValueError(f"{get_cancer_label(cancer_key)} 指標 {number} 的「{column}」超過 3000 字。")
            rule[field] = value

    expected = {(cancer_key, number) for cancer_key, rules in definition.items() for number in rules}
    if not seen:
        raise ValueError("請先刪除範例列，再填入至少一項要匯入的指標。")

    # New sample templates contain only visible descriptions; executable
    # calculation rules are inherited from the selected base version. Continue
    # accepting older templates that stored rules in hidden columns or a tab.
    if all(header in headers for header in INTERNAL_HEADERS):
        rule_source = sheet
        rule_headers = {
            "癌別代碼": headers["系統癌別代碼"],
            "指標編號": headers["指標編號"],
            "分子規則 JSON": headers["系統分子規則 JSON"],
            "分母規則 JSON": headers["系統分母規則 JSON"],
        }
        rule_min_row = 2
    elif RULE_SHEET in workbook.sheetnames:
        rule_source = workbook[RULE_SHEET]
        rule_headers = {_text(cell.value): index for index, cell in enumerate(next(rule_source.iter_rows(min_row=1, max_row=1), ()), 0)}
        if any(header not in rule_headers for header in RULE_HEADERS):
            raise ValueError("系統計算規則工作表格式不正確。")
        rule_min_row = 2
    else:
        rule_source = None
        rule_headers = {}
        rule_min_row = 0
    seen_rules = set()
    for values in rule_source.iter_rows(min_row=rule_min_row, values_only=True) if rule_source else ():
        if not any(value not in (None, "") for value in values):
            continue
        cancer_key = _text(values[rule_headers["癌別代碼"]])
        try:
            number = int(values[rule_headers["指標編號"]])
        except (TypeError, ValueError):
            raise ValueError("系統計算規則的指標編號必須是整數。") from None
        key = (cancer_key, number)
        if key not in seen or key in seen_rules:
            raise ValueError("系統計算規則包含不正確或重複的癌別／指標編號。")
        seen_rules.add(key)
        definition[cancer_key][number]["numerator"] = _read_json_rule(values[rule_headers["分子規則 JSON"]], f"{get_cancer_label(cancer_key)} 指標 {number} 分子規則")
        definition[cancer_key][number]["denominator"] = _read_json_rule(values[rule_headers["分母規則 JSON"]], f"{get_cancer_label(cancer_key)} 指標 {number} 分母規則")
    if rule_source is not None and seen_rules != seen:
        raise ValueError("系統計算規則列與指標資料列不一致。")
    return definition
