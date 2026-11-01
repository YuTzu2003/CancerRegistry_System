import os
import re
import shutil
import uuid
import math
import hashlib
import json
from datetime import datetime, timezone
import pandas as pd
from flask import Blueprint, current_app, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.utils import secure_filename
from modules.services.auth import admin_required, login_required, position_required
from modules.services.audit import write_audit_log
from modules.services.db import get_conn
from modules.blueprint.auth.key_access import data_update_key_required, has_data_update_access
from modules.blueprint.dashboard.input_format import (
    preview_dashboard_upload,
    read_csv_with_encoding,
    validate_and_normalize_dashboard_upload,
)
from modules.blueprint.clean.pipeline import get_formats_logic
from modules.blueprint.dashboard.llm_tasks import create_llm_task, find_reusable_llm_task, get_llm_task_payload
from modules.blueprint.indicators.analysis import build_indicators_export_frame, run_indicators_analysis
from modules.blueprint.indicators.catalog import CANCER_SPECS, get_cancer_label, get_indicator_rules
from modules.blueprint.indicators.excel_export import create_indicators_excel
from modules.blueprint.indicators.export_report import generate_indicator_export_files
from modules.blueprint.indicators.rule_versions import default_rules, editable_conditions, apply_changes, next_revision_name, build_user_indicator, validate_rule_tree
from modules.blueprint.indicators.definition_versions import decode_definition, load_definition
from modules.blueprint.indicators.indicator_definitions import RULE_FIELD_LABELS, get_indicator_metadata

indicators_bp = Blueprint("indicators",__name__,template_folder="../blueprint/indicators/templates",)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INDICATORS_DATA_DIR = os.path.join(BASE_DIR, "tasks", "data", "indicators")
DEFINITION_STATUSES = frozenset({'DRAFT', 'PENDING', 'PUBLISHED', 'INACTIVE'})
DEFINITION_STATUS_TRANSITIONS = {
    # DRAFT is retained only for older or returned versions. New submissions
    # enter PENDING directly and need an administrator to approve them.
    'DRAFT': frozenset({'PENDING', 'INACTIVE'}),
    'PENDING': frozenset({'DRAFT', 'PUBLISHED', 'INACTIVE'}),
    'PUBLISHED': frozenset({'INACTIVE'}),
    # Re-enabling an inactive published snapshot must not make it editable.
    # It simply returns to the published list for new analyses.
    'INACTIVE': frozenset({'PUBLISHED'}),
}

def _definition_cancers():
    return [{'key': key, 'name': get_cancer_label(key)} for key in CANCER_SPECS]

def _definition_fingerprint(definition, version):
    # Compare the whole editable version, not only its rules: metadata and
    # status changes must also invalidate an open editing session.
    snapshot = {'rules': definition, 'id': str(version['id']), 'name': version.get('name'),
                'definition_year': version.get('definition_year'), 'description': version.get('description') or '',
                'status': version.get('status') or 'DRAFT', 'updated_at': version.get('updated_at')}
    canonical = json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def _locked_version_fingerprint(version_id, row):
    return _definition_fingerprint(decode_definition(row[0]), {
        'id': str(version_id), 'status': str(row[1] or 'DRAFT').upper(),
        'description': row[2] or '', 'name': row[3], 'definition_year': row[4],
        'updated_at': row[5].isoformat() if row[5] else None,
    })


def _definition_text(value, field_name, *, required=False, limit=1000):
    text = str(value or '').strip()
    if required and not text:
        raise ValueError(f'請填寫{field_name}。')
    if len(text) > limit:
        raise ValueError(f'{field_name}最多 {limit} 字。')
    return text


def _definition_year(value, *, required=False):
    """Validate an annual definition label without filtering diagnosis years."""
    if value in (None, ''):
        if required:
            raise ValueError('請選擇指標定義的適用年度。')
        return None
    try:
        if isinstance(value, bool):
            raise ValueError
        year = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError('適用年度須為 1 至 9999 的整數。') from None
    if not 1 <= year <= 9999:
        raise ValueError('適用年度須為 1 至 9999 的整數。')
    return year


def _annual_definition_name(year, existing_names):
    """Create an understandable annual title without exposing technical IDs."""
    base = f'{year} 年度指標定義'
    if base not in existing_names:
        return base
    number = 2
    while f'{base}（修訂 {number}）' in existing_names:
        number += 1
    return f'{base}（修訂 {number}）'


def _record_definition_history(cursor, *, version_id, action, status_before=None,
                               status_after=None, rules_before=None, rules_after=None,
                               reason=''):
    cursor.execute(
        'INSERT INTO dbo.IndicatorDefinitionVersionHistory '
        '(version_id, action, status_before, status_after, rules_before_json, rules_after_json, change_reason, changed_by) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (
            int(version_id), action, status_before, status_after, rules_before, rules_after,
            reason or None, str(session.get('id') or session.get('userid') or ''),
        ),
    )

def _selected_rule_versions(payload, cancers):
    legacy = payload.get('rule_versions')
    if legacy is not None and (not isinstance(legacy, dict) or any(value not in (None, '', 'default') for value in legacy.values())):
        raise ValueError('請重新整理頁面，選擇一套共同的指標定義版本。')
    if payload.get('oral_rule_version') not in (None, '', 'default'):
        raise ValueError('請重新整理頁面，選擇一套共同的指標定義版本。')
    if not isinstance(cancers, list) or any(not isinstance(key, str) or key not in CANCER_SPECS for key in cancers):
        raise ValueError('找不到指定的癌別。')
    definition, version = load_definition(payload.get('definition_version', 'default'), get_conn)
    _require_complete_definition(definition)
    missing = [get_cancer_label(key) for key in dict.fromkeys(cancers) if key not in definition]
    if missing:
        raise ValueError('所選指標定義版本未收錄：' + '、'.join(missing) + '。請至資料維護補齊，或選擇其他完整版本。')
    return ({key: definition[key] for key in dict.fromkeys(cancers)},
            {key: version for key in dict.fromkeys(cancers)})


def _require_complete_definition(definition):
    """A reusable definition version must carry a rule set for every cancer."""
    missing = [get_cancer_label(key) for key in CANCER_SPECS if key not in definition]
    if missing:
        raise ValueError('完整指標定義版本須包含所有癌別；尚未設定：' + '、'.join(missing) + '。')


def _analysis_result_snapshot(result):
    """Persist a compact, non-identifying summary sufficient for later audit."""
    reports = []
    for report in result.get('reports', []):
        reports.append({
            'cancer_key': report.get('cancer_key'),
            'cancer_name': report.get('cancer_name'),
            'input_count': report.get('input_count'),
            'included_count': report.get('included_count'),
            'global_exclusions': report.get('global_exclusions', {}),
            'indicators': [{
                'id': item.get('id'),
                'name': item.get('name'),
                'numerator': item.get('numerator'),
                'denominator': item.get('denominator'),
                'percentage': item.get('percentage'),
                'calculation_available': item.get('calculation_available'),
                'numerator_definition': item.get('numerator_definition'),
                'denominator_definition': item.get('denominator_definition'),
                'target_value': item.get('target_value'),
                'target_operator': item.get('target_operator') or (
                    '<=' if item.get('direction') == 'negative' else '>='
                ),
                'target_met': _indicator_target_met(item),
            } for item in report.get('indicators', [])],
        })
    return {'reports': reports}


