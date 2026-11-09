"""Cancer-specific immutable rule snapshots and numeric-condition edits."""
from __future__ import annotations

import copy
import json
import re

from modules.blueprint.indicators.catalog import CANCER_SPECS

COMPARISONS = frozenset({'equals', 'between', 'greater_than', 'greater_than_or_equal', 'less_than', 'less_than_or_equal'})
NEW_INDICATOR_TYPES = frozenset({'positive', 'negative', 'observation'})
DATE_RULE_FIELDS = frozenset({
    '2.5', '2.12', '4.1', '4.1.1', '4.1.2', '4.2.1.3',
    '4.3.4', '4.3.10', '4.3.15', '5.3',
})
NUMERIC_FIELD_OPERATIONS = COMPARISONS | {'in', 'not_in'}

# The original rule declarations predate the editable maintenance metadata, so
# they do not carry a selection reason.  Provide a readable baseline reason for
# every built-in rule while still allowing each version to replace it.
SYSTEM_SELECTION_REASON_OVERRIDES = {
    ('Oral_Cavity', 1): (
        '會影響局部區域的控制：口腔癌病人接受術後輔助治療時，'
        '應於手術後 6 週內開始，以維持預期的局部控制效果。'
    ),
}

# Plain-language numerator and denominator definitions transcribed from the
# indicator table supplied for oral-cavity monitoring.
SYSTEM_INDICATOR_DEFINITION_OVERRIDES = {
    ('Oral_Cavity', 1): {
        'numerator_definition': '分母中，手術後 6 週內開始輔助治療（放射治療或化學放射治療）的人數。',
        'denominator_definition': '手術後接受輔助治療（放射治療或化學放射治療）的人數。',
    },
    ('Oral_Cavity', 2): {
        'numerator_definition': '分母中，手術後 30 天內死亡的人數。',
        'denominator_definition': '口腔癌手術的人數。（排除緩和治療。）',
    },
    ('Oral_Cavity', 3): {
        'numerator_definition': '口腔癌病人開始接受放射治療（不含化療）後 90 天內死亡的人數。',
        'denominator_definition': '口腔癌病人接受放射治療（不含化療）的人數。（排除緩和治療。）',
    },
    ('Oral_Cavity', 4): {
        'numerator_definition': '口腔癌病人開始接受同步化學治療及放射治療後 90 天內死亡的人數。',
        'denominator_definition': '口腔癌病人接受同步化學治療及放射治療的人數。（排除緩和治療。）',
    },
    ('Oral_Cavity', 5): {
        'numerator_definition': '分母中，口腔癌切除標本淋巴結病理檢查報告 15 顆（含）以上的人數。',
        'denominator_definition': '第一個癌是口腔癌且接受頸部淋巴廓清術的人數。',
    },
    ('Oral_Cavity', 6): {
        'numerator_definition': '病理切緣小於 4 mm（不包含 4 mm）。（若有多個手術切緣距離，應摘錄最近的距離。）',
        'denominator_definition': '口腔鱗狀細胞癌施行根除性手術且有紀錄病理切緣。（排除病理切緣不詳者及病理報告描述手術切緣為非侵襲癌。）',
    },
}


def _system_selection_reason(cancer_key, number, rule):
    """Return the editable baseline rationale for a built-in indicator."""
    override = SYSTEM_SELECTION_REASON_OVERRIDES.get((cancer_key, int(number)))
    if override:
        return override
    direction = rule.get('type')
    if direction == 'negative':
        return '用於監測不良治療結果或照護流程風險的發生情形，作為照護品質改善參考。'
    if direction == 'observation':
        return '用於觀察目前的臨床處置與治療分布，作為癌症照護品質分析與改善參考。'
    return '用於監測病人是否依指標條件完成建議的診斷、治療或病理評估，作為照護品質改善參考。'

