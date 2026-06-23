from flask import Blueprint, render_template, request, session, jsonify, send_file
from modules.services.auth import login_required, admin_required
from modules.blueprint.clean import categorize_fields_logic,export_logic,preview_logic,get_formats_logic,add_format_logic,manage_format_logic,clean_job_logic,get_date_errors_logic,update_date_error_logic,download_temp_file_logic,download_file_logic

clean_bp = Blueprint('clean', __name__)

@clean_bp.route("/api/categorize_fields", methods=["POST"])
@login_required
def api_categorize_fields():
    data = request.json
    res, status = categorize_fields_logic(data.get("job_id"), data.get("scheme"))
    return jsonify(res), status

@clean_bp.route("/api/export", methods=["POST"])
@login_required
def api_export():
    data = request.json
    res, status = export_logic(data.get("job_id"), data.get("scheme"), data.get("fields", []))
    if res.get("send_file"):
        resp = send_file(res["path"], as_attachment=True, download_name=res["download_name"])
        resp.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
        return resp
    return jsonify(res), status

@clean_bp.route("/api/preview", methods=["POST"])
@login_required
def api_preview():
    data = request.json
    res, status = preview_logic(data.get("job_id"), data.get("scheme"), data.get("fields", []))
    return jsonify(res), status

@clean_bp.route("/clean")
@login_required
def clean():
    formats = get_formats_logic()
    return render_template("clean.html", active="clean", formats=formats)

@clean_bp.route("/api/formats", methods=["POST"])
@admin_required
def api_add_format():
    data = request.json if request.is_json else request.form
    res, status = add_format_logic(data.get("name"), data.get("version"), data.get("updated"))
    return jsonify(res), status

@clean_bp.route("/api/formats/<fmt_id>", methods=["PUT", "DELETE", "POST"])
@admin_required
def api_manage_format(fmt_id):
    data = request.json if request.is_json else request.form
    if request.method == "DELETE":
        res, status = manage_format_logic("DELETE", fmt_id, None, None, None)
    else:
        res, status = manage_format_logic("UPDATE", fmt_id, data.get("name"), data.get("version"), data.get("updated"))
    return jsonify(res), status

@clean_bp.route("/api/cleanJob", methods=["POST"])
@login_required
def api_clean():
    user_id = session.get("id")
    format_id = request.form.get("format_id")
    convert_txt_flag = request.form.get("convert_txt") == "true"
    uploaded_file = request.files.get("data_file")
    
    res, status = clean_job_logic(user_id, format_id, convert_txt_flag, uploaded_file)
    return jsonify(res), status

@clean_bp.route("/api/date_errors", methods=["POST"])
@login_required
def api_date_errors():
    data = request.get_json(silent=True) or {}
    res, status = get_date_errors_logic(data.get("job_id"))
    return jsonify(res), status

@clean_bp.route("/api/date_errors/update", methods=["POST"])
@login_required
def api_update_date_error():
    data = request.get_json(silent=True) or {}
    res, status = update_date_error_logic(data.get("job_id"), data.get("row_index"), data.get("updates"))
    return jsonify(res), status

@clean_bp.route("/api/download_temp/<file_type>/<temp_id>/<filename>")
@login_required
def download_temp_file(file_type, temp_id, filename):
    res, status = download_temp_file_logic(file_type, temp_id, filename)
    if res.get("send_file"):
        return send_file(res["path"], as_attachment=True, download_name=res["download_name"])
    return jsonify(res), status

@clean_bp.route("/api/download/<file_type>/<job_id>")
@login_required
def download_file(file_type, job_id):
    res, status = download_file_logic(file_type, job_id)
    if res.get("send_file"):
        return send_file(res["path"], as_attachment=True, download_name=res["download_name"])
    return jsonify(res), status