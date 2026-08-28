import logging
from zipfile import BadZipFile
from flask import flash, redirect, render_template, request, url_for
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from modules.services.auth import login_required
from modules.services.dashboard import dashboard_bp
from modules.services.db import get_conn

NATIONAL_IMPORT_SHEETS = {
    "年齡": {"table": "National_Age", "item_column": "Age", "headers": ("年度", "癌別", "年齡", "合計", "男性", "女性", "醫學中心", "非醫學中心")},
    "整併期別": {"table": "National_Period", "item_column": "Period", "headers": ("年度", "癌別", "整併期別", "合計", "男性", "女性", "醫學中心", "非醫學中心")},}

NATIONAL_DATASETS = {
    "age": {"table": "National_Age", "id_column": "NationAge_ID", "item_column": "Age", "label": "年齡", "item_label": "年齡"},
    "period": {"table": "National_Period", "id_column": "NationPeriod_ID", "item_column": "Period", "label": "整併期別", "item_label": "整併期別"},}

NATIONAL_COLUMN_LABELS = {
    "Year": "年度", "Cancer": "癌別", "Total": "合計", "Male": "男性", "Female": "女性",
    "Medical_Centers": "醫學中心", "N_Medical_Centers": "非醫學中心",}

def read_national_import_rows(file_source):
    try:
        workbook = load_workbook(file_source, read_only=True, data_only=True)
    except (BadZipFile, InvalidFileException, OSError) as error:
        raise ValueError("無法讀取 Excel 檔案。") from error
    try:
        missing = [name for name in NATIONAL_IMPORT_SHEETS if name not in workbook.sheetnames]
        if missing:
            raise ValueError(f"Excel 缺少工作表：{'、'.join(missing)}。")
        imported_rows = {}
        for sheet_name, config in NATIONAL_IMPORT_SHEETS.items():
            worksheet = workbook[sheet_name]
            try:
                headers = tuple(cell.value for cell in next(worksheet.iter_rows(max_row=1)))
            except StopIteration as error:
                raise ValueError(f"「{sheet_name}」工作表沒有標題列。") from error
            if headers != config["headers"]:
                raise ValueError(f"「{sheet_name}」工作表的欄位順序或名稱不正確。")
            rows = []
            for row_number, values in enumerate(worksheet.iter_rows(min_row=2, values_only=True), start=2):
                if all(value is None or (isinstance(value, str) and not value.strip()) for value in values):
                    continue
               
                year, cancer, item, *counts = values
                if any(isinstance(value, bool) for value in counts):
                    raise ValueError
                
                counts = [int(value) for value in counts]
                if any(value < 0 for value in counts):
                    raise ValueError(f"「{sheet_name}」工作表第 {row_number} 列的數值欄位不可為負數。")
                rows.append((
                    str(int(year)) if isinstance(year, float) and year.is_integer() else str(year).strip(),
                    str(cancer).strip(),
                    str(int(item)) if isinstance(item, float) and item.is_integer() else str(item).strip(),
                    *counts,
                ))
            imported_rows[sheet_name] = rows
        return imported_rows
    finally:
        workbook.close()

def get_national_data(dataset, selected_year="", search_column="", search_query=""):
    config = NATIONAL_DATASETS[dataset]
    fields = ["Year", "Cancer", config["item_column"], "Total", "Male", "Female", "Medical_Centers", "N_Medical_Centers"]
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(f"SELECT [Year], COUNT(*) FROM dbo.[{config['table']}] WHERE [Year] IS NOT NULL GROUP BY [Year]")
    year_counts = [(str(row[0]), int(row[1])) for row in cursor.fetchall()]
    years = sorted((year for year, _ in year_counts), key=lambda year: (year.isdigit(), int(year) if year.isdigit() else year), reverse=True)
    selected_year = selected_year if selected_year in years else next(iter(years), "")
    search_column = search_column if search_column in {"Cancer", config["item_column"]} else ""
    search_query = search_query.strip()
    query = "SELECT " + ", ".join(f"[{field}]" for field in [config["id_column"], *fields]) + f" FROM dbo.[{config['table']}]"
    conditions, parameters = [], []
    if selected_year:
        conditions.append("[Year] = ?")
        parameters.append(selected_year)
    if search_query:
        conditions.append(f"CONVERT(NVARCHAR(MAX), [{search_column or 'Cancer'}]) LIKE ?")
        parameters.append(f"%{search_query}%")
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    cursor.execute(query + f" ORDER BY [Cancer], [{config['item_column']}]", *parameters)
    rows = [tuple(row) for row in cursor.fetchall()]
    conn.close()
    return {"config": config, "rows": rows, "available_years": years, "selected_year": selected_year, "selected_year_count": dict(year_counts).get(selected_year, 0), "search_column": search_column, "search_query": search_query}