# Every operation implemented by rule.py has a fixed, validated schema here.
# The UI can therefore edit rules without ever accepting executable code.
TREE_SCHEMAS = {
    **{op: {'field': 'field', 'value': 'int'} for op in COMPARISONS if op != 'between'},
    'between': {'field': 'field', 'min': 'int', 'max': 'int'},
    **{op: {'field': 'field', 'values': 'ints'} for op in ('in', 'not_in')},
    **{op: {'field': 'field', 'values': 'strings'} for op in (
        'text_in', 'text_not_in', 'code_in', 'code_prefix_in', 'stage_in',
        'text_starts_with', 'stage_first_char_in', 'first_char_in',
    )},
    **{op: {'field': 'field', 'value': 'string'} for op in ('text_equals', 'text_not_equals')},
    'text_in_without_prefix': {'field': 'field', 'prefix': 'string', 'values': 'strings'},
    'zero_fill_text_in': {'field': 'field', 'width': 'positive_int', 'values': 'strings'},
    'all_fields_not_in': {'fields': 'fields', 'values': 'strings'},
    'concatenated_text_in': {'fields': 'fields', 'values': 'strings'},
    'preferred_stage_in': {
        'preferred_field': 'field', 'fallback_field': 'field',
        # 空字串是既有規則用來表示「期別欄位空白」的合法值。
        'invalid_values': 'strings_allow_blank', 'values': 'strings',
    },
    'stage_matches': {'field': 'field', 'pattern': 'pattern'},
    **{op: {'field': 'field'} for op in ('present', 'valid_date')},
    **{op: {'start_field': 'field', 'end_field': 'field'} for op in ('date_after', 'date_on_or_after')},
    'dates_equal': {'left_field': 'field', 'right_field': 'field'},
    'date_interval': {'start_field': 'field', 'end_field': 'field', 'min_days': 'int', 'max_days': 'int'},
    'date_year_between': {'field': 'field', 'min': 'int', 'max': 'int'},
    **{op: {'reference_field': 'field', 'candidate_fields': 'fields', 'min_days': 'int', 'max_days': 'int'}
       for op in ('earliest_after_within', 'earliest_on_or_after_within')},
    'any_date_on_or_after': {'reference_field': 'field', 'candidate_fields': 'fields'},
    'earliest_date_interval': {'start_fields': 'fields', 'end_field': 'field', 'min_days': 'int', 'max_days': 'int'},
    'bed_at_least': {'courses': 'courses', 'value': 'number', 'alpha_beta': 'positive_number_optional'},
}


def validate_rule_tree(tree, original=None):
    """Validate a rule tree without interpreting user-provided code."""
    from modules.blueprint.indicators.indicator_definitions import RULE_FIELD_LABELS
    fields = set(RULE_FIELD_LABELS)
    retained = []

    def collect(node):
        if not isinstance(node, dict):
            return
        retained.append(node)
        for child in node.get('rules', []):
            collect(child)
        collect(node.get('rule'))

    collect(original)
    count = 0

    def validate(node, depth=0):
        nonlocal count
        count += 1
        if count > 200 or depth > 12 or not isinstance(node, dict):
            raise ValueError('條件層數或數量超出限制，或格式不正確。')
        if node in retained:
            return copy.deepcopy(node)
        op = node.get('op')
        if op in ('all', 'any'):
            if set(node) != {'op', 'rules'} or not isinstance(node['rules'], list) or not 1 <= len(node['rules']) <= 30:
                raise ValueError('每組且/或條件至少需要一項，最多 30 項。')
            return {'op': op, 'rules': [validate(child, depth + 1) for child in node['rules']]}
        if op == 'not':
            if set(node) != {'op', 'rule'}:
                raise ValueError('排除條件格式不正確。')
            return {'op': op, 'rule': validate(node['rule'], depth + 1)}
        schema = TREE_SCHEMAS.get(op)
        if schema is None:
            if node in retained:
                return copy.deepcopy(node)
            raise ValueError('不支援的條件類型，請保留原有特殊條件。')
        allowed_keys = {'op', *schema}
        required_keys = allowed_keys - ({'alpha_beta'} if 'alpha_beta' in schema else set())
        if set(node) != allowed_keys and set(node) != required_keys:
            raise ValueError('條件欄位不完整或格式不正確。')
        result = {'op': op}
        for key, kind in schema.items():
            # alpha/beta 是 BED 規則的選填參數；省略時保持原始結構。
            if kind == 'positive_number_optional' and key not in node:
                continue
            value = node.get(key)
            if kind == 'field':
                if not isinstance(value, str) or value not in fields:
                    raise ValueError('請選擇有效的癌登欄位。')
            elif kind == 'fields':
                if not isinstance(value, list) or not 1 <= len(value) <= 20 or any(not isinstance(v, str) or v not in fields for v in value) or len(set(value)) != len(value):
                    raise ValueError('日期欄位清單不正確或有重複。')
            elif kind == 'int':
                if type(value) is not int or abs(value) > 1000000:
                    raise ValueError('條件數值必須是有效整數。')
            elif kind == 'positive_int':
                if type(value) is not int or not 1 <= value <= 1000000:
                    raise ValueError('條件數值必須是大於 0 的整數。')
            elif kind == 'number':
                if type(value) not in (int, float) or isinstance(value, bool) or abs(value) > 1000000:
                    raise ValueError('條件數值必須是有效數字。')
            elif kind == 'positive_number_optional':
                if value is not None and (type(value) not in (int, float) or isinstance(value, bool) or not 0 < value <= 1000000):
                    raise ValueError('alpha/beta 必須是大於 0 的數字。')
            elif kind == 'string':
                if not isinstance(value, str) or not value.strip() or len(value) > 1000:
                    raise ValueError('文字條件不可空白或過長。')
            elif kind == 'pattern':
                if not isinstance(value, str) or not value or len(value) > 300:
                    raise ValueError('期別格式不可空白或過長。')
                try:
                    re.compile(value)
                except re.error as error:
                    raise ValueError('期別格式不是有效的正規表示式。') from error
            elif kind == 'courses':
                if not isinstance(value, list) or not 1 <= len(value) <= 10:
                    raise ValueError('BED 療程至少要有一組，最多 10 組。')
                courses = []
                for course in value:
                    if not isinstance(course, dict) or set(course) != {'dose_field', 'fractions_field'}:
                        raise ValueError('BED 療程格式不正確。')
                    dose_field, fractions_field = course['dose_field'], course['fractions_field']
                    if (not isinstance(dose_field, str) or dose_field not in fields
                            or not isinstance(fractions_field, str) or fractions_field not in fields):
                        raise ValueError('BED 療程欄位不正確。')
                    courses.append({'dose_field': dose_field, 'fractions_field': fractions_field})
                result[key] = courses
                continue
            elif kind in ('ints', 'strings', 'strings_allow_blank'):
                if not isinstance(value, list) or not 1 <= len(value) <= 200:
                    raise ValueError('代碼清單至少需要一個值，最多 200 個。')
                if kind == 'ints' and any(type(v) is not int or abs(v) > 1000000 for v in value):
                    raise ValueError('數值代碼必須是有效整數。')
                if kind == 'strings' and any(not isinstance(v, str) or not v.strip() or len(v) > 100 for v in value):
                    raise ValueError('文字代碼格式不正確。')
                if kind == 'strings_allow_blank' and any(not isinstance(v, str) or len(v) > 100 for v in value):
                    raise ValueError('Invalid text list item.')
            result[key] = copy.deepcopy(value)
        if op in NUMERIC_FIELD_OPERATIONS and result.get('field') in DATE_RULE_FIELDS:
            raise ValueError('日期欄位不能使用數值比較，請改用日期條件（例如日期區間或日期年度範圍）。')
        for low, high in (('min', 'max'), ('min_days', 'max_days')):
            if low in result and result[low] > result[high]:
                raise ValueError('條件下限不可大於上限。')
        return result

    return validate(tree)