def _indicator_target_met(item):
    """Return the exact target outcome shown for an indicator, if calculable."""
    target = item.get('target_value')
    percentage = item.get('percentage')
    if target is None or percentage is None:
        return None
    try:
        target = float(target)
        percentage = float(percentage)
    except (TypeError, ValueError):
        return None
    operator = item.get('target_operator') or (
        '<=' if item.get('direction') == 'negative' else '>='
    )
    comparisons = {
        '>=': lambda value, limit: value >= limit,
        '>': lambda value, limit: value > limit,
        '<=': lambda value, limit: value <= limit,
        '<': lambda value, limit: value < limit,
        '=': lambda value, limit: value == limit,
    }
    comparison = comparisons.get(operator)
    return comparison(percentage, target) if comparison else None


def _record_indicator_analysis_run(*, cancers, year_start, year_end,
                                   rules_by_cancer, versions, result):
    """Store the exact rule and result snapshots used by one analysis request."""
    version = next(iter(versions.values()), {})
    version_id = version.get('id')
    definition_version_id = int(version_id) if str(version_id).isdigit() else None
    definition_snapshot = {key: rules_by_cancer[key] for key in dict.fromkeys(cancers)}
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO dbo.IndicatorAnalysisRun '
            '(user_id, year_start, year_end, cancer_keys_json, definition_version_id, '
            'definition_version_name, definition_snapshot_json, result_snapshot_json) '
            'OUTPUT INSERTED.run_id VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (
                str(session.get('id') or session.get('userid') or ''),
                year_start, year_end,
                json.dumps(list(dict.fromkeys(cancers)), ensure_ascii=False),
                definition_version_id,
                str(version.get('name') or '115 年度指標定義（系統基準）'),
                json.dumps(definition_snapshot, ensure_ascii=False),
                json.dumps(_analysis_result_snapshot(result), ensure_ascii=False),
            ),
        )
        row = cursor.fetchone()
        conn.commit()
        return int(row[0])
    finally:
        conn.close()


def _analysis_run_timestamp(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _snapshot_definition_texts(definition):
    for cancer_key, rules in definition.items():
        fields = ('numerator_definition', 'denominator_definition', 'selection_reason', 'notes')
        if all(all(field in rule for field in fields) for rule in rules.values()):
            continue
        metadata = {item['id']: item for item in get_indicator_metadata(cancer_key)}
        for number, rule in rules.items():
            for field in fields:
                fallback = '依已設定的分子規則計算。' if field == 'numerator_definition' else '依已設定的分母規則計算。' if field == 'denominator_definition' else ''
                rule.setdefault(field, metadata.get(number, {}).get(field) or fallback)
    return definition


@indicators_bp.route('/api/indicators/definition-versions', methods=['GET'])
@login_required
def list_definition_versions():
    include_all = request.args.get('include_all') == '1' and has_data_update_access()
    versions = [{'id': 'default', 'name': '115 年度指標定義（系統基準）', 'description': '系統內建的 115 年度指標規則。',
                 'status': 'PUBLISHED', 'cancers': list(CANCER_SPECS)}]
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT v.version_id, v.version_name, v.definition_year, v.rules_json, v.version_description, v.status, "
            "COALESCE(NULLIF(u.[Name], ''), '') AS created_by_name, v.created_at, "
            'v.updated_by, v.updated_at, v.published_by, v.published_at, v.created_by '
            'FROM dbo.IndicatorDefinitionVersion AS v '
            "LEFT JOIN dbo.Users AS u ON CONVERT(nvarchar(36), u.[ID]) = v.created_by OR u.[UserID] = v.created_by "
            'ORDER BY v.version_id DESC'
        )
        for row in cursor.fetchall():
            row_status = str(row[5] or 'DRAFT').upper()
            if not include_all and row_status != 'PUBLISHED':
                continue
            definition = decode_definition(row[3])
            complete = set(definition) == set(CANCER_SPECS)
            # Keep legacy per-cancer snapshots visible to maintainers, but
            # never offer an incomplete snapshot for a new analysis.
            if not include_all and not complete:
                continue
            version = {
                'id': str(row[0]), 'name': row[1], 'definition_year': row[2],
                'description': row[4] or '', 'status': row_status,
                'created_by': row[6] or '',
                'created_at': row[7].replace(tzinfo=timezone.utc).isoformat() if row[7] else None,
                'updated_by': row[8] or '', 'updated_at': row[9].isoformat() if row[9] else None,
                'published_by': row[10] or '', 'published_at': row[11].isoformat() if row[11] else None,
                'cancers': list(definition),
                'complete': complete,
            }
            if include_all:
                version['created_by_key'] = str(row[12] or '')
            versions.append(version)
    finally:
        conn.close()
    return jsonify({'ok': True, 'cancers': _definition_cancers(), 'versions': versions})


@indicators_bp.route('/api/indicators/definition-versions/<version_id>/cancers/<cancer_key>', methods=['GET'])
@login_required
@data_update_key_required(destination='indicator_definitions')
def get_definition_version(version_id, cancer_key):
    try:
        if cancer_key not in CANCER_SPECS:
            raise ValueError('找不到指定的癌別。')
        definition, version = load_definition(version_id, get_conn, allow_unpublished=True)
        version['fingerprint'] = _definition_fingerprint(definition, version)
        included = cancer_key in definition
        rules = definition[cancer_key] if included else default_rules(cancer_key)
        metadata = {item['id']: item for item in get_indicator_metadata(cancer_key)}
        descriptions = [{'id': number, 'name': rule['name'],
                         'numerator_definition': rule.get('numerator_definition', metadata.get(number, {}).get('numerator_definition', '')),
                         'denominator_definition': rule.get('denominator_definition', metadata.get(number, {}).get('denominator_definition', ''))}
                        for number, rule in sorted(rules.items())]
        field_labels = RULE_FIELD_LABELS
        return jsonify({'ok': True, 'cancer_key': cancer_key, 'included': included, 'version': version,
                        'conditions': editable_conditions(rules), 'descriptions': descriptions, 'field_labels': field_labels,
                        'rule_trees': {str(number): {'numerator': rule['numerator'], 'denominator': rule['denominator']}
                                       for number, rule in rules.items()}})
    except ValueError as error:
        return jsonify({'ok': False, 'error': str(error)}), 400


@indicators_bp.route('/indicators/definitions')
@login_required
@data_update_key_required(destination='indicator_definitions')
def indicator_definitions_page():
    return render_template(
        'indicator_definitions.html', active='indicators.indicator_definitions_page',
        can_manage_definitions=True,
        can_approve_definitions=session.get('position') == 'Admin',
        definition_cancers=_definition_cancers(),
    )


@indicators_bp.route('/indicators/definition-review')
@login_required
@data_update_key_required(destination='indicator_definitions')
def indicator_definition_review_page():
    return render_template(
        'indicator_definition_review.html', active='indicators.indicator_definition_review_page',
        definition_cancers=_definition_cancers(),
        can_approve_definitions=session.get('position') == 'Admin',
    )


