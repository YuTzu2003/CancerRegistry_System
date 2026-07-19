(function() {
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
  const aiNarrativeCache = new Map();
  const viewPreferences = { main: 'chart', target: 'chart' };
  const customYearControls = new Map();
  const yearSelects = [mainYear, mainYearEnd, targetYear, targetYearEnd];

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

  function selectedCompareItems() {
    return Array.from(document.querySelectorAll('.compare-subitem-check:checked')).map(input => input.value);
  }

  function markResultsStale() {
    if (hasRenderedResult) resultStale.classList.remove('d-none');
  }

  function selectedCancerValues() {
    return Array.from(window.selectedCancers || []);
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

  function setSettingsEnabled() {
    const filesAreReady = filesReady();
    const behaviorIsReady = filesAreReady && Boolean(behavior.value);
    const cancerIsReady = behaviorIsReady && selectedCancerValues().length > 0;
    const topicIsSelected = cancerIsReady && Boolean(selectedCompareType());
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
    document.getElementById('btnSelectAllCompareItems').disabled = !topicIsSelected;
    document.getElementById('btnClearCompareItems').disabled = !topicIsSelected;
    analysisStep?.classList.toggle('opacity-50', !cancerIsReady);
    analysisStep?.classList.toggle('pe-none', !cancerIsReady);

    return { filesAreReady, behaviorIsReady, cancerIsReady };
  }

  function updateButtonState() {
    const state = setSettingsEnabled();
    runButton.disabled = !(state.cancerIsReady && selectedCompareItems().length > 0);
    updateTopicCounts();
    updateSelectionSummary();
  }

  function updateSelectionSummary() {
    const formatDataSelection = (fileSelect, yearSelect, yearEndSelect) => {
      if (!fileSelect.value && !yearSelect.value) return '尚未選擇';
      const fileText = fileSelect.value || '尚未選擇檔案';
      const yearTextValue = yearSelect.value || '尚未選擇年度';
      const period = selectedCompareMode() === 'range' && yearEndSelect.value
        ? `${yearTextValue}–${yearEndSelect.value}` : yearTextValue;
      return `${fileText}｜${period}`;
    };
    const behaviorText = behavior.value ? behavior.selectedOptions[0]?.textContent?.trim() : '尚未選擇';
    const selectedCancerTitle = String(window.dashboardSelectedCancerTitle || '').trim();
    const cancerText = selectedCancerValues().length
      ? (selectedCancerTitle && selectedCancerTitle !== 'XX' ? selectedCancerTitle : `${selectedCancerValues().length} 個癌別`)
      : '尚未選擇';
    const items = selectedCompareItems();

    document.getElementById('summaryCompareMode').textContent = selectedCompareMode() === 'range' ? '年度區間比較' : '單一年度比較';
    document.getElementById('summaryMainData').textContent = formatDataSelection(mainFile, mainYear, mainYearEnd);
    document.getElementById('summaryTargetData').textContent = formatDataSelection(targetFile, targetYear, targetYearEnd);
    document.getElementById('summaryBehavior').textContent = behaviorText || '尚未選擇';
    document.getElementById('summaryCancer').textContent = cancerText;
    document.getElementById('summaryModeAi').textContent = modeAi.selectedOptions[0]?.textContent?.trim() || '平穩客觀';
    document.getElementById('summaryItems').textContent = items.length ? items.join('、') : '尚未選擇';
  }

  function updateTopicCounts() {
    document.querySelectorAll('.cat-count-badge[data-parent-group]').forEach(badge => {
      const group = document.querySelector(`[data-compare-subitems="${badge.dataset.parentGroup}"]`);
      const count = group?.querySelectorAll('.compare-subitem-check:checked').length || 0;
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
    metaEl.textContent = `${selectEl.value}｜讀取中…`;
    toggleEl?.classList.add('d-none');
    markResultsStale();
    if (selectEl === mainFile) mainYears = [];
    if (selectEl === targetFile) targetYears = [];

    fetch('/api/dashboard/file_years', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: selectEl.value })
    })
      .then(r => r.json())
      .then(data => {
        if (!data.ok) throw new Error(data.error || '年度偵測失敗');
        if (selectEl === mainFile) mainYears = data.years || [];
        if (selectEl === targetFile) targetYears = data.years || [];
        fillYearSelect(inputEl, data.years || []);
        fillYearSelect(endInput, data.years || []);
        renderPreview(previewEl, data.preview);
        metaEl.textContent = `${selectEl.value}｜年度 ${yearText(data.years || [])}｜預覽 ${data.preview?.rows?.length || 0} 筆`;
        toggleEl?.classList.remove('d-none');
      })
      .catch(err => {
        if (selectEl === mainFile) mainYears = [];
        if (selectEl === targetFile) targetYears = [];
        inputEl.innerHTML = '<option value="" selected>偵測失敗</option>';
        inputEl.disabled = true;
        endInput.innerHTML = '<option value="" selected>偵測失敗</option>';
        endInput.disabled = true;
        showPreviewMessage(previewEl, err.message);
        metaEl.textContent = `${selectEl.value}｜讀取失敗`;
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
    return (values || []).reduce((total, value) => total + Number(value || 0), 0);
  }

  function normalizeGenderAgeData(genderAgeData) {
    const labels = ['<=19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49', '50-54', '55-59', '60-64', '65-69', '70-74', '75-79', '80-84', '>=85'];
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
        textStyle: { fontSize: 16, fontWeight: 'bold' }
      },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 50, right: 35, top: 62, bottom: 72, containLabel: true },
      legend: { data: ['男性', '女性', '總計'], bottom: 20 },
      toolbox: { right: 8, top: 0, feature: { dataView: { show: true, readOnly: false }, saveAsImage: { show: true } } },
      xAxis: [{
        type: 'category',
        data: data.categories,
        axisPointer: { type: 'shadow' },
        axisLabel: { interval: 0 }
      }],
      yAxis: [{
        type: 'value',
        name: '個案數',
        min: 0,
        max: yMax,
        minInterval: 1
      }],
      series: [
        { name: '男性', type: 'bar', data: data.male, itemStyle: { color: '#5470C6' } },
        { name: '女性', type: 'bar', data: data.female, itemStyle: { color: '#EE6666' } },
        { name: '總計', type: 'line', data: data.total, symbol: 'circle', itemStyle: { color: '#91CC75' }, lineStyle: { color: '#91CC75', width: 2 } }
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

  function viewSwitchBlock() {
    return `
      <div class="compare-view-switch" role="group" aria-label="結果顯示方式">
        <button type="button" class="compare-view-button active" data-compare-view="chart"><i class="bi bi-bar-chart me-1"></i>圖表</button>
        <button type="button" class="compare-view-button" data-compare-view="table"><i class="bi bi-table me-1"></i>表格</button>
      </div>
    `;
  }

  function ageMedianBlock(chartData, yearTitle, cancerTitle) {
    const item = chartData?.ageMedianData || {};
    return `
      <div class="annual-report-table-wrap compare-compact-table">
        <table class="annual-report-table">
          <caption>表、${yearTitle}年新診斷${getCancerTitleForSentence(cancerTitle)}病患年齡中位數表<br><span class="text-muted fw-normal" style="font-size: 0.85em;">資料來源：癌症登記資料庫</span></caption>
          <thead><tr><th rowspan="2">項目</th><th colspan="2">發生個案</th></tr><tr><th>男性</th><th>女性</th></tr></thead>
          <tbody>
            <tr><td>個案數(人)</td><td>${item.male_count || 0}</td><td>${item.female_count || 0}</td></tr>
            <tr><td>年齡中位數</td><td>${item.male || 0}</td><td>${item.female || 0}</td></tr>
            <tr><td>性別比</td><td>${item.male_ratio || '0.00'}</td><td>${item.female_ratio || '0.00'}</td></tr>
          </tbody>
        </table>
      </div>
    `;
  }

  function analyzableBlock(chartData, yearTitle, cancerTitle) {
    const item = chartData?.analyzableConfirmedData || {};
    return `
      <div class="annual-report-table-wrap compare-analyzable-table">
        <table class="annual-report-table">
          <caption>表、${yearTitle}年${getCancerTitleForSentence(cancerTitle)}－癌症登記可分析個案與確診個案<br><span class="text-muted fw-normal" style="font-size: 0.85em;">資料來源：癌症登記資料庫</span></caption>
          <thead>
            <tr>
              <th>${yearTitle}年癌症總數<br>(A)</th>
              <th>*可分析個案數<br>(B)</th>
              <th>可分析個案百分比 %<br>(B/A)</th>
              <th>顯微鏡檢確診個案數<br>(C)</th>
              <th>確診個案百分比 %<br>(C/B)</th>
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
        <div>* 可分析個案包含：</div>
        <div class="compare-note-lines">Class1 本院診斷，並於本院接受全部或部分首次治療。</div>
        <div class="compare-note-lines">Class2 他院診斷，於本院接受全部或部分首次治療。</div>
      </div>
    `;
  }

  function escapeHtml(value) {
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
            <td>合計</td>
            <td></td>
            <td>${totalCount}</td>
            <td>${validData.length ? '100.0%' : '0.0%'}</td>
          </tr>`
      : '<tr><td colspan="4" class="text-center py-4">無資料</td></tr>';

    return `
      ${viewSwitchBlock()}
      <div data-compare-view-panel="chart">
        <div id="${chartId}" class="compare-chart" style="height: 450px;"></div>
        <div class="compare-chart-caption">圖、${yearTitle}年新診斷${getCancerTitleForSentence(cancerTitle)}病患組織型態分佈圖</div>
        ${chartNotes}
      </div>
      <div data-compare-view-panel="table" class="d-none">
        <div class="annual-report-table-wrap">
          <table class="annual-report-table">
            <caption>表、${yearTitle}年${getCancerTitleForSentence(cancerTitle)}組織型態分佈表<br><span class="text-muted fw-normal" style="font-size: 0.85em;">資料來源：癌症登記資料庫</span></caption>
            <thead>
              <tr>
                <th>ICD-O編碼</th>
                <th>組織型態</th>
                <th>人數</th>
                <th>百分比%</th>
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
        title: 'Class0 本院診斷，未於本院接受首次治療',
        totalKey: 'class0_total',
        subClasses: [
          { key: '0_1_0', label: '未接受任何治療即死亡或病危(0.1.0)' },
          { key: '0_1_2', label: '首次療程未於本院進行，或本院僅提供支援／諮詢(0.1.2)' }
        ]
      },
      {
        title: 'Class1 本院診斷，並於本院接受全部或部分首次治療。',
        totalKey: 'class1_total',
        subClasses: [
          { key: '1_1_1', label: '首次療程僅於本院完成(1.1.1)' },
          { key: '1_1_3', label: '首次療程由本院與他院共同完成(1.1.3)' },
          { key: '1_1_4', label: '首次療程為觀察、支持性或緩和治療(1.1.4)' }
        ]
      },
      {
        title: 'Class2 他院診斷，於本院接受全部或部分首次治療。',
        totalKey: 'class2_total',
        subClasses: [
          { key: '2_2_1', label: '首次療程僅於本院完成(2.2.1)' },
          { key: '2_2_3', label: '首次療程由本院與他院共同完成(2.2.3)' }
        ]
      },
      {
        title: 'Class3 他院診斷，未於本院接受首次治療，或因復發／持續癌症問題至本院就診。',
        totalKey: 'class3_total',
        subClasses: [
          { key: '3_2_0', label: '未接受任何治療即死亡或病危(3.2.0)' },
          { key: '3_3_2', label: '首次療程未於本院進行，或本院僅提供支援／諮詢(3.3.2)' }
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

    rows += `<tr class="table-secondary fw-bold" style="font-weight: bold; border-top: 2px solid #6c757d;"><td class="text-center">總計</td><td class="text-center">${total}</td><td class="text-center">${total > 0 ? '100.0%' : '0.0%'}</td></tr>`;

    return `
      ${viewSwitchBlock()}
      <div data-compare-view-panel="chart">
        <div id="${chartId}" class="compare-chart" style="height: 450px;"></div>
        <div class="compare-chart-caption">圖、${yearTitle}年新診斷${getCancerTitleForSentence(cancerTitle)}病患個案分類分佈圖</div>
      </div>
      <div data-compare-view-panel="table" class="d-none">
        <div class="annual-report-table-wrap mb-4">
          <table class="annual-report-table text-start" style="width: 100%;">
            <caption>表、${yearTitle}年${getCancerTitleForSentence(cancerTitle)}個案分類分佈表<br><span class="text-muted fw-normal" style="font-size: 0.85em;">資料來源：癌症登記資料庫</span></caption>
            <thead><tr><th class="text-center">個案分類</th><th class="text-center">人數</th><th class="text-center">百分比%</th></tr></thead>
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

  function renderSexAgeChart(chartId, chartData, sharedScale) {
    if (!window.echarts) return;
    const chartEl = document.getElementById(chartId);
    if (!chartEl) return;
    const oldChart = echarts.getInstanceByDom(chartEl);
    if (oldChart) oldChart.dispose();
    const chart = echarts.init(chartEl);
    chart.setOption(getGenderAgeChartOption(chartData?.genderAgeData || {}, sharedScale?.genderAgeMax));
    setTimeout(() => chart.resize(), 50);
  }

  function renderHistologyChart(chartId, chartData, sharedScale) {
    if (!window.echarts) return;
    const chartEl = document.getElementById(chartId);
    if (!chartEl) return;
    const oldChart = echarts.getInstanceByDom(chartEl);
    if (oldChart) oldChart.dispose();

    const histologyData = Array.isArray(chartData?.histologyData) ? chartData.histologyData : [];
    const validData = histologyData.filter(item => item.name !== 'Unknown / 未對應組織型態');
    const totalCount = validData.reduce((total, item) => total + Number(item.count || 0), 0);
    const names = validData.map(item => item.name);
    const values = validData.map(item => {
      const value = totalCount > 0 ? Number((Number(item.count || 0) / totalCount * 100).toFixed(1)) : 0;
      return { value, count: Number(item.count || 0) };
    });

    const chart = echarts.init(chartEl);
    chart.setOption({
      title: { text: '組織型態分佈圖', subtext: '資料來源：癌症登記資料庫', left: 'center' },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: function(params) {
          const p = params[0];
          if (!p || p.value === undefined || p.value === '-') return '';
          const count = p.data && p.data.count !== undefined ? p.data.count : '-';
          const val = typeof p.value === 'number' ? p.value.toFixed(1) : p.value;
          return `${p.name}<br/>${p.marker}個案比例: ${val}% (${count}人)`;
        }
      },
      grid: { left: 300, right: 170, bottom: 50, top: 60, containLabel: false },
      legend: { show: false },
      toolbox: { feature: { dataView: { show: true, readOnly: false }, saveAsImage: { show: true } } },
      xAxis: { type: 'value', name: '百分比 (%)', nameLocation: 'middle', nameGap: 30, min: 0, max: sharedScale?.histologyMax, interval: 10, axisLabel: { formatter: value => Number(value).toFixed(1) + '%' } },
      yAxis: { type: 'category', data: names, inverse: true, axisLabel: { width: 280, overflow: 'break', lineHeight: 16, align: 'right', margin: 12 } },
      series: [{
        name: '個案比例',
        type: 'bar',
        data: values,
        itemStyle: { color: '#73c0de' },
        label: {
          show: true,
          position: 'right',
          color: '#111827',
          fontSize: 12,
          formatter: params => `${Number(params.value || 0).toFixed(1)}%（${Number(params.data?.count || 0)}人）`
        }
      }]
    });
    setTimeout(() => chart.resize(), 50);
  }

  function renderClassificationChart(chartId, chartData, sharedScale) {
    if (!window.echarts) return;
    const chartEl = document.getElementById(chartId);
    if (!chartEl) return;
    const oldChart = echarts.getInstanceByDom(chartEl);
    if (oldChart) oldChart.dispose();

    const data = chartData?.diagnosisClassificationData || {};
    const total = data.total_count || 1;
    const calcPctNum = value => Number((Number(value || 0) / total * 100).toFixed(1));
    const labels = [
      'Class0 本院診斷，未於本院接受首次治療',
      'Class1 本院診斷，並於本院接受全部或部分首次治療。',
      'Class2 他院診斷，於本院接受全部或部分首次治療。',
      'Class3 他院診斷，未於本院接受首次治療，或因復發／持續癌症問題至本院就診。'
    ];
    const colors = ['#5470C6', '#91CC75', '#FAC858', '#EE6666'];

    const chart = echarts.init(chartEl);
    chart.setOption({
      title: { text: '個案分類分佈圖', subtext: '資料來源：癌症登記資料庫', left: 'center', textStyle: { fontSize: 20, fontWeight: 'bold', color: '#333' } },
      toolbox: { show: true, feature: { dataView: { show: true, readOnly: false, title: '數據檢視', lang: ['數據檢視', '關閉', '更新'] }, saveAsImage: { show: true, title: '下載圖片' } } },
      legend: { orient: 'vertical', right: '2%', top: 'middle', itemWidth: 14, itemHeight: 14, data: labels, textStyle: { fontSize: 14, lineHeight: 24, width: 450, overflow: 'break' } },
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

  function reportBlock(item, chartData, meta, chartPrefix) {
    const cancerTitle = selectedCancerTitle();
    if (item === '性別年齡分佈') return sexAgeBlock(chartData, meta.year_label, cancerTitle, `${chartPrefix}SexAgeChart`);
    if (item === '年齡中位數') return ageMedianBlock(chartData, meta.year_label, cancerTitle);
    if (item === '可分析個案與確診個案') return analyzableBlock(chartData, meta.year_label, cancerTitle);
    if (item === '組織型態') return histologyBlock(chartData, meta.year_label, cancerTitle, `${chartPrefix}HistologyChart`);
    if (item === '個案分類') return classificationBlock(chartData, meta.year_label, cancerTitle, `${chartPrefix}ClassificationChart`);
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
    if (number === 0) return '持平';
    const amount = Number.isInteger(Math.abs(number)) ? Math.abs(number) : Math.abs(number).toFixed(1);
    return `${number > 0 ? '增加' : '減少'}${amount}${suffix}`;
  }

  function changePercentText(mainValue, targetValue) {
    const main = Number(mainValue || 0);
    const target = Number(targetValue || 0);
    if (!main) return target ? '無法計算' : '持平';
    const percentage = (target - main) / main * 100;
    if (percentage === 0) return '持平';
    return `${percentage > 0 ? '增加' : '減少'}${Math.abs(percentage).toFixed(1)}%`;
  }

  function changePercentValue(mainValue, targetValue) {
    const main = Number(mainValue || 0);
    const target = Number(targetValue || 0);
    if (!main) return target ? '無法計算' : '0.0%';
    return `${Math.abs((target - main) / main * 100).toFixed(1)}%`;
  }

  function renderDifferenceSummary(data) {
    const mainAnalysis = data.analysis_data?.main || {};
    const targetAnalysis = data.analysis_data?.target || {};
    const mainAge = mainAnalysis.ageMedianData || {};
    const targetAge = targetAnalysis.ageMedianData || {};
    const mainGender = normalizeGenderAgeData(mainAnalysis.genderAgeData || {});
    const targetGender = normalizeGenderAgeData(targetAnalysis.genderAgeData || {});
    const changes = targetGender.categories.map((label, index) => ({
      label,
      value: Number(targetGender.total[index] || 0) - Number(mainGender.total[index] || 0)
    }));
    const biggest = changes.sort((a, b) => Math.abs(b.value) - Math.abs(a.value))[0] || { label: '—', value: 0 };
    const totalDiff = Number(data.target?.total_count || 0) - Number(data.main?.total_count || 0);
    const medianDiff = Number(targetAge.total || 0) - Number(mainAge.total || 0);
    const maleChange = changePercentText(mainAge.male_count, targetAge.male_count);
    const femaleChange = changePercentText(mainAge.female_count, targetAge.female_count);
    const formatPeriod = label => String(label || '').includes('–') ? label : `${label}年`;
    const comparisonLabel = escapeHtml(`${formatPeriod(data.target?.year_label || '對照資料')}相較於${formatPeriod(data.main?.year_label || '基準資料')}`);
    const rangeAverage = data.compare_mode === 'range'
      ? `<div class="compare-summary-subvalue">年平均${changeNumberText(data.diff?.annual_average, '人')}</div>` : '';
    const valueClass = value => Number(value) > 0 ? 'is-up' : Number(value) < 0 ? 'is-down' : '';
    document.getElementById('compareResultSummary').innerHTML = `
      <div class="compare-summary-card"><div class="compare-summary-label">${comparisonLabel}的總個案數差異</div><div class="compare-summary-value ${valueClass(totalDiff)}">${changeNumberText(totalDiff, '人')}（${changePercentValue(data.main?.total_count, data.target?.total_count)}）${rangeAverage}</div></div>
      <div class="compare-summary-card"><div class="compare-summary-label">${comparisonLabel}的年齡中位數差異</div><div class="compare-summary-value ${valueClass(medianDiff)}">${changeNumberText(medianDiff, '歲')}</div></div>
      <div class="compare-summary-card"><div class="compare-summary-label">${comparisonLabel}的變化最大的年齡層</div><div class="compare-summary-value ${valueClass(biggest.value)}">${biggest.label}（${changeNumberText(biggest.value, '人')}）</div></div>
      <div class="compare-summary-card"><div class="compare-summary-label">${comparisonLabel}的性別個案變化</div><div class="compare-summary-value">男 ${maleChange}｜女 ${femaleChange}</div></div>
    `;
  }

  function renderAnnualReport(containerId, chartData, meta, chartPrefix, item, side, sharedScale) {
    const container = document.getElementById(containerId);
    container.innerHTML = reportBlock(item, chartData, meta, chartPrefix);
    bindViewSwitch(container, side);
    const viewSwitch = container.querySelector('.compare-view-switch');
    const resultHeading = container.closest('.compare-result-item')?.querySelector('.compare-result-heading');
    if (viewSwitch && resultHeading) resultHeading.appendChild(viewSwitch);
    if (item === '性別年齡分佈') renderSexAgeChart(`${chartPrefix}SexAgeChart`, chartData, sharedScale);
    if (item === '組織型態') {
      renderHistologyChart(`${chartPrefix}HistologyChart`, chartData, sharedScale);
    }
    if (item === '個案分類') renderClassificationChart(`${chartPrefix}ClassificationChart`, chartData, sharedScale);
  }

  function renderResultItem(data, item, index) {
    document.querySelectorAll('.compare-result-tab').forEach((button, buttonIndex) => {
      button.classList.toggle('active', buttonIndex === index);
    });

    const sharedScale = calculateSharedScale(data);
    document.getElementById('compareResultPanel').innerHTML = `
      <div class="compare-result-grid">
        <section class="compare-result-item is-main">
          <div class="compare-result-heading"><div><h3>基準資料｜${escapeHtml(data.main?.year_label || '—')}</h3></div></div>
          <div id="mainAnnualReport"></div>
        </section>
        <section class="compare-result-item is-target">
          <div class="compare-result-heading"><div><h3>對照資料｜${escapeHtml(data.target?.year_label || '—')}</h3></div></div>
          <div id="targetAnnualReport"></div>
        </section>
      </div>
    `;

    renderAnnualReport('mainAnnualReport', data.analysis_data?.main || {}, data.main, `main${index}`, item, 'main', sharedScale);
    renderAnnualReport('targetAnnualReport', data.analysis_data?.target || {}, data.target, `target${index}`, item, 'target', sharedScale);
  }

  function buildAiComparisonPayload(data, analysisItem) {
    const pickAnalysis = analysis => {
      const selectedAnalysis = {};
      if (analysisItem === '性別年齡分佈') selectedAnalysis.gender_age = analysis?.genderAgeData || {};
      if (analysisItem === '年齡中位數') selectedAnalysis.age_median = analysis?.ageMedianData || {};
      if (analysisItem === '可分析個案與確診個案') selectedAnalysis.analyzable_confirmed = analysis?.analyzableConfirmedData || {};
      if (analysisItem === '組織型態') selectedAnalysis.histology = (analysis?.histologyData || []).filter(item => item.name !== 'Unknown / 未對應組織型態');
      if (analysisItem === '個案分類') selectedAnalysis.diagnosis_classification = analysis?.diagnosisClassificationData || {};
      return selectedAnalysis;
    };
    return {
      comparison_definition: '所有差異均以對照資料減去基準資料計算；正值代表對照資料較高，負值代表對照資料較低。',
      comparison_direction: `${data.target?.year_label || '對照年度'}相較於${data.main?.year_label || '基準年度'}`,
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

  function fetchAiNarrative(data, analysisItem, force = false) {
    if (!force && aiNarrativeCache.has(analysisItem)) {
      return Promise.resolve(aiNarrativeCache.get(analysisItem));
    }

    const comparisonPayload = buildAiComparisonPayload(data, analysisItem);
    return fetch('/api/dashboard/compare_insight', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        analysis_item: analysisItem,
        comparison_direction: comparisonPayload.comparison_direction,
        selected_conditions: comparisonPayload.selected_conditions,
        baseline: comparisonPayload.baseline,
        comparison: comparisonPayload.comparison,
        total_difference: comparisonPayload.total_difference,
        mode_ai: modeAi.value
      })
    })
      .then(response => response.json())
      .then(result => {
        if (!result.success) throw new Error(result.error || '語言模型分析產生失敗');
        const insight = result.insight || '語言模型未回傳分析內容。';
        aiNarrativeCache.set(analysisItem, insight);
        return insight;
      })
      .catch(() => {
        const errorText = '語言模型比較敘述暫時無法產生，請確認模型服務設定或稍後再試。';
        aiNarrativeCache.set(analysisItem, errorText);
        return errorText;
      });
  }

  function renderAiNarrative(data, analysisItem, force = false) {
    const section = document.getElementById('compareAiNarrative');
    const text = document.getElementById('compareAiNarrativeText');
    const retryButton = document.getElementById('btnRetryAiNarrative');
    activeAiNarrativeItem = analysisItem;
    section.classList.remove('d-none');
    retryButton.disabled = true;
    if (!force && aiNarrativeCache.has(analysisItem)) {
      text.textContent = aiNarrativeCache.get(analysisItem);
      retryButton.disabled = false;
      return Promise.resolve(aiNarrativeCache.get(analysisItem));
    }
    const requestId = ++aiNarrativeRequestId;
    text.innerHTML = '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>語言模型正在整理兩年度的比較差異，請稍候…';

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
    const chart = echarts.getInstanceByDom(container) || echarts.init(container);
    chart.setOption({
      color: ['#2563eb', '#f97316'],
      title: { text: '年度區間個案數趨勢', left: 'center', top: 18, textStyle: { fontSize: 16 } },
      tooltip: { trigger: 'axis' },
      legend: { top: 52, data: [`基準 ${data.main?.year_label || ''}`, `對照 ${data.target?.year_label || ''}`] },
      grid: { left: 50, right: 35, top: 92, bottom: 30, containLabel: true },
      xAxis: {
        type: 'category',
        name: '年度',
        nameLocation: 'middle',
        nameGap: 30,
        data: years,
        boundaryGap: true,
        axisTick: { alignWithLabel: true },
        axisLabel: { margin: 10 }
      },
      yAxis: { type: 'value', name: '個案數', minInterval: 1 },
      series: [
        {
          name: `基準 ${data.main?.year_label || ''}`,
          type: 'line',
          connectNulls: false,
          symbolSize: 8,
          data: years.map(year => Object.prototype.hasOwnProperty.call(mainCounts, year) ? mainCounts[year] : null)
        },
        {
          name: `對照 ${data.target?.year_label || ''}`,
          type: 'line',
          connectNulls: false,
          symbolSize: 8,
          data: years.map(year => Object.prototype.hasOwnProperty.call(targetCounts, year) ? targetCounts[year] : null)
        }
      ]
    }, true);
    setTimeout(() => chart.resize(), 0);
  }

  function renderResult(data) {
    const items = selectedCompareItems();
    lastComparisonData = data;
    hasRenderedResult = true;
    resultStale.classList.add('d-none');
    renderDifferenceSummary(data);
    renderRangeTrend(data);
    const tabs = document.getElementById('compareResultTabs');
    tabs.innerHTML = items.map((item, index) => `
      <button type="button" class="compare-result-tab ${index === 0 ? 'active' : ''}" data-index="${index}">${item}</button>
    `).join('');
    tabs.querySelectorAll('.compare-result-tab').forEach(button => {
      button.addEventListener('click', () => {
        const index = Number(button.dataset.index);
        renderResultItem(data, items[index], index);
        renderAiNarrative(data, items[index]);
      });
    });

    if (items.length > 0) renderResultItem(data, items[0], 0);
    resultBox.classList.remove('d-none');
    if (items.length > 0) renderAiNarrative(data, items[0]);
  }

  function showAlert(title, text) {
    if (window.Swal) Swal.fire({ icon: 'warning', title, text, confirmButtonColor: '#2563eb' });
    else alert(text || title);
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
    clearDataSelection(mainFile, mainYear, mainYearEnd, mainMeta, mainPreview, '基準資料預覽');
    clearDataSelection(targetFile, targetYear, targetYearEnd, targetMeta, targetPreview, '對照資料預覽');
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
  mainYear.addEventListener('change', () => { markResultsStale(); updateButtonState(); });
  targetYear.addEventListener('change', () => { markResultsStale(); updateButtonState(); });
  mainYearEnd.addEventListener('change', () => { markResultsStale(); updateButtonState(); });
  targetYearEnd.addEventListener('change', () => { markResultsStale(); updateButtonState(); });
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
    input.addEventListener('change', () => { markResultsStale(); updateButtonState(); });
  });
  document.getElementById('btnSelectAllCompareItems').addEventListener('click', () => {
    document.querySelectorAll(`[data-compare-subitems="${selectedCompareType()}"] .compare-subitem-check:not(:disabled)`).forEach(input => { input.checked = true; });
    markResultsStale();
    updateButtonState();
  });
  document.getElementById('btnClearCompareItems').addEventListener('click', () => {
    document.querySelectorAll(`[data-compare-subitems="${selectedCompareType()}"] .compare-subitem-check`).forEach(input => { input.checked = false; });
    markResultsStale();
    updateButtonState();
  });
  document.getElementById('btnRetryAiNarrative').addEventListener('click', () => {
    if (lastComparisonData && activeAiNarrativeItem) renderAiNarrative(lastComparisonData, activeAiNarrativeItem, true);
  });
  resetButton.addEventListener('click', resetComparison);
  document.getElementById('btnReselectMain').addEventListener('click', () => {
    reselectData(mainFile, mainYear, mainYearEnd, mainMeta, mainPreview, '基準資料預覽');
  });
  document.getElementById('btnReselectTarget').addEventListener('click', () => {
    reselectData(targetFile, targetYear, targetYearEnd, targetMeta, targetPreview, '對照資料預覽');
  });
  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(updateButtonState, 0);
  });

  runButton.addEventListener('click', () => {
    if (selectedCompareMode() === 'range'
        && (Number(mainYear.value) > Number(mainYearEnd.value)
          || Number(targetYear.value) > Number(targetYearEnd.value))) {
      showAlert('年度區間不正確', '起始年度不可晚於結束年度。');
      return;
    }
    if (!filesReady()) {
      showAlert('資料不可相同', '基準資料與對照資料不可使用相同檔案及相同年度。');
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
    [mainPreview, targetPreview].forEach(preview => preview.classList.add('d-none'));
    document.querySelectorAll('.compare-preview-toggle').forEach(button => { button.textContent = '查看資料預覽'; });
    resultBox.classList.add('d-none');
    runButton.disabled = true;
    runButton.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> 比較中...';
    if (window.utils && window.utils.showLoading) {
      window.utils.showLoading('分析中，請稍候...');
    }
    fetch('/api/dashboard/compare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        main_filename: mainFile.value,
        target_filename: targetFile.value,
        main_year: mainYear.value,
        target_year: targetYear.value,
        main_year_end: selectedCompareMode() === 'range' ? mainYearEnd.value : mainYear.value,
        target_year_end: selectedCompareMode() === 'range' ? targetYearEnd.value : targetYear.value,
        compare_mode: selectedCompareMode(),
        behavior: behavior.value,
        cancers: selectedCancerValues(),
        compare_type: selectedCompareType(),
        compare_items: selectedCompareItems()
      })
    })
      .then(r => r.json())
      .then(data => {
        if (!data.ok) throw new Error(data.error || '比較失敗');
        const items = selectedCompareItems();
        aiNarrativeCache.clear();
        return Promise.all(items.map(item => fetchAiNarrative(data.data, item)))
          .then(() => {
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
