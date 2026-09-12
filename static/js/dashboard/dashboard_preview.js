(() => {
  const source = document.getElementById('dashboardPreviewData');
  if (!source) return;
  window.dashboardPreviewMode = true;
  const { task: initialTask, payload } = JSON.parse(source.textContent || '{}');
  const chartData = payload.chart_data || {};
  const taskId = initialTask.TaskID || initialTask.taskId;
  const paneFor = (fieldKey) => {
    if (fieldKey.includes('Stage Distribution') || /期別分布|期別分佈/.test(fieldKey)) return '#chartPane-StageSummary';
    if (fieldKey.startsWith('期別與首次療程')) return '#chartPane-TreatmentFirstCourse';
    if (fieldKey.startsWith('期別與手術術式')) return '#chartPane-TreatmentSurgery';
    return ({ '性別與年齡分佈': '#chartPane-IncidenceAge', '年齡中位數': '#chartPane-IncidenceMedian', '癌症登記可分析個案與確診個案': '#chartPane-DiagnosisAnalyzable', '組織型態分佈': '#chartPane-DiagnosisHistology', '個案分類': '#chartPane-DiagnosisClassification' })[fieldKey] || null;
  };
  const responseFor = (fieldKey) => {
    if (fieldKey.includes('Stage Distribution') || /期別分布|期別分佈/.test(fieldKey)) return 'llmResponseStageSummary';
    if (fieldKey.startsWith('期別與首次療程')) return 'llmResponseTreatmentFirstCourse';
    if (fieldKey.startsWith('期別與手術術式')) return 'llmResponseTreatmentSurgery';
    return ({ '性別與年齡分佈': 'llmResponseMain', '年齡中位數': 'llmResponseMedian', '癌症登記可分析個案與確診個案': 'llmResponseAnalyzable', '組織型態分佈': 'llmResponseHistology', '個案分類': 'llmResponseDiagnosisClassification' })[fieldKey] || null;
  };
  const selected = (payload.items || []).map((item) => ({ ...item, pane: paneFor(item.field_key), response: responseFor(item.field_key) })).filter((item) => item.pane);
  const applyNarratives = (currentTask) => {
    const results = Object.fromEntries((currentTask.result || []).map((row) => [row.field_key, row.result?.insights || {}]));
    window.dashboardPreviewNarratives = Object.fromEntries(Object.entries(results).map(([fieldKey, insights]) => [fieldKey, insights['zh-TW'] || insights.en || '']));
    Object.entries(results).forEach(([fieldKey, insights]) => {
      const item = (payload.items || []).find((entry) => entry.field_key === fieldKey) || {};
      Object.entries(insights).forEach(([language, insight]) => window.DashboardRenderer?.insightCache?.set(`${language}|${item.mode_ai || 'balanced'}|${fieldKey}`, insight));
    });
    selected.forEach((item) => {
      const target = document.getElementById(item.response);
      if (!target) return;
      target.textContent = results[item.field_key]?.['zh-TW'] || (['failed', 'partial_failed', 'completed'].includes(currentTask.Status || currentTask.status) ? '此圖表敘述未能完成。' : '正在處理中…');
    });
    bindRegenerateButtons(currentTask);
  };
  const refreshNarratives = async () => {
    try {
      const response = await fetch(`/api/llm-tasks/${encodeURIComponent(taskId)}`);
      const data = await response.json();
      applyNarratives(data.task);
      const status = data.task.Status || data.task.status;
      const statusText = ['queued', 'running', 'retrying'].includes(status) ? '處理中' : status;
      document.querySelector('.page-head .lead').textContent = `${data.task.DocumentLabel || '年報分析'}｜${statusText}｜${data.task.ProgressCurrent || 0}/${data.task.ProgressTotal || 0}`;
      if (['queued', 'running', 'retrying'].includes(status)) setTimeout(refreshNarratives, 3000);
    } catch (_) { setTimeout(refreshNarratives, 3000); }
  };
  const displayTitle = (fieldKey) => {
    const stage = String(fieldKey || '').match(/^(.+?) Stage Distribution(?: by (Sex|Age Group))?$/);
    if (!stage) return fieldKey;
    if (stage[2] === 'Sex') return stage[1] + ' 性別及期別分布表';
    if (stage[2] === 'Age Group') return stage[1] + ' 年齡層及期別分布表';
    return stage[1] + ' 期別分布表';
  };  const renderTabs = () => {
    const area = document.getElementById('chartTabsArea'); const container = document.getElementById('chartTabsContainer');
    if (!area || !container) return;
    const panes = [...new Set(selected.map((item) => item.pane))];
    document.querySelectorAll('.chart-pane').forEach((pane) => pane.classList.add('d-none'));
    container.replaceChildren();
    panes.forEach((paneSelector, index) => {
      const item = selected.find((entry) => entry.pane === paneSelector);
      const button = document.createElement('button'); button.type = 'button'; button.className = 'btn btn-outline-primary chart-tab-btn'; button.dataset.target = paneSelector; button.textContent = displayTitle(item.field_key);
      button.addEventListener('click', () => {
        container.querySelectorAll('.chart-tab-btn').forEach((entry) => entry.classList.remove('active'));
        button.classList.add('active'); document.querySelectorAll('.chart-pane').forEach((pane) => pane.classList.add('d-none'));
        const pane = document.querySelector(paneSelector); pane?.classList.remove('d-none');
        pane?.querySelectorAll('div').forEach((element) => echarts.getInstanceByDom(element)?.resize());
      });
      container.appendChild(button); if (index === 0) button.click();
    });
    area.classList.remove('d-none');
  };
  const buttonFor = (response) => ({ llmResponseMain: 'btnAiMain', llmResponseMedian: 'btnAiMedian', llmResponseAnalyzable: 'btnAiAnalyzable', llmResponseHistology: 'btnAiHistology', llmResponseDiagnosisClassification: 'btnAiDiagnosisClassification', llmResponseStageSummary: 'btnAiStageSummary', llmResponseTreatmentFirstCourse: 'btnAiTreatmentFirstCourse', llmResponseTreatmentSurgery: 'btnAiTreatmentSurgery' })[response];
  const bindRegenerateButtons = (task) => {
    const canRegenerate = ['completed', 'partial_failed', 'failed'].includes(task.Status || task.status);
    selected.forEach((item) => {
      const button = document.getElementById(buttonFor(item.response));
      if (!button) return;
      button.style.display = 'block';
      button.disabled = !canRegenerate;
      if (!canRegenerate) return;
      button.onclick = async () => {
        button.disabled = true;
        const response = await fetch('/api/llm-tasks/' + encodeURIComponent(taskId) + '/regenerate/' + encodeURIComponent(item.item_id), { method: 'POST' });
        const data = await response.json();
        if (data.success) { applyNarratives(data.task); refreshNarratives(); }
        else button.disabled = false;
      };
    });
  };  const render = () => {
    const renderer = window.DashboardRenderer;
    if (!renderer || !window.dashboardChartInstance) return setTimeout(render, 50);
    const year = payload.items?.[0]?.year_start || 'XXXX'; const cancer = '癌症'; window.lastChartData = chartData;
    renderer.renderSexAgeTable?.(chartData.genderAgeData, year, cancer); renderer.renderAgeMedianTable?.(chartData.ageMedianData, year, cancer);
    renderer.renderAnalyzableConfirmedTable?.(chartData.analyzableConfirmedData, year, cancer); renderer.renderHistologyTable?.(chartData.histologyData, year, cancer, chartData.histologyNoDataReason);
    renderer.renderDiagnosisClassificationTable?.(chartData.diagnosisClassificationData, year, cancer); renderer.renderDiagnosisClassificationChart?.(chartData.diagnosisClassificationData, year, cancer);
    renderer.renderStageReportTabs?.(chartData.stageReports || [], year, cancer); renderer.updateHistologyChart?.(chartData.histologyData, chartData.histologyNoDataReason);
    document.querySelectorAll('button[id^="btnAi"]').forEach((button) => { button.style.display = 'none'; button.onclick = null; });
    window.dashboardChartInstance.setOption(renderer.getGenderAgeChartOption(chartData.genderAgeData || {}), true);
    document.querySelectorAll('.annual-data-content').forEach((content) => content.classList.remove('d-none'));
    document.querySelector('.page-head h1').textContent = initialTask.DocumentLabel || '年報分析'; document.querySelector('.page-head .lead').textContent = '年報任務預覽｜' + initialTask.ProgressCurrent + '/' + initialTask.ProgressTotal;
    document.getElementById('btnBackToQuery')?.addEventListener('click', () => {
      sessionStorage.setItem('dashboard_refresh_after_preview', '1');
      if (window.history.length > 1) window.history.back(); else window.location.assign('/dashboard');
    });
    renderTabs(); applyNarratives(initialTask); refreshNarratives();
    if (new URLSearchParams(window.location.search).get('export') === '1') document.getElementById('btnPrepareExport')?.click();
  };
  document.addEventListener('DOMContentLoaded', render);
})();