@indicators_bp.route('/api/indicators/definition-versions', methods=['POST'])
@indicators_bp.route('/api/indicators/definition-versions/<version_id>/revisions', methods=['POST'])
@indicators_bp.route('/api/indicators/definition-versions/<version_id>', methods=['PUT'])
@login_required
@data_update_key_required(destination='indicator_definitions')
def create_definition_version(version_id=None):
    payload = request.get_json(silent=True) or {}
    cancer_key = payload.get('cancer_key')
    revising = version_id is not None
    updating = request.method == 'PUT'
    if updating and (not version_id or not version_id.isdecimal() or not 0 < int(version_id) <= 2147483647):
        return jsonify({'ok': False, 'error': '原始指標定義無法直接更新，請建立新版本。'}), 400
    name = str(payload.get('name') or '').strip()
    definition_year = _definition_year(payload.get('definition_year'))
    if definition_year is not None and not updating:
        name = f'{definition_year} 年度指標定義'
    description = _definition_text(payload.get('description'), '版本說明')
    reason = _definition_text(payload.get('reason'), '本次修改原因', required=updating)
    if not revising and len(name) > 100:
        return jsonify({'ok': False, 'error': '請輸入 100 字以內的版本名稱。'}), 400
    try:
        definition, source_version = load_definition(
            version_id if revising else payload.get('base_version'), get_conn, allow_unpublished=True
        )
        if updating and payload.get('fingerprint') != _definition_fingerprint(definition, source_version):
            return jsonify({'ok': False, 'error': '此版本已被其他人修改，請重新整理並確認後再編輯。'}), 409
        edits = payload.get('cancer_edits')
        if edits is None:
            edits = {cancer_key: {'changes': payload.get('changes'), 'descriptions': payload.get('descriptions')}}
        if not isinstance(edits, dict) or not edits or len(edits) > len(CANCER_SPECS):
            raise ValueError('請確認要儲存的癌別。')
        for cancer_key, edit in edits.items():
            if not isinstance(cancer_key, str) or cancer_key not in CANCER_SPECS or not isinstance(edit, dict):
                raise ValueError('找不到指定的癌別。')
            baseline = definition[cancer_key] if cancer_key in definition else default_rules(cancer_key)
            rules = apply_changes(baseline, edit.get('changes'))
            rule_trees = edit.get('rule_trees', {})
            if not isinstance(rule_trees, dict) or len(rule_trees) > len(rules):
                raise ValueError('指標條件格式不正確。')
            for number_text, sections in rule_trees.items():
                if not str(number_text).isdecimal() or int(number_text) not in rules or not isinstance(sections, dict):
                    raise ValueError('指標條件編號不正確。')
                number = int(number_text)
                if not set(sections).issubset({'numerator', 'denominator'}):
                    raise ValueError('指標分子或分母條件格式不正確。')
                for section, tree in sections.items():
                    rules[number][section] = validate_rule_tree(tree, baseline[number][section])
            removed = edit.get('removed_indicators', [])
            new_items = edit.get('new_indicators', [])
            if not isinstance(new_items, list) or len(new_items) > 30:
                raise ValueError(f'{get_cancer_label(cancer_key)}：新增指標最多 30 項。')
            if (not isinstance(removed, list) or any(type(number) is not int or number not in rules for number in removed)
                    or len(set(removed)) != len(removed)):
                raise ValueError(f'{get_cancer_label(cancer_key)}：刪除的指標清單不正確。')
            for number in removed:
                del rules[number]
            descriptions = edit.get('descriptions')
            if not isinstance(descriptions, list) or len(descriptions) != len(rules):
                raise ValueError(f'{get_cancer_label(cancer_key)}：請確認各指標的名稱與分子、分母說明。')
            seen = set()
            for item in descriptions:
                if not isinstance(item, dict) or type(item.get('id')) is not int or item['id'] not in rules or item['id'] in seen:
                    raise ValueError('指標說明格式不正確。')
                seen.add(item['id'])
                for key in ('name', 'numerator_definition', 'denominator_definition'):
                    value = item.get(key)
                    if not isinstance(value, str) or not value.strip() or len(value) > 3000:
                        raise ValueError(f'{get_cancer_label(cancer_key)}：每項指標名稱及分子、分母說明均須填寫（最多 3000 字）。')
                    rules[item['id']][key] = value.strip()
            for item in new_items:
                new_rule = build_user_indicator(item, max(rules, default=0) + 1)
                for key in ('numerator_definition', 'denominator_definition'):
                    value = new_rule.get(key, '')
                    if not value or len(value) > 3000:
                        raise ValueError(f'{get_cancer_label(cancer_key)}：新增指標的分子與分母說明均須填寫（最多 3000 字）。')
                rules[max(rules, default=0) + 1] = new_rule
            if not rules:
                raise ValueError(f'{get_cancer_label(cancer_key)}：至少須保留或新增一項指標。')
            definition[cancer_key] = rules
        definition = _snapshot_definition_texts(definition)
        _require_complete_definition(definition)
    except (ValueError, TypeError) as error:
        return jsonify({'ok': False, 'error': str(error)}), 400
    conn = get_conn()
    try:
        cursor = conn.cursor()
        if updating:
            cursor.execute(
                'SELECT rules_json, status, version_description, version_name, definition_year, updated_at FROM dbo.IndicatorDefinitionVersion '
                'WITH (UPDLOCK, HOLDLOCK) WHERE version_id = ?', (int(version_id),)
            )
            current = cursor.fetchone()
            if not current or _locked_version_fingerprint(version_id, current) != payload.get('fingerprint'):
                conn.rollback()
                return jsonify({'ok': False, 'error': '此版本已被修改或刪除，請重新整理後再試。'}), 409
            current_status = str(current[1] or 'DRAFT').upper()
            if current_status not in {'DRAFT', 'PENDING', 'INACTIVE'}:
                conn.rollback()
                return jsonify({'ok': False, 'error': '已啟用的版本不可直接修改；請停用後編輯，或建立新版本。'}), 409
            name = source_version['name']
            new_rules_json = json.dumps(definition, ensure_ascii=False)
            updated_status = 'PENDING' if current_status == 'INACTIVE' else current_status
            cursor.execute(
                'UPDATE dbo.IndicatorDefinitionVersion SET rules_json = ?, version_description = ?, '
                'updated_by = ?, updated_at = SYSUTCDATETIME(), status = ? WHERE version_id = ?',
                (new_rules_json, description, str(session.get('id') or session.get('userid') or ''), updated_status, int(version_id)),
            )
            new_id = int(version_id)
            _record_definition_history(
                cursor, version_id=new_id, action='UPDATED', status_before=current_status, status_after=updated_status,
                rules_before=current[0], rules_after=new_rules_json, reason=reason,
            )
        elif revising:
            cursor.execute('SELECT version_name FROM dbo.IndicatorDefinitionVersion WITH (UPDLOCK, HOLDLOCK)')
            existing_names = [row[0] for row in cursor.fetchall()]
            name = (_annual_definition_name(definition_year, existing_names)
                    if definition_year is not None else next_revision_name(source_version, existing_names))
        else:
            cursor.execute('SELECT 1 FROM dbo.IndicatorDefinitionVersion WHERE version_name = ?', (name,))
            if cursor.fetchone():
                return jsonify({'ok': False, 'error': '整套版本名稱已存在，請使用其他名稱或更新為修訂版。'}), 400
        if not updating:
            new_rules_json = json.dumps(definition, ensure_ascii=False)
            cursor.execute(
                'INSERT INTO dbo.IndicatorDefinitionVersion '
                '(version_name, definition_year, version_description, status, rules_json, created_by) OUTPUT INSERTED.version_id '
                'VALUES (?, ?, ?, N\'PENDING\', ?, ?)',
                (name, definition_year, description, new_rules_json, str(session.get('id') or session.get('userid') or '')),
            )
            new_id = cursor.fetchone()[0]
            _record_definition_history(
                cursor, version_id=new_id, action='REVISED' if revising else 'CREATED',
                status_after='PENDING', rules_after=new_rules_json,
                reason=reason or ('以既有版本建立並送出審核' if revising else '建立版本並送出審核'),
            )
        conn.commit()
    except ValueError as error:
        conn.rollback()
        return jsonify({'ok': False, 'error': str(error)}), 400
    finally:
        conn.close()
    write_audit_log('indicator_definition_version_updated' if updating else 'indicator_definition_version_revised' if revising else 'indicator_definition_version_created',
                    {'cancer_keys': list(edits), 'version_id': new_id, 'name': name, 'definition_year': definition_year, 'base_version': source_version['id'],
                     'cancer_edits': edits, 'reason': reason})
    return jsonify({'ok': True, 'id': str(new_id), 'name': name,
                    'definition_year': definition_year if not updating else source_version.get('definition_year'),
                    'status': 'PENDING' if not updating else updated_status})


