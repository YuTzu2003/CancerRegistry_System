from flask import Blueprint, request, session, jsonify
from modules.services.auth import login_required, admin_required
from modules.services.db import get_conn
from modules.blueprint.dashboard import load_user_favorites, save_user_favorites
from modules.blueprint.dashboard.reply import get_chart_insight_logic, get_compare_insight_logic
from modules.blueprint.dashboard.definition.cancer_group_rules import CANCER_GROUP_RULES
from flask import send_file
from modules.blueprint.dashboard.export_report import generate_export_files
from modules.blueprint.dashboard.pbi_settings import (get_pbi_publish_path,get_pbi_publish_settings,save_pbi_publish_path,)
import os
import re
import logging
import uuid
import pandas as pd
from flask import render_template
from modules.blueprint.dashboard.national_age_compare import (get_national_age_options,get_national_age_preview,get_national_age_side)

dashboard_bp = Blueprint('dashboard', __name__, template_folder='../blueprint/dashboard/templates')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DASHBOARD_DATA = os.path.join(BASE_DIR, 'tasks', 'data')
DASHBOARD_UPLOADS = os.path.join(DASHBOARD_DATA, 'dashboard')
os.makedirs(DASHBOARD_DATA, exist_ok=True)

def _dashboard_storage_path(file_id, stored_name):
    return os.path.join('dashboard', str(file_id), str(stored_name))


def _absolute_dashboard_path(storage_path):
    data_dir = os.path.abspath(DASHBOARD_DATA)
    file_path = os.path.abspath(os.path.join(data_dir, storage_path or ''))
    if os.path.commonpath([data_dir, file_path]) != data_dir:
        raise ValueError('Invalid dashboard file path')
    return file_path


def _get_uploaded_dashboard_files(user_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""SELECT FileID, DisplayName, CreatedAt FROM dbo.DashboardFile WHERE UserID = ? ORDER BY CreatedAt DESC """, (str(user_id),))
    files = [
        {
            "id": str(row[0]),
            "name": str(row[1]),
            "time": row[2].strftime("%Y/%m/%d %H:%M") if row[2] else "—",
        }
        for row in cursor.fetchall()
    ]
    conn.close()
    return files


def _get_owned_dashboard_file(file_id, user_id):
    if not file_id:
        return None
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""SELECT DisplayName, StoragePath FROM dbo.DashboardFile WHERE FileID = ? AND UserID = ? """, (str(file_id), str(user_id)))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {"name": str(row[0]), "storage_path": str(row[1])}


def _get_cancer_name_translations():
    translations = {"All_Cancers": {"zh": "全癌別", "en": "All cancers"}}
    for rule in CANCER_GROUP_RULES:
        for entry in [rule, *rule.get("subgroups", [])]:
            key = entry.get("key")
            if key:
                translations[key] = {
                    "zh": entry.get("name_zh") or key,
                    "en": entry.get("name_en") or entry.get("name_zh") or key,
                }
    return translations

@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    uploaded_files = _get_uploaded_dashboard_files(session.get("id"))
    return render_template(
        "dashboard.html",
        active="dashboard",
        uploaded_files=uploaded_files,
        cancer_name_translations=_get_cancer_name_translations(),
        pbi_publish_path=get_pbi_publish_path(),
    )

@dashboard_bp.route("/dashboard/compare")
@login_required
def compare():
    uploaded_files = _get_uploaded_dashboard_files(session.get("id"))
    return render_template(
        "compare.html",
        active="compare",
        uploaded_files=uploaded_files,
        cancer_name_translations=_get_cancer_name_translations(),
    )