def next_revision_name(version, existing_names):
    """Name a new snapshot in the same revision family without overwriting one."""
    source_name = version['name']
    source_match = re.fullmatch(r'(.+)・修訂 ([1-9][0-9]*)', source_name)
    root = source_match.group(1) if source_match else source_name
    if len(root) > 84:
        root = f"{root[:70]}…#{version['id']}"
    pattern = re.compile(re.escape(root) + r'・修訂 ([1-9][0-9]*)', re.IGNORECASE)
    numbers = [int(match.group(1)) for name in existing_names if (match := pattern.fullmatch(name))]
    number = max(numbers, default=0) + 1
    if number > 2147483647:
        raise ValueError('修訂次數已超出可用範圍，請另建新版本。')
    return f'{root}・修訂 {number}'


def default_rules(cancer_key='Oral_Cavity'):
    spec = CANCER_SPECS.get(cancer_key)
    if spec is None:
        raise ValueError('找不到指定的癌別。')
    rules = copy.deepcopy(spec.rules)
    for number, rule in rules.items():
        if not str(rule.get('selection_reason') or '').strip():
            rule['selection_reason'] = _system_selection_reason(cancer_key, number, rule)
        definitions = SYSTEM_INDICATOR_DEFINITION_OVERRIDES.get((cancer_key, int(number)), {})
        for field, value in definitions.items():
            if not str(rule.get(field) or '').strip():
                rule[field] = value
    return rules


def editable_conditions(rules):
    conditions = []

    def walk(number, section, node, path):
        if not isinstance(node, dict):
            return
        if node.get('op') in COMPARISONS and 'field' in node:
            conditions.append({'indicator': number, 'section': section, 'path': path,
                               'field': node['field'], 'op': node['op'],
                               'value': node.get('value'), 'min': node.get('min'), 'max': node.get('max')})
        for index, child in enumerate(node.get('rules', [])):
            walk(number, section, child, path + [index])
        if isinstance(node.get('rule'), dict):
            walk(number, section, node['rule'], path + ['rule'])

    for number, rule in sorted(rules.items()):
        for section in ('denominator', 'numerator'):
            walk(int(number), section, rule.get(section), [])
    return conditions