@indicators_bp.route('/api/indicators/definition-versions/<version_id>/status', methods=['POST'])
@login_required
@data_update_key_required(destination='indicator_definitions')
@admin_required
def update_definition_version_status(version_id):
    if not version_id.isdecimal() or not 0 < int(version_id) <= 2147483647:
        return jsonify({'ok': False, 'error': '請選擇已建立的版本。'}), 400
    payload = request.get_json(silent=True) or {}
    target = str(payload.get('status') or '').upper()
    if target not in DEFINITION_STATUSES:
        return jsonify({'ok': False, 'error': '版本狀態不正確。'}), 400
    try:
        reason = _definition_text(payload.get('reason'), '狀態調整原因')
    except ValueError as error:
        return jsonify({'ok': False, 'error': str(error)}), 400
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT version_name, rules_json, status FROM dbo.IndicatorDefinitionVersion '
            'WITH (UPDLOCK, HOLDLOCK) WHERE version_id = ?', (int(version_id),)
        )
        row = cursor.fetchone()
        if not row:
            conn.rollback()
            return jsonify({'ok': False, 'error': '找不到所選版本。'}), 404
        current = str(row[2] or 'DRAFT').upper()
        if target not in DEFINITION_STATUS_TRANSITIONS.get(current, frozenset()):
            conn.rollback()
            return jsonify({'ok': False, 'error': f'「{current}」不可直接變更為「{target}」。'}), 409
        if target == 'PUBLISHED':
            definition = decode_definition(row[1])
            try:
                _require_complete_definition(definition)
            except ValueError as error:
                conn.rollback()
                return jsonify({'ok': False, 'error': str(error)}), 400
        actor = str(session.get('id') or session.get('userid') or '')
        if target == 'PUBLISHED':
            cursor.execute(
                'UPDATE dbo.IndicatorDefinitionVersion SET status = ?, updated_by = ?, updated_at = SYSUTCDATETIME(), '
                'published_by = ?, published_at = SYSUTCDATETIME() WHERE version_id = ?',
                (target, actor, actor, int(version_id)),
            )
        else:
            cursor.execute(
                'UPDATE dbo.IndicatorDefinitionVersion SET status = ?, updated_by = ?, updated_at = SYSUTCDATETIME() '
                'WHERE version_id = ?', (target, actor, int(version_id)),
            )
        _record_definition_history(
            cursor, version_id=int(version_id), action='STATUS_CHANGED', status_before=current,
            status_after=target, rules_before=row[1], rules_after=row[1], reason=reason,
        )
        conn.commit()
    finally:
        conn.close()
    write_audit_log('indicator_definition_version_status_changed', {
        'version_id': version_id, 'name': row[0], 'status_before': current,
        'status_after': target, 'reason': reason,
    })
    return jsonify({'ok': True, 'id': str(version_id), 'name': row[0], 'status': target})


@indicators_bp.route('/api/indicators/definition-versions/<version_id>/rename', methods=['POST'])
@login_required
@data_update_key_required(destination='indicator_definitions')
def rename_definition_version(version_id):
    if not version_id.isdecimal() or not 0 < int(version_id) <= 2147483647:
        return jsonify({'ok': False, 'error': '無效的指標定義版本。'}), 400
    payload = request.get_json(silent=True) or {}
    try:
        new_name = _definition_text(payload.get('name'), '版本名稱', required=True, limit=100)
    except ValueError as error:
        return jsonify({'ok': False, 'error': str(error)}), 400

    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT rules_json, status, version_description, version_name, definition_year, updated_at FROM dbo.IndicatorDefinitionVersion '
            'WITH (UPDLOCK, HOLDLOCK) WHERE version_id = ?', (int(version_id),)
        )
        row = cursor.fetchone()
        if not row:
            conn.rollback()
            return jsonify({'ok': False, 'error': '找不到指定的版本。'}), 404
        if _locked_version_fingerprint(version_id, row) != payload.get('fingerprint'):
            conn.rollback()
            return jsonify({'ok': False, 'error': '此版本已被其他人修改，請重新整理後再試。'}), 409
        old_name, rules_json, current_status = row[3], row[0], str(row[1] or 'DRAFT').upper()
        if current_status == 'PUBLISHED':
            conn.rollback()
            return jsonify({'ok': False, 'error': '已啟用的版本不可直接修改名稱，請先停用。'}), 409
        if new_name == old_name:
            conn.rollback()
            return jsonify({'ok': False, 'error': '新名稱與目前名稱相同。'}), 400
        cursor.execute(
            'SELECT 1 FROM dbo.IndicatorDefinitionVersion WITH (UPDLOCK, HOLDLOCK) '
            'WHERE version_name = ? AND version_id <> ?', (new_name, int(version_id))
        )
        if cursor.fetchone():
            conn.rollback()
            return jsonify({'ok': False, 'error': '這個版本名稱已經存在，請改用其他名稱。'}), 409
        updated_status = 'PENDING' if current_status == 'INACTIVE' else current_status
        cursor.execute(
            'UPDATE dbo.IndicatorDefinitionVersion SET version_name = ?, updated_by = ?, '
            'updated_at = SYSUTCDATETIME(), status = ? WHERE version_id = ?',
            (new_name, str(session.get('id') or session.get('userid') or ''), updated_status, int(version_id)),
        )
        _record_definition_history(
            cursor, version_id=int(version_id), action='RENAMED',
            status_before=current_status, status_after=updated_status,
            rules_before=rules_json, rules_after=rules_json,
            reason=f'版本名稱由「{old_name}」改為「{new_name}」。',
        )
        conn.commit()
    finally:
        conn.close()
    write_audit_log('indicator_definition_version_renamed', {
        'version_id': version_id, 'old_name': old_name, 'name': new_name,
    })
    return jsonify({'ok': True, 'id': str(version_id), 'name': new_name, 'status': updated_status})


