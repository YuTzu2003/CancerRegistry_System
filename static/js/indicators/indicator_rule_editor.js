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
    all: '全部符合（且）', any: '符合任一項（或）', not: '不符合此條件',
    equals: '數值等於', between: '數值介於（含上下限）', greater_than: '數值大於',
    greater_than_or_equal: '數值大於或等於', less_than: '數值小於', less_than_or_equal: '數值小於或等於',
    in: '數值包含於清單', not_in: '數值不包含於清單', text_in: '文字等於清單之一', text_equals: '文字等於', text_not_equals: '文字不等於',
    text_not_in: '文字不等於清單任一值', code_in: '代碼符合清單', code_prefix_in: '代碼開頭符合清單',
    text_starts_with: '文字開頭符合清單', text_in_without_prefix: '去除前綴後符合清單', zero_fill_text_in: '補零後符合清單',
    all_fields_not_in: '所有欄位皆不在排除清單', concatenated_text_in: '串接欄位符合清單',
    stage_in: '期別符合清單', stage_first_char_in: '期別第一碼符合清單', first_char_in: '文字第一碼符合清單',
    preferred_stage_in: '優先期別／備援期別符合清單', stage_matches: '期別符合格式', present: '欄位有值', valid_date: '日期有效',
    date_after: '結束日期晚於開始日期', date_on_or_after: '結束日期不早於開始日期',
    dates_equal: '兩個日期相同', date_interval: '兩個日期間隔天數',
    earliest_after_within: '基準日之後最早日期的間隔',
    earliest_on_or_after_within: '基準日當天或之後最早日期的間隔',
    any_date_on_or_after: '任一日期不早於基準日',
    earliest_date_interval: '多個開始日期取最早再計算間隔', date_year_between: '日期年度介於範圍',
    bed_at_least: '放射治療 BED 至少達門檻',
  };
  const labels = { field: '癌登欄位', value: '數值', min: '下限', max: '上限', values: '代碼清單（逗號分隔）',
    start_field: '開始日期', end_field: '結束日期', left_field: '日期一', right_field: '日期二',
    reference_field: '基準日期', candidate_fields: '候選日期（可複選）', start_fields: '開始日期（可複選）',
    min_days: '最少天數（含）', max_days: '最多天數（含）', fields: '癌登欄位（可複選）',
    preferred_field: '優先期別欄位', fallback_field: '備援期別欄位', invalid_values: '優先期別無效值（逗號分隔）',
    prefix: '要去除的前綴', width: '補零位數', pattern: '期別格式（正規表示式）',
    courses: 'BED 療程', alpha_beta: 'alpha/beta（未填時為 1.8）' };
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const isFields = key => ['candidate_fields', 'start_fields', 'fields'].includes(key);
  const isField = key => key === 'field' || key.endsWith('_field');
  const intList = op => op === 'in' || op === 'not_in';
  const listKey = key => key === 'values' || key === 'invalid_values';
  const textKey = (op, key) => ['prefix', 'pattern'].includes(key)
    || (key === 'value' && ['text_equals', 'text_not_equals'].includes(op));
  const clone = value => JSON.parse(JSON.stringify(value));
  const blankToken = '（空白）';

  window.describeIndicatorRule = (node, fieldLabels = {}) => {
    if (!node || typeof node !== 'object') return '條件未提供';
    if (node.op === 'all' || node.op === 'any') return `（${(node.rules || []).map(child => window.describeIndicatorRule(child, fieldLabels)).join(node.op === 'all' ? ' 且 ' : ' 或 ') || '無條件'}）`;
    if (node.op === 'not') return `不符合 ${window.describeIndicatorRule(node.rule, fieldLabels)}`;
    if (!schemas[node.op]) return `原有特殊條件（${node.op}）`;
    const details = schemas[node.op].map(key => {
      const value = node[key];
      const show = item => (isField(key) || isFields(key)) ? `${fieldLabels[item] || item}（${item}）` : item;
      return `${labels[key]}：${Array.isArray(value) ? value.map(show).join('、') : show(value ?? '')}`;
    });
    return `${names[node.op]}［${details.join('；')}］`;
  };

  window.openIndicatorRuleEditor = async (initial, fieldLabels) => {
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
        if (isFields(key)) return `<label>${labels[key]}<select multiple class="form-select form-select-sm" data-rule-key="${key}" data-path="${pathText}">${options(value || [], true)}</select><small>按住 Ctrl 可選多個${(value || []).some(field => !Object.hasOwn(fieldLabels, field)) ? '；原設定中有欄位待確認。' : ''}</small></label>`;
        if (isField(key)) return `<label>${labels[key]}<select class="form-select form-select-sm" data-rule-key="${key}" data-path="${pathText}">${options(value)}</select>${value && !Object.hasOwn(fieldLabels, value) ? '<small class="text-danger">原設定欄位待確認；修改此條件前請選擇有效欄位。</small>' : ''}</label>`;
        const listValue = listKey(key) ? (value || []).map(item => key === 'invalid_values' && item === '' ? blankToken : item).join(', ') : '';
        const hint = key === 'invalid_values' ? `<small>以「${blankToken}」表示欄位空白值。</small>` : '';
        return `<label>${labels[key]}<input class="form-control form-control-sm" ${listKey(key) || textKey(node.op, key) ? 'type="text"' : 'type="number" step="any"'} data-rule-key="${key}" data-path="${pathText}" value="${esc(listKey(key) ? listValue : value ?? '')}">${hint}</label>`;
      }).join('')}</div>`;
      const removable = path.length >= 2 && path[path.length - 2] === 'rules';
      return `<div class="rule-editor-node">${header}${removable ? `<button type="button" class="btn btn-outline-danger btn-sm" data-rule-remove data-path="${pathText}" aria-label="移除此條件">移除</button>` : ''}${body}</div>`;
    };
    const result = await Swal.fire({
      title:'編輯計算條件', html:'<div id="ruleEditor" class="rule-editor"></div>', width:'1000px',
      showCancelButton:true, confirmButtonText:'套用條件', cancelButtonText:'取消',
      didOpen: () => {
        const host = document.getElementById('ruleEditor');
        const render = () => { host.innerHTML = `<p class="text-secondary small">使用「且／或」群組組合條件；日期間隔的上下限均包含該天。</p>${renderNode(tree)}`; };
        host.addEventListener('change', event => {
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
            render(); return;
          }
          if (!el.dataset.ruleKey) return;
          const node = get(path), key = el.dataset.ruleKey;
          if (isFields(key)) node[key] = [...el.selectedOptions].map(option => option.value);
          else if (listKey(key)) node[key] = el.value.split(/[,，\n]/).map(v => v.trim()).filter(Boolean)
            .map(v => key === 'invalid_values' && v === blankToken ? '' : (intList(node.op) && /^-?\d+$/.test(v) ? Number(v) : v));
          else if (isField(key)) node[key] = el.value;
          else if (textKey(node.op, key)) node[key] = el.value;
          else node[key] = el.value === '' ? null : Number(el.value);
        });
        host.addEventListener('click', event => {
          const add = event.target.closest('[data-rule-add]'), remove = event.target.closest('[data-rule-remove]');
          const bedAdd = event.target.closest('[data-bed-add]'), bedRemove = event.target.closest('[data-bed-remove]');
          if (add) { get(JSON.parse(add.dataset.path)).rules.push(fresh('equals')); render(); }
          if (remove) { const path = JSON.parse(remove.dataset.path); get(path.slice(0, -1)).splice(path.at(-1), 1); render(); }
          if (bedAdd) { get(JSON.parse(bedAdd.dataset.path)).courses.push({dose_field:firstField, fractions_field:firstField}); render(); }
          if (bedRemove) { get(JSON.parse(bedRemove.dataset.path)).courses.splice(Number(bedRemove.dataset.courseIndex), 1); render(); }
        });
        render();
      },
      preConfirm: () => {
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
        if (!check(tree)) { Swal.showValidationMessage('請填妥每項條件，並確認數值上下限及代碼清單。'); return false; }
        return tree;
      },
    });
    return result.isConfirmed ? result.value : null;
  };
})();
