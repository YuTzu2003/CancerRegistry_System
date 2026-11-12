(() => {
  const schemas = {
    equals: ['field', 'value'], between: ['field', 'min', 'max'],
    greater_than: ['field', 'value'], greater_than_or_equal: ['field', 'value'],
    less_than: ['field', 'value'], less_than_or_equal: ['field', 'value'],
    in: ['field', 'values'], not_in: ['field', 'values'],
    text_in: ['field', 'values'], text_not_in: ['field', 'values'], text_equals: ['field', 'value'], text_not_equals: ['field', 'value'],
    code_in: ['field', 'values'], code_prefix_in: ['field', 'values'], text_starts_with: ['field', 'values'],
    text_in_without_prefix: ['field', 'prefix', 'values'], zero_fill_text_in: ['field', 'width', 'values'],
    all_fields_not_in: ['fields', 'values'], concatenated_text_in: ['fields', 'values'],
    stage_in: ['field', 'values'], stage_first_char_in: ['field', 'values'], first_char_in: ['field', 'values'],
    preferred_stage_in: ['preferred_field', 'fallback_field', 'invalid_values', 'values'], stage_matches: ['field', 'pattern'],
    present: ['field'], valid_date: ['field'],
    date_after: ['start_field', 'end_field'], date_on_or_after: ['start_field', 'end_field'],
    dates_equal: ['left_field', 'right_field'],
    date_interval: ['start_field', 'end_field', 'min_days', 'max_days'],
    date_year_between: ['field', 'min', 'max'],
    earliest_after_within: ['reference_field', 'candidate_fields', 'min_days', 'max_days'],
    earliest_on_or_after_within: ['reference_field', 'candidate_fields', 'min_days', 'max_days'],
    any_date_on_or_after: ['reference_field', 'candidate_fields'],
    earliest_date_interval: ['start_fields', 'end_field', 'min_days', 'max_days'],
    bed_at_least: ['courses', 'value', 'alpha_beta'],
  };
  const names = {
    all: '以下所有條件都要符合（且）', any: '以下任一條件符合即可（或）', not: '排除符合此條件的個案',
    equals: '欄位數值等於指定值', between: '欄位數值介於指定範圍（含上下限）', greater_than: '欄位數值大於指定值',
    greater_than_or_equal: '欄位數值大於或等於指定值', less_than: '欄位數值小於指定值', less_than_or_equal: '欄位數值小於或等於指定值',
    in: '欄位數值為清單中的任一值', not_in: '欄位數值不為清單中的任何值', text_in: '欄位文字為清單中的任一值', text_equals: '欄位文字等於指定內容', text_not_equals: '欄位文字不等於指定內容',
    text_not_in: '欄位文字不為清單中的任何內容', code_in: '欄位代碼為清單中的任一代碼', code_prefix_in: '欄位代碼開頭為清單中的任一值',
    text_starts_with: '欄位文字開頭為清單中的任一值', text_in_without_prefix: '移除指定前綴後，欄位文字為清單中的任一值', zero_fill_text_in: '欄位補零後為清單中的任一值',
    all_fields_not_in: '所有指定欄位皆不為排除清單中的值', concatenated_text_in: '指定欄位依序串接後為清單中的任一值',
    stage_in: '期別為清單中的任一期別', stage_first_char_in: '期別第一碼為清單中的任一值', first_char_in: '欄位第一碼為清單中的任一值',
    preferred_stage_in: '優先期別無效時改用備援期別，且結果符合清單', stage_matches: '期別符合指定格式', present: '欄位有填寫值', valid_date: '欄位為有效日期',
    date_after: '結束日期晚於開始日期', date_on_or_after: '結束日期不早於開始日期',
    dates_equal: '兩個日期相同', date_interval: '兩個日期相差指定天數',
    earliest_after_within: '候選日期中最早日期晚於基準日，且相差指定天數',
    earliest_on_or_after_within: '候選日期中最早日期不早於基準日，且相差指定天數',
    any_date_on_or_after: '候選日期中任一日期不早於基準日',
    earliest_date_interval: '多個開始日期取最早一日後，與結束日期相差指定天數', date_year_between: '日期年度介於指定範圍',
    bed_at_least: '放射治療 BED 至少達指定門檻',
  };
  const labels = { field: '要判斷的癌登欄位', value: '指定值', min: '最小值（含）', max: '最大值（含）', values: '可接受值清單（以逗號分隔）',
    start_field: '較早／開始日期欄位', end_field: '較晚／結束日期欄位', left_field: '第一個日期欄位', right_field: '第二個日期欄位',
    reference_field: '作為比較基準的日期', candidate_fields: '要比較的日期欄位（可複選）', start_fields: '可能的開始日期欄位（可複選）',
    min_days: '最少相差天數（含）', max_days: '最多相差天數（含）', fields: '要一起判斷的癌登欄位（可複選）',
    preferred_field: '優先使用的期別欄位', fallback_field: '優先欄位無效時改用的期別欄位', invalid_values: '優先期別視為無效的值（以逗號分隔）',
    prefix: '要移除的前綴文字', width: '補零後的總位數', pattern: '可接受的期別格式（進階）',
    courses: 'BED 療程', alpha_beta: 'alpha/beta（未填時使用 1.8）' };
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const isFields = key => ['candidate_fields', 'start_fields', 'fields'].includes(key);
  const isField = key => key === 'field' || key.endsWith('_field');
  const intList = op => op === 'in' || op === 'not_in';
  const listKey = key => key === 'values' || key === 'invalid_values';
  const textKey = (op, key) => ['prefix', 'pattern'].includes(key)
    || (key === 'value' && ['text_equals', 'text_not_equals'].includes(op));
  const clone = value => JSON.parse(JSON.stringify(value));
  const blankToken = '（空白）';

  // The rule tree stays the calculation source of truth.  This function only
  // changes its presentation into wording a registry user can read quickly.
  window.describeIndicatorRule = (node, fieldLabels = {}) => {
    const text = {
      unavailable: '\u689d\u4ef6\u672a\u63d0\u4f9b', none: '\u7121\u5176\u4ed6\u689d\u4ef6',
      all: '\u4ee5\u4e0b\u689d\u4ef6\u9808\u540c\u6642\u7b26\u5408', any: '\u7b26\u5408\u4ee5\u4e0b\u4efb\u4e00\u689d\u4ef6',
      not: '\u4e0d\u7b26\u5408', present: '\u5df2\u586b\u5beb', validDate: '\u70ba\u6709\u6548\u65e5\u671f',
      between: '\u4ecb\u65bc', values: '\u5176\u4e2d\u4e4b\u4e00', notValues: '\u4e0d\u70ba',
      dateAfter: '\u665a\u65bc', dateOnOrAfter: '\u4e0d\u65e9\u65bc', dateEqual: '\u76f8\u540c',
      days: '\u5929', year: '\u5e74', earliest: '\u5019\u9078\u65e5\u671f\u4e2d\u6700\u65e9\u7684\u4e00\u65e5',
      special: '\u7279\u6b8a\u689d\u4ef6', BED: 'BED \u81f3\u5c11\u9054\u5230',
    };
    const field = value => `${fieldLabels[value] || value || '\u672a\u8a2d\u5b9a\u6b04\u4f4d'}${value ? `(${value})` : ''}`;
    const fields = items => (items || []).map(field).join('\u3001');
    const values = items => (Array.isArray(items) ? items : [items]).map(item => String(item)).join('\u3001');
    const numbered = (heading, rules) => {
      const usable = (rules || []).filter(Boolean);
      return usable.length
        ? `${heading}\uff1a\n${usable.map((rule, index) => `${index + 1}. ${rule}`).join('\n')}`
        : `${heading}\uff1a${text.none}`;
    };
    const range = (minimum, maximum, suffix = '') => {
      if (minimum != null && maximum != null) return `${minimum}\uff5e${maximum}${suffix}`;
      if (minimum != null) return `\u2265 ${minimum}${suffix}`;
      if (maximum != null) return `\u2264 ${maximum}${suffix}`;
      return '';
    };
    if (!node || typeof node !== 'object') return text.unavailable;
    if (node.op === 'all') return numbered(text.all, (node.rules || []).map(child => window.describeIndicatorRule(child, fieldLabels)));
    if (node.op === 'any') return numbered(text.any, (node.rules || []).map(child => window.describeIndicatorRule(child, fieldLabels)));
    if (node.op === 'not') return `${text.not}${window.describeIndicatorRule(node.rule, fieldLabels)}`;
    const singleField = field(node.field);
    switch (node.op) {
      case 'equals': case 'text_equals': return `${singleField} = ${node.value}`;
      case 'text_not_equals': return `${singleField} \u2260 ${node.value}`;
      case 'between': return `${singleField}${text.between}${range(node.min, node.max)}`;
      case 'greater_than': return `${singleField} > ${node.value}`;
      case 'greater_than_or_equal': return `${singleField} \u2265 ${node.value}`;
      case 'less_than': return `${singleField} < ${node.value}`;
      case 'less_than_or_equal': return `${singleField} \u2264 ${node.value}`;
      case 'in': case 'text_in': case 'code_in': case 'stage_in': return `${singleField}${text.values}\uff1a${values(node.values)}`;
      case 'not_in': case 'text_not_in': return `${singleField}${text.notValues}\uff1a${values(node.values)}`;
      case 'code_prefix_in': case 'text_starts_with': return `${singleField}\u958b\u982d\u70ba\uff1a${values(node.values)}`;
      case 'text_in_without_prefix': return `${singleField}\u79fb\u9664\u300c${node.prefix || ''}\u300d\u524d\u7db4\u5f8c\u70ba\uff1a${values(node.values)}`;
      case 'zero_fill_text_in': return `${singleField}\u88dc\u96f6\u81f3 ${node.width} \u78bc\u5f8c\u70ba\uff1a${values(node.values)}`;
      case 'all_fields_not_in': return `${fields(node.fields)}\u7686${text.notValues}\uff1a${values(node.values)}`;
      case 'concatenated_text_in': return `${fields(node.fields)}\u4f9d\u5e8f\u4e32\u63a5\u5f8c${text.values}\uff1a${values(node.values)}`;
      case 'stage_first_char_in': case 'first_char_in': return `${singleField}\u7b2c\u4e00\u78bc${text.values}\uff1a${values(node.values)}`;
      case 'preferred_stage_in': return `${field(node.preferred_field)}\uff08\u82e5\u7121\u6548\u5247\u4f7f\u7528${field(node.fallback_field)}\uff09${text.values}\uff1a${values(node.values)}`;
      case 'stage_matches': return `${singleField}\u7b26\u5408\u5206\u671f\u683c\u5f0f\uff1a${node.pattern || ''}`;
      case 'present': return `${singleField}${text.present}`;
      case 'valid_date': return `${singleField}${text.validDate}`;
      case 'date_after': return `${field(node.end_field)}${text.dateAfter}${field(node.start_field)}`;
      case 'date_on_or_after': return `${field(node.end_field)}${text.dateOnOrAfter}${field(node.start_field)}`;
      case 'dates_equal': return `${field(node.left_field)}\u8207${field(node.right_field)}${text.dateEqual}`;
      case 'date_interval': return `${field(node.end_field)}\u6e1b${field(node.start_field)}${text.between}${range(node.min_days, node.max_days, text.days)}`;
      case 'date_year_between': return `${singleField}\u5e74\u4efd${text.between}${range(node.min, node.max, text.year)}`;
      case 'any_date_on_or_after': return `${fields(node.candidate_fields)}\u4e2d\u4efb\u4e00\u65e5\u671f${text.dateOnOrAfter}${field(node.reference_field)}`;
      case 'earliest_after_within': return `${text.earliest}\uff08${fields(node.candidate_fields)}\uff09\u665a\u65bc${field(node.reference_field)}\uff0c\u9593\u9694${range(node.min_days, node.max_days, text.days)}`;
      case 'earliest_on_or_after_within': return `${text.earliest}\uff08${fields(node.candidate_fields)}\uff09${text.dateOnOrAfter}${field(node.reference_field)}\uff0c\u9593\u9694${range(node.min_days, node.max_days, text.days)}`;
      case 'earliest_date_interval': return `${field(node.end_field)}\u6e1b${text.earliest}\uff08${fields(node.start_fields)}\uff09${text.between}${range(node.min_days, node.max_days, text.days)}`;
      case 'bed_at_least': return `${text.BED} ${node.value}${node.alpha_beta ? `\uff08alpha/beta = ${node.alpha_beta}\uff09` : ''}\uff1a${(node.courses || []).map(course => `${field(course.dose_field)} / ${field(course.fractions_field)}`).join('\u3001')}`;
      default: return `${text.special}\uff08${node.op || '\u672a\u547d\u540d'}\uff09`;
    }
  };

  function createRuleEditorCore(initial, fieldLabels) {
    const fields = Object.entries(fieldLabels).sort(([a], [b]) => a.localeCompare(b, undefined, {numeric:true}));
    const firstField = fields[0]?.[0] || '';
    let tree = clone(initial);
    const fresh = op => {
      if (op === 'all' || op === 'any') return {op, rules:[fresh('equals')]};
      if (op === 'not') return {op, rule:fresh('equals')};
      const initialValue = key => {
        if (isFields(key)) return [firstField];
        if (isField(key)) return firstField;
        if (listKey(key)) return [];
        if (key === 'courses') return [{dose_field:firstField, fractions_field:firstField}];
        if (key === 'alpha_beta') return null;
        if (textKey(op, key)) return '';
        return 0;
      };
      return Object.fromEntries([['op', op], ...(schemas[op] || []).map(key => [key, initialValue(key)])]);
    };
    const get = path => path.reduce((node, key) => node[key], tree);
    const set = (path, value) => {
      if (!path.length) { tree = value; return; }
      const parent = get(path.slice(0, -1)); parent[path[path.length - 1]] = value;
    };
    const options = (selected, multi = false) => {
      const values = multi ? (Array.isArray(selected) ? selected : []) : [selected];
      const missing = values.filter(value => value && !Object.hasOwn(fieldLabels, value));
      return missing.map(value => `<option value="${esc(value)}" selected>${esc(value)}（原設定欄位待確認）</option>`).join('')
        + fields.map(([code, label]) => `<option value="${esc(code)}"${values.includes(code) ? ' selected' : ''}>${esc(label)}（${esc(code)}）</option>`).join('');
    };
    const selectedFields = values => {
      const selected = Array.isArray(values) ? values : [];
      const chips = selected.map(value => `<span class="rule-editor-selected-chip">${esc(fieldLabels[value] || value)}${Object.hasOwn(fieldLabels, value) ? `（${esc(value)}）` : '（原設定欄位待確認）'}</span>`).join('');
      return `<div class="rule-editor-selected-fields" data-selected-fields><span class="rule-editor-selected-label">目前已選 ${selected.length} 項：</span>${chips || '<span class="rule-editor-selected-label">尚未選擇欄位</span>'}</div>`;
    };
    const renderNode = (node, path = []) => {
      const pathText = esc(JSON.stringify(path));
      const supported = node.op in names;
      const opOptions = Object.entries(names).map(([op, label]) => `<option value="${op}"${op === node.op ? ' selected' : ''}>${label}</option>`).join('');
      const header = supported ? `<label>條件類型<select class="form-select form-select-sm" data-rule-op data-path="${pathText}">${opOptions}</select></label>` : `<div><strong>不支援的舊條件：${esc(node.op)}</strong><div class="text-danger small">請勿直接儲存；此條件需先改為支援的條件類型。</div></div>`;
      let body = '';
      if (node.op === 'all' || node.op === 'any') {
        body = (node.rules || []).map((child, i) => renderNode(child, [...path, 'rules', i])).join('') + `<button type="button" class="btn btn-outline-primary btn-sm mt-2" data-rule-add data-path="${pathText}">新增條件</button>`;
      } else if (node.op === 'not') body = renderNode(node.rule, [...path, 'rule']);
      else if (node.op === 'bed_at_least') {
        const courses = Array.isArray(node.courses) ? node.courses : [];
        body = `<div class="rule-editor-fields"><label>BED 門檻<input class="form-control form-control-sm" type="number" step="any" data-rule-key="value" data-path="${pathText}" value="${esc(node.value)}"></label><label>alpha/beta（未填時為 1.8）<input class="form-control form-control-sm" type="number" step="any" data-rule-key="alpha_beta" data-path="${pathText}" value="${esc(node.alpha_beta ?? '')}"></label></div><div class="mt-2"><strong class="small">療程欄位</strong>${courses.map((course, index) => `<div class="rule-editor-fields mt-1"><label>劑量欄位<select class="form-select form-select-sm" data-bed-key="dose_field" data-course-index="${index}" data-path="${pathText}">${options(course.dose_field)}</select></label><label>分次欄位<select class="form-select form-select-sm" data-bed-key="fractions_field" data-course-index="${index}" data-path="${pathText}">${options(course.fractions_field)}</select></label>${courses.length > 1 ? `<button type="button" class="btn btn-outline-danger btn-sm align-self-end" data-bed-remove data-course-index="${index}" data-path="${pathText}">移除療程</button>` : ''}</div>`).join('')}<button type="button" class="btn btn-outline-primary btn-sm mt-2" data-bed-add data-path="${pathText}">新增療程</button></div>`;
      } else if (schemas[node.op]) body = `<div class="rule-editor-fields">${schemas[node.op].map(key => {
        const value = node[key];
        if (isFields(key)) return `<label>${labels[key]}<select multiple class="form-select form-select-sm" data-rule-key="${key}" data-path="${pathText}">${options(value || [], true)}</select><small>按住 Ctrl 可選多個${(value || []).some(field => !Object.hasOwn(fieldLabels, field)) ? '；原設定中有欄位待確認。' : ''}</small>${selectedFields(value)}</label>`;
        if (isField(key)) return `<label>${labels[key]}<select class="form-select form-select-sm" data-rule-key="${key}" data-path="${pathText}">${options(value)}</select>${value && !Object.hasOwn(fieldLabels, value) ? '<small class="text-danger">原設定欄位待確認；修改此條件前請選擇有效欄位。</small>' : ''}</label>`;
        const listValue = listKey(key) ? (value || []).map(item => key === 'invalid_values' && item === '' ? blankToken : item).join(', ') : '';
        const hint = key === 'invalid_values' ? `<small>以「${blankToken}」表示欄位空白值。</small>` : '';
        return `<label>${labels[key]}<input class="form-control form-control-sm" ${listKey(key) || textKey(node.op, key) ? 'type="text"' : 'type="number" step="any"'} data-rule-key="${key}" data-path="${pathText}" value="${esc(listKey(key) ? listValue : value ?? '')}">${hint}</label>`;
      }).join('')}</div>`;
      const removable = path.length >= 2 && path[path.length - 2] === 'rules';
      return `<div class="rule-editor-node">${header}${removable ? `<button type="button" class="btn btn-outline-danger btn-sm" data-rule-remove data-path="${pathText}" aria-label="移除此條件">移除</button>` : ''}${body}</div>`;
    };
    const render = host => {
      host.innerHTML = `<p class="text-secondary small">使用「且/或」群組組合條件；日期間隔的上下限均包含該天。</p>${renderNode(tree)}`;
    };
    const attachEvents = host => {
      const onChangeHandler = event => {
        const el = event.target;
        if (el.dataset.bedKey && el.dataset.path) {
          const node = get(JSON.parse(el.dataset.path));
          node.courses[Number(el.dataset.courseIndex)][el.dataset.bedKey] = el.value;
          return;
        }
        if (!el.dataset.path) return;
        const path = JSON.parse(el.dataset.path);
        if (el.matches('[data-rule-op]')) {
          const old = get(path);
          set(path, ['all', 'any'].includes(old.op) && ['all', 'any'].includes(el.value)
            ? {op:el.value, rules:old.rules} : fresh(el.value));
          render(host); return;
        }
        if (!el.dataset.ruleKey) return;
        const node = get(path), key = el.dataset.ruleKey;
        if (isFields(key)) {
          node[key] = [...el.selectedOptions].map(option => option.value);
          const summary = el.closest('label')?.querySelector('[data-selected-fields]');
          if (summary) summary.outerHTML = selectedFields(node[key]);
        }
        else if (listKey(key)) node[key] = el.value.split(/[,，\n]/).map(v => v.trim()).filter(Boolean)
          .map(v => key === 'invalid_values' && v === blankToken ? '' : (intList(node.op) && /^-?\d+$/.test(v) ? Number(v) : v));
        else if (isField(key)) node[key] = el.value;
        else if (textKey(node.op, key)) node[key] = el.value;
        else node[key] = el.value === '' ? null : Number(el.value);
      };
      const onClickHandler = event => {
        const add = event.target.closest('[data-rule-add]'), remove = event.target.closest('[data-rule-remove]');
        const bedAdd = event.target.closest('[data-bed-add]'), bedRemove = event.target.closest('[data-bed-remove]');
        if (add) { get(JSON.parse(add.dataset.path)).rules.push(fresh('equals')); render(host); }
        if (remove) { const path = JSON.parse(remove.dataset.path); get(path.slice(0, -1)).splice(path.at(-1), 1); render(host); }
        if (bedAdd) { get(JSON.parse(bedAdd.dataset.path)).courses.push({dose_field:firstField, fractions_field:firstField}); render(host); }
        if (bedRemove) { get(JSON.parse(bedRemove.dataset.path)).courses.splice(Number(bedRemove.dataset.courseIndex), 1); render(host); }
      };
      host.addEventListener('change', onChangeHandler);
      host.addEventListener('click', onClickHandler);
      return () => { host.removeEventListener('change', onChangeHandler); host.removeEventListener('click', onClickHandler); };
    };
    const validate = () => {
      const check = node => {
        if (!node || typeof node !== 'object') return false;
        if (node.op === 'all' || node.op === 'any') return node.rules?.length > 0 && node.rules.every(check);
        if (node.op === 'not') return check(node.rule);
        if (!schemas[node.op]) return false;
        if (node.op === 'bed_at_least') return Array.isArray(node.courses) && node.courses.length > 0
          && node.courses.every(course => course && course.dose_field && course.fractions_field)
          && Number.isFinite(node.value) && node.value >= 0
          && (node.alpha_beta == null || (Number.isFinite(node.alpha_beta) && node.alpha_beta > 0));
        return schemas[node.op].every(key => {
          if (isFields(key) || listKey(key)) return Array.isArray(node[key]) && node[key].length > 0;
          if (isField(key)) return !!node[key];
          if (textKey(node.op, key)) return typeof node[key] === 'string' && node[key].trim();
          if (key === 'alpha_beta') return node[key] == null || (Number.isFinite(node[key]) && node[key] > 0);
          return Number.isFinite(node[key]) && (key !== 'width' || Number.isInteger(node[key]) && node[key] > 0);
        })
          && (node.min === undefined || node.min <= node.max) && (node.min_days === undefined || node.min_days <= node.max_days)
          && (!intList(node.op) || node.values.every(Number.isInteger));
      };
      return check(tree) ? tree : null;
    };
    return { render, attachEvents, validate };
  }

  window.openIndicatorRuleEditor = async (initial, fieldLabels) => {
    const core = createRuleEditorCore(initial, fieldLabels);
    const result = await Swal.fire({
      title:'編輯計算條件', html:'<div id="ruleEditor" class="rule-editor"></div>', width:'1000px',
      showCancelButton:true, confirmButtonText:'套用條件', cancelButtonText:'取消',
      confirmButtonColor:'#262a31',
      didOpen: () => {
        const host = document.getElementById('ruleEditor');
        core.render(host);
        core.attachEvents(host);
      },
      preConfirm: () => {
        const tree = core.validate();
        if (!tree) { Swal.showValidationMessage('請填妥每項條件，並確認數值上下限及代碼清單。'); return false; }
        return tree;
      },
    });
    return result.isConfirmed ? result.value : null;
  };

  window.openInlineRuleEditor = (container, initial, fieldLabels, callbacks) => {
    const core = createRuleEditorCore(initial, fieldLabels);
    container.innerHTML = `<div class="rule-editor-inline"><div class="rule-editor"></div><p class="text-danger small mt-2 d-none" data-inline-error></p><div class="rule-editor-inline-actions"><button type="button" class="btn btn-sm btn-outline-secondary" data-inline-cancel>取消</button><button type="button" class="btn btn-sm btn-primary" data-inline-apply>套用條件</button></div></div>`;
    const host = container.querySelector('.rule-editor');
    core.render(host);
    const cleanup = core.attachEvents(host);
    container.querySelector('[data-inline-apply]').addEventListener('click', () => {
      const tree = core.validate();
      if (!tree) { const err = container.querySelector('[data-inline-error]'); err.textContent = '請填妥每項條件，並確認數值上下限及代碼清單。'; err.classList.remove('d-none'); return; }
      cleanup();
      container.innerHTML = '';
      callbacks.onApply(tree);
    });
    container.querySelector('[data-inline-cancel]').addEventListener('click', () => {
      cleanup();
      container.innerHTML = '';
      callbacks.onCancel?.();
    });
  };
})();
