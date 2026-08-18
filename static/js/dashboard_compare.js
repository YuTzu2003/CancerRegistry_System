(function() {
  window.AnnualReportRenderer?.applyConditionCatalog(document, 'comparison');

  const mainFile = document.getElementById('mainCompareFile');
  const targetFile = document.getElementById('targetCompareFile');
  const mainYear = document.getElementById('mainCompareYear');
  const targetYear = document.getElementById('targetCompareYear');
  const mainYearEnd = document.getElementById('mainCompareYearEnd');
  const targetYearEnd = document.getElementById('targetCompareYearEnd');
  const mainPreview = document.getElementById('mainComparePreview');
  const targetPreview = document.getElementById('targetComparePreview');
  const mainMeta = document.getElementById('mainCompareMeta');
  const targetMeta = document.getElementById('targetCompareMeta');
  const behavior = document.getElementById('compareBehavior');
  const modeAi = document.getElementById('compareModeAi');
  const runButton = document.getElementById('btnRunCompare');
  const resetButton = document.getElementById('btnResetCompare');
  const resultBox = document.getElementById('compareResult');
  const resultStale = document.getElementById('compareResultStale');
  let mainYears = [];
  let targetYears = [];
  let hasRenderedResult = false;
  let lastComparisonData = null;
  let activeAiNarrativeItem = '';
  let aiNarrativeRequestId = 0;
  let activeResultIndex = 0;
  const aiNarrativeCache = new Map();
  const aiNarrativeTimeoutMs = 180000;
  const viewPreferences = { main: 'chart', target: 'chart' };
  const customYearControls = new Map();
  const yearSelects = [mainYear, mainYearEnd, targetYear, targetYearEnd];
  let activeTreatmentStageSystem = '';
  const stageResultGroupItem = '__stage_reports__';
  let activeStageReportOption = '';

  function t(key, options) {
    return window.DashboardI18n?.t(key, options) || key;
  }

  function isEnglish() {
    return window.DashboardI18n?.getLanguage() === 'en';
  }

  function sourceLine() {
    return `<br><span class="text-muted fw-normal" style="font-size: 0.85em;">${t('source')}</span>`;
  }

  function selectedCancerEnglishTitle() {
    const translations = window.dashboardCancerNameTranslations || {};
    const values = selectedCancerValues();
    const names = values.map(value => translations[value]?.en).filter(Boolean);
    const fallback = selectedCancerTitle();
    return names.length ? names.join(', ') : (translations[fallback]?.en || fallback || 'Cancer');
  }

  function englishCancerPatientLabel() {
    const cancer = selectedCancerEnglishTitle();
    return /cancer|carcinoma|lymphoma|leukemia/i.test(cancer) ? cancer : `${cancer} Cancer`;
  }

  function reportCancerTitle(cancerTitle) {
    return isEnglish() ? englishCancerPatientLabel() : getCancerTitleForSentence(cancerTitle);
  }

  function closeCustomYearMenus(exceptSelect = null) {
    customYearControls.forEach((control, select) => {
      if (select === exceptSelect) return;
      control.wrapper.classList.remove('is-open');
      control.menu.hidden = true;
      control.button.setAttribute('aria-expanded', 'false');
    });
  }

  function syncCustomYearSelect(select) {
    const control = customYearControls.get(select);
    if (!control) return;
    const selectedOption = select.options[select.selectedIndex];
    control.button.textContent = selectedOption?.textContent?.trim() || '尚未選擇';
    control.button.disabled = select.disabled;
    control.menu.replaceChildren();
    Array.from(select.options).forEach(option => {
      const item = document.createElement('button');
      item.type = 'button';
      item.className = 'custom-year-select-option';
      item.textContent = option.textContent;
      item.disabled = option.disabled;
      item.classList.toggle('is-selected', option.value === select.value);
      item.setAttribute('role', 'option');
      item.setAttribute('aria-selected', option.value === select.value ? 'true' : 'false');
      item.addEventListener('click', () => {
        select.value = option.value;
        syncCustomYearSelect(select);
        closeCustomYearMenus();
        select.dispatchEvent(new Event('change', { bubbles: true }));
        control.button.focus();
      });
      control.menu.appendChild(item);
    });
    if (select.disabled) closeCustomYearMenus();
  }

  function enhanceYearSelect(select) {
    select.classList.add('year-native-select');
    const wrapper = document.createElement('div');
    wrapper.className = 'custom-year-select';
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'custom-year-select-button';
    button.setAttribute('aria-haspopup', 'listbox');
    button.setAttribute('aria-expanded', 'false');
    const menu = document.createElement('div');
    menu.className = 'custom-year-select-menu';
    menu.setAttribute('role', 'listbox');
    menu.hidden = true;
    wrapper.append(button, menu);
    select.insertAdjacentElement('afterend', wrapper);
    customYearControls.set(select, { wrapper, button, menu });

    button.addEventListener('click', event => {
      event.stopPropagation();
      if (button.disabled) return;
      const willOpen = menu.hidden;
      closeCustomYearMenus(select);
      wrapper.classList.toggle('is-open', willOpen);
      menu.hidden = !willOpen;
      button.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
      if (willOpen) menu.querySelector('.is-selected:not(:disabled), .custom-year-select-option:not(:disabled)')?.focus();
    });
    wrapper.addEventListener('keydown', event => {
      if (event.key === 'Escape') {
        closeCustomYearMenus();
        button.focus();
      }
    });
    select.addEventListener('change', () => syncCustomYearSelect(select));
    new MutationObserver(() => syncCustomYearSelect(select)).observe(select, {
      attributes: true,
      childList: true,
      subtree: true
    });
    syncCustomYearSelect(select);
  }

  yearSelects.forEach(enhanceYearSelect);
  document.addEventListener('click', () => closeCustomYearMenus());

  function selectedCompareMode() {
    return document.querySelector('input[name="compareMode"]:checked')?.value || 'single';
  }

  function selectedCompareType() {
    return document.querySelector('input[name="compareType"]:checked')?.value || '';
  }

  function selectedCompareItemsForGroups(groups) {
    return groups.flatMap(group => Array.from(document.querySelectorAll(
      `[data-compare-subitems="${group}"] .compare-subitem-check:checked:not(:disabled):not(.compare-stage-system-checkbox)`
    )).map(input => input.value));
  }

  function selectedCompareItems() {
    const selectedStageItems = Array.from(
      document.querySelectorAll('.compare-stage-option:checked:not(:disabled)')
    ).map(input => input.value);
    return [...new Set([
      ...selectedCompareItemsForGroups(['incidence', 'diagnosis']),
      ...selectedStageItems,
      ...selectedCompareItemsForGroups(['treatment', 'cross_year'])
    ])];
  }

  function selectedStageReportOptions() {
    return selectedCompareStageOptions().options.map(item => item.option);
  }

  function comparisonResultItems() {
    const stageOptions = new Set(selectedStageReportOptions());
    let stageGroupAdded = false;
    return selectedCompareItems().reduce((items, item) => {
      if (!stageOptions.has(item)) return [...items, item];
      if (stageGroupAdded) return items;
      stageGroupAdded = true;
      return [...items, stageResultGroupItem];
    }, []);
  }

  function activeComparisonItem(item) {
    return item === stageResultGroupItem ? activeStageReportOption : item;
  }

  function comparisonItemTitle(item) {
    return item === stageResultGroupItem ? (isEnglish() ? 'Stage' : '期別') : item;
  }

  function selectedCompareStageOptions() {
    const detailed = document.getElementById('compareItemStageDetailed')?.checked === true;
    const summary = document.getElementById('compareItemStageSummary')?.checked === true;
    const options = Array.from(document.querySelectorAll('.compare-stage-option:checked:not(:disabled)'))
      .map(input => ({
        system: input.closest('[data-stage-system]')?.dataset.stageSystem || '',
        option: input.value,
        detailed
      }))
      .filter(item => item.system && item.option);
    return {
      mode: detailed ? 'detailed' : summary ? 'summary' : '',
      detailed,
      options
    };
  }

  function treatmentStageOptions() {
    const selected = new Set(selectedCancerValues());
    const allSelected = selected.has('All_Cancers');
    const applicable = {
      AJCC: () => selected.size > 0,
      FIGO: () => ['Cervix_Uteri', 'Corpus_Uteri', 'Ovary'].some(value => selected.has(value)),
      BCLC: () => selected.has('Liver'),
      MAC: () => ['Colon', 'Rectum'].some(value => selected.has(value)),
      SCLC: () => ['Lung_and_Bronchus', 'Small_cell_carcinoma', 'Adenocarcinoma', 'Squamous_cell_carcinoma'].some(value => selected.has(value)),
      DSS: () => selected.has('Plasma_cell_neoplasms'),
      DRE: () => selected.has('Prostate'),
      'Breast Cancer Prognostic Stage': () => ['Breast_Female', 'Breast_Male'].some(value => selected.has(value)),
      Binet: () => selected.has('CLL')
    };
    return Object.keys(applicable)
      .filter(system => allSelected || applicable[system]())
      .map(system => ({ system, option: `${system}期別`, detailed: false }));
  }

  function markResultsStale() {
    if (hasRenderedResult) resultStale.classList.remove('d-none');
  }

  function selectedCancerValues() {
    return Array.from(window.selectedCancers || []);
  }

  function updateCompareStageOptions() {
    const detailed = document.getElementById('compareItemStageDetailed');
    const summary = document.getElementById('compareItemStageSummary');
    const panel = document.getElementById('compareStageOptions');
    if (!detailed || !summary || !panel) return;

    const cancerReady = selectedCancerValues().length > 0;
    if (detailed.checked) {
      summary.checked = false;
      summary.disabled = true;
      detailed.disabled = !cancerReady;
    } else if (summary.checked) {
      detailed.checked = false;
      detailed.disabled = true;
      summary.disabled = !cancerReady;
    } else {
      detailed.disabled = !cancerReady;
      summary.disabled = !cancerReady;
    }

    const enabled = cancerReady && (detailed.checked || summary.checked);
    const selectedCancers = new Set(selectedCancerValues());
    const applicable = {
      AJCC: () => selectedCancers.size > 0,
      FIGO: () => ['Cervix_Uteri', 'Corpus_Uteri', 'Ovary'].some(value => selectedCancers.has(value)),
      BCLC: () => selectedCancers.has('Liver'),
      MAC: () => ['Colon', 'Rectum'].some(value => selectedCancers.has(value)),
      SCLC: () => ['Lung_and_Bronchus', 'Small_cell_carcinoma', 'Adenocarcinoma', 'Squamous_cell_carcinoma']
        .some(value => selectedCancers.has(value)),
      DSS: () => selectedCancers.has('Plasma_cell_neoplasms'),
      DRE: () => selectedCancers.has('Prostate'),
      'Breast Cancer Prognostic Stage': () => ['Breast_Female', 'Breast_Male']
        .some(value => selectedCancers.has(value)),
      Binet: () => selectedCancers.has('CLL')
    };
    const allSelected = selectedCancers.has('All_Cancers');

    panel.classList.toggle('is-open', enabled);
    panel.querySelectorAll('.compare-stage-option-card').forEach(card => {
      const isApplicable = allSelected || applicable[card.dataset.stageSystem]?.() === true;
      const disabled = !enabled || !isApplicable;
      card.classList.toggle('is-disabled', disabled);
      card.querySelectorAll('.compare-stage-option').forEach(input => {
        input.disabled = disabled;
        if (disabled) input.checked = false;
      });
    });
  }

  function filesReady() {
    const hasBothFilesAndYears = fileSelectionsComplete();
    const mainEnd = selectedCompareMode() === 'range' ? mainYearEnd.value : mainYear.value;
    const targetEnd = selectedCompareMode() === 'range' ? targetYearEnd.value : targetYear.value;
    const validRanges = Number(mainYear.value) <= Number(mainEnd) && Number(targetYear.value) <= Number(targetEnd);
    const isSameFileSamePeriod = mainFile.value === targetFile.value
      && mainYear.value === targetYear.value && mainEnd === targetEnd;
    return hasBothFilesAndYears && validRanges && !isSameFileSamePeriod;
  }

  function fileSelectionsComplete() {
    const rangeComplete = selectedCompareMode() !== 'range' || (mainYearEnd.value && targetYearEnd.value);
    return Boolean(mainFile.value && targetFile.value && mainYear.value && targetYear.value && rangeComplete);
  }

  function updateCompareTreatmentSelection(isAvailable) {
    const hasStageAnalysis = Boolean(document.querySelector('.compare-stage-option:checked:not(:disabled)'));
    const enabled = Boolean(isAvailable && hasStageAnalysis);
    document.querySelectorAll('[data-compare-subitems="treatment"] .compare-subitem-check').forEach(input => {
      input.disabled = !enabled;
      if (!enabled) input.checked = false;
    });
    document.getElementById('compareTreatmentStageRequired')?.classList.toggle('d-none', enabled);
  }

  function setSettingsEnabled() {
    const filesAreReady = filesReady();
    const behaviorIsReady = filesAreReady && Boolean(behavior.value);
    const cancerIsReady = behaviorIsReady && selectedCancerValues().length > 0;
    const behaviorStep = document.getElementById('compareBehaviorStep');
    const cancerStep = document.getElementById('compareCancerStep');
    const analysisStep = document.getElementById('compareAnalysisStep');

    behavior.disabled = !filesAreReady;
    behaviorStep?.classList.toggle('opacity-50', !filesAreReady);
    behaviorStep?.classList.toggle('pe-none', !filesAreReady);
    const cancerPicker = document.getElementById('btnCancerPicker');
    if (cancerPicker) cancerPicker.disabled = !behaviorIsReady;
    cancerStep?.classList.toggle('opacity-50', !behaviorIsReady);
    cancerStep?.classList.toggle('pe-none', !behaviorIsReady);
    document.querySelectorAll('input[name="compareType"], .compare-subitem-check').forEach(input => {
      input.disabled = !cancerIsReady;
    });
    document.getElementById('btnSelectAllCompareItems').disabled = !cancerIsReady;
    document.getElementById('btnClearCompareItems').disabled = !cancerIsReady;
    analysisStep?.classList.toggle('opacity-50', !cancerIsReady);
    analysisStep?.classList.toggle('pe-none', !cancerIsReady);

    return { filesAreReady, behaviorIsReady, cancerIsReady };
  }

  function updateButtonState() {
    const state = setSettingsEnabled();
    updateCompareStageOptions();
    updateCompareTreatmentSelection(state.cancerIsReady);
    runButton.disabled = !(state.cancerIsReady && selectedCompareItems().length > 0);
    updateTopicCounts();
    updateSelectionSummary();
  }

  function updateSelectionSummary() {
    const sameFile = Boolean(mainFile.value) && mainFile.value === targetFile.value;
    const formatDataSelection = (fileSelect, yearSelect, yearEndSelect, includeFileName) => {
      if (!fileSelect.value && !yearSelect.value) return '尚未選擇';
      const fileText = fileSelect.selectedOptions[0]?.textContent?.trim() || '尚未選擇檔案';
      const yearTextValue = yearSelect.value || '尚未選擇年度';
      const period = selectedCompareMode() === 'range' && yearEndSelect.value
        ? `${yearTextValue}–${yearEndSelect.value}` : yearTextValue;
      return includeFileName ? `${fileText}｜${period}` : period;
    };
    const behaviorText = behavior.value ? behavior.selectedOptions[0]?.textContent?.trim() : '尚未選擇';
    const selectedCancerTitle = String(window.dashboardSelectedCancerTitle || '').trim();
    const cancerText = selectedCancerValues().length
      ? (selectedCancerTitle && selectedCancerTitle !== 'XX' ? selectedCancerTitle : `${selectedCancerValues().length} 個癌別`)
      : '尚未選擇';
    const stageOptions = selectedCompareStageOptions();
    const stageMode = stageOptions.detailed ? '分期呈現最細碼' : '分期不呈現最細碼';
    const stageSummary = stageOptions.options.length
      ? `期別（${stageMode}（${stageOptions.options.map(item => item.option).join('、')}））`
      : '';
    const summaryItems = [
      ...selectedCompareItemsForGroups(['incidence', 'diagnosis']),
      ...(stageSummary ? [stageSummary] : []),
      ...selectedCompareItemsForGroups(['treatment', 'cross_year'])
    ];

    document.getElementById('summaryCompareMode').textContent = selectedCompareMode() === 'range' ? '年度區間比較' : '單一年度比較';
    document.getElementById('summaryMainData').textContent = formatDataSelection(mainFile, mainYear, mainYearEnd, !sameFile);
    document.getElementById('summaryTargetData').textContent = formatDataSelection(targetFile, targetYear, targetYearEnd, !sameFile);
    document.getElementById('summaryBehavior').textContent = behaviorText || '尚未選擇';
    document.getElementById('summaryCancer').textContent = cancerText;
    document.getElementById('summaryModeAi').textContent = modeAi.selectedOptions[0]?.textContent?.trim() || '平穩客觀';
    document.getElementById('summaryItems').textContent = summaryItems.length ? summaryItems.join('、') : '尚未選擇';
  }

  function updateTopicCounts() {
    document.querySelectorAll('.cat-count-badge[data-parent-group]').forEach(badge => {
      const group = document.querySelector(`[data-compare-subitems="${badge.dataset.parentGroup}"]`);
      const count = badge.dataset.parentGroup === 'stage'
        ? selectedCompareStageOptions().options.length
        : (group?.querySelectorAll('.compare-subitem-check:checked').length || 0);
      badge.textContent = String(count);
      badge.classList.toggle('d-none', count === 0);
    });
  }

  function renderCompareSubItems() {
    const activeType = selectedCompareType();
    document.querySelectorAll('[data-compare-subitems]').forEach(group => {
      const isActive = group.dataset.compareSubitems === activeType;
      group.classList.toggle('d-none', !isActive);
    });
  }

  function yearText(years) {
    if (!years || years.length === 0) return '無法偵測';
    return years.length === 1 ? String(years[0]) : `${years[0]} - ${years[years.length - 1]}`;
  }

  function fillYearSelect(selectEl, years) {
    selectEl.innerHTML = '';
    if (!years || years.length === 0) {
      selectEl.appendChild(new Option('無法偵測', '', true, true));
      selectEl.disabled = true;
      return;
    }

    selectEl.appendChild(new Option('請選擇年度', '', true, true));
    years.forEach(year => {
      selectEl.appendChild(new Option(String(year), String(year)));
    });
    if (years.length === 1) {
      selectEl.value = String(years[0]);
    }
    selectEl.disabled = false;
  }

  function showPreviewMessage(previewEl, message) {
    previewEl.innerHTML = `<div class="compare-preview-empty">${message}</div>`;
  }

  function renderPreview(previewEl, preview) {
    const columns = preview?.columns || [];
    const rows = preview?.rows || [];
    if (!columns.length) {
      showPreviewMessage(previewEl, '沒有可預覽的資料');
      return;
    }

    const table = document.createElement('table');
    table.className = 'table table-sm table-bordered align-middle';
    table.innerHTML = `
      <thead><tr>${columns.map(column => `<th>${column}</th>`).join('')}</tr></thead>
      <tbody>${rows.map(row => `<tr>${columns.map((_, index) => `<td>${row[index] ?? ''}</td>`).join('')}</tr>`).join('')}</tbody>
    `;
    previewEl.innerHTML = '';
    previewEl.appendChild(table);
  }

  function refreshYearPreview(fileEl, yearEl, yearEndEl, previewEl) {
    const isRange = selectedCompareMode() === 'range';
    const yearStart = yearEl.value;
    const yearEnd = isRange ? yearEndEl.value : yearStart;
    const metaEl = fileEl === mainFile ? mainMeta : targetMeta;
    const years = fileEl === mainFile ? mainYears : targetYears;
    const toggleEl = document.querySelector(`[data-preview-target="${previewEl.id}"]`);

    if (!fileEl.value || !yearStart || !yearEnd) {
      showPreviewMessage(previewEl, isRange ? '請先選擇完整年度區間' : '請先選擇年度');
      metaEl.textContent = `年度 ${yearText(years)}｜等待選擇預覽年度`;
      toggleEl?.classList.add('d-none');
      return Promise.resolve();
    }

    showPreviewMessage(previewEl, '年度資料預覽載入中...');
    return fetch('/api/dashboard/file_years', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        file_id: fileEl.value,
        year_start: yearStart,
        year_end: yearEnd
      })
    })
      .then(r => r.json())
      .then(data => {
        if (!data.ok) throw new Error(data.error || '資料預覽載入失敗');
        renderPreview(previewEl, data.preview);
        const period = yearStart === yearEnd ? `${yearStart} 年` : `${yearStart}-${yearEnd} 年`;
        metaEl.textContent = `年度 ${yearText(data.years || years)}｜預覽 ${period}資料前 ${data.preview?.rows?.length || 0} 筆`;
        toggleEl?.classList.remove('d-none');
      })
      .catch(err => {
        showPreviewMessage(previewEl, err.message);
        metaEl.textContent = '年度預覽讀取失敗';
        toggleEl?.classList.remove('d-none');
      });
  }

  function detectYears(selectEl, inputEl, previewEl) {
    const endInput = selectEl === mainFile ? mainYearEnd : targetYearEnd;
    inputEl.innerHTML = '<option value="" selected>偵測中...</option>';
    inputEl.disabled = true;
    endInput.innerHTML = '<option value="" selected>偵測中...</option>';
    endInput.disabled = true;
    updateButtonState();
    showPreviewMessage(previewEl, '資料預覽載入中...');
    const metaEl = selectEl === mainFile ? mainMeta : targetMeta;
    const toggleEl = document.querySelector(`[data-preview-target="${previewEl.id}"]`);
    metaEl.textContent = '讀取中…';
    toggleEl?.classList.add('d-none');
    markResultsStale();
    if (selectEl === mainFile) mainYears = [];
    if (selectEl === targetFile) targetYears = [];

    fetch('/api/dashboard/file_years', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_id: selectEl.value })
    })
      .then(r => r.json())
      .then(data => {
        if (!data.ok) throw new Error(data.error || '年度偵測失敗');
        if (selectEl === mainFile) mainYears = data.years || [];
        if (selectEl === targetFile) targetYears = data.years || [];
        fillYearSelect(inputEl, data.years || []);
        fillYearSelect(endInput, data.years || []);
        if (inputEl.value) {
          refreshYearPreview(selectEl, inputEl, endInput, previewEl);
        } else {
          showPreviewMessage(previewEl, '請先選擇年度');
          metaEl.textContent = `年度 ${yearText(data.years || [])}｜等待選擇預覽年度`;
          toggleEl?.classList.add('d-none');
        }
      })
      .catch(err => {
        if (selectEl === mainFile) mainYears = [];
        if (selectEl === targetFile) targetYears = [];
        inputEl.innerHTML = '<option value="" selected>偵測失敗</option>';
        inputEl.disabled = true;
        endInput.innerHTML = '<option value="" selected>偵測失敗</option>';
        endInput.disabled = true;
        showPreviewMessage(previewEl, err.message);
        metaEl.textContent = '讀取失敗';
      })
      .finally(updateButtonState);
  }

  function getCancerTitleForSentence(cancerTitle) {
    if (!cancerTitle || cancerTitle === 'XX') return 'XX癌';
    if (cancerTitle.includes('癌') || cancerTitle.includes('全癌別')) return cancerTitle;
    return `${cancerTitle}癌`;
  }

  function selectedCancerTitle() {
    return window.dashboardSelectedCancerTitle && window.dashboardSelectedCancerTitle !== 'XX'
      ? window.dashboardSelectedCancerTitle
      : 'XX';
  }

  function sum(values) {
    return window.AnnualReportRenderer.sum(values);
  }

  function axisLabelLines(value, maxLength = 68) {
    return window.AnnualReportRenderer.axisLabelLines(value, maxLength);
    const lines = [];
    const segments = String(value ?? '')
      .trim()
      .replace(/\s*(?=[\[［])/g, '\n')
      .split('\n')
      .filter(Boolean);
    segments.forEach(segment => {
      let line = '';
      const segmentMaxLength = /^[\[［]/.test(segment) ? 88 : 82;
      segment.split(/\s+/).filter(Boolean).forEach(word => {
        const candidate = line ? `${line} ${word}` : word;
        if (line && candidate.length > segmentMaxLength) {
          lines.push(line);
          line = word;
        } else {
          line = candidate;
        }
      });
      if (line) lines.push(line);
    });
    return lines.length ? lines : [''];
  }

  function rightAlignedAxisLabel(value, maxLength = 68) {
    return window.AnnualReportRenderer.rightAlignedAxisLabel(value, maxLength);
    return axisLabelLines(value, maxLength)
      .map(text => `{${/^[\[［]/.test(text) ? 'bracket' : 'right'}|${text}}`)
      .join('\n');
  }

  function histologyRowHeight(names) {
    return window.AnnualReportRenderer.histologyRowHeight(names);
    const maxLines = Math.max(1, ...names.map(name => axisLabelLines(name).length));
    return Math.max(40, maxLines * 18 + 8);
  }

  function normalizeGenderAgeData(genderAgeData) {
    return window.AnnualReportRenderer.normalizeGenderAgeData(genderAgeData);
    const labels = ['≦19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49', '50-54', '55-59', '60-64', '65-69', '70-74', '75-79', '80-84', '≧85'];
    const categories = genderAgeData?.categories?.length ? genderAgeData.categories : labels;
    const fillValues = values => {
      const source = Array.isArray(values) ? values : [];
      return categories.map((_, index) => Number(source[index] || 0));
    };

    return {
      categories,
      male: fillValues(genderAgeData?.male),
      female: fillValues(genderAgeData?.female),
      total: fillValues(genderAgeData?.total)
    };
  }

  function getGenderAgeChartOption(genderAgeData, sharedMax = null) {
    const data = normalizeGenderAgeData(genderAgeData);
    const maxValue = Math.max(0, ...data.male, ...data.female, ...data.total);
    const yMax = sharedMax || Math.max(10, Math.ceil((maxValue * 1.15) / 5) * 5);

    return {
      title: {
        text: '性別與年齡分佈',
        subtext: '資料來源：癌症登記資料庫',
        left: 'center',
        top: 0,
        textStyle: { fontSize: 18, fontWeight: 'bold' }
      },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 72, right: 72, top: 70, bottom: 78, containLabel: false },
      legend: { data: ['男性', '女性', '總計'], bottom: 28, itemGap: 12 },
      toolbox: {
        right: 16,
        top: 0,
        feature: {
          dataView: { show: true, readOnly: false, title: '數據檢視', lang: ['數據檢視', '關閉', '更新'] },
          saveAsImage: { show: true, title: '下載圖片' }
        }
      },
      xAxis: [{
        type: 'category',
        data: data.categories,
        axisPointer: { type: 'shadow' },
        axisTick: { alignWithLabel: true },
        axisLabel: { interval: 0 }
      }],
      yAxis: [{
        type: 'value',
        name: '個案數',
        min: 0,
        max: yMax,
        minInterval: 1,
        splitNumber: 5,
        splitLine: { lineStyle: { color: '#e5eaf3' } }
      }],
      series: [
        { name: '男性', type: 'bar', data: data.male, barWidth: 20, barGap: '20%', barCategoryGap: '42%', itemStyle: { color: '#5470C6' } },
        { name: '女性', type: 'bar', data: data.female, barWidth: 20, itemStyle: { color: '#EE6666' } },
        { name: '總計', type: 'bar', data: data.total, barWidth: 20, z: 5, itemStyle: { color: '#91CC75' } }
      ]
    };
  }

  function sexAgeBlock(chartData, yearTitle, cancerTitle, chartId) {
    const genderAgeData = normalizeGenderAgeData(chartData?.genderAgeData || {});
    const ageLabels = genderAgeData.categories;
    const male = genderAgeData.male || [];
    const female = genderAgeData.female || [];
    const total = genderAgeData.total || [];
    return `
      ${viewSwitchBlock()}
      <div data-compare-view-panel="chart">
        <div id="${chartId}" class="compare-chart"></div>
        <div class="compare-chart-caption">圖、${yearTitle}年新診斷${getCancerTitleForSentence(cancerTitle)}病患性別及年齡分佈圖</div>
      </div>
      <div data-compare-view-panel="table" class="d-none">
        <div class="annual-report-table-wrap">
          <table class="annual-report-table">
            <caption>表、${yearTitle}年新診斷${getCancerTitleForSentence(cancerTitle)}病患性別及年齡分佈表<br><span class="text-muted fw-normal" style="font-size: 0.85em;">資料來源：癌症登記資料庫</span></caption>
            <thead>
              <tr><th rowspan="2">性別</th><th colspan="${ageLabels.length}">年齡層次</th><th rowspan="2">總計</th></tr>
              <tr>${ageLabels.map(label => `<th>${label}</th>`).join('')}</tr>
            </thead>
            <tbody>
              <tr><td>男</td>${male.map(value => `<td>${value}</td>`).join('')}<td>${sum(male)}</td></tr>
              <tr><td>女</td>${female.map(value => `<td>${value}</td>`).join('')}<td>${sum(female)}</td></tr>
              <tr><td>總計</td>${total.map(value => `<td>${value}</td>`).join('')}<td>${sum(total)}</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  function getUpdatedGenderAgeChartOption(genderAgeData, sharedMax = null, yearTitle = '', cancerTitle = '') {
    return window.AnnualReportRenderer.getGenderAgeChartOption(genderAgeData, {
      sharedMax,
      title: isEnglish()
        ? `Age and Sex Distribution of Newly Diagnosed with ${reportCancerTitle(cancerTitle)} Patients, ${yearTitle}`
        : (yearTitle ? `${yearTitle}年新診斷${reportCancerTitle(cancerTitle)}病患性別及年齡分布圖` : '性別及年齡分布圖'),
      source: t('source'),
      labels: {
        male: t('male'),
        female: t('female'),
        total: t('total'),
        age: t('age'),
        dataView: t('dataView'),
        close: t('close'),
        refresh: t('refresh'),
        downloadImage: t('downloadImage')
      }
    });
    const raw = normalizeGenderAgeData(genderAgeData);
    const data = {
      ...raw,
      categories: raw.categories.map(label => ['<=19', '≤19', '≦19'].includes(label) ? '≦19' : ['>=85', '≥85', '≧85'].includes(label) ? '≧85' : label)
    };
    const maxValue = Math.max(0, ...data.male, ...data.female, ...data.total);
    const yMax = sharedMax || Math.max(10, Math.ceil((maxValue * 1.15) / 5) * 5);
    const cancer = reportCancerTitle(cancerTitle);
    const title = isEnglish()
      ? `Age and Sex Distribution of Newly Diagnosed with ${cancer} Patients, ${yearTitle}`
      : (yearTitle ? `${yearTitle}年新診斷${cancer}病患性別及年齡分佈圖` : '性別及年齡分佈圖');
    const legendLabels = [t('male'), t('female'), t('total')];

    return {
      title: { text: title, subtext: t('source'), left: 'center', top: 0, textStyle: { fontSize: 18, fontWeight: 'bold' }, subtextStyle: { fontSize: 12 } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 72, right: 72, top: 98, bottom: 74, containLabel: false },
      legend: { data: legendLabels, top: 52, left: 'center', itemGap: 12 },
      toolbox: { right: 16, top: 0, feature: { dataView: { show: true, readOnly: false, title: t('dataView'), lang: [t('dataView'), t('close'), t('refresh')] }, saveAsImage: { show: true, title: t('downloadImage') } } },
      xAxis: [{ type: 'category', data: data.categories, name: t('age'), nameLocation: 'middle', nameGap: 30, axisPointer: { type: 'shadow' }, axisTick: { alignWithLabel: true }, axisLabel: { interval: 0 } }],
      yAxis: [{ type: 'value', min: 0, max: yMax, minInterval: 1, splitNumber: 5, splitLine: { lineStyle: { color: '#e5eaf3' } } }],
      series: [
        { name: legendLabels[0], type: 'bar', data: data.male, barWidth: 20, barGap: '20%', barCategoryGap: '42%', itemStyle: { color: '#5470C6' } },
        { name: legendLabels[1], type: 'bar', data: data.female, barWidth: 20, itemStyle: { color: '#EE6666' } },
        { name: legendLabels[2], type: 'bar', data: data.total, barWidth: 20, z: 5, itemStyle: { color: '#91CC75' } }
      ]
    };
  }

  function sexAgeBlockV2(chartData, yearTitle, cancerTitle, chartId) {
    const genderAgeData = normalizeGenderAgeData(chartData?.genderAgeData || {});
    const ageLabels = genderAgeData.categories.map(label => ['<=19', '≤19', '≦19'].includes(label) ? '≦19' : ['>=85', '≥85', '≧85'].includes(label) ? '≧85' : label);
    const male = genderAgeData.male || [];
    const female = genderAgeData.female || [];
    const total = genderAgeData.total || [];
    const totalCount = sum(total);
    const percentage = value => totalCount ? `${(Number(value || 0) / totalCount * 100).toFixed(1)}%` : '0.0%';
    const cancer = reportCancerTitle(cancerTitle);
    return `
      ${viewSwitchBlock()}
      <div data-compare-view-panel="chart">
        <div id="${chartId}" class="compare-chart"></div>
        <div class="compare-chart-caption">${isEnglish() ? `Figure : Age and Sex Distribution of Newly Diagnosed with ${cancer} Patients, ${yearTitle}` : `圖、${yearTitle}年新診斷${cancer}病患性別及年齡分佈圖`}</div>
      </div>
      <div data-compare-view-panel="table" class="d-none">
        <div class="annual-report-table-wrap">
          <table class="annual-report-table">
            <caption>${isEnglish() ? `Table . Age and Sex Distribution of Newly Diagnosed with ${cancer} Patients,\u00a0${yearTitle}` : `表、${yearTitle}年新診斷${cancer}病患性別及年齡分佈表`}${sourceLine()}</caption>
            <thead>
              <tr><th rowspan="2">${t('sex')}</th><th colspan="${ageLabels.length}">${t('ageGroup')}</th><th rowspan="2">${t('subtotal')}</th><th rowspan="2">${t('percent')}</th></tr>
              <tr>${ageLabels.map(label => `<th>${label}</th>`).join('')}</tr>
            </thead>
            <tbody>
              <tr><td>${t('male')}</td>${male.map(value => `<td>${value}</td>`).join('')}<td>${sum(male)}</td><td>${percentage(sum(male))}</td></tr>
              <tr><td>${t('female')}</td>${female.map(value => `<td>${value}</td>`).join('')}<td>${sum(female)}</td><td>${percentage(sum(female))}</td></tr>
              <tr><td>${t('total')}</td>${total.map(value => `<td>${value}</td>`).join('')}<td>${totalCount}</td><td>${percentage(totalCount)}</td></tr>
              <tr><td>%</td>${total.map(value => `<td>${percentage(value)}</td>`).join('')}<td>${percentage(totalCount)}</td><td>-</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  function viewSwitchBlock() {
    return `
      <div class="compare-view-switch" role="group" aria-label="結果顯示方式">
        <button type="button" class="compare-view-button active" data-compare-view="chart"><i class="bi bi-bar-chart me-1"></i>${t('chart')}</button>
        <button type="button" class="compare-view-button" data-compare-view="table"><i class="bi bi-table me-1"></i>${t('table')}</button>
      </div>
    `;
  }

  function ageMedianBlock(chartData, yearTitle, cancerTitle) {
    const item = chartData?.ageMedianData || {};
    const cancer = reportCancerTitle(cancerTitle);
    return `
      <div class="annual-report-table-wrap compare-compact-table">
        <table class="annual-report-table">
          <caption>${isEnglish() ? `Table . Median Age of Patients Newly Diagnosed with ${cancer},\u00a0${yearTitle}` : `表、${yearTitle}年新診斷${cancer}病患年齡中位數表`}${sourceLine()}</caption>
          <thead><tr><th rowspan="2">${t('medianCharacteristic')}</th><th colspan="2">${t('medianSex')}</th></tr><tr><th>${t('male')}</th><th>${t('female')}</th></tr></thead>
          <tbody>
            <tr><td>${t('medianN')}</td><td>${item.male_count || 0}</td><td>${item.female_count || 0}</td></tr>
            <tr><td>${t('medianAgeYears')}</td><td>${item.male || 0}</td><td>${item.female || 0}</td></tr>
            <tr><td>${t('medianMaleToFemaleRatio')}</td><td>${item.male_ratio || '0.00'}</td><td>${item.female_ratio || '0.00'}</td></tr>
          </tbody>
        </table>
      </div>
    `;
  }

  function analyzableBlock(chartData, yearTitle, cancerTitle) {
    const item = chartData?.analyzableConfirmedData || {};
    const cancer = reportCancerTitle(cancerTitle);
    return `
      <div class="annual-report-table-wrap compare-analyzable-table">
        <table class="annual-report-table">
          <caption>${isEnglish() ? `Table . Analysis-Eligible and Confirmed Cases of ${cancer} in the Cancer Registry,\u00a0${yearTitle}` : `表、${yearTitle}年${cancer}-癌症登記可分析個案與確診個案`}${sourceLine()}</caption>
          <thead>
            <tr>
              <th>${isEnglish() ? `${t('cancerTotal')}, ${yearTitle}` : `${yearTitle}年癌症總數`}<br>(A)</th>
              <th>${t('analysisEligibleCases')}<br>(B)</th>
              <th>${t('analysisEligiblePercent')}<br>(B/A)</th>
              <th>${t('microscopicallyConfirmedCases')}<br>(C)</th>
              <th>${t('microscopicallyConfirmedPercent')}<br>(C/B)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>${item.total_count || 0}</td>
              <td>${item.analyzable_count || 0}</td>
              <td>${item.analyzable_percent || '0.0%'}</td>
              <td>${item.confirmed_count || 0}</td>
              <td>${item.confirmed_percent || '0.0%'}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="compare-note">
        <div>${t('analysisEligibleNote')}</div>
        <div class="compare-note-lines">${t('analysisEligibleClass1')}</div>
        <div class="compare-note-lines">${t('analysisEligibleClass2')}</div>
      </div>
    `;
  }

  function escapeHtml(value) {
    return window.AnnualReportRenderer.escapeHtml(value);
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function histologyBlock(chartData, yearTitle, cancerTitle, chartId) {
    const histologyData = Array.isArray(chartData?.histologyData) ? chartData.histologyData : [];
    const warnings = Array.isArray(chartData?.histologyWarnings) ? chartData.histologyWarnings : [];
    const colonNotes = warnings.filter(item => {
      const code = String(item.icdo_code || '');
      const site = String(item.site || '').toUpperCase();
      return code === '8211/2' && site.startsWith('C18');
    });
    const chartNotes = colonNotes.length
      ? `<div class="text-danger small mt-1">${colonNotes.map(item => {
          const user = escapeHtml(item.user || '未知個案');
          return `註：有一筆組織型態不適用，已排除統計（${user} 不符合 M8211 診斷年度規範）`;
        }).join('<br>')}</div>`
      : '';
    const validData = histologyData.filter(item => item.name !== 'Unknown / 未對應組織型態');
    const noDataReason = escapeHtml(chartData?.histologyNoDataReason || '查無符合條件的組織型態資料。');
    const totalCount = validData.reduce((total, item) => total + Number(item.count || 0), 0);
    const rows = validData.length
      ? validData.map(item => {
          const pct = totalCount > 0 ? (Number(item.count || 0) / totalCount * 100).toFixed(1) : '0.0';
          return `
            <tr>
              <td>${escapeHtml(item.code)}</td>
              <td class="text-start">${escapeHtml(item.name)}</td>
              <td>${Number(item.count || 0)}</td>
              <td>${pct}%</td>
            </tr>
          `;
        }).join('') + `
          <tr class="fw-bold" style="background-color: var(--gray-50);">
            <td>${t('total')}</td>
            <td></td>
            <td>${totalCount}</td>
            <td>${validData.length ? '100.0%' : '0.0%'}</td>
          </tr>`
      : `<tr><td colspan="4" class="text-center">${t('noData')}<br><span class="text-muted small">${noDataReason}</span></td></tr>`;

    const cancer = reportCancerTitle(cancerTitle);

    return `
      ${viewSwitchBlock()}
      <div data-compare-view-panel="chart">
        <div id="${chartId}" class="compare-chart" style="height: 450px;"></div>
        <div class="compare-chart-caption">${isEnglish() ? `Figure. Histological Distribution of ${cancer}, ${yearTitle}` : `圖、${yearTitle}年${cancer}組織型態分佈圖`}</div>
        ${chartNotes}
      </div>
      <div data-compare-view-panel="table" class="d-none">
        <div class="annual-report-table-wrap">
          <table class="annual-report-table compare-histology-table">
            <caption>${isEnglish() ? `Table. Histological Distribution of ${cancer},\u00a0${yearTitle}` : `表、${yearTitle}年${cancer}組織型態分佈表`}${sourceLine()}</caption>
            <colgroup>
              <col style="width: 10%;">
              <col style="width: 75%;">
              <col style="width: 7.5%;">
              <col style="width: 7.5%;">
            </colgroup>
            <thead>
              <tr>
                <th>${t('icdoCode')}</th>
                <th>${t('histology')}</th>
                <th>${t('people')}</th>
                <th>${isEnglish() ? '%' : `${t('percentage')}%`}</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </div>
    `;
  }

  function diagnosisClassificationMappings() {
    return [
      {
        title: t('class0'),
        totalKey: 'class0_total',
        subClasses: [
          { key: '0_1_0', label: t('class010') },
          { key: '0_1_2', label: t('class012') }
        ]
      },
      {
        title: t('class1'),
        totalKey: 'class1_total',
        subClasses: [
          { key: '1_1_1', label: t('class111') },
          { key: '1_1_3', label: t('class113') },
          { key: '1_1_4', label: t('class114') }
        ]
      },
      {
        title: t('class2'),
        totalKey: 'class2_total',
        subClasses: [
          { key: '2_2_1', label: t('class221') },
          { key: '2_2_3', label: t('class223') }
        ]
      },
      {
        title: t('class3'),
        totalKey: 'class3_total',
        subClasses: [
          { key: '3_2_0', label: t('class320') },
          { key: '3_3_2', label: t('class332') }
        ]
      }
    ];
  }

  function classificationBlock(chartData, yearTitle, cancerTitle, chartId) {
    const tableData = chartData?.diagnosisClassificationData || {};
    const total = tableData.total_count || 0;
    const calcPct = value => total > 0 ? (Number(value || 0) / total * 100).toFixed(1) + '%' : '0.0%';
    let rows = '';

    diagnosisClassificationMappings().forEach(cls => {
      const clsTotal = Number(tableData[cls.totalKey] || 0);
      rows += `<tr class="table-light" style="border-top: 2px solid #6c757d;"><td style="font-size: 1.1em; font-weight: 900;">${cls.title}</td><td class="text-center fw-bold">${clsTotal}</td><td class="text-center fw-bold">${calcPct(clsTotal)}</td></tr>`;
      cls.subClasses.forEach(sub => {
        const count = Number(tableData[sub.key] || 0);
        rows += `<tr><td class="ps-4">${sub.label}</td><td class="text-end">${count}</td><td class="text-end">${calcPct(count)}</td></tr>`;
      });
    });

    rows += `<tr class="table-secondary fw-bold" style="font-weight: bold; border-top: 2px solid #6c757d;"><td class="text-center">${t('total')}</td><td class="text-center">${total}</td><td class="text-center">${total > 0 ? '100.0%' : '0.0%'}</td></tr>`;

    const cancer = reportCancerTitle(cancerTitle);

    return `
      ${viewSwitchBlock()}
      <div data-compare-view-panel="chart">
        <div id="${chartId}" class="compare-chart" style="height: 450px;"></div>
        <div class="compare-chart-caption">${isEnglish() ? `Figure. ${cancer} Case Class Distribution, ${yearTitle}` : `圖、${yearTitle}年${cancer}個案分類分佈圖`}</div>
      </div>
      <div data-compare-view-panel="table" class="d-none">
        <div class="annual-report-table-wrap mb-4">
          <table class="annual-report-table text-start" style="width: 100%;">
            <caption>${isEnglish() ? `Table . ${cancer} Case Class Distribution,\u00a0${yearTitle}` : `表、${yearTitle}年${cancer}個案分類分佈表`}${sourceLine()}</caption>
            <thead><tr><th class="text-center">${isEnglish() ? 'Class' : '個案分類'}</th><th class="text-center">${t('people')}</th><th class="text-center">${isEnglish() ? '%' : `${t('percentage')}%`}</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </div>
    `;
  }

  function bindViewSwitch(container, side) {
    const buttons = container.querySelectorAll('[data-compare-view]');
    if (!buttons.length) return;

    function applyView(selectedView) {
      viewPreferences[side] = selectedView;
      buttons.forEach(item => item.classList.toggle('active', item.dataset.compareView === selectedView));
      container.querySelectorAll('[data-compare-view-panel]').forEach(panel => {
        panel.classList.toggle('d-none', panel.dataset.compareViewPanel !== selectedView);
      });
      if (selectedView === 'chart' && window.echarts) {
        setTimeout(() => container.querySelectorAll('.compare-chart').forEach(chartEl => {
          echarts.getInstanceByDom(chartEl)?.resize();
        }), 0);
      }
    }

    buttons.forEach(button => {
      button.addEventListener('click', () => applyView(button.dataset.compareView));
    });
    applyView(viewPreferences[side] || 'chart');
  }

  function renderSexAgeChart(chartId, chartData, sharedScale, yearTitle, cancerTitle) {
    if (!window.echarts) return;
    const chartEl = document.getElementById(chartId);
    if (!chartEl) return;
    const oldChart = echarts.getInstanceByDom(chartEl);
    if (oldChart) oldChart.dispose();
    const chart = echarts.init(chartEl);
    chart.setOption(getUpdatedGenderAgeChartOption(chartData?.genderAgeData || {}, sharedScale?.genderAgeMax, yearTitle, cancerTitle));
    setTimeout(() => chart.resize(), 50);
  }

  function renderHistologyChart(chartId, chartData, yearTitle, cancerTitle, sharedScale) {
    if (!window.echarts) return;
    const chartEl = document.getElementById(chartId);
    if (!chartEl) return;
    const oldChart = echarts.getInstanceByDom(chartEl);
    if (oldChart) oldChart.dispose();

    const histologyData = Array.isArray(chartData?.histologyData) ? chartData.histologyData : [];
    const validData = histologyData.filter(item => item.name !== 'Unknown / 未對應組織型態');
    const totalCount = validData.reduce((total, item) => total + Number(item.count || 0), 0);
    // 與年報分析頁一致：由低比例到高比例排列，長清單依項目數自動增高。
    const displayData = [...validData].reverse();
    const names = displayData.map(item => item.name);
    const noDataReason = chartData?.histologyNoDataReason || '查無符合條件的組織型態資料。';
    const values = displayData.map(item => {
      const value = totalCount > 0 ? Number((Number(item.count || 0) / totalCount * 100).toFixed(1)) : 0;
      return { value, count: Number(item.count || 0) };
    });

    chartEl.style.height = `${Math.max(450, names.length * histologyRowHeight(names))}px`;
    const cancer = reportCancerTitle(cancerTitle);
    const chartTitle = isEnglish()
      ? `Histological Distribution of ${cancer}, ${yearTitle}`
      : `${yearTitle}年${cancer}組織型態分佈圖`;

    const chart = echarts.init(chartEl);
    if (!names.length) {
      chartEl.style.height = '450px';
      chart.setOption({
        animation: false,
        title: { text: chartTitle, subtext: t('source'), left: 'center', textStyle: { fontSize: 18, fontWeight: 'bold' } },
        tooltip: { show: false },
        toolbox: { show: false },
        xAxis: { show: false },
        yAxis: { show: false },
        series: [],
        graphic: [{
          type: 'text',
          left: 'center',
          top: 'middle',
          style: {
            text: `${t('noData')}\n${noDataReason}`,
            fill: '#6b7280',
            fontSize: 14,
            fontWeight: 500,
            lineHeight: 24,
            textAlign: 'center'
          }
        }]
      });
      setTimeout(() => chart.resize(), 50);
      return;
    }
    chart.setOption({
      animation: false,
      title: {
        text: chartTitle,
        subtext: t('source'),
        left: 'center',
        textStyle: { fontSize: 18, fontWeight: 'bold' }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: function(params) {
          const p = params[0];
          if (!p || p.value === undefined || p.value === '-') return '';
          const count = p.data && p.data.count !== undefined ? p.data.count : '-';
          const val = typeof p.value === 'number' ? p.value.toFixed(1) : p.value;
          return `${p.name}<br/>${p.marker}${t('caseRatio')}: ${val}% (${isEnglish() ? `N = ${count}` : `${count} 人`})`;
        }
      },
      grid: { left: 500, right: 60, bottom: 50, top: 60, containLabel: false },
      legend: { show: false },
      toolbox: {
        feature: {
          dataView: { show: true, readOnly: false, title: t('dataView'), lang: [t('dataView'), t('close'), t('refresh')] },
          saveAsImage: { show: true, title: t('downloadImage') }
        }
      },
      xAxis: { type: 'value', name: isEnglish() ? '%' : '百分比 (%)', nameLocation: 'middle', nameGap: 30, min: 0, max: sharedScale?.histologyMax, interval: 10, axisLabel: { formatter: value => Number(value).toFixed(1) + '%' } },
      yAxis: {
        type: 'category',
        data: names,
        inverse: true,
        axisLabel: {
          width: 420,
          align: 'right',
          margin: 20,
          formatter: value => rightAlignedAxisLabel(value),
          rich: {
            right: { width: 420, align: 'right', lineHeight: 18, fontSize: 12 },
            bracket: { width: 420, align: 'right', lineHeight: 18, fontSize: 10.5 }
          }
        }
      },
      series: [{
        name: '個案比例',
        type: 'bar',
        data: values,
        itemStyle: { color: '#73c0de' },
        label: {
          show: true,
          position: 'right',
          color: '#333',
          fontSize: 13,
          distance: 8,
          formatter: params => `${Number(params.value || 0).toFixed(1)}% (${isEnglish() ? `N = ${Number(params.data?.count || 0)}` : `${Number(params.data?.count || 0)} 人`})`
        }
      }]
    });
    setTimeout(() => chart.resize(), 50);
  }

  function renderClassificationChart(chartId, chartData, sharedScale, yearTitle, cancerTitle) {
    if (!window.echarts) return;
    const chartEl = document.getElementById(chartId);
    if (!chartEl) return;
    const oldChart = echarts.getInstanceByDom(chartEl);
    if (oldChart) oldChart.dispose();

    const data = chartData?.diagnosisClassificationData || {};
    const total = data.total_count || 1;
    const calcPctNum = value => Number((Number(value || 0) / total * 100).toFixed(1));
    const labels = [t('class0'), t('class1'), t('class2'), t('class3')];
    const colors = ['#5470C6', '#91CC75', '#FAC858', '#EE6666'];
    const chartTitle = isEnglish()
      ? `${reportCancerTitle(cancerTitle)} Case Class Distribution, ${yearTitle}`
      : `${yearTitle}年${reportCancerTitle(cancerTitle)}個案分類分佈圖`;

    const chart = echarts.init(chartEl);
    chart.setOption({
      animation: false,
      toolbox: { show: true, feature: { dataView: { show: true, readOnly: false, title: t('dataView'), lang: [t('dataView'), t('close'), t('refresh')] }, saveAsImage: { show: true, title: t('downloadImage') } } },
      title: { text: chartTitle, subtext: t('source'), left: 'center', textStyle: { fontSize: 18, fontWeight: 'bold', color: '#333' } },
      legend: { orient: 'vertical', right: '2%', top: 'middle', itemWidth: 14, itemHeight: 14, data: labels, textStyle: { fontSize: 14, lineHeight: 22, width: 450, overflow: 'break' } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '3%', right: '32%', top: '15%', bottom: '3%', containLabel: true },
      xAxis: [{ type: 'category', data: ['Class0', 'Class1', 'Class2', 'Class3'], axisTick: { alignWithLabel: true } }],
      yAxis: [{ type: 'value', min: 0, max: sharedScale?.classificationMax, axisLabel: { formatter: '{value}%' } }],
      series: [
        { name: labels[0], type: 'bar', stack: 'total', barWidth: '60%', data: [calcPctNum(data.class0_total), '-', '-', '-'], itemStyle: { borderRadius: [6, 6, 0, 0], color: colors[0] }, label: { show: true, position: 'top', color: '#333', fontSize: 14, fontWeight: 'bold', formatter: '{c}%' } },
        { name: labels[1], type: 'bar', stack: 'total', barWidth: '60%', data: ['-', calcPctNum(data.class1_total), '-', '-'], itemStyle: { borderRadius: [6, 6, 0, 0], color: colors[1] }, label: { show: true, position: 'top', color: '#333', fontSize: 14, fontWeight: 'bold', formatter: '{c}%' } },
        { name: labels[2], type: 'bar', stack: 'total', barWidth: '60%', data: ['-', '-', calcPctNum(data.class2_total), '-'], itemStyle: { borderRadius: [6, 6, 0, 0], color: colors[2] }, label: { show: true, position: 'top', color: '#333', fontSize: 14, fontWeight: 'bold', formatter: '{c}%' } },
        { name: labels[3], type: 'bar', stack: 'total', barWidth: '60%', data: ['-', '-', '-', calcPctNum(data.class3_total)], itemStyle: { borderRadius: [6, 6, 0, 0], color: colors[3] }, label: { show: true, position: 'top', color: '#333', fontSize: 14, fontWeight: 'bold', formatter: '{c}%' } }
      ]
    });
    setTimeout(() => chart.resize(), 50);
  }

  function treatmentLabel(treatment) {
    if (!isEnglish()) return treatment;
    const labels = {
      '手術': 'Surgery', '放療': 'Radiotherapy', '化療': 'Chemotherapy',
      '標靶': 'Targeted Therapy', '荷爾蒙': 'Hormone Therapy',
      '類固醇治療': 'Steroid Therapy', '免疫': 'Immunotherapy',
      '骨髓/幹細胞移植': 'Hematopoietic Stem Cell Transplantation (HSCT)',
      '內分泌處置': 'Endocrine Procedure', '其他治療': 'Other Treatment',
      '密切觀察或不予治療': 'No Treatment', '待確認': 'Pending Confirmation',
      'RFA/TAE/PEI混合治療': 'RFA/TAE/PEI Combined Treatment'
    };
    return String(treatment || '').split('、').map(value => labels[value] || value).join('、');
  }

  function treatmentFirstCourseBlock(chartData, yearTitle, cancerTitle, activeSystem) {
    const tables = Array.isArray(chartData?.stageFirstCourseData) ? chartData.stageFirstCourseData : [];
    const item = tables.find(table => table.system === activeSystem) || tables[0];
    if (!item) return '<div class="alert alert-light border mb-0">目前沒有可呈現的期別與首次療程資料。</div>';
    const stages = item.stage_columns || [];
    const rows = item.rows || [];
    const totalCount = Number(item.total_count || 0);
    const displayStage = stage => String(stage || '').replace(/^Stage\s+/i, '').trim();
    const rowPercentage = row => totalCount ? `${(Number(row.subtotal || 0) / totalCount * 100).toFixed(1)}%` : '0.0%';
    const unknown = Number(item.excluded_unknown || 0);
    const notApplicable = Number(item.excluded_not_applicable || 0);
    const unclassified = Number(item.excluded_unclassified_treatment || 0);
    const excluded = unknown + notApplicable + unclassified;
    const definitionNote = isEnglish()
      ? 'Note: First course treatment refers to all treatments administered before disease progression or recurrence.'
      : '註：首次療程的定義係指在癌病惡化或復發之前所執行的治療方法。';
    const stageNote = isEnglish()
      ? `Note: Of ${Number(item.analyzable_count || 0)} analyzable cases (Class 1–2), ${unknown} had unknown stage and ${notApplicable} had non-applicable stage${unclassified ? `; ${unclassified} case(s) could not be classified using the defined treatment codes` : ''}. A total of ${excluded} case(s) were excluded (percentage denominator = ${Number(item.included_count ?? totalCount)}).`
      : `註：可分析個案數（Class 1–2）共計 ${Number(item.analyzable_count || 0)} 例，其中分期不明 ${unknown} 例、分期不適用 ${notApplicable} 例${unclassified ? `；另有 ${unclassified} 例治療方式無法依既定治療代碼判定` : ''}。上述共 ${excluded} 例未納入期別與首次療程分佈百分比計算（百分比分母＝${Number(item.included_count ?? totalCount)}）。`;
    const caption = isEnglish()
      ? `Table . ${escapeHtml(item.system)} Stage and First Course Treatment Distribution of Newly Diagnosed ${escapeHtml(reportCancerTitle(cancerTitle))} Cases, ${yearTitle}${sourceLine()}`
      : `表、${yearTitle}年新診斷${escapeHtml(reportCancerTitle(cancerTitle))}${escapeHtml(item.system)}期別與首次療程表${sourceLine()}`;
    const bodyRows = rows.map(row => `<tr><td class="text-start ps-3">${escapeHtml(treatmentLabel(row.treatment))}</td>${(row.values || []).map(value => `<td>${value}</td>`).join('')}<td>${row.subtotal}</td><td>${rowPercentage(row)}</td></tr>`).join('');
    const totals = (item.totals || []).map(value => `<td>${value}</td>`).join('');
    const percentages = (item.percentages || []).map(value => `<td>${value}%</td>`).join('');
    return `<div class="annual-report-table-wrap"><table class="annual-report-table"><caption>${caption}</caption><thead><tr><th rowspan="2">${isEnglish() ? 'First Course of Treatment' : '首次療程'}</th><th colspan="${Math.max(stages.length, 1)}">${escapeHtml(item.system)} ${isEnglish() ? 'Stage' : '期別'}</th><th rowspan="2">${isEnglish() ? 'Total' : '小計'}</th><th rowspan="2">%</th></tr><tr>${stages.map(stage => `<th>${escapeHtml(displayStage(stage))}</th>`).join('')}</tr></thead><tbody>${bodyRows}<tr class="fw-bold"><td>${isEnglish() ? 'Total' : '總計'}</td>${totals}<td>${totalCount}</td><td>${totalCount ? '100.0%' : '0.0%'}</td></tr><tr><td>%</td>${percentages}<td>${totalCount ? '100.0%' : '0.0%'}</td><td>-</td></tr></tbody></table><div class="small text-secondary mt-2 mb-0">${definitionNote}</div><div class="small text-secondary mt-0 mb-0">${stageNote}</div></div>`;
  }

  function normalizeStageReport(report) {
    const stageLabels = Array.isArray(report?.stage_labels) ? report.stage_labels.map(String) : [];
    const values = source => stageLabels.map((_, index) => Number(source?.[index] || 0));
    return {
      ...report,
      stage_labels: stageLabels,
      stage_totals: values(report?.stage_totals),
      sex_rows: (report?.sex_rows || []).map(row => ({ ...row, values: values(row.values) }))
        .filter(row => row.values.some(value => value > 0)),
      age_rows: (report?.age_rows || []).map(row => ({ ...row, values: values(row.values) })),
      chart_stage_labels: Array.isArray(report?.chart_stage_labels) ? report.chart_stage_labels.map(String) : stageLabels,
      chart_age_rows: Array.isArray(report?.chart_age_rows) ? report.chart_age_rows : (report?.age_rows || []),
      analyzable_count: Number(report?.analyzable_count || 0),
      unknown_count: Number(report?.unknown_count || 0),
      not_applicable_count: Number(report?.not_applicable_count || 0),
      included_count: Number(report?.included_count || 0)
    };
  }

  function stageLabelSortKey(label) {
    const text = String(label || '').trim().toUpperCase();
    const match = text.match(/^(0|IV|III|II|I|4|3|2|1)(.*)$/);
    const order = { '0': 0, I: 10, '1': 10, II: 20, '2': 20, III: 30, '3': 30, IV: 40, '4': 40 };
    if (match) return [order[match[1]], match[2], text];
    return [999, '', text];
  }

  function compareStageLabels(left, right) {
    const leftKey = stageLabelSortKey(left);
    const rightKey = stageLabelSortKey(right);
    return leftKey[0] - rightKey[0]
      || leftKey[1].localeCompare(rightKey[1], undefined, { numeric: true })
      || leftKey[2].localeCompare(rightKey[2], undefined, { numeric: true });
  }

  function alignStageReportLabels(report, labels, chartLabels) {
    const source = normalizeStageReport(report);
    const valueMap = (sourceLabels, values) => Object.fromEntries(
      sourceLabels.map((label, index) => [label, Number(values?.[index] || 0)])
    );
    const alignValues = (sourceLabels, values, targetLabels) => {
      const mapped = valueMap(sourceLabels, values);
      return targetLabels.map(label => Number(mapped[label] || 0));
    };
    return {
      ...source,
      stage_labels: labels,
      stage_totals: alignValues(source.stage_labels, source.stage_totals, labels),
      sex_rows: source.sex_rows.map(row => ({
        ...row,
        values: alignValues(source.stage_labels, row.values, labels)
      })),
      age_rows: source.age_rows.map(row => ({
        ...row,
        values: alignValues(source.stage_labels, row.values, labels)
      })),
      chart_stage_labels: chartLabels,
      chart_age_rows: source.chart_age_rows.map(row => ({
        ...row,
        values: alignValues(source.chart_stage_labels, row.values, chartLabels)
      }))
    };
  }

  function alignStageComparisonReports(data, item) {
    const mainReports = data.analysis_data?.main?.stageReports || [];
    const targetReports = data.analysis_data?.target?.stageReports || [];
    const mainIndex = mainReports.findIndex(report => report.option === item);
    const targetIndex = targetReports.findIndex(report => report.option === item);
    if (mainIndex < 0 || targetIndex < 0) return;

    const main = normalizeStageReport(mainReports[mainIndex]);
    const target = normalizeStageReport(targetReports[targetIndex]);
    const labels = [...new Set([...main.stage_labels, ...target.stage_labels])].sort(compareStageLabels);
    const chartLabels = [...new Set([...main.chart_stage_labels, ...target.chart_stage_labels])]
      .sort(compareStageLabels);
    mainReports[mainIndex] = alignStageReportLabels(main, labels, chartLabels);
    targetReports[targetIndex] = alignStageReportLabels(target, labels, chartLabels);
  }

  function stageSystemTitle(system) {
    const name = String(system || '').trim();
    return isEnglish() ? name.replace(/\s+Stage$/i, '') : name;
  }

  function stageReportTitleOptions(report, yearTitle, cancerTitle) {
    return {
      year: yearTitle,
      cancer: reportCancerTitle(cancerTitle),
      system: stageSystemTitle(report.staging_system)
    };
  }

  function stageNote(report) {
    return t('stageStatisticsNote', {
      analyzable: report.analyzable_count,
      unknown: report.unknown_count,
      notApplicable: report.not_applicable_count,
      included: report.included_count
    });
  }

  function stageTableHtml(report, yearTitle, cancerTitle) {
    const titleOptions = stageReportTitleOptions(report, yearTitle, cancerTitle);
    const pct = value => report.included_count ? `${(Number(value || 0) / report.included_count * 100).toFixed(1)}%` : '0.0%';
    const total = values => values.reduce((sumValue, value) => sumValue + Number(value || 0), 0);
    let captionKey = 'stageTableTitle';
    let head = `<tr><th>${t('stage')}</th>${report.stage_labels.map(label => `<th>${escapeHtml(label)}</th>`).join('')}<th>${t('subtotal')}</th></tr>`;
    let rows = `<tr><th>${t('total')}</th>${report.stage_totals.map(value => `<td>${value}</td>`).join('')}<td>${report.included_count}</td></tr>
      <tr><th>%</th>${report.stage_totals.map(value => `<td>${pct(value)}</td>`).join('')}<td>${report.included_count ? '100.0%' : '0.0%'}</td></tr>`;

    if (report.view === 'sex') {
      captionKey = 'stageSexTableTitle';
      head = `<tr><th>${t('sex')}</th>${report.stage_labels.map(label => `<th>${escapeHtml(label)}</th>`).join('')}<th>${t('subtotal')}</th><th>%</th></tr>`;
      const sexLabel = sex => sex === '男性' ? t('male') : sex === '女性' ? t('female') : sex;
      rows = report.sex_rows.map(row => {
        const rowTotal = total(row.values);
        return `<tr><th>${escapeHtml(sexLabel(row.sex))}</th>${row.values.map(value => `<td>${value}</td>`).join('')}<td>${rowTotal}</td><td>${pct(rowTotal)}</td></tr>`;
      }).join('');
      rows += `<tr><th>${t('total')}</th>${report.stage_totals.map(value => `<td>${value}</td>`).join('')}<td>${report.included_count}</td><td>${report.included_count ? '100.0%' : '0.0%'}</td></tr>
        <tr><th>%</th>${report.stage_totals.map(value => `<td>${pct(value)}</td>`).join('')}<td>${report.included_count ? '100.0%' : '0.0%'}</td><td>-</td></tr>`;
    } else if (report.view === 'age') {
      captionKey = 'stageAgeTableTitle';
      head = `<tr><th>${t('ageGroup')}</th>${report.stage_labels.map(label => `<th>${escapeHtml(label)}</th>`).join('')}<th>${t('subtotal')}</th><th>%</th></tr>`;
      rows = report.age_rows.map(row => {
        const rowTotal = total(row.values);
        return `<tr><th>${escapeHtml(row.age)}</th>${row.values.map(value => `<td>${value}</td>`).join('')}<td>${rowTotal}</td><td>${pct(rowTotal)}</td></tr>`;
      }).join('');
      rows += `<tr><th>${t('total')}</th>${report.stage_totals.map(value => `<td>${value}</td>`).join('')}<td>${report.included_count}</td><td>${report.included_count ? '100.0%' : '0.0%'}</td></tr>
        <tr><th>%</th>${report.stage_totals.map(value => `<td>${pct(value)}</td>`).join('')}<td>${report.included_count ? '100.0%' : '0.0%'}</td><td>-</td></tr>`;
    }

    return `<div class="annual-report-table-wrap compare-stage-table-wrap">
      <table class="annual-report-table">
        <caption>${t(captionKey, titleOptions)}${sourceLine()}</caption>
        <thead>${head}</thead><tbody>${rows}</tbody>
      </table>
      <div class="annual-stage-report-note small text-secondary mt-2 mb-0 text-start">${escapeHtml(stageNote(report))}</div>
    </div>`;
  }

  function stageBlock(chartData, yearTitle, cancerTitle, chartId, item) {
    const source = (chartData?.stageReports || []).find(report => report.option === item);
    if (!source) return `<div class="alert alert-light border mb-0">${t('noData')}</div>`;
    const report = normalizeStageReport(source);
    const titleOptions = stageReportTitleOptions(report, yearTitle, cancerTitle);
    const figureKey = report.view === 'sex' ? 'stageSexFigureTitle' : report.view === 'age' ? 'stageAgeFigureTitle' : 'stageFigureTitle';
    return `${viewSwitchBlock()}
      <div data-compare-view-panel="chart">
        <div id="${chartId}" class="compare-chart compare-stage-chart"></div>
        <div class="compare-chart-caption">${t(figureKey, titleOptions)}</div>
        <div class="annual-stage-chart-note small text-secondary mt-2 mb-0">${escapeHtml(stageNote(report))}</div>
      </div>
      <div data-compare-view-panel="table" class="d-none">${stageTableHtml(report, yearTitle, cancerTitle)}</div>`;
  }

  function renderStageChart(chartId, chartData, yearTitle, cancerTitle, item) {
    if (!window.echarts) return;
    const chartEl = document.getElementById(chartId);
    const source = (chartData?.stageReports || []).find(report => report.option === item);
    if (!chartEl || !source) return;
    const report = normalizeStageReport(source);
    const oldChart = echarts.getInstanceByDom(chartEl);
    if (oldChart) oldChart.dispose();
    const chart = echarts.init(chartEl);
    const titleOptions = stageReportTitleOptions(report, yearTitle, cancerTitle);
    const chartTitleKey = report.view === 'sex' ? 'stageSexChartTitle' : report.view === 'age' ? 'stageAgeChartTitle' : 'stageChartTitle';
    const percentage = value => report.included_count ? Number(value || 0) / report.included_count * 100 : 0;
    const common = {
      animation: false,
      title: { text: t(chartTitleKey, titleOptions), subtext: t('source'), left: 'center', textStyle: { fontSize: 18, fontWeight: 'bold' } },
      toolbox: { right: 12, top: 0, feature: { dataView: { show: true, readOnly: false, title: t('dataView'), lang: [t('dataView'), t('close'), t('refresh')] }, saveAsImage: { show: true, title: t('downloadImage') } } }
    };

    if (report.view === 'sex') {
      const sexLabel = sex => sex === '男性' ? t('male') : sex === '女性' ? t('female') : sex;
      const rows = report.sex_rows;
      const sexSeries = rows.map(row => {
        const male = row.sex === '男性';
        return {
          name: sexLabel(row.sex),
          type: 'bar',
          stack: 'stage',
          barWidth: 45,
          data: row.values.map(value => Number(percentage(value).toFixed(1))),
          itemStyle: {
            color: male ? '#5470C6' : '#EE6666',
            borderColor: male ? '#5470C6' : '#EE6666',
            borderWidth: 1
          },
          label: { show: false }
        };
      });
      const maleRow = rows.find(row => row.sex === '男性');
      const femaleRow = rows.find(row => row.sex === '女性');
      const topLabelSeries = {
        name: '__stageSexLabels',
        type: 'bar',
        barWidth: 45,
        barGap: '-100%',
        silent: true,
        z: 10,
        tooltip: { show: false },
        data: report.stage_labels.map((_, index) => {
          const malePercent = percentage(maleRow?.values[index] || 0);
          const femalePercent = percentage(femaleRow?.values[index] || 0);
          return { value: Number((malePercent + femalePercent).toFixed(1)), malePercent, femalePercent };
        }),
        itemStyle: { color: 'transparent', borderColor: 'transparent' },
        label: {
          show: true,
          position: 'top',
          distance: 4,
          align: 'center',
          fontSize: 13,
          fontWeight: 'bold',
          formatter: params => {
            return [
              `{female|${Number(params.data.femalePercent || 0).toFixed(1)}%}`,
              `{male|${Number(params.data.malePercent || 0).toFixed(1)}%}`
            ].join('\n');
          },
          rich: {
            male: { color: '#36558f', fontSize: 13, fontWeight: 'bold', lineHeight: 16, width: 45, align: 'center' },
            female: { color: '#b54848', fontSize: 13, fontWeight: 'bold', lineHeight: 16, width: 45, align: 'center' }
          }
        }
      };
      chart.setOption({
        ...common,
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: params => {
            const lines = params.filter(entry => entry.seriesName !== '__stageSexLabels').map(entry => {
              const row = rows.find(itemRow => sexLabel(itemRow.sex) === entry.seriesName);
              const count = Number(row?.values[entry.dataIndex] || 0);
              return `${entry.marker}${entry.seriesName}: ${Number(entry.value).toFixed(1)}% (${count})`;
            });
            return `${report.staging_system} ${params[0]?.name || ''}<br/>${lines.join('<br/>')}`;
          }
        },
        legend: { top: 55, data: rows.map(row => sexLabel(row.sex)) },
        grid: { left: 60, right: 30, top: 95, bottom: 55 },
        xAxis: { type: 'category', data: report.stage_labels },
        yAxis: { type: 'value', min: 0, max: 100, interval: 10, axisLabel: { formatter: '{value}%' } },
        series: [...sexSeries, topLabelSeries]
      });
    } else if (report.view === 'age') {
      const colors = ['#F3AE9F', '#E9CB92', '#C3E4C3', '#A7B9DF', '#C8B0DC'];
      const labels = report.chart_stage_labels;
      const ageStagePercentages = report.chart_age_rows.map(row => {
        const total = (row.values || []).reduce((sumValue, value) => sumValue + Number(value || 0), 0);
        return labels.map((_, index) => total
          ? Number((Number(row.values?.[index] || 0) / total * 100).toFixed(1))
          : 0);
      });
      const smallStageLabelData = [];
      ageStagePercentages.forEach((values, rowIndex) => {
        let cumulative = 0;
        values.forEach((value, stageIndex) => {
          if (value > 0 && value <= 3) {
            smallStageLabelData.push([
              cumulative + value / 2,
              report.chart_age_rows[rowIndex].age,
              value,
              stageIndex
            ]);
          }
          cumulative += value;
        });
      });
      const smallStageLabelSeries = {
        name: '__smallStageLabels',
        type: 'custom',
        silent: true,
        tooltip: { show: false },
        z: 20,
        data: smallStageLabelData,
        renderItem: (params, api) => {
          const point = api.coord([api.value(0), api.value(1)]);
          const stageIndex = Number(api.value(3) || 0);
          const horizontalShift = 8;
          const lineStartY = point[1] - 10;
          const lineEnd = [point[0] + horizontalShift, point[1] - 18];
          return { type: 'group', children: [
            { type: 'line', shape: { x1: point[0], y1: lineStartY, x2: lineEnd[0], y2: lineEnd[1] }, style: { stroke: colors[stageIndex % colors.length], lineWidth: 1.5 } },
            { type: 'text', style: { text: `${Number(api.value(2)).toFixed(1)}%`, x: lineEnd[0], y: lineEnd[1] - 2, fill: '#4b5563', font: '700 11px Arial, sans-serif', align: 'center', verticalAlign: 'bottom' } }
          ] };
        }
      };
      chartEl.style.height = '680px';
      chart.setOption({ ...common, tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } }, legend: { top: 55, data: labels }, grid: { left: 62, right: 28, top: 95, bottom: 45 },
        xAxis: { type: 'value', min: 0, max: 100, axisLabel: { formatter: '{value}%' } }, yAxis: { type: 'category', data: report.chart_age_rows.map(row => row.age) },
        series: [...labels.map((label, index) => ({ name: label, type: 'bar', stack: 'age-stage', barMaxWidth: 22, data: ageStagePercentages.map(values => values[index]), itemStyle: { color: colors[index % colors.length] }, label: {
          show: true,
          position: 'inside',
          align: 'center',
          verticalAlign: 'middle',
          offset: [0, 1],
          color: '#4b5563',
          fontSize: 11,
          fontFamily: 'Arial, sans-serif',
          fontStyle: 'normal',
          fontWeight: 700,
          lineHeight: 22,
          textBorderWidth: 0,
          textShadowBlur: 0,
          formatter: params => Number(params.value || 0) > 3 ? `${Number(params.value).toFixed(1)}%` : ''
        } })), smallStageLabelSeries] });
    } else {
      chart.setOption({ ...common, tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } }, grid: { left: 58, right: 28, top: 82, bottom: 55 },
        xAxis: { type: 'category', data: report.stage_labels }, yAxis: { type: 'value', min: 0, max: 100, interval: 10, axisLabel: { formatter: '{value}%' } },
        series: [{ type: 'bar', barWidth: 45, data: report.stage_totals.map(value => Number(percentage(value).toFixed(1))),
          itemStyle: {
            color: '#D4B2F6',
            borderColor: '#D4B2F6',
            borderWidth: 1
          },
          label: { show: true, position: 'top', fontSize: 13, fontWeight: 'bold', formatter: params => `${Number(params.value || 0).toFixed(1)}%` } }] });
    }
    setTimeout(() => chart.resize(), 50);
  }

  function reportBlock(item, chartData, meta, chartPrefix, activeStageSystem = '') {
    const cancerTitle = selectedCancerTitle();
    if (item === '性別年齡分佈') return sexAgeBlockV2(chartData, meta.year_label, cancerTitle, `${chartPrefix}SexAgeChart`);
    if (item === '年齡中位數') return ageMedianBlock(chartData, meta.year_label, cancerTitle);
    if (item === '可分析個案與確診個案') return analyzableBlock(chartData, meta.year_label, cancerTitle);
    if (item === '組織型態') return histologyBlock(chartData, meta.year_label, cancerTitle, `${chartPrefix}HistologyChart`);
    if (item === '個案分類') return classificationBlock(chartData, meta.year_label, cancerTitle, `${chartPrefix}ClassificationChart`);
    if (item === '期別與首次療程') return treatmentFirstCourseBlock(chartData, meta.year_label, cancerTitle, activeStageSystem);
    if ((chartData?.stageReports || []).some(report => report.option === item)) {
      return stageBlock(chartData, meta.year_label, cancerTitle, `${chartPrefix}StageChart`, item);
    }
    return `<div class="alert alert-light border mb-0">目前尚未接上：${item}</div>`;
  }

  function calculateSharedScale(data) {
    const analyses = [data.analysis_data?.main || {}, data.analysis_data?.target || {}];
    const genderAgeMax = Math.max(0, ...analyses.flatMap(analysis => {
      const normalized = normalizeGenderAgeData(analysis.genderAgeData || {});
      return [...normalized.male, ...normalized.female, ...normalized.total];
    }));
    const histologyMax = Math.max(0, ...analyses.flatMap(analysis => {
      const valid = (analysis.histologyData || []).filter(item => item.name !== 'Unknown / 未對應組織型態');
      const total = valid.reduce((sumValue, item) => sumValue + Number(item.count || 0), 0);
      return valid.map(item => total ? Number(item.count || 0) / total * 100 : 0);
    }));
    const classificationMax = Math.max(0, ...analyses.flatMap(analysis => {
      const item = analysis.diagnosisClassificationData || {};
      const total = Number(item.total_count || 0);
      return ['class0_total', 'class1_total', 'class2_total', 'class3_total'].map(key => total ? Number(item[key] || 0) / total * 100 : 0);
    }));
    const roundedMax = (value, minimum = 10) => Math.max(minimum, Math.ceil((value * 1.15) / 10) * 10);
    return {
      genderAgeMax: Math.max(10, Math.ceil((genderAgeMax * 1.15) / 5) * 5),
      histologyMax: roundedMax(histologyMax),
      classificationMax: roundedMax(classificationMax)
    };
  }

  function changeNumberText(value, suffix = '') {
    const number = Number(value || 0);
    if (number === 0) return isEnglish() ? 'No change —' : '無變化 —';
    const amount = Number.isInteger(Math.abs(number)) ? Math.abs(number) : Math.abs(number).toFixed(1);
    if (isEnglish()) {
      const englishSuffix = suffix === '人'
        ? ` ${Number(amount) === 1 ? 'case' : 'cases'}`
        : suffix === '人／年' ? ' cases/year' : suffix ? ` ${suffix}` : '';
      return `${number > 0 ? 'Increase by' : 'Decrease by'} ${amount}${englishSuffix} ${number > 0 ? '▲' : '▼'}`;
    }
    return `${number > 0 ? '增加' : '減少'}${amount}${suffix} ${number > 0 ? '▲' : '▼'}`;
  }

  function signedPercentText(mainValue, targetValue) {
    const main = Number(mainValue || 0);
    const target = Number(targetValue || 0);
    if (!main) return target ? (isEnglish() ? 'N/A' : '無法計算') : '0.0%';
    const percentage = (target - main) / main * 100;
    if (percentage === 0) return '0.0%';
    return `${percentage > 0 ? '+' : '−'}${Math.abs(percentage).toFixed(1)}%`;
  }

  function summaryText(zhText, enText) {
    return isEnglish() ? enText : zhText;
  }

  function summaryCount(value) {
    const count = Number(value || 0);
    return isEnglish() ? `${count} ${count === 1 ? 'case' : 'cases'}` : `${count}人`;
  }

  function summaryPeriod(label, zhFallback, enFallback) {
    const text = String(label || (isEnglish() ? enFallback : zhFallback));
    if (isEnglish()) return text.replace(/年/g, '');
    return text.includes('年') ? text : `${text}年`;
  }

  function summaryParentheses(text) {
    return isEnglish() ? ` (${text})` : `（${text}）`;
  }

  const summaryTitleTranslations = {
    '可分析個案差異': 'Analyzable Case Difference',
    '顯微鏡檢確診個案差異': 'Microscopically Confirmed Case Difference',
    '主要組織型態差異': 'Leading Histology Difference',
    '個案分類最大差異': 'Largest Case Classification Difference',
    '可分析期別個案數差異': 'Analyzable Staged Case Difference',
    '主要期別差異': 'Leading Stage Difference',
    '性別期別最大差異': 'Largest Stage Difference by Sex',
    '年齡層期別最大差異': 'Largest Stage Difference by Age',
    '整體主要療程': 'Overall Leading Treatment',
    '整體主要療程差異': 'Overall Leading Treatment Difference',
    '早期主要療程': 'Leading Treatment for Early Stage',
    '早期主要療程（Stage I–II）': 'Leading Treatment for Early Stage (Stage I–II)',
    '早期主要療程差異（Stage I–II）': 'Leading Treatment Difference for Early Stage (Stage I–II)',
    '晚期主要療程': 'Leading Treatment for Late Stage',
    '晚期主要療程（Stage III–IV）': 'Leading Treatment for Late Stage (Stage III–IV)',
    '晚期主要療程差異（Stage III–IV）': 'Leading Treatment Difference for Late Stage (Stage III–IV)',
    '手術治療概況': 'Surgical Treatment Overview',
    '手術治療概況差異': 'Surgical Treatment Overview Difference'
  };

  function summaryTitle(title) {
    return isEnglish() ? (summaryTitleTranslations[title] || title) : title;
  }

  const summaryCardTitles = {
    diagnosis: [
      '可分析個案差異',
      '顯微鏡檢確診個案差異',
      '主要組織型態差異',
      '個案分類最大差異'
    ],
    stage: [
      '可分析期別個案數差異',
      '主要期別差異',
      '性別期別最大差異',
      '年齡層期別最大差異'
    ],
    treatment: [
      '整體主要療程',
      '早期主要療程',
      '晚期主要療程',
      '手術治療概況'
    ],
    cross_year: [
      '區間總個案數差異',
      '年平均個案數差異',
      '單年最高個案數差異',
      '區間個案數趨勢差異'
    ]
  };

  function summaryCategoryForItem(item) {
    if (['性別年齡分佈', '年齡中位數'].includes(item)) return 'incidence';
    if (['可分析個案與確診個案', '組織型態', '個案分類'].includes(item)) return 'diagnosis';
    if (/期別$/.test(String(item || '')) || ['AJCC期別分佈', 'FIGO/MAC/BCLC/SCLC期別分佈'].includes(item)) return 'stage';
    if (['期別與首次療程', '期別與手術術式'].includes(item)) return 'treatment';
    if (['存活率', '歷年年齡中位數', '歷年期別分佈', '歷年新診斷件數', '本院常見癌症'].includes(item)) return 'cross_year';
    return 'incidence';
  }

  function renderSummaryCardPlaceholders(category) {
    const titles = summaryCardTitles[category] || [];
    document.getElementById('compareResultSummary').innerHTML = titles.map(() => `
      <div class="compare-summary-card">
        <div class="compare-summary-placeholder-value">${summaryText('未設置', 'Not configured')}</div>
      </div>
    `).join('');
  }

  function renderDiagnosisDifferenceSummary(data) {
    const mainAnalysis = data.analysis_data?.main || {};
    const targetAnalysis = data.analysis_data?.target || {};
    const mainCases = mainAnalysis.analyzableConfirmedData || {};
    const targetCases = targetAnalysis.analyzableConfirmedData || {};
    const numberValue = value => Number(value || 0);
    const percentValue = value => {
      const parsed = Number.parseFloat(String(value ?? '').replace('%', ''));
      return Number.isFinite(parsed) ? parsed : 0;
    };
    const valueClass = value => numberValue(value) > 0 ? 'is-up' : numberValue(value) < 0 ? 'is-down' : 'is-flat';
    const mainPeriod = escapeHtml(summaryPeriod(data.main?.year_label, '基準期', 'Baseline'));
    const targetPeriod = escapeHtml(summaryPeriod(data.target?.year_label, '比較期', 'Comparison'));

    const analyzableMain = numberValue(mainCases.analyzable_count);
    const analyzableTarget = numberValue(targetCases.analyzable_count);
    const analyzableDiff = analyzableTarget - analyzableMain;
    const confirmedMain = numberValue(mainCases.confirmed_count);
    const confirmedTarget = numberValue(targetCases.confirmed_count);
    const confirmedDiff = confirmedTarget - confirmedMain;

    const validHistology = analysis => (Array.isArray(analysis.histologyData) ? analysis.histologyData : [])
      .filter(item => item?.name && item.name !== 'Unknown / 未對應組織型態')
      .sort((a, b) => numberValue(b.count) - numberValue(a.count));
    const mainHistology = validHistology(mainAnalysis)[0] || null;
    const targetHistology = validHistology(targetAnalysis)[0] || null;
    let histologyPrimary = `<span class="is-flat">${summaryText('無法判定 —', 'Unable to determine —')}</span>`;
    let histologyDetail = summaryText('兩期皆無可比較的組織型態資料', 'No comparable histology data in either period');
    if (mainHistology && targetHistology && mainHistology.name === targetHistology.name) {
      const histologyDiff = numberValue(targetHistology.count) - numberValue(mainHistology.count);
      const histologyShareDiff = percentValue(targetHistology.percentage) - percentValue(mainHistology.percentage);
      const histologyShareDiffText = `${histologyShareDiff > 0 ? '+' : histologyShareDiff < 0 ? '−' : ''}${Math.abs(histologyShareDiff).toFixed(1)}%`;
      const histologyCountChangeText = histologyDiff === 0
        ? `${summaryText('無變化', 'No change')} <span class="compare-summary-flat-dash">—</span>`
        : changeNumberText(histologyDiff, '人');
      histologyPrimary = `<span>${escapeHtml(mainHistology.name)}</span><span class="compare-summary-histology-change ${valueClass(histologyDiff)}"><span class="compare-summary-histology-change-text">${histologyCountChangeText}${summaryParentheses(histologyShareDiffText)}</span></span>`;
      histologyDetail = `${mainPeriod} ${summaryCount(mainHistology.count)}${summaryParentheses(escapeHtml(mainHistology.percentage || '0.0%'))} → ${targetPeriod} ${summaryCount(targetHistology.count)}${summaryParentheses(escapeHtml(targetHistology.percentage || '0.0%'))}`;
    } else if (mainHistology && targetHistology) {
      histologyPrimary = `<span class="is-flat">${summaryText('主要型態發生變化 ⇄', 'Leading histology changed ⇄')}</span>`;
      histologyDetail = `<span class="compare-summary-diagnosis-period-line">${mainPeriod} ${escapeHtml(mainHistology.name)}${summaryParentheses(escapeHtml(mainHistology.percentage || '0.0%'))}</span><span class="compare-summary-diagnosis-period-line">→ ${targetPeriod} ${escapeHtml(targetHistology.name)}${summaryParentheses(escapeHtml(targetHistology.percentage || '0.0%'))}</span>`;
    }

    const mainClass = mainAnalysis.diagnosisClassificationData || {};
    const targetClass = targetAnalysis.diagnosisClassificationData || {};
    const classRows = [0, 1, 2, 3].map(classNumber => {
      const mainCount = numberValue(mainClass[`class${classNumber}_total`]);
      const targetCount = numberValue(targetClass[`class${classNumber}_total`]);
      const mainTotal = numberValue(mainClass.total_count);
      const targetTotal = numberValue(targetClass.total_count);
      const mainShare = mainTotal ? mainCount / mainTotal * 100 : 0;
      const targetShare = targetTotal ? targetCount / targetTotal * 100 : 0;
      return {
        label: `Class ${classNumber}`,
        mainCount,
        targetCount,
        mainShare,
        targetShare,
        difference: targetShare - mainShare
      };
    });
    const biggestClass = classRows.sort(
      (a, b) => Math.abs(b.difference) - Math.abs(a.difference)
        || (b.mainCount + b.targetCount) - (a.mainCount + a.targetCount)
    )[0];

    if (data.compare_mode === 'range') {
      const periodYearCount = period => Number(period?.year_count || 0)
        || Object.keys(period?.yearly_counts || {}).length
        || 1;
      const percentagePointText = difference => {
        if (Math.abs(difference) < 0.05) return summaryText('無變化 —', 'No change —');
        return difference > 0
          ? summaryText(`上升${Math.abs(difference).toFixed(1)}個百分點 ▲`, `Increase by ${Math.abs(difference).toFixed(1)} percentage points ▲`)
          : summaryText(`下降${Math.abs(difference).toFixed(1)}個百分點 ▼`, `Decrease by ${Math.abs(difference).toFixed(1)} percentage points ▼`);
      };
      const countRatioText = (numerator, denominator) => isEnglish()
        ? `${numerator}/${denominator} cases`
        : `${numerator}／${denominator}人`;

      const mainTotal = numberValue(mainCases.total_count ?? data.main?.total_count);
      const targetTotal = numberValue(targetCases.total_count ?? data.target?.total_count);
      const mainAnalyzableShare = mainTotal ? analyzableMain / mainTotal * 100 : 0;
      const targetAnalyzableShare = targetTotal ? analyzableTarget / targetTotal * 100 : 0;
      const analyzableShareDiff = targetAnalyzableShare - mainAnalyzableShare;
      const mainAnnualAverage = analyzableMain / periodYearCount(data.main);
      const targetAnnualAverage = analyzableTarget / periodYearCount(data.target);
      const annualAverageDiff = targetAnnualAverage - mainAnnualAverage;

      const histologyRows = new Map();
      const addHistologyRows = (items, side) => {
        (Array.isArray(items) ? items : [])
          .filter(item => item?.name && item.name !== 'Unknown / 未對應組織型態')
          .forEach(item => {
            const row = histologyRows.get(item.name) || {
              name: item.name,
              mainCount: 0,
              targetCount: 0,
              mainShare: 0,
              targetShare: 0
            };
            row[`${side}Count`] = numberValue(item.count);
            row[`${side}Share`] = percentValue(item.percentage);
            histologyRows.set(item.name, row);
          });
      };
      addHistologyRows(mainAnalysis.histologyData, 'main');
      addHistologyRows(targetAnalysis.histologyData, 'target');
      const biggestHistology = [...histologyRows.values()]
        .map(row => ({ ...row, difference: row.targetShare - row.mainShare }))
        .sort((a, b) => Math.abs(b.difference) - Math.abs(a.difference)
          || (b.mainCount + b.targetCount) - (a.mainCount + a.targetCount))[0] || null;

      const histologyPrimaryRange = biggestHistology
        ? `<span>${escapeHtml(biggestHistology.name)}</span><span class="compare-summary-histology-change ${valueClass(biggestHistology.difference)}"><span class="compare-summary-histology-change-text">${percentagePointText(biggestHistology.difference)}</span></span>`
        : `<span class="is-flat">${summaryText('無法判定 —', 'Unable to determine —')}</span>`;
      const histologyDetailRange = biggestHistology
        ? `${mainPeriod} ${summaryCount(biggestHistology.mainCount)}${summaryParentheses(`${biggestHistology.mainShare.toFixed(1)}%`)} → ${targetPeriod} ${summaryCount(biggestHistology.targetCount)}${summaryParentheses(`${biggestHistology.targetShare.toFixed(1)}%`)}`
        : summaryText('兩個區間皆無可比較的組織型態資料', 'No comparable histology data in either interval');

      document.getElementById('compareResultSummary').innerHTML = `
        <div class="compare-summary-card">
          <div class="compare-summary-label">${summaryText('年平均可分析個案數差異', 'Annual Average Analyzable Case Difference')}</div>
          <div class="compare-summary-value ${valueClass(annualAverageDiff)}">${summaryText('年平均', 'Annual average ')}${changeNumberText(annualAverageDiff, '人／年')}${summaryParentheses(signedPercentText(mainAnnualAverage, targetAnnualAverage))}</div>
          <div class="compare-summary-period-detail">${mainPeriod} ${mainAnnualAverage.toFixed(1)}${summaryText('人／年', ' cases/year')} → ${targetPeriod} ${targetAnnualAverage.toFixed(1)}${summaryText('人／年', ' cases/year')}</div>
          <div class="compare-summary-period-detail compare-summary-period-detail-next">${summaryText('區間總數：', 'Interval total: ')}${summaryCount(analyzableMain)} → ${summaryCount(analyzableTarget)}</div>
        </div>
        <div class="compare-summary-card">
          <div class="compare-summary-label">${summaryText('可分析個案差異（依區間內確診個案的可分析率判定）', 'Analyzable Case Difference (based on the analyzable rate among diagnosed cases in each interval)')}</div>
          <div class="compare-summary-value ${valueClass(analyzableShareDiff)}">${percentagePointText(analyzableShareDiff)}</div>
          <div class="compare-summary-period-detail compare-summary-period-comparison compare-summary-range-diagnosis-detail">
            <span class="compare-summary-period-main">${mainPeriod} ${countRatioText(analyzableMain, mainTotal)}${summaryParentheses(`${mainAnalyzableShare.toFixed(1)}%`)}</span>
            <span class="compare-summary-period-target"><span class="compare-summary-period-arrow">→</span>${targetPeriod} ${countRatioText(analyzableTarget, targetTotal)}${summaryParentheses(`${targetAnalyzableShare.toFixed(1)}%`)}</span>
          </div>
        </div>
        <div class="compare-summary-card">
          <div class="compare-summary-label">${summaryText('組織型態分布差異', 'Histology Distribution Difference')}</div>
          <div class="compare-summary-diagnosis-primary">${histologyPrimaryRange}</div>
          <div class="compare-summary-period-detail compare-summary-diagnosis-detail">${histologyDetailRange}</div>
        </div>
        <div class="compare-summary-card">
          <div class="compare-summary-label">${summaryText('個案分類分布差異', 'Case Classification Distribution Difference')}</div>
          <div class="compare-summary-age-row">
            <span class="compare-summary-age-group">${escapeHtml(biggestClass?.label || '—')}</span>
            <span class="compare-summary-age-change ${valueClass(biggestClass?.difference)}">${biggestClass ? percentagePointText(biggestClass.difference) : summaryText('無法判定', 'Unable to determine')}</span>
          </div>
          <div class="compare-summary-period-values compare-summary-range-classification-detail">${mainPeriod} ${summaryCount(biggestClass?.mainCount)}${summaryParentheses(`${numberValue(biggestClass?.mainShare).toFixed(1)}%`)} → ${targetPeriod} ${summaryCount(biggestClass?.targetCount)}${summaryParentheses(`${numberValue(biggestClass?.targetShare).toFixed(1)}%`)}</div>
        </div>
      `;
      return;
    }

    const classChangeText = biggestClass
      ? `${changeNumberText(biggestClass.targetCount - biggestClass.mainCount, '人')}${summaryParentheses(`${biggestClass.difference > 0 ? '+' : biggestClass.difference < 0 ? '−' : ''}${Math.abs(biggestClass.difference).toFixed(1)}%`)}`
      : summaryText('無法判定', 'Unable to determine');

    document.getElementById('compareResultSummary').innerHTML = `
      <div class="compare-summary-card">
        <div class="compare-summary-label">${summaryTitle('可分析個案差異')}</div>
        <div class="compare-summary-value ${valueClass(analyzableDiff)}">${changeNumberText(analyzableDiff, '人')}${summaryParentheses(signedPercentText(analyzableMain, analyzableTarget))}</div>
        <div class="compare-summary-period-detail">${mainPeriod} ${summaryCount(analyzableMain)}${summaryParentheses(escapeHtml(mainCases.analyzable_percent || '0.0%'))} → ${targetPeriod} ${summaryCount(analyzableTarget)}${summaryParentheses(escapeHtml(targetCases.analyzable_percent || '0.0%'))}</div>
      </div>
      <div class="compare-summary-card">
        <div class="compare-summary-label">${summaryTitle('顯微鏡檢確診個案差異')}</div>
        <div class="compare-summary-value ${valueClass(confirmedDiff)}">${changeNumberText(confirmedDiff, '人')}${summaryParentheses(signedPercentText(confirmedMain, confirmedTarget))}</div>
        <div class="compare-summary-period-detail">${mainPeriod} ${summaryCount(confirmedMain)}${summaryParentheses(escapeHtml(mainCases.confirmed_percent || '0.0%'))} → ${targetPeriod} ${summaryCount(confirmedTarget)}${summaryParentheses(escapeHtml(targetCases.confirmed_percent || '0.0%'))}</div>
      </div>
      <div class="compare-summary-card">
        <div class="compare-summary-label">${summaryTitle('主要組織型態差異')}</div>
        <div class="compare-summary-diagnosis-primary">${histologyPrimary}</div>
        <div class="compare-summary-period-detail compare-summary-diagnosis-detail">${histologyDetail}</div>
      </div>
      <div class="compare-summary-card">
        <div class="compare-summary-label">${summaryTitle('個案分類最大差異')}</div>
        <div class="compare-summary-age-row">
          <span class="compare-summary-age-group">${escapeHtml(biggestClass?.label || '—')}</span>
          <span class="compare-summary-age-change ${valueClass(biggestClass?.difference)}">${classChangeText}</span>
        </div>
        <div class="compare-summary-period-values">${mainPeriod} ${summaryCount(biggestClass?.mainCount)}${summaryParentheses(`${numberValue(biggestClass?.mainShare).toFixed(1)}%`)} → ${targetPeriod} ${summaryCount(biggestClass?.targetCount)}${summaryParentheses(`${numberValue(biggestClass?.targetShare).toFixed(1)}%`)}</div>
      </div>
    `;
  }

  function renderStageDifferenceSummary(data, item) {
    const findReport = side => normalizeStageReport(
      (data.analysis_data?.[side]?.stageReports || []).find(report => report.option === item) || {}
    );
    const main = findReport('main');
    const target = findReport('target');
    const valueClass = value => Number(value) > 0 ? 'is-up' : Number(value) < 0 ? 'is-down' : 'is-flat';
    const mainPeriod = escapeHtml(summaryPeriod(data.main?.year_label, '基準期', 'Baseline'));
    const targetPeriod = escapeHtml(summaryPeriod(data.target?.year_label, '比較期', 'Comparison'));
    const stageLabel = label => {
      const text = String(label || '').trim();
      if (!text || text === '—') return '—';
      return /^Stage\s+/i.test(text) ? text : `Stage ${text}`;
    };
    const ageLabel = label => {
      const text = String(label || '—').replace(/^(\d+)-(\d+)$/, '$1–$2');
      if (text === '—') return text;
      if (isEnglish()) return `${text.replace(/歲/g, '')} yrs`;
      return text.includes('歲') ? text : `${text}歲`;
    };
    const share = (count, total) => total ? Number(count || 0) / total * 100 : 0;
    const shareDiffText = difference => `${difference > 0 ? '+' : difference < 0 ? '−' : ''}${Math.abs(difference).toFixed(1)}%`;
    const countChangeText = difference => changeNumberText(difference, '人');
    const labels = [...new Set([...main.stage_labels, ...target.stage_labels])].sort(compareStageLabels);
    const dominantStage = report => report.stage_labels.map((label, index) => ({
      label,
      count: Number(report.stage_totals[index] || 0),
      share: share(report.stage_totals[index], report.included_count)
    })).sort((a, b) => b.count - a.count || compareStageLabels(a.label, b.label))[0] || { label: '—', count: 0, share: 0 };
    const mainDominant = dominantStage(main);
    const targetDominant = dominantStage(target);
    const sameDominant = mainDominant.label === targetDominant.label;

    const rowMap = reportRows => Object.fromEntries((reportRows || []).map(row => [String(row.sex ?? row.age ?? ''), row]));
    const largestCellDifference = (mainRows, targetRows) => {
      const mainMap = rowMap(mainRows);
      const targetMap = rowMap(targetRows);
      const rowLabels = [...new Set([...Object.keys(mainMap), ...Object.keys(targetMap)])];
      const cells = [];
      rowLabels.forEach(rowLabel => {
        labels.forEach(label => {
          const mainIndex = main.stage_labels.indexOf(label);
          const targetIndex = target.stage_labels.indexOf(label);
          const mainCount = mainIndex >= 0 ? Number(mainMap[rowLabel]?.values?.[mainIndex] || 0) : 0;
          const targetCount = targetIndex >= 0 ? Number(targetMap[rowLabel]?.values?.[targetIndex] || 0) : 0;
          const mainShare = share(mainCount, main.included_count);
          const targetShare = share(targetCount, target.included_count);
          cells.push({ rowLabel, label, mainCount, targetCount, mainShare, targetShare, difference: targetShare - mainShare });
        });
      });
      return cells.sort((a, b) => Math.abs(b.difference) - Math.abs(a.difference)
        || Math.abs(b.targetCount - b.mainCount) - Math.abs(a.targetCount - a.mainCount)
        || (b.mainCount + b.targetCount) - (a.mainCount + a.targetCount))[0]
        || { rowLabel: '—', label: '—', mainCount: 0, targetCount: 0, mainShare: 0, targetShare: 0, difference: 0 };
    };
    const largestSexDifference = sex => largestCellDifference(
      main.sex_rows.filter(row => row.sex === sex),
      target.sex_rows.filter(row => row.sex === sex)
    );
    const sexDifferences = ['男性', '女性'].map(sex => ({ sex, ...largestSexDifference(sex) }));
    const ageLargest = largestCellDifference(main.age_rows, target.age_rows);
    const sexLabel = label => label === '男性' ? summaryText('男性', 'Male') : label === '女性' ? summaryText('女性', 'Female') : label;
    const includedDiff = target.included_count - main.included_count;
    const includedPercentDiff = main.included_count ? includedDiff / main.included_count * 100 : 0;
    const periodComparison = (mainText, targetText) => `<span class="compare-summary-period-main">${mainText}</span><span class="compare-summary-period-target"><span class="compare-summary-period-arrow">→</span>${targetText}</span>`;

    if (data.compare_mode === 'range') {
      const periodYearCount = period => Number(period?.year_count || 0)
        || Object.keys(period?.yearly_counts || {}).length
        || 1;
      const percentagePointText = difference => {
        if (Math.abs(difference) < 0.05) return summaryText('無變化 —', 'No change —');
        return difference > 0
          ? summaryText(`上升${Math.abs(difference).toFixed(1)}個百分點 ▲`, `Increase by ${Math.abs(difference).toFixed(1)} percentage points ▲`)
          : summaryText(`下降${Math.abs(difference).toFixed(1)}個百分點 ▼`, `Decrease by ${Math.abs(difference).toFixed(1)} percentage points ▼`);
      };
      const countRatioText = (count, total) => isEnglish()
        ? `${count}/${total} cases`
        : `${count}／${total}人`;
      const valuesForLabels = (report, values) => labels.map(label => {
        const index = report.stage_labels.indexOf(label);
        return index >= 0 ? Number(values?.[index] || 0) : 0;
      });
      const sum = values => values.reduce((total, value) => total + Number(value || 0), 0);
      const largestDifference = rows => rows
        .filter(row => row.mainTotal > 0 || row.targetTotal > 0)
        .sort((a, b) => Math.abs(b.difference) - Math.abs(a.difference)
          || Math.abs(b.targetCount - b.mainCount) - Math.abs(a.targetCount - a.mainCount)
          || (b.mainCount + b.targetCount) - (a.mainCount + a.targetCount))[0] || null;

      const overallLargest = largestDifference(labels.map(label => {
        const mainIndex = main.stage_labels.indexOf(label);
        const targetIndex = target.stage_labels.indexOf(label);
        const mainCount = mainIndex >= 0 ? Number(main.stage_totals[mainIndex] || 0) : 0;
        const targetCount = targetIndex >= 0 ? Number(target.stage_totals[targetIndex] || 0) : 0;
        const mainShare = share(mainCount, main.included_count);
        const targetShare = share(targetCount, target.included_count);
        return {
          label,
          mainCount,
          targetCount,
          mainTotal: main.included_count,
          targetTotal: target.included_count,
          mainShare,
          targetShare,
          difference: targetShare - mainShare
        };
      }));

      const groupDifference = (rowKey, rowValue) => {
        const mainRow = (main[rowKey] || []).find(row => String(row.sex ?? row.age ?? '') === rowValue);
        const targetRow = (target[rowKey] || []).find(row => String(row.sex ?? row.age ?? '') === rowValue);
        const mainValues = valuesForLabels(main, mainRow?.values);
        const targetValues = valuesForLabels(target, targetRow?.values);
        const mainTotal = sum(mainValues);
        const targetTotal = sum(targetValues);
        return largestDifference(labels.map((label, index) => {
          const mainCount = mainValues[index];
          const targetCount = targetValues[index];
          const mainShare = share(mainCount, mainTotal);
          const targetShare = share(targetCount, targetTotal);
          return { label, mainCount, targetCount, mainTotal, targetTotal, mainShare, targetShare, difference: targetShare - mainShare };
        }));
      };
      const rangeSexDifferences = ['男性', '女性'].map(sex => ({ sex, difference: groupDifference('sex_rows', sex) }));

      const mainAgeMap = Object.fromEntries((main.age_rows || []).map(row => [String(row.age || ''), row]));
      const targetAgeMap = Object.fromEntries((target.age_rows || []).map(row => [String(row.age || ''), row]));
      const rangeAgeRows = [];
      [...new Set([...Object.keys(mainAgeMap), ...Object.keys(targetAgeMap)])].forEach(rowLabel => {
        const mainValues = valuesForLabels(main, mainAgeMap[rowLabel]?.values);
        const targetValues = valuesForLabels(target, targetAgeMap[rowLabel]?.values);
        const mainTotal = sum(mainValues);
        const targetTotal = sum(targetValues);
        labels.forEach((label, index) => {
          const mainCount = mainValues[index];
          const targetCount = targetValues[index];
          const mainShare = share(mainCount, mainTotal);
          const targetShare = share(targetCount, targetTotal);
          rangeAgeRows.push({ rowLabel, label, mainCount, targetCount, mainTotal, targetTotal, mainShare, targetShare, difference: targetShare - mainShare });
        });
      });
      const rangeAgeLargest = largestDifference(
        rangeAgeRows.filter(row => row.mainTotal >= 5 && row.targetTotal >= 5)
      );

      const mainAnnualAverage = main.included_count / periodYearCount(data.main);
      const targetAnnualAverage = target.included_count / periodYearCount(data.target);
      const annualAverageDiff = targetAnnualAverage - mainAnnualAverage;
      const sexRangeSummary = ({ sex, difference }) => {
        if (!difference) {
          return {
            primary: `<span class="is-flat">${escapeHtml(sexLabel(sex))} ${summaryText('無法判定', 'Unable to determine')}</span>`,
            detail: summaryText('無可比較的期別資料', 'No comparable stage data')
          };
        }
        return {
          primary: `<span class="${valueClass(difference.difference)}">${escapeHtml(sexLabel(sex))} ${escapeHtml(stageLabel(difference.label))} ${percentagePointText(difference.difference)}</span>`,
          detail: periodComparison(`${mainPeriod} ${countRatioText(difference.mainCount, difference.mainTotal)}${summaryParentheses(`${difference.mainShare.toFixed(1)}%`)}`, `${targetPeriod} ${countRatioText(difference.targetCount, difference.targetTotal)}${summaryParentheses(`${difference.targetShare.toFixed(1)}%`)}`)
        };
      };
      const maleRange = sexRangeSummary(rangeSexDifferences[0]);
      const femaleRange = sexRangeSummary(rangeSexDifferences[1]);

      document.getElementById('compareResultSummary').innerHTML = `
        <div class="compare-summary-card">
          <div class="compare-summary-label">${summaryText('年平均可分析期別個案數差異', 'Annual Average Analyzable Staged Case Difference')}</div>
          <div class="compare-summary-value ${valueClass(annualAverageDiff)}">${summaryText('年平均', 'Annual average ')}${changeNumberText(annualAverageDiff, '人／年')}${summaryParentheses(signedPercentText(mainAnnualAverage, targetAnnualAverage))}</div>
          <div class="compare-summary-period-detail compare-summary-period-comparison">${periodComparison(`${mainPeriod} ${mainAnnualAverage.toFixed(1)}${summaryText('人／年', ' cases/year')}`, `${targetPeriod} ${targetAnnualAverage.toFixed(1)}${summaryText('人／年', ' cases/year')}`)}</div>
          <div class="compare-summary-period-detail compare-summary-period-detail-next">${summaryText('區間總數：', 'Interval total: ')}${summaryCount(main.included_count)} → ${summaryCount(target.included_count)}</div>
        </div>
        <div class="compare-summary-card">
          <div class="compare-summary-label">${summaryText('期別分布最大差異', 'Largest Stage Distribution Difference')}</div>
          <div class="compare-summary-age-row">
            <span class="compare-summary-age-group">${escapeHtml(stageLabel(overallLargest?.label || '—'))}</span>
            <span class="compare-summary-age-change ${valueClass(overallLargest?.difference)}">${overallLargest ? percentagePointText(overallLargest.difference) : summaryText('無法判定', 'Unable to determine')}</span>
          </div>
          <div class="compare-summary-period-values compare-summary-period-comparison">${overallLargest ? periodComparison(`${mainPeriod} ${summaryCount(overallLargest.mainCount)}${summaryParentheses(`${overallLargest.mainShare.toFixed(1)}%`)}`, `${targetPeriod} ${summaryCount(overallLargest.targetCount)}${summaryParentheses(`${overallLargest.targetShare.toFixed(1)}%`)}`) : summaryText('兩個區間皆無可比較的期別資料', 'No comparable stage data in either interval')}</div>
        </div>
        <div class="compare-summary-card">
          <div class="compare-summary-label">${summaryText('性別期別分布差異', 'Stage Distribution Difference by Sex')}</div>
          <div class="compare-summary-stage-sex-primary">${maleRange.primary}</div>
          <div class="compare-summary-stage-sex-primary compare-summary-stage-sex-primary-next">${femaleRange.primary}</div>
          <div class="compare-summary-period-detail compare-summary-period-comparison compare-summary-stage-sex-detail compare-summary-range-stage-sex-detail"><span class="compare-summary-sex-prefix">${summaryText('男：', 'Male:')}</span>${maleRange.detail}</div>
          <div class="compare-summary-period-detail compare-summary-period-detail-next compare-summary-period-comparison compare-summary-stage-sex-detail compare-summary-range-stage-sex-detail"><span class="compare-summary-sex-prefix">${summaryText('女：', 'Female:')}</span>${femaleRange.detail}</div>
        </div>
        <div class="compare-summary-card">
          <div class="compare-summary-label">${summaryText('年齡層期別分布最大差異', 'Largest Stage Distribution Difference by Age')}</div>
          <div class="compare-summary-age-row">
            <span class="compare-summary-age-group">${rangeAgeLargest ? `${escapeHtml(ageLabel(rangeAgeLargest.rowLabel))} ${escapeHtml(stageLabel(rangeAgeLargest.label))}` : '—'}</span>
            <span class="compare-summary-age-change ${valueClass(rangeAgeLargest?.difference)}">${rangeAgeLargest ? percentagePointText(rangeAgeLargest.difference) : summaryText('無法判定', 'Unable to determine')}</span>
          </div>
          <div class="compare-summary-period-values compare-summary-period-comparison">${rangeAgeLargest ? periodComparison(`${mainPeriod} ${countRatioText(rangeAgeLargest.mainCount, rangeAgeLargest.mainTotal)}${summaryParentheses(`${rangeAgeLargest.mainShare.toFixed(1)}%`)}`, `${targetPeriod} ${countRatioText(rangeAgeLargest.targetCount, rangeAgeLargest.targetTotal)}${summaryParentheses(`${rangeAgeLargest.targetShare.toFixed(1)}%`)}`) : summaryText('兩個區間皆無可比較的年齡層期別資料', 'No comparable age-stage data in either interval')}</div>
        </div>`;
      return;
    }

    const sexDifferenceSummary = difference => {
      const hasData = difference.label !== '—';
      const countDiff = difference.targetCount - difference.mainCount;
      return {
        primary: `<span class="${hasData ? valueClass(countDiff) : 'is-flat'}">${escapeHtml(sexLabel(difference.sex))}${hasData ? ` ${escapeHtml(stageLabel(difference.label))} ${countChangeText(countDiff)}${summaryParentheses(shareDiffText(difference.difference))}` : ` ${summaryText('無法判定', 'Unable to determine')}`}</span>`,
        detail: hasData
          ? periodComparison(`${mainPeriod} ${summaryCount(difference.mainCount)}${summaryParentheses(`${difference.mainShare.toFixed(1)}%`)}`, `${targetPeriod} ${summaryCount(difference.targetCount)}${summaryParentheses(`${difference.targetShare.toFixed(1)}%`)}`)
          : summaryText('無法判定', 'Unable to determine')
      };
    };
    const maleSexDifference = sexDifferenceSummary(sexDifferences[0]);
    const femaleSexDifference = sexDifferenceSummary(sexDifferences[1]);
    document.getElementById('compareResultSummary').innerHTML = `
      <div class="compare-summary-card">
        <div class="compare-summary-label">${summaryTitle('可分析期別個案數差異')}</div>
        <div class="compare-summary-value ${valueClass(includedDiff)}">${countChangeText(includedDiff)}${summaryParentheses(shareDiffText(includedPercentDiff))}</div>
        <div class="compare-summary-period-detail compare-summary-period-comparison">${periodComparison(`${mainPeriod} ${summaryCount(main.included_count)}`, `${targetPeriod} ${summaryCount(target.included_count)}`)}</div>
      </div>
      <div class="compare-summary-card">
        <div class="compare-summary-label">${summaryTitle('主要期別差異')}</div>
        <div class="compare-summary-value ${sameDominant ? 'is-flat' : ''}">${sameDominant ? `${escapeHtml(stageLabel(mainDominant.label))} ${summaryText('維持不變 —', 'remained unchanged —')}` : `${escapeHtml(stageLabel(mainDominant.label))} ⇄ ${escapeHtml(stageLabel(targetDominant.label))}`}</div>
        <div class="compare-summary-period-detail compare-summary-period-comparison">${periodComparison(`${mainPeriod} ${escapeHtml(stageLabel(mainDominant.label))} ${summaryCount(mainDominant.count)}${summaryParentheses(`${mainDominant.share.toFixed(1)}%`)}`, `${targetPeriod} ${escapeHtml(stageLabel(targetDominant.label))} ${summaryCount(targetDominant.count)}${summaryParentheses(`${targetDominant.share.toFixed(1)}%`)}`)}</div>
      </div>
      <div class="compare-summary-card">
        <div class="compare-summary-label">${summaryTitle('性別期別最大差異')}</div>
        <div class="compare-summary-stage-sex-primary">${maleSexDifference.primary}</div>
        <div class="compare-summary-stage-sex-primary compare-summary-stage-sex-primary-next">${femaleSexDifference.primary}</div>
        <div class="compare-summary-period-detail compare-summary-period-comparison compare-summary-stage-sex-detail"><span class="compare-summary-sex-prefix">${summaryText('男：', 'Male:')}</span>${maleSexDifference.detail}</div>
        <div class="compare-summary-period-detail compare-summary-period-detail-next compare-summary-period-comparison compare-summary-stage-sex-detail"><span class="compare-summary-sex-prefix">${summaryText('女：', 'Female:')}</span>${femaleSexDifference.detail}</div>
      </div>
      <div class="compare-summary-card">
        <div class="compare-summary-label">${summaryTitle('年齡層期別最大差異')}</div>
        <div class="compare-summary-age-row">
          <span class="compare-summary-age-group">${escapeHtml(ageLabel(ageLargest.rowLabel))} ${escapeHtml(stageLabel(ageLargest.label))}</span>
          <span class="compare-summary-age-change ${valueClass(ageLargest.targetCount - ageLargest.mainCount)}">${countChangeText(ageLargest.targetCount - ageLargest.mainCount)}${summaryParentheses(shareDiffText(ageLargest.difference))}</span>
        </div>
        <div class="compare-summary-period-values compare-summary-period-comparison">${periodComparison(`${mainPeriod} ${summaryCount(ageLargest.mainCount)}${summaryParentheses(`${ageLargest.mainShare.toFixed(1)}%`)}`, `${targetPeriod} ${summaryCount(ageLargest.targetCount)}${summaryParentheses(`${ageLargest.targetShare.toFixed(1)}%`)}`)}</div>
      </div>`;
  }

  function renderTreatmentDifferenceSummary(data) {
    const tablesFor = side => Array.isArray(data.analysis_data?.[side]?.stageFirstCourseData)
      ? data.analysis_data[side].stageFirstCourseData
      : [];
    const mainTables = tablesFor('main');
    const targetTables = tablesFor('target');
    const sharedSystems = mainTables.map(table => table.system).filter(system => targetTables.some(table => table.system === system));
    const system = sharedSystems.includes(activeTreatmentStageSystem) ? activeTreatmentStageSystem : sharedSystems[0];
    const tableFor = tables => tables.find(table => table.system === system) || null;
    const main = tableFor(mainTables);
    const target = tableFor(targetTables);
    const valueClass = value => Number(value) > 0 ? 'is-up' : Number(value) < 0 ? 'is-down' : 'is-flat';
    const mainPeriod = escapeHtml(summaryPeriod(data.main?.year_label, '基準期', 'Baseline'));
    const targetPeriod = escapeHtml(summaryPeriod(data.target?.year_label, '比較期', 'Comparison'));
    const percentage = (value, total) => total ? Number(value || 0) / Number(total) * 100 : 0;
    const percentDiffText = value => `${value > 0 ? '+' : value < 0 ? '−' : ''}${Math.abs(value).toFixed(1)}%`;
    const periodComparison = (mainText, targetText) => `<span class="compare-summary-period-main">${mainText}</span><span class="compare-summary-period-target"><span class="compare-summary-period-arrow">→</span>${targetText}</span>`;
    const normalizeTable = table => ({
      stageColumns: (table?.stage_columns || []).map(String),
      rows: Array.isArray(table?.rows) ? table.rows : [],
      totals: (table?.totals || []).map(value => Number(value || 0)),
      total: Number(table?.total_count || 0)
    });
    const mainTable = normalizeTable(main);
    const targetTable = normalizeTable(target);
    const stageIndexes = (table, orders) => table.stageColumns
      .map((label, index) => ({ index, order: stageLabelSortKey(String(label).replace(/^Stage\s+/i, ''))[0] }))
      .filter(item => orders.includes(item.order))
      .map(item => item.index);
    const leadingTreatment = (table, indexes = null) => {
      const selectedIndexes = indexes || table.stageColumns.map((_, index) => index);
      const denominator = selectedIndexes.reduce((sum, index) => sum + Number(table.totals[index] || 0), 0);
      const result = table.rows.map(row => ({
        treatment: String(row.treatment || ''),
        count: selectedIndexes.reduce((sum, index) => sum + Number(row.values?.[index] || 0), 0)
      })).filter(row => row.treatment && row.count > 0)
        .sort((a, b) => b.count - a.count || a.treatment.localeCompare(b.treatment, 'zh-Hant'))[0];
      return result ? { ...result, denominator, share: percentage(result.count, denominator) }
        : { treatment: '', count: 0, denominator, share: 0 };
    };
    const treatmentCard = (title, mainItem, targetItem) => {
      if (!mainItem.treatment || !targetItem.treatment) {
        const unavailableReason = (item, period) => Number(item.denominator || 0) > 0
          ? summaryText(`${period}無有效首次療程資料`, `No valid first-course treatment data for ${period}`)
          : summaryText(`${period}無符合期別的可分析個案`, `No analyzable cases in the applicable stages for ${period}`);
        const reasons = [];
        if (!mainItem.treatment) reasons.push(unavailableReason(mainItem, mainPeriod));
        if (!targetItem.treatment) reasons.push(unavailableReason(targetItem, targetPeriod));
        return `<div class="compare-summary-card">
          <div class="compare-summary-label">${summaryTitle(title)}</div>
          <div class="compare-summary-placeholder-value compare-summary-treatment-unavailable">${summaryText('無法判定', 'Unable to determine')}</div>
          <div class="compare-summary-unavailable-reason">${reasons.join(summaryText('；', '; '))}</div>
        </div>`;
      }
      const sameTreatment = mainItem.treatment === targetItem.treatment;
      const countDiff = targetItem.count - mainItem.count;
      const shareDiff = targetItem.share - mainItem.share;
      const mainTreatment = escapeHtml(treatmentLabel(mainItem.treatment));
      const targetTreatment = escapeHtml(treatmentLabel(targetItem.treatment));
      const primary = sameTreatment
        ? `<div class="compare-summary-treatment-same-row"><span class="compare-summary-treatment-name">${mainTreatment}</span><span class="compare-summary-treatment-change ${valueClass(countDiff)}">${changeNumberText(countDiff, '人')}${summaryParentheses(percentDiffText(shareDiff))}</span></div>`
        : summaryText('主要療程發生變化 ⇄', 'Leading treatment changed ⇄');
      const primaryClass = sameTreatment ? 'compare-summary-treatment-primary' : 'compare-summary-value is-flat';
      const mainText = `${mainPeriod} ${mainTreatment} ${mainItem.count}／${summaryCount(mainItem.denominator)}${summaryParentheses(`${mainItem.share.toFixed(1)}%`)}`;
      const targetText = `${targetPeriod} ${targetTreatment} ${targetItem.count}／${summaryCount(targetItem.denominator)}${summaryParentheses(`${targetItem.share.toFixed(1)}%`)}`;
      return `<div class="compare-summary-card">
        <div class="compare-summary-label">${summaryTitle(title)}</div>
        <div class="${primaryClass}">${primary}</div>
        <div class="compare-summary-period-detail compare-summary-period-comparison compare-summary-treatment-detail">${periodComparison(mainText, targetText)}</div>
      </div>`;
    };

    if (data.compare_mode === 'range') {
      const rangeTitles = [
        summaryText('整體療程分布差異', 'Overall Treatment Distribution Difference'),
        summaryText('早期主要療程分佈差異（Stage I–II）', 'Leading Treatment Distribution Difference for Early Stage (Stage I–II)'),
        summaryText('晚期主要療程分佈差異（Stage III–IV）', 'Leading Treatment Distribution Difference for Late Stage (Stage III–IV)'),
        summaryText('手術治療概況差異', 'Surgical Treatment Overview Difference')
      ];
      if (!main || !target) {
        document.getElementById('compareResultSummary').innerHTML = rangeTitles.map((title, index) => `
          <div class="compare-summary-card">
            <div class="compare-summary-label">${title}</div>
            <div class="compare-summary-placeholder-value">${index === 3 ? summaryText('尚未設置', 'Not configured') : summaryText('無法判定', 'Unable to determine')}</div>
          </div>
        `).join('');
        return;
      }

      const aggregateTreatments = (table, indexes = null) => {
        const selectedIndexes = indexes || table.stageColumns.map((_, index) => index);
        const denominator = selectedIndexes.reduce((total, index) => total + Number(table.totals[index] || 0), 0);
        const counts = new Map();
        table.rows.forEach(row => {
          const treatment = String(row.treatment || '').trim();
          if (!treatment) return;
          const count = selectedIndexes.reduce((total, index) => total + Number(row.values?.[index] || 0), 0);
          counts.set(treatment, count);
        });
        return { denominator, counts };
      };
      const largestTreatmentDifference = (mainAggregate, targetAggregate) => {
        if (!mainAggregate.denominator || !targetAggregate.denominator) return null;
        return [...new Set([...mainAggregate.counts.keys(), ...targetAggregate.counts.keys()])]
          .map(treatment => {
            const mainCount = Number(mainAggregate.counts.get(treatment) || 0);
            const targetCount = Number(targetAggregate.counts.get(treatment) || 0);
            const mainShare = percentage(mainCount, mainAggregate.denominator);
            const targetShare = percentage(targetCount, targetAggregate.denominator);
            return {
              treatment,
              mainCount,
              targetCount,
              mainDenominator: mainAggregate.denominator,
              targetDenominator: targetAggregate.denominator,
              mainShare,
              targetShare,
              difference: targetShare - mainShare
            };
          })
          .filter(row => row.mainCount > 0 || row.targetCount > 0)
          .sort((a, b) => Math.abs(b.difference) - Math.abs(a.difference)
            || Math.abs(b.targetCount - b.mainCount) - Math.abs(a.targetCount - a.mainCount)
            || (b.mainCount + b.targetCount) - (a.mainCount + a.targetCount))[0] || null;
      };
      const percentagePointText = difference => {
        if (Math.abs(difference) < 0.05) return summaryText('無變化 —', 'No change —');
        return difference > 0
          ? summaryText(`上升${Math.abs(difference).toFixed(1)}個百分點 ▲`, `Increase by ${Math.abs(difference).toFixed(1)} percentage points ▲`)
          : summaryText(`下降${Math.abs(difference).toFixed(1)}個百分點 ▼`, `Decrease by ${Math.abs(difference).toFixed(1)} percentage points ▼`);
      };
      const countRatioText = (count, total) => isEnglish()
        ? `${count}/${total} cases`
        : `${count}／${total}人`;
      const rangeTreatmentCard = (title, difference) => {
        if (!difference) {
          return `<div class="compare-summary-card">
            <div class="compare-summary-label">${title}</div>
            <div class="compare-summary-placeholder-value compare-summary-treatment-unavailable">${summaryText('無法判定', 'Unable to determine')}</div>
            <div class="compare-summary-unavailable-reason">${summaryText('其中一個區間無符合期別的可分析個案', 'One interval has no analyzable cases in the applicable stages')}</div>
          </div>`;
        }
        const treatment = escapeHtml(treatmentLabel(difference.treatment));
        const mainText = `${mainPeriod} ${treatment} ${countRatioText(difference.mainCount, difference.mainDenominator)}${summaryParentheses(`${difference.mainShare.toFixed(1)}%`)}`;
        const targetText = `${targetPeriod} ${treatment} ${countRatioText(difference.targetCount, difference.targetDenominator)}${summaryParentheses(`${difference.targetShare.toFixed(1)}%`)}`;
        return `<div class="compare-summary-card">
          <div class="compare-summary-label">${title}</div>
          <div class="compare-summary-treatment-primary">
            <div class="compare-summary-treatment-same-row">
              <span class="compare-summary-treatment-name">${treatment}</span>
              <span class="compare-summary-treatment-change ${valueClass(difference.difference)}">${percentagePointText(difference.difference)}</span>
            </div>
          </div>
          <div class="compare-summary-period-detail compare-summary-period-comparison compare-summary-treatment-detail">${periodComparison(mainText, targetText)}</div>
        </div>`;
      };

      const mainOverallRange = aggregateTreatments(mainTable);
      const targetOverallRange = aggregateTreatments(targetTable);
      const mainEarlyRange = aggregateTreatments(mainTable, stageIndexes(mainTable, [10, 20]));
      const targetEarlyRange = aggregateTreatments(targetTable, stageIndexes(targetTable, [10, 20]));
      const mainLateRange = aggregateTreatments(mainTable, stageIndexes(mainTable, [30, 40]));
      const targetLateRange = aggregateTreatments(targetTable, stageIndexes(targetTable, [30, 40]));

      document.getElementById('compareResultSummary').innerHTML = `
        ${rangeTreatmentCard(rangeTitles[0], largestTreatmentDifference(mainOverallRange, targetOverallRange))}
        ${rangeTreatmentCard(rangeTitles[1], largestTreatmentDifference(mainEarlyRange, targetEarlyRange))}
        ${rangeTreatmentCard(rangeTitles[2], largestTreatmentDifference(mainLateRange, targetLateRange))}
        <div class="compare-summary-card">
          <div class="compare-summary-label">${rangeTitles[3]}</div>
          <div class="compare-summary-placeholder-value">${summaryText('尚未設置', 'Not configured')}</div>
        </div>`;
      return;
    }

    if (!main || !target) {
      document.getElementById('compareResultSummary').innerHTML = summaryCardTitles.treatment.map(title => `
        <div class="compare-summary-card"><div class="compare-summary-label">${summaryTitle(title)}</div><div class="compare-summary-placeholder-value">${summaryText('無法判定', 'Unable to determine')}</div></div>
      `).join('');
      return;
    }

    const mainOverall = leadingTreatment(mainTable);
    const targetOverall = leadingTreatment(targetTable);
    const mainEarly = leadingTreatment(mainTable, stageIndexes(mainTable, [10, 20]));
    const targetEarly = leadingTreatment(targetTable, stageIndexes(targetTable, [10, 20]));
    const mainLate = leadingTreatment(mainTable, stageIndexes(mainTable, [30, 40]));
    const targetLate = leadingTreatment(targetTable, stageIndexes(targetTable, [30, 40]));
    document.getElementById('compareResultSummary').innerHTML = `
      ${treatmentCard('整體主要療程差異', mainOverall, targetOverall)}
      ${treatmentCard('早期主要療程差異（Stage I–II）', mainEarly, targetEarly)}
      ${treatmentCard('晚期主要療程差異（Stage III–IV）', mainLate, targetLate)}
      <div class="compare-summary-card">
        <div class="compare-summary-label">${summaryTitle('手術治療概況差異')}</div>
        <div class="compare-summary-placeholder-value">${summaryText('尚未設置', 'Not configured')}</div>
      </div>`;
  }

  function renderDifferenceSummary(data, analysisItem = '性別年齡分佈') {
    const category = summaryCategoryForItem(analysisItem);
    if (category === 'diagnosis') {
      renderDiagnosisDifferenceSummary(data);
      return;
    }
    if (category === 'stage') {
      renderStageDifferenceSummary(data, analysisItem);
      return;
    }
    if (category === 'treatment') {
      renderTreatmentDifferenceSummary(data);
      return;
    }
    if (category !== 'incidence') {
      renderSummaryCardPlaceholders(category);
      return;
    }
    const mainAnalysis = data.analysis_data?.main || {};
    const targetAnalysis = data.analysis_data?.target || {};
    const mainAge = mainAnalysis.ageMedianData || {};
    const targetAge = targetAnalysis.ageMedianData || {};
    const mainGender = normalizeGenderAgeData(mainAnalysis.genderAgeData || {});
    const targetGender = normalizeGenderAgeData(targetAnalysis.genderAgeData || {});
    const changes = targetGender.categories.map((label, index) => {
      const mainCount = Number(mainGender.total[index] || 0);
      const targetCount = Number(targetGender.total[index] || 0);
      return { label, mainCount, targetCount, value: targetCount - mainCount };
    });
    const biggest = changes.sort((a, b) => Math.abs(b.value) - Math.abs(a.value))[0]
      || { label: '—', mainCount: 0, targetCount: 0, value: 0 };
    const mainAgeGroupTotal = mainGender.total.reduce((sum, value) => sum + Number(value || 0), 0);
    const targetAgeGroupTotal = targetGender.total.reduce((sum, value) => sum + Number(value || 0), 0);
    const mainAgeShare = mainAgeGroupTotal ? biggest.mainCount / mainAgeGroupTotal * 100 : 0;
    const targetAgeShare = targetAgeGroupTotal ? biggest.targetCount / targetAgeGroupTotal * 100 : 0;
    const ageShareDiff = targetAgeShare - mainAgeShare;
    const ageShareDiffText = ageShareDiff > 0
      ? `+${ageShareDiff.toFixed(1)}%`
      : ageShareDiff < 0 ? `−${Math.abs(ageShareDiff).toFixed(1)}%` : '0.0%';
    const formatAgeGroup = label => {
      const text = String(label || '—').replace(/^(\d+)-(\d+)$/, '$1–$2');
      if (text === '—') return text;
      if (isEnglish()) return `${text.replace(/歲/g, '')} yrs`;
      return `${text}${text.includes('歲') ? '' : '歲'}`;
    };
    const ageGroupLabel = formatAgeGroup(biggest.label);
    const medianGroup = genderData => {
      const counts = genderData.total.map(value => Number(value || 0));
      const total = counts.reduce((sum, value) => sum + value, 0);
      if (!total) return { index: -1, label: '—' };
      const medianPosition = (total + 1) / 2;
      let cumulative = 0;
      const index = counts.findIndex(value => {
        cumulative += value;
        return cumulative >= medianPosition;
      });
      return {
        index,
        label: index >= 0 ? formatAgeGroup(genderData.categories[index]) : '—'
      };
    };
    const mainMedianGroup = medianGroup(mainGender);
    const targetMedianGroup = medianGroup(targetGender);
    const medianGroupDiff = mainMedianGroup.index >= 0 && targetMedianGroup.index >= 0
      ? targetMedianGroup.index - mainMedianGroup.index
      : 0;
    const medianGroupChangeText = mainMedianGroup.index < 0 || targetMedianGroup.index < 0
      ? summaryText('無法判定', 'Unable to determine')
      : medianGroupDiff > 0
        ? summaryText(`上升${medianGroupDiff}個年齡級距 ▲`, `Increased by ${medianGroupDiff} age ${medianGroupDiff === 1 ? 'band' : 'bands'} ▲`)
        : medianGroupDiff < 0
          ? summaryText(`下降${Math.abs(medianGroupDiff)}個年齡級距 ▼`, `Decreased by ${Math.abs(medianGroupDiff)} age ${Math.abs(medianGroupDiff) === 1 ? 'band' : 'bands'} ▼`)
          : summaryText('中位年齡層無變化 —', 'No change in median age group —');
    const totalDiff = Number(data.target?.total_count || 0) - Number(data.main?.total_count || 0);
    const maleCountDiff = Number(targetAge.male_count || 0) - Number(mainAge.male_count || 0);
    const femaleCountDiff = Number(targetAge.female_count || 0) - Number(mainAge.female_count || 0);
    const mainGenderTotal = Number(mainAge.male_count || 0) + Number(mainAge.female_count || 0);
    const targetGenderTotal = Number(targetAge.male_count || 0) + Number(targetAge.female_count || 0);
    const mainMaleShare = mainGenderTotal ? Number(mainAge.male_count || 0) / mainGenderTotal * 100 : 0;
    const targetMaleShare = targetGenderTotal ? Number(targetAge.male_count || 0) / targetGenderTotal * 100 : 0;
    const mainFemaleShare = mainGenderTotal ? Number(mainAge.female_count || 0) / mainGenderTotal * 100 : 0;
    const targetFemaleShare = targetGenderTotal ? Number(targetAge.female_count || 0) / targetGenderTotal * 100 : 0;
    const maleShareDiff = targetMaleShare - mainMaleShare;
    const femaleShareDiff = targetFemaleShare - mainFemaleShare;
    const shareChangeText = (mainShare, targetShare) => {
      const difference = targetShare - mainShare;
      if (Math.abs(difference) < 0.05) return '0.0%';
      return `${difference > 0 ? '+' : '−'}${Math.abs(difference).toFixed(1)}%`;
    };
    const shareValueClass = difference => difference > 0 ? 'is-up' : difference < 0 ? 'is-down' : '';
    const formatPeriod = (label, zhFallback, enFallback) => summaryPeriod(label, zhFallback, enFallback);
    const mainPeriodLabel = escapeHtml(formatPeriod(data.main?.year_label, '基準期', 'Baseline'));
    const targetPeriodLabel = escapeHtml(formatPeriod(data.target?.year_label, '比較期', 'Comparison'));
    const rangePeriodComparison = (prefix, mainText, targetText) => `<span class="compare-summary-period-main">${prefix}${mainText}</span><span class="compare-summary-period-target"><span class="compare-summary-period-arrow">→</span>${targetText}</span>`;
    const valueClass = value => Number(value) > 0 ? 'is-up' : Number(value) < 0 ? 'is-down' : 'is-flat';
    if (data.compare_mode === 'range') {
      const periodYearCount = period => Number(period?.year_count || 0)
        || Object.keys(period?.yearly_counts || {}).length
        || 1;
      const mainAnnualAverage = Number(data.main?.total_count || 0) / periodYearCount(data.main);
      const targetAnnualAverage = Number(data.target?.total_count || 0) / periodYearCount(data.target);
      const annualAverageDiff = targetAnnualAverage - mainAnnualAverage;
      const annualAveragePercent = mainAnnualAverage ? annualAverageDiff / mainAnnualAverage * 100 : 0;
      const percentagePointChangeText = difference => {
        if (Math.abs(difference) < 0.05) return summaryText('無變化 —', 'No change —');
        return difference > 0
          ? summaryText(`上升${Math.abs(difference).toFixed(1)}個百分點 ▲`, `Increase by ${Math.abs(difference).toFixed(1)} percentage points ▲`)
          : summaryText(`下降${Math.abs(difference).toFixed(1)}個百分點 ▼`, `Decrease by ${Math.abs(difference).toFixed(1)} percentage points ▼`);
      };
      const mainRangeTotal = summaryCount(data.main?.total_count);
      const targetRangeTotal = summaryCount(data.target?.total_count);
      document.getElementById('compareResultSummary').innerHTML = `
        <div class="compare-summary-card">
          <div class="compare-summary-label">${summaryText('年平均個案數差異', 'Annual Average Case Difference')}</div>
          <div class="compare-summary-value ${valueClass(annualAverageDiff)}">${changeNumberText(annualAverageDiff, '人／年')}${summaryParentheses(`${annualAveragePercent > 0 ? '+' : annualAveragePercent < 0 ? '−' : ''}${Math.abs(annualAveragePercent).toFixed(1)}%`)}</div>
          <div class="compare-summary-period-detail">${mainPeriodLabel} ${mainAnnualAverage.toFixed(1)}${summaryText('人／年', ' cases/year')} → ${targetPeriodLabel} ${targetAnnualAverage.toFixed(1)}${summaryText('人／年', ' cases/year')}</div>
          <div class="compare-summary-period-detail compare-summary-period-detail-next">${summaryText('區間總數：', 'Period total: ')}${mainRangeTotal} → ${targetRangeTotal}</div>
        </div>
        <div class="compare-summary-card">
          <div class="compare-summary-label">${summaryText('年齡層分布差異', 'Age Distribution Difference')}</div>
          <div class="compare-summary-age-row">
            <span class="compare-summary-age-group">${escapeHtml(ageGroupLabel)}</span>
            <span class="compare-summary-age-change ${valueClass(ageShareDiff)}">${percentagePointChangeText(ageShareDiff)}</span>
          </div>
          <div class="compare-summary-period-values">${mainPeriodLabel} ${summaryCount(biggest.mainCount)}${summaryParentheses(`${mainAgeShare.toFixed(1)}%`)} → ${targetPeriodLabel} ${summaryCount(biggest.targetCount)}${summaryParentheses(`${targetAgeShare.toFixed(1)}%`)}</div>
        </div>
        <div class="compare-summary-card">
          <div class="compare-summary-label">${summaryText('性別分布差異', 'Sex Distribution Difference')}</div>
          <div class="compare-summary-gender-primary compare-summary-range-gender-primary">
            <span class="${shareValueClass(maleShareDiff)}">${summaryText('男', 'Male')} ${percentagePointChangeText(maleShareDiff)}</span>
            <span class="compare-summary-divider">｜</span>
            <span class="${shareValueClass(femaleShareDiff)}">${summaryText('女', 'Female')} ${percentagePointChangeText(femaleShareDiff)}</span>
          </div>
          <div class="compare-summary-period-detail compare-summary-period-comparison compare-summary-range-gender-detail">${rangePeriodComparison(summaryText('男：', 'Male: '), `${mainPeriodLabel} ${summaryCount(mainAge.male_count)}${summaryParentheses(`${mainMaleShare.toFixed(1)}%`)}`, `${targetPeriodLabel} ${summaryCount(targetAge.male_count)}${summaryParentheses(`${targetMaleShare.toFixed(1)}%`)}`)}</div>
          <div class="compare-summary-period-detail compare-summary-period-detail-next compare-summary-period-comparison compare-summary-range-gender-detail">${rangePeriodComparison(summaryText('女：', 'Female: '), `${mainPeriodLabel} ${summaryCount(mainAge.female_count)}${summaryParentheses(`${mainFemaleShare.toFixed(1)}%`)}`, `${targetPeriodLabel} ${summaryCount(targetAge.female_count)}${summaryParentheses(`${targetFemaleShare.toFixed(1)}%`)}`)}</div>
        </div>
        <div class="compare-summary-card">
          <div class="compare-summary-label">${summaryText('中位年齡層差異', 'Median Age Group Difference')}<span class="compare-summary-label-note">${summaryText('（依區間內全體個案的年齡層分布判定）', ' (based on the age distribution of all cases in each period)')}</span></div>
          <div class="compare-summary-median-change ${valueClass(medianGroupDiff)}">${medianGroupChangeText}</div>
          <div class="compare-summary-median-period">${mainPeriodLabel} ${escapeHtml(mainMedianGroup.label)} → ${targetPeriodLabel} ${escapeHtml(targetMedianGroup.label)}</div>
        </div>
      `;
      return;
    }
    document.getElementById('compareResultSummary').innerHTML = `
      <div class="compare-summary-card">
        <div class="compare-summary-label">${summaryText('總個案數差異', 'Total Case Difference')}</div>
        <div class="compare-summary-value ${valueClass(totalDiff)}">${changeNumberText(totalDiff, '人')}${summaryParentheses(signedPercentText(data.main?.total_count, data.target?.total_count))}</div>
        <div class="compare-summary-period-detail">${mainPeriodLabel} ${summaryCount(data.main?.total_count)} → ${targetPeriodLabel} ${summaryCount(data.target?.total_count)}</div>
      </div>
      <div class="compare-summary-card">
        <div class="compare-summary-label">${summaryText('年齡層個案數差異', 'Largest Case Difference by Age')}</div>
        <div class="compare-summary-age-row">
          <span class="compare-summary-age-group">${escapeHtml(ageGroupLabel)}</span>
          <span class="compare-summary-age-change ${valueClass(biggest.value)}">${changeNumberText(biggest.value, '人')}${summaryParentheses(ageShareDiffText)}</span>
        </div>
        <div class="compare-summary-period-values">${escapeHtml(formatPeriod(data.main?.year_label, '基準期', 'Baseline'))} ${summaryCount(biggest.mainCount)}${summaryParentheses(`${mainAgeShare.toFixed(1)}%`)} → ${escapeHtml(formatPeriod(data.target?.year_label, '比較期', 'Comparison'))} ${summaryCount(biggest.targetCount)}${summaryParentheses(`${targetAgeShare.toFixed(1)}%`)}</div>
      </div>
      <div class="compare-summary-card">
        <div class="compare-summary-label">${summaryText('性別個案數差異', 'Case Difference by Sex')}</div>
        <div class="compare-summary-gender-primary"><span class="${valueClass(maleCountDiff)}">${summaryText('男', 'Male')} ${changeNumberText(maleCountDiff, '人')}</span> <span class="${shareValueClass(maleShareDiff)}">${summaryParentheses(shareChangeText(mainMaleShare, targetMaleShare))}</span><span class="compare-summary-divider">｜</span><span class="${valueClass(femaleCountDiff)}">${summaryText('女', 'Female')} ${changeNumberText(femaleCountDiff, '人')}</span> <span class="${shareValueClass(femaleShareDiff)}">${summaryParentheses(shareChangeText(mainFemaleShare, targetFemaleShare))}</span></div>
        <div class="compare-summary-period-detail">${summaryText('男：', 'Male: ')}${mainPeriodLabel} ${summaryCount(mainAge.male_count)}${summaryParentheses(`${mainMaleShare.toFixed(1)}%`)} → ${targetPeriodLabel} ${summaryCount(targetAge.male_count)}${summaryParentheses(`${targetMaleShare.toFixed(1)}%`)}</div>
        <div class="compare-summary-period-detail compare-summary-period-detail-next">${summaryText('女：', 'Female: ')}${mainPeriodLabel} ${summaryCount(mainAge.female_count)}${summaryParentheses(`${mainFemaleShare.toFixed(1)}%`)} → ${targetPeriodLabel} ${summaryCount(targetAge.female_count)}${summaryParentheses(`${targetFemaleShare.toFixed(1)}%`)}</div>
      </div>
      <div class="compare-summary-card">
        <div class="compare-summary-label">${summaryText('中位年齡層差異', 'Median Age Group Difference')}<span class="compare-summary-label-note">${summaryText('（依全體個案的年齡層分布判定）', ' (based on the age distribution of all cases)')}</span></div>
        <div class="compare-summary-median-change ${valueClass(medianGroupDiff)}">${medianGroupChangeText}</div>
        <div class="compare-summary-median-period">${mainPeriodLabel} ${escapeHtml(mainMedianGroup.label)} → ${targetPeriodLabel} ${escapeHtml(targetMedianGroup.label)}</div>
      </div>
    `;
  }

  function renderAnnualReport(containerId, chartData, meta, chartPrefix, item, side, sharedScale, activeStageSystem = '') {
    const container = document.getElementById(containerId);
    container.innerHTML = reportBlock(item, chartData, meta, chartPrefix, activeStageSystem);
    bindViewSwitch(container, side);
    const viewSwitch = container.querySelector('.compare-view-switch');
    const resultHeading = container.closest('.compare-result-item')?.querySelector('.compare-result-heading');
    if (viewSwitch && resultHeading) resultHeading.appendChild(viewSwitch);
    if (item === '性別年齡分佈') renderSexAgeChart(`${chartPrefix}SexAgeChart`, chartData, sharedScale, meta.year_label, selectedCancerTitle());
    if (item === '組織型態') {
      renderHistologyChart(`${chartPrefix}HistologyChart`, chartData, meta.year_label, selectedCancerTitle(), sharedScale);
    }
    if (item === '個案分類') renderClassificationChart(`${chartPrefix}ClassificationChart`, chartData, sharedScale, meta.year_label, selectedCancerTitle());
    if ((chartData?.stageReports || []).some(report => report.option === item)) {
      renderStageChart(`${chartPrefix}StageChart`, chartData, meta.year_label, selectedCancerTitle(), item);
    }
  }

  function renderResultItem(data, item, index) {
    activeResultIndex = index;
    const stageOptions = selectedStageReportOptions();
    const isStageGroup = item === stageResultGroupItem;
    if (isStageGroup && !stageOptions.includes(activeStageReportOption)) {
      activeStageReportOption = stageOptions[0] || '';
    }
    const activeItem = activeComparisonItem(item);
    alignStageComparisonReports(data, activeItem);
    renderDifferenceSummary(data, activeItem);
    document.querySelectorAll('.compare-result-tab').forEach((button, buttonIndex) => {
      button.classList.toggle('active', buttonIndex === index);
    });

    const sharedScale = calculateSharedScale(data);
    const isTreatmentFirstCourse = activeItem === '期別與首次療程';
    const treatmentSystems = Array.from(new Set([
      ...(data.analysis_data?.main?.stageFirstCourseData || []).map(table => table.system),
      ...(data.analysis_data?.target?.stageFirstCourseData || []).map(table => table.system)
    ]));
    if (isTreatmentFirstCourse && !treatmentSystems.includes(activeTreatmentStageSystem)) {
      activeTreatmentStageSystem = treatmentSystems[0] || '';
    }
    const treatmentTabs = isTreatmentFirstCourse && treatmentSystems.length > 1
      ? `<div class="d-flex flex-wrap gap-2 mb-3" role="tablist">${treatmentSystems.map(system => `<button type="button" class="btn btn-outline-dark btn-sm compare-treatment-stage-tab${system === activeTreatmentStageSystem ? ' active' : ''}" data-stage-system="${escapeHtml(system)}">${escapeHtml(system)}${isEnglish() ? ' Stage' : '期別'}</button>`).join('')}</div>`
      : '';
    const stageTabs = isStageGroup && stageOptions.length > 1
      ? `<div class="d-flex flex-wrap gap-2 mb-3" role="tablist">${stageOptions.map(option => `<button type="button" class="btn btn-outline-dark btn-sm compare-stage-report-tab${option === activeStageReportOption ? ' active' : ''}" data-stage-option="${escapeHtml(option)}">${escapeHtml(option)}</button>`).join('')}</div>`
      : '';
    document.getElementById('compareResultPanel').innerHTML = `
      ${stageTabs}
      ${treatmentTabs}
      <div class="compare-result-grid">
        <section class="compare-result-item is-main">
          <div class="compare-result-heading"><div><h3>${isEnglish() ? 'Baseline period' : '基準期資料'}｜${escapeHtml(data.main?.year_label || '—')}</h3></div></div>
          <div id="mainAnnualReport"></div>
        </section>
        <section class="compare-result-item is-target">
          <div class="compare-result-heading"><div><h3>${isEnglish() ? 'Comparison period' : '比較期資料'}｜${escapeHtml(data.target?.year_label || '—')}</h3></div></div>
          <div id="targetAnnualReport"></div>
        </section>
      </div>
    `;

    renderAnnualReport('mainAnnualReport', data.analysis_data?.main || {}, data.main, `main${index}`, activeItem, 'main', sharedScale, activeTreatmentStageSystem);
    renderAnnualReport('targetAnnualReport', data.analysis_data?.target || {}, data.target, `target${index}`, activeItem, 'target', sharedScale, activeTreatmentStageSystem);
    document.querySelectorAll('.compare-treatment-stage-tab').forEach(button => {
      button.addEventListener('click', () => {
        activeTreatmentStageSystem = button.dataset.stageSystem || '';
        renderResultItem(data, item, index);
        renderAiNarrative(data, activeComparisonItem(item));
      });
    });
    document.querySelectorAll('.compare-stage-report-tab').forEach(button => {
      button.addEventListener('click', () => {
        activeStageReportOption = button.dataset.stageOption || '';
        renderResultItem(data, item, index);
        renderAiNarrative(data, activeStageReportOption);
      });
    });
  }

  function buildAiComparisonPayload(data, analysisItem) {
    const pickAnalysis = analysis => {
      const selectedAnalysis = {};
      if (analysisItem === '性別年齡分佈') selectedAnalysis.gender_age = analysis?.genderAgeData || {};
      if (analysisItem === '年齡中位數') selectedAnalysis.age_median = analysis?.ageMedianData || {};
      if (analysisItem === '可分析個案與確診個案') selectedAnalysis.analyzable_confirmed = analysis?.analyzableConfirmedData || {};
      if (analysisItem === '組織型態') {
        selectedAnalysis.histology = (analysis?.histologyData || []).filter(item => item.name !== 'Unknown / 未對應組織型態');
        selectedAnalysis.no_data_reason = analysis?.histologyNoDataReason || '';
      }
      if (analysisItem === '個案分類') selectedAnalysis.diagnosis_classification = analysis?.diagnosisClassificationData || {};
      if (analysisItem === '期別與首次療程') {
        const tables = analysis?.stageFirstCourseData || [];
        selectedAnalysis.stage_first_course = tables.find(table => table.system === activeTreatmentStageSystem) || tables[0] || {};
      }
      const stageReport = (analysis?.stageReports || []).find(report => report.option === analysisItem);
      if (stageReport) selectedAnalysis.stage_report = stageReport;
      return selectedAnalysis;
    };
    return {
      comparison_definition: '所有差異均以比較期資料減去基準期資料計算；正值代表比較期資料較高，負值代表比較期資料較低。',
      comparison_direction: `${data.target?.year_label || '比較期年度'}相較於${data.main?.year_label || '基準期年度'}`,
      selected_conditions: {
        behavior: behavior.selectedOptions[0]?.textContent?.trim() || '',
        cancer: selectedCancerTitle(),
        analysis_item: analysisItem
      },
      baseline: {
        year: data.main?.year_label,
        total_count: data.main?.total_count,
        annual_average: data.main?.annual_average,
        yearly_counts: data.main?.yearly_counts,
        analysis: pickAnalysis(data.analysis_data?.main)
      },
      comparison: {
        year: data.target?.year_label,
        total_count: data.target?.total_count,
        annual_average: data.target?.annual_average,
        yearly_counts: data.target?.yearly_counts,
        analysis: pickAnalysis(data.analysis_data?.target)
      },
      total_difference: data.diff || {}
    };
  }

  function aiNarrativeCacheKey(analysisItem) {
    const stageSystem = analysisItem === '期別與首次療程' ? `|${activeTreatmentStageSystem}` : '';
    return `${window.DashboardI18n?.getLanguage() || 'zh-TW'}|${analysisItem}${stageSystem}`;
  }

  function fetchAiNarrative(data, analysisItem, force = false) {
    const stageSystemAtRequest = analysisItem === '期別與首次療程' ? activeTreatmentStageSystem : '';
    const language = window.DashboardI18n?.getLanguage() || 'zh-TW';
    const cacheKey = `${language}|${analysisItem}${stageSystemAtRequest ? `|${stageSystemAtRequest}` : ''}`;
    if (!force && aiNarrativeCache.has(cacheKey)) {
      return Promise.resolve(aiNarrativeCache.get(cacheKey));
    }

    const comparisonPayload = buildAiComparisonPayload(data, analysisItem);
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), aiNarrativeTimeoutMs);
    return fetch('/api/dashboard/compare_insight', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        analysis_item: analysisItem,
        comparison_direction: comparisonPayload.comparison_direction,
        selected_conditions: comparisonPayload.selected_conditions,
        baseline: comparisonPayload.baseline,
        comparison: comparisonPayload.comparison,
        total_difference: comparisonPayload.total_difference,
        mode_ai: modeAi.value,
        language: window.DashboardI18n?.getLanguage() || 'zh-TW'
      })
    })
      .then(response => response.json())
      .then(result => {
        if (!result.success) throw new Error(result.error || '語言模型分析產生失敗');
        const insight = result.insight || '語言模型未回傳分析內容。';
        const insights = result.insights || {};
        Object.entries(insights).forEach(([insightLanguage, value]) => aiNarrativeCache.set(`${insightLanguage}|${analysisItem}${stageSystemAtRequest ? `|${stageSystemAtRequest}` : ''}`, value));
        aiNarrativeCache.set(cacheKey, insight);
        return insight;
      })
      .catch(error => {
        const errorText = error.name === 'AbortError'
          ? '語言模型比較敘述產生逾時，請稍後重試。'
          : '語言模型比較敘述暫時無法產生，請確認模型服務設定或稍後再試。';
        aiNarrativeCache.set(cacheKey, errorText);
        return errorText;
      })
      .finally(() => window.clearTimeout(timeoutId));
  }

  function renderAiNarrative(data, analysisItem, force = false) {
    const section = document.getElementById('compareAiNarrative');
    const text = document.getElementById('compareAiNarrativeText');
    const retryButton = document.getElementById('btnRetryAiNarrative');
    activeAiNarrativeItem = analysisItem;
    section.classList.remove('d-none');
    retryButton.disabled = true;
    const cacheKey = aiNarrativeCacheKey(analysisItem);
    if (!force && aiNarrativeCache.has(cacheKey)) {
      text.textContent = aiNarrativeCache.get(cacheKey);
      retryButton.disabled = false;
      return Promise.resolve(aiNarrativeCache.get(cacheKey));
    }
    const requestId = ++aiNarrativeRequestId;
    text.innerHTML = '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>正在產生 LLM 敘述，請稍候…';

    return fetchAiNarrative(data, analysisItem, force)
      .then(insight => {
        if (requestId === aiNarrativeRequestId && activeAiNarrativeItem === analysisItem) text.textContent = insight;
      })
      .finally(() => {
        if (requestId === aiNarrativeRequestId && activeAiNarrativeItem === analysisItem) retryButton.disabled = false;
      });
  }

  function renderRangeTrend(data) {
    const container = document.getElementById('compareRangeTrend');
    if (data.compare_mode !== 'range') {
      container.classList.add('d-none');
      return;
    }
    container.classList.remove('d-none');
    const mainCounts = data.main?.yearly_counts || {};
    const targetCounts = data.target?.yearly_counts || {};
    const years = Array.from(new Set([...Object.keys(mainCounts), ...Object.keys(targetCounts)]))
      .sort((a, b) => Number(a) - Number(b));

    const baselineLabel = isEnglish() ? 'Baseline period' : '基準期';
    const comparisonLabel = isEnglish() ? 'Comparison period' : '比較期';
    const chart = echarts.getInstanceByDom(container) || echarts.init(container);
    chart.setOption({
      color: ['#166534', '#c2410c'],
      title: {
        text: isEnglish() ? 'Annual Case Count Trend' : '年度區間個案數趨勢',
        left: 'center',
        top: 18,
        textStyle: { fontSize: 18 }
      },
      tooltip: { trigger: 'axis' },
      legend: { top: 52, data: [`${baselineLabel} ${data.main?.year_label || ''}`, `${comparisonLabel} ${data.target?.year_label || ''}`] },
      grid: { left: 50, right: 35, top: 92, bottom: 30, containLabel: true },
      xAxis: {
        type: 'category',
        name: isEnglish() ? 'Year' : '年度',
        nameLocation: 'middle',
        nameGap: 30,
        data: years,
        boundaryGap: true,
        axisTick: { alignWithLabel: true },
        axisLabel: { margin: 10 }
      },
      yAxis: { type: 'value', name: isEnglish() ? 'Cases' : '個案數', minInterval: 1 },
      series: [
        {
          name: `${baselineLabel} ${data.main?.year_label || ''}`,
          type: 'line',
          connectNulls: false,
          triggerLineEvent: true,
          symbol: 'circle',
          symbolSize: 8,
          lineStyle: { type: 'solid', width: 3, color: '#166534' },
          itemStyle: { color: '#166534' },
          emphasis: {
            focus: 'series',
            scale: 1.5,
            lineStyle: { type: 'solid', width: 5, color: '#166534', opacity: 1 },
            itemStyle: { color: '#166534', borderColor: '#fff', borderWidth: 2, opacity: 1 }
          },
          blur: {
            lineStyle: { opacity: 0.18 },
            itemStyle: { opacity: 0.18 },
            label: { opacity: 0.18 }
          },
          label: { show: true, position: 'top' },
          data: years.map(year => Object.prototype.hasOwnProperty.call(mainCounts, year) ? mainCounts[year] : null)
        },
        {
          name: `${comparisonLabel} ${data.target?.year_label || ''}`,
          type: 'line',
          connectNulls: false,
          triggerLineEvent: true,
          symbol: 'circle',
          symbolSize: 8,
          lineStyle: { type: 'solid', width: 3, color: '#c2410c' },
          itemStyle: { color: '#c2410c' },
          emphasis: {
            focus: 'series',
            scale: 1.5,
            lineStyle: { type: 'solid', width: 5, color: '#c2410c', opacity: 1 },
            itemStyle: { color: '#c2410c', borderColor: '#fff', borderWidth: 2, opacity: 1 }
          },
          blur: {
            lineStyle: { opacity: 0.18 },
            itemStyle: { opacity: 0.18 },
            label: { opacity: 0.18 }
          },
          label: { show: true, position: 'top' },
          data: years.map(year => Object.prototype.hasOwnProperty.call(targetCounts, year) ? targetCounts[year] : null)
        }
      ]
    }, true);
    setTimeout(() => chart.resize(), 0);
  }

  function renderResult(data) {
    const items = comparisonResultItems();
    lastComparisonData = data;
    hasRenderedResult = true;
    resultStale.classList.add('d-none');
    renderRangeTrend(data);
    const tabs = document.getElementById('compareResultTabs');
    tabs.innerHTML = items.map((item, index) => `
      <button type="button" class="compare-result-tab ${index === 0 ? 'active' : ''}" data-index="${index}">${comparisonItemTitle(item)}</button>
    `).join('');
    tabs.querySelectorAll('.compare-result-tab').forEach(button => {
      button.addEventListener('click', () => {
        const index = Number(button.dataset.index);
        renderResultItem(data, items[index], index);
        renderAiNarrative(data, activeComparisonItem(items[index]));
      });
    });

    if (items.length > 0) renderResultItem(data, items[0], 0);
    resultBox.classList.remove('d-none');
    if (items.length > 0) renderAiNarrative(data, activeComparisonItem(items[0]));
  }

  window.DashboardCompare = {
    rerenderCompareLanguage() {
      const languageLabel = document.getElementById('compareLanguageLabel');
      if (languageLabel) languageLabel.textContent = isEnglish() ? 'English' : '繁體中文';
      const narrativeHeading = document.querySelector('#compareAiNarrative h6');
      if (narrativeHeading) narrativeHeading.textContent = t('llmInsight');
      const retryButton = document.getElementById('btnRetryAiNarrative');
      if (retryButton) retryButton.innerHTML = `<i class="bi bi-arrow-clockwise me-1"></i>${t('regenerateInsight')}`;
      if (!lastComparisonData || !hasRenderedResult) return;
      const items = comparisonResultItems();
      const item = items[activeResultIndex] || items[0];
      if (!item) return;
      renderRangeTrend(lastComparisonData);
      renderResultItem(lastComparisonData, item, activeResultIndex);
      renderAiNarrative(lastComparisonData, activeComparisonItem(item));
    }
  };

  function showAlert(title, text) {
    if (window.Swal) Swal.fire({ icon: 'warning', title, text, confirmButtonColor: '#2563eb' });
    else window.utils?.alert(text || title, 'warning');
  }

  function resetComparison() {
    behavior.selectedIndex = 0;
    modeAi.value = 'balanced';
    document.querySelectorAll('.cancer-cb-leaf, .cancer-cb-subgroup, .cancer-cb-group').forEach(input => {
      input.checked = false;
      input.indeterminate = false;
    });
    window.selectedCancers = new Set();
    window.dashboardSelectedCancerIds = [];
    window.dashboardSelectedCancerTitle = 'XX';
    const cancerPickerText = document.getElementById('btnCancerPickerText');
    if (cancerPickerText) cancerPickerText.textContent = '— 尚未選擇癌別 —';

    document.querySelectorAll('input[name="compareType"]').forEach(input => {
      input.checked = false;
    });
    document.querySelectorAll('.compare-subitem-check').forEach(input => {
      input.checked = false;
    });
    hasRenderedResult = false;
    lastComparisonData = null;
    activeAiNarrativeItem = '';
    aiNarrativeRequestId += 1;
    aiNarrativeCache.clear();
    resultStale.classList.add('d-none');
    resultBox.classList.add('d-none');
    document.getElementById('compareResultSummary').replaceChildren();
    document.getElementById('compareResultTabs').replaceChildren();
    document.getElementById('compareResultPanel').replaceChildren();
    document.getElementById('compareAiNarrative').classList.add('d-none');
    document.getElementById('compareAiNarrativeText').textContent = '';

    renderCompareSubItems();
    updateButtonState();
  }

  function updateCompareMode() {
    const isRange = selectedCompareMode() === 'range';
    clearDataSelection(mainFile, mainYear, mainYearEnd, mainMeta, mainPreview, '基準期資料預覽');
    clearDataSelection(targetFile, targetYear, targetYearEnd, targetMeta, targetPreview, '比較期資料預覽');
    document.getElementById('compareDataGrid').classList.toggle('is-range-mode', isRange);
    document.getElementById('mainYearEndGroup').classList.toggle('d-none', !isRange);
    document.getElementById('targetYearEndGroup').classList.toggle('d-none', !isRange);
    document.getElementById('mainYearLabel').textContent = isRange ? '起始年度' : '年度';
    document.getElementById('targetYearLabel').textContent = isRange ? '起始年度' : '年度';
    resetComparison();
  }

  function clearDataSelection(fileSelect, yearSelect, yearEndSelect, metaElement, previewElement, emptyText) {
    fileSelect.selectedIndex = 0;
    [yearSelect, yearEndSelect].forEach(select => {
      select.innerHTML = '<option value="" selected>尚未選擇</option>';
      select.disabled = true;
    });
    metaElement.textContent = '尚未選擇檔案';
    showPreviewMessage(previewElement, emptyText);
    previewElement.classList.add('d-none');
    const previewButton = document.querySelector(`[data-preview-target="${previewElement.id}"]`);
    if (previewButton) {
      previewButton.classList.add('d-none');
      previewButton.textContent = '查看資料預覽';
    }
    if (fileSelect === mainFile) mainYears = [];
    if (fileSelect === targetFile) targetYears = [];
  }

  function reselectData(fileSelect, yearSelect, yearEndSelect, metaElement, previewElement, emptyText) {
    resetComparison();
    clearDataSelection(fileSelect, yearSelect, yearEndSelect, metaElement, previewElement, emptyText);
    updateButtonState();
    fileSelect.focus();

  }

  mainFile.addEventListener('change', () => detectYears(mainFile, mainYear, mainPreview));
  targetFile.addEventListener('change', () => detectYears(targetFile, targetYear, targetPreview));
  document.querySelectorAll('.compare-preview-toggle').forEach(button => {
    button.addEventListener('click', () => {
      const preview = document.getElementById(button.dataset.previewTarget);
      const willShow = preview.classList.contains('d-none');
      preview.classList.toggle('d-none', !willShow);
      button.textContent = willShow ? '收合資料預覽' : '查看資料預覽';
    });
  });
  mainYear.addEventListener('change', () => {
    markResultsStale();
    refreshYearPreview(mainFile, mainYear, mainYearEnd, mainPreview);
    updateButtonState();
  });
  targetYear.addEventListener('change', () => {
    markResultsStale();
    refreshYearPreview(targetFile, targetYear, targetYearEnd, targetPreview);
    updateButtonState();
  });
  mainYearEnd.addEventListener('change', () => {
    markResultsStale();
    refreshYearPreview(mainFile, mainYear, mainYearEnd, mainPreview);
    updateButtonState();
  });
  targetYearEnd.addEventListener('change', () => {
    markResultsStale();
    refreshYearPreview(targetFile, targetYear, targetYearEnd, targetPreview);
    updateButtonState();
  });
  document.querySelectorAll('input[name="compareMode"]').forEach(input => {
    input.addEventListener('change', updateCompareMode);
  });
  behavior.addEventListener('change', () => { markResultsStale(); updateButtonState(); });
  modeAi.addEventListener('change', () => {
    aiNarrativeCache.clear();
    updateSelectionSummary();
    if (lastComparisonData && activeAiNarrativeItem) {
      renderAiNarrative(lastComparisonData, activeAiNarrativeItem, true);
    }
  });
  document.getElementById('btnConfirmCancer')?.addEventListener('click', () => { markResultsStale(); updateButtonState(); });
  document.querySelectorAll('input[name="compareType"]').forEach(input => {
    input.addEventListener('change', () => {
      markResultsStale();
      renderCompareSubItems();
      updateButtonState();
    });
  });
  document.querySelectorAll('.compare-subitem-check').forEach(input => {
    input.addEventListener('change', () => {
      markResultsStale();
      updateButtonState();
    });
  });
  document.querySelectorAll('.compare-stage-option').forEach(input => {
    input.addEventListener('change', () => {
      markResultsStale();
      updateButtonState();
    });
  });
  document.getElementById('btnSelectAllCompareItems').addEventListener('click', () => {
    if (selectedCompareType() === 'stage') {
      const summary = document.getElementById('compareItemStageSummary');
      const detailed = document.getElementById('compareItemStageDetailed');
      if (!summary?.checked && !detailed?.checked && summary && !summary.disabled) summary.checked = true;
      updateCompareStageOptions();
      document.querySelectorAll('.compare-stage-option:not(:disabled)').forEach(input => { input.checked = true; });
    } else {
      document.querySelectorAll('.compare-subitem-check:not(:disabled):not(.compare-stage-system-checkbox)')
        .forEach(input => { input.checked = true; });
    }
    markResultsStale();
    updateButtonState();
  });
  document.getElementById('btnClearCompareItems').addEventListener('click', () => {
    document.querySelectorAll('.compare-subitem-check').forEach(input => { input.checked = false; });
    document.querySelectorAll('.compare-stage-option').forEach(input => { input.checked = false; });
    markResultsStale();
    updateButtonState();
  });
  document.getElementById('btnRetryAiNarrative').addEventListener('click', () => {
    if (lastComparisonData && activeAiNarrativeItem) renderAiNarrative(lastComparisonData, activeAiNarrativeItem, true);
  });
  resetButton.addEventListener('click', resetComparison);
  document.getElementById('btnReselectMain').addEventListener('click', () => {
    reselectData(mainFile, mainYear, mainYearEnd, mainMeta, mainPreview, '基準期資料預覽');
  });
  document.getElementById('btnReselectTarget').addEventListener('click', () => {
    reselectData(targetFile, targetYear, targetYearEnd, targetMeta, targetPreview, '比較期資料預覽');
  });
  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(updateButtonState, 0);
    const languagePicker = document.getElementById('compareLanguagePicker');
    document.querySelectorAll('[data-compare-language]').forEach(option => {
      option.addEventListener('click', () => {
        if (languagePicker) languagePicker.open = false;
        window.DashboardI18n?.setLanguage(option.dataset.compareLanguage);
      });
    });
    window.DashboardCompare.rerenderCompareLanguage();
  });

  runButton.addEventListener('click', () => {
    if (selectedCompareMode() === 'range'
        && (Number(mainYear.value) > Number(mainYearEnd.value)
          || Number(targetYear.value) > Number(targetYearEnd.value))) {
      showAlert('年度區間不正確', '起始年度不可晚於結束年度。');
      return;
    }
    if (!filesReady()) {
      showAlert('資料不可相同', '基準期資料與比較期資料不可使用相同檔案及相同年度。');
      return;
    }
    if (!behavior.value) {
      showAlert('尚未選擇性態碼', '請先選擇性態碼後再開始比較。');
      return;
    }
    if (selectedCancerValues().length === 0) {
      showAlert('尚未選擇癌別', '請至少選擇一個癌別後再開始比較。');
      return;
    }
    if (selectedCompareItems().length === 0) {
      showAlert('尚未選擇分析項目', '請至少選擇一個分析項目後再開始比較。');
      return;
    }
    if (selectedCompareType() === 'stage') {
      const stageOptions = selectedCompareStageOptions();
      if (!stageOptions.mode) {
        showAlert('尚未選擇期別模式', '請先選擇「分期呈現最細碼」或「分期不呈現最細碼」。');
        return;
      }
      if (stageOptions.options.length === 0) {
        showAlert('尚未選擇期別報表', '請至少選擇一個分期系統的期別表圖。');
        return;
      }
    }
    [mainPreview, targetPreview].forEach(preview => preview.classList.add('d-none'));
    document.querySelectorAll('.compare-preview-toggle').forEach(button => { button.textContent = '查看資料預覽'; });
    resultBox.classList.add('d-none');
    runButton.disabled = true;
    runButton.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> 資料分析中，請稍候…';
    if (window.utils && window.utils.showLoading) {
      window.utils.showLoading('資料分析中，請稍候…');
    }
    const compareItems = selectedCompareItems();
    const stageOptions = [...selectedCompareStageOptions().options];
    if (compareItems.includes('期別與首次療程')) {
      treatmentStageOptions().forEach(option => {
        if (!stageOptions.some(selected => selected.system === option.system && selected.option === option.option)) {
          stageOptions.push(option);
        }
      });
    }
    fetch('/api/dashboard/compare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        main_file_id: mainFile.value,
        target_file_id: targetFile.value,
        main_year: mainYear.value,
        target_year: targetYear.value,
        main_year_end: selectedCompareMode() === 'range' ? mainYearEnd.value : mainYear.value,
        target_year_end: selectedCompareMode() === 'range' ? targetYearEnd.value : targetYear.value,
        compare_mode: selectedCompareMode(),
        behavior: behavior.value,
        cancers: selectedCancerValues(),
        compare_type: selectedCompareType(),
        compare_items: compareItems,
        stage_options: stageOptions
      })
    })
      .then(r => r.json())
      .then(data => {
        if (!data.ok) throw new Error(data.error || '比較失敗');
        const items = selectedCompareItems();
        aiNarrativeCache.clear();
        const treatmentSystems = Array.from(new Set([
          ...(data.data.analysis_data?.main?.stageFirstCourseData || []).map(table => table.system),
          ...(data.data.analysis_data?.target?.stageFirstCourseData || []).map(table => table.system)
        ]));
        const originalTreatmentSystem = activeTreatmentStageSystem;
        const narrativeRequests = items.flatMap(item => {
          if (item !== '期別與首次療程') return [{ item, stageSystem: '' }];
          return treatmentSystems.length
            ? treatmentSystems.map(stageSystem => ({ item, stageSystem }))
            : [{ item, stageSystem: '' }];
        });
        let completedNarratives = 0;
        const updateNarrativeProgress = () => {
          if (window.utils && window.utils.showLoading) {
            window.utils.showLoading(`正在產生 LLM 敘述（${completedNarratives}/${narrativeRequests.length}）…`);
          }
        };
        updateNarrativeProgress();
        return narrativeRequests.reduce((chain, { item, stageSystem }) => chain.then(() => {
          activeTreatmentStageSystem = stageSystem;
          return fetchAiNarrative(data.data, item).finally(() => {
            completedNarratives += 1;
            updateNarrativeProgress();
          });
        }), Promise.resolve())
          .then(() => {
            activeTreatmentStageSystem = originalTreatmentSystem;
            renderResult(data.data);
            setTimeout(() => resultBox.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50);
          });
      })
      .catch(err => showAlert('比較失敗', err.message))
      .finally(() => {
        if (window.utils && window.utils.hideLoading) window.utils.hideLoading();
        runButton.innerHTML = '<i class="bi bi-columns-gap me-1"></i> 開始比較';
        updateButtonState();
      });
  });

  renderCompareSubItems();
  updateButtonState();
})();