def apply_changes(rules, changes):
    if not isinstance(changes, list) or len(changes) > 100:
        raise ValueError('條件設定格式不正確。')
    result = copy.deepcopy(rules)
    available = {(item['indicator'], item['section'], tuple(item['path'])) for item in editable_conditions(result)}
    seen = set()
    for change in changes:
        if not isinstance(change, dict):
            raise ValueError('條件設定格式不正確。')
        number, section, path = change.get('indicator'), change.get('section'), change.get('path')
        if (type(number) is not int or section not in ('numerator', 'denominator')
                or not isinstance(path, list)
                or any(not (type(i) is int and i >= 0) and i != 'rule' for i in path)):
            raise ValueError('條件位置不正確。')
        key = (number, section, tuple(path))
        if key not in available or key in seen:
            raise ValueError('條件位置不存在或重複。')
        seen.add(key)
        node = result[number][section]
        for index in path:
            node = node['rule'] if index == 'rule' else node['rules'][index]
        op = change.get('op')
        if op not in COMPARISONS:
            raise ValueError('不支援的數值比較方式。')
        fields = ('min', 'max') if op == 'between' else ('value',)
        values = {}
        for field in fields:
            value = change.get(field)
            if type(value) is not int or not -1000000 <= value <= 1000000:
                raise ValueError('比較數值必須是有效整數。')
            values[field] = value
        if op == 'between' and values['min'] > values['max']:
            raise ValueError('區間下限不可大於上限。')
        field_name = node['field']
        if field_name in DATE_RULE_FIELDS:
            raise ValueError('日期欄位不能使用數值比較，請改用日期條件（例如日期區間或日期年度範圍）。')
        node.clear()
        node.update({'op': op, 'field': field_name, **values})
    return result


def build_user_indicator(item, number):
    """Build a new, executable indicator from the supported online criteria editor."""
    from modules.blueprint.indicators.indicator_definitions import RULE_FIELD_LABELS

    if not isinstance(item, dict):
        raise ValueError('新增指標資料格式不正確。')
    name = str(item.get('name') or '').strip()
    direction = item.get('type')
    if not name or len(name) > 3000 or direction not in NEW_INDICATOR_TYPES:
        raise ValueError('請填寫新增指標名稱並選擇正確的指標屬性。')
    allowed_fields = set(RULE_FIELD_LABELS)

    def build_group(section):
        conditions = item.get(section)
        if isinstance(conditions, dict):
            return validate_rule_tree(conditions)
        if not isinstance(conditions, list) or not 1 <= len(conditions) <= 30:
            label = '分子' if section == 'numerator' else '分母'
            raise ValueError(f'新增指標的{label}至少要設定一個條件，最多 30 個。')
        built = []
        for condition in conditions:
            if not isinstance(condition, dict):
                raise ValueError('新增指標的條件格式不正確。')
            field = condition.get('field')
            op = condition.get('op')
            if field not in allowed_fields or op not in COMPARISONS:
                raise ValueError('新增指標目前只支援癌登欄位的數值比較條件。')
            if op == 'between':
                minimum, maximum = condition.get('min'), condition.get('max')
                if (type(minimum) is not int or type(maximum) is not int
                        or not -1000000 <= minimum <= maximum <= 1000000):
                    raise ValueError('介於條件的上下限必須是有效整數，且下限不可大於上限。')
                built.append({'op': op, 'field': field, 'min': minimum, 'max': maximum})
            else:
                value = condition.get('value')
                if type(value) is not int or not -1000000 <= value <= 1000000:
                    raise ValueError('新增指標的比較值必須是有效整數。')
                built.append({'op': op, 'field': field, 'value': value})
        return validate_rule_tree({'op': 'all', 'rules': built})

    return {
        'name': name,
        'type': direction,
        'selection_reason': str(item.get('selection_reason') or '').strip()[:3000],
        'notes': str(item.get('notes') or '').strip()[:3000],
        'numerator_definition': str(item.get('numerator_definition') or '').strip(),
        'denominator_definition': str(item.get('denominator_definition') or '').strip(),
        'numerator': build_group('numerator'),
        'denominator': build_group('denominator'),
    }


def decode_rules(raw):
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError('指標版本資料格式不正確。')
    return {int(number): rule for number, rule in data.items()}
