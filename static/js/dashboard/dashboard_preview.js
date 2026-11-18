(() => {
  const source = document.getElementById('dashboardPreviewData');
  if (!source) return;

  window.dashboardPreviewMode = true;
  const { task: initialTask, payload } = JSON.parse(source.textContent || '{}');
  const rawChartData = payload.chart_data || {};
  const legacyKey = (payload.cancer_display_keys || [])[0] || '';
  const reportEntries = Array.isArray(rawChartData.reports) && rawChartData.reports.length
    ? rawChartData.reports
    : [{ key: legacyKey, title: payload.cancer_title || '癌症', data: rawChartData }];
  const firstItem = payload.items?.[0] || {};
  const savedYearStart = String(firstItem.year_start || '');
  const savedYearEnd = String(firstItem.year_end || '');
  const yearTitle = payload.year_title
    || (savedYearStart && savedYearEnd && savedYearStart !== savedYearEnd ? `${savedYearStart}-${savedYearEnd}` : savedYearStart || savedYearEnd || 'XXXX');
  const taskId = initialTask.TaskID || initialTask.taskId;
  const cancerNameMap = window.dashboardCancerNameTranslations || {};
  let activeReport = reportEntries[0];
  let chartData = activeReport.data || {};
  let selected = [];
  let activePreviewItem = null;
  let currentTask = initialTask;
  let renderer = null;

  window.dashboardPreviewYearTitle = yearTitle;
  window.dashboardSelectedCancerDisplayKeys = payload.cancer_display_keys || [];
  window.dashboardPreviewTask = initialTask;
  window.dashboardReportEntries = reportEntries;

  const reportTitle = (report, language = window.DashboardI18n?.getLanguage() || 'zh-TW') => {
    if (language === 'en') return report.title_en || cancerNameMap[report.key]?.en || report.title || 'Cancer';
    return report.title || cancerNameMap[report.key]?.zh || '癌症';
  };
  const paneFor = (fieldKey) => {
    if (fieldKey.includes('Stage Distribution') || /期別分布|期別分佈/.test(fieldKey)) return '#chartPane-StageSummary';
    if (fieldKey.startsWith('期別與首次療程')) return '#chartPane-TreatmentFirstCourse';
    if (fieldKey.startsWith('期別與手術術式')) return '#chartPane-TreatmentSurgery';
    return ({
      '性別與年齡分佈': '#chartPane-IncidenceAge',
      '年齡中位數': '#chartPane-IncidenceMedian',
      '癌症登記可分析個案與確診個案': '#chartPane-DiagnosisAnalyzable',
      '組織型態分佈': '#chartPane-DiagnosisHistology',
      '個案分類': '#chartPane-DiagnosisClassification'
    })[fieldKey] || null;
  };
  const responseFor = (fieldKey) => {
    if (fieldKey.includes('Stage Distribution') || /期別分布|期別分佈/.test(fieldKey)) return 'llmResponseStageSummary';
    if (fieldKey.startsWith('期別與首次療程')) return 'llmResponseTreatmentFirstCourse';
    if (fieldKey.startsWith('期別與手術術式')) return 'llmResponseTreatmentSurgery';
    return ({
      '性別與年齡分佈': 'llmResponseMain',
      '年齡中位數': 'llmResponseMedian',
      '癌症登記可分析個案與確診個案': 'llmResponseAnalyzable',
      '組織型態分佈': 'llmResponseHistology',
      '個案分類': 'llmResponseDiagnosisClassification'
    })[fieldKey] || null;
  };
  const stageSystemFromFieldKey = (fieldKey) => {
    const label = String(fieldKey || '');
    const stageMatch = label.match(/^(.*?) Stage Distribution(?: by Sex| by Age Group)?$/);
    if (stageMatch?.[1]) return stageMatch[1].trim();
    const treatmentMatch = label.match(/^期別與首次療程[（(](.+?)期別[）)]$/);
    return treatmentMatch?.[1]?.trim() || '';
  };
  const isPreviewItemApplicable = (item) => {
    const pane = paneFor(item?.field_key);
    if (!['#chartPane-StageSummary', '#chartPane-TreatmentFirstCourse'].includes(pane)) return true;
    const report = pane === '#chartPane-StageSummary'
      ? (chartData.stageReports || []).find(entry => stageFieldKey(entry) === item.field_key)
        || { staging_system: stageSystemFromFieldKey(item.field_key) }
      : { staging_system: stageSystemFromFieldKey(item.field_key) };
    return !report.staging_system
      || window.DashboardRenderer?.isStageReportApplicableToActiveCancer?.(report) !== false;
  };
  const activeItems = () => (payload.items || [])
    .filter(item => !item.report_key || item.report_key === activeReport.key)
    .map(item => ({ ...item, pane: paneFor(item.field_key), response: responseFor(item.field_key) }))
    .filter(item => item.pane && isPreviewItemApplicable(item));
  const resultByItemId = (task) => new Map((task?.result || []).map(row => [row.custom_id, row.result]));
  const insightFor = (item, language) => resultByItemId(currentTask).get(item?.item_id)?.insights?.[language] || '';
  const taskReadyForExport = (task) => {
    if ((task?.Status || task?.status) !== 'completed' || !payload.items?.length) return false;
    const results = resultByItemId(task);
    return payload.items.every((item) => {
      const result = results.get(item.item_id);
      return result?.success && ['zh-TW', 'en'].every(language =>
        typeof result.insights?.[language] === 'string' && result.insights[language].trim()
      );
    });
  };
  window.isAnnualPreviewExportReady = taskReadyForExport;
  const stageFieldKey = (report) => {
    const view = report?.view || 'stage';
    return `${report?.staging_system || ''} Stage Distribution${view === 'sex' ? ' by Sex' : view === 'age' ? ' by Age Group' : ''}`;
  };

  const renderCancerTabs = () => {
    const area = document.getElementById('cancerReportTabsArea');
    const container = document.getElementById('cancerReportTabs');
    if (!area || !container) return;
    container.replaceChildren();
    if (reportEntries.length < 2) {
      area.classList.add('d-none');
      return;
    }
    reportEntries.forEach((report) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'btn btn-outline-dark btn-sm';
      button.textContent = reportTitle(report);
      button.dataset.reportKey = report.key || '';
      button.classList.toggle('active', report === activeReport);
      button.addEventListener('click', () => renderReport(report.key));
      container.appendChild(button);
    });
    area.classList.remove('d-none');
  };
  const activatePreviewItem = (item) => {
    activePreviewItem = item;
    if (item.response === 'llmResponseTreatmentFirstCourse') {
      const system = window.stageFirstCourseActiveSystem;
      const fieldKey = system ? `期別與首次療程（${system}期別）` : item.field_key;
      activePreviewItem = selected.find(entry => entry.field_key === fieldKey) || item;
    }
    if (item.response === 'llmResponseTreatmentSurgery') {
      const tables = chartData.stageSurgeryData || [];
      const index = tables.findIndex((table, i) => window.AnnualReportRenderer.surgeryTableKey(table, i) === window.stageSurgeryActiveTableKey);
      if (index >= 0) {
        const fieldKey = window.AnnualReportRenderer.surgeryInsightKey(tables[index], index);
        activePreviewItem = selected.find(entry => entry.field_key === fieldKey) || item;
      }
    }
    const pane = document.querySelector(item.pane);
    document.querySelectorAll('.chart-pane').forEach(entry => entry.classList.add('d-none'));
    pane?.classList.remove('d-none');
    if (item.response === 'llmResponseStageSummary') {
      const report = (chartData.stageReports || []).find(entry => stageFieldKey(entry) === item.field_key);
      if (report) {
        const sections = {
          stage: document.getElementById('annualStageDistributionSection'),
          sex: document.getElementById('annualStageSexSection'),
          age: document.getElementById('annualStageAgeSection')
        };
        Object.values(sections).forEach(section => section?.classList.add('d-none'));
        sections[report.view || 'stage']?.classList.remove('d-none');
        const cancer = renderer?.getSelectedCancerTitle?.() || reportTitle(activeReport);
        if (report.view === 'sex') renderer?.renderStageSexReport?.(report, yearTitle, cancer);
        else if (report.view === 'age') renderer?.renderStageAgeReport?.(report, yearTitle, cancer);
        else renderer?.renderStageDistributionReport?.(report, yearTitle, cancer);
      }
    }
    pane?.querySelectorAll('div').forEach(element => echarts.getInstanceByDom(element)?.resize());
    applyNarratives(currentTask);
  };
  const primaryTabs = () => [
    { pane: '#chartPane-IncidenceAge', label: '性別年齡分佈' },
    { pane: '#chartPane-IncidenceMedian', label: '年齡中位數' },
    { pane: '#chartPane-DiagnosisAnalyzable', label: '可分析個案與確診個案' },
    { pane: '#chartPane-DiagnosisHistology', label: '組織型態' },
    { pane: '#chartPane-DiagnosisClassification', label: '個案分類' },
    {
      pane: '#chartPane-StageSummary',
      label: (chartData.stageReports || []).some(report => report.detailed) ? '分期呈現最細碼' : '分期不呈現最細碼'
    },
    { pane: '#chartPane-TreatmentFirstCourse', label: '期別與首次療程' },
    { pane: '#chartPane-TreatmentSurgery', label: '期別與手術術式' },
    { pane: '#chartPane-CrossYearSurvival', label: '存活率' }
  ];
  const renderTabs = () => {
    const area = document.getElementById('chartTabsArea');
    const container = document.getElementById('chartTabsContainer');
    if (!area || !container) return;
    document.querySelectorAll('.chart-pane').forEach(pane => pane.classList.add('d-none'));
    container.replaceChildren();
    const tabs = primaryTabs()
      .map(tab => ({ ...tab, item: selected.find(item => item.pane === tab.pane) }))
      .filter(tab => tab.item);
    tabs.forEach((tab, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'btn btn-outline-primary chart-tab-btn';
      button.dataset.target = tab.pane;
      button.dataset.labelZh = tab.label;
      button.textContent = window.AnnualReportRenderer?.resultTabLabel(tab.label, window.DashboardI18n?.getLanguage()) || tab.label;
      button.addEventListener('click', () => {
        container.querySelectorAll('.chart-tab-btn').forEach(entry => entry.classList.remove('active'));
        button.classList.add('active');
        activatePreviewItem(tab.item);
      });
      container.appendChild(button);
      if (index === 0) button.click();
    });
    area.classList.remove('d-none');
  };
  const buttonFor = (response) => ({
    llmResponseMain: 'btnAiMain',
    llmResponseMedian: 'btnAiMedian',
    llmResponseAnalyzable: 'btnAiAnalyzable',
    llmResponseHistology: 'btnAiHistology',
    llmResponseDiagnosisClassification: 'btnAiDiagnosisClassification',
    llmResponseStageSummary: 'btnAiStageSummary',
    llmResponseTreatmentFirstCourse: 'btnAiTreatmentFirstCourse',
    llmResponseTreatmentSurgery: 'btnAiTreatmentSurgery'
  })[response];
  const bindRegenerateButtons = (task) => {
    const canRegenerate = ['completed', 'partial_failed', 'failed'].includes(task.Status || task.status);
    const item = activePreviewItem || selected[0];
    const button = item && document.getElementById(buttonFor(item.response));
    if (!button) return;
    button.style.display = 'block';
    button.dataset.insightFieldKey = item.field_key;
    button.disabled = !canRegenerate || !item.item_id;
    if (button.disabled) {
      button.onclick = null;
      return;
    }
    button.onclick = async () => {
      button.disabled = true;
      const response = await fetch(`/api/llm-tasks/${encodeURIComponent(taskId)}/regenerate/${encodeURIComponent(item.item_id)}`, { method: 'POST' });
      const data = await response.json();
      if (data.success) {
        applyNarratives(data.task);
        refreshNarratives();
      } else {
        button.disabled = false;
      }
    };
  };
  const applyNarratives = (task) => {
    currentTask = task || initialTask;
    window.dashboardPreviewTask = currentTask;
    const status = currentTask.Status || currentTask.status;
    const statusText = ({ queued: '處理中', running: '處理中', retrying: '處理中', completed: '已完成', partial_failed: '部分完成', failed: '處理失敗', cancelled: '已取消' })[status] || status;
    document.querySelector('.page-head .lead').textContent = `${currentTask.DocumentLabel || '年報分析'}｜${statusText}｜中英敘述 ${currentTask.ProgressCurrent || 0}/${currentTask.ProgressTotal || 0}`;
    const exportButton = document.getElementById('btnPrepareExport');
    if (exportButton) {
      exportButton.disabled = !taskReadyForExport(currentTask);
      exportButton.title = exportButton.disabled ? '所有癌別與表格的中英文敘述完成後才能匯出。' : '';
    }
    const language = window.DashboardI18n?.getLanguage() || 'zh-TW';
    window.dashboardPreviewNarratives = Object.fromEntries(selected.map(item => [item.field_key, insightFor(item, language)]));
    selected.forEach((item) => {
      const insight = insightFor(item, language);
      if (insight) window.DashboardRenderer?.insightCache?.set(`${language}|${item.mode_ai || 'balanced'}|${item.field_key}`, insight);
    });
    const responseItems = new Map();
    selected.forEach((item) => {
      if (!responseItems.has(item.response) || item.field_key === activePreviewItem?.field_key) responseItems.set(item.response, item);
    });
    if (activePreviewItem?.response) responseItems.set(activePreviewItem.response, activePreviewItem);
    responseItems.forEach((item, responseId) => {
      const target = document.getElementById(responseId);
      if (!target) return;
      const insight = insightFor(item, language);
      target.textContent = insight || (!item.item_id
        ? '此表格沒有對應的敘述，請重新建立年報分析任務。'
        : ['failed', 'partial_failed', 'completed'].includes(status) ? '此圖表敘述未能完成。' : '正在處理中…');
    });
    bindRegenerateButtons(currentTask);
  };
  window.updateAnnualPreviewTask = applyNarratives;
  window.rerenderDashboardPreviewNarrative = () => renderReport(activeReport.key, { preservePane: true });
  window.showDashboardPreviewNarrative = (fieldKey) => {
    const item = selected.find(entry => entry.field_key === fieldKey);
    const pane = paneFor(fieldKey);
    if (document.querySelector('.chart-tab-btn.active')?.dataset.target === (item?.pane || pane)) {
      activePreviewItem = item || { field_key: fieldKey, pane, response: responseFor(fieldKey) };
      applyNarratives(currentTask);
    }
  };
  const refreshNarratives = async () => {
    try {
      const response = await fetch(`/api/llm-tasks/${encodeURIComponent(taskId)}`);
      const data = await response.json();
      applyNarratives(data.task);
      const status = data.task.Status || data.task.status;
      if (['queued', 'running', 'retrying'].includes(status)) setTimeout(refreshNarratives, 3000);
    } catch (_) {
      setTimeout(refreshNarratives, 3000);
    }
  };
  const renderReport = (reportKey) => {
    const nextReport = reportEntries.find(entry => entry.key === reportKey) || reportEntries[0];
    if (!nextReport || !renderer) return Promise.resolve();
    activeReport = nextReport;
    chartData = activeReport.data || {};
    window.dashboardActiveCancerKey = activeReport.key || '';
    window.dashboardActiveCancerTitle = reportTitle(activeReport);
    window.dashboardPreviewCancerTitle = reportTitle(activeReport);
    window.lastChartData = chartData;
    selected = activeItems();
    activePreviewItem = selected[0] || null;
    const cancer = renderer.getSelectedCancerTitle();
    renderer.renderSexAgeTable?.(chartData.genderAgeData, yearTitle, cancer);
    renderer.renderAgeMedianTable?.(chartData.ageMedianData, yearTitle, cancer);
    renderer.renderAnalyzableConfirmedTable?.(chartData.analyzableConfirmedData, yearTitle, cancer);
    renderer.renderHistologyTable?.(chartData.histologyData, yearTitle, cancer, chartData.histologyNoDataReason);
    renderer.renderColonHistologyTableNote?.(chartData.histologyWarnings || []);
    renderer.renderDiagnosisClassificationTable?.(chartData.diagnosisClassificationData, yearTitle, cancer);
    renderer.renderDiagnosisClassificationChart?.(chartData.diagnosisClassificationData, yearTitle, cancer);
    renderer.renderStageReportTabs?.(chartData.stageReports || [], yearTitle, cancer);
    renderer.renderStageFirstCourseTables?.(chartData.stageFirstCourseData || [], yearTitle, cancer);
    renderer.renderStageSurgeryTables?.(chartData.stageSurgeryData || [], yearTitle, cancer);
    renderer.updateHistologyChart?.(chartData.histologyData, chartData.histologyNoDataReason);
    renderer.updateChartCaptions?.(yearTitle, cancer);
    document.querySelectorAll('button[id^="btnAi"]').forEach(button => { button.style.display = 'none'; button.onclick = null; });
    window.dashboardChartInstance?.setOption(renderer.getGenderAgeChartOption(chartData.genderAgeData || {}), true);
    document.querySelectorAll('.annual-data-content').forEach(content => content.classList.remove('d-none'));
    renderCancerTabs();
    renderTabs();
    applyNarratives(currentTask);
    return new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  };
  window.dashboardSetActiveReport = (reportKey) => renderReport(reportKey);
  const render = () => {
    renderer = window.DashboardRenderer;
    if (!renderer || !window.dashboardChartInstance) return setTimeout(render, 50);
    document.querySelector('.page-head h1').textContent = initialTask.DocumentLabel || '年報分析';
    document.getElementById('btnBackToQuery')?.addEventListener('click', () => {
      sessionStorage.setItem('dashboard_refresh_after_preview', '1');
      if (window.history.length > 1) window.history.back();
      else window.location.assign('/dashboard');
    });
    renderReport(activeReport.key).then(() => {
      refreshNarratives();
      if (new URLSearchParams(window.location.search).get('export') === '1') document.getElementById('btnPrepareExport')?.click();
    });
  };
  document.addEventListener('DOMContentLoaded', render);
})();
