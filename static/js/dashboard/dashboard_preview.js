(() => {
  const source = document.getElementById('dashboardPreviewData');
  if (!source) return;
  window.dashboardPreviewMode = true;
  const { task: initialTask, payload } = JSON.parse(source.textContent || '{}');
  const chartData = payload.chart_data || {};
  const firstItem = payload.items?.[0] || {};
  const savedYearStart = String(firstItem.year_start || '');
  const savedYearEnd = String(firstItem.year_end || '');
  const yearTitle = payload.year_title
    || (savedYearStart && savedYearEnd && savedYearStart !== savedYearEnd ? `${savedYearStart}-${savedYearEnd}` : savedYearStart || savedYearEnd || 'XXXX');
  const cancerTitle = payload.cancer_title || '癌症';
  window.dashboardPreviewYearTitle = yearTitle;
  window.dashboardPreviewCancerTitle = cancerTitle;
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
  let activePreviewItem = selected[0] || null;
  let currentTask = initialTask;
  let renderer = null;
  const stageFieldKey = (report) => {
    const view = report?.view || 'stage';
    return `${report?.staging_system || ''} Stage Distribution${view === 'sex' ? ' by Sex' : view === 'age' ? ' by Age Group' : ''}`;
  };
  const activatePreviewItem = (item) => {
    activePreviewItem = item;
    const pane = document.querySelector(item.pane);
    document.querySelectorAll('.chart-pane').forEach((entry) => entry.classList.add('d-none'));
    pane?.classList.remove('d-none');
    if (item.response === 'llmResponseStageSummary') {
      const report = (chartData.stageReports || []).find((entry) => stageFieldKey(entry) === item.field_key);
      if (report) {
        const sections = {
          stage: document.getElementById('annualStageDistributionSection'),
          sex: document.getElementById('annualStageSexSection'),
          age: document.getElementById('annualStageAgeSection')
        };
        Object.values(sections).forEach((section) => section?.classList.add('d-none'));
        sections[report.view || 'stage']?.classList.remove('d-none');
        if (report.view === 'sex') renderer?.renderStageSexReport?.(report, yearTitle, cancerTitle);
        else if (report.view === 'age') renderer?.renderStageAgeReport?.(report, yearTitle, cancerTitle);
        else renderer?.renderStageDistributionReport?.(report, yearTitle, cancerTitle);
      }
    }
    pane?.querySelectorAll('div').forEach((element) => echarts.getInstanceByDom(element)?.resize());
    applyNarratives(currentTask);
  };
  const applyNarratives = (task) => {
    currentTask = task || initialTask;
    const results = Object.fromEntries((currentTask.result || []).map((row) => [row.field_key, row.result?.insights || {}]));
    window.dashboardPreviewNarratives = Object.fromEntries(Object.entries(results).map(([fieldKey, insights]) => [fieldKey, insights['zh-TW'] || insights.en || '']));
    Object.entries(results).forEach(([fieldKey, insights]) => {
      const item = (payload.items || []).find((entry) => entry.field_key === fieldKey) || {};
      Object.entries(insights).forEach(([language, insight]) => window.DashboardRenderer?.insightCache?.set(`${language}|${item.mode_ai || 'balanced'}|${fieldKey}`, insight));
    });
    const item = activePreviewItem || selected[0];
    const target = item && document.getElementById(item.response);
    if (target) target.textContent = results[item.field_key]?.['zh-TW'] || (['failed', 'partial_failed', 'completed'].includes(currentTask.Status || currentTask.status) ? '此圖表敘述未能完成。' : '正在處理中…');
    bindRegenerateButtons(currentTask);
  };
  window.showDashboardPreviewNarrative = (fieldKey) => {
    const item = selected.find((entry) => entry.field_key === fieldKey);
    if (item) activePreviewItem = item;
    applyNarratives(currentTask);
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
  const primaryTabs = [
    { pane: '#chartPane-IncidenceAge', label: '性別年齡分佈' },
    { pane: '#chartPane-IncidenceMedian', label: '年齡中位數' },
    { pane: '#chartPane-DiagnosisAnalyzable', label: '可分析個案與確診個案' },
    { pane: '#chartPane-DiagnosisHistology', label: '組織型態' },
    { pane: '#chartPane-DiagnosisClassification', label: '個案分類' },
    {
      pane: '#chartPane-StageSummary',
      label: (chartData.stageReports || []).some((report) => report.detailed)
        ? '分期呈現最細碼' : '分期不呈現最細碼'
    },
    { pane: '#chartPane-TreatmentFirstCourse', label: '期別與首次療程' },
    { pane: '#chartPane-TreatmentSurgery', label: '期別與手術術式' },
    { pane: '#chartPane-CrossYearSurvival', label: '存活率' }
  ];
  const renderTabs = () => {
    const area = document.getElementById('chartTabsArea'); const container = document.getElementById('chartTabsContainer');
    if (!area || !container) return;
    document.querySelectorAll('.chart-pane').forEach((pane) => pane.classList.add('d-none'));
    container.replaceChildren();
    const tabs = primaryTabs
      .map((tab) => ({ ...tab, item: selected.find((item) => item.pane === tab.pane) }))
      .filter((tab) => tab.item);
    tabs.forEach((tab, index) => {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'btn btn-outline-primary chart-tab-btn'; button.dataset.target = tab.pane; button.textContent = tab.label;
      button.addEventListener('click', () => {
        container.querySelectorAll('.chart-tab-btn').forEach((entry) => entry.classList.remove('active'));
        button.classList.add('active');
        activatePreviewItem(tab.item);
      });
      container.appendChild(button); if (index === 0) button.click();
    });
    area.classList.remove('d-none');
  };
  const buttonFor = (response) => ({ llmResponseMain: 'btnAiMain', llmResponseMedian: 'btnAiMedian', llmResponseAnalyzable: 'btnAiAnalyzable', llmResponseHistology: 'btnAiHistology', llmResponseDiagnosisClassification: 'btnAiDiagnosisClassification', llmResponseStageSummary: 'btnAiStageSummary', llmResponseTreatmentFirstCourse: 'btnAiTreatmentFirstCourse', llmResponseTreatmentSurgery: 'btnAiTreatmentSurgery' })[response];
  const bindRegenerateButtons = (task) => {
    const canRegenerate = ['completed', 'partial_failed', 'failed'].includes(task.Status || task.status);
    const item = activePreviewItem || selected[0];
    const button = item && document.getElementById(buttonFor(item.response));
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
  };  const render = () => {
    renderer = window.DashboardRenderer;
    if (!renderer || !window.dashboardChartInstance) return setTimeout(render, 50);
    const year = yearTitle; const cancer = cancerTitle; window.lastChartData = chartData;
    renderer.renderSexAgeTable?.(chartData.genderAgeData, year, cancer); renderer.renderAgeMedianTable?.(chartData.ageMedianData, year, cancer);
    renderer.renderAnalyzableConfirmedTable?.(chartData.analyzableConfirmedData, year, cancer); renderer.renderHistologyTable?.(chartData.histologyData, year, cancer, chartData.histologyNoDataReason);
    renderer.renderDiagnosisClassificationTable?.(chartData.diagnosisClassificationData, year, cancer); renderer.renderDiagnosisClassificationChart?.(chartData.diagnosisClassificationData, year, cancer);
    renderer.renderStageReportTabs?.(chartData.stageReports || [], year, cancer); renderer.renderStageFirstCourseTables?.(chartData.stageFirstCourseData || [], year, cancer);
    renderer.renderStageSurgeryTables?.(chartData.stageSurgeryData || [], year, cancer); renderer.updateHistologyChart?.(chartData.histologyData, chartData.histologyNoDataReason);
    renderer.updateChartCaptions?.(year, cancer);
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
