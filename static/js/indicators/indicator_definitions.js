(() => {
  const manager = document.getElementById('definitionManager');
  if (!manager) return;
  const canManage = manager.dataset.canManage === 'true';
  const canApprove = manager.dataset.canApprove === 'true';
  const cancerSelect = document.getElementById('definitionCancer');
  const versionSelect = document.getElementById('definitionVersion');
  const backLink = document.getElementById('backToIndicators');
  const startButton = document.getElementById('startDefinitionEdit');
  const startButtonLabel = document.getElementById('startDefinitionEditLabel');
  const reviseButton = document.getElementById('reviseDefinitionVersion');
  const reviseButtonLabel = document.getElementById('reviseDefinitionVersionLabel');
  const deleteButton = document.getElementById('deleteDefinitionVersion');
  const renameButton = document.createElement('button');
  renameButton.id = 'renameDefinitionVersion';
  renameButton.type = 'button';
  renameButton.className = 'btn btn-outline-secondary btn-sm';
  renameButton.innerHTML = '<i class="bi bi-tag me-1" aria-hidden="true"></i>重新命名';
  deleteButton?.before(renameButton);
  const historyButton = document.getElementById('definitionHistory');
  const statusTarget = document.getElementById('definitionStatusTarget');
  const changeStatusButton = document.getElementById('changeDefinitionStatus');
  const availabilityControl = document.getElementById('definitionAvailabilityControl');
  const availabilitySwitch = document.getElementById('definitionAvailability');
  const availabilityLabel = document.getElementById('definitionAvailabilityLabel');
  const statusActions = document.getElementById('definitionStatusActions');
  const saveButton = document.getElementById('saveDefinitionVersion');
  const cancelButton = document.getElementById('cancelDefinitionEdit');
  const contents = document.getElementById('definitionContents');
  const yearInput = document.getElementById('definitionYear');
  // The save workflow historically used `nameInput`; the displayed field is now
  // the annual edition, and the server derives a readable version name from it.
  const nameInput = yearInput;
  const descriptionInput = document.getElementById('definitionVersionDescription');
  const reasonInput = document.getElementById('definitionChangeReason');
  const status = document.getElementById('definitionStatus');
  const settings = document.getElementById('definitionEditSettings');
  const actions = document.getElementById('definitionEditActions');
  const operators = { between: '介於（含上下限）', equals: '等於', greater_than: '大於', greater_than_or_equal: '大於或等於', less_than: '小於', less_than_or_equal: '小於或等於' };
  let currentData = null;
  let editing = false;
  let revising = false;
  let busy = false;
  let loadId = 0;
  let drafts = {};
  let originals = {};
  let sourceFingerprint = '';
  let originalVersionDescription = '';
  const draftStatus = document.getElementById('definitionDraftStatus');
  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
  const fetchJson = async (url, options = {}) => {
    const response = await fetch(url, { credentials: 'same-origin', ...options });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok) throw new Error(data.error || '無法讀取指標定義，請確認資料庫更新及登入狀態。');
    return data;
  };
  const showStatus = (message, error = false) => {
    status.textContent = message;
    status.className = error ? 'alert alert-danger mt-3' : 'text-secondary mt-3';
  };
  const updateNavigation = () => {
    const url = new URL(backLink.href, window.location.origin);
    url.searchParams.delete('oral_rule_version');
    url.searchParams.delete('rule_cancer');
    url.searchParams.delete('rule_version');
    url.searchParams.set('definition_version', versionSelect.value);
    backLink.href = url.href;
    const page = new URL(window.location.href);
    page.searchParams.set('cancer', cancerSelect.value);
    page.searchParams.set('version', versionSelect.value);
    window.history.replaceState(null, '', page);
  };
  const statusLabels = { DRAFT: '退回修改', PENDING: '待審核', PUBLISHED: '已啟用', INACTIVE: '已停用' };
  const nextStatuses = {
    DRAFT: ['PENDING', 'INACTIVE'],
    PENDING: ['DRAFT', 'PUBLISHED', 'INACTIVE'],
    PUBLISHED: ['INACTIVE'],
    INACTIVE: ['PUBLISHED'],
  };
  const statusTransitionLabels = {
    DRAFT: '退回修改',
    PENDING: '送出審核',
    PUBLISHED: '核准啟用',
    INACTIVE: '停用版本',
  };
  const updateVersionState = () => {
    const state = document.getElementById('definitionVersionState');
    if (!state || !currentData?.version) return;
    const current = currentData.version.status || 'PUBLISHED';
    state.className = `definition-status-badge definition-status-${current}`;
    state.textContent = statusLabels[current] || current;
    const canToggleAvailability = canApprove && versionSelect.value !== 'default' && ['PUBLISHED', 'INACTIVE'].includes(current);
    availabilityControl?.classList.toggle('d-none', !canToggleAvailability);
    statusActions?.classList.toggle('d-none', !canApprove || canToggleAvailability);
    if (availabilitySwitch) availabilitySwitch.checked = current === 'PUBLISHED';
    if (availabilityLabel) availabilityLabel.textContent = current === 'PUBLISHED' ? '提供一般使用者選擇' : '目前不提供一般使用者選擇';
    const viewerVersion = document.getElementById('definitionContentsVersion');
    if (viewerVersion) viewerVersion.textContent = `${currentData.version.name} | ${statusLabels[current] || current}`;
    if (!statusTarget) return;
    statusTarget.replaceChildren(...(nextStatuses[current] || []).map(value => {
      const option = document.createElement('option'); option.value = value;
      option.textContent = statusTransitionLabels[value] || `變更為：${statusLabels[value] || value}`;
      return option;
    }));
  };
  const updateControls = () => {
    const versionStatus = currentData?.version?.status || 'PUBLISHED';
    const canToggleAvailability = canApprove && versionSelect.value !== 'default' && ['PUBLISHED', 'INACTIVE'].includes(versionStatus);
    cancerSelect.disabled = busy;
    versionSelect.disabled = busy || editing || !currentData;
    const isDefaultVersion = versionSelect.value === 'default';
    const canEditExisting = ['DRAFT', 'PENDING', 'INACTIVE'].includes(versionStatus);
    if (startButton) {
      startButton.disabled = busy || editing || !currentData;
      startButton.classList.toggle('d-none', !isDefaultVersion && !canEditExisting);
      if (startButtonLabel) startButtonLabel.textContent = isDefaultVersion ? '建立空白版本' : '另建版本';
    }
    if (deleteButton) deleteButton.disabled = busy || editing || !currentData || versionSelect.value === 'default' || versionStatus === 'PUBLISHED';
    renameButton.disabled = busy || editing || !currentData || versionSelect.value === 'default' || versionStatus === 'PUBLISHED';
    if (historyButton) historyButton.disabled = busy || !currentData || versionSelect.value === 'default';
    if (availabilitySwitch) availabilitySwitch.disabled = busy || editing || !canApprove || !canToggleAvailability;
    if (statusTarget) statusTarget.disabled = busy || editing || !canApprove || canToggleAvailability || !currentData || versionSelect.value === 'default' || !(nextStatuses[versionStatus] || []).length;
    if (changeStatusButton) changeStatusButton.disabled = busy || editing || !canApprove || canToggleAvailability || !currentData || versionSelect.value === 'default' || !(nextStatuses[versionStatus] || []).length;
    if (reviseButton) {
      reviseButton.disabled = busy || editing || !currentData || versionSelect.value === 'default';
      const reviseLabel = currentData?.included === false
        ? '加入此癌別並建立新版'
        : canEditExisting ? '編輯版本' : '沿用此版本建立新版';
      if (reviseButtonLabel) reviseButtonLabel.textContent = reviseLabel;
      else reviseButton.textContent = reviseLabel;
    }
    settings.classList.toggle('d-none', !editing);
    actions?.classList.toggle('d-none', !editing);
    yearInput.disabled = !editing || busy || revising;
    descriptionInput.disabled = !editing || busy;
    reasonInput.disabled = !editing || busy;
    const revisionHint = document.getElementById('definitionRevisionHint');
    const creatingFromVersion = editing && !revising && versionSelect.value !== 'default';
    revisionHint.textContent = creatingFromVersion
      ? '將依目前版本建立待審版本。'
      : currentData?.version.status === 'INACTIVE' ? '儲存後須重新審核。' : '修改後須由管理員核准。';
    revisionHint.classList.toggle('d-none', !editing || (!revising && !creatingFromVersion));
    contents.querySelectorAll('input, textarea, select').forEach(element => { element.disabled = !editing || busy; });
    contents.querySelectorAll('[data-add-new-indicator], [data-remove-new-indicator], [data-add-new-condition], [data-remove-new-condition]').forEach(button => { button.disabled = !editing || busy; });
    contents.querySelectorAll('[data-edit-rule-tree], [data-edit-new-tree]').forEach(button => { button.disabled = !editing || busy; });
    if (saveButton) { saveButton.disabled = busy; saveButton.textContent = revising ? '儲存修改' : '送出審核'; }
    if (cancelButton) cancelButton.disabled = busy;
  };
  const readDraft = () => ({
    conditions: [...contents.querySelectorAll('[data-condition]')].map(row => ({
      op: row.querySelector('[data-op]').value,
      first: row.querySelector('[data-first]').value,
      second: row.querySelector('[data-second]').value,
    })),
    ruleTrees: Object.fromEntries([...contents.querySelectorAll('[data-rule-indicator]')].map(card => [card.dataset.ruleIndicator,
      Object.fromEntries([...card.querySelectorAll('[data-rule-tree]')].map(input => [input.dataset.ruleTree, JSON.parse(input.value)]))])),
    descriptions: [...contents.querySelectorAll('[data-description]')].map(element => element.value),
    removed: [...contents.querySelectorAll('[data-remove-indicator]:checked')].map(element => Number(element.value)),
    newIndicators: readNewIndicators(),
  });
  const blankNewIndicator = () => ({ name: '', type: 'positive', selection_reason: '', numerator_definition: '', denominator_definition: '', numerator: [blankNewCondition()], denominator: [blankNewCondition()] });
  const blankNewCondition = () => ({ field: Object.keys(currentData?.field_labels || {})[0] || '', op: 'equals', value: '', min: '', max: '' });
  const readNewIndicators = () => [...contents.querySelectorAll('[data-new-indicator-card]')].map(card => {
    const readConditions = section => {
      const advanced = card.querySelector(`[data-new-tree="${section}"]`);
      if (advanced?.value) return JSON.parse(advanced.value);
      return [...card.querySelectorAll(`[data-new-condition="${section}"]`)].map(row => ({
      field: row.querySelector('[data-new-field]').value,
      op: row.querySelector('[data-new-op]').value,
      value: row.querySelector('[data-new-value]').value,
      min: row.querySelector('[data-new-min]').value,
      max: row.querySelector('[data-new-max]').value,
      }));
    };
    return {
      name: card.querySelector('[data-new-name]').value,
      type: card.querySelector('[data-new-type]').value,
      selection_reason: card.querySelector('[data-new-reason]').value,
      numerator_definition: card.querySelector('[data-new-numerator-description]').value,
      denominator_definition: card.querySelector('[data-new-denominator-description]').value,
      numerator: readConditions('numerator'),
      denominator: readConditions('denominator'),
    };
  });
  const isChanged = key => drafts[key] && JSON.stringify(drafts[key].values) !== JSON.stringify(originals[key]);
  const updateDraftStatus = () => {
    const changed = Object.keys(drafts).filter(isChanged);
    const names = changed.map(key => [...cancerSelect.options].find(option => option.value === key)?.textContent || key);
    draftStatus.textContent = names.length ? `尚未儲存的癌別：${names.join('、')}` : '尚未修改任何癌別。';
  };
  const captureDraft = () => {
    if (!editing || !currentData) return;
    const key = currentData.cancer_key;
    drafts[key] = { data: currentData, values: readDraft() };
    updateDraftStatus();
  };
  const restoreDraft = key => {
    const values = drafts[key]?.values;
    if (!values) return;
    contents.querySelectorAll('[data-condition]').forEach((row, index) => {
      const value = values.conditions[index];
      row.querySelector('[data-op]').value = value.op;
      row.querySelector('[data-first]').value = value.first;
      row.querySelector('[data-second]').value = value.second;
      row.querySelector('[data-op]').dispatchEvent(new Event('change'));
    });
    contents.querySelectorAll('[data-description]').forEach((element, index) => { element.value = values.descriptions[index]; });
    contents.querySelectorAll('[data-remove-indicator]').forEach(element => { element.checked = values.removed.includes(Number(element.value)); });
    contents.querySelectorAll('[data-rule-indicator]').forEach(card => {
      const sections = values.ruleTrees?.[card.dataset.ruleIndicator];
      if (sections) card.querySelectorAll('[data-rule-tree]').forEach(input => { input.value = JSON.stringify(sections[input.dataset.ruleTree]); });
    });
    renderNewIndicatorEditor(values.newIndicators || []);
  };
  const reviewChanges = keys => {
    const conditionText = value => `${operators[value.op] || value.op} ${value.first}${value.op === 'between' ? ` 至 ${value.second}` : ''}`;
    const item = (title, before, after) => `<div class="definition-review-item"><strong>${escapeHtml(title)}</strong><div class="definition-review-value">修改前：${escapeHtml(before || '（空白）')}</div><div class="definition-review-value">修改後：${escapeHtml(after || '（空白）')}</div></div>`;
    const groups = keys.map(key => {
      const { data, values } = drafts[key];
      const original = originals[key];
      const cancer = [...cancerSelect.options].find(option => option.value === key)?.textContent || key;
      const rows = [];
      if (data.included === false) rows.push('<p class="small">此癌別尚未收錄於來源版本，儲存後會加入。</p>');
      values.removed.forEach(number => {
        const indicator = data.descriptions.find(entry => entry.id === number);
        rows.push(item(`指標 ${number}・移除`, indicator?.name || '', '從儲存後的版本移除'));
      });
      const descriptionLabels = ['指標名稱', '分母說明', '分子說明'];
      values.descriptions.forEach((after, index) => {
        const before = original.descriptions[index];
        if (!values.removed.includes(data.descriptions[Math.floor(index / 3)].id) && before.trim() !== after.trim()) {
          const indicator = data.descriptions[Math.floor(index / 3)];
          rows.push(item(`指標 ${indicator.id}・${descriptionLabels[index % 3]}`, before.trim(), after.trim()));
        }
      });
      values.conditions.forEach((after, index) => {
        const before = original.conditions[index];
        const beforeText = conditionText(before);
        const afterText = conditionText(after);
        if (!values.removed.includes(data.conditions[index].indicator) && beforeText !== afterText) {
          const condition = data.conditions[index];
          const field = data.field_labels?.[condition.field] || condition.field;
          rows.push(item(`指標 ${condition.indicator}・${condition.section === 'numerator' ? '分子' : '分母'}・${field}（${condition.field}）`, beforeText, afterText));
        }
      });
      values.newIndicators.forEach((indicator, index) => {
        rows.push(item(`新增指標 ${index + 1}（${indicator.type === 'positive' ? '正向' : indicator.type === 'negative' ? '負向' : '觀察'}）`, '尚未建立', indicator.name.trim() || '未命名指標'));
        for (const section of ['denominator', 'numerator']) {
          const tree = Array.isArray(indicator[section]) ? {op:'all', rules:indicator[section].map(condition => ({
            op:condition.op, field:condition.field, ...(condition.op === 'between' ? {min:condition.min, max:condition.max} : {value:condition.value}),
          }))} : indicator[section];
          rows.push(item(`新增指標 ${index + 1}・${section === 'numerator' ? '分子' : '分母'}計算條件`, '尚未建立', window.describeIndicatorRule(tree, data.field_labels)));
        }
      });
      Object.entries(values.ruleTrees || {}).forEach(([number, sections]) => {
        if (values.removed.includes(Number(number))) return;
        for (const section of ['denominator', 'numerator']) {
          if (JSON.stringify(sections[section]) !== JSON.stringify(original.ruleTrees?.[number]?.[section]))
            rows.push(item(`指標 ${number}・${section === 'numerator' ? '分子' : '分母'}計算條件`, window.describeIndicatorRule(original.ruleTrees?.[number]?.[section], data.field_labels), window.describeIndicatorRule(sections[section], data.field_labels)));
        }
      });
      return rows.length ? `<section class="definition-review-group"><strong>${escapeHtml(cancer)}</strong>${rows.join('')}</section>` : '';
    }).join('');
    return groups || '<p>本次沒有修改指標內容，將以來源版本的內容建立版本。</p>';
  };
  const renderNewIndicatorEditor = indicators => {
    const host = contents.querySelector('[data-new-indicator-list]');
    if (!host) return;
    const fieldOptions = Object.entries(currentData?.field_labels || {}).sort(([a], [b]) => a.localeCompare(b, undefined, { numeric: true }));
    const renderCondition = (condition, indicatorIndex, section, conditionIndex) => {
      const range = condition.op === 'between';
      return `<div class="definition-condition" data-new-condition="${section}" data-indicator-index="${indicatorIndex}" data-condition-index="${conditionIndex}">
        <div class="definition-condition-controls">
          <select class="form-select form-select-sm" data-new-field aria-label="\u764c\u767b\u6b04\u4f4d">${fieldOptions.map(([code, label]) => `<option value="${escapeHtml(code)}"${code === condition.field ? ' selected' : ''}>${escapeHtml(label)} (${escapeHtml(code)})</option>`).join('')}</select>
          <select class="form-select form-select-sm" data-new-op aria-label="\u6bd4\u8f03\u65b9\u5f0f">${Object.entries(operators).map(([op, label]) => `<option value="${op}"${condition.op === op ? ' selected' : ''}>${label}</option>`).join('')}</select>
          <input type="number" class="form-control form-control-sm" data-new-value step="1" min="-1000000" max="1000000" value="${escapeHtml(condition.value)}"${range ? ' hidden' : ''} aria-label="\u6bd4\u8f03\u503c">
          <input type="number" class="form-control form-control-sm" data-new-min step="1" min="-1000000" max="1000000" value="${escapeHtml(condition.min)}"${range ? '' : ' hidden'} aria-label="\u6700\u5c0f\u503c">
          <span data-new-range-label${range ? '' : ' hidden'}>\u81f3</span>
          <input type="number" class="form-control form-control-sm" data-new-max step="1" min="-1000000" max="1000000" value="${escapeHtml(condition.max)}"${range ? '' : ' hidden'} aria-label="\u6700\u5927\u503c">
          <button type="button" class="btn btn-outline-danger btn-sm" data-remove-new-condition data-section="${section}" data-indicator-index="${indicatorIndex}" data-condition-index="${conditionIndex}" aria-label="\u79fb\u9664\u6b64\u689d\u4ef6"><i class="bi bi-trash" aria-hidden="true"></i></button>
        </div>
      </div>`;
    };
    host.innerHTML = indicators.map((item, index) => `<details class="definition-indicator" data-new-indicator-card open>
      <summary>\u65b0\u589e\u6307\u6a19 ${index + 1}${item.name ? `?${escapeHtml(item.name)}` : ''}</summary>
      <div class="definition-indicator-body">
        <div class="row g-3">
          <label class="col-md-8">\u6307\u6a19\u540d\u7a31<input class="form-control mt-2" data-new-name maxlength="3000" required value="${escapeHtml(item.name)}"></label>
          <label class="col-md-4">\u6307\u6a19\u5c6c\u6027<select class="form-select mt-2" data-new-type><option value="positive"${item.type === 'positive' ? ' selected' : ''}>\u6b63\u5411\u6307\u6a19</option><option value="negative"${item.type === 'negative' ? ' selected' : ''}>\u8ca0\u5411\u6307\u6a19</option><option value="observation"${item.type === 'observation' ? ' selected' : ''}>\u89c0\u5bdf\u6307\u6a19</option></select></label>
          <label class="col-12">\u9078\u53d6\u7406\u7531<textarea class="form-control mt-2" data-new-reason rows="2" maxlength="3000">${escapeHtml(item.selection_reason)}</textarea></label>
          <label class="col-md-6">\u5206\u5b50\u5b9a\u7fa9<textarea class="form-control mt-2" data-new-numerator-description rows="3" maxlength="3000" required>${escapeHtml(item.numerator_definition)}</textarea></label>
          <label class="col-md-6">\u5206\u6bcd\u5b9a\u7fa9<textarea class="form-control mt-2" data-new-denominator-description rows="3" maxlength="3000" required>${escapeHtml(item.denominator_definition)}</textarea></label>
        </div>
        ${['denominator', 'numerator'].map(section => `<section class="definition-section"><h4>${section === 'denominator' ? '分母條件' : '分子條件'}</h4><textarea hidden data-new-tree="${section}">${Array.isArray(item[section]) ? '' : escapeHtml(JSON.stringify(item[section]))}</textarea>${Array.isArray(item[section]) ? `<p class="small text-secondary mb-2">簡易條件須全部符合；日期、代碼與「或」請使用完整條件編輯。</p><div data-new-condition-list="${section}">${item[section].map((condition, conditionIndex) => renderCondition(condition, index, section, conditionIndex)).join('')}</div><button type="button" class="btn btn-outline-secondary btn-sm mt-2" data-add-new-condition data-section="${section}" data-indicator-index="${index}">新增條件</button>` : '<p class="small text-secondary">已使用完整條件設定。</p>'} <button type="button" class="btn btn-outline-primary btn-sm mt-2" data-edit-new-tree data-section="${section}" data-indicator-index="${index}">編輯完整條件</button></section>`).join('')}
        <button type="button" class="btn btn-outline-danger btn-sm mt-3" data-remove-new-indicator data-indicator-index="${index}"><i class="bi bi-trash me-1" aria-hidden="true"></i>\u79fb\u9664\u6b64\u6307\u6a19</button>
      </div>
    </details>`).join('');
    host.querySelectorAll('[data-new-condition]').forEach(row => {
      const range = row.querySelector('[data-new-op]').value === 'between';
      row.querySelector('[data-new-value]').hidden = range;
      row.querySelector('[data-new-min]').hidden = !range;
      row.querySelector('[data-new-max]').hidden = !range;
      row.querySelector('[data-new-range-label]').hidden = !range;
      row.querySelector('[data-new-value]').required = !range;
      row.querySelector('[data-new-min]').required = range;
      row.querySelector('[data-new-max]').required = range;
    });
  };
  const render = () => {
    const renderConditions = (item, section) => {
      const tree = currentData.rule_trees?.[item.id]?.[section];
      return `<textarea hidden data-rule-tree="${section}">${escapeHtml(JSON.stringify(tree))}</textarea><button type="button" class="btn btn-outline-primary btn-sm mt-2" data-edit-rule-tree="${section}">編輯完整條件</button>`;
    };
    contents.innerHTML = `<p class="small text-secondary mt-4 mb-2">點選指標名稱展開內容。請確認說明與計算條件一致；特殊條件保留原設定。</p>` + (currentData.descriptions || []).map(item => {
      const sections = ['denominator', 'numerator'].map(section => {
        const label = section === 'denominator' ? '分母' : '分子';
        const key = `${section}_definition`;
        return `<div class="definition-section"><h4>${label}</h4>
          <label class="w-100">${label}說明<textarea class="form-control" data-description="${key}" data-indicator="${escapeHtml(item.id)}" rows="3" maxlength="3000" required>${escapeHtml(item[key])}</textarea></label>
          <div class="small text-secondary mt-3">計算條件</div>${renderConditions(item, section)}</div>`;
      }).join('');
      return `<details class="definition-indicator" data-rule-indicator="${escapeHtml(item.id)}"><summary>指標 ${escapeHtml(item.id)}：${escapeHtml(item.name)}</summary>
        <div class="definition-indicator-body"><label class="w-100">指標名稱<input class="form-control mt-2" data-description="name" data-indicator="${escapeHtml(item.id)}" maxlength="3000" required value="${escapeHtml(item.name)}"></label>${sections}<label class="d-block mt-3 text-danger"><input type="checkbox" data-remove-indicator value="${escapeHtml(item.id)}"> 從儲存後的版本移除此指標</label></div></details>`;
    }).join('');
    if (editing) {
      contents.insertAdjacentHTML('beforeend', '<div class="definition-section mt-4"><div class="d-flex flex-wrap justify-content-between align-items-center gap-2"><h4 class="mb-1">新增指標</h4><button type="button" class="btn btn-outline-primary btn-sm" data-add-new-indicator><i class="bi bi-plus-lg me-1" aria-hidden="true"></i>新增指標</button></div><div data-new-indicator-list></div></div>');
      renderNewIndicatorEditor(drafts[currentData.cancer_key]?.values.newIndicators || []);
    }
    contents.querySelectorAll('[data-condition]').forEach(row => {
      const toggle = () => {
        const range = row.querySelector('[data-op]').value === 'between';
        row.querySelector('[data-second]').hidden = !range;
        row.querySelector('[data-second]').required = range;
        row.querySelector('[data-range-label]').hidden = !range;
      };
      row.querySelector('[data-op]').addEventListener('change', toggle);
      toggle();
    });
    updateControls();
  };
  const loadDetails = async () => {
    const requestId = ++loadId;
    busy = true; currentData = null; contents.replaceChildren(); updateControls();
    showStatus('正在載入指標定義…');
    try {
      const data = await fetchJson(`/api/indicators/definition-versions/${encodeURIComponent(versionSelect.value)}/cancers/${encodeURIComponent(cancerSelect.value)}`);
      if (requestId !== loadId) return;
      currentData = data; render();
      updateVersionState();
      if (editing) {
        if (!originals[data.cancer_key]) originals[data.cancer_key] = readDraft();
        restoreDraft(data.cancer_key);
        updateDraftStatus();
      }
      updateNavigation();
      const coverage = data.version.cancers?.length || 0;
      showStatus(data.included === false
        ? '此套版本尚未收錄這個癌別。目前顯示原始定義供加入，分析時不會自動套用。請確認後更新版本。'
        : coverage < cancerSelect.options.length
          ? `此套版本目前收錄 ${coverage}/${cancerSelect.options.length} 個癌別。可切換至未收錄癌別，確認定義後加入版本。`
          : editing ? '可切換癌別，一次儲存。' : versionSelect.value === 'default' ? '系統基準供建立新版本。' : data.version.status === 'INACTIVE' ? '可編輯，修改後須審核。' : ['DRAFT', 'PENDING'].includes(data.version.status) ? '可編輯，核准後啟用。' : '請先停用或建立新版再編輯。');
    } catch (error) { if (requestId === loadId) showStatus(error.message, true); }
    finally { if (requestId === loadId) { busy = false; updateControls(); } }
  };
  const loadVersions = async selected => {
    busy = true; currentData = null; contents.replaceChildren(); updateControls();
    const data = await fetchJson('/api/indicators/definition-versions?include_all=1');
    const versions = data.versions;
    versionSelect.replaceChildren(...versions.map(version => {
      const option = document.createElement('option');
      option.value = version.id;
      option.textContent = version.name;
      return option;
    }));
    if (!versions.some(version => version.id === selected)) {
      if (selected !== 'default') throw new Error('找不到指定的指標定義版本，請返回監測指標重新選擇。');
      selected = 'default';
    }
    versionSelect.value = selected;
    await loadDetails();
  };
  cancerSelect.addEventListener('change', () => {
    captureDraft();
    void loadDetails();
  });
  versionSelect.addEventListener('change', () => { void loadDetails(); });
  renameButton.addEventListener('click', async () => {
    if (busy || editing || !currentData || versionSelect.value === 'default') return;
    const selected = versionSelect.value;
    const result = await Swal.fire({
      title: '重新命名版本',
      text: currentData.version.status === 'INACTIVE' ? '重新命名後會送交管理員審核，核准後才能再次啟用。' : '',
      input: 'text',
      inputValue: currentData.version.name,
      inputAttributes: { maxlength: 100, 'aria-label': '版本名稱' },
      showCancelButton: true,
      confirmButtonText: '儲存名稱',
      cancelButtonText: '取消',
      inputValidator: value => !String(value || '').trim() ? '請輸入版本名稱。' : String(value).trim().length > 100 ? '版本名稱不可超過 100 個字。' : undefined
    });
    if (!result.isConfirmed) return;
    busy = true; updateControls();
    try {
      const renamed = await fetchJson(`/api/indicators/definition-versions/${encodeURIComponent(selected)}/rename`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: result.value, fingerprint: currentData.version.fingerprint })
      });
      await loadVersions(selected);
      showStatus(`版本已重新命名為「${renamed.name}」。${renamed.status === 'PENDING' ? '待管理員核准後才能啟用。' : ''}`);
    } catch (error) { showStatus(error.message, true); }
    finally { busy = false; updateControls(); }
  });
  deleteButton?.addEventListener('click', async () => {
    if (busy || editing || versionSelect.value === 'default') return;
    const selected = versionSelect.value;
    const name = versionSelect.selectedOptions[0].textContent;
    const confirmation = await window.utils.confirm(`確定刪除版本「${name}」？刪除後無法復原。已發布版本不可刪除。`, '刪除指標版本');
    if (!confirmation.isConfirmed) return;
    busy = true; updateControls();
    try {
      await fetchJson(`/api/indicators/definition-versions/${encodeURIComponent(selected)}`, { method: 'DELETE' });
      await loadVersions('default');
      showStatus(`已刪除版本「${name}」，目前顯示 115 年度指標定義（系統基準）。`);
    } catch (error) { showStatus(error.message, true); }
    finally { busy = false; updateControls(); }
  });
  startButton?.addEventListener('click', () => {
    if (!canManage || !currentData || busy) return;
    editing = true; revising = false; drafts = {}; originals = {}; originalVersionDescription = ''; originals[currentData.cancer_key] = readDraft(); updateDraftStatus(); nameInput.value = ''; descriptionInput.value = ''; reasonInput.value = ''; render(); nameInput.focus();
    showStatus('正在編輯新的整套版本。可切換癌別，完成後一次儲存。');
  });
  reviseButton?.addEventListener('click', () => {
    if (!canManage || !currentData || busy) return;
    if (versionSelect.value === 'default') return;
    if (!['DRAFT', 'PENDING', 'INACTIVE'].includes(currentData.version.status)) {
      editing = true; revising = false; drafts = {}; originals = {};
      originals[currentData.cancer_key] = readDraft();
      updateDraftStatus();
      nameInput.value = currentData.version?.definition_year || '';
      descriptionInput.value = currentData.version?.description || '';
      originalVersionDescription = '';
      reasonInput.value = '';
      render();
      contents.querySelector('details')?.setAttribute('open', '');
      contents.querySelector('input, textarea, select')?.focus();
      showStatus('正在以目前版本為來源建立新版；修改送審後不會覆寫原版本。');
      return;
    }
    editing = true; revising = true; drafts = {}; originals = {}; sourceFingerprint = currentData.version.fingerprint; originals[currentData.cancer_key] = readDraft(); updateDraftStatus();
    nameInput.value = currentData.version?.definition_year || '';
    descriptionInput.value = currentData.version?.description || '';
    originalVersionDescription = descriptionInput.value;
    reasonInput.value = '';
    render();
    contents.querySelector('details')?.setAttribute('open', '');
    contents.querySelector('input, textarea, select')?.focus();
    showStatus(currentData.version.status === 'INACTIVE' ? '正在編輯已停用版本；儲存後會送交管理員審核。' : '正在編輯待審或退回修改版本。可切換癌別，完成後一次儲存至目前版本。');
  });
  cancelButton?.addEventListener('click', async () => {
    captureDraft();
    const hasUnsavedMetadata = revising
      ? descriptionInput.value.trim() !== originalVersionDescription || reasonInput.value.trim()
      : nameInput.value.trim() || descriptionInput.value.trim() || reasonInput.value.trim();
    if (Object.keys(drafts).some(isChanged) || hasUnsavedMetadata) {
      const result = await window.utils.confirm('捨棄後會放棄所有尚未儲存的癌別與版本說明修改。確定捨棄？', '捨棄變更');
      if (!result.isConfirmed) return;
    }
    editing = false; revising = false; drafts = {}; originals = {}; originalVersionDescription = ''; render(); showStatus('已取消編輯，顯示原本選取的版本。');
  });
  saveButton?.addEventListener('click', async () => {
    if (!canManage || !editing || busy) return;
    const name = nameInput.value.trim();
    const description = descriptionInput.value.trim();
    const reason = reasonInput.value.trim();
    if (!revising && !name) { showStatus('請填寫新版本名稱。', true); nameInput.reportValidity(); nameInput.focus(); return; }
    if (revising && !reason) { showStatus('請填寫本次修改原因，以保留版本歷程。', true); reasonInput.reportValidity(); reasonInput.focus(); return; }
    captureDraft();
    let keys = Object.keys(drafts).filter(isChanged);
    const metadataChanged = revising && description !== originalVersionDescription;
    if (revising && currentData.included === false && !keys.includes(currentData.cancer_key)) keys.push(currentData.cancer_key);
    if (revising && !keys.length && !metadataChanged) { showStatus('尚未修改任何指標或版本說明，無需更新版本。'); return; }
    if (!keys.length) keys = [currentData.cancer_key];
    const cancerEdits = {};
    for (const key of keys) {
      const { data, values } = drafts[key];
      const label = [...cancerSelect.options].find(option => option.value === key)?.textContent || key;
      if (values.removed.length >= data.descriptions.length) {
        showStatus(`${label}至少須保留一項指標，請切換至該癌別檢查。`, true); return;
      }
      const validNumber = value => value !== '' && Number.isInteger(Number(value)) && Math.abs(Number(value)) <= 1000000;
      if (values.conditions.some((value, index) => !values.removed.includes(data.conditions[index].indicator) && (!validNumber(value.first) || (value.op === 'between' && (!validNumber(value.second) || Number(value.first) > Number(value.second)))))) {
        showStatus(`${label}的數值條件不完整或區間有誤，請切換至該癌別檢查。`, true); return;
      }
      if (values.descriptions.some((value, index) => !values.removed.includes(data.descriptions[Math.floor(index / 3)].id) && (!value.trim() || value.length > 3000))) {
        showStatus(`${label}的指標名稱或分子、分母說明未填寫，請切換至該癌別檢查。`, true); return;
      }
      const changes = [];
      const descriptions = data.descriptions.map((item, index) => ({ id: item.id,
        name: values.descriptions[index * 3].trim(), denominator_definition: values.descriptions[index * 3 + 1].trim(),
        numerator_definition: values.descriptions[index * 3 + 2].trim() })).filter(item => !values.removed.includes(item.id));
      if (values.newIndicators.length > 30) { showStatus(`${label}：一次最多新增 30 個指標。`, true); return; }
      for (const [newIndex, item] of values.newIndicators.entries()) {
        if (!item.name.trim() || !item.numerator_definition.trim() || !item.denominator_definition.trim()) {
          showStatus(`${label}：新增指標 ${newIndex + 1} 請填寫名稱、分子定義與分母定義。`, true); return;
        }
        for (const section of ['numerator', 'denominator']) {
          if (!Array.isArray(item[section])) continue;
          if (!item[section].length || item[section].length > 30 || item[section].some(condition => {
            if (!condition.field) return true;
            if (condition.op === 'between') return !validNumber(condition.min) || !validNumber(condition.max) || Number(condition.min) > Number(condition.max);
            return !validNumber(condition.value);
          })) {
            showStatus(`${label}：新增指標 ${newIndex + 1} 的${section === 'numerator' ? '分子' : '分母'}條件尚未填完整或數值範圍錯誤。`, true); return;
          }
        }
      }
      const ruleTrees = Object.fromEntries(Object.entries(values.ruleTrees || {}).filter(([number, sections]) =>
        !values.removed.includes(Number(number)) && JSON.stringify(sections) !== JSON.stringify(originals[key].ruleTrees?.[number])));
      const newIndicators = values.newIndicators.map(item => ({...item, ...Object.fromEntries(['numerator', 'denominator'].map(section => [section,
        Array.isArray(item[section]) ? item[section].map(condition => ({field:condition.field, op:condition.op,
          ...(condition.op === 'between' ? {min:Number(condition.min), max:Number(condition.max)} : {value:Number(condition.value)})})) : item[section]]))}));
      cancerEdits[key] = { changes, descriptions, removed_indicators: values.removed, new_indicators: newIndicators, rule_trees: ruleTrees };
    }
    const confirmText = revising
      ? `確定更新目前版本？本次儲存 ${keys.length} 個癌別，其他癌別沿用原設定。${currentData.version.status === 'INACTIVE' ? '已停用版本儲存後會送交管理員審核。' : '待審核或退回修改期間仍可繼續修改。'}`
      : `確定建立整套待審版本「${name}」？本次儲存 ${keys.length} 個癌別，其他癌別沿用原設定。送出後須由管理員核准，才能用於分析。`;
    const isRevision = revising;
    busy = true; updateControls();
    try {
      const confirmation = await Swal.fire({
        title: '確認本次修改',
        html: `<div class="definition-review"><p>${escapeHtml(confirmText)}</p>${reviewChanges(keys)}</div>`,
        showCancelButton: true,
        confirmButtonText: isRevision ? '確認更新版本' : '確認並建立版本',
        cancelButtonText: '返回修改',
        confirmButtonColor: '#2563eb',
        width: '720px',
        focusCancel: true,
      });
      if (!confirmation.isConfirmed) { busy = false; updateControls(); return; }
    } catch (error) {
      busy = false; updateControls(); showStatus('無法開啟確認視窗，請重新整理頁面後再試。', true); return;
    }
    const endpoint = '/api/indicators/definition-versions'
      + (isRevision ? `/${encodeURIComponent(versionSelect.value)}` : '');
    showStatus(isRevision ? '正在更新版本…' : '正在建立版本…');
    try {
      const result = await fetchJson(endpoint, { method: isRevision ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, definition_year: isRevision ? null : name, description, reason, base_version: versionSelect.value, fingerprint: sourceFingerprint, cancer_edits: cancerEdits }) });
      editing = false; revising = false; drafts = {}; originals = {}; originalVersionDescription = '';
      await loadVersions(result.id);
      if (currentData) showStatus(isRevision
        ? `已更新版本「${result.name}」。${result.status === 'DRAFT' ? '請送交審核後由管理員核准。' : '待管理員核准後，才可在監測指標分析中選用。'}`
        : '新待審版本已建立。待管理員核准後，才可在監測指標分析中選用。');
    } catch (error) { showStatus(error.message, true); }
    finally { busy = false; updateControls(); }
  });
  historyButton?.addEventListener('click', async () => {
    if (busy || !currentData || versionSelect.value === 'default') return;
    busy = true; updateControls();
    try {
      const data = await fetchJson(`/api/indicators/definition-versions/${encodeURIComponent(versionSelect.value)}/history`);
      const actionLabel = { CREATED: '建立版本並送審', REVISED: '由既有版本建立並送審', UPDATED: '更新版本', RENAMED: '重新命名', STATUS_CHANGED: '變更狀態', DELETED: '刪除版本' };
      const items = data.history.map(item => `<li class="mb-3"><strong>${escapeHtml(actionLabel[item.action] || item.action)}</strong>${item.status_before || item.status_after ? `：${escapeHtml(statusLabels[item.status_before] || item.status_before || '')} → ${escapeHtml(statusLabels[item.status_after] || item.status_after || '')}` : ''}<br><span class="text-secondary small">${escapeHtml(item.changed_at ? new Date(item.changed_at).toLocaleString('zh-TW', { hour12: false, timeZone: 'Asia/Taipei' }) : '')}${item.changed_by ? ` ・ ${escapeHtml(item.changed_by)}` : ''}</span>${item.reason ? `<div class="mt-1">原因：${escapeHtml(item.reason)}</div>` : ''}${item.rules_changed ? '<div class="text-secondary small">此筆紀錄包含規則或文字說明調整。</div>' : ''}</li>`).join('') || '<li>尚無修改歷程。</li>';
      await Swal.fire({ title: `修改歷程：${escapeHtml(currentData.version.name)}`, html: `<ol class="text-start ps-4">${items}</ol>`, width: '680px', confirmButtonText: '關閉' });
    } catch (error) { showStatus(error.message, true); }
    finally { busy = false; updateControls(); }
  });
  availabilitySwitch?.addEventListener('change', async () => {
    if (busy || !canApprove || !currentData || versionSelect.value === 'default') return;
    const target = availabilitySwitch.checked ? 'PUBLISHED' : 'INACTIVE';
    const previousChecked = !availabilitySwitch.checked;
    const result = await window.utils.confirm(
      target === 'PUBLISHED'
        ? '確定重新開啟此版本，讓一般使用者可在分析前選擇嗎？'
        : '確定關閉此版本，讓一般使用者無法再用於新的分析嗎？',
      target === 'PUBLISHED' ? '開啟版本' : '關閉版本',
    );
    if (!result.isConfirmed) { availabilitySwitch.checked = previousChecked; return; }
    busy = true; updateControls();
    try {
      const response = await fetchJson(`/api/indicators/definition-versions/${encodeURIComponent(versionSelect.value)}/status`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: target }),
      });
      await loadVersions(response.id);
      showStatus(target === 'PUBLISHED' ? '此版本已開啟，可供一般使用者分析時選擇。' : '此版本已關閉，不再提供新的分析選擇。');
    } catch (error) {
      availabilitySwitch.checked = previousChecked;
      showStatus(error.message, true);
    } finally { busy = false; updateControls(); }
  });
  changeStatusButton?.addEventListener('click', async () => {
    if (busy || !canApprove || !currentData || versionSelect.value === 'default' || !statusTarget.value) return;
    const target = statusTarget.value;
    const result = await Swal.fire({
      title: target === 'PUBLISHED' ? '核准並啟用此版本？' : `變更為「${statusLabels[target] || target}」`,
      text: target === 'PUBLISHED' ? '核准後，一般使用者即可在監測指標分析時選擇此版本。' : '',
      showCancelButton: true, confirmButtonText: target === 'PUBLISHED' ? '核准啟用' : '確認變更', cancelButtonText: '取消',
    });
    if (!result.isConfirmed) return;
    busy = true; updateControls();
    try {
      const response = await fetchJson(`/api/indicators/definition-versions/${encodeURIComponent(versionSelect.value)}/status`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: target }),
      });
      await loadVersions(response.id);
      showStatus(response.status === 'PUBLISHED'
        ? '版本已核准並啟用，一般使用者可在監測指標分析時選擇。'
        : `版本已變更為「${statusLabels[response.status] || response.status}」。`);
    } catch (error) { showStatus(error.message, true); }
    finally { busy = false; updateControls(); }
  });
  contents.addEventListener('click', event => {
    if (!editing || busy) return;
    const existingTree = event.target.closest('[data-edit-rule-tree]');
    if (existingTree) {
      const card = existingTree.closest('[data-rule-indicator]');
      const input = card.querySelector(`[data-rule-tree="${existingTree.dataset.editRuleTree}"]`);
      void window.openIndicatorRuleEditor(JSON.parse(input.value), currentData.field_labels).then(tree => {
        if (tree) { input.value = JSON.stringify(tree); captureDraft(); }
      });
      return;
    }
    const newTree = event.target.closest('[data-edit-new-tree]');
    if (newTree) {
      captureDraft();
      const key = currentData.cancer_key, index = Number(newTree.dataset.indicatorIndex), section = newTree.dataset.section;
      const item = drafts[key].values.newIndicators[index];
      let tree = item[section];
      if (Array.isArray(tree)) tree = {op:'all', rules:tree.map(condition => ({op:condition.op, field:condition.field,
        ...(condition.op === 'between' ? {min:condition.min === '' ? null : Number(condition.min), max:condition.max === '' ? null : Number(condition.max)} : {value:condition.value === '' ? null : Number(condition.value)})}))};
      void window.openIndicatorRuleEditor(tree, currentData.field_labels).then(result => {
        if (result) { item[section] = result; render(); restoreDraft(key); updateDraftStatus(); }
      });
      return;
    }
    const button = event.target.closest('[data-add-new-indicator], [data-remove-new-indicator], [data-add-new-condition], [data-remove-new-condition]');
    if (!button) return;
    captureDraft();
    const key = currentData.cancer_key;
    const items = drafts[key].values.newIndicators;
    const indicatorIndex = Number(button.dataset.indicatorIndex);
    if (button.hasAttribute('data-add-new-indicator')) items.push(blankNewIndicator());
    else if (button.hasAttribute('data-remove-new-indicator')) items.splice(indicatorIndex, 1);
    else {
      const section = button.dataset.section;
      if (button.hasAttribute('data-add-new-condition')) items[indicatorIndex][section].push(blankNewCondition());
      else items[indicatorIndex][section].splice(Number(button.dataset.conditionIndex), 1);
    }
    render();
    restoreDraft(key);
    updateDraftStatus();
  });
  contents.addEventListener('input', () => { if (editing) captureDraft(); });
  contents.addEventListener('change', event => {
    if (!editing) return;
    const row = event.target.closest('[data-new-condition]');
    if (row && event.target.matches('[data-new-op]')) {
      const range = event.target.value === 'between';
      row.querySelector('[data-new-value]').hidden = range;
      row.querySelector('[data-new-min]').hidden = !range;
      row.querySelector('[data-new-max]').hidden = !range;
      row.querySelector('[data-new-range-label]').hidden = !range;
      row.querySelector('[data-new-value]').required = !range;
      row.querySelector('[data-new-min]').required = range;
      row.querySelector('[data-new-max]').required = range;
    }
    captureDraft();
  });
  window.addEventListener('beforeunload', event => {
    const hasUnsavedMetadata = revising
      ? descriptionInput.value.trim() !== originalVersionDescription || reasonInput.value.trim()
      : nameInput.value.trim() || descriptionInput.value.trim() || reasonInput.value.trim();
    if (editing && (Object.keys(drafts).some(isChanged) || hasUnsavedMetadata)) { event.preventDefault(); event.returnValue = ''; }
  });
  const params = new URLSearchParams(window.location.search);
  const initialCancer = params.get('cancer') || 'Oral_Cavity';
  if (![...cancerSelect.options].some(option => option.value === initialCancer)) {
    showStatus('找不到指定的癌別。', true); return;
  }
  cancerSelect.value = initialCancer;
  const initialVersion = params.get('version') || 'default';
  void loadVersions(initialVersion).catch(error => { busy = false; showStatus(error.message, true); updateControls(); });
})();