@dashboard_bp.route("/dashboard/upload", methods=["POST"])
@login_required
def dashboard_upload():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "未選擇檔案"}), 400
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in ("xls", "xlsx"):
        return jsonify({"ok": False, "error": "僅接受 .xls 或 .xlsx 格式"}), 400
    raw_filename = f.filename or ""
    basename = os.path.basename(raw_filename)
    filename = re.sub(r'[\\/:*?"<>|\s]', '_', basename)
    if not filename.strip() or filename == f".{ext}":
        filename = f"uploaded_file.{ext}"
    user_id = session.get("id")
    file_id = str(uuid.uuid4())
    storage_name = f"{file_id}{os.path.splitext(filename)[1].lower()}"
    storage_path = _dashboard_storage_path(file_id, storage_name)
    save_path = _absolute_dashboard_path(storage_path)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    f.save(save_path)
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO dbo.DashboardFile (FileID, UserID, DisplayName, StoragePath) VALUES (?, ?, ?, ?)""", (file_id, str(user_id), filename, storage_path))
        conn.commit()
        conn.close()
    except Exception:
        if os.path.isfile(save_path):
            os.remove(save_path)
        raise
    logging.info(f"Dashboard upload: {filename} saved for user {user_id}")
    return jsonify({"ok": True, "filename": filename, "file_id": file_id})


@dashboard_bp.route('/api/dashboard/year_range', methods=['POST'])
@login_required
def dashboard_year_range():
    data = request.json or {}
    file_id = data.get("file_id", "")
    owned_file = _get_owned_dashboard_file(file_id, session.get("id"))
    if not owned_file:
        return jsonify({"ok": False, "error": "未選擇檔案"}), 400
    fpath = _absolute_dashboard_path(owned_file["storage_path"])
    if not os.path.isfile(fpath):
        return jsonify({"ok": False, "error": "檔案不存在"}), 404

    try:
        from modules.blueprint.dashboard.chart_analytics import _read_dashboard_excel, get_column_names
        df = _read_dashboard_excel(owned_file["storage_path"])
        cols = get_column_names(df)
        year_col = cols.get("year_col")
        if not year_col or year_col not in df.columns:
            return jsonify({"ok": False, "error": "找不到診斷年度欄位"}), 400

        years = pd.to_numeric(df[year_col].astype(str).str[:4], errors="coerce").dropna()
        if years.empty:
            return jsonify({"ok": False, "error": "查無符合條件資料！"}), 400

        return jsonify({
            "ok": True,
            "year_start": int(years.min()),
            "year_end": int(years.max())
        }), 200
    except Exception as e:
        logging.error(f"Error reading dashboard year range: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@dashboard_bp.route("/dashboard/delete", methods=["POST"])
@login_required
def dashboard_delete():
    data = request.json or {}
    file_id = data.get("file_id", "")
    owned_file = _get_owned_dashboard_file(file_id, session.get("id"))
    if not owned_file:
        return jsonify({"ok": False, "error": "未指定檔案名稱"}), 400
    fpath = _absolute_dashboard_path(owned_file["storage_path"])
    if not os.path.isfile(fpath):
        return jsonify({"ok": False, "error": "檔案不存在"}), 404
    os.remove(fpath)
    try:
        os.rmdir(os.path.dirname(fpath))
    except OSError:
        pass
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM dbo.DashboardFile WHERE FileID = ? AND UserID = ?", (str(file_id), str(session.get("id"))))
    conn.commit()
    conn.close()
    logging.info(f"Dashboard delete: {file_id}")
    return jsonify({"ok": True})

@dashboard_bp.route("/api/chart_insight", methods=["POST"])
@login_required
def chart_insight_route():
    try:
        data = request.json or {}
        result = get_chart_insight_logic(data)
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error in chart_insight_route: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@dashboard_bp.route("/api/dashboard/compare_insight", methods=["POST"])
@login_required
def compare_insight_route():
    try:
        data = request.json or {}
        result = get_compare_insight_logic(data)
        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code
    except Exception as e:
        logging.error(f"Error in compare_insight_route: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@dashboard_bp.route('/api/favorites', methods=['GET'])
@login_required
def get_favorites():
    db_id = session.get("id")
    user_favs = load_user_favorites(db_id)
    return jsonify({"ok": True, "favorites": user_favs}), 200

@dashboard_bp.route('/api/favorites', methods=['POST'])
@login_required
def add_favorite():
    db_id = session.get("id")
    data = request.json or {}
    name = data.get("name", "").strip()
    behavior = data.get("behavior", "")
    cancers = data.get("cancers", [])
    main_category = data.get("main_category", "")
    sub_category = data.get("sub_category", "")
    stage_options = data.get("stage_options", [])
    user_favs = load_user_favorites(db_id)
    
    if any(f.get("name") == name for f in user_favs):
        return jsonify({"ok": False, "error": "已有相同的最愛範本名稱"}), 400
        
    max_id = max([f.get("id", 0) for f in user_favs], default=0)
    new_id = max_id + 1
    new_fav = {"id": new_id,"name": name,"behavior": behavior,"cancers": cancers, "main_category": main_category, "sub_category": sub_category, "stage_options": stage_options}
    user_favs.append(new_fav)
    save_user_favorites(db_id, user_favs)
    return jsonify({"ok": True, "favorite": new_fav}), 200


@dashboard_bp.route('/api/favorites/<int:fav_id>', methods=['PUT'])
@login_required
def rename_favorite(fav_id):
    db_id = session.get("id")
    data = request.json or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"ok": False, "error": "請輸入新範本名稱"}), 400
     
    user_favs = load_user_favorites(db_id)
    if any(f.get("name") == name and f.get("id") != fav_id for f in user_favs):
        return jsonify({"ok": False, "error": "已有相同的最愛範本名稱"}), 400
       
    for f in user_favs:
        if f.get("id") == fav_id:
            f["name"] = name
            break     
    save_user_favorites(db_id, user_favs)
    return jsonify({"ok": True}), 200

@dashboard_bp.route('/api/favorites/<int:fav_id>', methods=['DELETE'])
@login_required
def delete_favorite(fav_id):
    db_id = session.get("id")
    user_favs = load_user_favorites(db_id)
    new_user_favs = [f for f in user_favs if f.get("id") != fav_id]
    if len(new_user_favs) == len(user_favs):
        return jsonify({"ok": False, "error": "找不到該最愛範本"}), 404      
    save_user_favorites(db_id, new_user_favs)
    return jsonify({"ok": True}), 200

@dashboard_bp.route('/api/dashboard/analyze_file', methods=['POST'])
@login_required
def analyze_dashboard_file_route():
    data = request.json or {}
    file_id = data.get("file_id", "")
    cancers = data.get("cancers", [])
    year_start = data.get("year_start", "")
    year_end = data.get("year_end", "")
    behavior = data.get("behavior", "")
    analysis_items = data.get("analysis_items", [])
    stage_options = data.get("stage_options", [])
    
    owned_file = _get_owned_dashboard_file(file_id, session.get("id"))
    if not owned_file:
        return jsonify({"ok": False, "error": "未提供檔案名稱"}), 400
        
    try:
        from modules.blueprint.dashboard.chart_analytics import analyze_dashboard_file
        chart_data = analyze_dashboard_file(
            owned_file["storage_path"], cancers, year_start, year_end, behavior, analysis_items,
            stage_options=stage_options,
        )
        return jsonify({"ok": True, "data": chart_data}), 200
    except Exception as e:
        import logging
        logging.error(f"Error analyzing dashboard file: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@dashboard_bp.route('/api/dashboard/publish_pbi', methods=['POST'])
@admin_required
def publish_dashboard_selection_to_pbi():
    data = request.json or {}
    file_id = data.get("file_id", "")
    cancers = data.get("cancers", [])
    year_start = str(data.get("year_start", "")).strip()
    year_end = str(data.get("year_end", "")).strip()
    behavior = str(data.get("behavior", "")).strip()
    owned_file = _get_owned_dashboard_file(file_id, session.get("id"))
    if not owned_file:
        return jsonify({"ok": False, "error": "找不到已選擇的年報檔案"}), 400
    if not year_start or not year_end or not cancers:
        return jsonify({"ok": False, "error": "請先完成年度、性態碼與癌別選擇"}), 400

    publish_path = get_pbi_publish_path()
    if not publish_path:
        return jsonify({"ok": False, "error": "尚未設定 Power BI 發布路徑，請先由管理者完成設定"}), 400

    try:
        from modules.blueprint.dashboard.pbi_export import export_pbi_dataset
        result = export_pbi_dataset(
            _absolute_dashboard_path(owned_file["storage_path"]),
            publish_path,
            cancers=cancers,
            year_start=year_start,
            year_end=year_end,
            behavior=behavior,
        )
        logging.info("Dashboard selection published to PBI by user %s: %s rows", session.get("userid"), result["rows"])
        return jsonify({"ok": True, "rows": result["rows"], "message": "已更新 Power BI 發布資料，報表將於下一次刷新後顯示。"})
    except Exception as exc:
        logging.exception("Failed to publish dashboard selection to PBI")
        return jsonify({"ok": False, "error": str(exc)}), 500


@dashboard_bp.route('/api/dashboard/pbi_settings', methods=['GET'])
@admin_required
def get_pbi_settings_route():
    settings = get_pbi_publish_settings()
    return jsonify({"ok": True, "settings": settings})


@dashboard_bp.route('/api/dashboard/pbi_settings', methods=['PUT'])
@admin_required
def save_pbi_settings_route():
    path = (request.json or {}).get("publish_path", "")
    try:
        settings = save_pbi_publish_path(path, session.get("userid") or session.get("id"))
        return jsonify({"ok": True, "settings": settings})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        logging.exception("Failed to save Power BI publish settings")
        return jsonify({"ok": False, "error": str(exc)}), 500

@dashboard_bp.route('/api/dashboard/file_years', methods=['POST'])
@login_required
def dashboard_file_years_route():
    data = request.json or {}
    file_id = data.get("file_id", "")
    if file_id == "national_age":
        # 「全國癌症年齡統計資料」是系統固定檔案，不在使用者上傳檔案表中。
        try:

            options = get_national_age_options()
            preview = get_national_age_preview(data.get("year_start", ""), data.get("year_end", ""))
            return jsonify({"ok": True, "years": options["years"], "preview": preview}), 200
        except Exception as error:
            logging.error("Error reading national age data: %s", error)
            return jsonify({"ok": False, "error": str(error)}), 500
    year_start = str(data.get("year_start", "")).strip()
    year_end = str(data.get("year_end", "")).strip()
    owned_file = _get_owned_dashboard_file(file_id, session.get("id"))
    if not owned_file:
        return jsonify({"ok": False, "error": "未提供檔案名稱"}), 400

    try:
        from modules.blueprint.dashboard.chart_analytics import (
            _read_dashboard_excel,
            get_column_names,
            get_dashboard_file_preview,
            get_dashboard_file_years,
        )
        source_df = _read_dashboard_excel(owned_file["storage_path"])
        cols = get_column_names(source_df)
        years = get_dashboard_file_years(owned_file["storage_path"], source_df, cols)
        preview = get_dashboard_file_preview(
            owned_file["storage_path"], 10, year_start, year_end, source_df, cols
        )
        return jsonify({"ok": True, "years": years, "preview": preview}), 200
    except Exception as e:
        logging.error(f"Error detecting dashboard file years: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@dashboard_bp.route('/api/dashboard/compare', methods=['POST'])
@login_required
def compare_dashboard_files_route():
    data = request.json or {}
    main_file_id = data.get("main_file_id", "")
    target_file_id = data.get("target_file_id", "")
    main_year = str(data.get("main_year", "")).strip()
    target_year = str(data.get("target_year", "")).strip()
    main_year_end = str(data.get("main_year_end", "")).strip()
    target_year_end = str(data.get("target_year_end", "")).strip()
    compare_mode = str(data.get("compare_mode", "single")).strip()
    behavior = data.get("behavior", "")
    cancers = data.get("cancers", [])
    compare_items = data.get("compare_items", [])
    stage_options = data.get("stage_options", [])
    is_national_compare = main_file_id == "national_age" or target_file_id == "national_age"
    if not isinstance(compare_items, list):
        return jsonify({"ok": False, "error": "分析項目格式錯誤"}), 400
    if not isinstance(stage_options, list):
        return jsonify({"ok": False, "error": "期別選項格式錯誤"}), 400
    stage_options = [
        option for option in stage_options
        if isinstance(option, dict)
        and str(option.get("system", "")).strip()
        and str(option.get("option", "")).strip()
    ]
    if compare_items and any(str(item).endswith("期別") for item in compare_items) and not stage_options:
        return jsonify({"ok": False, "error": "請至少選擇一個分期系統及表圖類型"}), 400

    # 全國檔不需使用者檔案所有權驗證；另一側仍依原規則取得使用者上傳檔。
    main_file = None if main_file_id == "national_age" else _get_owned_dashboard_file(main_file_id, session.get("id"))
    target_file = None if target_file_id == "national_age" else _get_owned_dashboard_file(target_file_id, session.get("id"))
    if (main_file_id != "national_age" and not main_file) or (target_file_id != "national_age" and not target_file):
        return jsonify({"ok": False, "error": "請選擇基準期資料與比較期資料"}), 400
    if compare_mode not in {"single", "range"}:
        return jsonify({"ok": False, "error": "比較模式不正確"}), 400
    if compare_mode == "single":
        main_year_end = main_year
        target_year_end = target_year
    if not main_year or not target_year or not main_year_end or not target_year_end:
        return jsonify({"ok": False, "error": "請選擇基準期資料與比較期資料的年度"}), 400
    if not all(year.isdigit() for year in (main_year, target_year, main_year_end, target_year_end)):
        return jsonify({"ok": False, "error": "年度格式不正確"}), 400
    if int(main_year) > int(main_year_end) or int(target_year) > int(target_year_end):
        return jsonify({"ok": False, "error": "起始年度不可晚於結束年度"}), 400
    if not is_national_compare and main_file_id == target_file_id and main_year == target_year and main_year_end == target_year_end:
        return jsonify({"ok": False, "error": "同一份 Excel 比較時，基準期間與比較期間不可相同"}), 400
    if (main_file_id != "national_age" or target_file_id != "national_age") and not behavior:
        return jsonify({"ok": False, "error": "請選擇性態碼"}), 400
    if not cancers:
        return jsonify({"ok": False, "error": "請選擇癌別"}), 400
    if not compare_items:
        return jsonify({"ok": False, "error": "請選擇分析項目"}), 400

    try:
        if is_national_compare:
            # 任一側是全國彙總檔時，兩側都只組裝性別年齡分布，維持原比較頁的資料格式。
            from modules.blueprint.dashboard.chart_analytics import (
                _read_dashboard_excel,
                analyze_dashboard_file,
                filter_dashboard_data,
                get_column_names,
                get_dashboard_file_years,
                summarize_dashboard_file,
            )


            def build_local_side(file_info, year, year_end):
                # 院內檔仍使用既有逐案資料篩選與年齡圖計算，避免改變原本統計規則。
                source = _read_dashboard_excel(file_info["storage_path"])
                columns = get_column_names(source)
                filtered = filter_dashboard_data(source, columns, cancers, year, year_end, behavior)
                summary = summarize_dashboard_file(
                    file_info["storage_path"], behavior, cancers, year, year_end,
                    source, columns, filtered,
                )
                analysis = analyze_dashboard_file(
                    file_info["storage_path"], cancers, year, year_end, behavior,
                    ["性別年齡分佈"], source, columns, filtered,
                )
                return summary, {"genderAgeData": analysis["genderAgeData"]}

            main_summary, main_analysis = (
                (get_national_age_side(main_year, cancers), None)
                if main_file_id == "national_age"
                else build_local_side(main_file, main_year, main_year_end)
            )
            target_summary, target_analysis = (
                (get_national_age_side(target_year, cancers), None)
                if target_file_id == "national_age"
                else build_local_side(target_file, target_year, target_year_end)
            )
            main_analysis = main_analysis or {"genderAgeData": main_summary.pop("genderAgeData")}
            target_analysis = target_analysis or {"genderAgeData": target_summary.pop("genderAgeData")}
            for file_info, year, year_end in ((main_file, main_year, main_year_end), (target_file, target_year, target_year_end)):
                if file_info:
                    available_years = get_dashboard_file_years(file_info["storage_path"])
                    if int(year) not in available_years or int(year_end) not in available_years:
                        return jsonify({"ok": False, "error": "所選年度不存在於院內 Excel"}), 400
            diff = target_summary["total_count"] - main_summary["total_count"]
            result = {
                "main": main_summary,
                "target": target_summary,
                "analysis_data": {
                    "main": main_analysis,
                    "target": target_analysis,
                    "items": ["性別年齡分佈"],
                },
                "compare_mode": "single",
                "diff": {
                    "total_count": diff,
                    "total_percent": f"{diff / main_summary['total_count'] * 100:.1f}%" if main_summary["total_count"] else "",
                    "annual_average": diff,
                },
            }
            return jsonify({"ok": True, "data": result}), 200
        from modules.blueprint.dashboard.chart_analytics import compare_dashboard_files, get_dashboard_file_years
        main_years = get_dashboard_file_years(main_file["storage_path"])
        target_years = get_dashboard_file_years(target_file["storage_path"])
        if (int(main_year) not in main_years or int(main_year_end) not in main_years
                or int(target_year) not in target_years or int(target_year_end) not in target_years):
            return jsonify({"ok": False, "error": "選擇的年度不在 Excel 資料範圍內"}), 400

        result = compare_dashboard_files(
            main_file["storage_path"], target_file["storage_path"], behavior, cancers, compare_items,
            main_year, target_year, main_year_end, target_year_end, compare_mode, stage_options
        )
        return jsonify({"ok": True, "data": result}), 200
    except ValueError as e:
        logging.error(f"Error comparing dashboard files: {e}")
        return jsonify({"ok": False, "error": f"無數據：{e}"}), 400
    except Exception as e:
        logging.error(f"Error comparing dashboard files: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500



@dashboard_bp.route('/dashboard/export_report', methods=['GET'])
@login_required
def export_report_page():
    return render_template('export_report.html', active='dashboard')

@dashboard_bp.route('/api/dashboard/export', methods=['POST'])
@login_required
def export_report_api():
    data = request.json or {}
    format_pdf = data.get('format_pdf', True)
    format_word = data.get('format_word', False)
    charts = data.get('charts', [])
    export_language = data.get('export_language', 'zh-TW')
    
    if not charts:
        return jsonify({'ok': False, 'error': '沒有圖表資料可匯出'}), 400
        
    output_dir = os.path.join(DASHBOARD_DATA, 'exports')
    
    try:
        file_obj, mimetype, dl_name = generate_export_files(
            format_pdf, format_word, charts, output_dir, export_language
        )
        if file_obj:
            return send_file(file_obj, mimetype=mimetype, as_attachment=True, download_name=dl_name)
        else:
            return jsonify({'ok': False, 'error': '無法產生匯出檔案'}), 500
    except Exception as e:
        import logging
        logging.error(f'Export error: {e}')
        return jsonify({'ok': False, 'error': str(e)}), 500
