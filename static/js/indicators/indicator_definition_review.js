(() => {
  const root = document.getElementById('definitionReview');
  if (!root) return;

  const timeline = document.getElementById('reviewTimeline');
  const statusEl = document.getElementById('reviewStatus');
  const countEl = document.getElementById('reviewCount');
  const userFilter = document.getElementById('reviewUser');
  const dateFilter = document.getElementById('reviewDate');
  const clearFilter = document.getElementById('reviewClear');
  const canApprove = root.dataset.canApprove === 'true';
  const cancers = JSON.parse(root.dataset.cancers || '[]');
  const cancerNames = Object.fromEntries(cancers.map(item => [item.key, item.name]));
  const labels = { DRAFT: '退回修改', PENDING: '待審核', PUBLISHED: '已啟用', INACTIVE: '已停用' };
  const comparisonLabels = {
    between: '介於', equals: '等於', greater_than: '大於',
    greater_than_or_equal: '大於或等於', less_than: '小於', less_than_or_equal: '小於或等於',
  };
  let versions = [];

  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[char]));
  const showStatus = (message, isError = false) => {
    statusEl.textContent = message;
    statusEl.className = isError ? 'alert alert-danger mb-3' : 'text-secondary mb-3';
  };
  const fetchJson = async (url, options = {}) => {
    const response = await fetch(url, { credentials: 'same-origin', ...options });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok) throw new Error(data.error || '無法讀取指標版本資料。');
    return data;
  };
  const dateText = value => {
    if (!value) return '時間未提供';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString('zh-TW', { hour12: false, timeZone: 'Asia/Taipei' });
  };
  const taipeiDayKey = value => {
    if (!value) return 'unknown';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'unknown';
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Taipei', year: 'numeric', month: '2-digit', day: '2-digit',
    }).formatToParts(date);
    const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
    return `${values.year}-${values.month}-${values.day}`;
  };
  const taipeiDayText = key => {
    if (key === 'unknown') return '日期未提供';
    return new Date(`${key}T00:00:00+08:00`).toLocaleDateString('zh-TW', {
      timeZone: 'Asia/Taipei', year: 'numeric', month: 'long', day: 'numeric',
    });
  };
  const statusActions = version => {
    if (!canApprove) return '';
    const id = escapeHtml(version.id);
    const button = (target, text, klass, icon) => `<button type="button" class="btn ${klass} btn-sm" data-review-action data-id="${id}" data-target="${target}"><i class="bi ${icon} me-1" aria-hidden="true"></i>${text}</button>`;
    if (version.status === 'PENDING') return `${button('PUBLISHED', '核准並啟用', 'btn-success', 'bi-check-lg')}${button('DRAFT', '退回修改', 'btn-outline-danger', 'bi-arrow-counterclockwise')}`;
    if (version.status === 'DRAFT') return button('PENDING', '送交審核', 'btn-outline-primary', 'bi-send');
    if (version.status === 'PUBLISHED') return button('INACTIVE', '停用版本', 'btn-outline-danger', 'bi-toggle-off');
    if (version.status === 'INACTIVE') return button('PUBLISHED', '重新啟用', 'btn-outline-success', 'bi-toggle-on');
    return '';
  };
  const versionCard = version => {
    const cancerCount = version.cancers?.length ?? 0;
    const year = version.definition_year ? `・適用年度 ${escapeHtml(version.definition_year)}` : '';
    const description = version.description ? `<div class="text-secondary small mt-1">${escapeHtml(version.description)}</div>` : '';
    return `<article class="review-card">
      <div class="review-card-main">
        <div class="review-card-title">${escapeHtml(version.name)}</div>
        <div class="review-meta"><span><i class="bi bi-person me-1" aria-hidden="true"></i>${escapeHtml(version.created_by || '未提供建立者')}</span><span><i class="bi bi-clock me-1" aria-hidden="true"></i>${escapeHtml(dateText(version.created_at))}</span><span><i class="bi bi-pencil-square me-1" aria-hidden="true"></i>${escapeHtml(cancerCount)} 個癌別</span><span class="review-status review-status-${escapeHtml(version.status)}">${escapeHtml(labels[version.status] || version.status)}</span>${year ? `<span>${year}</span>` : ''}</div>${description}
      </div>
      <div class="review-actions"><button type="button" class="btn btn-sm btn-outline-secondary commit-card__action-icon" data-preview-id="${escapeHtml(version.id)}" title="查看版本內容" aria-label="查看版本內容"><i class="bi bi-file-earmark-text" aria-hidden="true"></i></button>${statusActions(version)}</div>
    </article>`;
  };
  const render = () => {
    const allSaved = versions.filter(version => version.id !== 'default');
    const saved = allSaved.filter(version => (!userFilter.value || version.created_by_key === userFilter.value)
      && (!dateFilter.value || taipeiDayKey(version.created_at) === dateFilter.value));
    const groups = new Map();
    saved.forEach(version => {
      const key = taipeiDayKey(version.created_at);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(version);
    });
    timeline.innerHTML = [...groups.entries()].map(([key, items]) => {
      const label = taipeiDayText(key);
      return `<section class="review-day"><div class="review-day-label"><span class="review-day-node" aria-hidden="true"></span>${escapeHtml(label)}</div>${items.map(versionCard).join('')}</section>`;
    }).join('') || `<div class="review-empty">${allSaved.length ? '沒有符合篩選條件的版本。' : '目前沒有已建立的指標版本。'}</div>`;
    const pending = saved.filter(version => version.status === 'PENDING').length;
    countEl.textContent = `共 ${saved.length} 個版本${canApprove ? `・待審核 ${pending} 個` : ''}`;
    clearFilter.hidden = !userFilter.value && !dateFilter.value;
  };
  const updateUserOptions = () => {
    const selected = userFilter.value;
    const creators = new Map();
    versions.filter(version => version.id !== 'default' && version.created_by_key).forEach(version => {
      creators.set(version.created_by_key, version.created_by || '未提供建立者');
    });
    userFilter.replaceChildren(new Option('所有操作者', ''));
    [...creators.entries()].sort((a, b) => a[1].localeCompare(b[1], 'zh-TW')).forEach(([key, name]) => {
      userFilter.add(new Option(name, key));
    });
    if (creators.has(selected)) userFilter.value = selected;
  };
  const load = async () => {
    showStatus('正在載入指標版本紀錄…');
    try {
      const data = await fetchJson('/api/indicators/definition-versions?include_all=1');
      versions = data.versions || [];
      updateUserOptions();
      render();
      showStatus('版本清單已更新。');
    } catch (error) {
      showStatus(error.message, true);
    }
  };
  const conditionText = condition => {
    const op = comparisonLabels[condition.op] || condition.op;
    return condition.op === 'between'
      ? `${op} ${condition.min} 至 ${condition.max}`
      : `${op} ${condition.value}`;
  };
  const showVersion = async version => {
    showStatus(`正在載入「${version.name}」的指標內容…`);
    try {
      const cancerKeys = version.cancers || [];
      const details = await Promise.all(cancerKeys.map(key => fetchJson(
        `/api/indicators/definition-versions/${encodeURIComponent(version.id)}/cancers/${encodeURIComponent(key)}`,
      )));
      const html = details.map(data => {
        const descriptions = new Map(data.descriptions.map(item => [Number(item.id), item]));
        const grouped = new Map();
        data.conditions.forEach(condition => {
          if (!grouped.has(condition.indicator)) grouped.set(condition.indicator, []);
          grouped.get(condition.indicator).push(condition);
        });
        const indicatorIds = [...new Set([...descriptions.keys(), ...grouped.keys()])].sort((a, b) => a - b);
        const indicators = indicatorIds.map(id => {
          const item = descriptions.get(id) || {};
          return `<div class="review-indicator"><strong>指標 ${id}：${escapeHtml(item.name || '')}</strong>
            <div><strong>分母定義：</strong>${escapeHtml(item.denominator_definition || '未提供')}</div>
            <div><strong>分子定義：</strong>${escapeHtml(item.numerator_definition || '未提供')}</div>
            <div class="review-condition">分母條件：${escapeHtml(window.describeIndicatorRule(data.rule_trees?.[id]?.denominator, data.field_labels))}</div>
            <div class="review-condition">分子條件：${escapeHtml(window.describeIndicatorRule(data.rule_trees?.[id]?.numerator, data.field_labels))}</div>
          </div>`;
        }).join('');
        return `<details class="review-cancer"><summary>${escapeHtml(cancerNames[data.cancer_key] || data.cancer_key)}（${indicatorIds.length} 項指標）</summary>${indicators || '<p class="text-secondary mb-0 mt-2">此癌別沒有指標。</p>'}</details>`;
      }).join('');
      await Swal.fire({
        title: escapeHtml(version.name),
        html: `<div class="review-details">${html || '<p>此版本沒有包含癌別。</p>'}</div>`,
        width: '900px', confirmButtonText: '關閉', confirmButtonColor: '#2563eb',
      });
      showStatus(`已載入「${version.name}」內容。`);
    } catch (error) {
      showStatus(error.message, true);
    }
  };
  const changeStatus = async (version, target) => {
    let reason = '';
    const returning = target === 'DRAFT';
    const messages = {
      PUBLISHED: '核准後，此完整版本會提供給使用者進行監測指標分析。',
      DRAFT: '退回後，建立者可回到資料維護頁修改並再次送審。',
      PENDING: '送審後，版本會出現在待審核清單。',
      INACTIVE: '停用後，使用者不能再將此版本用於新的分析。',
    };
    if (returning) {
      const result = await Swal.fire({
        title: '退回指標版本', text: messages[target], input: 'textarea',
        inputLabel: '退回原因', inputPlaceholder: '請說明需要修改的地方',
        showCancelButton: true, confirmButtonText: '確認退回', cancelButtonText: '取消',
        inputValidator: value => String(value || '').trim() ? undefined : '請填寫退回原因。',
      });
      if (!result.isConfirmed) return;
      reason = String(result.value || '').trim();
    } else {
      const result = await Swal.fire({
        title: target === 'PUBLISHED' ? '確認啟用版本？' : target === 'INACTIVE' ? '確認停用版本？' : '確認送交審核？',
        text: messages[target] || '', showCancelButton: true,
        confirmButtonText: target === 'PUBLISHED' ? '核准並啟用' : target === 'INACTIVE' ? '停用版本' : '送交審核',
        cancelButtonText: '取消', confirmButtonColor: target === 'INACTIVE' ? '#dc3545' : '#198754',
      });
      if (!result.isConfirmed) return;
    }
    showStatus(`正在更新「${version.name}」狀態…`);
    try {
      const data = await fetchJson(`/api/indicators/definition-versions/${encodeURIComponent(version.id)}/status`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: target, reason }),
      });
      showStatus(`「${data.name}」已變更為「${labels[data.status] || data.status}」。`);
      await load();
    } catch (error) {
      showStatus(error.message, true);
    }
  };

  document.addEventListener('click', event => {
    const previewButton = event.target.closest('[data-preview-id]');
    if (previewButton) {
      const version = versions.find(item => item.id === previewButton.dataset.previewId);
      if (version) void showVersion(version);
      return;
    }
    const actionButton = event.target.closest('[data-review-action]');
    if (actionButton) {
      const version = versions.find(item => item.id === actionButton.dataset.id);
      if (version) void changeStatus(version, actionButton.dataset.target);
    }
  });

  userFilter.addEventListener('change', render);
  dateFilter.addEventListener('change', render);
  clearFilter.addEventListener('click', () => {
    userFilter.value = '';
    dateFilter.value = '';
    render();
  });
  void load();
})();
