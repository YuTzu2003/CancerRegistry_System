(() => {
  const labels = { queued: '處理中', running: '處理中', retrying: '處理中', completed: '已完成', partial_failed: '部分完成', failed: '處理失敗', cancelled: '已取消' };
  const value = (task, key) => task[key] ?? task[key[0].toLowerCase() + key.slice(1)];
  const esc = (text) => String(text ?? '').replace(/[&<>'"`]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;', '`': '&#x60;' }[char]));
  const filters = { query: '', status: '' };
  let tasks = [];
  let loadError = false;
  let currentPage = 0;
  let hasMoreTasks = false;
  let loadingPage = false;
  const selectedTaskIds = new Set();
  const taskPanel = document.querySelector('#annualLlmTaskPanel');
  const taskTypes = taskPanel?.dataset.llmTaskType === 'comparison_report' ? ['comparison_report'] : ['chart', 'annual_report'];
  const taskList = taskPanel?.querySelector('#llmTaskList');

  const confirmTaskDeletion = async (count) => {
    if (!window.Swal) return false;
    const result = await window.Swal.fire({
      icon: 'warning',
      title: count === 1 ? '確定要刪除這筆紀錄嗎？' : `確定要刪除 ${count} 筆紀錄嗎？`,
      text: '刪除後無法復原。',
      showCancelButton: true,
      confirmButtonText: '確認刪除',
      cancelButtonText: '取消',
      confirmButtonColor: '#dc3545',
      reverseButtons: true,
    });
    return result.isConfirmed;
  };

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
    const statusMatches = filters.status === 'processing'
      ? ['queued', 'running', 'retrying'].includes(status)
      : !filters.status || status === filters.status;
    return (!filters.query || text.includes(filters.query.toLocaleLowerCase())) && statusMatches;
  });
  const taskInfoModal = () => {
    let modal = document.getElementById('analysisInfoModal');
    if (modal) return modal;
    document.body.insertAdjacentHTML('beforeend', `<div class="modal fade analysis-info-modal" id="analysisInfoModal" tabindex="-1" aria-labelledby="analysisInfoModalTitle" aria-hidden="true"><div class="modal-dialog modal-dialog-centered modal-dialog-scrollable"><div class="modal-content"><div class="modal-header"><h2 class="modal-title" id="analysisInfoModalTitle">分析資訊</h2><button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="關閉"></button></div><div class="modal-body" data-analysis-info-body></div><div class="modal-footer"><button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">關閉</button></div></div></div></div>`);
    return document.getElementById('analysisInfoModal');
  };
  const showTaskInfo = (task) => {
    if (!task) return;
    const info = value(task, 'AnalysisInfo') || {};
    const items = Array.isArray(info.analysis_items) ? info.analysis_items : [];
    const status = String(value(task, 'Status') || 'queued');
    const statusText = labels[status] || status || '未記錄';
    const cancerTitle = info.cancer_title || '未記錄';
    const yearTitle = info.year_title || '未記錄';
    const rows = [
      ['分析檔案', value(task, 'DocumentLabel') || '年報分析'],
      ['任務狀態', statusText],
      ['建立時間', formatDate(value(task, 'CreatedAt'))],
      ['完成時間', value(task, 'CompletedAt') ? formatDate(value(task, 'CompletedAt')) : '尚未完成'],
    ];
    const analysisItems = items.length ? items : [value(task, 'TaskTitle') || '未記錄'];
    const text = [
      `癌別：${cancerTitle}`,
      `分析年度：${yearTitle}`,
      `分析項目：${analysisItems.join('、')}`,
      ...rows.map(([label, detail]) => `${label}：${detail}`),
    ].join('\n');
    if (!window.bootstrap?.Modal) return window.alert(text);
    const modal = taskInfoModal();
    modal.querySelector('[data-analysis-info-body]').innerHTML = `<section class="analysis-info" aria-label="分析資訊明細"><section class="analysis-info__focus" aria-label="篩選條件"><dl class="analysis-info__selection"><div><dt>癌別</dt><dd>${esc(cancerTitle)}</dd></div><div><dt>分析年度</dt><dd>${esc(yearTitle)}</dd></div></dl></section><section class="analysis-info__items"><h3>分析項目（癌別｜項目）</h3><ul>${analysisItems.map((item) => `<li>${esc(item)}</li>`).join('')}</ul></section><dl class="analysis-info__facts">${rows.map(([label, detail]) => `<div class="analysis-info__fact"><dt>${esc(label)}</dt><dd>${esc(detail)}</dd></div>`).join('')}</dl></section>`;
    window.bootstrap.Modal.getOrCreateInstance(modal).show();
  };
  const render = () => {
    if (!taskPanel || !taskList) return;
    taskPanel.classList.remove('d-none');
    const displayed = visibleTasks();
    taskPanel.querySelector('#llmTaskCount').textContent = loadError ? '紀錄載入失敗' : `第 ${currentPage + 1} 頁，顯示 ${displayed.length} 筆${hasMoreTasks ? '，尚有下一頁' : ''}`;
    const taskRows = displayed.map((task) => {
      const status = String(value(task, 'Status') || 'queued'); const id = String(value(task, 'TaskID') || '');
      const elapsed = duration(value(task, 'CreatedAt'), ['completed', 'partial_failed', 'failed', 'cancelled'].includes(status) ? value(task, 'CompletedAt') : null);
      const progress = ['annual_report', 'comparison_report'].includes(value(task, 'TaskType')) ? `<span>中英敘述：${esc(value(task, 'ProgressCurrent') || 0)}/${esc(value(task, 'ProgressTotal') || 0)}</span>` : '';
      return `<article class="llm-task-row"><label class="llm-task-select" aria-label="選取任務 ${esc(id)}"><input class="task-cb" type="checkbox" value="${esc(id)}"${selectedTaskIds.has(id) ? ' checked' : ''}></label><div class="llm-task-row__content"><div class="llm-task-row__heading"><h3>${esc(value(task, 'DocumentLabel') || '年報分析')}</h3></div><div style="display:flex; flex-wrap:wrap; gap:8px; align-items:center; font-size:12px; margin-top:6px; color:var(--muted,#6b7280);"><span>建立時間：${esc(formatDate(value(task, 'CreatedAt')))}</span><span style="width:4px;height:4px;border-radius:50%;background:#d1d5db;flex-shrink:0;"></span><span>處理時間：${esc(elapsed)}</span><span style="width:4px;height:4px;border-radius:50%;background:#d1d5db;flex-shrink:0;"></span><span class="llm-task-status is-${esc(status)}">狀態：${esc(labels[status] || status)}</span>${progress}</div></div><div class="llm-task-side"><span class="llm-task-id">${esc(id.slice(-5))}</span><div class="llm-task-side__bottom"><div class="llm-task-row__actions"><button class="btn btn-sm btn-outline-dark llm-preview" type="button" data-id="${esc(id)}" data-type="${esc(value(task, 'TaskType'))}">預覽</button>${value(task, 'TaskType') === 'annual_report' && status === 'completed' ? `<button class="btn btn-sm btn-success llm-export" type="button" data-id="${esc(id)}">匯出</button>` : ''}<button class="btn btn-sm btn-danger llm-row-delete" type="button" data-id="${esc(id)}">刪除</button></div></div></div></article>`;
    }).join('');
    const emptyState = loadError && !tasks.length ? '<div class="llm-task-empty">暫時無法載入紀錄，請按「重新整理」再試。</div>' : displayed.length ? taskRows : `<div class="llm-task-empty">${tasks.length ? '找不到符合搜尋或狀態條件的任務。' : '目前尚無工作任務。'}</div>`;
    const pagination = `<nav class="llm-task-pagination" aria-label="年報分析紀錄分頁"><button id="btnPreviousTaskPage" class="llm-task-pagination__button" type="button"${currentPage === 0 || loadingPage ? ' disabled' : ''}>上一頁</button><p class="llm-task-pagination__current"><strong>第 ${currentPage + 1} 頁</strong></p><button id="btnNextTaskPage" class="llm-task-pagination__button" type="button"${!hasMoreTasks || loadingPage ? ' disabled' : ''}>下一頁</button></nav>`;
    taskList.innerHTML = emptyState + pagination;
    taskList.querySelectorAll('.llm-preview').forEach((button) => {
      button.insertAdjacentHTML('beforebegin', `<button class="btn btn-sm btn-outline-secondary llm-info" type="button" data-id="${esc(button.dataset.id)}">資訊</button>`);
    });
  };
  const preview = (id, taskType) => { window.location.assign((taskType === 'comparison_report' ? '/comparison-preview/' : '/dashboard-preview/') + encodeURIComponent(id)); };
  const load = async (page = currentPage) => {
    if (loadingPage) return;
    const targetPage = Math.max(0, Number(page) || 0);
    loadingPage = true;
    try {
      const response = await fetch(`/api/llm-tasks?limit=20&offset=${targetPage * 20}`);
      const payload = await response.json();
      if (!response.ok || !payload.success) throw new Error(payload.error || '紀錄載入失敗');
      tasks = (payload.tasks || []).filter((task) => (
        taskTypes.includes(value(task, 'TaskType'))
        && value(task, 'InsightModule') !== 'indicators'
      ));
      currentPage = targetPage;
      hasMoreTasks = Boolean(payload.has_more);
      loadError = false;
    } catch (error) {
      loadError = true;
      console.error('Unable to load LLM tasks:', error);
    } finally {
      loadingPage = false;
    }
    render();
    if (tasks.some((task) => ['queued', 'running', 'retrying'].includes(value(task, 'Status')))) {
      setTimeout(() => load(currentPage).catch(() => {}), 3000);
    }
  };
  const bindPanelEvents = () => {
    if (!taskPanel || !taskList) return;
    taskPanel.querySelector('#llmTaskQuery').addEventListener('input', (event) => { filters.query = event.target.value; render(); });
    taskPanel.querySelector('#llmTaskStatus').addEventListener('change', (event) => { filters.status = event.target.value; render(); });
    taskPanel.querySelector('#btnResetTaskFilters').addEventListener('click', () => {
      filters.query = ''; filters.status = '';
      taskPanel.querySelector('#llmTaskQuery').value = '';
      taskPanel.querySelector('#llmTaskStatus').value = '';
      render();
    });
    taskPanel.querySelector('#btnRefreshTasks').addEventListener('click', () => load());
    taskPanel.querySelector('#btnSelectAllTasks').addEventListener('click', () => {
      taskList.querySelectorAll('.task-cb').forEach((item) => { item.checked = true; selectedTaskIds.add(item.value); });
    });
    taskPanel.querySelector('#btnClearTaskSelection').addEventListener('click', () => {
      selectedTaskIds.clear(); taskList.querySelectorAll('.task-cb').forEach((item) => { item.checked = false; });
    });
    taskPanel.querySelector('#btnBatchDelete').addEventListener('click', async () => {
      const ids = [...taskList.querySelectorAll('.task-cb:checked')].map((item) => item.value);
      if (!ids.length || !(await confirmTaskDeletion(ids.length))) return;
      await Promise.all(ids.map((id) => fetch(`/api/llm-tasks/${encodeURIComponent(id)}`, { method: 'DELETE' })));
      ids.forEach((id) => selectedTaskIds.delete(id));
      await load();
    });
    taskList.addEventListener('change', (event) => {
      if (!event.target.matches('.task-cb')) return;
      if (event.target.checked) selectedTaskIds.add(event.target.value); else selectedTaskIds.delete(event.target.value);
    });
    taskList.addEventListener('click', async (event) => {
      const button = event.target.closest('button');
      if (!button) return;
      if (button.matches('.llm-info')) showTaskInfo(tasks.find((task) => String(value(task, 'TaskID')) === button.dataset.id));
      if (button.matches('.llm-preview')) preview(button.dataset.id, button.dataset.type);
      if (button.matches('.llm-export')) window.location.assign('/dashboard-preview/' + encodeURIComponent(button.dataset.id) + '?export=1');
      if (button.matches('#btnPreviousTaskPage')) await load(currentPage - 1);
      if (button.matches('#btnNextTaskPage')) await load(currentPage + 1);
      if (button.matches('.llm-row-delete') && await confirmTaskDeletion(1)) {
        await fetch(`/api/llm-tasks/${encodeURIComponent(button.dataset.id)}`, { method: 'DELETE' });
        selectedTaskIds.delete(button.dataset.id);
        await load();
      }
    });
  };
  document.addEventListener('DOMContentLoaded', () => { bindPanelEvents(); load().catch(() => {}); });
  window.addEventListener('llm-task-created', () => { currentPage = 0; load().catch(() => {}); });
})();
