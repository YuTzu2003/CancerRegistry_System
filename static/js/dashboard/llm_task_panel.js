(() => {
  const labels = { queued: '排隊中', running: '處理中', retrying: '準備重試', completed: '已完成', partial_failed: '部分完成', failed: '處理失敗', cancelled: '已取消' };
  const value = (task, key) => task[key] ?? task[key[0].toLowerCase() + key.slice(1)];
  const esc = (text) => String(text ?? '').replace(/[&<>'"`]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;', '`': '&#x60;' }[char]));
  const filters = { query: '', status: '' };
  let tasks = [];
  const selectedTaskIds = new Set();

  const formatDate = (text) => {
    if (!text) return '尚未開始';
    const date = new Date(text);
    if (Number.isNaN(date.getTime())) return text;
    const pad = (number) => String(number).padStart(2, '0');
    return `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
  };
  const duration = (startText, endText) => {
    if (!startText) return '0 秒';
    const start = new Date(startText); const end = endText ? new Date(endText) : new Date();
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return '0 秒';
    const seconds = Math.max(0, Math.floor((end - start) / 1000));
    return seconds >= 60 ? `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒` : `${seconds} 秒`;
  };
  const visibleTasks = () => tasks.filter((task) => {
    const status = String(value(task, 'Status') || '');
    const text = [value(task, 'DocumentLabel'), value(task, 'TaskTitle'), value(task, 'TaskID'), labels[status]].join(' ').toLocaleLowerCase();
    return (!filters.query || text.includes(filters.query.toLocaleLowerCase())) && (!filters.status || status === filters.status);
  });
  const render = () => {
    const panel = document.querySelector('#annualLlmTaskPanel');
    if (!panel) return;
    panel.classList.remove('d-none');
    const displayed = visibleTasks();
    panel.innerHTML = `<section class="llm-task-panel">
      <header class="llm-record-header"><div><span class="llm-record-kicker">MANAGE</span><h2>LLM 工作任務</h2><p class="llm-record-count">顯示 ${displayed.length} / ${tasks.length} 筆任務</p></div>
      <div class="llm-batch-actions"><button id="btnSelectAllTasks" class="btn btn-outline-secondary" type="button">全部勾選</button><button id="btnClearTaskSelection" class="btn btn-outline-secondary" type="button">取消勾選</button><button id="btnBatchDelete" class="btn btn-danger" type="button">刪除勾選項目</button><button id="btnRefreshTasks" class="btn btn-outline-secondary" type="button">重新整理</button></div></header>
      <div class="llm-task-filters"><label class="llm-filter-field llm-filter-field--search"><span>搜尋</span><input id="llmTaskQuery" type="search" value="${esc(filters.query)}" placeholder="年報檔名、分析項目、任務 ID"></label><label class="llm-filter-field"><span>狀態</span><select id="llmTaskStatus"><option value="">全部狀態</option>${Object.entries(labels).map(([key, label]) => `<option value="${key}"${filters.status === key ? ' selected' : ''}>${label}</option>`).join('')}</select></label><button id="btnResetTaskFilters" class="btn btn-outline-secondary" type="button">重設</button></div>
      <div class="llm-task-list">${displayed.length ? displayed.map((task) => {
        const status = String(value(task, 'Status') || 'queued'); const id = String(value(task, 'TaskID') || '');
        const elapsed = duration(value(task, 'CreatedAt'), ['completed', 'partial_failed', 'failed', 'cancelled'].includes(status) ? value(task, 'UpdatedAt') : null);
        return `<article class="llm-task-row"><label class="llm-task-select" aria-label="選取任務 ${esc(id)}"><input class="task-cb" type="checkbox" value="${esc(id)}"${selectedTaskIds.has(id) ? ' checked' : ''}></label><div class="llm-task-row__content"><div class="llm-task-row__heading"><h3>${esc(value(task, 'DocumentLabel') || '年報分析')}</h3></div><div style="display:flex; flex-wrap:wrap; gap:8px; align-items:center; font-size:12px; margin-top:6px; color:var(--muted,#6b7280);"><span>建立時間：${esc(formatDate(value(task, 'CreatedAt')))}</span><span style="width:4px;height:4px;border-radius:50%;background:#d1d5db;flex-shrink:0;"></span><span>處理時間：${esc(elapsed)}</span><span style="width:4px;height:4px;border-radius:50%;background:#d1d5db;flex-shrink:0;"></span><span class="llm-task-status is-${esc(status)}">狀態：${esc(labels[status] || status)}</span></div></div><div class="llm-task-side"><span class="llm-task-id">${esc(id.slice(-5))}</span><div class="llm-task-side__bottom"><div class="llm-task-row__actions"><button class="btn btn-sm btn-outline-dark llm-preview" type="button" data-id="${esc(id)}">預覽</button>${value(task, 'TaskType') === 'annual_report' && status === 'completed' ? `<button class="btn btn-sm btn-outline-success llm-export" type="button" data-id="${esc(id)}">匯出</button>` : ''}<button class="btn btn-sm btn-danger llm-row-delete" type="button" data-id="${esc(id)}">刪除</button></div></div></div></article>`;
      }).join('') : `<div class="llm-task-empty">${tasks.length ? '找不到符合搜尋或狀態條件的任務。' : '目前尚無工作任務。'}</div>`}</div></section>`;
    const updateDeleteLabel = () => { panel.querySelector('#btnBatchDelete').textContent = '刪除勾選項目'; };
    panel.querySelector('#llmTaskQuery').addEventListener('input', (event) => { filters.query = event.target.value; render(); });
    panel.querySelector('#llmTaskStatus').addEventListener('change', (event) => { filters.status = event.target.value; render(); });
    panel.querySelector('#btnResetTaskFilters').addEventListener('click', () => { filters.query = ''; filters.status = ''; render(); });
    panel.querySelector('#btnRefreshTasks').addEventListener('click', () => load());
    panel.querySelector('#btnSelectAllTasks').addEventListener('click', () => { panel.querySelectorAll('.task-cb').forEach((item) => { item.checked = true; selectedTaskIds.add(item.value); }); updateDeleteLabel(); });
    panel.querySelector('#btnClearTaskSelection').addEventListener('click', () => { selectedTaskIds.clear(); panel.querySelectorAll('.task-cb').forEach((item) => { item.checked = false; }); updateDeleteLabel(); });
    panel.querySelectorAll('.task-cb').forEach((item) => item.addEventListener('change', () => { if (item.checked) selectedTaskIds.add(item.value); else selectedTaskIds.delete(item.value); updateDeleteLabel(); }));
    panel.querySelector('#btnBatchDelete').addEventListener('click', async () => { const ids = [...panel.querySelectorAll('.task-cb:checked')].map((item) => item.value); if (!ids.length || !confirm(`確定要刪除 ${ids.length} 筆工作任務嗎？`)) return; await Promise.all(ids.map((id) => fetch(`/api/llm-tasks/${encodeURIComponent(id)}`, { method: 'DELETE' }))); await load(); });
    panel.querySelectorAll('.llm-row-delete').forEach((button) => button.addEventListener('click', async () => { if (!confirm('確定要刪除此工作任務嗎？')) return; await fetch(`/api/llm-tasks/${encodeURIComponent(button.dataset.id)}`, { method: 'DELETE' }); await load(); }));
    panel.querySelectorAll('.llm-preview').forEach((button) => button.addEventListener('click', () => preview(button.dataset.id)));
    panel.querySelectorAll('.llm-export').forEach((button) => button.addEventListener('click', () => window.location.assign('/dashboard-preview/' + encodeURIComponent(button.dataset.id) + '?export=1')));
  };
  const preview = (id) => { window.location.assign('/dashboard-preview/' + encodeURIComponent(id)); };
  const load = async () => {
    try {
      const response = await fetch('/api/llm-tasks?limit=50');
      const payload = await response.json();
      if (response.ok && payload.success) {
        tasks = (payload.tasks || []).filter((task) => ['chart', 'annual_report'].includes(value(task, 'TaskType')));
      }
    } catch (e) {}
    render();
    if (tasks.some((task) => ['queued', 'running', 'retrying'].includes(value(task, 'Status')))) {
      setTimeout(() => load().catch(() => {}), 3000);
    }
  };
  document.addEventListener('DOMContentLoaded', () => load().catch(() => {}));
  window.addEventListener('llm-task-created', () => load().catch(() => {}));
})();