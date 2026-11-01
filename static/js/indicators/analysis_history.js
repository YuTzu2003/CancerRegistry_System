(() => {
  document.body.insertAdjacentHTML('beforeend', `
    <div class="modal fade" id="indicatorAnalysisHistoryModal" tabindex="-1" aria-labelledby="indicatorAnalysisHistoryTitle" aria-hidden="true">
      <div class="modal-dialog modal-xl modal-dialog-scrollable"><div class="modal-content">
        <div class="modal-header"><h2 class="modal-title fs-5" id="indicatorAnalysisHistoryTitle">分析紀錄</h2><button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="關閉"></button></div>
        <div class="modal-body"><p class="text-secondary small">保存每次分析使用的診斷年度、指標版本、規則快照與彙總結果。</p>
          <div id="indicatorAnalysisHistoryStatus" class="text-secondary" role="status" aria-live="polite">按「載入紀錄」查看已保存的分析。</div>
          <div class="table-responsive"><table class="table table-sm table-bordered align-middle d-none" id="indicatorAnalysisHistoryTable"><thead class="table-light"><tr><th>分析時間</th><th>診斷年度</th><th>癌別</th><th>指標定義</th><th>操作者</th><th>內容</th></tr></thead><tbody id="indicatorAnalysisHistoryRows"></tbody></table></div>
          <section id="indicatorAnalysisHistoryDetail" class="d-none mt-4" aria-live="polite"></section>
        </div>
        <div class="modal-footer"><button type="button" class="btn btn-outline-secondary" id="btnLoadIndicatorAnalysisHistory">載入紀錄</button><button type="button" class="btn btn-secondary" data-bs-dismiss="modal">關閉</button></div>
      </div></div>
    </div>`);
  const modal = document.getElementById('indicatorAnalysisHistoryModal');
  if (!modal) return;

  const loadButton = document.getElementById('btnLoadIndicatorAnalysisHistory');
  const status = document.getElementById('indicatorAnalysisHistoryStatus');
  const table = document.getElementById('indicatorAnalysisHistoryTable');
  const rows = document.getElementById('indicatorAnalysisHistoryRows');
  const detail = document.getElementById('indicatorAnalysisHistoryDetail');
  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[char]);
  const formatTime = value => {
    if (!value) return '—';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? escapeHtml(value) : new Intl.DateTimeFormat('zh-TW', {
      timeZone: 'Asia/Taipei', year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
    }).format(date);
  };
  let loading = false;

  const loadRuns = async () => {
    if (loading) return;
    loading = true;
    loadButton.disabled = true;
    status.textContent = '正在載入分析紀錄…';
    detail.classList.add('d-none');
    try {
      const response = await fetch('/api/indicators/analysis-runs', { headers: { Accept: 'application/json' } });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.ok) throw new Error(data.error || '載入分析紀錄失敗。');
      rows.innerHTML = data.runs.map(run => `
        <tr>
          <td>${formatTime(run.created_at)}</td>
          <td>${escapeHtml(run.year_start)}–${escapeHtml(run.year_end)}</td>
          <td>${escapeHtml((run.cancers || []).join('、'))}</td>
          <td>${escapeHtml(run.definition_version_name)}</td>
          <td>${escapeHtml(run.user_id)}</td>
          <td><button class="btn btn-sm btn-outline-primary" type="button" data-open-analysis-run="${escapeHtml(run.id)}">查看結果</button></td>
        </tr>`).join('');
      table.classList.toggle('d-none', data.runs.length === 0);
      status.textContent = data.runs.length
        ? `共載入 ${data.runs.length} 筆${data.can_view_all ? '（包含其他使用者）' : ''}。最多顯示最近 100 筆。`
        : '目前沒有已保存的分析紀錄。';
    } catch (error) {
      table.classList.add('d-none');
      status.textContent = error.message || '載入分析紀錄失敗。';
    } finally {
      loading = false;
      loadButton.disabled = false;
    }
  };

  const showRun = async runId => {
    detail.classList.remove('d-none');
    detail.innerHTML = '<div class="text-secondary">正在讀取分析內容…</div>';
    try {
      const response = await fetch(`/api/indicators/analysis-runs/${encodeURIComponent(runId)}`, { headers: { Accept: 'application/json' } });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.ok) throw new Error(data.error || '讀取分析內容失敗。');
      const run = data.run;
      const reports = run.result_snapshot?.reports || [];
      const reportSections = reports.map(report => {
        const indicators = (report.indicators || []).map(item => {
          const targetLabel = item.target_value == null
            ? '\u672a\u8a2d\u5b9a'
            : `${escapeHtml(item.target_operator || '>=')}${escapeHtml(item.target_value)}%`;
          const targetStatus = item.target_met == null
            ? '\u672a\u5224\u5b9a'
            : item.target_met ? '\u9054\u6a19' : '\u672a\u9054\u6a19';
          return `
          <tr><td>${escapeHtml(item.id)}</td><td>${escapeHtml(item.name)}</td>
          <td>${escapeHtml(item.numerator)}</td><td>${escapeHtml(item.denominator)}</td>
          <td>${item.percentage == null ? '\u2014' : `${escapeHtml(item.percentage)}%`}</td>
          <td>${targetLabel}</td><td>${targetStatus}</td>
          <td>${escapeHtml(item.numerator_definition)}</td><td>${escapeHtml(item.denominator_definition)}</td></tr>`;
        }).join('');
        return `<h3 class="h6 mt-4">${escapeHtml(report.cancer_name || report.cancer_key)}</h3>
          <p class="small text-secondary">\u8f38\u5165 ${escapeHtml(report.input_count)} \u7b46\uff0c\u7d0d\u5165\u5206\u6790 ${escapeHtml(report.included_count)} \u7b46</p>
          <div class="table-responsive"><table class="table table-sm table-bordered align-middle"><thead class="table-light"><tr><th>\u7de8\u865f</th><th>\u6307\u6a19</th><th>\u5206\u5b50</th><th>\u5206\u6bcd</th><th>\u6bd4\u7387</th><th>\u76ee\u6a19\u9580\u6abb</th><th>\u9054\u6a19\u72c0\u614b</th><th>\u5206\u5b50\u5b9a\u7fa9</th><th>\u5206\u6bcd\u5b9a\u7fa9</th></tr></thead><tbody>${indicators || '<tr><td colspan="9">\u6c92\u6709\u6307\u6a19\u7d50\u679c</td></tr>'}</tbody></table></div>`;
      }).join('');
      const ruleJson = escapeHtml(JSON.stringify(run.definition_snapshot, null, 2));
      detail.innerHTML = `<div class="d-flex justify-content-between align-items-start gap-3"><div><h3 class="h5 mb-1">分析紀錄 #${escapeHtml(run.id)}</h3><div class="small text-secondary">${formatTime(run.created_at)} ・診斷年度 ${escapeHtml(run.year_start)}–${escapeHtml(run.year_end)} ・${escapeHtml(run.definition_version_name)}</div></div><button type="button" class="btn-close" data-close-analysis-detail aria-label="關閉內容"></button></div>
        ${reportSections || '<p class="mt-3">此紀錄沒有彙總結果。</p>'}
        <details class="mt-3"><summary>查看本次完整規則快照</summary><pre class="border rounded bg-light p-3 mt-2" style="max-height:360px;overflow:auto;white-space:pre-wrap;">${ruleJson}</pre></details>`;
    } catch (error) {
      detail.innerHTML = `<div class="alert alert-danger mb-0">${escapeHtml(error.message || '讀取分析內容失敗。')}</div>`;
    }
  };

  loadButton.addEventListener('click', () => void loadRuns());
  modal.addEventListener('show.bs.modal', () => void loadRuns());
  modal.addEventListener('click', event => {
    const openButton = event.target.closest('[data-open-analysis-run]');
    if (openButton) void showRun(openButton.dataset.openAnalysisRun);
    if (event.target.closest('[data-close-analysis-detail]')) detail.classList.add('d-none');
  });
})();
