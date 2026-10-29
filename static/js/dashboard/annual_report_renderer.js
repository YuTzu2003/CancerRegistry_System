(function(global) {
  const DEFAULT_AGE_GROUPS = [
    '≤19', '20-24', '25-29', '30-34', '35-39',
    '40-44', '45-49', '50-54', '55-59', '60-64',
    '65-69', '70-74', '75-79', '80-84', '≥85'
  ];
  const GENDER_AGE_COLORS = Object.freeze({
    male: '#5470C6',
    female: '#EE6666',
    total: '#91CC75'
  });
  // ECharts calculates one uniform width for every age group in a chart.
  // The maximum keeps the bars from becoming oversized on wide displays.
  const GENDER_AGE_BAR_MAX_WIDTH = 16;
  const RESULT_TAB_ENGLISH = Object.freeze({
    '性別年齡分佈': 'Sex and age distribution',
    '性別年齡分布': 'Sex and age distribution',
    '年齡中位數': 'Median age',
    '可分析個案與確診個案': 'Analyzable and confirmed cases',
    '組織型態': 'Histology',
    '個案分類': 'Case classification',
    '期別': 'Stage',
    '分期呈現最細碼': 'Detailed stage',
    '分期不呈現最細碼': 'Stage summary',
    '期別與首次療程': 'Stage and first course treatment',
    '期別與手術術式': 'Stage and surgical procedure',
    '存活率': 'Survival',
    '歷年年齡中位數': 'Median age over time',
    '歷年期別分佈': 'Stage distribution over time',
    '歷年新診斷件數': 'New diagnoses over time',
    '本院常見癌症': 'Common cancers at our hospital'
  });
  function resultTabLabel(label, language) {
    return language === 'en' ? (RESULT_TAB_ENGLISH[label] || label) : label;
  }
  function surgeryTableKey(table, index) {
    return `${table?.manual_key || 'unknown'}::${table?.system || 'stage'}::${index}`;
  }
  function surgeryInsightKey(table, index) {
    return `期別與手術術式|${surgeryTableKey(table, index)}`;
  }
  const SURGERY_STAGE_MANUALS = Object.freeze({
    FIGO: ['Cervix_Uteri', 'Corpus_Uteri', 'Ovary'],
    MAC: ['Colon', 'Rectum'], BCLC: ['Liver'], SCLC: ['Lung'],
    DSS: ['Plasma_cell_neoplasms'], DRE: ['Prostate'],
    'Breast Cancer Prognostic Stage': ['Breast'], Binet: ['CLL']
  });
  function surgeryStageApplicable(table) {
    return table?.system === 'AJCC' || (SURGERY_STAGE_MANUALS[table?.system] || []).includes(table?.manual_key);
  }
  const ANALYSIS_CONDITIONS = Object.freeze([
    { label: '性別年齡分佈', analysisId: 'chkIncidenceAge', comparisonId: 'compareItemGenderAge' },
    { label: '年齡中位數', analysisId: 'chkIncidenceMedian', comparisonId: 'compareItemAgeMedian' },
    { label: '可分析個案與確診個案', analysisId: 'chkDiagnosisAnalyzable', comparisonId: 'compareItemAnalyzable' },
    { label: '組織型態', analysisId: 'chkDiagnosisHistology', comparisonId: 'compareItemHistology' },
    { label: '個案分類', analysisId: 'chkDiagnosisClassification', comparisonId: 'compareItemClassification' },
    { label: 'AJCC期別分佈', analysisId: 'chkStageAjcc', comparisonId: 'compareItemStageAjcc' },
    { label: 'FIGO/MAC/BCLC/SCLC期別分佈', analysisId: 'chkStageOtherSystems', comparisonId: 'compareItemStageOtherSystems' },
    { label: '期別與首次療程', analysisId: 'chkTreatmentFirstCourse', comparisonId: 'compareItemTreatmentFirstCourse' },
    { label: '期別與手術術式', analysisId: 'chkTreatmentSurgery', comparisonId: 'compareItemTreatmentSurgery' },
    { label: '存活率', analysisId: 'chkCrossYearSurvival', comparisonId: 'compareItemSurvival' },
    { label: '歷年年齡中位數', analysisId: 'chkCrossYearMedianAge', comparisonId: 'compareItemCrossMedianAge' },
    { label: '歷年期別分佈', analysisId: 'chkCrossYearStage', comparisonId: 'compareItemCrossStage' },
    { label: '歷年新診斷件數', analysisId: 'chkCrossYearNewCases', comparisonId: 'compareItemCrossNewCases' },
    { label: '本院常見癌症', analysisId: 'chkCrossYearCommonCancers', comparisonId: 'compareItemCommonCancers' }
  ]);

  function sum(values) {
    return (values || []).reduce((total, value) => total + Number(value || 0), 0);
  }

  function normalizeAgeGroupLabel(label) {
    const value = String(label ?? '');
    if (['<=19', '≤19', '≦19'].includes(value)) return '≤19';
    if (['>=85', '≥85', '≧85'].includes(value)) return '≥85';
    return value;
  }

  function normalizeGenderAgeData(genderAgeData) {
    const sourceCategories = Array.isArray(genderAgeData?.categories) && genderAgeData.categories.length
      ? genderAgeData.categories
      : DEFAULT_AGE_GROUPS;
    const categories = sourceCategories.map(normalizeAgeGroupLabel);
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

  function calculateGenderAgeMax(genderAgeData, sharedMax = null) {
    if (Number(sharedMax) > 0) return Number(sharedMax);
    const data = normalizeGenderAgeData(genderAgeData);
    const maxValue = Math.max(0, ...data.male, ...data.female, ...data.total);
    return Math.max(10, Math.ceil((maxValue * 1.15) / 5) * 5);
  }

  function axisLabelLines(value, maxLength = 68) {
    const lines = [];
    const segments = String(value ?? '')
      .trim()
      // 中文原位癌後綴視為名稱的一部分，不強制拆成下一行。
      .replace(/\s*(?=[[(])/g, '\n')
      .split('\n')
      .filter(Boolean);
    segments.forEach(segment => {
      let line = '';
      const segmentMaxLength = /^[[(]/.test(segment) ? 88 : 82;
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
    return axisLabelLines(value, maxLength)
      .map(text => `{${/^[[(]/.test(text) ? 'bracket' : 'right'}|${text}}`)
      .join('\n');
  }

  function histologyRowHeight(names) {
    const maxLines = Math.max(1, ...(names || []).map(name => axisLabelLines(name).length));
    return Math.max(40, maxLines * 18 + 8);
  }

  function escapeHtml(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function applyConditionCatalog(root = document, mode = 'analysis') {
    const idKey = mode === 'comparison' ? 'comparisonId' : 'analysisId';
    ANALYSIS_CONDITIONS.forEach(item => {
      const input = root.getElementById(item[idKey]);
      if (!input) return;
      input.value = item.label;
      const label = root.querySelector(`label[for="${item[idKey]}"]`);
      if (label) label.textContent = item.label;
    });
  }

  function getGenderAgeChartOption(genderAgeData, options = {}) {
    const data = normalizeGenderAgeData(genderAgeData);
    const labels = {
      male: options.labels?.male || '男性',
      female: options.labels?.female || '女性',
      total: options.labels?.total || '總計',
      age: options.labels?.age || '年齡',
      dataView: options.labels?.dataView || '資料檢視',
      close: options.labels?.close || '關閉',
      refresh: options.labels?.refresh || '重新整理',
      downloadImage: options.labels?.downloadImage || '下載圖片'
    };
    const legendLabels = [labels.male, labels.female, labels.total];

    return {
      title: {
        text: options.title || '',
        subtext: options.source || '',
        left: 'center',
        top: 0,
        textStyle: { fontSize: 18, fontWeight: 'bold' },
        subtextStyle: { fontSize: 12 }
      },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 72, right: 72, top: 98, bottom: 74, containLabel: false },
      legend: { data: legendLabels, top: 52, left: 'center', itemGap: 12 },
      toolbox: {
        right: 16,
        top: 0,
        feature: {
          dataView: {
            show: true,
            readOnly: false,
            title: labels.dataView,
            lang: [labels.dataView, labels.close, labels.refresh]
          },
          saveAsImage: { show: true, title: labels.downloadImage }
        }
      },
      xAxis: [{
        type: 'category',
        data: data.categories,
        name: labels.age,
        nameLocation: 'middle',
        nameGap: 30,
        axisPointer: { type: 'shadow' },
        axisTick: { alignWithLabel: true },
        axisLabel: { interval: 0 }
      }],
      yAxis: [{
        type: 'value',
        min: 0,
        max: calculateGenderAgeMax(data, options.sharedMax),
        minInterval: 1,
        splitNumber: 5,
        axisLabel: { formatter: '{value}' },
        splitLine: { lineStyle: { color: '#e5eaf3' } }
      }],
      series: [
        {
          name: labels.male,
          type: 'bar',
          data: data.male,
          barMaxWidth: GENDER_AGE_BAR_MAX_WIDTH,
          // Keep the three series visually grouped, while leaving a clearer
          // separation before the next age group.
          barGap: '10%',
          barCategoryGap: '48%',
          itemStyle: { color: GENDER_AGE_COLORS.male }
        },
        {
          name: labels.female,
          type: 'bar',
          data: data.female,
          barMaxWidth: GENDER_AGE_BAR_MAX_WIDTH,
          itemStyle: { color: GENDER_AGE_COLORS.female }
        },
        {
          name: labels.total,
          type: 'bar',
          data: data.total,
          barMaxWidth: GENDER_AGE_BAR_MAX_WIDTH,
          z: 5,
          itemStyle: { color: GENDER_AGE_COLORS.total }
        }
      ]
    };
  }

  global.AnnualReportRenderer = Object.freeze({
    DEFAULT_AGE_GROUPS,
    GENDER_AGE_COLORS,
    ANALYSIS_CONDITIONS,
    resultTabLabel,
    surgeryTableKey,
    surgeryInsightKey,
    surgeryStageApplicable,
    sum,
    normalizeAgeGroupLabel,
    normalizeGenderAgeData,
    calculateGenderAgeMax,
    axisLabelLines,
    rightAlignedAxisLabel,
    histologyRowHeight,
    escapeHtml,
    applyConditionCatalog,
    getGenderAgeChartOption
  });
})(window);