@indicators_bp.route('/api/indicators/definition-versions/<version_id>/history', methods=['GET'])
@login_required
@data_update_key_required(destination='indicator_definitions')
def list_definition_version_history(version_id):
    if version_id != 'default' and (not version_id.isdecimal() or not 0 < int(version_id) <= 2147483647):
        return jsonify({'ok': False, 'error': '版本不正確。'}), 400
    if version_id == 'default':
        return jsonify({'ok': True, 'history': []})
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT history_id, action, status_before, status_after, rules_before_json, rules_after_json, '
            "change_reason, COALESCE(NULLIF(u.[Name], ''), '') AS changed_by_name, h.changed_at "
            'FROM dbo.IndicatorDefinitionVersionHistory AS h '
            "LEFT JOIN dbo.Users AS u ON CONVERT(nvarchar(36), u.[ID]) = h.changed_by OR u.[UserID] = h.changed_by "
            'WHERE h.version_id = ? ORDER BY h.history_id DESC', (int(version_id),)
        )
        history = [{
            'id': row[0], 'action': row[1], 'status_before': row[2], 'status_after': row[3],
            'rules_changed': row[4] != row[5], 'reason': row[6] or '', 'changed_by': row[7] or '',
            'changed_at': row[8].replace(tzinfo=timezone.utc).isoformat() if row[8] else None,
        } for row in cursor.fetchall()]
    finally:
        conn.close()
    return jsonify({'ok': True, 'history': history})


@indicators_bp.route('/api/indicators/definition-versions/<version_id>', methods=['DELETE'])
@login_required
@data_update_key_required(destination='indicator_definitions')
def delete_definition_version(version_id):
    if not version_id.isdecimal() or not 0 < int(version_id) <= 2147483647:
        return jsonify({'ok': False, 'error': '原始指標定義不可刪除，請選擇已建立的版本。'}), 400
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT version_name, rules_json, status FROM dbo.IndicatorDefinitionVersion '
            'WITH (UPDLOCK, HOLDLOCK) WHERE version_id = ?', (int(version_id),)
        )
        row = cursor.fetchone()
        if not row:
            conn.rollback()
            return jsonify({'ok': False, 'error': '找不到所選版本。'}), 404
        current_status = str(row[2] or 'DRAFT').upper()
        if current_status == 'PUBLISHED':
            conn.rollback()
            return jsonify({'ok': False, 'error': '已發布版本不可刪除；請先停用後再決定是否刪除。'}), 409
        name = row[0]
        cursor.execute(
            'SELECT 1 FROM dbo.IndicatorAnalysisRun WHERE definition_version_id = ?', (int(version_id),)
        )
        if cursor.fetchone():
            conn.rollback()
            return jsonify({'ok': False, 'error': '此版本已用於分析紀錄，為保留結果追溯性，不能刪除；可改為停用。'}), 409
        _record_definition_history(
            cursor, version_id=int(version_id), action='DELETED', status_before=current_status,
            rules_before=row[1], reason=f'刪除{current_status}版本',
        )
        cursor.execute('DELETE FROM dbo.IndicatorDefinitionVersion WHERE version_id = ?', (int(version_id),))
        conn.commit()
    finally:
        conn.close()
    write_audit_log('indicator_definition_version_deleted', {'version_id': version_id, 'name': name})
    return jsonify({'ok': True})
ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".txt"}
DIAGNOSIS_DATE_CODE = "2.5"
CANONICAL_HEADER_PATTERN = re.compile(r"^\d+(?:\.\d+)*(?:$|[^0-9.])")
MAX_SESSION_SOURCES = 10
INDICATOR_NARRATIVE_PROMPT_VERSION = "2026-09-30-concise-status-summary-v10"
INDICATOR_THRESHOLD_EDITOR_POSITIONS = frozenset({"Admin", "Doctor", "Ctr"})

def _read_uploaded_file(path, extension, nrows=5000):
    options = {"dtype": str}
    if nrows is not None:
        options["nrows"] = nrows
    if extension == ".csv":
        return read_csv_with_encoding(path, **options)
    return pd.read_excel(path, **options)

def _find_diagnosis_year_column(columns):
    for column in columns:
        if str(column).strip().startswith(DIAGNOSIS_DATE_CODE):
            return column
    return None

def _extract_years(values):
    years = []
    for value in values.dropna():
        match = re.search(r"(?<!\d)((?:19|20)\d{2})", str(value))
        if match:
            years.append(int(match.group(1)))
    return sorted(set(years))

def _stored_sources():
    sources = session.get("indicators_sources") or []
    valid_sources = []
    changed = False
    for source in sources:
        if not isinstance(source, dict) or not source.get("file_id") or not source.get("path"):
            continue
        if not os.path.isfile(source["path"]):
            continue
        if source.get("header_normalized"):
            valid_sources.append(source)
            continue
        try:
            _normalize_indicator_source(source)
            changed = True
        except Exception as exc:
            current_app.logger.warning("Unable to normalize indicator source %s: %s", source.get("file_id"), exc)
        valid_sources.append(source)
    if changed or len(valid_sources) != len(sources):
        session["indicators_sources"] = valid_sources
    return valid_sources

def _normalize_indicator_source(source):
    path = source["path"]
    extension = os.path.splitext(path)[1].lower().lstrip(".")
    headers = _read_uploaded_file(path, f".{extension}", nrows=0).columns
    if source.get("header_normalized") and any(
        CANONICAL_HEADER_PATTERN.match(str(header).strip()) for header in headers
    ):
        return source
    normalized_path = validate_and_normalize_dashboard_upload(
        path,
        extension,
        "original",
        connection_factory=get_conn,
    )
    source["path"] = normalized_path
    source["header_normalized"] = True
    source["file_size"] = os.path.getsize(normalized_path)
    return source

def _source_response(source):
    return {
        "file_id": source["file_id"],
        "filename": source["filename"],
        "file_size": source.get("file_size", 0),
        "record_count": source.get("record_count", 0),
        "year_column": source.get("year_column", ""),
        "years": source.get("years", []),
        "uploaded_at": source.get("uploaded_at") or datetime.fromtimestamp(
            os.path.getmtime(source["path"])
        ).strftime("%Y/%m/%d %H:%M"),
    }

def _delete_source_file(source):
    stored_path = os.path.abspath(source.get("path") or "")
    data_root = os.path.abspath(INDICATORS_DATA_DIR)
    if not stored_path or os.path.commonpath([data_root, stored_path]) != data_root:
        return
    source_folder = os.path.dirname(stored_path)
    if os.path.isdir(source_folder):
        shutil.rmtree(source_folder)

@indicators_bp.route("/indicators")
@login_required
def indicators():
    return render_template(
        "indicators.html",
        active="indicators",
        can_manage_thresholds=session.get("position") in INDICATOR_THRESHOLD_EDITOR_POSITIONS,
        definition_cancers=_definition_cancers(),
        formats=get_formats_logic(),
    )

@indicators_bp.route("/monitoring")
@login_required
def monitoring_legacy():
    return redirect(url_for("indicators.indicators"))


@indicators_bp.route("/indicators/export-report")
@login_required
def indicators_export_report_page():
    return render_template("indicators_export_report.html", active="indicators")


