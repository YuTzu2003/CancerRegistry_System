from flask import Blueprint, flash, redirect, render_template, request, url_for
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from zipfile import BadZipFile
from modules.services.auth import login_required
from modules.services.db import get_conn

histology_mapping_bp = Blueprint("histology_mapping",__name__,template_folder="templates",)

_COLUMN_LABELS = {
    "codeyear": "年度",
    "code_year": "年度",
    "cancergroupkey": "癌別群組",
    "cancer_group_key": "癌別群組",
    "cancergroup_zh": "癌別(中)",
    "cancergroup_en": "癌別(英)",
    "histcode": "性態碼",
    "hist": "性態碼",
    "behaviorcode": "行為碼",
    "behavior": "行為碼",
    "histologyzh": "組織型態(中)",
    "hist_zh": "組織型態(中)",
    "histologyen": "組織型態(英)",
    "hist_en": "組織型態(英)",
    "behavior_en": "組織型態(英)",
    "histology": "組織型態(英)",
    "siteinclude": "納入部位",
    "site_include": "納入部位",
    "siteexclude": "排除部位",
    "site_exclude": "排除部位",
}

_DISPLAY_COLUMN_NAMES = (
    "codeyear",
    "cancergroup_zh",
    "cancergroup_en",
    "hist",
    "behavior",
    "hist_zh",
    "hist_en",
)

_IMPORT_COLUMNS = (
    "CodeYear",
    "CancerGroupKey",
    "CancerGroup_zh",
    "CancerGroup_en",
    "hist",
    "behavior",
    "hist_zh",
    "hist_en",
)


def _quote_identifier(identifier):
    return f"[{identifier.replace(']', ']]')}]"


def _code_year_column(columns):
    return next((column for column in columns if column.lower() in {"codeyear", "code_year"}), None)


def _year_sort_key(year):
    try:
        return 0, int(str(year))
    except (TypeError, ValueError):
        return 1, str(year)