def insert_national_rows(imported_rows):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        for sheet_name, config in NATIONAL_IMPORT_SHEETS.items():
            cursor.executemany(f"INSERT INTO dbo.[{config['table']}] ([Year], [Cancer], [{config['item_column']}], [Total], [Male], [Female], [Medical_Centers], [N_Medical_Centers]) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", imported_rows[sheet_name])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_national_rows(dataset, record_ids):
    config = NATIONAL_DATASETS[dataset]
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM dbo.[{config['table']}] WHERE [{config['id_column']}] IN ({', '.join('?' for _ in record_ids)})", *record_ids)
        conn.commit()
        return cursor.rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def update_national_row(dataset, record_id, values):
    config = NATIONAL_DATASETS[dataset]
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE dbo.[{config['table']}] SET [Year] = ?, [Cancer] = ?, [{config['item_column']}] = ?, [Total] = ?, [Male] = ?, [Female] = ?, [Medical_Centers] = ?, [N_Medical_Centers] = ? WHERE [{config['id_column']}] = ?", *values, record_id)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def redirect_national_import():
    return redirect(url_for("dashboard.national_import", view=request.form.get("view", "age"), year=request.form.get("year", ""), column=request.form.get("column", ""), q=request.form.get("q", "")))

@dashboard_bp.route("/dashboard/national-import", methods=["GET", "POST"])
@login_required
def national_import():
    if request.method == "GET":
        dataset = request.args.get("view", "age")
        dataset = dataset if dataset in NATIONAL_DATASETS else "age"
        try:
            data = get_national_data(dataset, request.args.get("year", ""), request.args.get("column", ""), request.args.get("q", ""))
        except Exception:
            logging.exception("Unable to read national import data")
            flash("無法讀取資料表。", "danger")
            data = {"config": NATIONAL_DATASETS[dataset], "rows": [], "available_years": [], "selected_year": "", "selected_year_count": 0, "search_column": "", "search_query": ""}
        return render_template("national_import.html", active="national_import", dataset=dataset, datasets=NATIONAL_DATASETS, column_labels=NATIONAL_COLUMN_LABELS, editing_id=request.args.get("edit_id", "").strip(), **data)

    uploaded_file = request.files.get("import_file")
    try:
        if not uploaded_file or not uploaded_file.filename:
            raise ValueError("請選擇國家資料 Excel 檔案。")
        if not uploaded_file.filename.lower().endswith(".xlsx"):
            raise ValueError("僅接受 .xlsx 格式的國家資料檔案。")
        imported_rows = read_national_import_rows(uploaded_file)
        insert_national_rows(imported_rows)
    except ValueError as error:
        flash(str(error), "danger")
    except Exception:
        logging.exception("Unable to import national data")
        flash("匯入失敗，資料未寫入。請確認資料庫連線與資料表。", "danger")
    else:
        flash(f"匯入完成：National_Age {len(imported_rows['年齡'])} 筆、National_Period {len(imported_rows['整併期別'])} 筆。", "success")
    return redirect(url_for("dashboard.national_import"))

@dashboard_bp.route("/dashboard/national-import/delete", methods=["POST"])
@login_required
def delete_national_rows_route():
    dataset, record_ids = request.form.get("view", "age"), request.form.getlist("record_ids")
    try:
        if dataset not in NATIONAL_DATASETS:
            raise ValueError("資料類型不正確。")
        if not record_ids:
            raise ValueError("請先選擇要刪除的資料。")
        if any(not record_id.isdigit() for record_id in record_ids):
            raise ValueError("刪除資料識別碼不正確。")
        deleted_count = delete_national_rows(dataset, record_ids)
    except ValueError as error:
        flash(str(error), "warning")
    except Exception:
        logging.exception("Unable to delete national data")
        flash("刪除失敗，資料未變更。", "danger")
    else:
        flash(f"已刪除 {deleted_count} 筆{NATIONAL_DATASETS[dataset]['label']}資料。", "success")
    return redirect_national_import()


@dashboard_bp.route("/dashboard/national-import/<int:record_id>/update", methods=["POST"])
@login_required
def update_national_row_route(record_id):
    dataset = request.form.get("view", "age")
    config = NATIONAL_DATASETS.get(dataset)
    values = [request.form.get(name, "").strip() for name in ("Year", "Cancer", config["item_column"] if config else "", "Total", "Male", "Female", "Medical_Centers", "N_Medical_Centers")]
    try:
        if not config:
            raise ValueError("資料類型不正確。")
        if not all(values[:3]):
            raise ValueError("年度、癌別與資料項目不可空白。")
        if any(not value.isdigit() for value in values[3:]):
            raise ValueError("合計、男性、女性、醫學中心與非醫學中心必須為非負整數。")
        update_national_row(dataset, record_id, (*values[:3], *(int(value) for value in values[3:])))
    except ValueError as error:
        flash(str(error), "danger")
    except Exception:
        logging.exception("Unable to update national data")
        flash("修改資料時發生錯誤。", "danger")
    else:
        flash("資料已修改。", "success")
    return redirect_national_import()


@dashboard_bp.route("/dashboard/national-import/<int:record_id>/delete", methods=["POST"])
@login_required
def delete_national_row_route(record_id):
    dataset = request.form.get("view", "age")
    try:
        if dataset not in NATIONAL_DATASETS:
            raise ValueError("資料類型不正確。")
        deleted_count = delete_national_rows(dataset, [str(record_id)])
    except ValueError as error:
        flash(str(error), "danger")
    except Exception:
        logging.exception("Unable to delete national data")
        flash("刪除資料時發生錯誤。", "danger")
    else:
        flash(f"已刪除 {deleted_count} 筆資料。", "success")
    return redirect_national_import()