@indicators_bp.route("/api/indicators/export", methods=["POST"])
@login_required
def export_indicators_report():
    payload = request.get_json(silent=True) or {}
    format_pdf = bool(payload.get("format_pdf", True))
    format_word = bool(payload.get("format_word", False))
    charts = payload.get("charts") or []
    if not isinstance(charts, list) or not charts:
        return jsonify({"ok": False, "error": "沒有監測指標資料可匯出。"}), 400
    if any(
        chart.get("includeAi", True) and not str(chart.get("llmText") or "").strip()
        for chart in charts
        if isinstance(chart, dict)
    ):
        return jsonify({"ok": False, "error": "請先產生分析敘述，再進行預覽或下載!!"}), 400
    if not format_pdf and not format_word:
        return jsonify({"ok": False, "error": "請至少選擇一種匯出格式。"}), 400

    output_dir = os.path.join(INDICATORS_DATA_DIR, "exports")
    try:
        file_obj, mimetype, download_name = generate_indicator_export_files(
            format_pdf,
            format_word,
            charts,
            output_dir,
        )
        if not file_obj:
            return jsonify({"ok": False, "error": "無法產生監測指標匯出檔案。"}), 500
        return send_file(
            file_obj,
            mimetype=mimetype,
            as_attachment=True,
            download_name=download_name,
        )
    except Exception as exc:
        current_app.logger.exception("Monitoring-indicator export failed")
        return jsonify({"ok": False, "error": str(exc)}), 500


@indicators_bp.route("/api/indicators/export-excel", methods=["POST"])
@login_required
def export_indicators_excel():
    source = session.get("indicators_source") or {}
    if source:
        _normalize_indicator_source(source)
        session["indicators_source"] = source
    stored_path = source.get("path")
    if not stored_path or not os.path.isfile(stored_path):
        return jsonify({"ok": False, "error": "請先上傳要匯出的資料檔。"}), 400

    payload = request.get_json(silent=True) or {}
    cancers = payload.get("cancers") or []
    try:
        year_start = int(payload.get("year_start"))
        year_end = int(payload.get("year_end"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "請選擇起始與結束診斷年度。"}), 400
    if year_start > year_end or not cancers:
        return jsonify({"ok": False, "error": "請確認診斷年度區間與癌別選擇。"}), 400

    extension = os.path.splitext(stored_path)[1].lower()
    try:
        dataframe = _read_uploaded_file(stored_path, extension, nrows=None)
        rules_by_cancer, _ = _selected_rule_versions(payload, cancers)
        export_frame = build_indicators_export_frame(
            dataframe,
            cancers,
            year_start,
            year_end,
            cancer_label_getter=get_cancer_label,
            rules_by_cancer=rules_by_cancer,
        )
        file_obj = create_indicators_excel(export_frame, len(dataframe.columns))
        return send_file(
            file_obj,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="indicators_data.xlsx",
        )
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Monitoring-indicator Excel export failed")
        return jsonify({"ok": False, "error": f"產生 Excel 失敗：{exc}"}), 500

@indicators_bp.route("/api/monitoring/upload", methods=["POST"])
@indicators_bp.route("/api/indicators/upload", methods=["POST"])
@login_required
def upload_indicators_source():
    uploaded_file = request.files.get("file")
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({"ok": False, "error": "請選擇要分析的資料檔。"}), 400

    original_name = uploaded_file.filename
    extension = os.path.splitext(original_name)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        return jsonify({"ok": False, "error": "請上傳 Excel、CSV 或 TXT 檔案。"}), 400

    input_scheme = str(request.form.get("input_scheme", "")).strip()
    format_id = str(request.form.get("format_id", "")).strip()
    txt_has_header = str(request.form.get("txt_has_header", "")).strip().lower() == "true"
    if not format_id:
        return jsonify({"ok": False, "error": "請選擇申報欄位格式。"}), 400
    extra_fields_raw = request.form.get("extra_fields")
    try:
        extra_fields = json.loads(extra_fields_raw) if extra_fields_raw is not None else None
    except json.JSONDecodeError:
        return jsonify({"ok": False, "error": "未匹配欄位設定格式不正確。"}), 400
    if extra_fields is not None and not isinstance(extra_fields, list):
        return jsonify({"ok": False, "error": "未匹配欄位設定格式不正確。"}), 400

    sources = _stored_sources()
    if len(sources) >= MAX_SESSION_SOURCES:
        return jsonify({"ok": False, "error": f"檔案清單最多保留 {MAX_SESSION_SOURCES} 個檔案，請先刪除不需要的檔案。"}), 400

    safe_name = secure_filename(original_name) or f"indicators_source{extension}"
    file_id = str(uuid.uuid4())
    folder = os.path.join(INDICATORS_DATA_DIR, file_id)
    stored_path = os.path.join(folder, safe_name)

    try:
        os.makedirs(folder, exist_ok=True)
        uploaded_file.save(stored_path)
        stored_path = validate_and_normalize_dashboard_upload(
            stored_path,
            extension.lstrip("."),
            input_scheme,
            connection_factory=get_conn,
            extra_fields=extra_fields,
            format_id=format_id,
            txt_has_header=txt_has_header,
        )
        extension = os.path.splitext(stored_path)[1].lower()
        dataframe = _read_uploaded_file(stored_path, extension, nrows=None)
        year_column = _find_diagnosis_year_column(dataframe.columns)
        years = _extract_years(dataframe[year_column]) if year_column is not None else []
    except Exception as exc:
        if os.path.isdir(folder):
            shutil.rmtree(folder, ignore_errors=True)
        return jsonify({"ok": False, "error": f"無法讀取資料檔：{exc}"}), 400

    if not years:
        shutil.rmtree(folder, ignore_errors=True)
        return jsonify({"ok": False, "error": "找不到可用的診斷年度欄位，請確認資料欄位內容。"}), 400

    source = {
        "file_id": file_id,
        "filename": original_name,
        "path": stored_path,
        "file_size": os.path.getsize(stored_path),
        "record_count": int(len(dataframe)),
        "year_column": str(year_column) if year_column is not None else "",
        "years": years,
        "uploaded_at": datetime.now().strftime("%Y/%m/%d %H:%M"),
        "header_normalized": True,
    }
    sources.append(source)
    session["indicators_sources"] = sources
    session["indicators_source"] = source
    return jsonify({"ok": True, **_source_response(source)})


@indicators_bp.route("/api/indicators/input-preview", methods=["POST"])
@login_required
def preview_indicators_input():
    uploaded_file = request.files.get("file")
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({"ok": False, "error": "請選擇檔案。"}), 400
    extension = uploaded_file.filename.rsplit(".", 1)[-1].lower() if "." in uploaded_file.filename else ""
    if extension not in {"txt", "csv", "xls", "xlsx"}:
        return jsonify({"ok": False, "error": "僅支援 .txt、.csv、.xls 或 .xlsx 檔案。"}), 400
    input_scheme = str(request.form.get("input_scheme", "")).strip()
    format_id = str(request.form.get("format_id", "")).strip()
    txt_has_header = str(request.form.get("txt_has_header", "")).strip().lower() == "true"
    if not format_id:
        return jsonify({"ok": False, "error": "請選擇申報欄位格式。"}), 400
    try:
        result = preview_dashboard_upload(
            uploaded_file.stream,
            extension,
            input_scheme,
            get_conn,
            format_id=format_id,
            txt_has_header=txt_has_header,
        )
        return jsonify({"ok": True, **result})
    except ValueError as error:
        return jsonify({"ok": False, "error": str(error)}), 400