def _get_mapping_data(search_column="", search_query="", selected_year=""):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT TOP 0 * FROM dbo.histology_code_mapping")
        columns = [column[0] for column in cursor.description]
        query = "SELECT * FROM dbo.histology_code_mapping"
        conditions = []
        parameters = []
        code_year_column = _code_year_column(columns)
        if selected_year and code_year_column:
            conditions.append(f"{_quote_identifier(code_year_column)} = ?")
            parameters.append(selected_year)
        search_query = search_query.strip()
        if search_query:
            searchable_columns = [search_column] if search_column in columns else columns
            expression = " + N' ' + ".join(
                f"COALESCE(CONVERT(NVARCHAR(MAX), {_quote_identifier(column)}), N'')"
                for column in searchable_columns
            )
            conditions.append(f"({expression}) LIKE ?")
            parameters.append(f"%{search_query}%")
        if conditions:
            query += f" WHERE {' AND '.join(conditions)}"
        cursor.execute(query, *parameters)
        return columns, [tuple(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def _primary_key(columns):
    return next((column for column in columns if column.lower() == "histcode_id"), None)


def _return_to_mapping():
    return redirect(url_for("histology_mapping.histology_code_mapping"))


def _read_import_rows(uploaded_file):
    workbook = load_workbook(uploaded_file, read_only=True, data_only=True)
    try:
        worksheet = workbook.active
        headers = tuple(cell.value for cell in next(worksheet.iter_rows(max_row=1)))
        if headers != _IMPORT_COLUMNS:
            raise ValueError("Excel 欄位須完全符合組織型態表範本。")

        rows = []
        for row_number, values in enumerate(worksheet.iter_rows(min_row=2, values_only=True), start=2):
            if all(value is None or str(value).strip() == "" for value in values):
                continue
            if any(value is None or str(value).strip() == "" for value in values):
                raise ValueError(f"第 {row_number} 列有未填寫欄位。")
            rows.append(tuple(str(value).strip() for value in values))
        if not rows:
            raise ValueError("Excel 沒有可新增的資料。")
        return rows
    finally:
        workbook.close()


@histology_mapping_bp.route("/dashboard/histology-code-mapping")
@login_required
def histology_code_mapping():
    search_column = request.args.get("column", "")
    search_query = request.args.get("q", "")
    edit_id = request.args.get("edit_id", "")
    columns, all_rows = _get_mapping_data()
    code_year_column = _code_year_column(columns)
    year_index = columns.index(code_year_column) if code_year_column else None
    available_years = sorted(
        {str(row[year_index]) for row in all_rows if row[year_index] is not None},
        key=_year_sort_key,
        reverse=True,
    )
    requested_year = request.args.get("year", "")
    selected_year = requested_year if requested_year in available_years else (available_years[0] if available_years else "")
    columns, rows = _get_mapping_data(search_column, search_query, selected_year)
    selected_year_count = sum(
        1 for row in all_rows if year_index is not None and str(row[year_index]) == selected_year
    )
    primary_key = _primary_key(columns)
    editing_row = None
    if edit_id and primary_key:
        key_index = columns.index(primary_key)
        editing_row = next((row for row in rows if str(row[key_index]) == edit_id), None)
    return render_template(
        "histology_code_mapping.html",
        active="histology_code_mapping",
        columns=columns,
        display_columns=[
            column for name in _DISPLAY_COLUMN_NAMES for column in columns if column.lower() == name
        ],
        column_labels={column: _COLUMN_LABELS.get(column.lower(), column) for column in columns},
        rows=rows,
        available_years=available_years,
        selected_year=selected_year,
        selected_year_count=selected_year_count,
        primary_key=primary_key,
        editable_columns=[column for column in columns if column != primary_key],
        search_column=search_column if search_column in columns else "",
        search_query=search_query,
        editing_row=editing_row,
    )


@histology_mapping_bp.route("/dashboard/histology-code-mapping/create", methods=["POST"])
@login_required
def create_histology_code_mapping():
    columns, _ = _get_mapping_data()
    editable_columns = [column for column in columns if column != _primary_key(columns)]
    values = [request.form.get(column, "") for column in editable_columns]
    conn = get_conn()
    try:
        cursor = conn.cursor()
        fields = ", ".join(_quote_identifier(column) for column in editable_columns)
        placeholders = ", ".join("?" for _ in editable_columns)
        cursor.execute(f"INSERT INTO dbo.histology_code_mapping ({fields}) VALUES ({placeholders})", *values)
        conn.commit()
    finally:
        conn.close()
    flash("組織型態資料已新增。", "success")
    return _return_to_mapping()


@histology_mapping_bp.route("/dashboard/histology-code-mapping/import", methods=["POST"])
@login_required
def import_histology_code_mapping():
    uploaded_file = request.files.get("import_file")
    if not uploaded_file or not uploaded_file.filename:
        flash("請選擇組織型態表 Excel 檔案。", "danger")
        return _return_to_mapping()
    if not uploaded_file.filename.lower().endswith(".xlsx"):
        flash("僅接受 .xlsx 格式的組織型態表。", "danger")
        return _return_to_mapping()

    try:
        rows = _read_import_rows(uploaded_file)
    except (ValueError, OSError, KeyError, BadZipFile, InvalidFileException) as error:
        flash(str(error), "danger")
        return _return_to_mapping()

    columns, _ = _get_mapping_data()
    editable_columns = [column for column in columns if column != _primary_key(columns)]
    if tuple(editable_columns) != _IMPORT_COLUMNS:
        flash("資料庫欄位與組織型態表範本不一致，無法匯入。", "danger")
        return _return_to_mapping()

    conn = get_conn()
    try:
        cursor = conn.cursor()
        fields = ", ".join(_quote_identifier(column) for column in editable_columns)
        placeholders = ", ".join("?" for _ in editable_columns)
        cursor.executemany(
            f"INSERT INTO dbo.histology_code_mapping ({fields}) VALUES ({placeholders})",
            rows,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    flash(f"已新增 {len(rows)} 筆組織型態資料。", "success")
    return _return_to_mapping()


@histology_mapping_bp.route("/dashboard/histology-code-mapping/<int:histcode_id>/update", methods=["POST"])
@login_required
def update_histology_code_mapping(histcode_id):
    columns, _ = _get_mapping_data()
    primary_key = _primary_key(columns)
    if not primary_key:
        return "histology_code_mapping 缺少 HistCode_ID 主鍵", 500
    editable_columns = [column for column in columns if column != primary_key]
    values = [request.form.get(column, "") for column in editable_columns]
    assignments = ", ".join(f"{_quote_identifier(column)} = ?" for column in editable_columns)
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE dbo.histology_code_mapping SET {assignments} WHERE {_quote_identifier(primary_key)} = ?",
            *values,
            histcode_id,
        )
        conn.commit()
    finally:
        conn.close()
    flash("組織型態資料已更新。", "success")
    return _return_to_mapping()


@histology_mapping_bp.route("/dashboard/histology-code-mapping/<int:histcode_id>/delete", methods=["POST"])
@login_required
def delete_histology_code_mapping(histcode_id):
    columns, _ = _get_mapping_data()
    primary_key = _primary_key(columns)
    if not primary_key:
        return "histology_code_mapping 缺少 HistCode_ID 主鍵", 500
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"DELETE FROM dbo.histology_code_mapping WHERE {_quote_identifier(primary_key)} = ?",
            histcode_id,
        )
        conn.commit()
    finally:
        conn.close()
    flash("組織型態資料已刪除。", "success")
    return _return_to_mapping()
