"""One immutable definition version contains the rules for multiple cancers."""
from __future__ import annotations

import json

from modules.blueprint.indicators.catalog import CANCER_SPECS
from modules.blueprint.indicators.rule_versions import default_rules, decode_rules


def default_definition():
    return {key: default_rules(key) for key in CANCER_SPECS}


def _merge_system_metadata(rules, connection_factory):
    """Overlay legacy database descriptions onto the built-in system rules."""
    conn = connection_factory()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT cancer_group_key, indicator_no, selection_reason, numerator_definition, '
            'denominator_definition, notes, target_value, target_operator '
            'FROM dbo.Indicator_definition_metadata'
        )
        for row in cursor.fetchall():
            cancer_key, indicator_no = str(row[0]), int(row[1])
            rule = rules.get(cancer_key, {}).get(indicator_no)
            if rule is None:
                continue
            # Use database rationale and notes where present. Fill blank
            # definitions while preserving any newer, explicitly authored
            # system wording (for example, corrected oral-cavity definitions).
            for field, value in (
                ('selection_reason', row[2]),
                ('notes', row[5]),
            ):
                if value is not None and str(value).strip():
                    rule[field] = str(value).strip()
            for field, value in (
                ('numerator_definition', row[3]),
                ('denominator_definition', row[4]),
            ):
                if not str(rule.get(field) or '').strip() and value is not None and str(value).strip():
                    rule[field] = str(value).strip()
            if rule.get('target_value') is None and row[6] is not None:
                rule['target_value'] = float(row[6])
            if not rule.get('target_operator') and row[7]:
                rule['target_operator'] = str(row[7]).strip()
    finally:
        conn.close()
    return rules


def decode_definition(raw):
    data = json.loads(raw)
    if not isinstance(data, dict) or not data or any(key not in CANCER_SPECS for key in data):
        raise ValueError('整套指標定義版本的內容不正確。')
    decoded = {}
    for cancer_key, rules in data.items():
        rules = decode_rules(json.dumps(rules))
        if (not rules or any(
            type(number) is not int or number < 1 or not isinstance(rule, dict)
            # Keep the legacy ``unspecified`` category used by an existing
            # built-in indicator (Cervix_Uteri #5). New indicators created in
            # the UI still require one of the three explicit categories.
            or rule.get('type') not in {'positive', 'negative', 'observation', 'unspecified'}
            or not isinstance(rule.get('name'), str) or not rule['name'].strip()
            or not isinstance(rule.get('numerator'), dict)
            or not isinstance(rule.get('denominator'), dict)
            for number, rule in rules.items()
        )):
            raise ValueError('整套指標定義版本的內容不完整。')
        decoded[cancer_key] = rules
    return decoded


def load_definition(version_id, connection_factory, *, allow_unpublished=False):
    if version_id in (None, '', 'default'):
        rules = _merge_system_metadata(default_definition(), connection_factory)
        return rules, {
            'id': 'default', 'name': '115 年度指標定義（系統基準）', 'description': '系統內建的 115 年度指標規則。',
            'definition_year': None, 'status': 'PUBLISHED', 'cancers': list(rules), 'immutable': True,
        }
    try:
        if isinstance(version_id, bool):
            raise ValueError
        number = int(str(version_id))
        if not 0 < number <= 2147483647:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError('指標定義版本不正確。') from None
    conn = connection_factory()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT version_name, definition_year, rules_json, version_description, status, created_by, created_at, '
            'updated_by, updated_at, published_by, published_at '
            'FROM dbo.IndicatorDefinitionVersion WHERE version_id = ?',
            (number,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError('找不到所選的整套指標定義版本。')
        status = str(row[4] or 'DRAFT').upper()
        if not allow_unpublished and status != 'PUBLISHED':
            raise ValueError('所選指標定義版本尚未發布，無法用於分析。')
        rules = decode_definition(row[2])
        return rules, {
            'id': str(number), 'name': row[0], 'definition_year': row[1],
            'description': row[3] or '', 'status': status,
            'created_by': row[5] or '', 'created_at': row[6].isoformat() if row[6] else None,
            'updated_by': row[7] or '', 'updated_at': row[8].isoformat() if row[8] else None,
            'published_by': row[9] or '', 'published_at': row[10].isoformat() if row[10] else None,
            'cancers': list(rules), 'immutable': status != 'DRAFT',
        }
    finally:
        conn.close()