@indicators_bp.route("/api/indicators/sources", methods=["GET"])
@login_required
def list_indicators_sources():
    active_source = session.get("indicators_source") or {}
    return jsonify({"ok": True,"active_file_id": active_source.get("file_id"),"sources": [_source_response(source) for source in _stored_sources()],})

@indicators_bp.route("/api/indicators/source/<file_id>/activate", methods=["POST"])
@login_required
def activate_indicators_source(file_id):
    source = next((item for item in _stored_sources() if item["file_id"] == file_id), None)
    if source is None:
        return jsonify({"ok": False, "error": "找不到指定的檔案，請重新上傳。"}), 404
    session["indicators_source"] = source
    return jsonify({"ok": True, **_source_response(source)})


@indicators_bp.route("/api/indicators/source/<file_id>", methods=["DELETE"])
@login_required
def delete_indicators_source(file_id):
    sources = _stored_sources()
    source = next((item for item in sources if item["file_id"] == file_id), None)
    if source is None:
        return jsonify({"ok": False, "error": "找不到指定的檔案。"}), 404

    try:
        _delete_source_file(source)
    except OSError as exc:
        return jsonify({"ok": False, "error": f"無法刪除檔案：{exc}"}), 500

    session["indicators_sources"] = [item for item in sources if item["file_id"] != file_id]
    active_source = session.get("indicators_source") or {}
    if active_source.get("file_id") == file_id:
        session.pop("indicators_source", None)
    return jsonify({"ok": True})


@indicators_bp.route("/api/indicators/sources", methods=["DELETE"])
@login_required
def batch_delete_indicators_sources():
    payload = request.get_json(silent=True) or {}
    file_ids = payload.get("file_ids") or []
    if not isinstance(file_ids, list):
        return jsonify({"ok": False, "error": "刪除項目格式不正確。"}), 400

    selected_ids = {str(file_id).strip() for file_id in file_ids if str(file_id).strip()}
    if not selected_ids:
        return jsonify({"ok": False, "error": "請先勾選欲刪除的檔案。"}), 400

    sources = _stored_sources()
    selected_sources = [source for source in sources if source["file_id"] in selected_ids]
    if not selected_sources:
        return jsonify({"ok": False, "error": "找不到指定的檔案。"}), 404

    try:
        for source in selected_sources:
            _delete_source_file(source)
    except OSError as exc:
        return jsonify({"ok": False, "error": f"無法刪除檔案：{exc}"}), 500

    deleted_ids = {source["file_id"] for source in selected_sources}
    session["indicators_sources"] = [source for source in sources if source["file_id"] not in deleted_ids]
    active_source = session.get("indicators_source") or {}
    if active_source.get("file_id") in deleted_ids:
        session.pop("indicators_source", None)
    return jsonify({"ok": True, "deleted": len(deleted_ids)})


@indicators_bp.route("/api/indicators/thresholds", methods=["POST"])
@position_required(
    *INDICATOR_THRESHOLD_EDITOR_POSITIONS,
    error_message="權限不足，只有管理員、醫師或癌登師可以修改閾值。",
)
def save_indicator_threshold():
    payload = request.get_json(silent=True) or {}
    cancer_key = str(payload.get("cancer_key") or "").strip()
    try:
        indicator_no = int(payload.get("indicator_no"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "指標編號格式不正確。"}), 400

    if cancer_key not in CANCER_SPECS or indicator_no < 1:
        return jsonify({"ok": False, "error": "找不到指定的癌別或監測指標。"}), 404
    rule = get_indicator_rules(cancer_key).get(indicator_no)
    direction = (rule or {}).get("type") or str(payload.get("direction") or "positive")
    if direction not in {"positive", "negative", "observation"}:
        return jsonify({"ok": False, "error": "指標屬性不正確。"}), 400
    default_operator = "<=" if direction == "negative" else ">="
    target_raw = payload.get("target_value")
    if target_raw is None or str(target_raw).strip() == "":
        target_value = None
        target_operator = None
    else:
        try:
            target_value = round(float(target_raw), 2)
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "閾值必須是數字。"}), 400
        if not math.isfinite(target_value) or not 0 <= target_value <= 100:
            return jsonify({"ok": False, "error": "閾值必須介於 0 至 100。"}), 400
        target_operator = str(payload.get("target_operator") or default_operator).strip()
        if target_operator not in {">=", ">", "<=", "<", "="}:
            return jsonify({"ok": False, "error": "閾值比較方式不正確。"}), 400

    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE dbo.Indicator_definition_metadata SET target_value = ?, target_operator = ? "
            "WHERE cancer_group_key = ? AND indicator_no = ?",
            (target_value, target_operator, cancer_key, indicator_no),
        )
        if cursor.rowcount == 0:
            cursor.execute(
                "INSERT INTO dbo.Indicator_definition_metadata "
                "(cancer_group_key, indicator_no, target_value, target_operator) VALUES (?, ?, ?, ?)",
                (cancer_key, indicator_no, target_value, target_operator),
            )
        conn.commit()
    finally:
        conn.close()

    write_audit_log(
        "indicators_threshold_update",
        {
            "cancer_key": cancer_key,
            "indicator_no": indicator_no,
            "target_value": target_value,
            "target_operator": target_operator,
        },
    )
    return jsonify({
        "ok": True,
        "cancer_key": cancer_key,
        "indicator_no": indicator_no,
        "target_value": target_value,
        "target_operator": target_operator or default_operator,
    })


@indicators_bp.route("/api/indicators/narrative-job", methods=["POST"])
@login_required
def create_indicators_narrative_job():
    payload = request.get_json(silent=True) or {}
    items = payload.get("items") or []
    if not isinstance(items, list) or not items:
        return jsonify({"ok": False, "error": "沒有可產生敘述的監測指標。"}), 400
    if len(items) > 20:
        return jsonify({"ok": False, "error": "一次最多產生 20 個癌別的監測指標敘述。"}), 400

    mode_ai = str(payload.get("mode_ai") or "balanced").strip()
    if mode_ai not in {"balanced", "formal", "concise"}:
        return jsonify({"ok": False, "error": "敘述風格不正確。"}), 400

    normalized_items = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict) or not isinstance(item.get("data"), dict):
            return jsonify({"ok": False, "error": "監測指標敘述資料格式不正確。"}), 400
        indicators = item["data"].get("indicators")
        if not isinstance(indicators, list) or not indicators:
            return jsonify({"ok": False, "error": "沒有可產生敘述的監測指標。"}), 400
        if any(
            not isinstance(indicator, dict)
            or not str(indicator.get("threshold") or "").strip()
            or str(indicator.get("threshold") or "").strip() == "尚未設定"
            for indicator in indicators
        ):
            return jsonify({"ok": False, "error": "請先完成所有監測指標的閾值設定。"}), 400
        normalized_items.append({
            "item_id": str(item.get("item_id") or f"indicators-{index}"),
            "insight_module": "indicators",
            "field_key": str(item.get("field_key") or "監測指標分析"),
            "data": item["data"],
            "fields": [],
            "mode_ai": mode_ai,
            "year_start": str(payload.get("year_start") or ""),
            "year_end": str(payload.get("year_end") or ""),
            "language": "zh-TW",
        })

    task_payload = {
        "items": normalized_items,
        "insight_module": "indicators",
        "prompt_version": INDICATOR_NARRATIVE_PROMPT_VERSION,
        "mode_ai": mode_ai,
        "year_start": str(payload.get("year_start") or ""),
        "year_end": str(payload.get("year_end") or ""),
        "_document_label": "監測指標分析",
        "job_title": "監測指標分析",
    }
    request_signature = {
        "insight_module": "indicators",
        "prompt_version": INDICATOR_NARRATIVE_PROMPT_VERSION,
        "mode_ai": mode_ai,
        "year_start": task_payload["year_start"],
        "year_end": task_payload["year_end"],
        "items": [
            {"field_key": item["field_key"], "data": item["data"]}
            for item in normalized_items
        ],
    }
    request_key = hashlib.sha256(
        json.dumps(request_signature, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    task_payload["_request_key"] = request_key

    if not bool(payload.get("force")):
        existing = find_reusable_llm_task(session.get("id"), "indicator_report", request_key)
        if not existing:
            # Reuse monitoring tasks created before they received a dedicated task type.
            existing = find_reusable_llm_task(session.get("id"), "annual_report", request_key)
        if existing:
            existing_payload = get_llm_task_payload(existing["TaskID"], session.get("id")) or {}
            return jsonify({
                "ok": True,
                "reused": True,
                "task_id": existing["TaskID"],
                "status": existing["Status"],
                "progress_current": existing["ProgressCurrent"],
                "progress_total": existing["ProgressTotal"],
                "item_ids": [item.get("item_id") for item in existing_payload.get("items", [])],
            }), 200

    created = create_llm_task(session.get("id"), "indicator_report", task_payload)
    return jsonify({
        "ok": True,
        "reused": False,
        "item_ids": [item["item_id"] for item in normalized_items],
        **created,
    }), 202

@indicators_bp.route("/api/monitoring/preview", methods=["POST"])
@indicators_bp.route("/api/indicators/preview", methods=["POST"])
@login_required
def preview_indicators():
    source = session.get("indicators_source") or {}
    if source:
        _normalize_indicator_source(source)
        session["indicators_source"] = source
    stored_path = source.get("path")
    if not stored_path or not os.path.isfile(stored_path):
        return jsonify({"ok": False, "error": "請先上傳要分析的資料檔。"}), 400

    payload = request.get_json(silent=True) or {}
    cancers = payload.get("cancers") or []
    year_start = payload.get("year_start")
    year_end = payload.get("year_end")
    try:
        year_start, year_end = int(year_start), int(year_end)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "請選擇起始與結束診斷年度。"}), 400
    if year_start > year_end or not cancers:
        return jsonify({"ok": False, "error": "請確認診斷年度區間與癌別選擇。"}), 400

    extension = os.path.splitext(stored_path)[1].lower()
    try:
        dataframe = _read_uploaded_file(stored_path, extension, nrows=None)
        rules_by_cancer, versions = _selected_rule_versions(payload, cancers)
        result = run_indicators_analysis(dataframe, cancers, year_start, year_end, rules_by_cancer=rules_by_cancer)
        analysis_run_id = _record_indicator_analysis_run(
            cancers=cancers, year_start=year_start, year_end=year_end,
            rules_by_cancer=rules_by_cancer, versions=versions, result=result,
        )
        for report in result.get('reports', []):
            report['rule_version'] = versions.get(report['cancer_key'])
            report['analysis_run_id'] = analysis_run_id
        result['analysis_run_id'] = analysis_run_id
        write_audit_log('indicator_analysis_recorded', {
            'analysis_run_id': analysis_run_id,
            'year_start': year_start, 'year_end': year_end,
            'cancers': list(dict.fromkeys(cancers)),
            'definition_version_id': next(iter(versions.values()), {}).get('id'),
        })
    except ValueError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": f"產生指標內容失敗：{exc}"}), 500
    return jsonify(result), (200 if result.get("ok") else 400)


@indicators_bp.route('/api/indicators/analysis-runs/<run_id>', methods=['GET'])
@login_required
def get_indicator_analysis_run(run_id):
    """Return a persisted analysis snapshot for its owner or a maintenance user."""
    if not run_id.isdecimal() or not 0 < int(run_id):
        return jsonify({'ok': False, 'error': '分析紀錄編號不正確。'}), 400
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT run_id, user_id, created_at, year_start, year_end, cancer_keys_json, '
            'definition_version_id, definition_version_name, definition_snapshot_json, result_snapshot_json '
            'FROM dbo.IndicatorAnalysisRun WHERE run_id = ?', (int(run_id),)
        )
        row = cursor.fetchone()
    finally:
        conn.close()
    if not row:
        return jsonify({'ok': False, 'error': '找不到分析紀錄。'}), 404
    current_user_id = str(session.get('id') or session.get('userid') or '')
    if row[1] != current_user_id and not has_data_update_access():
        return jsonify({'ok': False, 'error': '沒有權限查看此分析紀錄。'}), 403
    return jsonify({
        'ok': True,
        'run': {
            'id': str(row[0]), 'user_id': row[1],
            'created_at': _analysis_run_timestamp(row[2]),
            'year_start': row[3], 'year_end': row[4],
            'cancers': json.loads(row[5]),
            'definition_version_id': str(row[6]) if row[6] is not None else 'default',
            'definition_version_name': row[7],
            'definition_snapshot': json.loads(row[8]),
            'result_snapshot': json.loads(row[9]),
        },
    })


@indicators_bp.route('/api/indicators/analysis-runs', methods=['GET'])
@login_required
def list_indicator_analysis_runs():
    """List recent saved analysis snapshots for the current user."""
    current_user_id = str(session.get('id') or session.get('userid') or '')
    can_view_all = has_data_update_access()
    conn = get_conn()
    try:
        cursor = conn.cursor()
        if can_view_all:
            cursor.execute(
                'SELECT TOP (100) run_id, user_id, created_at, year_start, year_end, '
                'cancer_keys_json, definition_version_name '
                'FROM dbo.IndicatorAnalysisRun ORDER BY created_at DESC, run_id DESC'
            )
        else:
            cursor.execute(
                'SELECT TOP (100) run_id, user_id, created_at, year_start, year_end, '
                'cancer_keys_json, definition_version_name '
                'FROM dbo.IndicatorAnalysisRun WHERE user_id = ? '
                'ORDER BY created_at DESC, run_id DESC', (current_user_id,)
            )
        rows = cursor.fetchall()
    except Exception as exc:
        return jsonify({'ok': False, 'error': f'讀取分析紀錄失敗：{exc}'}), 500
    finally:
        conn.close()
    return jsonify({
        'ok': True,
        'can_view_all': can_view_all,
        'runs': [{
            'id': str(row[0]), 'user_id': row[1],
            'created_at': _analysis_run_timestamp(row[2]),
            'year_start': row[3], 'year_end': row[4],
            'cancers': json.loads(row[5]),
            'definition_version_name': row[6],
        } for row in rows],
    })
